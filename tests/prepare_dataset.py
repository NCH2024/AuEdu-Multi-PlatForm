"""
tests/prepare_dataset.py
========================
Tự động tải và chuẩn bị bộ dữ liệu LFW (Labeled Faces in the Wild) 
cho kiểm thử hệ thống AuEdu.

Bộ dữ liệu LFW được chọn vì các lý do sau:
    1. LFW là CHUẨN QUỐC TẾ (benchmark standard) được sử dụng rộng rãi 
       trong hơn 5,000 bài báo khoa học [Huang et al., 2007].
    2. ArcFace (thuật toán nhận diện của AuEdu) đã được benchmark chính thức 
       trên LFW, đạt 99.83% [Deng et al., 2019]. Việc dùng cùng dataset 
       cho phép SO SÁNH TRỰC TIẾP kết quả.
    3. LFW chứa ảnh "in the wild" (không kiểm soát) — ánh sáng, góc chụp, 
       biểu cảm, nền phong phú — phản ánh điều kiện thực tế tốt hơn 
       dataset phòng thí nghiệm.
    4. Tải tự động qua scikit-learn, đảm bảo TÍNH TÁI LẬP (reproducibility).

Cấu trúc output:
    tests/dataset/
    ├── registered/         ← 20 người, mỗi người ≥5 ảnh (enrolled + probe)
    │   ├── person_001_George_W_Bush/
    │   │   ├── enroll_001.jpg
    │   │   ├── probe_002.jpg
    │   │   └── ...
    │   └── ...
    ├── unknown/            ← 30 ảnh người chỉ có 1 ảnh (không đăng ký)
    ├── blurred/            ← Ảnh mờ tạo từ registered/ bằng Gaussian + Motion Blur
    └── spoofing/
        ├── print_attack/   ← Giả lập ảnh in giấy (thêm nhiễu print artifacts)
        └── screen_attack/  ← Giả lập ảnh chụp màn hình (moiré + color shift)

Sử dụng:
    cd Server
    python ../tests/prepare_dataset.py
    python ../tests/prepare_dataset.py --min-faces 5 --num-registered 20
    python ../tests/prepare_dataset.py --skip-download   # nếu đã tải rồi

Phụ thuộc:
    pip install scikit-learn pillow numpy opencv-python

Tác giả: Chanh-Hiep NGUYEN
Ngày tạo: 2026-05-24
"""

import os
import sys
import json
import shutil
import argparse
import warnings
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

import numpy as np
import cv2


def to_uint8(img: np.ndarray) -> np.ndarray:
    """
    Chuyển ảnh sang uint8 [0,255] an toàn.
    
    scikit-learn trả ảnh LFW dạng float64 với giá trị ĐÃ trong [0, 255]
    (KHÔNG phải [0, 1]). Nếu nhân thêm ×255 sẽ bị trắng xóa!
    """
    if img.dtype in (np.float64, np.float32):
        if img.max() > 1.5:
            # Giá trị đã ở [0, 255] — chỉ cần cast
            return img.clip(0, 255).astype(np.uint8)
        else:
            # Giá trị ở [0, 1] — nhân 255
            return (img * 255).clip(0, 255).astype(np.uint8)
    return img.astype(np.uint8)

# Suppress sklearn deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ==============================================================================
# HẰNG SỐ CẤU HÌNH
# ==============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent          # .../tests/
PROJECT_ROOT = SCRIPT_DIR.parent                       # .../AuEdu-Multi-PlatForm/
DEFAULT_DATASET_DIR = SCRIPT_DIR / "dataset"

# Cấu hình mặc định
DEFAULT_NUM_REGISTERED = 20     # Số người đăng ký (registered)
DEFAULT_MIN_FACES = 5           # Tối thiểu N ảnh/người
DEFAULT_NUM_UNKNOWN = 30        # Số ảnh người lạ (unknown)
DEFAULT_NUM_BLUR = 50           # Số ảnh mờ tạo ra
DEFAULT_NUM_SPOOF_PRINT = 25    # Số ảnh giả lập print attack
DEFAULT_NUM_SPOOF_SCREEN = 25   # Số ảnh giả lập screen attack

# Random seed cho tính tái lập
RANDOM_SEED = 42


# ==============================================================================
# 1. TẢI BỘ DỮ LIỆU LFW
# ==============================================================================

