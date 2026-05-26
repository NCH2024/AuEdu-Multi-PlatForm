# AuEdu — Hệ thống Điểm danh Khuôn mặt AI | AI Face Recognition Attendance System

<p align="center">
  <b>🌐 Language / Ngôn ngữ:</b>&nbsp;&nbsp;
  <a href="README.md">🇻🇳 Tiếng Việt</a> ·
  <a href="README.en.md">🇬🇧 English</a>
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

## 🔍 AuEdu là gì? (What is AuEdu?)

**AuEdu** (Automated Education) là phần mềm **điểm danh tự động bằng nhận diện khuôn mặt** (face recognition attendance system) mã nguồn mở, được thiết kế đặc biệt cho **trường học, đại học, và cơ sở giáo dục**. Thay vì sử dụng thiết bị chuyên dụng đắt tiền (8–40 triệu VNĐ), AuEdu chạy trực tiếp trên laptop/PC sẵn có với webcam thông thường.

### Tại sao chọn AuEdu?

| Vấn đề | Giải pháp của AuEdu |
|:---|:---|
| Thiết bị chấm công đắt đỏ (ZKTeco, Hikvision) | ✅ **Miễn phí** — chạy trên laptop sẵn có |
| Chỉ hỗ trợ 1 nền tảng | ✅ **5 nền tảng** — Windows, macOS, Android, iOS, Web |
| Dễ bị gian lận (ảnh, video) | ✅ **Anti-Spoofing AI** — MiniFASNet chặn 98% giả mạo |
| Ảnh mờ, backlight cho kết quả sai | ✅ **FIQA** — tự động lọc ảnh kém chất lượng |
| Độ chính xác thấp | ✅ **ArcFace 512-D** — Accuracy 98.75%, FAR = 0% |

### Tính năng chính (Key Features)

- 🎯 **Nhận diện khuôn mặt SOTA** — RetinaFace (detection) + ArcFace/MobileFaceNet (recognition) qua InsightFace `buffalo_s`
- 🛡️ **Chống giả mạo (Anti-Spoofing)** — MiniFASNet (Central Difference Convolution) chặn ảnh in, màn hình
- 📸 **Kiểm tra chất lượng ảnh (FIQA)** — Laplacian Variance lọc ảnh mờ, ngược sáng
- ⚡ **Real-time streaming** — WebSocket truyền frame < 30ms, vector search < 0.2ms
- 🔍 **Vector database** — pgvector (PostgreSQL) + In-memory Numpy Cache cho tìm kiếm O(1)
- 📱 **Đa nền tảng (Cross-platform)** — 1 codebase Python/Flet → 5 nền tảng
- 🆓 **Mã nguồn mở (Open-source)** — miễn phí cho mục đích giáo dục và nghiên cứu

---

