# AuEdu — Hệ thống Điểm danh Khuôn mặt AI | AI Face Recognition Attendance System

<p align="center">
  <b>Ngôn ngữ / Language:</b>&nbsp;&nbsp;
  <a href="README.md">Tiếng Việt</a> ·
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white" alt="Python 3.10">
  <img src="https://img.shields.io/badge/FastAPI-0.135.1-009688?logo=fastapi&logoColor=white" alt="FastAPI Framework">
  <img src="https://img.shields.io/badge/Flet-0.85.0-02569B?logo=flutter&logoColor=white" alt="Flet Cross Platform UI">
  <img src="https://img.shields.io/badge/InsightFace-ArcFace-FF6F00?logo=ai&logoColor=white" alt="InsightFace ArcFace Face Recognition">
  <img src="https://img.shields.io/badge/ONNX_Runtime-GPU_CUDA-76B900?logo=nvidia&logoColor=white" alt="ONNX Runtime GPU CUDA Inference">
  <img src="https://img.shields.io/badge/pgvector-Vector_Search-336791?logo=postgresql&logoColor=white" alt="pgvector PostgreSQL Vector Search">
  <img src="https://img.shields.io/badge/License-Academic-yellow" alt="Academic License">
</p>

> **Hệ thống điểm danh khuôn mặt thời gian thực (real-time face recognition attendance) dành cho giáo dục**, sử dụng ArcFace + Anti-Spoofing + FIQA. Chạy trên **5 nền tảng** (Windows, Android, iOS, macOS, Web) từ cùng một codebase Python. Chi phí triển khai **0 VNĐ** — chỉ cần laptop sẵn có.

---

## Giới thiệu về AuEdu (What is AuEdu?)

**AuEdu** (Automated Education) là phần mềm **điểm danh tự động bằng nhận diện khuôn mặt** (face recognition attendance system) mã nguồn mở, được thiết kế đặc biệt cho **trường học, đại học, và cơ sở giáo dục**. Thay vì sử dụng thiết bị chuyên dụng đắt tiền (8–40 triệu VNĐ), AuEdu chạy trực tiếp trên laptop/PC sẵn có với webcam thông thường.

### So sánh giải pháp

| Vấn đề thực tế | Giải pháp của AuEdu |
|:---|:---|
| Thiết bị chấm công đắt đỏ (ZKTeco, Hikvision) | Hỗ trợ miễn phí, tận dụng phần cứng máy tính sẵn có |
| Chỉ hỗ trợ một số nền tảng cố định | Đa nền tảng (Windows, macOS, Android, iOS, Web) |
| Gian lận điểm danh bằng ảnh chụp hoặc video | Chống giả mạo sinh trắc học qua mô hình MiniFASNet |
| Ảnh chụp mờ, ngược sáng dẫn đến kết quả sai | Lọc chất lượng ảnh bằng phương sai Laplacian (FIQA) |
| Độ chính xác nhận diện thấp hoặc không ổn định | Sử dụng ArcFace 512-D (Độ chính xác 98.75%, FAR = 0%) |

### Tính năng cốt lõi (Key Features)

- **Nhận diện khuôn mặt công nghệ SOTA** — Tích hợp RetinaFace (phát hiện) và ArcFace/MobileFaceNet (nhận diện) qua InsightFace `buffalo_s`.
- **Chống giả mạo sinh trắc học (Anti-Spoofing)** — Mô hình MiniFASNet chặn các hình thức tấn công bằng ảnh in hoặc màn hình.
- **Kiểm tra chất lượng ảnh đầu vào (FIQA)** — Sử dụng Laplacian Variance loại bỏ ảnh mờ, ngược sáng.
- **Truyền luồng thời gian thực (Real-time Streaming)** — Giao thức WebSocket cho thời gian truyền frame dưới 30ms, so khớp vector dưới 0.2ms.
- **Cơ sở dữ liệu Vector chuyên dụng** — Sử dụng pgvector (PostgreSQL) kết hợp bộ nhớ đệm Numpy giúp tối ưu tốc độ tìm kiếm O(1).
- **Phát triển đa nền tảng (Cross-platform)** — Sử dụng thư viện Flet giúp đóng gói ứng dụng chạy trên 5 nền tảng từ một mã nguồn duy nhất.
- **Học thuật và mã nguồn mở** — Miễn phí phục vụ nghiên cứu khoa học và giáo dục.

---