def download_lfw(min_faces_per_person: int = 5, color: bool = True) -> dict:
    """
    Tải bộ dữ liệu LFW từ scikit-learn.
    
    Hàm fetch_lfw_people() tự động:
        1. Tải dataset từ server (lần đầu ~200MB)
        2. Cache vào ~/scikit_learn_data/ (không cần tải lại)
        3. Parse metadata (tên người, labels)
    
    Args:
        min_faces_per_person: Chỉ giữ người có ít nhất N ảnh
        color: True = ảnh RGB, False = grayscale
    
    Returns:
        dict chứa images, target, target_names
    """
    print("\n" + "=" * 70)
    print("  BƯỚC 1: TẢI BỘ DỮ LIỆU LFW (Labeled Faces in the Wild)")
    print("=" * 70)
    print(f"  Nguồn: scikit-learn (tự động cache)")
    print(f"  Bộ lọc: ≥ {min_faces_per_person} ảnh/người")
    print(f"  Chế độ: {'Màu (RGB)' if color else 'Xám (Grayscale)'}")
    print()
    
    try:
        from sklearn.datasets import fetch_lfw_people
    except ImportError:
        print("  ✗ Lỗi: scikit-learn chưa được cài đặt!")
        print("  → Chạy: pip install scikit-learn")
        sys.exit(1)
    
    print("  Đang tải (lần đầu có thể mất 2-5 phút)...")
    
    # QUAN TRỌNG:
    # - slice_=None → lấy ảnh 250×250 ĐẦY ĐỦ (mặc định sklearn crop xuống 125×94)
    # - resize=1.0 → giữ nguyên kích thước
    # - Ảnh 250×250 đủ lớn để RetinaFace detect được khuôn mặt
    lfw = fetch_lfw_people(
        min_faces_per_person=min_faces_per_person,
        color=color,
        resize=1.0,
        slice_=None,  # Lấy ảnh 250×250 đầy đủ, KHÔNG crop
    )
    
    # Thống kê
    n_samples, h, w = lfw.images.shape[0], lfw.images.shape[1], lfw.images.shape[2]
    n_people = len(lfw.target_names)
    
    print(f"\n  ✓ Đã tải thành công!")
    print(f"  • Tổng ảnh:    {n_samples:,}")
    print(f"  • Số người:    {n_people}")
    print(f"  • Kích thước:  {w}x{h} px")
    
    # In top 10 người có nhiều ảnh nhất
    print(f"\n  Top 10 người có nhiều ảnh nhất:")
    unique, counts = np.unique(lfw.target, return_counts=True)
    sorted_idx = np.argsort(-counts)
    for i in range(min(10, len(sorted_idx))):
        idx = sorted_idx[i]
        name = lfw.target_names[unique[idx]]
        count = counts[idx]
        print(f"    {i+1:2d}. {name:<35s} — {count:3d} ảnh")
    
    return {
        "images": lfw.images,
        "target": lfw.target,
        "target_names": lfw.target_names,
    }



def get_unknown_from_data(
    lfw_data: dict, 
    registered_targets: set, 
    max_images: int = 30
) -> list:
    """
    Lấy ảnh unknown từ CHÍNH dữ liệu LFW đã tải (không tải lại).
    
    Chọn người KHÔNG nằm trong danh sách registered (top 20),
    lấy 1 ảnh ngẫu nhiên của mỗi người.
    
    Args:
        lfw_data: dict từ download_lfw() (đã có sẵn trong RAM)
        registered_targets: set các target ID đã dùng cho registered
        max_images: Số ảnh unknown cần lấy
    
    Returns:
        list các ảnh numpy
    """
    images = lfw_data["images"]
    target = lfw_data["target"]
    
    rng = np.random.RandomState(RANDOM_SEED + 1)
    
    # Tìm tất cả người KHÔNG nằm trong registered
    unique_targets = np.unique(target)
    unknown_targets = [t for t in unique_targets if t not in registered_targets]
    
    # Chọn ngẫu nhiên
    if len(unknown_targets) > max_images:
        selected = rng.choice(unknown_targets, max_images, replace=False)
    else:
        selected = unknown_targets[:max_images]
    
    unknown_images = []
    for t in selected:
        mask = target == t
        person_imgs = images[mask]
        # Lấy 1 ảnh ngẫu nhiên
        idx = rng.randint(0, len(person_imgs))
        unknown_images.append(person_imgs[idx])
    
    print(f"  ✓ Đã lấy {len(unknown_images)} ảnh unknown (từ {len(unknown_targets)} người không đăng ký)")
    return unknown_images



# ==============================================================================
# 2. TẠO ẢNH MỜ (BLURRED) CHO FIQA TEST
# ==============================================================================

def create_blurred_images(
    source_images: List[np.ndarray],
    output_dir: Path,
    num_blur: int = 50,
) -> int:
    """
    Tạo ảnh mờ từ ảnh nguồn bằng các kỹ thuật blur khác nhau.
    
    Kỹ thuật:
        1. Gaussian Blur — mô phỏng out-of-focus
        2. Motion Blur — mô phỏng camera rung
        3. Average Blur — mô phỏng camera chất lượng thấp
    
    Trong hệ thống AuEdu, FIQA (Face Image Quality Assessment) sử dụng 
    Laplacian Variance để đo độ sắc nét. Ảnh mờ sẽ có FIQA score thấp 
    và bị lọc bỏ trước khi đưa vào pipeline nhận diện.
    
    Args:
        source_images: Danh sách ảnh nguồn (RGB float64 hoặc uint8)
        output_dir: Thư mục lưu ảnh mờ
        num_blur: Số ảnh mờ cần tạo
    
    Returns:
        Số ảnh đã tạo thành công
    """
    print("\n" + "=" * 70)
    print("  BƯỚC 3: TẠO ẢNH MỜ (BLURRED) CHO FIQA TEST")
    print("=" * 70)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(RANDOM_SEED + 2)
    
    created = 0
    blur_methods = ["gaussian", "motion", "average"]
    
    for i in range(min(num_blur, len(source_images))):
        img = source_images[i % len(source_images)]
        
        # Chuyển sang uint8 BGR nếu cần
        img_uint8 = to_uint8(img)
        
        # Chuyển RGB → BGR cho OpenCV
        if len(img_uint8.shape) == 3 and img_uint8.shape[2] == 3:
            img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_uint8
        
        # Chọn phương pháp blur
        method = blur_methods[i % len(blur_methods)]
        
        if method == "gaussian":
            # Gaussian Blur — kernel lớn = mờ nhiều
            kernel_size = rng.choice([15, 21, 27, 35])
            blurred = cv2.GaussianBlur(img_bgr, (kernel_size, kernel_size), 0)
            suffix = f"gaussian_k{kernel_size}"
            
        elif method == "motion":
            # Motion Blur — tạo kernel dạng đường thẳng
            kernel_size = int(rng.choice([15, 20, 25, 30]))
            # Tạo motion blur kernel
            kernel = np.zeros((kernel_size, kernel_size))
            angle = int(rng.randint(0, 180))  # Góc blur ngẫu nhiên
            
            # Tạo đường thẳng trong kernel
            center = kernel_size // 2
            # Đường thẳng ngang
            kernel[center, :] = np.ones(kernel_size)
            kernel = kernel / kernel_size
            
            # Xoay kernel theo góc
            M = cv2.getRotationMatrix2D((center, center), float(angle), 1.0)
            kernel = cv2.warpAffine(kernel, M, (kernel_size, kernel_size))
            kernel = kernel / kernel.sum() if kernel.sum() > 0 else kernel
            
            blurred = cv2.filter2D(img_bgr, -1, kernel)
            suffix = f"motion_k{kernel_size}_a{angle}"
            
        else:  # average
            kernel_size = rng.choice([11, 15, 21])
            blurred = cv2.blur(img_bgr, (kernel_size, kernel_size))
            suffix = f"average_k{kernel_size}"
        
        # Lưu ảnh
        filename = f"blur_{i+1:03d}_{suffix}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), blurred, [cv2.IMWRITE_JPEG_QUALITY, 90])
        created += 1
    
    print(f"  ✓ Đã tạo {created} ảnh mờ tại: {output_dir}")
    return created


