"""
tests/test_accuracy.py
======================
Kiểm thử Độ chính xác Hệ thống Nhận diện Khuôn mặt AuEdu

Script này đánh giá toàn diện các module AI của hệ thống AuEdu:
    1. Tỉ lệ Phát hiện Khuôn mặt (Face Detection Rate)
    2. Trích xuất Vector Đặc trưng 512-D (Embedding Extraction)
    3. Độ chính xác Nhận diện (Recognition Accuracy) với Confusion Matrix
    4. Phân tích Ngưỡng (Threshold Analysis) – FAR, FRR tại nhiều ngưỡng
    5. Đánh giá Chất lượng Ảnh (FIQA Evaluation)
    6. Đánh giá Chống Giả mạo (Anti-Spoofing Evaluation)

Cấu trúc thư mục dataset yêu cầu:
    tests/dataset/
      registered/           # Ảnh đã đăng ký (known faces)
        student_001/
          img_01.jpg
          img_02.jpg
        student_002/
          ...
      unknown/              # Ảnh người lạ (unknown faces)
        stranger_01.jpg
        stranger_02.jpg
      blurred/              # Ảnh mờ để test FIQA
        blur_01.jpg
      spoofing/             # Ảnh giả mạo
        print_attack/
          print_01.jpg
        screen_attack/
          screen_01.jpg

Sử dụng:
    cd Server
    python ../tests/test_accuracy.py
    python ../tests/test_accuracy.py --dataset ../tests/dataset --threshold 0.45
    python ../tests/test_accuracy.py --output ../tests/results

Tác giả: Chanh-Hiep NGUYEN
"""

# ==============================================================================
# THIẾT LẬP MÔI TRƯỜNG (Environment Setup)
# ==============================================================================
# Thêm thư mục Server/ vào sys.path để import được app.ai.engine
# Script được thiết kế để chạy từ thư mục Server/:  cd Server && python ../tests/test_accuracy.py

import sys
import os
from pathlib import Path

# Xác định thư mục gốc của project và thư mục Server
# __file__ = tests/test_accuracy.py → parent = tests/ → parent.parent = project root
SCRIPT_DIR = Path(__file__).resolve().parent        # .../tests/
PROJECT_ROOT = SCRIPT_DIR.parent                     # .../AuEdu-Multi-PlatForm/
SERVER_DIR = PROJECT_ROOT / "Server"                 # .../AuEdu-Multi-PlatForm/Server/

# Thêm Server/ vào sys.path để `from app.ai.engine import face_engine` hoạt động
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# Chuyển working directory sang Server/ (cần cho các đường dẫn tương đối của model)
os.chdir(SERVER_DIR)

import cv2
import json
import csv
import time
import base64
import argparse
import traceback
import numpy as np
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


# ==============================================================================
# HẰNG SỐ VÀ CẤU HÌNH MẶC ĐỊNH
# ==============================================================================

# Các định dạng ảnh được hỗ trợ
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Các ngưỡng cosine distance để phân tích (Threshold Analysis)
ANALYSIS_THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

# Các ngưỡng FIQA để phân tích tỉ lệ lọc
FIQA_THRESHOLDS = [0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]

# Separator dùng cho bảng console
SEP = "=" * 78
THIN_SEP = "-" * 78


# ==============================================================================
# HÀM TIỆN ÍCH (Utility Functions)
# ==============================================================================

def is_image_file(filepath: Path) -> bool:
    """Kiểm tra xem file có phải ảnh hợp lệ không (dựa trên extension)."""
    return filepath.suffix.lower() in SUPPORTED_EXTENSIONS


def load_image_bgr(filepath: Path) -> Optional[np.ndarray]:
    """
    Đọc ảnh từ file và trả về dạng BGR (OpenCV format).
    Trả về None nếu không đọc được.
    """
    try:
        # Đọc ảnh hỗ trợ cả đường dẫn Unicode (tiếng Việt)
        img = cv2.imdecode(
            np.fromfile(str(filepath), dtype=np.uint8),
            cv2.IMREAD_COLOR
        )
        return img
    except Exception as e:
        print(f"  [WARN] Không đọc được ảnh: {filepath.name} – {e}")
        return None


