# 🎓 AuEdu — AI Face Attendance System

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

### AI Core

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
│   │   ├── ai/                      # AI Core Engine
│   │   │   ├── engine.py            #   FaceEngine (RetinaFace + ArcFace + MiniFAS)
│   │   │   ├── attendance_cache.py  #   In-memory vector cache (Numpy)
│   │   │   └── models/              #   ONNX model files (auto-download)
│   │   ├── api/                     # API Routes
│   │   │   ├── auth.py              #   Xác thực (JWT)
│   │   │   ├── attendance.py        #   Điểm danh REST API
│   │   │   ├── websocket.py         #   WebSocket real-time handler
│   │   │   └── training.py          #   Đăng ký khuôn mặt
│   │   ├── core/                    # Cấu hình (Settings, Config)
│   │   ├── db/                      # Database models & connection
│   │   ├── services/                # Business logic
│   │   └── main.py                  # FastAPI entry point
│   ├── migrations/                  # Alembic DB migrations
│   └── requirements.txt             # Python dependencies
│
├── Client/                          # 📱 Front-end Flet App
│   ├── components/                  # UI Components
│   │   ├── sidebar.py               #   Navigation sidebar
│   │   ├── topbar.py                #   Top navigation bar
│   │   └── camera_view.py           #   Camera stream component
│   ├── pages/                       # Các trang chức năng
│   │   ├── dashboard.py             #   Trang chủ
│   │   ├── attendance.py            #   Trang điểm danh
│   │   └── register_face.py         #   Đăng ký khuôn mặt
│   ├── core/                        # Theme, Device Manager, API
│   ├── main.py                      # Flet entry point
│   └── requirements.txt             # Client dependencies
│
├── tests/                           # 🧪 Bộ kiểm thử
│   ├── prepare_dataset.py           # Tải & chuẩn bị LFW dataset
│   ├── test_accuracy.py             # Kiểm thử accuracy, FIQA, anti-spoof
│   ├── test_latency.py              # Kiểm thử tốc độ pipeline
│   ├── test_resource_monitor.py     # Kiểm thử tài nguyên (CPU, RAM, GPU)
│   ├── test_vector_search.py        # Benchmark vector search
│   ├── generate_word_report.py      # Tạo báo cáo Word (.docx)
│   ├── dataset/                     # ⚠️ Không tải lên GitHub
│   │   └── .gitkeep
│   └── results/                     # ⚠️ Không tải lên GitHub
│       └── .gitkeep
│
├── .gitignore
└── README.md
```

> ⚠️ **Lưu ý:** Thư mục `tests/dataset/` và `tests/results/` chứa ảnh và kết quả nặng, **không được tải lên GitHub**. Chạy `prepare_dataset.py` để tự động tải dataset.

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
git clone https://github.com/<username>/AuEdu-Multi-PlatForm.git
cd AuEdu-Multi-PlatForm
```

### 2. Cài đặt Server

```bash
cd Server

# Tạo virtual environment
python -m venv venv

# Kích hoạt
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Cấu hình database
cp .env.example .env
# Chỉnh sửa .env với thông tin Supabase/PostgreSQL

# Chạy migrations
alembic upgrade head

# Khởi động server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Cài đặt Client

```bash
cd Client

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Chạy ứng dụng
flet run main.py

# Hoặc build APK (Android)
flet build apk
```

### 4. Cấu hình `.env`

**Server (`Server/.env`):**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-key
SECRET_KEY=your-secret-key
```

**Client (`Client/.env`):**
```env
API_BASE_URL=http://192.168.1.x:8000
WS_URL=ws://192.168.1.x:8000/ws
```

---

## 🧪 Kiểm thử hệ thống

### Tổng quan bộ kiểm thử

Bộ kiểm thử gồm **5 scripts** đánh giá toàn diện hệ thống:

| Script | Chức năng | Output |
|:---|:---|:---|
| `prepare_dataset.py` | Tải LFW dataset + sinh ảnh spoofing/blur | `tests/dataset/` |
| `test_accuracy.py` | Accuracy, FIQA, Anti-Spoofing, Confusion Matrix | `accuracy_report.json` |
| `test_latency.py` | Đo latency từng bước pipeline AI | `latency_report.json` |
| `test_resource_monitor.py` | Giám sát CPU, RAM, GPU, VRAM | `resource_report.json` |
| `test_vector_search.py` | Benchmark Numpy vs pgvector | `vector_search_report.json` |

### Bước 1: Chuẩn bị dataset

```bash
# Cài thư viện bổ sung (nếu chưa có)
pip install scikit-learn psutil

# Tải & chuẩn bị dataset LFW tự động
python tests/prepare_dataset.py
```