# ==============================================================================
# 3. TẠO ẢNH GIẢ MẠO (SPOOFING) CHO ANTI-SPOOFING TEST
# ==============================================================================

def create_print_attack_images(
    source_images: List[np.ndarray],
    output_dir: Path,
    num_images: int = 25,
) -> int:
    """
    Tạo ảnh giả lập tấn công in giấy (Print Attack).
    
    Phương pháp mô phỏng hiệu ứng ảnh bị in ra giấy rồi chụp lại:
        1. Giảm độ phân giải (simulating printer DPI limitation)
        2. Thêm nhiễu halftone/dot pattern (giả lập hạt mực in)
        3. Giảm contrast + tăng brightness (giấy phản xạ ánh sáng)
        4. Thêm nhiễu Gaussian (nhiễu quang học khi chụp lại)
        5. Biến dạng nhẹ (giấy không phẳng hoàn toàn)
    
    Kỹ thuật này được sử dụng trong SynthASpoof [CVPR 2023] để tạo 
    dữ liệu spoofing giả lập khi không có phương tiện thu thập thực tế.
    
    Args:
        source_images: Ảnh nguồn (RGB)
        output_dir: Thư mục output
        num_images: Số ảnh cần tạo
    
    Returns:
        Số ảnh đã tạo
    """
    print("\n  Đang tạo ảnh Print Attack (giả lập ảnh in giấy)...")
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(RANDOM_SEED + 3)
    
    created = 0
    for i in range(min(num_images, len(source_images))):
        img = source_images[i % len(source_images)]
        
        # Chuyển sang uint8 BGR
        img_uint8 = to_uint8(img)
        
        if len(img_uint8.shape) == 3 and img_uint8.shape[2] == 3:
            img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_uint8
        
        h, w = img_bgr.shape[:2]
        result = img_bgr.astype(np.float32)
        
        # ── Bước 1: Giảm resolution rồi phóng lại (print DPI limitation) ──
        scale = rng.uniform(0.4, 0.6)
        small = cv2.resize(result, (int(w * scale), int(h * scale)), 
                          interpolation=cv2.INTER_LINEAR)
        result = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
        
        # ── Bước 2: Thay đổi color balance (giấy + mực in) ──
        # Giấy trắng phản xạ → tăng brightness, giảm contrast
        alpha = rng.uniform(0.65, 0.85)   # Contrast reduction
        beta = rng.uniform(20, 50)         # Brightness increase
        result = alpha * result + beta
        
        # Shift màu nhẹ (mực in không hoàn hảo)
        color_shift = rng.uniform(-15, 15, size=3).astype(np.float32)
        result += color_shift.reshape(1, 1, 3)
        
        # ── Bước 3: Thêm texture giấy (paper grain noise) ──
        grain = rng.normal(0, rng.uniform(3, 8), result.shape).astype(np.float32)
        result += grain
        
        # ── Bước 4: Halftone effect nhẹ (dot pattern) ──
        # Simulating printer dots bằng periodic noise
        period = rng.choice([3, 4, 5])
        halftone = np.zeros_like(result)
        halftone[::period, ::period, :] = rng.uniform(5, 15)
        result += halftone
        
        # ── Bước 5: Slight color desaturation (mực in pha trộn) ──
        gray = cv2.cvtColor(result.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR).astype(np.float32)
        desat_factor = rng.uniform(0.15, 0.35)
        result = result * (1 - desat_factor) + gray_3ch * desat_factor
        
        # ── Bước 6: Slight warping (giấy cong/nhăn) ──
        # Affine transform nhẹ mô phỏng giấy không phẳng
        pts1 = np.float32([[0, 0], [w, 0], [0, h]])
        dx = rng.uniform(-3, 3, 3)
        dy = rng.uniform(-3, 3, 3)
        pts2 = np.float32([
            [0 + dx[0], 0 + dy[0]], 
            [w + dx[1], 0 + dy[1]], 
            [0 + dx[2], h + dy[2]]
        ])
        M = cv2.getAffineTransform(pts1, pts2)
        result = cv2.warpAffine(result.clip(0, 255).astype(np.uint8), M, (w, h),
                                borderMode=cv2.BORDER_REFLECT)
        
        # ── Bước 7: JPEG compression artifacts ──
        result = result.clip(0, 255).astype(np.uint8)
        encode_quality = rng.randint(40, 70)
        _, encoded = cv2.imencode('.jpg', result, 
                                  [cv2.IMWRITE_JPEG_QUALITY, encode_quality])
        result = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        
        # Lưu
        filename = f"print_attack_{i+1:03d}.jpg"
        cv2.imwrite(str(output_dir / filename), result, [cv2.IMWRITE_JPEG_QUALITY, 85])
        created += 1
    
    print(f"    ✓ Đã tạo {created} ảnh print attack")
    return created