## Kiến trúc hệ thống (System Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                  CLIENT (Flet Cross-Platform App)               │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Camera   │  │ MediaPipe │  │ WebSocket│  │  UI Pages    │  │
│  │ Capture  │──│ Face Det. │──│ Sender   │  │  (Dashboard, │  │
│  │ (30 FPS) │  │ (Client)  │  │ (base64) │  │   Register)  │  │
│  └──────────┘  └───────────┘  └────┬─────┘  └──────────────┘  │
└────────────────────────────────────┼────────────────────────────┘
                                     │ WebSocket (wss://)
┌────────────────────────────────────┼────────────────────────────┐
│              SERVER (FastAPI + Uvicorn + CUDA)                  │
│  ┌─────────────────────────────────┼─────────────────────────┐  │
│  │              AI CORE ENGINE     ▼                         │  │
│  │  ┌──────────┐  ┌────────┐  ┌────────┐  ┌──────────────┐  │  │
│  │  │RetinaFace│─▶│ FIQA   │─▶│MiniFAS │─▶│ ArcFace      │  │  │
│  │  │Detection │  │ Filter │  │Anti-   │  │ Embedding    │  │  │
│  │  │          │  │Laplace │  │Spoof   │  │ 512-D        │  │  │
│  │  └──────────┘  └────────┘  └────────┘  └──────┬───────┘  │  │
│  └───────────────────────────────────────────────┼───────────┘  │
│                                                  ▼              │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Numpy Cache         │  │  PostgreSQL + pgvector          │  │
│  │  (dot product < 0.2ms│  │  HNSW Index, cosine_distance    │  │
│  └──────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Công nghệ sử dụng (Tech Stack)

### Back-end Server

| Công nghệ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Python** | 3.10 | Ngôn ngữ lập trình chính |
| **FastAPI** | 0.135.1 | REST API + WebSocket framework |
| **Uvicorn** | 0.41.0 | ASGI Server (async) |
| **SQLAlchemy** | 2.0.30 | ORM |
| **Alembic** | — | Database migrations |
| **PostgreSQL + pgvector** | 16.x + ≥ 0.2.5 | CSDL quan hệ + Vector search |
| **Supabase** | — | Backend-as-a-Service (auth, storage) |

### AI Core Engine — Nhận diện khuôn mặt

| Công nghệ | Model | Vai trò |
|:---|:---|:---|
| **InsightFace** | `buffalo_s` | RetinaFace (detection) + MobileFaceNet (recognition) |
| **MiniFASNet** | `modelrgb.onnx` | Anti-Spoofing — Central Difference Convolution (CDC) |
| **ONNX Runtime** | GPU (CUDA 12.x) | Inference Engine — tăng tốc GPU |
| **OpenCV** | ≥ 4.8.0 | Xử lý ảnh, decode frame |

### Front-end Client — Ứng dụng đa nền tảng

| Công nghệ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Flet** | 0.85.0 | UI framework đa nền tảng (Flutter-based) |
| **MediaPipe** | — | Face detection phía client (tiết kiệm bandwidth) |

---

## Cấu trúc dự án (Project Structure)

```
AuEdu-Multi-PlatForm/
│
├── Server/                          # Back-end FastAPI
│   ├── app/
│   │   ├── ai/                      # AI Core Engine
│   │   │   ├── engine.py            #   FaceEngine (RetinaFace + ArcFace + MiniFAS)
│   │   │   ├── attendance_cache.py  #   In-memory vector cache (Numpy)
│   │   │   └── models/              #   ONNX model files (auto-download)
│   │   ├── api/                     # API Routes
│   │   │   ├── auth.py              #   JWT Authentication
│   │   │   ├── attendance.py        #   Điểm danh REST API
│   │   │   ├── websocket.py         #   WebSocket real-time handler
│   │   │   └── training.py          #   Đăng ký khuôn mặt (face enrollment)
│   │   ├── core/                    #   Cấu hình hệ thống (Settings)
│   │   ├── db/                      #   Database models (SQLAlchemy)
│   │   ├── services/                #   Business logic
│   │   └── main.py                  #   FastAPI entry point
│   ├── migrations/                  # Alembic DB migrations
│   ├── .env.example                 # Mẫu cấu hình (không chứa secrets)
│   └── requirements.txt
│
├── Client/                          # Front-end Flet Cross-Platform App
│   ├── components/                  #   UI Components (Sidebar, Camera, ...)
│   ├── pages/                       #   Trang chức năng (Dashboard, Attendance, ...)
│   ├── core/                        #   Theme, Device Manager, API Config
│   ├── main.py                      #   Flet entry point
│   ├── .env.example                 # Mẫu cấu hình client
│   └── requirements.txt
│
├── tests/                           # Bộ kiểm thử (Test Suite)
│   ├── prepare_dataset.py           #   Tải & chuẩn bị LFW dataset tự động
│   ├── test_accuracy.py             #   Accuracy, Confusion Matrix, FIQA, Anti-Spoofing
│   ├── test_latency.py              #   Benchmark tốc độ pipeline AI
│   ├── test_resource_monitor.py     #   Giám sát CPU, RAM, GPU, VRAM
│   ├── test_vector_search.py        #   Benchmark Numpy vs pgvector
│   ├── generate_word_report.py      #   Tạo báo cáo Word (.docx) tự động
│   ├── dataset/                     # Git-ignored (tự tải bằng script)
│   └── results/                     # Git-ignored (tự sinh khi chạy test)
│
├── .gitignore
├── README.md                        # Bản Tiếng Việt
└── README.en.md                     # Bản Tiếng Anh
```

---

## Cài đặt và Khởi chạy (Installation & Setup)

### Yêu cầu hệ thống (System Requirements)

| Thành phần | Tối thiểu | Khuyến nghị |
|:---|:---|:---|
| **CPU** | 4 cores | 6+ cores (Ryzen 5 / i5) |
| **RAM** | 4 GB | 8+ GB |
| **GPU** | Không bắt buộc (CPU mode) | NVIDIA GPU với CUDA |
| **Python** | 3.10 | 3.10 |
| **OS** | Windows 10 / Ubuntu 20.04 | Windows 11 |
| **Camera** | Webcam 720p | 1080p |

### 1. Clone repository

```bash
git clone https://github.com/NCH2024/AuEdu-Multi-PlatForm.git
cd AuEdu-Multi-PlatForm
```

### 2. Cài đặt Server

```bash
cd Server
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# Khởi chạy server
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Cài đặt Client

```bash
cd Client
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
flet run main.py

# Build APK cho Android:
flet build apk
```

### 4. Cấu hình môi trường (.env) — Yêu cầu bắt buộc

> **Bảo mật:** File `.env` chứa secrets (API keys, mật khẩu database) và **KHÔNG được tải lên GitHub**.
> Dự án chỉ cung cấp file `.env.example` làm mẫu.

**Bước 1:** Copy file mẫu

```bash
cp Server/.env.example Server/.env
cp Client/.env.example Client/.env
```

**Bước 2:** Tạo project Supabase miễn phí

1. Truy cập [supabase.com](https://supabase.com) → **Start your project** (đăng nhập bằng GitHub)
2. **New project** → Đặt tên + mật khẩu database → Region: `Southeast Asia`
3. Lấy thông tin kết nối:

| Thông tin | Lấy ở đâu (Supabase Dashboard) | Điền vào |
|:---|:---|:---|
| `SUPABASE_URL` | Settings → API → Project URL | `Server/.env` + `Client/.env` |
| `SUPABASE_KEY` | Settings → API → `anon` `public` key | `Server/.env` + `Client/.env` |
| `DATABASE_URL` | Settings → Database → Connection string (URI) | `Server/.env` |

**Bước 3:** Kích hoạt pgvector

```sql
-- Chạy trong Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

> **Chú ý:** **KHÔNG bao giờ** commit file `.env` lên GitHub. Nếu vô tình push, hãy thay đổi mật khẩu ngay lập tức.

---

## Kiểm thử hệ thống (Testing & Benchmarking)

AuEdu đi kèm **bộ kiểm thử tự động** đánh giá toàn diện hiệu năng AI:

| Script | Chức năng | Output |
|:---|:---|:---|
| `prepare_dataset.py` | Tải LFW dataset + sinh ảnh spoofing/blur | `tests/dataset/` |
| `test_accuracy.py` | Accuracy, Confusion Matrix, FIQA, Anti-Spoofing | `accuracy_report.json` |
| `test_latency.py` | Đo latency từng bước pipeline AI | `latency_report.json` |
| `test_resource_monitor.py` | CPU, RAM, GPU, VRAM monitoring | `resource_report.json` |
| `test_vector_search.py` | Benchmark Numpy vs pgvector | `vector_search_report.json` |
| `generate_word_report.py` | Tạo báo cáo Word (.docx) từ kết quả | `THUC_NGHIEM_AUEDU.docx` |

### Chạy kiểm thử

```bash
# 1. Chuẩn bị dataset LFW (tự động tải ~200MB)
pip install scikit-learn psutil
python tests/prepare_dataset.py

# 2. Chạy test (từ thư mục Server/)
cd Server && venv\Scripts\activate
python ../tests/test_accuracy.py --dataset ../tests/dataset
python ../tests/test_latency.py --iterations 50
python ../tests/test_resource_monitor.py --duration 30
python ../tests/test_vector_search.py

# 3. Tạo báo cáo Word
pip install python-docx
python tests/generate_word_report.py
```

---

## Kết quả thực nghiệm và So sánh thực tế (Evaluation & Comparative Analysis)

> Thực nghiệm thực tế trên **LFW dataset** (Labeled Faces in the Wild) — 1,906 ảnh, 20 người.
> Hardware máy test: AMD Ryzen 5 5600H + NVIDIA RTX 3050 Laptop GPU (4GB VRAM).

### 1. Tiêu chí 1: Tính ứng dụng và So sánh chức năng (Application & System Features)

AuEdu vượt trội về độ linh hoạt, khả năng bảo mật ngầm từ mã nguồn thực tế và tính hoàn thiện của phần mềm so với các giải pháp thương mại đắt đỏ hay thư viện thô.

| Tiêu chí | **AuEdu** (Đề xuất) | ZKTeco Terminal [10] | Hikvision MinMoe [11] | Suprema FaceStation [12] | FPT.AI eKYC [13] | VNPT vnFace | face_rec (dlib) [14] | DeepFace [15] |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Loại giải pháp** | Phần mềm mở | Phần cứng nhúng | Phần cứng nhúng | Phần cứng nhúng | Cloud API | Cloud App | Thư viện mở | Thư viện mở |
| **Chi phí ban đầu** | Miễn phí (0 VNĐ) | 8 - 25 triệu VNĐ | 10 - 30 triệu VNĐ | 15 - 40 triệu VNĐ | Cloud (0 VNĐ) | Thấp (Thuê bao) | Miễn phí (0 VNĐ) | Miễn phí (0 VNĐ) |
| **Đa nền tảng** | Có (5 nền tảng) | Không (Thiết bị riêng) | Không (Thiết bị riêng) | Không (Thiết bị riêng) | Có (API đa nền tảng) | Hạn chế (Mobile/Tablet) | Hạn chế (Chỉ Python) | Hạn chế (Chỉ Python) |
| **Lọc chất lượng FIQA** | Có (Laplacian Variance) | Có (Tự động/Nhúng) | Có (Tự động/Nhúng) | Có (Tự động/Nhúng) | Có hỗ trợ | Có hỗ trợ | Không hỗ trợ | Không hỗ trợ |
| **Chống giả mạo AI** | Có (MiniFAS RGB Liveness) | Có (IR Dual Cam) | Có (Structured Light) | Có (Visual + IR) | Có (Liveness API) | Có (Liveness API) | Không hỗ trợ | Không hỗ trợ |
| **Hiệu chỉnh ống kính** | Có (OpenCV Calibration) | Có (Cân chỉnh nhúng) | Có (Cân chỉnh nhúng) | Có (Cân chỉnh nhúng) | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ |
| **Hoạt động ngoại tuyến** | Có (LAN / Local) | Có (Standalone) | Có (Standalone) | Có (Standalone) | Không (Yêu cầu Internet) | Không (Yêu cầu Internet) | Có (Cục bộ) | Có (Cục bộ) |
| **Real-time WebSocket** | Có (WebSocket Stream) | Có (Tích hợp sẵn) | Có (Tích hợp sẵn) | Có (Tích hợp sẵn) | Không (API đồng bộ) | Không (API đồng bộ) | Không hỗ trợ | Không hỗ trợ |
| **CSDL Vector chuyên dụng**| Có (pgvector HNSW) | N/A (Nhúng) | N/A (Nhúng) | N/A (Nhúng) | N/A (Cloud) | N/A (Cloud) | Không (Brute-force) | Không (Brute-force) |
| **Bộ nhớ đệm thông minh** | Có (Numpy Cache O(1)) | Có (Trên RAM chip) | Có (Trên RAM chip) | Có (Trên RAM chip) | N/A (Cloud) | N/A (Cloud) | Không hỗ trợ | Không hỗ trợ |
| **Định vị & Vị trí GPS** | Có (OSM Nominatim) | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Hạn chế (Tọa độ thô) | Không hỗ trợ | Không hỗ trợ |
| **Giám sát thời gian phiên**| Có (Background Thread) | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không (Đăng nhập thô) | Không hỗ trợ | Không hỗ trợ |
| **Định danh thiết bị** | Có (X-Device-ID Header) | Có (Serial / MAC) | Có (Serial / MAC) | Có (Serial / MAC) | Không hỗ trợ | Có hỗ trợ | Không hỗ trợ | Không hỗ trợ |
| **Bộ nhớ đệm Client 2 tầng**| Có (Memory + Prefs Cache) | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ |
| **Đồng bộ URL tự động** | Có (Public Config Sync) | Không hỗ trợ | Không hỗ trợ | Không hỗ trợ | N/A (Cloud) | N/A (Cloud) | Không hỗ trợ | Không hỗ trợ |
| **Phân quyền RBAC** | Có (Admin/GV/SV UI) | Có (Quyền thiết bị) | Có (Quyền thiết bị) | Có (Quyền thiết bị) | Không hỗ trợ | Có hỗ trợ | Không hỗ trợ | Không hỗ trợ |
| **Tùy biến bảng màu** | Có (Dark + 4 Palettes) | Không (UI cố định) | Không (UI cố định) | Không (UI cố định) | Không (Chỉ cung cấp API) | Không (UI cố định) | Không hỗ trợ | Không hỗ trợ |
| **Quản trị học đường** | Có hỗ trợ đầy đủ | Hạn chế (Chỉ Phòng ban) | Hạn chế (Chỉ Phòng ban) | Hạn chế (Chỉ Phòng ban) | Không hỗ trợ | Hạn chế (Chỉ lớp/SV thô) | Không hỗ trợ | Không hỗ trợ |
| **Thống kê đồ thị** | Có (Flet Charts) | Không hỗ trợ | Hỗ trợ (HikCentral) | Hỗ trợ (BioStar 2) | Không hỗ trợ | Hạn chế (Đồ thị cơ bản) | Không hỗ trợ | Không hỗ trợ |
| **Xuất báo cáo** | Có hỗ trợ (Excel/CSV) | Có hỗ trợ (Excel/CSV) | Có hỗ trợ (Excel/CSV) | Có hỗ trợ (Excel/CSV) | Không hỗ trợ | Có hỗ trợ (Excel/CSV) | Không hỗ trợ | Không hỗ trợ |

### 2. Tiêu chí 2: Tốc độ xử lý & Độ trễ tác vụ (Speed & Latency)

Hệ thống đạt phản hồi giao diện tức thì (< 50 ms nhờ Flutter Engine) và xử lý luồng ảnh qua WebSocket cực nhanh:

- **Tốc độ AI Pipeline (E2E):** **~38.00 ms** (Base64 decode: 0.72 ms, Face Detection: 35.08 ms, FIQA: 0.20 ms, Anti-spoof: 3.94 ms, ArcFace embedding: 35.55 ms).
- **Thông lượng Throughput:** Đạt thực tế **21.56 FPS** khi stream ảnh liên tục.
- **Tốc độ so khớp sinh viên (Numpy Cache):** **< 0.2 ms** đối với quy mô N = 1,000 sinh viên.

#### Chi tiết so sánh độ trễ và thông lượng giữa các hệ thống:

| Tiêu chí | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Độ trễ giao diện (UI)** | **< 50 ms** | < 100 ms | < 100 ms | < 80 ms | < 150 ms | < 120 ms | N/A | N/A |
| **Độ trễ mạng truyền tải** | **Thấp (WS)** | Thấp (TCP) | Thấp (TCP) | Thấp (TCP) | Cao (HTTP) | Cao (HTTP) | Không có | Không có |
| **Độ trễ trích xuất (Infer)**| **~35.5 ms** | ~100-200 ms | ~80-150 ms | ~50-100 ms | ~200-400 ms | ~150-300 ms | ~150-300 ms | ~200-500 ms |
| **Độ trễ so khớp Vector** | **< 0.2 ms** | < 5 ms | < 5 ms | < 3 ms | < 50 ms | < 30 ms | > 10 ms | > 20 ms |
| **Độ trễ toàn luồng E2E** | **~38.0 ms** | < 300 ms | < 300 ms | < 200 ms | > 500 ms | > 400 ms | > 200 ms | > 300 ms |
| **Thông lượng (FPS)** | **~21.5 FPS**| ~5-10 FPS | ~5-10 FPS | ~10-15 FPS| < 2 FPS | < 3 FPS | < 5 FPS | < 3 FPS |

### 3. Tiêu chí 3: Dung lượng cài đặt và Tài nguyên hệ thống (Capacity & Resource Overhead)

AuEdu cực kỳ tối ưu về kích thước mã nguồn và tải bộ nhớ, an toàn tuyệt đối cho cấu hình văn phòng phổ thông.

- **Dung lượng mã nguồn:** Siêu nhẹ chỉ **8.10 MB** (Client code: 4.65 MB, Server code: 3.45 MB).
- **File đóng gói installer:** Client APK di động ~45 MB, Desktop Windows .exe ~80 MB. (Nhẹ hơn nhiều so với môi trường dlib của face_recognition > 200 MB).
- **Bộ nhớ RAM tiến trình:** Chỉ **~468.3 MB** lúc chờ (Idle) và giữ mức ổn định trung bình **~1209.1 MB** (đỉnh 1217.2 MB) lúc đang xử lý nhận diện liên tục.
- **Tài nguyên GPU & VRAM:** Tải GPU trung bình ~37.2% (đỉnh 95%), bộ nhớ VRAM chiếm dụng cực thấp **~999.1 MB** (trên tổng 4GB VRAM của card RTX 3050), giúp giải phóng CPU và tránh quá nhiệt hệ thống.

#### Chi tiết dung lượng và tài nguyên so sánh:

| Tiêu chí | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Dung lượng mã nguồn** | **~8.1 MB** | N/A (~500 MB) | N/A (~2 GB) | N/A (~1.5 GB) | N/A | N/A | N/A | N/A |
| **Độ cồng kềnh MT chạy** | **Nhẹ (ONNX)**| Cực lớn | Cực lớn | Cực lớn | Không có | Không có | Rất lớn (dlib)| Rất lớn (TF) |
| **Dung lượng file APK** | **~45 MB** | N/A | N/A | N/A | N/A | ~60 MB | N/A | N/A |
| **Dung lượng file Windows**| **~80 MB** | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **RAM tiến trình (đỉnh)** | **< 1.3 GB** | > 2 GB | > 4 GB | > 3 GB | Không tốn | Thấp | > 1.5 GB | > 2 GB |
| **Chi phí phần cứng** | **Không tốn** | 8-25tr VNĐ | 10-30tr VNĐ | 15-40tr VNĐ | API theo lượt | Thuê bao app | Không tốn | Không tốn |



---

## Tài liệu tham khảo (References)

| # | Tài liệu |
|:---|:---|
| [1] | J. Deng et al., "**ArcFace**: Additive Angular Margin Loss for Deep Face Recognition," *CVPR*, 2019. |
| [2] | S. Chen et al., "**MobileFaceNets**: Efficient CNNs for Real-Time Face Verification on Mobile," *CCBR*, 2018. |
| [3] | Z. Yu et al., "Searching **Central Difference Convolutional Networks** for Face Anti-Spoofing," *CVPR*, 2020. |
| [4] | S. Pertuz et al., "Analysis of **Focus Measure Operators** for Shape-from-Focus," *Pattern Recognition*, 2013. |
| [5] | G. B. Huang et al., "**Labeled Faces in the Wild**: A Database for Studying Face Recognition," *UMass*, 2007. |

---

## Thông tin tác giả (Author)

| | |
|:---|:---|
| **Họ tên** | **Nguyễn Chánh Hiệp** |
| **Vai trò** | Sinh viên năm 4 |
| **Khoa** | Trường Công nghệ số và Trí tuệ nhân tạo DNC |
| **Trường** | Trường Đại học Nam Cần Thơ (Nam Can Tho University) |
| **Mục đích** | Nghiên cứu khoa học & Luận văn tốt nghiệp |

---

## Đóng góp và Ủng hộ (Support)

Nếu dự án hữu ích, hãy nhấn Star cho kho lưu trữ (repository) này trên GitHub để dự án tiếp cận được nhiều người hơn.

Mọi đóng góp (issues, pull requests) đều được chào đón.

---

<p align="center">
  <i>AuEdu — Phần mềm điểm danh khuôn mặt AI mã nguồn mở cho giáo dục Việt Nam.<br>
  Open-source AI face recognition attendance system for Vietnamese education.</i>
</p>