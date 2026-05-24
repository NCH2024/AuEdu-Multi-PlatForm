# 🎓 AuEdu — AI Face Attendance System

<p align="center">
  <b>🌐 Language / Ngôn ngữ:</b>&nbsp;&nbsp;
  <a href="README.md">🇻🇳 Tiếng Việt</a> ·
  <a href="README.en.md">🇬🇧 English</a>
</p>

> **Real-time Face Recognition Attendance System for Education**
> Powered by ArcFace + Anti-Spoofing + FIQA | Cross-platform (Windows, Android, iOS, macOS, Web)

[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135.1-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Flet](https://img.shields.io/badge/Flet-0.85.0-02569B?logo=flutter)](https://flet.dev)
[![License](https://img.shields.io/badge/License-Academic-yellow)]()

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Testing](#-testing)
- [Benchmark Results](#-benchmark-results)
- [Author](#-author)

---

## 🔍 Overview

AuEdu is an automated attendance system using **AI face recognition** designed for educational environments. The system combines multiple processing layers:

| Layer | Technology | Function |
|:---|:---|:---|
| **Face Detection** | RetinaFace [1] | Real-time face detection |
| **Face Recognition** | ArcFace / MobileFaceNet [2] | 512-D embedding extraction & identity matching |
| **Anti-Spoofing** | MiniFASNet (CDC) [3] | Prevent spoofing (printed photos, screens) |
| **FIQA** | Laplacian Variance [4] | Filter blurry images before recognition |
| **Vector Search** | pgvector HNSW + Numpy Cache | Vector search < 0.2ms |
| **Real-time** | WebSocket + Async Queue | Low-latency frame streaming |

### Key Highlights

- ✅ **Zero hardware cost** — runs on existing laptops/PCs
- ✅ **Cross-platform** — 1 Python codebase → Windows, macOS, Android, iOS, Web
- ✅ **FAR = 0%** — zero false acceptance across 36,358 impostor pairs
- ✅ **98.75% Accuracy** — benchmarked on international LFW dataset
- ✅ **98% Anti-spoofing** — blocked 49/50 spoofing attempts
- ✅ **Real-time** — embedding < 30ms, vector search < 0.2ms

---

## 🏗 System Architecture

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

## ⚙️ Tech Stack

### Back-end (Server)

| Technology | Version | Role |
|:---|:---|:---|
| Python | 3.10 | Primary language |
| FastAPI | 0.135.1 | REST API + WebSocket |
| Uvicorn | 0.41.0 | ASGI Server |
| SQLAlchemy | 2.0.30 | ORM |
| Alembic | — | Database migrations |
| PostgreSQL + pgvector | 16.x + ≥ 0.2.5 | Database + Vector Search |

### AI Core

| Technology | Model | Role |
|:---|:---|:---|
| InsightFace | `buffalo_s` | RetinaFace + MobileFaceNet |
| MiniFASNet | `modelrgb.onnx` | Anti-Spoofing (CDC) |
| ONNX Runtime | GPU (CUDA 12.x) | Inference Engine |
| OpenCV | ≥ 4.8.0 | Image processing |

### Front-end (Client)

| Technology | Version | Role |
|:---|:---|:---|
| Flet | 0.85.0 | Cross-platform UI (Flutter-based) |
| MediaPipe | — | Client-side face detection |

---

## 📂 Project Structure

```
AuEdu-Multi-PlatForm/
│
├── Server/                          # 🖥 Back-end FastAPI
│   ├── app/
│   │   ├── ai/                      # AI Core Engine
│   │   │   ├── engine.py            #   Main FaceEngine
│   │   │   ├── attendance_cache.py  #   In-memory vector cache
│   │   │   └── models/              #   ONNX models (auto-download)
│   │   ├── api/                     # API Routes
│   │   │   ├── auth.py              #   Authentication (JWT)
│   │   │   ├── attendance.py        #   Attendance REST API
│   │   │   ├── websocket.py         #   WebSocket handler
│   │   │   └── training.py          #   Face registration
│   │   ├── core/                    # System configuration
│   │   ├── db/                      # Database models
│   │   ├── services/                # Business logic
│   │   └── main.py                  # Entry point
│   ├── migrations/                  # Alembic migrations
│   └── requirements.txt
│
├── Client/                          # 📱 Front-end Flet App
│   ├── components/                  # UI Components
│   ├── pages/                       # Feature pages
│   ├── core/                        # Theme, Config
│   ├── main.py                      # Entry point
│   └── requirements.txt
│
├── tests/                           # 🧪 Test Suite
│   ├── prepare_dataset.py           # Download & prepare LFW dataset
│   ├── test_accuracy.py             # Accuracy, FIQA, Anti-Spoofing
│   ├── test_latency.py              # Pipeline latency benchmark
│   ├── test_resource_monitor.py     # Resource monitoring
│   ├── test_vector_search.py        # Vector search benchmark
│   ├── generate_word_report.py      # Generate Word report
│   ├── dataset/                     # ⚠ Not uploaded to GitHub
│   └── results/                     # ⚠ Not uploaded to GitHub
│
├── .gitignore
├── README.md                        # 🇻🇳 Vietnamese
└── README.en.md                     # 🇬🇧 English (this file)
```

> ⚠️ `tests/dataset/` and `tests/results/` contain heavy image/result files and are **excluded from GitHub**. Run `prepare_dataset.py` to auto-download the dataset.

---

## 🚀 Installation & Setup

### System Requirements

| Component | Minimum | Recommended |
|:---|:---|:---|
| CPU | 4 cores | 6+ cores |
| RAM | 4 GB | 8+ GB |
| GPU | Not required | NVIDIA GPU (CUDA) |
| Python | 3.10 | 3.10 |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 |

### 1. Clone repository

```bash
git clone https://github.com/NCH2024/AuEdu-Multi-PlatForm.git
cd AuEdu-Multi-PlatForm
```

### 2. Server setup

```bash
cd Server
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env with your PostgreSQL/Supabase credentials

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Client setup

```bash
cd Client
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
flet run main.py

# Build Android APK:
flet build apk
```

### 4. Environment variables (`.env`)

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

## 🧪 Testing

### Test Suite Overview

| Script | Function | Output |
|:---|:---|:---|
| `prepare_dataset.py` | Download LFW + generate spoofing/blur images | `tests/dataset/` |
| `test_accuracy.py` | Accuracy, FIQA, Anti-Spoofing evaluation | `accuracy_report.json` |
| `test_latency.py` | AI pipeline latency measurement | `latency_report.json` |
| `test_resource_monitor.py` | CPU, RAM, GPU, VRAM monitoring | `resource_report.json` |
| `test_vector_search.py` | Numpy vs pgvector benchmark | `vector_search_report.json` |

### Step 1: Prepare dataset

```bash
pip install scikit-learn psutil
python tests/prepare_dataset.py
```

> 💡 Re-running will automatically skip if dataset already exists. Use `--force` to re-download.

### Step 2: Run tests

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

### Step 3: Generate Word report

```bash
pip install python-docx
python tests/generate_word_report.py
# Output: tests/results/THUC_NGHIEM_AUEDU.docx
```

---

## 📊 Benchmark Results

> Benchmarked on LFW dataset · AMD Ryzen 5 5600H + RTX 3050 (4GB VRAM)

### Recognition Accuracy

| Metric | Result |
|:---|:---|
| **Face Detection Rate** | 99.79% (1,902/1,906) |
| **Accuracy** | 98.75% (threshold 0.45) |
| **FAR** (False Acceptance Rate) | **0.00%** |
| **F1-Score (best)** | **99.33%** (threshold 0.60) |
| **Precision** | **100%** |

### Threshold Analysis

| Threshold | Accuracy | FAR | FRR | F1-Score |
|:---|:---|:---|:---|:---|
| 0.30 | 95.72% | 0% | 86.93% | 23.12% |
| 0.40 | 97.58% | 0% | 49.10% | 67.46% |
| **0.45** ⬅️ | **98.75%** | **0%** | **25.35%** | **85.49%** |
| 0.50 | 99.55% | 0% | 9.19% | 95.18% |
| 0.55 | 99.86% | 0% | 2.92% | 98.52% |
| **0.60** ⭐ | **99.93%** | **0%** | **1.33%** | **99.33%** |

### Anti-Spoofing & FIQA

| Test | Result |
|:---|:---|
| Print Attack blocked | **96%** (24/25) |
| Screen Attack blocked | **100%** (25/25) |
| FIQA blur filtering (threshold 0.10) | **90%** (45/50) |

### Vector Search Performance

| N vectors | Avg latency | P95 latency |
|:---|:---|:---|
| 50 | 0.135 ms | 0.199 ms |
| 100 | 0.153 ms | 0.252 ms |
| 500 | 0.123 ms | 0.176 ms |
| 1,000 | 0.161 ms | 0.219 ms |

---

## 📚 References

| # | Reference |
|:---|:---|
| [1] | J. Deng et al., "ArcFace: Additive Angular Margin Loss for Deep Face Recognition," CVPR, 2019. |
| [2] | S. Chen et al., "MobileFaceNets: Efficient CNNs for Real-Time Face Verification on Mobile," CCBR, 2018. |
| [3] | Z. Yu et al., "Searching Central Difference Convolutional Networks for Face Anti-Spoofing," CVPR, 2020. |
| [4] | S. Pertuz et al., "Analysis of Focus Measure Operators for Shape-from-Focus," Pattern Recognition, 2013. |
| [5] | G. B. Huang et al., "Labeled Faces in the Wild," UMass Amherst, Tech. Rep. 07-49, 2007. |

---

## 👨‍💻 Author

| | |
|:---|:---|
| **Name** | Nguyen Chanh Hiep |
| **Role** | 4th-year undergraduate student |
| **Faculty** | School of Digital Technology and Artificial Intelligence (DNC) |
| **University** | Nam Can Tho University |
| **Purpose** | Scientific research & Graduation thesis |

---

<p align="center">
  <i>This project is for academic research and educational development purposes.</i>
</p>