def create_screen_attack_images(
    source_images: List[np.ndarray],
    output_dir: Path,
    num_images: int = 25,
) -> int:
    """
    Tạo ảnh giả lập tấn công qua màn hình (Screen/Replay Attack).
    
    Phương pháp mô phỏng hiệu ứng ảnh hiển thị trên màn hình rồi chụp lại:
        1. Thêm moiré pattern (giao thoa giữa pixel grid và camera sensor)
        2. Thêm color banding (dải màu do màn hình LCD)
        3. Screen reflection artifacts (ánh sáng phản chiếu)
        4. Giảm dynamic range (màn hình có contrast ratio hữu hạn)
        5. Pixelation effect (nhìn thấy pixel khi chụp gần)
    
    Args:
        source_images: Ảnh nguồn
        output_dir: Thư mục output
        num_images: Số ảnh cần tạo
    
    Returns:
        Số ảnh đã tạo
    """
    print("  Đang tạo ảnh Screen Attack (giả lập ảnh trên màn hình)...")
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(RANDOM_SEED + 4)
    
    created = 0
    for i in range(min(num_images, len(source_images))):
        img = source_images[i % len(source_images)]
        
        img_uint8 = to_uint8(img)
        
        if len(img_uint8.shape) == 3 and img_uint8.shape[2] == 3:
            img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_uint8
        
        h, w = img_bgr.shape[:2]
        result = img_bgr.astype(np.float32)
        
        # ── Bước 1: Moiré pattern (giao thoa sensor-screen) ──
        # Tạo sóng sin 2D mô phỏng moiré
        freq_x = rng.uniform(0.03, 0.08)
        freq_y = rng.uniform(0.03, 0.08)
        amplitude = rng.uniform(8, 20)
        x_coords = np.arange(w).reshape(1, -1)
        y_coords = np.arange(h).reshape(-1, 1)
        moire = amplitude * np.sin(2 * np.pi * freq_x * x_coords + 
                                    2 * np.pi * freq_y * y_coords)
        moire = np.stack([moire, moire, moire], axis=2)
        result += moire
        
        # ── Bước 2: Color banding (horizontal bands) ──
        band_height = rng.randint(3, 8)
        for y in range(0, h, band_height * 2):
            end_y = min(y + band_height, h)
            shift = rng.uniform(-8, 8, 3).astype(np.float32)
            result[y:end_y, :, :] += shift.reshape(1, 1, 3)
        
        # ── Bước 3: Screen color temperature shift ──
        # Màn hình LCD có color temperature khác tự nhiên
        # Thường hơi xanh (blue tint)
        blue_shift = rng.uniform(5, 20)
        result[:, :, 0] += blue_shift      # Blue channel
        result[:, :, 2] -= blue_shift / 2  # Red channel giảm
        
        # ── Bước 4: Giảm dynamic range ──
        # Màn hình có black level > 0 và white level < 255
        black_level = rng.uniform(10, 30)
        white_level = rng.uniform(230, 245)
        result = result.clip(0, 255)
        result = black_level + (result / 255.0) * (white_level - black_level)
        
        # ── Bước 5: Screen reflection / glare ──
        # Thêm vùng sáng mờ (mô phỏng ánh sáng phản chiếu)
        if rng.random() > 0.3:  # 70% chance
            glare_cx = rng.randint(w // 4, 3 * w // 4)
            glare_cy = rng.randint(h // 4, 3 * h // 4)
            glare_r = rng.randint(w // 4, w // 2)
            glare_strength = rng.uniform(15, 40)
            
            Y, X = np.ogrid[:h, :w]
            dist = np.sqrt((X - glare_cx)**2 + (Y - glare_cy)**2)
            glare_mask = np.exp(-dist**2 / (2 * glare_r**2)) * glare_strength
            glare_mask = np.stack([glare_mask]*3, axis=2)
            result += glare_mask
        
        # ── Bước 6: Pixelation (simulating low PPI visible) ──
        pixel_scale = rng.uniform(0.7, 0.85)
        small = cv2.resize(result.clip(0, 255).astype(np.uint8), 
                          (int(w * pixel_scale), int(h * pixel_scale)),
                          interpolation=cv2.INTER_LINEAR)
        result = cv2.resize(small, (w, h), 
                           interpolation=cv2.INTER_NEAREST).astype(np.float32)
        
        # ── Bước 7: Gaussian noise (camera sensor noise khi chụp) ──
        noise = rng.normal(0, rng.uniform(3, 8), result.shape).astype(np.float32)
        result += noise
        
        # Lưu
        result = result.clip(0, 255).astype(np.uint8)
        filename = f"screen_attack_{i+1:03d}.jpg"
        cv2.imwrite(str(output_dir / filename), result, [cv2.IMWRITE_JPEG_QUALITY, 80])
        created += 1
    
    print(f"    ✓ Đã tạo {created} ảnh screen attack")
    return created


# ==============================================================================
# 4. TỔ CHỨC DATASET THEO CẤU TRÚC TEST
# ==============================================================================

def organize_dataset(
    lfw_data: dict,
    dataset_dir: Path,
    num_registered: int = 20,
    num_unknown: int = 30,
    num_blur: int = 50,
    num_spoof_print: int = 25,
    num_spoof_screen: int = 25,
) -> dict:
    """
    Tổ chức dữ liệu LFW thành cấu trúc dataset cho test_accuracy.py.
    
    Logic chọn người:
        1. Sắp xếp theo số ảnh giảm dần
        2. Chọn top N người có nhiều ảnh nhất → registered/
        3. Người chỉ có 1 ảnh → unknown/
    
    Args:
        lfw_data: dict từ download_lfw()
        dataset_dir: Thư mục gốc dataset
        num_registered: Số người đăng ký
        num_unknown: Số ảnh unknown
        num_blur: Số ảnh blur
        num_spoof_print: Số ảnh print attack
        num_spoof_screen: Số ảnh screen attack
    
    Returns:
        dict thống kê dataset đã tạo
    """
    print("\n" + "=" * 70)
    print("  BƯỚC 2: TỔ CHỨC DATASET")
    print("=" * 70)
    
    images = lfw_data["images"]
    target = lfw_data["target"]
    target_names = lfw_data["target_names"]
    
    # Xoá dataset cũ nếu có
    if dataset_dir.exists():
        print(f"  ⚠ Xoá dataset cũ tại: {dataset_dir}")
        shutil.rmtree(dataset_dir)
    
    # Tạo cấu trúc thư mục
    registered_dir = dataset_dir / "registered"
    unknown_dir = dataset_dir / "unknown"
    blurred_dir = dataset_dir / "blurred"
    spoof_print_dir = dataset_dir / "spoofing" / "print_attack"
    spoof_screen_dir = dataset_dir / "spoofing" / "screen_attack"
    
    for d in [registered_dir, unknown_dir, blurred_dir, spoof_print_dir, spoof_screen_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # ── Sắp xếp theo số ảnh ──
    unique_targets, counts = np.unique(target, return_counts=True)
    sorted_idx = np.argsort(-counts)
    
    stats = {
        "registered_people": 0,
        "registered_images": 0,
        "unknown_images": 0,
        "blurred_images": 0,
        "spoof_print_images": 0,
        "spoof_screen_images": 0,
        "people_list": [],
    }
    
    # ── Tạo registered/ ──
    print(f"\n  Đang tạo registered/ ({num_registered} người)...")
    all_registered_images = []
    
    for rank, idx in enumerate(sorted_idx[:num_registered]):
        person_id = unique_targets[idx]
        person_name = target_names[person_id]
        person_mask = target == person_id
        person_images = images[person_mask]
        n_imgs = len(person_images)
        
        # Tạo tên thư mục: person_001_George_W_Bush
        safe_name = person_name.replace(" ", "_")
        folder_name = f"person_{rank+1:03d}_{safe_name}"
        person_dir = registered_dir / folder_name
        person_dir.mkdir(parents=True, exist_ok=True)
        
        # Lưu ảnh: ảnh đầu = enroll, còn lại = probe
        for j, img in enumerate(person_images):
            # Chuyển sang uint8 an toàn
            img_uint8 = to_uint8(img)
            
            # RGB → BGR cho OpenCV
            img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
            
            if j == 0:
                filename = f"enroll_{j+1:03d}.jpg"
            else:
                filename = f"probe_{j+1:03d}.jpg"
            
            cv2.imwrite(str(person_dir / filename), img_bgr, 
                       [cv2.IMWRITE_JPEG_QUALITY, 95])
            all_registered_images.append(img)
        
        stats["people_list"].append({
            "name": person_name,
            "folder": folder_name,
            "num_images": n_imgs,
            "enroll": 1,
            "probe": n_imgs - 1,
        })
        stats["registered_people"] += 1
        stats["registered_images"] += n_imgs
        
        print(f"    ✓ {folder_name}: {n_imgs} ảnh (1 enroll + {n_imgs-1} probe)")
    
    # ── Tạo unknown/ ──
    print(f"\n  Đang tạo unknown/ ({num_unknown} ảnh)...")
    
    # Lấy danh sách target ID đã dùng cho registered
    registered_target_ids = set()
    for idx in sorted_idx[:num_registered]:
        registered_target_ids.add(unique_targets[idx])
    
    unknown_images = get_unknown_from_data(lfw_data, registered_target_ids, num_unknown)
    
    if len(unknown_images) > 0:
        for j, img in enumerate(unknown_images):
            img_uint8 = to_uint8(img)
            
            img_bgr = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2BGR)
            filename = f"unknown_{j+1:03d}.jpg"
            cv2.imwrite(str(unknown_dir / filename), img_bgr,
                       [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        stats["unknown_images"] = len(unknown_images)
        print(f"  ✓ Đã tạo {len(unknown_images)} ảnh unknown")
    
    # ── Tạo blurred/ ──
    stats["blurred_images"] = create_blurred_images(
        all_registered_images, blurred_dir, num_blur
    )
    
    # ── Tạo spoofing/ ──
    print("\n" + "=" * 70)
    print("  BƯỚC 4: TẠO ẢNH SPOOFING GIẢ LẬP")
    print("=" * 70)
    
    # Dùng ảnh registered để tạo spoofing
    spoof_source = all_registered_images[:max(num_spoof_print, num_spoof_screen)]
    
    stats["spoof_print_images"] = create_print_attack_images(
        spoof_source, spoof_print_dir, num_spoof_print
    )
    stats["spoof_screen_images"] = create_screen_attack_images(
        spoof_source, spoof_screen_dir, num_spoof_screen
    )
    
    return stats


# ==============================================================================
# 5. TẠO METADATA FILE
# ==============================================================================

def save_metadata(dataset_dir: Path, stats: dict):
    """
    Lưu thông tin metadata của dataset để truy xuất sau.
    """
    metadata = {
        "dataset_name": "AuEdu Test Dataset (based on LFW)",
        "created_at": datetime.now().isoformat(),
        "source": "Labeled Faces in the Wild (LFW)",
        "citation": (
            'G. B. Huang, M. Ramesh, T. Berg, and E. Learned-Miller, '
            '"Labeled Faces in the Wild: A Database for Studying Face '
            'Recognition in Unconstrained Environments," University of '
            'Massachusetts, Amherst, Technical Report 07-49, Oct. 2007.'
        ),
        "citation_ieee": (
            '[19] G. B. Huang, M. Ramesh, T. Berg, and E. Learned-Miller, '
            '"Labeled Faces in the Wild: A Database for Studying Face '
            'Recognition in Unconstrained Environments," Univ. Massachusetts, '
            'Amherst, Tech. Rep. 07-49, Oct. 2007. [Online]. Available: '
            'http://vis-www.cs.umass.edu/lfw/'
        ),
        "description": {
            "vi": (
                "Bộ dữ liệu kiểm thử được tạo từ LFW — bộ dữ liệu chuẩn quốc tế "
                "cho nhận diện khuôn mặt. Ảnh mờ (blurred) được sinh bằng Gaussian "
                "và Motion Blur. Ảnh giả mạo (spoofing) được sinh bằng kỹ thuật "
                "augmentation mô phỏng print attack (nhiễu in ấn) và screen attack "
                "(moiré pattern, color shift)."
            ),
            "en": (
                "Test dataset derived from LFW — the international standard benchmark "
                "for face recognition. Blurred images generated via Gaussian and Motion "
                "Blur. Spoofing images generated via augmentation simulating print "
                "attacks (print artifacts) and screen attacks (moiré patterns, color shift)."
            ),
        },
        "statistics": stats,
        "spoofing_generation_method": {
            "print_attack": [
                "Resolution reduction (simulating printer DPI)",
                "Contrast reduction + brightness increase",
                "Color shift (ink imperfection)",
                "Paper grain noise (texture)",
                "Halftone dot pattern",
                "Partial desaturation",
                "Slight affine warping (paper bending)",
                "Heavy JPEG compression artifacts",
            ],
            "screen_attack": [
                "Moiré pattern (sensor-screen interference)",
                "Horizontal color banding (LCD subpixels)",
                "Blue color temperature shift",
                "Reduced dynamic range (black/white levels)",
                "Screen reflection/glare",
                "Pixelation (visible pixel grid)",
                "Gaussian sensor noise",
            ],
        },
        "justification": {
            "vi": (
                "Việc sử dụng LFW thay vì dataset tự thu thập được lý giải bởi: "
                "(1) LFW là benchmark chuẩn với hơn 5,000 trích dẫn, đảm bảo kết quả "
                "có thể SO SÁNH TRỰC TIẾP với các nghiên cứu khác; "
                "(2) ArcFace — thuật toán cốt lõi của AuEdu — được benchmark chính thức "
                "trên LFW (99.83%), tạo baseline cho đánh giá; "
                "(3) Ảnh 'in the wild' phản ánh điều kiện thực tế (biến thiên ánh sáng, "
                "góc chụp, biểu cảm) tốt hơn dataset phòng thí nghiệm; "
                "(4) Tải tự động qua scikit-learn đảm bảo tính tái lập hoàn toàn."
            ),
        },
    }
    
    metadata_path = dataset_dir / "dataset_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n  💾 Metadata đã lưu tại: {metadata_path}")


# ==============================================================================
# 6. IN TỔNG HỢP
# ==============================================================================

def print_summary(dataset_dir: Path, stats: dict):
    """In bảng tổng hợp dataset đã tạo."""
    
    print("\n")
    print("╔" + "═" * 70 + "╗")
    print("║" + "  DATASET ĐÃ SẴN SÀNG – TỔNG HỢP  ".center(70) + "║")
    print("╠" + "═" * 70 + "╣")
    print("║" + f"  📁 Vị trí: {str(dataset_dir)[:55]}".ljust(70) + "║")
    print("║" + f"  📦 Nguồn:  LFW (Labeled Faces in the Wild)".ljust(70) + "║")
    print("╠" + "═" * 70 + "╣")
    
    rows = [
        ("registered/", f"{stats['registered_people']} người, {stats['registered_images']} ảnh"),
        ("unknown/", f"{stats['unknown_images']} ảnh"),
        ("blurred/", f"{stats['blurred_images']} ảnh"),
        ("spoofing/print_attack/", f"{stats['spoof_print_images']} ảnh"),
        ("spoofing/screen_attack/", f"{stats['spoof_screen_images']} ảnh"),
    ]
    
    total = (stats['registered_images'] + stats['unknown_images'] + 
             stats['blurred_images'] + stats['spoof_print_images'] + 
             stats['spoof_screen_images'])
    
    for label, value in rows:
        print("║" + f"  {label:<25s} {value}".ljust(70) + "║")
    
    print("║" + "  ─" * 34 + "──║")
    print("║" + f"  {'TỔNG CỘNG':<25s} {total} ảnh".ljust(70) + "║")
    
    print("╠" + "═" * 70 + "╣")
    print("║" + "  Bước tiếp theo:".ljust(70) + "║")
    print("║" + "    cd Server".ljust(70) + "║")
    print("║" + "    python ../tests/test_accuracy.py".ljust(70) + "║")
    print("╚" + "═" * 70 + "╝")


# ==============================================================================
# MAIN
# ==============================================================================

def check_existing_dataset(dataset_dir: Path) -> dict:
    """
    Kiểm tra xem dataset đã tồn tại hay chưa.
    
    Returns:
        dict thống kê nếu dataset tồn tại, None nếu chưa có
    """
    registered_dir = dataset_dir / "registered"
    unknown_dir = dataset_dir / "unknown"
    blurred_dir = dataset_dir / "blurred"
    spoof_print_dir = dataset_dir / "spoofing" / "print_attack"
    spoof_screen_dir = dataset_dir / "spoofing" / "screen_attack"
    
    # Kiểm tra registered/ có thư mục con với ảnh không
    if not registered_dir.exists():
        return None
    
    person_dirs = [d for d in registered_dir.iterdir() if d.is_dir()]
    if len(person_dirs) == 0:
        return None
    
    # Đếm ảnh trong từng thư mục
    stats = {
        "registered_people": 0,
        "registered_images": 0,
        "unknown_images": 0,
        "blurred_images": 0,
        "spoof_print_images": 0,
        "spoof_screen_images": 0,
        "people_list": [],
    }
    
    for person_dir in sorted(person_dirs):
        imgs = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png"))
        if len(imgs) > 0:
            stats["registered_people"] += 1
            stats["registered_images"] += len(imgs)
            enroll_count = len([f for f in imgs if f.name.startswith("enroll")])
            probe_count = len(imgs) - enroll_count
            stats["people_list"].append({
                "name": person_dir.name,
                "folder": person_dir.name,
                "num_images": len(imgs),
                "enroll": enroll_count,
                "probe": probe_count,
            })
    
    # Đếm các thư mục khác
    if unknown_dir.exists():
        stats["unknown_images"] = len(list(unknown_dir.glob("*.jpg")) + 
                                       list(unknown_dir.glob("*.png")))
    if blurred_dir.exists():
        stats["blurred_images"] = len(list(blurred_dir.glob("*.jpg")) + 
                                       list(blurred_dir.glob("*.png")))
    if spoof_print_dir.exists():
        stats["spoof_print_images"] = len(list(spoof_print_dir.glob("*.jpg")) + 
                                           list(spoof_print_dir.glob("*.png")))
    if spoof_screen_dir.exists():
        stats["spoof_screen_images"] = len(list(spoof_screen_dir.glob("*.jpg")) + 
                                            list(spoof_screen_dir.glob("*.png")))
    
    # Chỉ coi là tồn tại nếu có ít nhất 1 người registered
    if stats["registered_people"] > 0:
        return stats
    return None


# ==============================================================================
# MAIN
# ==============================================================================

def resume_missing_parts(dataset_dir: Path, existing_stats: dict, args) -> dict:
    """
    Bổ sung các phần còn thiếu (blurred, spoofing) mà không xóa 
    registered/ và unknown/ đã có sẵn.
    
    Logic:
        - registered/ đã có → giữ nguyên, chỉ đọc ảnh ra để sinh blur/spoof
        - unknown/ đã có → giữ nguyên
        - blurred/ thiếu hoặc không đủ → sinh bổ sung
        - spoofing/ thiếu → sinh mới
    """
    print("\n" + "=" * 70)
    print("  CHẾ ĐỘ BỔ SUNG – Giữ nguyên registered/ & unknown/")
    print("=" * 70)
    
    registered_dir = dataset_dir / "registered"
    blurred_dir = dataset_dir / "blurred"
    spoof_print_dir = dataset_dir / "spoofing" / "print_attack"
    spoof_screen_dir = dataset_dir / "spoofing" / "screen_attack"
    
    # Đọc ảnh từ registered/ để dùng cho blur/spoof
    print("\n  Đang đọc ảnh từ registered/ ...")
    all_registered_images = []
    
    for person_dir in sorted(registered_dir.iterdir()):
        if not person_dir.is_dir():
            continue
        for img_path in sorted(person_dir.glob("*.jpg")):
            img = cv2.imread(str(img_path))
            if img is not None:
                # BGR → RGB
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                all_registered_images.append(img_rgb)
    
    print(f"  ✓ Đã đọc {len(all_registered_images)} ảnh từ registered/")
    
    if len(all_registered_images) == 0:
        print("  ✗ Không tìm thấy ảnh nào trong registered/!")
        return existing_stats
    
    updated_stats = existing_stats.copy()
    
    # ── Kiểm tra & bổ sung blurred/ ──
    target_blur = getattr(args, 'num_blur', DEFAULT_NUM_BLUR)
    if existing_stats["blurred_images"] < target_blur:
        print(f"\n  ⚠ blurred/ chỉ có {existing_stats['blurred_images']}/{target_blur} ảnh → Sinh bổ sung")
        # Xóa blurred cũ (không đủ)
        if blurred_dir.exists():
            shutil.rmtree(blurred_dir)
        updated_stats["blurred_images"] = create_blurred_images(
            all_registered_images, blurred_dir, target_blur
        )
    else:
        print(f"\n  ✓ blurred/ đã đủ ({existing_stats['blurred_images']} ảnh)")
    
    # ── Kiểm tra & bổ sung print_attack/ ──
    target_print = getattr(args, 'num_spoof_print', DEFAULT_NUM_SPOOF_PRINT)
    if existing_stats["spoof_print_images"] < target_print:
        print(f"\n  ⚠ print_attack/ chỉ có {existing_stats['spoof_print_images']}/{target_print} ảnh → Sinh bổ sung")
        if spoof_print_dir.exists():
            shutil.rmtree(spoof_print_dir)
        
        print("\n" + "=" * 70)
        print("  TẠO ẢNH SPOOFING GIẢ LẬP")
        print("=" * 70)
        
        spoof_source = all_registered_images[:max(target_print, target_print)]
        updated_stats["spoof_print_images"] = create_print_attack_images(
            spoof_source, spoof_print_dir, target_print
        )
    else:
        print(f"\n  ✓ print_attack/ đã đủ ({existing_stats['spoof_print_images']} ảnh)")
    
    # ── Kiểm tra & bổ sung screen_attack/ ──
    target_screen = getattr(args, 'num_spoof_screen', DEFAULT_NUM_SPOOF_SCREEN)
    if existing_stats["spoof_screen_images"] < target_screen:
        print(f"\n  ⚠ screen_attack/ chỉ có {existing_stats['spoof_screen_images']}/{target_screen} ảnh → Sinh bổ sung")
        if spoof_screen_dir.exists():
            shutil.rmtree(spoof_screen_dir)
        
        spoof_source = all_registered_images[:target_screen]
        updated_stats["spoof_screen_images"] = create_screen_attack_images(
            spoof_source, spoof_screen_dir, target_screen
        )
    else:
        print(f"\n  ✓ screen_attack/ đã đủ ({existing_stats['spoof_screen_images']} ảnh)")
    
    return updated_stats


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Tải và chuẩn bị bộ dữ liệu LFW cho kiểm thử AuEdu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
    python tests/prepare_dataset.py              # Tự động: tải mới hoặc bổ sung thiếu
    python tests/prepare_dataset.py --force       # Xóa hết, tải lại từ đầu
    python tests/prepare_dataset.py --num-blur 80 # Tạo 80 ảnh blur (nhiều hơn mặc định)
        """,
    )
    parser.add_argument(
        "--output", type=str, default=str(DEFAULT_DATASET_DIR),
        help=f"Thư mục output (mặc định: {DEFAULT_DATASET_DIR})"
    )
    parser.add_argument(
        "--min-faces", type=int, default=DEFAULT_MIN_FACES,
        help=f"Tối thiểu N ảnh/người (mặc định: {DEFAULT_MIN_FACES})"
    )
    parser.add_argument(
        "--num-registered", type=int, default=DEFAULT_NUM_REGISTERED,
        help=f"Số người đăng ký (mặc định: {DEFAULT_NUM_REGISTERED})"
    )
    parser.add_argument(
        "--num-unknown", type=int, default=DEFAULT_NUM_UNKNOWN,
        help=f"Số ảnh unknown (mặc định: {DEFAULT_NUM_UNKNOWN})"
    )
    parser.add_argument(
        "--num-blur", type=int, default=DEFAULT_NUM_BLUR,
        help=f"Số ảnh mờ (mặc định: {DEFAULT_NUM_BLUR})"
    )
    parser.add_argument(
        "--num-spoof-print", type=int, default=DEFAULT_NUM_SPOOF_PRINT,
        help=f"Số ảnh print attack (mặc định: {DEFAULT_NUM_SPOOF_PRINT})"
    )
    parser.add_argument(
        "--num-spoof-screen", type=int, default=DEFAULT_NUM_SPOOF_SCREEN,
        help=f"Số ảnh screen attack (mặc định: {DEFAULT_NUM_SPOOF_SCREEN})"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ghi đè dataset cũ (xóa hết rồi tải lại từ đầu)"
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("  AUEDU - TAI & CHUAN BI BO DU LIEU KIEM THU")
    print("  Nguon: LFW (Labeled Faces in the Wild)")
    print("=" * 70)
    
    dataset_dir = Path(args.output).resolve()
    
    # ── KIỂM TRA DATASET ĐÃ TỒN TẠI ──
    if not args.force:
        existing_stats = check_existing_dataset(dataset_dir)
        if existing_stats is not None:
            # Kiểm tra có phần nào thiếu không
            needs_resume = (
                existing_stats["blurred_images"] < args.num_blur or
                existing_stats["spoof_print_images"] < args.num_spoof_print or
                existing_stats["spoof_screen_images"] < args.num_spoof_screen
            )
            
            if needs_resume:
                # ── CHẾ ĐỘ BỔ SUNG ──
                print("\n  Dataset registered/ da co nhung mot so phan con thieu.")
                print("  -> Tu dong bo sung phan thieu...")
                
                updated_stats = resume_missing_parts(dataset_dir, existing_stats, args)
                
                # Lưu metadata
                save_metadata(dataset_dir, updated_stats)
                
                # In tổng hợp
                print_summary(dataset_dir, updated_stats)
                print("\n  Hoan tat! Dataset da san sang.")
                return
            else:
                # ── ĐÃ ĐẦY ĐỦ ──
                print("\n" + "=" * 70)
                print("  DATASET DA TON TAI - BO QUA TAI LAI")
                print("=" * 70)
                print(f"  Vi tri: {dataset_dir}")
                print()
                print(f"  Registered: {existing_stats['registered_people']} nguoi, "
                      f"{existing_stats['registered_images']} anh")
                print(f"  Unknown:    {existing_stats['unknown_images']} anh")
                print(f"  Blurred:    {existing_stats['blurred_images']} anh")
                print(f"  Print Attack: {existing_stats['spoof_print_images']} anh")
                print(f"  Screen Attack: {existing_stats['spoof_screen_images']} anh")
                
                total = (existing_stats['registered_images'] + 
                         existing_stats['unknown_images'] + 
                         existing_stats['blurred_images'] + 
                         existing_stats['spoof_print_images'] + 
                         existing_stats['spoof_screen_images'])
                print(f"  TONG CONG: {total} anh")
                
                print()
                print("  Neu muon tai lai (ghi de), chay:")
                print(f"     python tests/prepare_dataset.py --force")
                print()
                print("  Buoc tiep theo:")
                print("    cd Server")
                print("    python ../tests/test_accuracy.py --dataset ../tests/dataset")
                print()
                print("  Dataset san sang cho kiem thu!")
                return
    
    # ── CHẾ ĐỘ TẢI MỚI HOÀN TOÀN ──
    # Bước 1: Tải LFW
    lfw_data = download_lfw(min_faces_per_person=args.min_faces, color=True)
    
    # Bước 2-4: Tổ chức dataset
    stats = organize_dataset(
        lfw_data,
        dataset_dir,
        num_registered=args.num_registered,
        num_unknown=args.num_unknown,
        num_blur=args.num_blur,
        num_spoof_print=args.num_spoof_print,
        num_spoof_screen=args.num_spoof_screen,
    )
    
    # Bước 5: Lưu metadata
    save_metadata(dataset_dir, stats)
    
    # Bước 6: In tổng hợp
    print_summary(dataset_dir, stats)
    
    print("\n  Hoan tat! Dataset da san sang cho kiem thu.")


if __name__ == "__main__":
    main()

