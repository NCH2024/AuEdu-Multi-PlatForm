"""
tests/test_resource_monitor.py
==============================
Giám sát Tài nguyên Hệ thống (Resource Monitor) – AuEdu Face Recognition

Mục đích:
    Đo lường mức tiêu thụ tài nguyên hệ thống khi AI Engine hoạt động:
        1. CPU Usage (%) – mức sử dụng CPU
        2. RAM Usage (MB) – bộ nhớ tiến trình hiện tại
        3. GPU Usage (%) – mức sử dụng GPU (NVIDIA)
        4. VRAM Usage (MB) – bộ nhớ GPU
    So sánh 3 trạng thái: Idle (nghỉ), Processing (đang xử lý), Peak (đỉnh).
    Bổ sung: Đo kích thước cài đặt ứng dụng (Server + Client).

Phụ thuộc:
    - psutil: pip install psutil         (bắt buộc – CPU/RAM monitoring)
    - pynvml:  pip install pynvml        (tùy chọn – GPU monitoring, NVIDIA only)

Sử dụng:
    python tests/test_resource_monitor.py
    python tests/test_resource_monitor.py --duration 60 --image path/to/face.jpg
    python tests/test_resource_monitor.py --output tests/results/my_resource.json

Kết quả được in ra console dạng bảng so sánh và lưu vào file JSON.
"""

# ==============================================================================
# 0. THIẾT LẬP MÔI TRƯỜNG
# ==============================================================================
import sys
import os
import time
import json
import argparse
import base64
import threading
from pathlib import Path

# Thêm thư mục Server vào sys.path để import được app.ai.engine
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SERVER_DIR = _PROJECT_ROOT / "Server"
_CLIENT_DIR = _PROJECT_ROOT / "Client"
sys.path.insert(0, str(_SERVER_DIR))

# Đặt working directory về Server để .env và calib.npy được tìm thấy đúng
os.chdir(str(_SERVER_DIR))

import cv2
import numpy as np

# ==============================================================================
# 1. KIỂM TRA THƯ VIỆN PHỤ THUỘC
# ==============================================================================

# ── psutil: CPU/RAM monitoring (BẮT BUỘC) ──
try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

# ── pynvml: GPU monitoring qua NVIDIA Management Library (TÙY CHỌN) ──
_PYNVML_AVAILABLE = False
_GPU_NAME = "N/A"
try:
    import pynvml
    pynvml.nvmlInit()
    _gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    _GPU_NAME = pynvml.nvmlDeviceGetName(_gpu_handle)
    if isinstance(_GPU_NAME, bytes):
        _GPU_NAME = _GPU_NAME.decode("utf-8")
    _PYNVML_AVAILABLE = True
except Exception:
    _gpu_handle = None


def check_dependencies():
    """Kiểm tra và in hướng dẫn cài đặt nếu thiếu thư viện."""
    if not _PSUTIL_AVAILABLE:
        print("╔" + "═" * 70 + "╗")
        print("║  ❌ THƯ VIỆN 'psutil' CHƯA ĐƯỢC CÀI ĐẶT                           ║")
        print("║                                                                      ║")
        print("║  psutil là thư viện bắt buộc để giám sát CPU và RAM.                 ║")
        print("║  Hãy cài đặt bằng lệnh:                                              ║")
        print("║                                                                      ║")
        print("║      pip install psutil                                               ║")
        print("║                                                                      ║")
        print("║  Hoặc nếu dùng virtual environment của Server:                        ║")
        print("║      Server\\venv\\Scripts\\pip install psutil                          ║")
        print("╚" + "═" * 70 + "╝")
        sys.exit(1)

    if not _PYNVML_AVAILABLE:
        print("┌" + "─" * 70 + "┐")
        print("│  ⚠  THƯ VIỆN 'pynvml' KHÔNG KHẢ DỤNG                                │")
        print("│                                                                      │")
        print("│  GPU monitoring sẽ bị tắt. Để bật, cài đặt:                          │")
        print("│      pip install pynvml                                               │")
        print("│                                                                      │")
        print("│  Lưu ý: Chỉ hoạt động với GPU NVIDIA có driver đã cài đặt.           │")
        print("│  Script vẫn chạy bình thường với chỉ CPU/RAM monitoring.              │")
        print("└" + "─" * 70 + "┘")
    else:
        print(f"[INFO] GPU detected: {_GPU_NAME}")


