# AuEdu — AI Face Recognition Attendance System | Open-Source Cross-Platform

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

> **Open-source real-time face recognition attendance system for education**, powered by ArcFace + Anti-Spoofing + FIQA. Runs on **5 platforms** (Windows, Android, iOS, macOS, Web) from a single Python codebase. **Zero additional hardware cost** — just use your existing laptop.

---

## 🔍 What is AuEdu?

**AuEdu** (Automated Education) is an open-source **face recognition attendance system** specifically designed for **schools, universities, and educational institutions**. Instead of expensive dedicated hardware ($300–$1,500), AuEdu runs directly on existing laptops/PCs with a standard webcam.

### Why AuEdu?

| Problem | AuEdu's Solution |
|:---|:---|
| Expensive attendance terminals (ZKTeco, Hikvision) | ✅ **Free** — runs on existing hardware |
| Single-platform only | ✅ **5 platforms** — Windows, macOS, Android, iOS, Web |
| Easy to cheat (photos, videos) | ✅ **Anti-Spoofing AI** — MiniFASNet blocks 98% of attacks |
| Blurry/backlit images → wrong results | ✅ **FIQA** — auto-filters low quality images |
| Low accuracy | ✅ **ArcFace 512-D** — 98.75% Accuracy, 0% FAR |

### Key Features

- 🎯 **SOTA Face Recognition** — RetinaFace (detection) + ArcFace/MobileFaceNet (recognition) via InsightFace `buffalo_s`
- 🛡️ **Anti-Spoofing** — MiniFASNet (Central Difference Convolution) blocks print & screen attacks
- 📸 **Face Image Quality Assessment (FIQA)** — Laplacian Variance filters blurry images
- ⚡ **Real-time streaming** — WebSocket frame delivery < 30ms, vector search < 0.2ms
- 🔍 **Vector database** — pgvector (PostgreSQL) + In-memory Numpy Cache for O(1) lookup
- 📱 **Cross-platform** — 1 Python/Flet codebase → 5 platforms
- 🆓 **Open-source** — free for education and research

---

## 🏗 System Architecture

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

## ⚙️ Tech Stack

### Back-end Server

| Technology | Version | Role |
|:---|:---|:---|
| **Python** | 3.10 | Primary language |
| **FastAPI** | 0.135.1 | REST API + WebSocket framework |
| **Uvicorn** | 0.41.0 | ASGI Server |
| **SQLAlchemy** | 2.0.30 | ORM |
| **PostgreSQL + pgvector** | 16.x + ≥ 0.2.5 | Database + Vector Search |
| **Supabase** | — | Backend-as-a-Service |

### AI Core Engine

| Technology | Model | Role |
|:---|:---|:---|
| **InsightFace** | `buffalo_s` | RetinaFace + MobileFaceNet |
| **MiniFASNet** | `modelrgb.onnx` | Anti-Spoofing (CDC) |
| **ONNX Runtime** | GPU (CUDA 12.x) | Inference Engine |
| **OpenCV** | ≥ 4.8.0 | Image processing |

### Front-end Client

| Technology | Version | Role |
|:---|:---|:---|
| **Flet** | 0.85.0 | Cross-platform UI (Flutter-based) |
| **MediaPipe** | — | Client-side face detection |

---

## 🚀 Installation & Setup

### System Requirements

| Component | Minimum | Recommended |
|:---|:---|:---|
| **CPU** | 4 cores | 6+ cores |
| **RAM** | 4 GB | 8+ GB |
| **GPU** | Not required (CPU mode) | NVIDIA GPU with CUDA |
| **Python** | 3.10 | 3.10 |
| **OS** | Windows 10 / Ubuntu 20.04 | Windows 11 |

### Quick Start

```bash
# 1. Clone
git clone https://github.com/NCH2024/AuEdu-Multi-PlatForm.git
cd AuEdu-Multi-PlatForm

# 2. Server
cd Server
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env  # Edit with your Supabase credentials
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Client
cd ../Client
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your Supabase credentials
flet run main.py
```

### Environment Configuration (`.env`) — ⚠️ REQUIRED

> **🔒 Security:** `.env` files contain secrets and are **NOT on GitHub**. Only `.env.example` templates are provided.

