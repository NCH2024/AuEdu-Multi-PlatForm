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

## 📊 Benchmark Results

> LFW dataset · AMD Ryzen 5 5600H + RTX 3050 (4GB VRAM)

| Metric | Result |
|:---|:---|
| **Face Detection** | 99.79% (1,902/1,906) |
| **Accuracy** | **98.75%** (threshold 0.45) |
| **FAR** (False Acceptance) | **0.00%** |
| **F1-Score (best)** | **99.33%** (threshold 0.60) |
| **Precision** | **100%** |
| **Anti-Spoofing** | **98%** (49/50 blocked) |
| **FIQA blur filtering** | **90%** at threshold 0.10 |
| **Vector Search** | **< 0.2ms** for N ≤ 1,000 |
| **Embedding speed** | **29.71 ms**/image |

### Comparison with Existing Solutions

| Criteria | **AuEdu** | ZKTeco | Hikvision | face_recognition |
|:---|:---|:---|:---|:---|
| **Cost** | **$0** | $300–1,000 | $400–1,500 | $0 |
| **Cross-platform** | ✅ 5 platforms | ❌ | ❌ | ⚠ Python |
| **Anti-Spoofing** | ✅ MiniFASNet | ✅ IR | ✅ Structured | ❌ |
| **Open-source** | ✅ | ❌ | ❌ | ✅ |

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
