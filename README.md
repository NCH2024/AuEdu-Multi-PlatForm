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

## 📊 Kết quả thực nghiệm (Benchmark Results)

> Benchmark trên **LFW dataset** (Labeled Faces in the Wild) — 1,906 ảnh, 20 người
> Phần cứng: AMD Ryzen 5 5600H + NVIDIA RTX 3050 (4GB VRAM)

### Độ chính xác nhận diện khuôn mặt (Face Recognition Accuracy)

| Chỉ số | Kết quả | Đánh giá |
|:---|:---|:---|
| **Face Detection Rate** | 99.79% (1,902/1,906) | ✅ Xuất sắc |
| **Recognition Accuracy** | **98.75%** (threshold 0.45) | ✅ Rất tốt |
| **FAR** (False Acceptance Rate) | **0.00%** — không nhận nhầm | ✅ Hoàn hảo |
| **F1-Score (best)** | **99.33%** (threshold 0.60) | ✅ Xuất sắc |
| **Precision** | **100%** | ✅ Hoàn hảo |
| **Embedding extraction** | 29.71 ms/ảnh | ✅ Real-time |

### Phân tích ngưỡng nhận diện (Threshold Analysis)

| Threshold | Accuracy | FAR | FRR | F1-Score | Ghi chú |
|:---|:---|:---|:---|:---|:---|
| 0.30 | 95.72% | 0% | 86.93% | 23.12% | Quá chặt |
| 0.40 | 97.58% | 0% | 49.10% | 67.46% | |
| **0.45** | **98.75%** | **0%** | **25.35%** | **85.49%** | ⬅️ Mặc định |
| 0.50 | 99.55% | 0% | 9.19% | 95.18% | Cân bằng tốt |
| 0.55 | 99.86% | 0% | 2.92% | 98.52% | |
| **0.60** | **99.93%** | **0%** | **1.33%** | **99.33%** | ⭐ F1 tốt nhất |

### Chống giả mạo & Lọc chất lượng ảnh (Anti-Spoofing & FIQA)

| Test | Kết quả |
|:---|:---|
| 🖨️ Print Attack blocked | **96%** (24/25) |
| 📱 Screen Attack blocked | **100%** (25/25) |
| 📸 FIQA lọc ảnh mờ (ngưỡng 0.10) | **90%** (45/50) |
| FIQA false positive | 0.42% (8/1,902) |

### Tốc độ truy vấn Vector (Vector Search Performance)

| N vectors | Avg latency | P95 latency | Đánh giá |
|:---|:---|:---|:---|
| 50 | 0.135 ms | 0.199 ms | ✅ Real-time |
| 100 | 0.153 ms | 0.252 ms | ✅ Real-time |
| 500 | 0.123 ms | 0.176 ms | ✅ Real-time |
| 1,000 | 0.161 ms | 0.219 ms | ✅ Real-time |

### So sánh với các giải pháp trên thị trường

| Tiêu chí | **AuEdu** | ZKTeco | Hikvision | face_recognition |
|:---|:---|:---|:---|:---|
| **Chi phí** | **0 VNĐ** | 8–25 triệu | 10–30 triệu | 0 VNĐ |
| **Đa nền tảng** | ✅ 5 nền tảng | ❌ Terminal | ❌ Terminal | ⚠ Python only |
| **Anti-Spoofing** | ✅ MiniFASNet | ✅ IR Dual | ✅ Structured | ❌ Không |
| **Accuracy (LFW)** | 98.75% | N/A | ~99% | ~99.38% |
| **Real-time** | ✅ WebSocket | ✅ | ✅ | ❌ |
| **Vector DB** | ✅ pgvector | N/A | N/A | ❌ |
| **Mã nguồn mở** | ✅ | ❌ | ❌ | ✅ |

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