def bgr_to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    """Chuyển ảnh từ BGR sang RGB."""
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def image_to_base64(img_bgr: np.ndarray) -> str:
    """Encode ảnh BGR sang Base64 string (JPEG format)."""
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def cosine_distance(emb_a: List[float], emb_b: List[float]) -> float:
    """
    Tính khoảng cách cosine giữa 2 embedding vectors.
    cosine_distance = 1 - cosine_similarity
    Giá trị càng nhỏ → 2 khuôn mặt càng giống nhau.
    """
    a = np.array(emb_a, dtype=np.float32)
    b = np.array(emb_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0  # Trường hợp đặc biệt: vector rỗng
    similarity = np.dot(a, b) / (norm_a * norm_b)
    return float(1.0 - similarity)


def print_table(headers: List[str], rows: List[List], col_widths: Optional[List[int]] = None):
    """
    In bảng đơn giản ra console (không cần thư viện ngoài).
    headers: Danh sách tiêu đề cột
    rows: Danh sách các hàng dữ liệu
    col_widths: Độ rộng tùy chỉnh cho từng cột (tự tính nếu None)
    """
    if col_widths is None:
        # Tự tính độ rộng dựa trên nội dung
        col_widths = []
        for i, h in enumerate(headers):
            max_w = len(str(h))
            for row in rows:
                if i < len(row):
                    max_w = max(max_w, len(str(row[i])))
            col_widths.append(max_w + 2)

    # In header
    header_line = "│".join(str(h).center(w) for h, w in zip(headers, col_widths))
    separator = "┼".join("─" * w for w in col_widths)
    print(f"│{header_line}│")
    print(f"│{separator}│")

    # In dữ liệu
    for row in rows:
        row_line = "│".join(str(v).center(w) for v, w in zip(row, col_widths))
        print(f"│{row_line}│")


def ensure_dir(path: Path):
    """Tạo thư mục nếu chưa tồn tại."""
    path.mkdir(parents=True, exist_ok=True)


def print_dataset_instructions():
    """
    In hướng dẫn chi tiết cách chuẩn bị dataset khi thư mục không tồn tại.
    Dùng tiếng Việt cho luận văn.
    """
    print(f"\n{SEP}")
    print("  HƯỚNG DẪN CHUẨN BỊ DATASET ĐỂ KIỂM THỬ")
    print(SEP)
    print("""
  Dataset không được tìm thấy. Vui lòng chuẩn bị theo cấu trúc sau:

  tests/dataset/
  ├── registered/              ← Ảnh khuôn mặt đã biết (known faces)
  │   ├── student_001/         ← Mỗi thư mục = 1 người (tên thư mục = ID)
  │   │   ├── img_01.jpg       ← Ảnh đầu tiên → dùng để ĐĂNG KÝ (enrolled)
  │   │   ├── img_02.jpg       ← Ảnh còn lại → dùng để KIỂM TRA (probe)
  │   │   └── img_03.jpg
  │   ├── student_002/
  │   │   ├── img_01.jpg
  │   │   └── img_02.jpg
  │   └── ...                  ← Tối thiểu 3-5 người, mỗi người 3-5 ảnh
  │
  ├── unknown/                 ← Ảnh người lạ (KHÔNG có trong registered/)
  │   ├── stranger_01.jpg      ← Mỗi file = 1 người lạ khác nhau
  │   ├── stranger_02.jpg
  │   └── ...                  ← Tối thiểu 5-10 ảnh
  │
  ├── blurred/                 ← Ảnh mờ để kiểm tra FIQA filtering
  │   ├── blur_01.jpg          ← Ảnh chụp mất nét / motion blur
  │   ├── blur_02.jpg
  │   └── ...
  │
  └── spoofing/                ← Ảnh giả mạo (spoof attacks)
      ├── print_attack/        ← In ảnh khuôn mặt ra giấy rồi chụp lại
      │   ├── print_01.jpg
      │   └── ...
      └── screen_attack/       ← Hiển thị ảnh trên màn hình rồi chụp lại
          ├── screen_01.jpg
          └── ...

  HƯỚNG DẪN CHỤP ẢNH:
  ────────────────────
  1. registered/: Chụp mỗi người ở nhiều góc độ, ánh sáng khác nhau.
     - Ảnh đầu tiên (img_01.jpg): Chụp rõ ràng, chính diện → dùng để đăng ký
     - Ảnh còn lại: Chụp nghiêng nhẹ, ánh sáng khác, biểu cảm khác → dùng để test
     - Kích thước tối thiểu: 640x480, khuôn mặt chiếm ít nhất 20% khung hình

  2. unknown/: Dùng ảnh người KHÔNG có trong registered/.
     - Có thể dùng ảnh từ internet (đảm bảo chất lượng)
     - Khuôn mặt phải rõ ràng, đủ lớn

  3. blurred/: Cố tình chụp mờ hoặc dùng phần mềm blur.
     - Motion blur: Rung tay khi chụp
     - Out-of-focus: Chụp mất nét
     - Gaussian blur: Dùng phần mềm blur ảnh

  4. spoofing/:
     - print_attack/: In ảnh khuôn mặt ra giấy A4, đặt trước camera chụp lại
     - screen_attack/: Hiển thị ảnh khuôn mặt trên điện thoại/laptop, rồi dùng
       camera khác chụp lại

  LƯU Ý QUAN TRỌNG:
  ──────────────────
  • Dùng định dạng: .jpg, .jpeg, .png, .bmp, .webp
  • Tên file/thư mục KHÔNG nên có dấu tiếng Việt
  • Mỗi thư mục student_xxx cần TỐI THIỂU 2 ảnh (1 enrolled + 1 probe)
  • Nên có 5-10 sinh viên, mỗi sinh viên 3-5 ảnh cho kết quả đáng tin cậy
""")
    print(SEP)


# ==============================================================================
# LỚP KIỂM THỬ CHÍNH (Main Test Class)
# ==============================================================================

class AccuracyTester:
    """
    Lớp quản lý toàn bộ quá trình kiểm thử độ chính xác.
    Tổ chức kết quả và xuất report.
    """

    def __init__(self, dataset_dir: str, default_threshold: float, output_dir: str):
        """
        Khởi tạo AccuracyTester.

        Args:
            dataset_dir: Đường dẫn đến thư mục dataset chứa ảnh test
            default_threshold: Ngưỡng cosine distance mặc định (thường 0.45)
            output_dir: Thư mục lưu kết quả (JSON, CSV)
        """
        self.dataset_dir = Path(dataset_dir).resolve()
        self.default_threshold = default_threshold
        self.output_dir = Path(output_dir).resolve()

        # Các đường dẫn con của dataset
        self.registered_dir = self.dataset_dir / "registered"
        self.unknown_dir = self.dataset_dir / "unknown"
        self.blurred_dir = self.dataset_dir / "blurred"
        self.spoofing_dir = self.dataset_dir / "spoofing"

        # Kết quả tổng hợp – sẽ được ghi vào file JSON cuối cùng
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "dataset_dir": str(self.dataset_dir),
                "default_threshold": self.default_threshold,
                "script_version": "1.0.0",
            },
            "detection": {},
            "embedding": {},
            "recognition": {},
            "threshold_analysis": {},
            "fiqa": {},
            "anti_spoofing": {},
        }

        # Lưu trữ embedding đã trích xuất (dùng lại giữa các test)
        # Format: { "student_001": { "enrolled": [...], "probes": [[...], [...]] } }
        self.embeddings_cache: Dict[str, dict] = {}

        # Lưu trữ embedding của unknown faces
        self.unknown_embeddings: List[List[float]] = []

        # Engine AI – sẽ được khởi tạo khi chạy test
        self.engine = None

    # --------------------------------------------------------------------------
    # KHỞI TẠO AI ENGINE
    # --------------------------------------------------------------------------

    def _init_engine(self):
        """
        Import và khởi tạo FaceEngine singleton.
        Bước này tải model InsightFace + Anti-Spoof vào bộ nhớ.
        """
        print(f"\n{SEP}")
        print("  BƯỚC 0: KHỞI TẠO AI ENGINE")
        print(SEP)

        try:
            from app.ai.engine import face_engine
            self.engine = face_engine
            print("  ✓ AI Engine (face_engine) đã sẵn sàng.")
            print(f"  • InsightFace: {'Có' if self.engine.app else 'Không (OpenCV fallback)'}")
            print(f"  • Anti-Spoof:  {'Có' if self.engine.anti_spoof_session else 'Không'}")
            print(f"  • Calibrator:  {'Có' if self.engine._calibration_enabled else 'Không'}")
        except Exception as e:
            print(f"\n  ✗ KHÔNG THỂ KHỞI TẠO AI ENGINE!")
            print(f"    Lỗi: {e}")
            print(f"\n    Hãy chắc chắn:")
            print(f"    1. Đang chạy từ thư mục Server/")
            print(f"    2. Đã cài đặt đủ dependencies (pip install -r requirements.txt)")
            print(f"    3. Đã tải model InsightFace (buffalo_s)")
            traceback.print_exc()
            sys.exit(1)

    # --------------------------------------------------------------------------
    # KIỂM TRA DATASET
    # --------------------------------------------------------------------------

    def _validate_dataset(self) -> bool:
        """
        Kiểm tra cấu trúc thư mục dataset.
        In hướng dẫn nếu dataset chưa tồn tại.
        Trả về True nếu dataset hợp lệ để chạy test.
        """
        print(f"\n{SEP}")
        print("  KIỂM TRA DATASET")
        print(SEP)
        print(f"  Đường dẫn: {self.dataset_dir}")

        if not self.dataset_dir.exists():
            print(f"  ✗ Thư mục dataset KHÔNG tồn tại!")
            print_dataset_instructions()
            return False

        # Kiểm tra từng thư mục con
        status = {}
        dirs_to_check = {
            "registered": self.registered_dir,
            "unknown": self.unknown_dir,
            "blurred": self.blurred_dir,
            "spoofing": self.spoofing_dir,
        }

        all_ok = True
        for name, path in dirs_to_check.items():
            if path.exists():
                # Đếm số ảnh
                if name == "registered":
                    # Đếm số thư mục con (mỗi thư mục = 1 người)
                    subdirs = [d for d in path.iterdir() if d.is_dir()]
                    total_imgs = sum(
                        1 for d in subdirs
                        for f in d.iterdir() if is_image_file(f)
                    )
                    status[name] = f"✓ {len(subdirs)} người, {total_imgs} ảnh"
                elif name == "spoofing":
                    # Đếm trong print_attack/ và screen_attack/
                    print_dir = path / "print_attack"
                    screen_dir = path / "screen_attack"
                    n_print = sum(1 for f in print_dir.iterdir() if is_image_file(f)) if print_dir.exists() else 0
                    n_screen = sum(1 for f in screen_dir.iterdir() if is_image_file(f)) if screen_dir.exists() else 0
                    status[name] = f"✓ print={n_print}, screen={n_screen}"
                else:
                    n_imgs = sum(1 for f in path.iterdir() if is_image_file(f))
                    status[name] = f"✓ {n_imgs} ảnh"
            else:
                status[name] = "✗ KHÔNG tồn tại"
                if name == "registered":
                    all_ok = False  # registered/ là bắt buộc

        for name, st in status.items():
            required = " (BẮT BUỘC)" if name == "registered" else " (tùy chọn)"
            print(f"  • {name}/{required}: {st}")

        if not all_ok:
            print(f"\n  ✗ Thiếu thư mục bắt buộc! Không thể chạy test.")
            print_dataset_instructions()

        return all_ok

    # --------------------------------------------------------------------------
    # TEST 1: TỈ LỆ PHÁT HIỆN KHUÔN MẶT (Face Detection Rate)
    # --------------------------------------------------------------------------

    def test_detection_rate(self):
        """
        Kiểm tra tỉ lệ phát hiện khuôn mặt trên tất cả ảnh trong registered/.
        Với mỗi ảnh, kiểm tra InsightFace có phát hiện được khuôn mặt hay không.
        """
        print(f"\n{SEP}")
        print("  TEST 1: TỈ LỆ PHÁT HIỆN KHUÔN MẶT (Face Detection Rate)")
        print(SEP)

        if not self.registered_dir.exists():
            print("  ✗ Bỏ qua – registered/ không tồn tại.")
            return

        total_images = 0     # Tổng số ảnh
        detected = 0         # Số ảnh phát hiện được khuôn mặt
        failed_files = []    # Danh sách ảnh không phát hiện được

        # Duyệt từng thư mục sinh viên
        for student_dir in sorted(self.registered_dir.iterdir()):
            if not student_dir.is_dir():
                continue

            student_id = student_dir.name

            for img_file in sorted(student_dir.iterdir()):
                if not is_image_file(img_file):
                    continue

                total_images += 1
                img_bgr = load_image_bgr(img_file)

                if img_bgr is None:
                    failed_files.append(f"{student_id}/{img_file.name} (đọc file lỗi)")
                    continue

                # Dùng InsightFace để phát hiện khuôn mặt
                faces = self.engine._get_faces_sorted_by_area(img_bgr)

                if faces:
                    detected += 1
                    print(f"  ✓ {student_id}/{img_file.name} → {len(faces)} khuôn mặt")
                else:
                    failed_files.append(f"{student_id}/{img_file.name}")
                    print(f"  ✗ {student_id}/{img_file.name} → KHÔNG phát hiện")

        # Tính tỉ lệ
        rate = (detected / total_images * 100) if total_images > 0 else 0

        print(f"\n  {THIN_SEP}")
        print(f"  KẾT QUẢ DETECTION:")
        print(f"  • Tổng ảnh:              {total_images}")
        print(f"  • Phát hiện thành công:   {detected}")
        print(f"  • Thất bại:              {total_images - detected}")
        print(f"  • Tỉ lệ phát hiện:       {rate:.1f}%")

        if failed_files:
            print(f"\n  Các ảnh thất bại:")
            for f in failed_files:
                print(f"    - {f}")

        # Lưu kết quả
        self.results["detection"] = {
            "total_images": total_images,
            "detected": detected,
            "failed": total_images - detected,
            "detection_rate": round(rate, 2),
            "failed_files": failed_files,
        }

    # --------------------------------------------------------------------------
    # TEST 2: TRÍCH XUẤT EMBEDDING 512-D
    # --------------------------------------------------------------------------

    def test_embedding_extraction(self):
        """
        Kiểm tra trích xuất embedding vector cho mỗi ảnh đã phát hiện khuôn mặt.
        Đồng thời xây dựng cache embedding để dùng cho test nhận diện.
        """
        print(f"\n{SEP}")
        print("  TEST 2: TRÍCH XUẤT VECTOR ĐẶC TRƯNG 512-D (Embedding)")
        print(SEP)

        if not self.registered_dir.exists():
            print("  ✗ Bỏ qua – registered/ không tồn tại.")
            return

        total_images = 0       # Tổng số ảnh
        extracted = 0          # Số ảnh trích xuất thành công
        dim_errors = 0         # Số embedding sai chiều (phải là 512)
        extraction_times = []  # Thời gian trích xuất từng ảnh (ms)

        # Xoá cache cũ
        self.embeddings_cache.clear()

        for student_dir in sorted(self.registered_dir.iterdir()):
            if not student_dir.is_dir():
                continue

            student_id = student_dir.name
            self.embeddings_cache[student_id] = {"enrolled": None, "probes": []}

            # Lấy danh sách ảnh, sắp xếp để ảnh đầu tiên luôn là enrolled
            img_files = sorted(
                [f for f in student_dir.iterdir() if is_image_file(f)]
            )

            for i, img_file in enumerate(img_files):
                total_images += 1
                img_bgr = load_image_bgr(img_file)
                if img_bgr is None:
                    continue

                # Chuyển sang RGB vì extract_embedding() nhận RGB
                img_rgb = bgr_to_rgb(img_bgr)

                # Đo thời gian trích xuất
                t_start = time.perf_counter()
                embedding = self.engine.extract_embedding(img_rgb)
                t_elapsed = (time.perf_counter() - t_start) * 1000  # → ms

                if embedding is not None:
                    # Kiểm tra chiều của embedding
                    if len(embedding) == 512:
                        extracted += 1
                        extraction_times.append(t_elapsed)

                        # Ảnh đầu tiên → enrolled, còn lại → probe
                        if i == 0:
                            self.embeddings_cache[student_id]["enrolled"] = embedding
                            role = "ENROLLED"
                        else:
                            self.embeddings_cache[student_id]["probes"].append(embedding)
                            role = "PROBE"

                        print(f"  ✓ {student_id}/{img_file.name} → 512-D ({role}) [{t_elapsed:.1f}ms]")
                    else:
                        dim_errors += 1
                        print(f"  ⚠ {student_id}/{img_file.name} → {len(embedding)}-D (SAI CHIỀU!)")
                else:
                    print(f"  ✗ {student_id}/{img_file.name} → Không trích xuất được")

        # Trích xuất embedding cho unknown faces (nếu có)
        self.unknown_embeddings.clear()
        if self.unknown_dir.exists():
            print(f"\n  Đang xử lý unknown faces...")
            for img_file in sorted(self.unknown_dir.iterdir()):
                if not is_image_file(img_file):
                    continue

                img_bgr = load_image_bgr(img_file)
                if img_bgr is None:
                    continue

                img_rgb = bgr_to_rgb(img_bgr)
                embedding = self.engine.extract_embedding(img_rgb)

                if embedding and len(embedding) == 512:
                    self.unknown_embeddings.append(embedding)
                    print(f"  ✓ unknown/{img_file.name} → 512-D")
                else:
                    print(f"  ✗ unknown/{img_file.name} → Không trích xuất được")

        # Thống kê
        avg_time = np.mean(extraction_times) if extraction_times else 0
        std_time = np.std(extraction_times) if extraction_times else 0

        print(f"\n  {THIN_SEP}")
        print(f"  KẾT QUẢ EMBEDDING EXTRACTION:")
        print(f"  • Tổng ảnh registered:    {total_images}")
        print(f"  • Trích xuất thành công:  {extracted}")
        print(f"  • Sai chiều (≠512-D):     {dim_errors}")
        print(f"  • Thất bại:               {total_images - extracted - dim_errors}")
        print(f"  • Unknown faces:          {len(self.unknown_embeddings)}")
        print(f"  • Thời gian TB:           {avg_time:.1f} ± {std_time:.1f} ms")

        self.results["embedding"] = {
            "total_images": total_images,
            "extracted": extracted,
            "dimension_errors": dim_errors,
            "failed": total_images - extracted - dim_errors,
            "unknown_faces": len(self.unknown_embeddings),
            "avg_extraction_time_ms": round(avg_time, 2),
            "std_extraction_time_ms": round(std_time, 2),
        }

    # --------------------------------------------------------------------------
    # TEST 3: ĐỘ CHÍNH XÁC NHẬN DIỆN (Recognition Accuracy + Confusion Matrix)
    # --------------------------------------------------------------------------

    def test_recognition_accuracy(self):
        """
        Đánh giá độ chính xác nhận diện bằng cách:
        1. Lấy enrolled embedding của mỗi sinh viên
        2. So sánh probe embedding với TẤT CẢ enrolled embeddings
        3. Xây dựng Confusion Matrix: TP, TN, FP, FN
        4. Tính: Accuracy, FAR (False Accept Rate), FRR (False Reject Rate),
           Precision, Recall, F1-Score

        Quy tắc:
        - Genuine pair: probe và enrolled thuộc CÙNG 1 người
        - Impostor pair: probe và enrolled thuộc KHÁC người hoặc unknown
        - So sánh: cosine_distance < threshold → "match" (nhận diện)
        """
        print(f"\n{SEP}")
        print("  TEST 3: ĐỘ CHÍNH XÁC NHẬN DIỆN (Confusion Matrix)")
        print(f"  Ngưỡng mặc định: {self.default_threshold}")
        print(SEP)

        # Kiểm tra xem đã có embedding chưa
        enrolled_ids = [
            sid for sid, data in self.embeddings_cache.items()
            if data["enrolled"] is not None
        ]

        if len(enrolled_ids) < 2:
            print("  ✗ Cần ít nhất 2 người đã đăng ký (enrolled) để chạy test nhận diện.")
            return

        # Tính confusion matrix tại ngưỡng mặc định
        metrics = self._compute_metrics_at_threshold(self.default_threshold)

        # In kết quả chi tiết
        print(f"\n  {THIN_SEP}")
        print(f"  CONFUSION MATRIX (threshold = {self.default_threshold}):")
        print(f"  {THIN_SEP}")

        # Bảng confusion matrix
        print(f"                         Predicted")
        print(f"                    ┌──────────┬──────────┐")
        print(f"                    │  Match   │ No Match │")
        print(f"  ┌─────────────────┼──────────┼──────────┤")
        print(f"  │  Actual Match   │ TP={metrics['TP']:5d} │ FN={metrics['FN']:5d} │")
        print(f"  ├─────────────────┼──────────┼──────────┤")
        print(f"  │ Actual No Match │ FP={metrics['FP']:5d} │ TN={metrics['TN']:5d} │")
        print(f"  └─────────────────┴──────────┴──────────┘")

        print(f"\n  CÁC CHỈ SỐ ĐÁNH GIÁ:")
        print(f"  • Accuracy:   {metrics['accuracy']:.4f}  ({metrics['accuracy']*100:.2f}%)")
        print(f"  • Precision:  {metrics['precision']:.4f}")
        print(f"  • Recall:     {metrics['recall']:.4f}")
        print(f"  • F1-Score:   {metrics['f1']:.4f}")
        print(f"  • FAR:        {metrics['FAR']:.4f}  (False Accept Rate)")
        print(f"  • FRR:        {metrics['FRR']:.4f}  (False Reject Rate)")
        print(f"  • Genuine pairs:   {metrics['genuine_pairs']}")
        print(f"  • Impostor pairs:  {metrics['impostor_pairs']}")

        self.results["recognition"] = metrics

    def _compute_metrics_at_threshold(self, threshold: float) -> dict:
        """
        Tính các chỉ số đánh giá tại một ngưỡng cosine distance cụ thể.

        Genuine pair: probe và enrolled thuộc cùng 1 người
            - cosine_dist < threshold → TP (nhận đúng)
            - cosine_dist >= threshold → FN (từ chối nhầm)

        Impostor pair: probe và enrolled thuộc khác người
            - cosine_dist < threshold → FP (chấp nhận nhầm)
            - cosine_dist >= threshold → TN (từ chối đúng)

        Returns:
            dict chứa TP, TN, FP, FN, accuracy, precision, recall, f1, FAR, FRR
        """
        TP = 0  # True Positive  – Nhận đúng người đúng
        TN = 0  # True Negative  – Từ chối đúng người lạ
        FP = 0  # False Positive – Chấp nhận nhầm (người lạ → nhận là quen)
        FN = 0  # False Negative – Từ chối nhầm (người quen → bị từ chối)

        genuine_pairs = 0
        impostor_pairs = 0
        genuine_distances = []
        impostor_distances = []

        enrolled_ids = [
            sid for sid, data in self.embeddings_cache.items()
            if data["enrolled"] is not None
        ]

        # ── 1. So sánh Genuine pairs (cùng người) ──
        for sid in enrolled_ids:
            enrolled_emb = self.embeddings_cache[sid]["enrolled"]
            probes = self.embeddings_cache[sid]["probes"]

            for probe_emb in probes:
                dist = cosine_distance(enrolled_emb, probe_emb)
                genuine_pairs += 1
                genuine_distances.append(dist)

                if dist < threshold:
                    TP += 1  # Nhận đúng
                else:
                    FN += 1  # Từ chối nhầm

        # ── 2. So sánh Impostor pairs (khác người, registered vs registered) ──
        for i, sid_a in enumerate(enrolled_ids):
            enrolled_a = self.embeddings_cache[sid_a]["enrolled"]

            for j, sid_b in enumerate(enrolled_ids):
                if i == j:
                    continue  # Bỏ qua so sánh với chính mình

                # So sánh enrolled_a vs tất cả probe của sid_b
                for probe_emb in self.embeddings_cache[sid_b]["probes"]:
                    dist = cosine_distance(enrolled_a, probe_emb)
                    impostor_pairs += 1
                    impostor_distances.append(dist)

                    if dist < threshold:
                        FP += 1  # Chấp nhận nhầm
                    else:
                        TN += 1  # Từ chối đúng

        # ── 3. So sánh Impostor pairs (unknown vs enrolled) ──
        for unknown_emb in self.unknown_embeddings:
            for sid in enrolled_ids:
                enrolled_emb = self.embeddings_cache[sid]["enrolled"]
                dist = cosine_distance(enrolled_emb, unknown_emb)
                impostor_pairs += 1
                impostor_distances.append(dist)

                if dist < threshold:
                    FP += 1
                else:
                    TN += 1

        # ── 4. Tính các chỉ số ──
        total = TP + TN + FP + FN
        accuracy = (TP + TN) / total if total > 0 else 0
        precision = TP / (TP + FP) if (TP + FP) > 0 else 0
        recall = TP / (TP + FN) if (TP + FN) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # FAR = FP / (FP + TN) = tỉ lệ người lạ bị chấp nhận nhầm
        FAR = FP / (FP + TN) if (FP + TN) > 0 else 0

        # FRR = FN / (FN + TP) = tỉ lệ người quen bị từ chối nhầm
        FRR = FN / (FN + TP) if (FN + TP) > 0 else 0

        return {
            "threshold": threshold,
            "TP": TP, "TN": TN, "FP": FP, "FN": FN,
            "genuine_pairs": genuine_pairs,
            "impostor_pairs": impostor_pairs,
            "accuracy": round(accuracy, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "FAR": round(FAR, 6),
            "FRR": round(FRR, 6),
            "mean_genuine_dist": round(float(np.mean(genuine_distances)), 4) if genuine_distances else None,
            "std_genuine_dist": round(float(np.std(genuine_distances)), 4) if genuine_distances else None,
            "mean_impostor_dist": round(float(np.mean(impostor_distances)), 4) if impostor_distances else None,
            "std_impostor_dist": round(float(np.std(impostor_distances)), 4) if impostor_distances else None,
        }

    # --------------------------------------------------------------------------
    # TEST 4: PHÂN TÍCH NGƯỠNG (Threshold Analysis)
    # --------------------------------------------------------------------------

    def test_threshold_analysis(self):
        """
        Chạy lại bài test nhận diện tại nhiều ngưỡng khác nhau.
        Cho phép tìm ngưỡng tối ưu (trade-off giữa FAR và FRR).
        """
        print(f"\n{SEP}")
        print("  TEST 4: PHÂN TÍCH NGƯỠNG (Threshold Analysis)")
        print(SEP)

        enrolled_ids = [
            sid for sid, data in self.embeddings_cache.items()
            if data["enrolled"] is not None and len(data["probes"]) > 0
        ]

        if len(enrolled_ids) < 2:
            print("  ✗ Không đủ dữ liệu để phân tích ngưỡng.")
            return

        # Tính metrics tại mỗi ngưỡng
        threshold_results = []
        for th in ANALYSIS_THRESHOLDS:
            metrics = self._compute_metrics_at_threshold(th)
            threshold_results.append(metrics)

        # In bảng kết quả
        print(f"\n  Bảng so sánh các ngưỡng (Cosine Distance):")
        print()

        headers = ["Threshold", "TP", "TN", "FP", "FN", "Accuracy", "FAR", "FRR", "F1"]
        rows = []
        for m in threshold_results:
            marker = " ◄" if m["threshold"] == self.default_threshold else ""
            rows.append([
                f"{m['threshold']:.2f}{marker}",
                m["TP"], m["TN"], m["FP"], m["FN"],
                f"{m['accuracy']:.4f}",
                f"{m['FAR']:.4f}",
                f"{m['FRR']:.4f}",
                f"{m['f1']:.4f}",
            ])

        print_table(headers, rows)

        # Tìm ngưỡng tối ưu (F1 cao nhất)
        best = max(threshold_results, key=lambda x: x["f1"])
        print(f"\n  ★ Ngưỡng tối ưu (F1 cao nhất): {best['threshold']:.2f}")
        print(f"    F1 = {best['f1']:.4f}, Accuracy = {best['accuracy']:.4f}")
        print(f"    FAR = {best['FAR']:.4f}, FRR = {best['FRR']:.4f}")

        # Tìm EER (Equal Error Rate) – điểm FAR ≈ FRR
        # Nội suy tuyến tính để tìm giao điểm
        eer_threshold = None
        eer_value = None
        for i in range(len(threshold_results) - 1):
            far_i = threshold_results[i]["FAR"]
            frr_i = threshold_results[i]["FRR"]
            far_j = threshold_results[i+1]["FAR"]
            frr_j = threshold_results[i+1]["FRR"]

            # Kiểm tra xem FAR và FRR có giao nhau giữa 2 ngưỡng
            if (far_i - frr_i) * (far_j - frr_j) <= 0:
                # Nội suy tuyến tính tìm điểm giao
                th_i = threshold_results[i]["threshold"]
                th_j = threshold_results[i+1]["threshold"]

                if (far_i - frr_i) != (far_j - frr_j):
                    alpha = (far_i - frr_i) / ((far_i - frr_i) - (far_j - frr_j))
                    eer_threshold = th_i + alpha * (th_j - th_i)
                    eer_value = far_i + alpha * (far_j - far_i)

        if eer_threshold is not None:
            print(f"\n  ★ EER (Equal Error Rate) ≈ {eer_value:.4f} tại ngưỡng ≈ {eer_threshold:.3f}")

        # Phân phối khoảng cách
        if threshold_results[0].get("mean_genuine_dist") is not None:
            print(f"\n  Phân phối Cosine Distance:")
            print(f"  • Genuine pairs  (cùng người):  mean = {threshold_results[0]['mean_genuine_dist']:.4f} ± {threshold_results[0]['std_genuine_dist']:.4f}")
            print(f"  • Impostor pairs (khác người):  mean = {threshold_results[0]['mean_impostor_dist']:.4f} ± {threshold_results[0]['std_impostor_dist']:.4f}")

        # Lưu kết quả
        self.results["threshold_analysis"] = {
            "thresholds": [m["threshold"] for m in threshold_results],
            "results": threshold_results,
            "best_threshold": best["threshold"],
            "best_f1": best["f1"],
            "eer_threshold": round(eer_threshold, 4) if eer_threshold else None,
            "eer_value": round(eer_value, 4) if eer_value else None,
        }

    # --------------------------------------------------------------------------
    # TEST 5: ĐÁNH GIÁ CHẤT LƯỢNG ẢNH (FIQA Evaluation)
    # --------------------------------------------------------------------------

    def test_fiqa_evaluation(self):
        """
        Đánh giá chất lượng ảnh khuôn mặt (Face Image Quality Assessment).
        So sánh điểm FIQA giữa ảnh rõ (registered/) và ảnh mờ (blurred/).
        Phân tích tỉ lệ lọc tại các ngưỡng FIQA khác nhau.
        """
        print(f"\n{SEP}")
        print("  TEST 5: ĐÁNH GIÁ CHẤT LƯỢNG ẢNH (FIQA)")
        print(SEP)

        # Thu thập điểm FIQA cho ảnh rõ (từ registered/)
        clear_scores = []   # Danh sách (filename, fiqa_score) cho ảnh rõ
        blurred_scores = [] # Danh sách (filename, fiqa_score) cho ảnh mờ

        # ── Ảnh rõ ──
        if self.registered_dir.exists():
            print("  Đánh giá ảnh rõ (registered/)...")
            for student_dir in sorted(self.registered_dir.iterdir()):
                if not student_dir.is_dir():
                    continue

                for img_file in sorted(student_dir.iterdir()):
                    if not is_image_file(img_file):
                        continue

                    img_bgr = load_image_bgr(img_file)
                    if img_bgr is None:
                        continue

                    # Phát hiện khuôn mặt để crop trước khi tính FIQA
                    faces = self.engine._get_faces_sorted_by_area(img_bgr)
                    if not faces:
                        continue

                    # Crop khuôn mặt lớn nhất
                    bbox = faces[0].bbox.astype(int)
                    h, w = img_bgr.shape[:2]
                    x1, y1, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), min(w, bbox[2]), min(h, bbox[3])
                    face_crop = img_bgr[y1:y2, x1:x2]

                    score = self.engine.evaluate_fiqa(face_crop)
                    label = f"{student_dir.name}/{img_file.name}"
                    clear_scores.append((label, score))
                    print(f"    {label}: FIQA = {score:.4f}")

        # ── Ảnh mờ ──
        if self.blurred_dir.exists():
            print(f"\n  Đánh giá ảnh mờ (blurred/)...")
            for img_file in sorted(self.blurred_dir.iterdir()):
                if not is_image_file(img_file):
                    continue

                img_bgr = load_image_bgr(img_file)
                if img_bgr is None:
                    continue

                # Với ảnh mờ, đôi khi không phát hiện được khuôn mặt
                # → dùng toàn bộ ảnh để tính FIQA
                faces = self.engine._get_faces_sorted_by_area(img_bgr)
                if faces:
                    bbox = faces[0].bbox.astype(int)
                    h, w = img_bgr.shape[:2]
                    x1, y1, x2, y2 = max(0, bbox[0]), max(0, bbox[1]), min(w, bbox[2]), min(h, bbox[3])
                    face_crop = img_bgr[y1:y2, x1:x2]
                else:
                    face_crop = img_bgr  # Dùng toàn bộ ảnh nếu không detect được

                score = self.engine.evaluate_fiqa(face_crop)
                blurred_scores.append((img_file.name, score))
                print(f"    {img_file.name}: FIQA = {score:.4f}")

        # ── Thống kê ──
        print(f"\n  {THIN_SEP}")
        print(f"  THỐNG KÊ FIQA:")

        clear_values = [s for _, s in clear_scores]
        blurred_values = [s for _, s in blurred_scores]

        if clear_values:
            print(f"  • Ảnh rõ (registered/):  n={len(clear_values)}")
            print(f"    Mean = {np.mean(clear_values):.4f}, Std = {np.std(clear_values):.4f}")
            print(f"    Min  = {np.min(clear_values):.4f}, Max = {np.max(clear_values):.4f}")

        if blurred_values:
            print(f"  • Ảnh mờ (blurred/):     n={len(blurred_values)}")
            print(f"    Mean = {np.mean(blurred_values):.4f}, Std = {np.std(blurred_values):.4f}")
            print(f"    Min  = {np.min(blurred_values):.4f}, Max = {np.max(blurred_values):.4f}")

        # ── Phân tích tỉ lệ lọc tại các ngưỡng FIQA ──
        if clear_values or blurred_values:
            print(f"\n  Tỉ lệ bị lọc (rejected) tại các ngưỡng FIQA:")
            headers = ["FIQA Threshold", "Clear Rejected", "Blurred Rejected"]
            rows = []
            fiqa_threshold_data = []

            for th in FIQA_THRESHOLDS:
                clear_rej = sum(1 for v in clear_values if v < th)
                blur_rej = sum(1 for v in blurred_values if v < th)

                clear_rej_pct = (clear_rej / len(clear_values) * 100) if clear_values else 0
                blur_rej_pct = (blur_rej / len(blurred_values) * 100) if blurred_values else 0

                rows.append([
                    f"{th:.2f}",
                    f"{clear_rej}/{len(clear_values)} ({clear_rej_pct:.0f}%)",
                    f"{blur_rej}/{len(blurred_values)} ({blur_rej_pct:.0f}%)" if blurred_values else "N/A",
                ])

                fiqa_threshold_data.append({
                    "threshold": th,
                    "clear_rejected": clear_rej,
                    "clear_total": len(clear_values),
                    "clear_rejected_pct": round(clear_rej_pct, 2),
                    "blurred_rejected": blur_rej,
                    "blurred_total": len(blurred_values),
                    "blurred_rejected_pct": round(blur_rej_pct, 2),
                })

            print()
            print_table(headers, rows)

        # Lưu kết quả
        self.results["fiqa"] = {
            "clear_scores": [{"file": f, "score": round(s, 4)} for f, s in clear_scores],
            "blurred_scores": [{"file": f, "score": round(s, 4)} for f, s in blurred_scores],
            "clear_stats": {
                "count": len(clear_values),
                "mean": round(float(np.mean(clear_values)), 4) if clear_values else None,
                "std": round(float(np.std(clear_values)), 4) if clear_values else None,
                "min": round(float(np.min(clear_values)), 4) if clear_values else None,
                "max": round(float(np.max(clear_values)), 4) if clear_values else None,
            },
            "blurred_stats": {
                "count": len(blurred_values),
                "mean": round(float(np.mean(blurred_values)), 4) if blurred_values else None,
                "std": round(float(np.std(blurred_values)), 4) if blurred_values else None,
                "min": round(float(np.min(blurred_values)), 4) if blurred_values else None,
                "max": round(float(np.max(blurred_values)), 4) if blurred_values else None,
            },
            "threshold_analysis": fiqa_threshold_data if (clear_values or blurred_values) else [],
        }

    # --------------------------------------------------------------------------
    # TEST 6: ĐÁNH GIÁ CHỐNG GIẢ MẠO (Anti-Spoofing)
    # --------------------------------------------------------------------------

    def test_anti_spoofing(self):
        """
        Đánh giá hiệu quả module Anti-Spoofing (MiniFASNet):
        1. Ảnh giả mạo (spoofing/) → nên được phát hiện là SPOOF
        2. Ảnh thật (registered/)  → KHÔNG nên bị đánh nhầm là SPOOF

        Tính:
        - Spoof Detection Rate (SDR): tỉ lệ phát hiện đúng ảnh giả
        - False Positive Rate (FPR): tỉ lệ ảnh thật bị đánh nhầm là giả
        """
        print(f"\n{SEP}")
        print("  TEST 6: ĐÁNH GIÁ CHỐNG GIẢ MẠO (Anti-Spoofing)")
        print(SEP)

        if self.engine.anti_spoof_session is None:
            print("  ✗ Anti-Spoof model chưa được tải. Bỏ qua test này.")
            self.results["anti_spoofing"] = {"status": "skipped", "reason": "Model not loaded"}
            return

        # ── 1. Kiểm tra ảnh giả mạo ──
        spoof_results = {"print_attack": [], "screen_attack": []}

        for attack_type in ["print_attack", "screen_attack"]:
            attack_dir = self.spoofing_dir / attack_type

            if not attack_dir.exists():
                print(f"  ⚠ {attack_type}/ không tồn tại, bỏ qua.")
                continue

            print(f"\n  Kiểm tra {attack_type}/...")

            for img_file in sorted(attack_dir.iterdir()):
                if not is_image_file(img_file):
                    continue

                img_bgr = load_image_bgr(img_file)
                if img_bgr is None:
                    continue

                # Encode sang base64 để dùng process_attendance_frame
                b64 = image_to_base64(img_bgr)
                result = self.engine.process_attendance_frame(b64, mode="1")

                is_spoof = result.get("spoof_detected", False)
                has_embeddings = len(result.get("embeddings", [])) > 0

                # Nếu spoof_detected = True → phát hiện đúng
                # Hoặc nếu không có embedding nào → cũng có thể là bị chặn bởi FIQA/spoof
                detected_correctly = is_spoof or not has_embeddings

                spoof_results[attack_type].append({
                    "file": img_file.name,
                    "spoof_detected": is_spoof,
                    "has_embeddings": has_embeddings,
                    "correctly_blocked": detected_correctly,
                })

                status = "✓ BLOCKED" if detected_correctly else "✗ MISSED"
                print(f"    {img_file.name}: spoof={is_spoof}, emb={has_embeddings} → {status}")

        # ── 2. Kiểm tra False Positive trên ảnh thật ──
        live_results = []

        if self.registered_dir.exists():
            print(f"\n  Kiểm tra False Positive trên ảnh thật (registered/)...")
            # Chỉ test một ảnh đại diện mỗi sinh viên để tiết kiệm thời gian
            for student_dir in sorted(self.registered_dir.iterdir()):
                if not student_dir.is_dir():
                    continue

                img_files = sorted([f for f in student_dir.iterdir() if is_image_file(f)])
                if not img_files:
                    continue

                img_file = img_files[0]  # Lấy ảnh đầu tiên
                img_bgr = load_image_bgr(img_file)
                if img_bgr is None:
                    continue

                b64 = image_to_base64(img_bgr)
                result = self.engine.process_attendance_frame(b64, mode="1")

                is_spoof = result.get("spoof_detected", False)
                has_embeddings = len(result.get("embeddings", [])) > 0

                # Ảnh thật KHÔNG nên bị đánh là spoof
                false_positive = is_spoof

                live_results.append({
                    "file": f"{student_dir.name}/{img_file.name}",
                    "spoof_detected": is_spoof,
                    "has_embeddings": has_embeddings,
                    "false_positive": false_positive,
                })

                status = "✓ LIVE (đúng)" if not false_positive else "✗ FALSE POSITIVE"
                print(f"    {student_dir.name}/{img_file.name}: spoof={is_spoof} → {status}")

        # ── 3. Thống kê ──
        print(f"\n  {THIN_SEP}")
        print(f"  KẾT QUẢ ANTI-SPOOFING:")

        total_spoof = 0
        blocked_spoof = 0

        for attack_type, items in spoof_results.items():
            n_total = len(items)
            n_blocked = sum(1 for x in items if x["correctly_blocked"])
            total_spoof += n_total
            blocked_spoof += n_blocked
            rate = (n_blocked / n_total * 100) if n_total > 0 else 0
            print(f"  • {attack_type}: {n_blocked}/{n_total} blocked ({rate:.1f}%)")

        overall_sdr = (blocked_spoof / total_spoof * 100) if total_spoof > 0 else 0
        print(f"  • Tổng SDR (Spoof Detection Rate): {blocked_spoof}/{total_spoof} ({overall_sdr:.1f}%)")

        n_live = len(live_results)
        n_fp = sum(1 for x in live_results if x["false_positive"])
        fpr = (n_fp / n_live * 100) if n_live > 0 else 0
        print(f"  • False Positive (ảnh thật bị nhầm): {n_fp}/{n_live} ({fpr:.1f}%)")

        # Lưu kết quả
        self.results["anti_spoofing"] = {
            "spoof_results": spoof_results,
            "live_results": live_results,
            "summary": {
                "total_spoof_images": total_spoof,
                "correctly_blocked": blocked_spoof,
                "spoof_detection_rate": round(overall_sdr, 2),
                "total_live_images": n_live,
                "false_positives": n_fp,
                "false_positive_rate": round(fpr, 2),
            }
        }

    # --------------------------------------------------------------------------
    # XUẤT KẾT QUẢ (Output Results)
    # --------------------------------------------------------------------------

    def save_results(self):
        """
        Lưu kết quả ra file:
        1. accuracy_report.json – Báo cáo chi tiết đầy đủ
        2. accuracy_summary.csv – Bảng tóm tắt (dễ import vào Excel/Google Sheets)
        """
        ensure_dir(self.output_dir)

        # ── 1. Lưu JSON ──
        json_path = self.output_dir / "accuracy_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n  ✓ Chi tiết: {json_path}")

        # ── 2. Lưu CSV tóm tắt ──
        csv_path = self.output_dir / "accuracy_summary.csv"
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            # Header section: Metadata
            writer.writerow(["AuEdu Face Recognition – Accuracy Test Report"])
            writer.writerow(["Timestamp", self.results["metadata"]["timestamp"]])
            writer.writerow(["Default Threshold", self.results["metadata"]["default_threshold"]])
            writer.writerow([])

            # Section 1: Detection
            writer.writerow(["=== DETECTION RATE ==="])
            det = self.results.get("detection", {})
            writer.writerow(["Total Images", det.get("total_images", "N/A")])
            writer.writerow(["Detected", det.get("detected", "N/A")])
            writer.writerow(["Detection Rate (%)", det.get("detection_rate", "N/A")])
            writer.writerow([])

            # Section 2: Embedding
            writer.writerow(["=== EMBEDDING EXTRACTION ==="])
            emb = self.results.get("embedding", {})
            writer.writerow(["Total Images", emb.get("total_images", "N/A")])
            writer.writerow(["Extracted", emb.get("extracted", "N/A")])
            writer.writerow(["Avg Time (ms)", emb.get("avg_extraction_time_ms", "N/A")])
            writer.writerow([])

            # Section 3: Recognition at default threshold
            writer.writerow(["=== RECOGNITION (default threshold) ==="])
            rec = self.results.get("recognition", {})
            for key in ["threshold", "TP", "TN", "FP", "FN",
                        "accuracy", "precision", "recall", "f1", "FAR", "FRR"]:
                writer.writerow([key, rec.get(key, "N/A")])
            writer.writerow([])

            # Section 4: Threshold Analysis
            writer.writerow(["=== THRESHOLD ANALYSIS ==="])
            th_data = self.results.get("threshold_analysis", {})
            if th_data.get("results"):
                writer.writerow(["Threshold", "TP", "TN", "FP", "FN",
                                 "Accuracy", "FAR", "FRR", "F1"])
                for m in th_data["results"]:
                    writer.writerow([
                        m["threshold"], m["TP"], m["TN"], m["FP"], m["FN"],
                        m["accuracy"], m["FAR"], m["FRR"], m["f1"]
                    ])
            writer.writerow([])

            # Section 5: FIQA
            writer.writerow(["=== FIQA ==="])
            fiqa = self.results.get("fiqa", {})
            cs = fiqa.get("clear_stats", {})
            bs = fiqa.get("blurred_stats", {})
            writer.writerow(["Category", "Count", "Mean", "Std", "Min", "Max"])
            writer.writerow(["Clear", cs.get("count"), cs.get("mean"), cs.get("std"),
                             cs.get("min"), cs.get("max")])
            writer.writerow(["Blurred", bs.get("count"), bs.get("mean"), bs.get("std"),
                             bs.get("min"), bs.get("max")])
            writer.writerow([])

            # Section 6: Anti-Spoofing
            writer.writerow(["=== ANTI-SPOOFING ==="])
            asf = self.results.get("anti_spoofing", {})
            summary = asf.get("summary", {})
            writer.writerow(["Spoof Detection Rate (%)", summary.get("spoof_detection_rate", "N/A")])
            writer.writerow(["False Positive Rate (%)", summary.get("false_positive_rate", "N/A")])

        print(f"  ✓ Tóm tắt:  {csv_path}")

    # --------------------------------------------------------------------------
    # IN BÁO CÁO TỔNG KẾT
    # --------------------------------------------------------------------------

    def print_summary(self):
        """In bảng tổng kết cuối cùng ra console."""
        print(f"\n{'█' * 78}")
        print(f"  TỔNG KẾT KIỂM THỬ ĐỘ CHÍNH XÁC – HỆ THỐNG AUEDU")
        print(f"  Thời gian: {self.results['metadata']['timestamp']}")
        print(f"{'█' * 78}")

        headers = ["Hạng mục", "Kết quả", "Chi tiết"]
        rows = []

        # Detection
        det = self.results.get("detection", {})
        if det:
            rows.append([
                "Face Detection",
                f"{det.get('detection_rate', 0):.1f}%",
                f"{det.get('detected', 0)}/{det.get('total_images', 0)} ảnh"
            ])

        # Embedding
        emb = self.results.get("embedding", {})
        if emb:
            rows.append([
                "Embedding (512-D)",
                f"{emb.get('extracted', 0)}/{emb.get('total_images', 0)}",
                f"Avg: {emb.get('avg_extraction_time_ms', 0):.1f}ms"
            ])

        # Recognition
        rec = self.results.get("recognition", {})
        if rec:
            rows.append([
                f"Recognition (θ={rec.get('threshold', '?')})",
                f"F1={rec.get('f1', 0):.4f}",
                f"Acc={rec.get('accuracy', 0):.4f}"
            ])
            rows.append([
                "  └ FAR / FRR",
                f"{rec.get('FAR', 0):.4f} / {rec.get('FRR', 0):.4f}",
                f"TP={rec.get('TP', 0)} FP={rec.get('FP', 0)}"
            ])

        # Best threshold
        th = self.results.get("threshold_analysis", {})
        if th:
            rows.append([
                "Best Threshold",
                f"θ = {th.get('best_threshold', '?')}",
                f"F1 = {th.get('best_f1', 0):.4f}"
            ])
            if th.get("eer_threshold"):
                rows.append([
                    "EER",
                    f"≈ {th.get('eer_value', 0):.4f}",
                    f"θ ≈ {th.get('eer_threshold', 0):.3f}"
                ])

        # FIQA
        fiqa = self.results.get("fiqa", {})
        cs = fiqa.get("clear_stats", {})
        bs = fiqa.get("blurred_stats", {})
        if cs.get("mean") is not None:
            rows.append([
                "FIQA (Clear)",
                f"Mean={cs['mean']:.4f}",
                f"n={cs.get('count', 0)}"
            ])
        if bs.get("mean") is not None:
            rows.append([
                "FIQA (Blurred)",
                f"Mean={bs['mean']:.4f}",
                f"n={bs.get('count', 0)}"
            ])

        # Anti-Spoofing
        asf = self.results.get("anti_spoofing", {})
        summary = asf.get("summary", {})
        if summary:
            rows.append([
                "Anti-Spoof SDR",
                f"{summary.get('spoof_detection_rate', 0):.1f}%",
                f"{summary.get('correctly_blocked', 0)}/{summary.get('total_spoof_images', 0)}"
            ])
            rows.append([
                "Anti-Spoof FPR",
                f"{summary.get('false_positive_rate', 0):.1f}%",
                f"{summary.get('false_positives', 0)}/{summary.get('total_live_images', 0)} live"
            ])

        print()
        print_table(headers, rows)
        print(f"\n{'█' * 78}\n")

    # --------------------------------------------------------------------------
    # CHẠY TOÀN BỘ KIỂM THỬ (Run All Tests)
    # --------------------------------------------------------------------------

    def run(self):
        """Entry point: chạy tất cả các bài test theo thứ tự."""
        start_time = time.time()

        print(f"\n{'█' * 78}")
        print(f"  AUEDU – KIỂM THỬ ĐỘ CHÍNH XÁC NHẬN DIỆN KHUÔN MẶT")
        print(f"  Bắt đầu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'█' * 78}")

        # Bước 0: Kiểm tra dataset
        if not self._validate_dataset():
            return

        # Bước 1: Khởi tạo AI Engine (tải model vào bộ nhớ)
        self._init_engine()

        # Bước 2: Chạy các bài test tuần tự
        print("\n  Bắt đầu chạy 6 bài test...\n")

        self.test_detection_rate()        # Test 1: Face Detection
        self.test_embedding_extraction()  # Test 2: Embedding 512-D
        self.test_recognition_accuracy()  # Test 3: Recognition + Confusion Matrix
        self.test_threshold_analysis()    # Test 4: Threshold Analysis
        self.test_fiqa_evaluation()       # Test 5: FIQA
        self.test_anti_spoofing()         # Test 6: Anti-Spoofing

        # Bước 3: Lưu kết quả
        elapsed = time.time() - start_time
        self.results["metadata"]["total_time_seconds"] = round(elapsed, 2)

        print(f"\n{SEP}")
        print("  LƯU KẾT QUẢ")
        print(SEP)
        self.save_results()

        # Bước 4: In báo cáo tổng kết
        self.print_summary()

        print(f"  Tổng thời gian chạy: {elapsed:.1f} giây")
        print(f"  Kết quả lưu tại:     {self.output_dir}/")
        print()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main():
    """
    Hàm main – parse command line arguments và khởi chạy kiểm thử.
    """
    parser = argparse.ArgumentParser(
        description="AuEdu – Kiểm thử Độ chính xác Nhận diện Khuôn mặt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  # Chạy với cấu hình mặc định (từ thư mục Server/)
  python ../tests/test_accuracy.py

  # Chỉ định dataset và ngưỡng
  python ../tests/test_accuracy.py --dataset ../tests/dataset --threshold 0.40

  # Chỉ định thư mục output
  python ../tests/test_accuracy.py --output ../tests/results
        """
    )

    parser.add_argument(
        "--dataset",
        type=str,
        default=str(SCRIPT_DIR / "dataset"),
        help="Đường dẫn đến thư mục dataset (default: tests/dataset/)"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="Ngưỡng cosine distance mặc định để nhận diện (default: 0.45)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=str(SCRIPT_DIR / "results"),
        help="Thư mục lưu kết quả JSON/CSV (default: tests/results/)"
    )

    args = parser.parse_args()

    # Khởi tạo và chạy
    tester = AccuracyTester(
        dataset_dir=args.dataset,
        default_threshold=args.threshold,
        output_dir=args.output,
    )
    tester.run()


if __name__ == "__main__":
    main()