# ==============================================================================
# 2. HÀM TẠO ẢNH THỬ NGHIỆM
# ==============================================================================

def generate_synthetic_face_image(width: int = 640, height: int = 480) -> np.ndarray:
    """
    Tạo ảnh BGR giả lập chứa hình oval mô phỏng khuôn mặt.
    Giống với test_latency.py để đảm bảo tính nhất quán.
    """
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        shade = int(180 + 40 * (y / height))
        img[y, :] = (shade, shade, shade)

    cx, cy = width // 2, height // 2
    cv2.ellipse(img, (cx, cy), (80, 110), 0, 0, 360, (180, 200, 230), -1)
    cv2.circle(img, (cx - 30, cy - 25), 8, (50, 50, 50), -1)
    cv2.circle(img, (cx + 30, cy - 25), 8, (50, 50, 50), -1)
    cv2.ellipse(img, (cx, cy + 35), (25, 10), 0, 0, 180, (100, 100, 180), 2)

    return img


def load_or_generate_image(image_path: str = None) -> np.ndarray:
    """Tải ảnh từ đường dẫn hoặc tạo ảnh giả lập."""
    if image_path and os.path.exists(image_path):
        img = cv2.imread(image_path)
        if img is not None:
            print(f"[INFO] Đã tải ảnh thật: {image_path} ({img.shape[1]}x{img.shape[0]})")
            return img
        else:
            print(f"[WARN] Không đọc được ảnh: {image_path}. Dùng ảnh giả lập.")

    print("[INFO] Sử dụng ảnh giả lập (synthetic face-like image).")
    return generate_synthetic_face_image()


def image_to_base64(img_bgr: np.ndarray, quality: int = 85) -> str:
    """Encode ảnh BGR thành chuỗi Base64 JPEG."""
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ==============================================================================
# 3. LỚP THU THẬP TÀI NGUYÊN (Resource Sampler)
# ==============================================================================