Script sẽ tự động:
1. **Tải LFW** từ scikit-learn (~200MB, cache lần sau)
2. **Chọn 20 người** có nhiều ảnh nhất → `registered/` (1,906 ảnh)
3. **Lấy 30 ảnh** người lạ → `unknown/`
4. **Sinh 50 ảnh mờ** → `blurred/` (Gaussian, Motion, Average Blur)
5. **Sinh 50 ảnh giả mạo** → `spoofing/` (Print Attack + Screen Attack)

> 💡 Chạy lại sẽ **tự động bỏ qua** nếu dataset đã tồn tại. Dùng `--force` để tải lại.

**Cấu trúc dataset sau khi chạy:**
```
tests/dataset/
├── registered/                  # 20 người × N ảnh/người
│   ├── person_001_George_W_Bush/
│   │   ├── enroll_001.jpg       # Ảnh đăng ký (gallery)
│   │   ├── probe_002.jpg        # Ảnh thử (query)
│   │   └── ...
│   └── person_020_.../
├── unknown/                     # 30 ảnh người lạ
├── blurred/                     # 50 ảnh mờ (FIQA test)
├── spoofing/
│   ├── print_attack/            # 25 ảnh giả lập in giấy
│   └── screen_attack/           # 25 ảnh giả lập màn hình
└── dataset_metadata.json        # Metadata + trích dẫn IEEE
```

### Bước 2: Chạy kiểm thử

```bash
# Kích hoạt venv Server (vì cần InsightFace)
cd Server
venv\Scripts\activate

# ── Test Accuracy (bao gồm FIQA + Anti-Spoofing) ──
python ../tests/test_accuracy.py --dataset ../tests/dataset
# Output: tests/results/accuracy_report.json
#         tests/results/accuracy_summary.csv

# ── Test Latency ──
python ../tests/test_latency.py --iterations 50
# Output: tests/results/latency_report.json

# ── Test Resource Monitor ──
python ../tests/test_resource_monitor.py --duration 30
# Output: tests/results/resource_report.json

# ── Test Vector Search ──
python ../tests/test_vector_search.py
# Output: tests/results/vector_search_report.json
```

### Bước 3: Tạo báo cáo Word

```bash
# Cài python-docx (nếu chưa có)
pip install python-docx

# Tạo file .docx với số liệu thực
python tests/generate_word_report.py
# Output: tests/results/THUC_NGHIEM_AUEDU.docx
```

### Tùy chỉnh kiểm thử

```bash
# Tùy chỉnh dataset
python tests/prepare_dataset.py --num-registered 30 --num-blur 100 --force

# Tùy chỉnh accuracy test
python ../tests/test_accuracy.py --dataset ../tests/dataset --threshold 0.50

# Tùy chỉnh latency test
python ../tests/test_latency.py --iterations 100 --image path/to/image.jpg

# Test vector search với PostgreSQL
python ../tests/test_vector_search.py --db-url "postgresql://user:pass@localhost:5432/db"
```

---

## 📊 Kết quả thực nghiệm

> Kết quả benchmark trên LFW dataset, chạy trên AMD Ryzen 5 5600H + RTX 3050 (4GB VRAM)

### Độ chính xác nhận diện

| Chỉ số | Kết quả | Ghi chú |
|:---|:---|:---|
| **Face Detection Rate** | 99.79% | 1,902/1,906 ảnh |
| **Accuracy** | 98.75% | Tại ngưỡng 0.45 |
| **FAR** (False Acceptance Rate) | **0.00%** | Không nhận nhầm |
| **FRR** (False Rejection Rate) | 25.35% | Tại ngưỡng 0.45 |
| **F1-Score (best)** | **99.33%** | Tại ngưỡng 0.60 |
| **Precision** | **100%** | TP = 1,405; FP = 0 |

### Phân tích ngưỡng

| Threshold | Accuracy | FAR | FRR | F1-Score |
|:---|:---|:---|:---|:---|
| 0.30 | 95.72% | 0% | 86.93% | 23.12% |
| 0.35 | 96.43% | 0% | 72.58% | 43.04% |
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
| FIQA false positive | 0.42% (8/1,902) |

### Vector Search Performance

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
| **Đơn vị** | Sinh viên năm 4, Ngành Kỹ thuật Phần mềm |
| **Trường** | Đại học Nam Cần Thơ (DNC) |
| **Mục đích** | Nghiên cứu khoa học & Luận văn tốt nghiệp |

---

<p align="center">
  <i>Dự án phục vụ mục đích nghiên cứu và phát triển học thuật.</i>
</p>