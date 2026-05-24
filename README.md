# 🎓 AuEdu — AI Face Attendance System

<p align="center">
  <b>🌐 Language / Ngôn ngữ:</b>&nbsp;&nbsp;
  <a href="README.md">🇻🇳 Tiếng Việt</a> ·
  <a href="README.en.md">🇬🇧 English</a>
</p>

> **Hệ thống điểm danh khuôn mặt thời gian thực dành cho giáo dục**
> Sử dụng ArcFace + Anti-Spoofing + FIQA | Đa nền tảng (Windows, Android, iOS, macOS, Web)

[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135.1-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Flet](https://img.shields.io/badge/Flet-0.85.0-02569B?logo=flutter)](https://flet.dev)
[![License](https://img.shields.io/badge/License-Academic-yellow)]()

---

## 📋 Mục lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Cài đặt & Chạy](#-cài-đặt--chạy)
- [Kiểm thử hệ thống](#-kiểm-thử-hệ-thống)
- [Kết quả thực nghiệm](#-kết-quả-thực-nghiệm)
- [Tác giả](#-tác-giả)

---

## 🔍 Tổng quan

AuEdu là hệ thống điểm danh tự động sử dụng **nhận diện khuôn mặt AI** được thiết kế cho môi trường giáo dục. Hệ thống kết hợp nhiều lớp xử lý:

| Lớp | Công nghệ | Chức năng |
|:---|:---|:---|
| **Face Detection** | RetinaFace [1] | Phát hiện khuôn mặt real-time |
| **Face Recognition** | ArcFace / MobileFaceNet [2] | Trích xuất embedding 512-D, so khớp danh tính |
| **Anti-Spoofing** | MiniFASNet (CDC) [3] | Chống giả mạo (ảnh in, màn hình) |
| **FIQA** | Laplacian Variance [4] | Lọc ảnh mờ trước khi nhận diện |
| **Vector Search** | pgvector HNSW + Numpy Cache | Tìm kiếm vector < 0.2ms |
| **Real-time** | WebSocket + Async Queue | Truyền frame độ trễ thấp |

### Điểm nổi bật

- ✅ **Chi phí triển khai = 0 VNĐ** — chạy trên laptop/PC sẵn có
- ✅ **Đa nền tảng** — 1 codebase Python → Windows, macOS, Android, iOS, Web
- ✅ **FAR = 0%** — không nhận nhầm người lạ (trên 36,358 cặp impostor)
- ✅ **Accuracy 98.75%** — benchmark trên LFW dataset chuẩn quốc tế
- ✅ **Anti-spoofing 98%** — chặn 49/50 ảnh giả mạo
- ✅ **Real-time** — embedding < 30ms, vector search < 0.2ms

---

## 🏗 Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Flet App)                        │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Camera   │  │ MediaPipe │  │ WebSocket│  │  UI Pages    │  │
│  │ Capture  │──│ Face Det. │──│ Sender   │  │  (Dashboard, │  │
│  │ (30 FPS) │  │ (Client)  │  │ (base64) │  │   Register)  │  │
│  └──────────┘  └───────────┘  └────┬─────┘  └──────────────┘  │
└────────────────────────────────────┼────────────────────────────┘
                                     │ WebSocket (wss://)
┌────────────────────────────────────┼────────────────────────────┐
│                     SERVER (FastAPI + Uvicorn)                   │
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
│  │  In-memory Cache     │  │  PostgreSQL + pgvector          │  │
│  │  (Numpy dot product) │  │  HNSW Index, cosine_distance    │  │
│  │  < 0.2ms lookup      │  │  Persistent storage             │  │
│  └──────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Công nghệ sử dụng

### Back-end (Server)

| Công nghệ | Phiên bản | Vai trò |
|:---|:---|:---|
| Python | 3.10 | Ngôn ngữ chính |
| FastAPI | 0.135.1 | REST API + WebSocket |
| Uvicorn | 0.41.0 | ASGI Server |
| SQLAlchemy | 2.0.30 | ORM |
| Alembic | — | Database migrations |
| PostgreSQL + pgvector | 16.x + ≥ 0.2.5 | CSDL + Vector Search |

### Lõi AI (AI Core)

| Công nghệ | Model | Vai trò |
|:---|:---|:---|
| InsightFace | `buffalo_s` | RetinaFace + MobileFaceNet |
| MiniFASNet | `modelrgb.onnx` | Anti-Spoofing (CDC) |
| ONNX Runtime | GPU (CUDA 12.x) | Inference Engine |
| OpenCV | ≥ 4.8.0 | Xử lý ảnh |

### Front-end (Client)

| Công nghệ | Phiên bản | Vai trò |
|:---|:---|:---|
| Flet | 0.85.0 | UI đa nền tảng (Flutter-based) |
| MediaPipe | — | Face Detection phía client |

---

## 📂 Cấu trúc dự án

```
AuEdu-Multi-PlatForm/
│
├── Server/                          # 🖥 Back-end FastAPI
│   ├── app/
│   │   ├── ai/                      # Lõi xử lý AI
│   │   │   ├── engine.py            #   FaceEngine chính
│   │   │   ├── attendance_cache.py  #   In-memory vector cache
│   │   │   └── models/              #   ONNX models (tự tải)
│   │   ├── api/                     # API Routes
│   │   │   ├── auth.py              #   Xác thực (JWT)
│   │   │   ├── attendance.py        #   Điểm danh REST
│   │   │   ├── websocket.py         #   WebSocket handler
│   │   │   └── training.py          #   Đăng ký khuôn mặt
│   │   ├── core/                    # Cấu hình hệ thống
│   │   ├── db/                      # Database models
│   │   ├── services/                # Business logic
│   │   └── main.py                  # Entry point
│   ├── migrations/                  # Alembic migrations
│   └── requirements.txt
│
├── Client/                          # 📱 Front-end Flet App
│   ├── components/                  # UI Components
│   ├── pages/                       # Các trang chức năng
│   ├── core/                        # Theme, Config
│   ├── main.py                      # Entry point
│   └── requirements.txt
│
├── tests/                           # 🧪 Bộ kiểm thử
│   ├── prepare_dataset.py           # Tải & chuẩn bị LFW dataset
│   ├── test_accuracy.py             # Accuracy, FIQA, Anti-Spoofing
│   ├── test_latency.py              # Benchmark tốc độ
│   ├── test_resource_monitor.py     # Giám sát tài nguyên
│   ├── test_vector_search.py        # Benchmark vector search
│   ├── generate_word_report.py      # Tạo báo cáo Word
│   ├── dataset/                     # ⚠ Không tải lên GitHub
│   └── results/                     # ⚠ Không tải lên GitHub
│
├── .gitignore
└── README.md
```

> ⚠️ Thư mục `tests/dataset/` và `tests/results/` chứa ảnh và kết quả nặng, **không được tải lên GitHub**. Chạy `prepare_dataset.py` để tự động tải dataset.

---

## 🚀 Cài đặt & Chạy

### Yêu cầu hệ thống

| Thành phần | Tối thiểu | Khuyến nghị |
|:---|:---|:---|
| CPU | 4 cores | 6+ cores |
| RAM | 4 GB | 8+ GB |
| GPU | Không bắt buộc | NVIDIA GPU (CUDA) |
| Python | 3.10 | 3.10 |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 |

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

# Cấu hình database
cp .env.example .env
# Chỉnh sửa .env với thông tin PostgreSQL/Supabase

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

# Build APK (Android):
flet build apk
```

### 4. Cấu hình môi trường (`.env`) — ⚠️ BẮT BUỘC

> **🔒 Bảo mật:** File `.env` chứa secrets (API keys, mật khẩu database) và **KHÔNG được tải lên GitHub**.
> Dự án chỉ cung cấp file `.env.example` làm mẫu. Bạn cần tạo `.env` riêng.

**Bước 1:** Copy file mẫu

```bash
# Server
cd Server
cp .env.example .env

# Client
cd ../Client
cp .env.example .env
```

**Bước 2:** Tạo project Supabase (miễn phí)

1. Truy cập [supabase.com](https://supabase.com) → **Start your project** (đăng nhập bằng GitHub)
2. **New project** → Đặt tên + mật khẩu database → Chọn region `Southeast Asia`
3. Lấy thông tin kết nối tại **Settings → API**:

| Thông tin | Lấy ở đâu | Điền vào |
|:---|:---|:---|
| `SUPABASE_URL` | Settings → API → Project URL | `Server/.env` + `Client/.env` |
| `SUPABASE_KEY` | Settings → API → `anon` `public` key | `Server/.env` + `Client/.env` |
| `DATABASE_URL` | Settings → Database → Connection string → URI | `Server/.env` |

**Bước 3:** Chỉnh sửa `.env`

**Server (`Server/.env`):**
```env
# Thay bằng thông tin thật từ Supabase Dashboard
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGci...your-anon-key...
SUPABASE_STORAGE_BUCKET=thongbao_images

# Thay user, password, host từ Supabase → Database → Connection string
DATABASE_URL=postgresql+asyncpg://postgres:your-password@db.your-project-id.supabase.co:5432/postgres

# Giữ nguyên (không cần thay đổi)
FIQA_THRESHOLD=0.05
ANTI_SPOOF_MODEL=modelrgb.onnx
MAX_QUEUE_SIZE=8
DROP_OLDEST=true
CALIBRATION_MODE=auto
CALIBRATION_DATA=calib.npy
```

**Client (`Client/.env`):**
```env
# Phải trùng với Server/.env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGci...your-anon-key...
SUPABASE_STORAGE_BUCKET=thongbao_images
```

**Bước 4:** Kích hoạt extension pgvector trên Supabase

```sql
-- Chạy trong Supabase SQL Editor (Database → SQL Editor)
CREATE EXTENSION IF NOT EXISTS vector;
```

> ⚠️ **Lưu ý bảo mật:**
> - **KHÔNG bao giờ** commit file `.env` lên GitHub
> - File `.env` đã được thêm vào `.gitignore`
> - Nếu vô tình push secrets, hãy đổi mật khẩu Supabase ngay lập tức
> - Chỉ sử dụng key `anon/public` cho client, **KHÔNG dùng** `service_role` key

---

## 🧪 Kiểm thử hệ thống

### Tổng quan

| Script | Chức năng | Output |
|:---|:---|:---|
| `prepare_dataset.py` | Tải LFW + sinh ảnh spoofing/blur | `tests/dataset/` |
| `test_accuracy.py` | Accuracy, FIQA, Anti-Spoofing | `accuracy_report.json` |
| `test_latency.py` | Đo latency pipeline AI | `latency_report.json` |
| `test_resource_monitor.py` | CPU, RAM, GPU, VRAM | `resource_report.json` |
| `test_vector_search.py` | Numpy vs pgvector benchmark | `vector_search_report.json` |

### Bước 1: Chuẩn bị dataset

```bash
pip install scikit-learn psutil
python tests/prepare_dataset.py
```

> 💡 Chạy lại sẽ tự động bỏ qua nếu dataset đã tồn tại. Dùng `--force` để tải lại.

### Bước 2: Chạy kiểm thử

```bash
cd Server
venv\Scripts\activate

# Accuracy + FIQA + Anti-Spoofing
python ../tests/test_accuracy.py --dataset ../tests/dataset

# Latency
python ../tests/test_latency.py --iterations 50

# Resource Monitor
python ../tests/test_resource_monitor.py --duration 30

# Vector Search
python ../tests/test_vector_search.py
```

### Bước 3: Tạo báo cáo Word

```bash
pip install python-docx
python tests/generate_word_report.py
# Output: tests/results/THUC_NGHIEM_AUEDU.docx
```

---

## 📊 Kết quả thực nghiệm

> Benchmark trên LFW dataset · AMD Ryzen 5 5600H + RTX 3050 (4GB)

### Độ chính xác nhận diện

| Chỉ số | Kết quả |
|:---|:---|
| **Face Detection Rate** | 99.79% (1,902/1,906) |
| **Accuracy** | 98.75% (ngưỡng 0.45) |
| **FAR** (nhận nhầm) | **0.00%** |
| **F1-Score (best)** | **99.33%** (ngưỡng 0.60) |
| **Precision** | **100%** |

### Phân tích ngưỡng

| Threshold | Accuracy | FAR | FRR | F1-Score |
|:---|:---|:---|:---|:---|
| 0.30 | 95.72% | 0% | 86.93% | 23.12% |
| 0.40 | 97.58% | 0% | 49.10% | 67.46% |
| **0.45** ⬅️ | **98.75%** | **0%** | **25.35%** | **85.49%** |
| 0.50 | 99.55% | 0% | 9.19% | 95.18% |
| 0.55 | 99.86% | 0% | 2.92% | 98.52% |
| **0.60** ⭐ | **99.93%** | **0%** | **1.33%** | **99.33%** |

### Anti-Spoofing & FIQA

| Test | Kết quả |
|:---|:---|
| Print Attack blocked | **96%** (24/25) |
| Screen Attack blocked | **100%** (25/25) |
| FIQA lọc ảnh mờ (ngưỡng 0.10) | **90%** (45/50) |

### Vector Search

| N vectors | Avg latency | P95 latency |
|:---|:---|:---|
| 50 | 0.135 ms | 0.199 ms |
| 100 | 0.153 ms | 0.252 ms |
| 500 | 0.123 ms | 0.176 ms |
| 1,000 | 0.161 ms | 0.219 ms |

---

## 📚 Tài liệu tham khảo

| # | Tài liệu |
|:---|:---|
| [1] | J. Deng et al., "ArcFace: Additive Angular Margin Loss for Deep Face Recognition," CVPR, 2019. |
| [2] | S. Chen et al., "MobileFaceNets: Efficient CNNs for Real-Time Face Verification on Mobile," CCBR, 2018. |
| [3] | Z. Yu et al., "Searching Central Difference Convolutional Networks for Face Anti-Spoofing," CVPR, 2020. |
| [4] | S. Pertuz et al., "Analysis of Focus Measure Operators for Shape-from-Focus," Pattern Recognition, 2013. |
| [5] | G. B. Huang et al., "Labeled Faces in the Wild," UMass Amherst, Tech. Rep. 07-49, 2007. |

---

## 👨‍💻 Tác giả

| | |
|:---|:---|
| **Họ tên** | Nguyễn Chánh Hiệp |
| **Vai trò** | Sinh viên năm 4 |
| **Khoa** | Trường Công nghệ số và Trí tuệ nhân tạo DNC |
| **Trường** | Trường Đại học Nam Cần Thơ |
| **Mục đích** | Nghiên cứu khoa học & Luận văn tốt nghiệp |

---

<p align="center">
  <i>Dự án phục vụ mục đích nghiên cứu và phát triển học thuật.</i>
</p>