1. **Copy templates:** `cp Server/.env.example Server/.env && cp Client/.env.example Client/.env`
2. **Create Supabase project** at [supabase.com](https://supabase.com) (free)
3. **Fill in credentials** from Supabase Dashboard → Settings → API
4. **Enable pgvector:** Run `CREATE EXTENSION IF NOT EXISTS vector;` in SQL Editor

---

## 🧪 Testing & Benchmarking

| Script | Function | Output |
|:---|:---|:---|
| `prepare_dataset.py` | Download LFW + generate spoofing/blur | `tests/dataset/` |
| `test_accuracy.py` | Accuracy, Confusion Matrix, FIQA, Anti-Spoofing | `accuracy_report.json` |
| `test_latency.py` | AI pipeline latency benchmark | `latency_report.json` |
| `test_resource_monitor.py` | CPU, RAM, GPU monitoring | `resource_report.json` |
| `test_vector_search.py` | Numpy vs pgvector benchmark | `vector_search_report.json` |

```bash
python tests/prepare_dataset.py              # Auto-download LFW (~200MB)
cd Server && venv\Scripts\activate
python ../tests/test_accuracy.py --dataset ../tests/dataset
python ../tests/test_vector_search.py
```

---

## 📊 Evaluation & Comparative Analysis

> Real-world benchmark on **LFW dataset** (Labeled Faces in the Wild) — 1,906 images, 20 identities.
> Test Hardware: AMD Ryzen 5 5600H + NVIDIA RTX 3050 Laptop GPU (4GB VRAM).

### 1. Criterion 1: Application & Feature Comparison (Application)

AuEdu offers superior flexibility and complete administrative features compared to expensive commercial solutions and bare libraries.

| Criteria | **AuEdu** (Proposed) | ZKTeco Terminal | Hikvision Terminal | face_recognition (dlib) |
|:---|:---|:---|:---|:---|
| **Hardware Cost** | 🆓 **$0** (runs on existing PC) | 💸 $300–1,000 | 💸 $400–1,500 | 🆓 $0 |
| **Cross-platform** | ✅ **5 platforms** (Windows, macOS, Linux, Android, iOS) | ❌ Proprietary device only | ❌ Proprietary device only | ⚠ Python script only |
| **Anti-Spoofing AI** | ✅ MiniFASNet (RGB liveness) | ✅ IR Dual Cam | ✅ Structured Light | ❌ Not supported |
| **FIQA Quality Filter** | ✅ Laplacian Variance | ⚠ Automatic (embedded) | ⚠ Automatic (embedded) | ❌ Not supported |
| **Class/Student CRUD** | ✅ Complete UI Management | ⚠ Basic config | ⚠ Central software | ❌ Not supported |
| **Security Audit Logs** | ✅ IP & User-Agent logging | ⚠ Basic history logs | ✅ Supported | ❌ Not supported |
| **Vector Database** | ✅ pgvector HNSW + Numpy Cache | N/A (Embedded) | N/A (Embedded) | ❌ Brute-force |
| **Offline Operation** | ✅ Full offline/local hosting | ✅ Standalone | ✅ Standalone | ✅ Local |

### 2. Criterion 2: Processing Speed & Task Latency (Speed)

The system achieves instant UI response (< 50ms powered by Flutter Engine) and ultra-fast frame processing via WebSockets:

- **AI Pipeline Latency (E2E):** **~38.00 ms** (Base64 decode: 0.72ms, Face Detection: 35.08ms, FIQA: 0.20ms, Anti-spoof: 3.94ms, ArcFace embedding: 35.55ms).
- **Throughput:** Real-world **21.56 FPS** under continuous frame streaming.
- **Match Latency (Numpy Cache):** **< 0.2ms** for class matching scale of N = 1,000.

#### Detailed Latency Stats per Processing Step (N = 50):

| Step | Avg (ms) | Min (ms) | Max (ms) | P95 (ms) |
|:---|:---|:---|:---|:---|
| **1. Base64 Decode** | 0.72 ms | 0.51 ms | 2.15 ms | 0.92 ms |
| **2. Face Detection (RetinaFace)** | 35.08 ms | 29.13 ms | 54.50 ms | 41.68 ms |
| **3. FIQA Evaluation (Laplacian)** | 0.20 ms | 0.13 ms | 0.42 ms | 0.33 ms |
| **4. Anti-Spoof (MiniFASNet)** | 3.94 ms | 2.48 ms | 8.20 ms | 5.18 ms |
| **5. Embedding Extract (ArcFace)** | 35.55 ms | 31.19 ms | 46.58 ms | 42.37 ms |
| **6. Full Pipeline (E2E)** | **38.00 ms** | 32.65 ms | 49.98 ms | 48.37 ms |

### 3. Criterion 3: Installation Size & System Resources (Capacity)

AuEdu is highly optimized for codebase size and memory footprint, making it extremely safe for standard office PCs.

- **Codebase Size:** Lightweight **8.10 MB** (Client code: 4.65 MB, Server code: 3.45 MB).
- **Package Installer:** Client mobile APK ~45 MB, Desktop Windows .exe ~80 MB. (Much lighter than face_recognition's > 200 MB dlib runtime).
- **Process Memory (RAM):** Only **~468.3 MB** when Idle, and stays at **~1209.1 MB** (Peak: 1217.2 MB) during active processing.
- **GPU & VRAM Usage:** Avg GPU load ~37.2% (Peak: 95.0%), VRAM consumption is extremely low at **~999.1 MB** (out of 4GB on RTX 3050), freeing up system CPU and preventing overheating.

---

## 📚 References

| # | Reference |
|:---|:---|
| [1] | J. Deng et al., "**ArcFace**: Additive Angular Margin Loss for Deep Face Recognition," *CVPR*, 2019. |
| [2] | S. Chen et al., "**MobileFaceNets**: Efficient CNNs for Real-Time Face Verification on Mobile," *CCBR*, 2018. |
| [3] | Z. Yu et al., "Searching **Central Difference Convolutional Networks** for Face Anti-Spoofing," *CVPR*, 2020. |
| [4] | S. Pertuz et al., "Analysis of **Focus Measure Operators** for Shape-from-Focus," *Pattern Recognition*, 2013. |
| [5] | G. B. Huang et al., "**Labeled Faces in the Wild**," *UMass Amherst*, 2007. |

---

## 👨‍💻 Author

| | |
|:---|:---|
| **Name** | **Nguyen Chanh Hiep** |
| **Role** | 4th-year undergraduate student |
| **Faculty** | School of Digital Technology and Artificial Intelligence (DNC) |
| **University** | Nam Can Tho University, Vietnam |
| **Purpose** | Scientific research & Graduation thesis |

---

## ⭐ Support

If this project is useful, please **⭐ Star** this repo — it helps more people discover it!

Contributions (issues, pull requests) are welcome.

---

<p align="center">
  <i>AuEdu — Open-source AI face recognition attendance system for education.<br>
  Phần mềm điểm danh khuôn mặt AI mã nguồn mở cho giáo dục.</i>
</p>