## 🏗 Kiến trúc hệ thống (System Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                  📱 CLIENT (Flet Cross-Platform App)             │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Camera   │  │ MediaPipe │  │ WebSocket│  │  UI Pages    │  │
│  │ Capture  │──│ Face Det. │──│ Sender   │  │  (Dashboard, │  │
│  │ (30 FPS) │  │ (Client)  │  │ (base64) │  │   Register)  │  │
│  └──────────┘  └───────────┘  └────┬─────┘  └──────────────┘  │
└────────────────────────────────────┼────────────────────────────┘
                                     │ WebSocket (wss://)
┌────────────────────────────────────┼────────────────────────────┐
│              🖥 SERVER (FastAPI + Uvicorn + CUDA)                │
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

## ⚙️ Công nghệ sử dụng (Tech Stack)

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

## 📂 Cấu trúc dự án (Project Structure)

```
AuEdu-Multi-PlatForm/
│
├── Server/                          # 🖥 Back-end FastAPI
│   ├── app/
│   │   ├── ai/                      # 🧠 AI Core Engine
│   │   │   ├── engine.py            #   FaceEngine (RetinaFace + ArcFace + MiniFAS)
│   │   │   ├── attendance_cache.py  #   In-memory vector cache (Numpy)
│   │   │   └── models/              #   ONNX model files (auto-download)
│   │   ├── api/                     # 🔌 API Routes
│   │   │   ├── auth.py              #   JWT Authentication
│   │   │   ├── attendance.py        #   Điểm danh REST API
│   │   │   ├── websocket.py         #   WebSocket real-time handler
│   │   │   └── training.py          #   Đăng ký khuôn mặt (face enrollment)
│   │   ├── core/                    #   Cấu hình hệ thống (Settings)
│   │   ├── db/                      #   Database models (SQLAlchemy)
│   │   ├── services/                #   Business logic
│   │   └── main.py                  #   FastAPI entry point
│   ├── migrations/                  # Alembic DB migrations
│   ├── .env.example                 # 🔒 Mẫu cấu hình (không chứa secrets)
│   └── requirements.txt
│
├── Client/                          # 📱 Front-end Flet Cross-Platform App
│   ├── components/                  #   UI Components (Sidebar, Camera, ...)
│   ├── pages/                       #   Trang chức năng (Dashboard, Attendance, ...)
│   ├── core/                        #   Theme, Device Manager, API Config
│   ├── main.py                      #   Flet entry point
│   ├── .env.example                 # 🔒 Mẫu cấu hình client
│   └── requirements.txt
│
├── tests/                           # 🧪 Bộ kiểm thử (Test Suite)
│   ├── prepare_dataset.py           #   Tải & chuẩn bị LFW dataset tự động
│   ├── test_accuracy.py             #   Accuracy, Confusion Matrix, FIQA, Anti-Spoofing
│   ├── test_latency.py              #   Benchmark tốc độ pipeline AI
│   ├── test_resource_monitor.py     #   Giám sát CPU, RAM, GPU, VRAM
│   ├── test_vector_search.py        #   Benchmark Numpy vs pgvector
│   ├── generate_word_report.py      #   Tạo báo cáo Word (.docx) tự động
│   ├── dataset/                     # ⚠ Git-ignored (tự tải bằng script)
│   └── results/                     # ⚠ Git-ignored (tự sinh khi chạy test)
│
├── .gitignore
├── README.md                        # 🇻🇳 Tiếng Việt (file này)
└── README.en.md                     # 🇬🇧 English
```

---

## 🚀 Cài đặt & Chạy (Installation & Setup)

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

### 4. Cấu hình môi trường (`.env`) — ⚠️ BẮT BUỘC

> **🔒 Bảo mật:** File `.env` chứa secrets (API keys, mật khẩu database) và **KHÔNG được tải lên GitHub**.
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

> ⚠️ **KHÔNG bao giờ** commit file `.env` lên GitHub. Nếu vô tình push, hãy đổi mật khẩu ngay.

---

## 🧪 Kiểm thử hệ thống (Testing & Benchmarking)

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

## 📊 Kết quả thực nghiệm & So sánh thực tế (Evaluation & Comparative Analysis)

> Thực nghiệm thực tế trên **LFW dataset** (Labeled Faces in the Wild) — 1,906 ảnh, 20 người.
> Phần cứng máy test: AMD Ryzen 5 5600H + NVIDIA RTX 3050 Laptop GPU (4GB VRAM).

### 1. Tiêu chí 1: Tính ứng dụng & So sánh chức năng (Application & System Features)

AuEdu vượt trội về độ linh hoạt, khả năng bảo mật ngầm từ mã nguồn thực tế và tính hoàn thiện của phần mềm so với các giải pháp thương mại đắt đỏ hay thư viện thô.

| Tiêu chí | **AuEdu** (Đề xuất) | ZKTeco Terminal [10] | Hikvision MinMoe [11] | Suprema FaceStation [12] | FPT.AI eKYC [13] | VNPT vnFace | face_rec (dlib) [14] | DeepFace [15] |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Loại giải pháp** | Phần mềm mở | Phần cứng nhúng | Phần cứng nhúng | Phần cứng nhúng | Cloud API | Cloud App | Thư viện mở | Thư viện mở |
| **Chi phí ban đầu** | 🆓 **0 VNĐ** (chạy máy sẵn) | 💸 8–25 triệu VNĐ | 💸 10–30 triệu VNĐ | 💸 15–40 triệu VNĐ | Cloud (0 VNĐ) | Thấp (Thuê bao) | 🆓 0 VNĐ | 🆓 0 VNĐ |
| **Đa nền tảng** | ✅ **5 nền tảng** (Flet) | ❌ Thiết bị riêng | ❌ Thiết bị riêng | ❌ Thiết bị riêng | ✅ API đa nền tảng | ⚠ Mobile/Tablet | ⚠ Python duy nhất | ⚠ Python duy nhất |
| **Lọc chất lượng FIQA** | ✅ Laplacian Variance | ⚠ Tự động (nhúng) | ⚠ Tự động (nhúng) | ⚠ Tự động (nhúng) | ✅ Có hỗ trợ | ✅ Có hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Chống giả mạo AI** | ✅ MiniFAS RGB Liveness | ✅ IR Dual Cam | ✅ Structured Light | ✅ Visual + IR | ✅ Liveness API | ✅ Liveness API | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Hiệu chỉnh ống kính** | ✅ OpenCV Calibration | ✅ Cân chỉnh nhúng | ✅ Cân chỉnh nhúng | ✅ Cân chỉnh nhúng | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Hoạt động ngoại tuyến** | ✅ LAN / Local hoàn toàn | ✅ Standalone | ✅ Standalone | ✅ Standalone | ❌ Yêu cầu Internet | ❌ Yêu cầu Internet | ✅ Cục bộ | ✅ Cục bộ |
| **Real-time WebSocket** | ✅ WebSocket Stream | ✅ Tích hợp sẵn | ✅ Tích hợp sẵn | ✅ Tích hợp sẵn | ❌ API đồng bộ | ❌ API đồng bộ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **CSDL Vector chuyên dụng**| ✅ pgvector HNSW | N/A (Nhúng) | N/A (Nhúng) | N/A (Nhúng) | N/A (Cloud) | N/A (Cloud) | ❌ Brute-force | ❌ Brute-force |
| **Bộ nhớ đệm thông minh** | ✅ Numpy Cache O(1) | ✅ Trên RAM chip | ✅ Trên RAM chip | ✅ Trên RAM chip | N/A (Cloud) | N/A (Cloud) | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Định vị & Vị trí GPS** | ✅ OSM Nominatim Cache | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ⚠ Tọa độ thô | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Giám sát thời gian phiên**| ✅ Background Thread exp | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Đăng nhập thô | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Định danh thiết bị** | ✅ X-Device-ID Header | ✅ Serial / MAC | ✅ Serial / MAC | ✅ Serial / MAC | ❌ Không hỗ trợ | ✅ Có hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Bộ nhớ đệm Client 2 tầng**| ✅ Memory + Prefs Cache | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Đồng bộ URL tự động** | ✅ Public Config Sync | ❌ Không hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ | N/A (Cloud) | N/A (Cloud) | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Phân quyền RBAC** | ✅ Admin/GV/SV UI | ✅ Quyền thiết bị | ✅ Quyền thiết bị | ✅ Quyền thiết bị | ❌ Không hỗ trợ | ✅ Có hỗ trợ | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Tùy biến bảng màu** | ✅ Dark Mode + 4 Palettes| ❌ UI cố định | ❌ UI cố định | ❌ UI cố định | ❌ Không có UI | ❌ UI thương hiệu | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Quản trị học đường** | ✅ CRUD đầy đủ | ⚠ Chỉ Phòng ban | ⚠ Chỉ Phòng ban | ⚠ Chỉ Phòng ban | ❌ Không hỗ trợ | ⚠ Chỉ lớp/SV thô | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Thống kê đồ thị** | ✅ Flet Charts trực quan | ❌ Không hỗ trợ | ⚠ HikCentral phụ | ⚠ BioStar 2 phụ | ❌ Không hỗ trợ | ⚠ Đồ thị cơ bản | ❌ Không hỗ trợ | ❌ Không hỗ trợ |
| **Xuất báo cáo** | ✅ Excel / CSV | ✅ Excel/CSV/TXT | ✅ Excel / CSV | ✅ Excel/CSV/PDF | ❌ Không hỗ trợ | ✅ Excel / CSV | ❌ Không hỗ trợ | ❌ Không hỗ trợ |

### 2. Tiêu chí 2: Tốc độ xử lý & Độ trễ tác vụ (Speed & Latency)

Hệ thống đạt phản hồi giao diện tức thì (< 50ms nhờ Flutter Engine) và xử lý luồng ảnh qua WebSocket cực nhanh:

- **Tốc độ AI Pipeline (E2E):** **~38.00 ms** (Base64 decode: 0.72ms, Face Detection: 35.08ms, FIQA: 0.20ms, Anti-spoof: 3.94ms, ArcFace embedding: 35.55ms).
- **Thông lượng Throughput:** Đạt thực tế **21.56 FPS** khi stream ảnh liên tục.
- **Tốc độ so khớp sinh viên (Numpy Cache):** **< 0.2ms** đối với quy mô N = 1,000 sinh viên.

#### Chi tiết so sánh độ trễ & thông lượng giữa các hệ thống:

| Tiêu chí | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Độ trễ giao diện (UI)** | **< 50ms** | < 100ms | < 100ms | < 80ms | < 150ms | < 120ms | N/A | N/A |
| **Độ trễ mạng truyền tải** | **Thấp (WS)** | Thấp (TCP) | Thấp (TCP) | Thấp (TCP) | Cao (HTTP) | Cao (HTTP) | Không có | Không có |
| **Độ trễ trích xuất (Infer)**| **~35.5ms** | ~100-200ms | ~80-150ms | ~50-100ms | ~200-400ms | ~150-300ms | ~150-300ms | ~200-500ms |
| **Độ trễ so khớp Vector** | **< 0.2ms** | < 5ms | < 5ms | < 3ms | < 50ms | < 30ms | > 10ms | > 20ms |
| **Độ trễ toàn luồng E2E** | **~38.0ms** | < 300ms | < 300ms | < 200ms | > 500ms | > 400ms | > 200ms | > 300ms |
| **Thông lượng (FPS)** | **~21.5 FPS**| ~5-10 FPS | ~5-10 FPS | ~10-15 FPS| < 2 FPS | < 3 FPS | < 5 FPS | < 3 FPS |

### 3. Tiêu chí 3: Dung lượng cài đặt & Tài nguyên RAM/GPU (Capacity & Resource Overhead)

AuEdu cực kỳ tối ưu về kích thước mã nguồn và tải bộ nhớ, an toàn tuyệt đối cho cấu hình văn phòng phổ thông.

- **Dung lượng mã nguồn:** Siêu nhẹ chỉ **8.10 MB** (Client code: 4.65 MB, Server code: 3.45 MB).
- **File đóng gói installer:** Client APK di động ~45 MB, Desktop Windows .exe ~80 MB. (Nhẹ hơn nhiều so với môi trường dlib của face_recognition > 200 MB).
- **Bộ nhớ RAM tiến trình:** Chỉ **~468.3 MB** lúc chờ (Idle) và giữ mức ổn định trung bình **~1209.1 MB** (đỉnh 1217.2 MB) lúc đang xử lý nhận diện liên tục.
- **Tài nguyên GPU & VRAM:** Tải GPU trung bình ~37.2% (đỉnh 95%), bộ nhớ VRAM chiếm dụng cực thấp **~999.1 MB** (trên tổng 4GB VRAM của card RTX 3050), giúp giải phóng CPU và tránh quá nhiệt hệ thống.

#### Chi tiết dung lượng & tài nguyên so sánh:

| Tiêu chí | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Dung lượng mã nguồn** | **~8.1 MB** | N/A (~500M) | N/A (~2GB) | N/A (~1.5G) | N/A | N/A | N/A | N/A |
| **Độ cồng kềnh MT chạy** | **Nhẹ (ONNX)**| Cực lớn | Cực lớn | Cực lớn | Không có | Không có | Rất lớn (dlib)| Rất lớn (TF) |
| **Dung lượng file APK** | **~45 MB** | N/A | N/A | N/A | N/A | ~60 MB | N/A | N/A |
| **Dung lượng file Windows**| **~80 MB** | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **RAM tiến trình (đỉnh)** | **< 1.3 GB** | > 2 GB | > 4 GB | > 3 GB | Không tốn | Thấp | > 1.5 GB | > 2 GB |
| **Chi phí phần cứng** | **0 VNĐ** | 8-25tr VNĐ | 10-30tr VNĐ | 15-40tr VNĐ | API theo lượt | Thuê bao app | 0 VNĐ | 0 VNĐ |


---

## 📚 Tài liệu tham khảo (References)

| # | Tài liệu |
|:---|:---|
| [1] | J. Deng et al., "**ArcFace**: Additive Angular Margin Loss for Deep Face Recognition," *CVPR*, 2019. |
| [2] | S. Chen et al., "**MobileFaceNets**: Efficient CNNs for Real-Time Face Verification on Mobile," *CCBR*, 2018. |
| [3] | Z. Yu et al., "Searching **Central Difference Convolutional Networks** for Face Anti-Spoofing," *CVPR*, 2020. |
| [4] | S. Pertuz et al., "Analysis of **Focus Measure Operators** for Shape-from-Focus," *Pattern Recognition*, 2013. |
| [5] | G. B. Huang et al., "**Labeled Faces in the Wild**: A Database for Studying Face Recognition," *UMass*, 2007. |

---

## 👨‍💻 Tác giả (Author)

| | |
|:---|:---|
| **Họ tên** | **Nguyễn Chánh Hiệp** |
| **Vai trò** | Sinh viên năm 4 |
| **Khoa** | Trường Công nghệ số và Trí tuệ nhân tạo DNC |
| **Trường** | Trường Đại học Nam Cần Thơ (Nam Can Tho University) |
| **Mục đích** | Nghiên cứu khoa học & Luận văn tốt nghiệp |

---

## ⭐ Ủng hộ dự án (Support)

Nếu dự án hữu ích, hãy **⭐ Star** repo này trên GitHub — nó giúp dự án tiếp cận nhiều người hơn!

Mọi đóng góp (issues, pull requests) đều được chào đón.

---

<p align="center">
  <i>AuEdu — Phần mềm điểm danh khuôn mặt AI mã nguồn mở cho giáo dục Việt Nam.<br>
  Open-source AI face recognition attendance system for Vietnamese education.</i>
</p>