class ResourceSampler:
    """
    Thread-safe sampler thu thập CPU%, RAM, GPU%, VRAM theo chu kỳ.
    
    Chạy trên một thread riêng, lấy mẫu mỗi sample_interval giây.
    Lưu trữ toàn bộ samples để tính avg, peak sau.
    """

    def __init__(self, sample_interval: float = 0.5):
        """
        Args:
            sample_interval: Khoảng thời gian giữa các lần lấy mẫu (giây).
                             0.5s = 2 mẫu/giây, đủ chính xác cho benchmark.
        """
        self.sample_interval = sample_interval
        self.samples = []           # Danh sách tất cả samples đã thu thập
        self._running = False       # Flag điều khiển thread
        self._thread = None         # Thread lấy mẫu
        self._process = psutil.Process(os.getpid())  # Tiến trình hiện tại

    def _get_gpu_stats(self) -> dict:
        """
        Lấy thông tin GPU từ pynvml (NVIDIA).
        Trả về dict: gpu_util (%), vram_used_mb, vram_total_mb
        """
        if not _PYNVML_AVAILABLE:
            return {"gpu_util": 0.0, "vram_used_mb": 0.0, "vram_total_mb": 0.0}

        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(_gpu_handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(_gpu_handle)
            return {
                "gpu_util": float(util.gpu),
                "vram_used_mb": round(mem_info.used / (1024 ** 2), 1),
                "vram_total_mb": round(mem_info.total / (1024 ** 2), 1),
            }
        except Exception:
            return {"gpu_util": 0.0, "vram_used_mb": 0.0, "vram_total_mb": 0.0}

    def _sample_once(self) -> dict:
        """Thu thập một lần mẫu tài nguyên hiện tại."""
        # CPU Usage: dùng per-process CPU % (interval=None → non-blocking)
        cpu_percent = self._process.cpu_percent(interval=None)

        # RAM: bộ nhớ RSS (Resident Set Size) của tiến trình
        mem_info = self._process.memory_info()
        ram_mb = round(mem_info.rss / (1024 ** 2), 1)

        # System-wide CPU (tất cả các core)
        system_cpu = psutil.cpu_percent(interval=None)

        # GPU stats
        gpu = self._get_gpu_stats()

        return {
            "timestamp": time.time(),
            "process_cpu_percent": cpu_percent,
            "system_cpu_percent": system_cpu,
            "ram_mb": ram_mb,
            "gpu_util_percent": gpu["gpu_util"],
            "vram_used_mb": gpu["vram_used_mb"],
            "vram_total_mb": gpu["vram_total_mb"],
        }

    def _sampling_loop(self):
        """Vòng lặp chạy trên thread riêng, liên tục lấy mẫu."""
        # Khởi tạo CPU % tracking (lần đầu luôn trả 0.0)
        self._process.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None)
        time.sleep(0.1)  # Đợi một chút để có baseline

        while self._running:
            sample = self._sample_once()
            self.samples.append(sample)
            time.sleep(self.sample_interval)

    def start(self):
        """Bắt đầu thu thập mẫu trên background thread."""
        self.samples = []
        self._running = True
        self._thread = threading.Thread(target=self._sampling_loop, daemon=True)
        self._thread.start()

    def stop(self) -> list:
        """Dừng thu thập và trả về tất cả samples."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        return self.samples

    @staticmethod
    def compute_aggregate(samples: list) -> dict:
        """
        Tính avg, min, max, peak từ danh sách samples.
        
        Returns:
            dict chứa avg/peak cho mỗi metric
        """
        if not samples:
            return {
                "sample_count": 0,
                "cpu_avg": 0, "cpu_peak": 0,
                "system_cpu_avg": 0, "system_cpu_peak": 0,
                "ram_avg_mb": 0, "ram_peak_mb": 0,
                "gpu_avg": 0, "gpu_peak": 0,
                "vram_avg_mb": 0, "vram_peak_mb": 0,
                "vram_total_mb": 0,
            }

        return {
            "sample_count": len(samples),
            # Process CPU
            "cpu_avg": round(sum(s["process_cpu_percent"] for s in samples) / len(samples), 1),
            "cpu_peak": round(max(s["process_cpu_percent"] for s in samples), 1),
            # System CPU
            "system_cpu_avg": round(sum(s["system_cpu_percent"] for s in samples) / len(samples), 1),
            "system_cpu_peak": round(max(s["system_cpu_percent"] for s in samples), 1),
            # RAM
            "ram_avg_mb": round(sum(s["ram_mb"] for s in samples) / len(samples), 1),
            "ram_peak_mb": round(max(s["ram_mb"] for s in samples), 1),
            # GPU
            "gpu_avg": round(sum(s["gpu_util_percent"] for s in samples) / len(samples), 1),
            "gpu_peak": round(max(s["gpu_util_percent"] for s in samples), 1),
            # VRAM
            "vram_avg_mb": round(sum(s["vram_used_mb"] for s in samples) / len(samples), 1),
            "vram_peak_mb": round(max(s["vram_used_mb"] for s in samples), 1),
            "vram_total_mb": round(samples[0]["vram_total_mb"], 1) if samples else 0,
        }


# ==============================================================================
# 4. ĐO KÍCH THƯỚC CÀI ĐẶT ỨNG DỤNG
# ==============================================================================

def get_directory_size(dir_path: Path, exclude_dirs: set = None) -> dict:
    """
    Tính tổng kích thước thư mục (đệ quy), loại trừ các thư mục không cần thiết.
    
    Args:
        dir_path: Đường dẫn thư mục
        exclude_dirs: Tập tên thư mục cần loại trừ (vd: venv, __pycache__, .git)
    
    Returns:
        dict: total_bytes, total_mb, file_count
    """
    if exclude_dirs is None:
        exclude_dirs = {"venv", "venv-linux", "__pycache__", ".git", "node_modules", "build"}

    total_bytes = 0
    file_count = 0

    if not dir_path.exists():
        return {"total_bytes": 0, "total_mb": 0, "file_count": 0}

    for item in dir_path.rglob("*"):
        # Bỏ qua thư mục trong exclude list
        if any(exc in item.parts for exc in exclude_dirs):
            continue
        if item.is_file():
            try:
                total_bytes += item.stat().st_size
                file_count += 1
            except (OSError, PermissionError):
                pass

    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 ** 2), 2),
        "file_count": file_count,
    }


def measure_install_size() -> dict:
    """
    Đo kích thước cài đặt của Server và Client directories.
    Loại trừ venv, __pycache__, build để phản ánh kích thước source thật.
    """
    print("\n" + "=" * 70)
    print("  ĐO KÍCH THƯỚC CÀI ĐẶT ỨNG DỤNG")
    print("=" * 70)

    server_size = get_directory_size(_SERVER_DIR)
    client_size = get_directory_size(_CLIENT_DIR)

    total_mb = server_size["total_mb"] + client_size["total_mb"]

    print(f"  Server: {server_size['total_mb']:>8.2f} MB ({server_size['file_count']} files)")
    print(f"  Client: {client_size['total_mb']:>8.2f} MB ({client_size['file_count']} files)")
    print(f"  ──────────────────────")
    print(f"  Tổng:   {total_mb:>8.2f} MB")
    print(f"  (Đã loại trừ: venv, __pycache__, .git, node_modules, build)")

    return {
        "server": server_size,
        "client": client_size,
        "total_mb": total_mb,
    }


# ==============================================================================
# 5. ĐO TÀI NGUYÊN Ở TRẠNG THÁI IDLE
# ==============================================================================

def measure_idle(sampler: ResourceSampler, idle_duration: float = 5.0) -> dict:
    """
    Đo tài nguyên khi AI Engine đã load nhưng KHÔNG xử lý gì.
    
    Args:
        sampler: ResourceSampler instance
        idle_duration: Thời gian đo idle (giây)
    
    Returns:
        dict aggregate stats cho trạng thái idle
    """
    print("\n" + "=" * 70)
    print(f"  PHASE 1: ĐO TÀI NGUYÊN IDLE ({idle_duration:.0f}s)")
    print("=" * 70)
    print("  Engine đã load, đang chờ (không xử lý frame)...")

    sampler.start()
    time.sleep(idle_duration)
    idle_samples = sampler.stop()

    result = ResourceSampler.compute_aggregate(idle_samples)
    print(f"  Thu thập: {result['sample_count']} mẫu")
    print(f"  CPU (process): avg={result['cpu_avg']}%, peak={result['cpu_peak']}%")
    print(f"  RAM: avg={result['ram_avg_mb']} MB, peak={result['ram_peak_mb']} MB")
    if _PYNVML_AVAILABLE:
        print(f"  GPU: avg={result['gpu_avg']}%, peak={result['gpu_peak']}%")
        print(f"  VRAM: avg={result['vram_avg_mb']} MB, peak={result['vram_peak_mb']} MB")

    return result


# ==============================================================================
# 6. ĐO TÀI NGUYÊN TRONG QUÁ TRÌNH XỬ LÝ
# ==============================================================================

def measure_processing(sampler: ResourceSampler, face_engine, b64_image: str,
                       duration: float = 30.0) -> dict:
    """
    Đo tài nguyên khi AI Engine đang xử lý frame liên tục.
    
    Chạy process_attendance_frame() liên tục trong 'duration' giây,
    đồng thời thu thập mẫu tài nguyên trên thread riêng.
    
    Args:
        sampler: ResourceSampler instance
        face_engine: FaceEngine instance
        b64_image: Ảnh Base64 để xử lý
        duration: Thời gian đo (giây)
    
    Returns:
        dict chứa aggregate stats + frames_processed + fps
    """
    print("\n" + "=" * 70)
    print(f"  PHASE 2: ĐO TÀI NGUYÊN PROCESSING ({duration:.0f}s)")
    print("=" * 70)
    print("  Đang xử lý frame liên tục...")

    # Warm-up: 3 frame trước khi bắt đầu đo
    for _ in range(3):
        face_engine.process_attendance_frame(b64_image, mode="1")

    # Bắt đầu sampling + processing đồng thời
    sampler.start()

    frame_count = 0
    t_start = time.perf_counter()
    t_end_target = t_start + duration

    while time.perf_counter() < t_end_target:
        face_engine.process_attendance_frame(b64_image, mode="1")
        frame_count += 1

        # In tiến trình mỗi 5 giây
        elapsed = time.perf_counter() - t_start
        if frame_count % 50 == 0:
            current_fps = frame_count / elapsed
            print(f"  ... {elapsed:.0f}s | {frame_count} frames | {current_fps:.1f} FPS")

    actual_duration = time.perf_counter() - t_start
    processing_samples = sampler.stop()

    result = ResourceSampler.compute_aggregate(processing_samples)
    fps = frame_count / actual_duration if actual_duration > 0 else 0

    # Thêm thông tin processing
    result["frames_processed"] = frame_count
    result["duration_sec"] = round(actual_duration, 2)
    result["fps"] = round(fps, 2)

    print(f"\n  Thu thập: {result['sample_count']} mẫu, {frame_count} frames trong {actual_duration:.1f}s")
    print(f"  CPU (process): avg={result['cpu_avg']}%, peak={result['cpu_peak']}%")
    print(f"  RAM: avg={result['ram_avg_mb']} MB, peak={result['ram_peak_mb']} MB")
    if _PYNVML_AVAILABLE:
        print(f"  GPU: avg={result['gpu_avg']}%, peak={result['gpu_peak']}%")
        print(f"  VRAM: avg={result['vram_avg_mb']} MB, peak={result['vram_peak_mb']} MB")
    print(f"  Throughput: {fps:.2f} FPS")

    return result


# ==============================================================================
# 7. IN BẢNG SO SÁNH (Idle vs Processing vs Peak)
# ==============================================================================

def print_comparison_table(idle_stats: dict, proc_stats: dict, install_size: dict):
    """In bảng so sánh tài nguyên giữa 3 trạng thái: Idle, Processing, Peak."""

    print("\n")
    print("╔" + "═" * 80 + "╗")
    print("║" + "  KẾT QUẢ GIÁM SÁT TÀI NGUYÊN – AUEDU AI ENGINE  ".center(80) + "║")
    print("╠" + "═" * 80 + "╣")

    # ── Header ──
    header = f"  {'Chỉ số (Metric)':<30} {'Idle':>12} {'Processing':>12} {'Peak':>12}"
    print("║" + header.ljust(80) + "║")
    print("║" + "  " + "─" * 76 + "  ║")

    # ── Các hàng dữ liệu ──
    rows = [
        ("CPU – Process (%)",
         f"{idle_stats['cpu_avg']:.1f}",
         f"{proc_stats['cpu_avg']:.1f}",
         f"{proc_stats['cpu_peak']:.1f}"),

        ("CPU – System (%)",
         f"{idle_stats['system_cpu_avg']:.1f}",
         f"{proc_stats['system_cpu_avg']:.1f}",
         f"{proc_stats['system_cpu_peak']:.1f}"),

        ("RAM (MB)",
         f"{idle_stats['ram_avg_mb']:.1f}",
         f"{proc_stats['ram_avg_mb']:.1f}",
         f"{proc_stats['ram_peak_mb']:.1f}"),
    ]

    # GPU rows (chỉ hiện nếu có)
    if _PYNVML_AVAILABLE:
        rows.extend([
            ("GPU Utilization (%)",
             f"{idle_stats['gpu_avg']:.1f}",
             f"{proc_stats['gpu_avg']:.1f}",
             f"{proc_stats['gpu_peak']:.1f}"),

            ("VRAM Used (MB)",
             f"{idle_stats['vram_avg_mb']:.1f}",
             f"{proc_stats['vram_avg_mb']:.1f}",
             f"{proc_stats['vram_peak_mb']:.1f}"),

            ("VRAM Total (MB)",
             f"{proc_stats['vram_total_mb']:.1f}",
             f"{proc_stats['vram_total_mb']:.1f}",
             f"{proc_stats['vram_total_mb']:.1f}"),
        ])

    for label, idle_val, proc_val, peak_val in rows:
        row = f"  {label:<30} {idle_val:>12} {proc_val:>12} {peak_val:>12}"
        print("║" + row.ljust(80) + "║")

    print("╠" + "═" * 80 + "╣")

    # ── Throughput ──
    print("║" + f"  ⚡ Throughput: {proc_stats.get('fps', 0):.2f} FPS ({proc_stats.get('frames_processed', 0)} frames / {proc_stats.get('duration_sec', 0)}s)".ljust(80) + "║")

    print("╠" + "═" * 80 + "╣")

    # ── Kích thước cài đặt ──
    print("║" + "  📦 Kích thước cài đặt ứng dụng (không bao gồm venv/build):".ljust(80) + "║")
    print("║" + f"     Server: {install_size['server']['total_mb']:>8.2f} MB ({install_size['server']['file_count']} files)".ljust(80) + "║")
    print("║" + f"     Client: {install_size['client']['total_mb']:>8.2f} MB ({install_size['client']['file_count']} files)".ljust(80) + "║")
    print("║" + f"     Tổng:   {install_size['total_mb']:>8.2f} MB".ljust(80) + "║")

    print("╠" + "═" * 80 + "╣")

    # ── Ghi chú ──
    if _PYNVML_AVAILABLE:
        gpu_note = f"GPU: {_GPU_NAME}"
    else:
        gpu_note = "GPU: không khả dụng (pynvml chưa cài hoặc không có NVIDIA GPU)"
    notes = [
        "  Ghi chú:",
        f"  • {gpu_note}",
        "  • CPU Process = CPU riêng tiến trình Python (có thể > 100% = multi-core)",
        "  • CPU System = CPU toàn hệ thống (tất cả tiến trình)",
        "  • RAM = RSS (Resident Set Size) của tiến trình Python",
        "  • Peak = giá trị cao nhất ghi nhận trong suốt quá trình xử lý",
        "  • Sampling interval: 0.5 giây",
    ]
    for note in notes:
        print("║" + note.ljust(80) + "║")

    print("╚" + "═" * 80 + "╝")


# ==============================================================================
# 8. LƯU KẾT QUẢ RA FILE JSON
# ==============================================================================

def save_report(output_path: str, idle_stats: dict, proc_stats: dict,
                install_size: dict, args_dict: dict):
    """Lưu toàn bộ kết quả giám sát vào file JSON cho luận văn."""

    report = {
        "test_name": "AuEdu AI Engine Resource Monitor",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configuration": args_dict,
        "system_info": {
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "total_ram_mb": round(psutil.virtual_memory().total / (1024 ** 2), 1),
            "gpu_name": _GPU_NAME if _PYNVML_AVAILABLE else "N/A",
            "gpu_available": _PYNVML_AVAILABLE,
        },
        "idle": idle_stats,
        "processing": proc_stats,
        "peak": {
            "cpu_peak": proc_stats.get("cpu_peak", 0),
            "system_cpu_peak": proc_stats.get("system_cpu_peak", 0),
            "ram_peak_mb": proc_stats.get("ram_peak_mb", 0),
            "gpu_peak": proc_stats.get("gpu_peak", 0),
            "vram_peak_mb": proc_stats.get("vram_peak_mb", 0),
        },
        "install_size": install_size,
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVE] Kết quả đã lưu vào: {output_file.resolve()}")


# ==============================================================================
# 9. ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AuEdu AI Engine Resource Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python tests/test_resource_monitor.py
  python tests/test_resource_monitor.py --duration 60 --image photos/face.jpg
  python tests/test_resource_monitor.py --output tests/results/resource_custom.json
        """,
    )
    parser.add_argument(
        "--duration", type=float, default=30.0,
        help="Thời gian đo tài nguyên khi processing (giây, mặc định: 30)"
    )
    parser.add_argument(
        "--image", type=str, default=None,
        help="Đường dẫn ảnh khuôn mặt thật. Không có sẽ dùng ảnh giả lập."
    )
    parser.add_argument(
        "--output", type=str, default="tests/results/resource_report.json",
        help="Đường dẫn file JSON lưu kết quả (mặc định: tests/results/resource_report.json)"
    )
    parser.add_argument(
        "--idle-duration", type=float, default=5.0,
        help="Thời gian đo idle (giây, mặc định: 5)"
    )
    args = parser.parse_args()

    # ── Kiểm tra thư viện ──
    check_dependencies()

    print("\n╔" + "═" * 70 + "╗")
    print("║" + "  AUEDU – AI ENGINE RESOURCE MONITOR  ".center(70) + "║")
    print("║" + f"  Processing: {args.duration:.0f}s | Idle: {args.idle_duration:.0f}s  ".center(70) + "║")
    print("╚" + "═" * 70 + "╝")

    # ── Chuẩn bị ảnh test ──
    image_path = args.image
    if image_path and not os.path.isabs(image_path):
        image_path = str(_PROJECT_ROOT / image_path)

    img_bgr = load_or_generate_image(image_path)
    b64_image = image_to_base64(img_bgr)
    print(f"[INFO] Kích thước Base64: {len(b64_image):,} characters ({len(b64_image) / 1024:.1f} KB)")

    # ── Load AI Engine ──
    print("\n[INFO] Đang khởi tạo AI Engine (có thể mất vài giây)...")
    from app.ai.engine import face_engine
    print("[INFO] AI Engine đã sẵn sàng.")

    # ── Tạo sampler ──
    sampler = ResourceSampler(sample_interval=0.5)

    # ── Phase 1: Idle ──
    idle_stats = measure_idle(sampler, idle_duration=args.idle_duration)

    # ── Phase 2: Processing ──
    proc_stats = measure_processing(
        sampler, face_engine, b64_image, duration=args.duration
    )

    # ── Đo kích thước cài đặt ──
    install_size = measure_install_size()

    # ── In bảng so sánh ──
    print_comparison_table(idle_stats, proc_stats, install_size)

    # ── Lưu kết quả ──
    args_dict = {
        "image": args.image or "(synthetic)",
        "processing_duration_sec": args.duration,
        "idle_duration_sec": args.idle_duration,
        "image_size": f"{img_bgr.shape[1]}x{img_bgr.shape[0]}",
    }

    output_path = args.output
    if not os.path.isabs(output_path):
        output_path = str(_PROJECT_ROOT / output_path)

    save_report(output_path, idle_stats, proc_stats, install_size, args_dict)

    # ── Cleanup GPU ──
    if _PYNVML_AVAILABLE:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    print("\n✅ Resource monitoring hoàn tất!")


if __name__ == "__main__":
    main()
