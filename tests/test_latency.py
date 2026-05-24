"""
tests/test_latency.py
=====================
Đo lường Độ trễ (Latency) của Pipeline AI – AuEdu Face Recognition

Mục đích:
    Benchmark chi tiết thời gian xử lý của từng bước trong pipeline AI:
        1. Giải mã Base64 → BGR frame
        2. Phát hiện khuôn mặt (RetinaFace / InsightFace)
        3. Đánh giá chất lượng ảnh (FIQA – Laplacian Variance)
        4. Kiểm tra Anti-Spoof (MiniFASNet ONNX)
        5. Trích xuất vector đặc trưng (ArcFace Embedding 512-D)
        6. Toàn bộ pipeline (process_attendance_frame)
    Bổ sung: Cold Start (thời gian khởi tạo model) và Throughput (FPS).

Sử dụng:
    python tests/test_latency.py
    python tests/test_latency.py --image path/to/real_face.jpg --iterations 100
    python tests/test_latency.py --output tests/results/my_latency.json

Kết quả được in ra console dạng bảng và lưu vào file JSON.
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
import statistics
from pathlib import Path

# Thêm thư mục Server vào sys.path để import được app.ai.engine
# Cấu trúc: AuEdu-Multi-PlatForm/tests/test_latency.py
#            AuEdu-Multi-PlatForm/Server/app/ai/engine.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SERVER_DIR = _PROJECT_ROOT / "Server"
sys.path.insert(0, str(_SERVER_DIR))

# Đặt working directory về Server để .env và calib.npy được tìm thấy đúng
os.chdir(str(_SERVER_DIR))

import cv2
import numpy as np


# ==============================================================================
# 1. HÀM TẠO ẢNH THỬ NGHIỆM (Synthetic Face-like Image)
# ==============================================================================

def generate_synthetic_face_image(width: int = 640, height: int = 480) -> np.ndarray:
    """
    Tạo ảnh BGR giả lập chứa hình chữ nhật mô phỏng khuôn mặt.
    
    Ảnh này không phải khuôn mặt thật nên RetinaFace có thể KHÔNG phát hiện được.
    Trong trường hợp đó, chỉ đo được thời gian detect (trả về 0 faces).
    Để đo đầy đủ pipeline, nên dùng --image với ảnh khuôn mặt thật.
    """
    # Nền gradient nhẹ (giống phòng học)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        shade = int(180 + 40 * (y / height))
        img[y, :] = (shade, shade, shade)

    # Vẽ hình oval mô phỏng khuôn mặt ở giữa ảnh
    cx, cy = width // 2, height // 2
    # Vẽ hình chữ nhật da (skin-color rectangle)
    cv2.ellipse(img, (cx, cy), (80, 110), 0, 0, 360, (180, 200, 230), -1)
    # Vẽ "mắt"
    cv2.circle(img, (cx - 30, cy - 25), 8, (50, 50, 50), -1)
    cv2.circle(img, (cx + 30, cy - 25), 8, (50, 50, 50), -1)
    # Vẽ "miệng"
    cv2.ellipse(img, (cx, cy + 35), (25, 10), 0, 0, 180, (100, 100, 180), 2)

    return img


def load_or_generate_image(image_path: str = None) -> np.ndarray:
    """
    Tải ảnh từ đường dẫn hoặc tạo ảnh giả lập.
    Trả về ảnh BGR (OpenCV format).
    """
    if image_path and os.path.exists(image_path):
        img = cv2.imread(image_path)
        if img is not None:
            print(f"[INFO] Đã tải ảnh thật: {image_path} ({img.shape[1]}x{img.shape[0]})")
            return img
        else:
            print(f"[WARN] Không đọc được ảnh: {image_path}. Dùng ảnh giả lập.")

    print("[INFO] Sử dụng ảnh giả lập (synthetic face-like image).")
    print("[INFO] → Để đo đầy đủ pipeline, hãy dùng: --image <ảnh_khuôn_mặt_thật>")
    return generate_synthetic_face_image()


def image_to_base64(img_bgr: np.ndarray, quality: int = 85) -> str:
    """Encode ảnh BGR thành chuỗi Base64 JPEG."""
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


# ==============================================================================
# 2. HÀM TÍNH THỐNG KÊ
# ==============================================================================

def compute_stats(times_ms: list) -> dict:
    """
    Tính các chỉ số thống kê từ danh sách thời gian (mili giây).
    Trả về dict: avg, min, max, std, p50, p95, p99
    """
    if not times_ms:
        return {"avg": 0, "min": 0, "max": 0, "std": 0, "p50": 0, "p95": 0, "p99": 0, "count": 0}

    sorted_t = sorted(times_ms)
    n = len(sorted_t)

    return {
        "count": n,
        "avg": round(statistics.mean(sorted_t), 3),
        "min": round(sorted_t[0], 3),
        "max": round(sorted_t[-1], 3),
        "std": round(statistics.stdev(sorted_t), 3) if n > 1 else 0,
        "p50": round(sorted_t[int(n * 0.50)], 3),
        "p95": round(sorted_t[min(int(n * 0.95), n - 1)], 3),
        "p99": round(sorted_t[min(int(n * 0.99), n - 1)], 3),
    }


# ==============================================================================
# 3. ĐO LƯỜNG COLD START (Thời gian khởi tạo model)
# ==============================================================================

def measure_cold_start() -> float:
    """
    Đo thời gian khởi tạo FaceEngine (load tất cả model AI).
    
    Lưu ý: FaceEngine là Singleton, nên ta phải import lại module
    hoặc tạo instance mới bằng cách gọi trực tiếp __init__.
    Cách an toàn nhất: đo thời gian import lần đầu.
    
    Returns:
        Thời gian khởi tạo tính bằng mili giây.
    """
    print("\n" + "=" * 70)
    print("  BƯỚC 1: ĐO COLD START (Thời gian khởi tạo AI Engine)")
    print("=" * 70)

    # Xóa module khỏi cache nếu đã import trước đó
    modules_to_remove = [key for key in sys.modules if key.startswith("app.ai")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    t_start = time.perf_counter()

    # Import lại → trigger FaceEngine.__init__() (Singleton)
    from app.ai.engine import face_engine  # noqa: F811

    t_end = time.perf_counter()
    cold_start_ms = (t_end - t_start) * 1000

    print(f"\n[COLD START] Thời gian khởi tạo FaceEngine: {cold_start_ms:.1f} ms")
    return cold_start_ms


# ==============================================================================
# 4. ĐO LƯỜNG TỪNG BƯỚC PIPELINE (Step-by-step Latency)
# ==============================================================================

def measure_step_latencies(face_engine, b64_image: str, img_bgr: np.ndarray,
                           iterations: int) -> dict:
    """
    Đo thời gian xử lý của từng bước riêng lẻ trong pipeline AI.
    
    Các bước:
        1. base64_decode: Giải mã Base64 → BGR frame
        2. face_detection: Phát hiện khuôn mặt (InsightFace app.get())
        3. fiqa_eval: Đánh giá chất lượng ảnh (Laplacian Variance)
        4. anti_spoof: Kiểm tra liveness (MiniFASNet ONNX)
        5. embedding_extract: Trích xuất vector 512-D (ArcFace)
        6. full_pipeline: Toàn bộ process_attendance_frame()
    
    Args:
        face_engine: Instance FaceEngine đã khởi tạo
        b64_image: Ảnh dạng Base64
        img_bgr: Ảnh BGR (numpy array)
        iterations: Số lần lặp đo
    
    Returns:
        dict chứa danh sách thời gian (ms) của mỗi bước
    """
    print("\n" + "=" * 70)
    print(f"  BƯỚC 2: ĐO LATENCY TỪNG BƯỚC ({iterations} iterations)")
    print("=" * 70)

    # Khởi tạo danh sách lưu kết quả từng bước
    results = {
        "base64_decode": [],
        "face_detection": [],
        "fiqa_eval": [],
        "anti_spoof": [],
        "embedding_extract": [],
        "full_pipeline": [],
    }

    # Warm-up: chạy 3 lần trước để loại bỏ hiệu ứng cache lạnh
    print("[INFO] Warm-up (3 iterations)...")
    for _ in range(3):
        face_engine.process_attendance_frame(b64_image, mode="1")

    # ── Chạy đo chính ──
    faces_detected_count = 0  # Đếm số lần phát hiện được khuôn mặt

    for i in range(iterations):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  Iteration {i + 1}/{iterations}...")

        # ── Bước 1: Giải mã Base64 ──
        t0 = time.perf_counter()
        frame = face_engine._decode_base64_to_bgr(b64_image)
        t1 = time.perf_counter()
        results["base64_decode"].append((t1 - t0) * 1000)

        if frame is None:
            continue

        # ── Bước 2: Phát hiện khuôn mặt (InsightFace) ──
        t0 = time.perf_counter()
        if face_engine.app is not None:
            faces = face_engine.app.get(frame)
        else:
            faces = []
        t1 = time.perf_counter()
        results["face_detection"].append((t1 - t0) * 1000)

        # Nếu phát hiện được khuôn mặt → đo tiếp FIQA, Anti-Spoof, Embedding
        if faces:
            faces_detected_count += 1
            face = faces[0]
            bbox = face.bbox.astype(int)
            x1 = max(0, bbox[0])
            y1 = max(0, bbox[1])
            x2 = min(frame.shape[1], bbox[2])
            y2 = min(frame.shape[0], bbox[3])
            face_crop = frame[y1:y2, x1:x2]

            # ── Bước 3: FIQA (Đánh giá chất lượng ảnh) ──
            t0 = time.perf_counter()
            fiqa_score = face_engine.evaluate_fiqa(face_crop)
            t1 = time.perf_counter()
            results["fiqa_eval"].append((t1 - t0) * 1000)

            # ── Bước 4: Anti-Spoof (Liveness Detection) ──
            t0 = time.perf_counter()
            face_engine._is_live_face(frame, face, fiqa_score)
            t1 = time.perf_counter()
            results["anti_spoof"].append((t1 - t0) * 1000)

            # ── Bước 5: Trích xuất Embedding ──
            t0 = time.perf_counter()
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_engine.extract_embedding(img_rgb)
            t1 = time.perf_counter()
            results["embedding_extract"].append((t1 - t0) * 1000)

        # ── Bước 6: Toàn bộ Pipeline (end-to-end) ──
        t0 = time.perf_counter()
        face_engine.process_attendance_frame(b64_image, mode="1")
        t1 = time.perf_counter()
        results["full_pipeline"].append((t1 - t0) * 1000)

    print(f"\n[INFO] Số lần phát hiện khuôn mặt: {faces_detected_count}/{iterations}")
    if faces_detected_count == 0:
        print("[WARN] Không phát hiện được khuôn mặt nào!")
        print("[WARN] → FIQA, Anti-Spoof, Embedding sẽ không có dữ liệu.")
        print("[WARN] → Hãy dùng --image với ảnh khuôn mặt thật để đo đầy đủ.")

    return results


# ==============================================================================
# 5. ĐO THROUGHPUT (Số frame/giây)
# ==============================================================================

def measure_throughput(face_engine, b64_image: str, duration_sec: float = 10.0) -> dict:
    """
    Đo throughput: số frame AI xử lý được mỗi giây (FPS).
    
    Chạy liên tục process_attendance_frame trong duration_sec giây,
    đếm tổng số frame đã xử lý.
    
    Returns:
        dict: total_frames, duration_sec, fps
    """
    print("\n" + "=" * 70)
    print(f"  BƯỚC 3: ĐO THROUGHPUT (chạy liên tục trong {duration_sec:.0f}s)")
    print("=" * 70)

    frame_count = 0
    t_start = time.perf_counter()
    t_end_target = t_start + duration_sec

    while time.perf_counter() < t_end_target:
        face_engine.process_attendance_frame(b64_image, mode="1")
        frame_count += 1
        # In tiến trình mỗi 50 frame
        if frame_count % 50 == 0:
            elapsed = time.perf_counter() - t_start
            current_fps = frame_count / elapsed
            print(f"  ... {frame_count} frames | {elapsed:.1f}s | {current_fps:.1f} FPS")

    actual_duration = time.perf_counter() - t_start
    fps = frame_count / actual_duration if actual_duration > 0 else 0

    print(f"\n[THROUGHPUT] {frame_count} frames trong {actual_duration:.2f}s → {fps:.2f} FPS")

    return {
        "total_frames": frame_count,
        "duration_sec": round(actual_duration, 3),
        "fps": round(fps, 2),
    }


# ==============================================================================
# 6. IN BẢNG KẾT QUẢ (Formatted Summary Table)
# ==============================================================================

def print_summary_table(step_stats: dict, cold_start_ms: float, throughput: dict):
    """In bảng tổng hợp kết quả đẹp mắt ra console."""

    print("\n")
    print("╔" + "═" * 90 + "╗")
    print("║" + "  KẾT QUẢ ĐO LƯỜNG LATENCY – AUEDU AI PIPELINE  ".center(90) + "║")
    print("╠" + "═" * 90 + "╣")

    # ── Cold Start ──
    print("║" + f"  ❄  Cold Start (Khởi tạo model): {cold_start_ms:>10.1f} ms".ljust(90) + "║")
    print("║" + f"  ⚡ Throughput: {throughput['fps']:>6.2f} FPS ({throughput['total_frames']} frames / {throughput['duration_sec']}s)".ljust(90) + "║")
    print("╠" + "═" * 90 + "╣")

    # ── Header bảng chi tiết ──
    header = f"  {'Bước xử lý':<25} {'Count':>5} {'Avg':>8} {'Min':>8} {'Max':>8} {'P50':>8} {'P95':>8} {'P99':>8}"
    unit_row = f"  {'':25} {'':>5} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8} {'(ms)':>8}"
    print("║" + header.ljust(90) + "║")
    print("║" + unit_row.ljust(90) + "║")
    print("║" + "  " + "─" * 86 + "  " + "║")

    # ── Tên hiển thị cho từng bước ──
    step_display_names = {
        "base64_decode": "1. Base64 Decode",
        "face_detection": "2. Face Detection",
        "fiqa_eval": "3. FIQA Evaluation",
        "anti_spoof": "4. Anti-Spoof Check",
        "embedding_extract": "5. Embedding Extract",
        "full_pipeline": "6. Full Pipeline (E2E)",
    }

    for step_key, display_name in step_display_names.items():
        st = step_stats.get(step_key, {})
        count = st.get("count", 0)
        if count == 0:
            row = f"  {display_name:<25} {'N/A':>5} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'—':>8}"
        else:
            row = (
                f"  {display_name:<25} "
                f"{count:>5} "
                f"{st['avg']:>8.2f} "
                f"{st['min']:>8.2f} "
                f"{st['max']:>8.2f} "
                f"{st['p50']:>8.2f} "
                f"{st['p95']:>8.2f} "
                f"{st['p99']:>8.2f}"
            )
        print("║" + row.ljust(90) + "║")

    print("╠" + "═" * 90 + "╣")

    # ── Ghi chú ──
    notes = [
        "  Ghi chú:",
        "  • Cold Start = thời gian load InsightFace + Anti-Spoof + Calibrator",
        "  • Full Pipeline = decode + undistort + detect + fiqa + spoof + embed",
        "  • P95/P99 = percentile 95/99 (giá trị tệ nhất thường gặp)",
        "  • Warm-up 3 iterations đã được loại bỏ khỏi kết quả",
    ]
    for note in notes:
        print("║" + note.ljust(90) + "║")
    print("╚" + "═" * 90 + "╝")


# ==============================================================================
# 7. LƯU KẾT QUẢ RA FILE JSON
# ==============================================================================

def save_report(output_path: str, step_stats: dict, cold_start_ms: float,
                throughput: dict, args_dict: dict):
    """Lưu toàn bộ kết quả đo lường vào file JSON cho luận văn."""

    report = {
        "test_name": "AuEdu AI Pipeline Latency Benchmark",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configuration": args_dict,
        "cold_start_ms": round(cold_start_ms, 1),
        "throughput": throughput,
        "step_latencies": step_stats,
    }

    # Tạo thư mục nếu chưa có
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVE] Kết quả đã lưu vào: {output_file.resolve()}")


# ==============================================================================
# 8. ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="AuEdu AI Pipeline Latency Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python tests/test_latency.py
  python tests/test_latency.py --image photos/test_face.jpg --iterations 100
  python tests/test_latency.py --output tests/results/latency_custom.json
        """,
    )
    parser.add_argument(
        "--image", type=str, default=None,
        help="Đường dẫn đến ảnh khuôn mặt thật (khuyến nghị). Nếu không có sẽ dùng ảnh giả lập."
    )
    parser.add_argument(
        "--iterations", type=int, default=50,
        help="Số lần lặp đo latency (mặc định: 50)"
    )
    parser.add_argument(
        "--output", type=str, default="tests/results/latency_report.json",
        help="Đường dẫn file JSON lưu kết quả (mặc định: tests/results/latency_report.json)"
    )
    parser.add_argument(
        "--throughput-duration", type=float, default=10.0,
        help="Thời gian chạy đo throughput (giây, mặc định: 10)"
    )
    args = parser.parse_args()

    print("╔" + "═" * 70 + "╗")
    print("║" + "  AUEDU – AI PIPELINE LATENCY BENCHMARK  ".center(70) + "║")
    print("║" + f"  Iterations: {args.iterations} | Throughput Duration: {args.throughput_duration}s  ".center(70) + "║")
    print("╚" + "═" * 70 + "╝")

    # ── Bước 0: Chuẩn bị ảnh test ──
    # Nếu --image là relative path, resolve từ project root
    image_path = args.image
    if image_path and not os.path.isabs(image_path):
        image_path = str(_PROJECT_ROOT / image_path)

    img_bgr = load_or_generate_image(image_path)
    b64_image = image_to_base64(img_bgr)
    print(f"[INFO] Kích thước Base64: {len(b64_image):,} characters ({len(b64_image) / 1024:.1f} KB)")

    # ── Bước 1: Cold Start ──
    cold_start_ms = measure_cold_start()

    # Import engine sau cold start (đã được load)
    from app.ai.engine import face_engine

    # ── Bước 2: Step-by-step Latency ──
    raw_results = measure_step_latencies(face_engine, b64_image, img_bgr, args.iterations)

    # Tính thống kê cho mỗi bước
    step_stats = {}
    for step_name, times in raw_results.items():
        step_stats[step_name] = compute_stats(times)

    # ── Bước 3: Throughput ──
    throughput = measure_throughput(face_engine, b64_image, args.throughput_duration)

    # ── Bước 4: In bảng tổng hợp ──
    print_summary_table(step_stats, cold_start_ms, throughput)

    # ── Bước 5: Lưu kết quả ──
    args_dict = {
        "image": args.image or "(synthetic)",
        "iterations": args.iterations,
        "throughput_duration_sec": args.throughput_duration,
        "image_size": f"{img_bgr.shape[1]}x{img_bgr.shape[0]}",
        "base64_size_kb": round(len(b64_image) / 1024, 1),
    }

    # Output path: resolve relative to project root
    output_path = args.output
    if not os.path.isabs(output_path):
        output_path = str(_PROJECT_ROOT / output_path)

    save_report(output_path, step_stats, cold_start_ms, throughput, args_dict)

    print("\n✅ Benchmark hoàn tất!")


if __name__ == "__main__":
    main()
