# AuEdu — AI Face Recognition Attendance System | Open-Source Cross-Platform

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

> **Open-source real-time face recognition attendance system for education**, powered by ArcFace + Anti-Spoofing + FIQA. Runs on **5 platforms** (Windows, Android, iOS, macOS, Web) from a single Python codebase. **Zero additional hardware cost** — just use your existing laptop.

---

## Introduction to AuEdu (What is AuEdu?)

**AuEdu** (Automated Education) is an open-source **face recognition attendance system** specifically designed for **schools, universities, and educational institutions**. Instead of expensive dedicated hardware ($300–$1,500), AuEdu runs directly on existing laptops/PCs with a standard webcam.

### Solutions Comparison

| Problem | AuEdu's Solution |
|:---|:---|
| Expensive attendance terminals (ZKTeco, Hikvision) | Free — runs on existing hardware and webcam |
| Single-platform only | Multi-platform support (Windows, macOS, Android, iOS, Web) |
| Easy to cheat (photos, videos) | Biometric anti-spoofing via MiniFASNet model |
| Blurry/backlit images → wrong results | FIQA filters low-quality inputs using Laplacian Variance |
| Low accuracy | High accuracy via ArcFace 512-D (98.75% Accuracy, 0% FAR) |

### Key Features

- **SOTA Face Recognition** — Integrates RetinaFace (detection) and ArcFace/MobileFaceNet (recognition) via InsightFace `buffalo_s`.
- **Anti-Spoofing** — Biometric liveness check using MiniFASNet (Central Difference Convolution) to block screen & print attacks.
- **Face Image Quality Assessment (FIQA)** — Laplacian Variance filtering for backlit and blurry frames.
- **Real-time Streaming** — WebSocket-based real-time frame transmission (< 30ms) and vector search (< 0.2ms).
- **Vector Database Integration** — Utilizes pgvector (PostgreSQL) combined with Numpy in-memory caching for O(1) matching.
- **Cross-platform Client** — A single Python/Flet codebase compiled for 5 different platforms.
- **Open-source & Academic** — Free for academic, educational, and research purposes.

---

## System Architecture

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

## Tech Stack

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

## Installation & Setup

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

### Environment Configuration (.env) — REQUIRED

> **Security:** `.env` files contain secrets and are **NOT on GitHub**. Only `.env.example` templates are provided.

1. **Copy templates:** `cp Server/.env.example Server/.env && cp Client/.env.example Client/.env`
2. **Create Supabase project** at [supabase.com](https://supabase.com) (free)
3. **Fill in credentials** from Supabase Dashboard → Settings → API
4. **Enable pgvector:** Run `CREATE EXTENSION IF NOT EXISTS vector;` in SQL Editor

---

## Testing & Benchmarking

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

## Evaluation & Comparative Analysis

> Real-world benchmark on **LFW dataset** (Labeled Faces in the Wild) — 1,906 images, 20 identities.
> Test Hardware: AMD Ryzen 5 5600H + NVIDIA RTX 3050 Laptop GPU (4GB VRAM).

### 1. Criterion 1: Application & Feature Comparison (Application & System Features)

AuEdu offers superior flexibility, under-the-hood security controls from actual production code, and complete academic administrative features compared to expensive commercial hardware solutions and bare libraries.

| Criteria | **AuEdu** (Proposed) | ZKTeco Terminal [10] | Hikvision MinMoe [11] | Suprema FaceStation [12] | FPT.AI eKYC [13] | VNPT vnFace | face_rec (dlib) [14] | DeepFace [15] |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Solution Type** | Open Software | Embedded HW | Embedded HW | Embedded HW | Cloud API | Cloud App | Open Library | Open Library |
| **Initial Cost** | Free ($0) | $300–$1,000 | $400–$1,200 | $600–$1,600 | Cloud ($0) | Low (Subscription) | Free ($0) | Free ($0) |
| **Cross-platform** | Yes (5 Platforms) | No (Proprietary HW) | No (Proprietary HW) | No (Proprietary HW) | Yes (API-based) | Partial (Mobile/Tablet) | Partial (Python only) | Partial (Python only) |
| **FIQA Quality Filter** | Yes (Laplacian Variance) | Yes (Auto/Embedded) | Yes (Auto/Embedded) | Yes (Auto/Embedded) | Yes (Supported) | Yes (Supported) | No (Not supported) | No (Not supported) |
| **Anti-Spoofing AI** | Yes (MiniFAS RGB Liveness) | Yes (IR Dual Cam) | Yes (Structured Light) | Yes (Visual + IR) | Yes (Liveness API) | Yes (Liveness API) | No (Not supported) | No (Not supported) |
| **Lens Calibration** | Yes (OpenCV Calibration) | Yes (Embedded Calib) | Yes (Embedded Calib) | Yes (Embedded Calib) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) |
| **Offline Operation** | Yes (Local LAN) | Yes (Standalone) | Yes (Standalone) | Yes (Standalone) | No (Requires Internet) | No (Requires Internet) | Yes (Local) | Yes (Local) |
| **Real-time WebSocket** | Yes (WS Stream) | Yes (Supported) | Yes (Supported) | Yes (Supported) | No (Synced API) | No (Synced API) | No (Not supported) | No (Not supported) |
| **Vector Similarity DB** | Yes (pgvector HNSW) | N/A (Embedded) | N/A (Embedded) | N/A (Embedded) | N/A (Cloud) | N/A (Cloud) | No (Brute-force) | No (Brute-force) |
| **Smart Memory Cache** | Yes (Numpy Cache) | Yes (On-chip RAM) | Yes (On-chip RAM) | Yes (On-chip RAM) | N/A (Cloud) | N/A (Cloud) | No (Not supported) | No (Not supported) |
| **GPS Geolocation** | Yes (OSM Nominatim) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) | Partial (Raw Coord) | No (Not supported) | No (Not supported) |
| **Session Timeout Monitor**| Yes (BG Thread exp) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) | No (Basic Login) | No (Not supported) | No (Not supported) |
| **Device Identity Audit**| Yes (X-Device-ID) | Yes (Serial / MAC) | Yes (Serial / MAC) | Yes (Serial / MAC) | No (Not supported) | Yes (Supported) | No (Not supported) | No (Not supported) |
| **2-Layer Client Cache** | Yes (Memory + Prefs) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) | No (Not supported) |
| **Auto API URL Sync** | Yes (Public Config) | No (Not supported) | No (Not supported) | No (Not supported) | N/A (Cloud) | N/A (Cloud) | No (Not supported) | No (Not supported) |
| **RBAC Access** | Yes (Admin/GV/SV) | Yes (Device Admin) | Yes (Device Admin) | Yes (Device Admin) | No (Not supported) | Yes (Supported) | No (Not supported) | No (Not supported) |
| **Dynamic Themes** | Yes (Dark + 4 Palettes) | No (Fixed UI) | No (Fixed UI) | No (Fixed UI) | No (No UI) | No (Branded UI) | No (Not supported) | No (Not supported) |
| **Academic CRUD** | Yes (Complete CRUD) | Partial (Departments only) | Partial (Departments only) | Partial (Departments only) | No (Not supported) | Partial (Basic Class/Student) | No (Not supported) | No (Not supported) |
| **Charts & Analytics** | Yes (Flet Charts) | No (Not supported) | Partial (HikCentral addon) | Partial (BioStar 2 addon) | No (Not supported) | Partial (Basic Charts) | No (Not supported) | No (Not supported) |
| **Report Export** | Yes (Excel / CSV) | Yes (Excel/CSV/TXT) | Yes (Excel / CSV) | Yes (Excel/CSV/PDF) | No (Not supported) | Yes (Excel / CSV) | No (Not supported) | No (Not supported) |

### 2. Criterion 2: Processing Speed & Task Latency (Speed & Latency)

The system achieves instant UI response (< 50 ms powered by Flutter Engine) and ultra-fast frame processing via WebSockets:

- **AI Pipeline Latency (E2E):** **~38.00 ms** (Base64 decode: 0.72 ms, Face Detection: 35.08 ms, FIQA: 0.20 ms, Anti-spoof: 3.94 ms, ArcFace embedding: 35.55 ms).
- **Throughput:** Real-world **21.56 FPS** under continuous frame streaming.
- **Match Latency (Numpy Cache):** **< 0.2 ms** for class matching scale of N = 1,000.

#### Detailed Latency & Throughput Comparison:

| Criteria | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **UI Response Latency** | **< 50 ms** | < 100 ms | < 100 ms | < 80 ms | < 150 ms | < 120 ms | N/A | N/A |
| **Network Overhead** | **Low (WS)** | Low (TCP) | Low (TCP) | Low (TCP) | High (HTTP) | High (HTTP) | None | None |
| **Inference Latency** | **~35.5 ms** | ~100-200 ms | ~80-150 ms | ~50-100 ms | ~200-400 ms | ~150-300 ms | ~150-300 ms | ~200-500 ms |
| **Vector Match Latency** | **< 0.2 ms** | < 5 ms | < 5 ms | < 3 ms | < 50 ms | < 30 ms | > 10 ms | > 20 ms |
| **E2E Pipeline Latency** | **~38.0 ms** | < 300 ms | < 300 ms | < 200 ms | > 500 ms | > 400 ms | > 200 ms | > 300 ms |
| **Throughput (FPS)** | **~21.5 FPS**| ~5-10 FPS | ~5-10 FPS | ~10-15 FPS| < 2 FPS | < 3 FPS | < 5 FPS | < 3 FPS |

### 3. Criterion 3: Installation Size & System Resources (Capacity & Resource Overhead)

AuEdu is highly optimized for codebase size and memory footprint, making it extremely safe for standard office PCs.

- **Codebase Size:** Lightweight **8.10 MB** (Client code: 4.65 MB, Server code: 3.45 MB).
- **Package Installer:** Client mobile APK ~45 MB, Desktop Windows .exe ~80 MB. (Much lighter than face_recognition's > 200 MB dlib runtime).
- **Process Memory (RAM):** Only **~468.3 MB** when Idle, and stays at **~1209.1 MB** (Peak: 1217.2 MB) during active processing.
- **GPU & VRAM Usage:** Avg GPU load ~37.2% (Peak: 95.0%), VRAM consumption is extremely low at **~999.1 MB** (out of 4GB on RTX 3050), freeing up system CPU and preventing overheating.

#### Detailed Size & Resource Comparison:

| Criteria | **AuEdu** | ZKTeco | Hikvision | Suprema | FPT.AI | VNPT | face_rec | DeepFace |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Codebase Size** | **~8.1 MB** | N/A (~500 MB) | N/A (~2 GB) | N/A (~1.5 GB) | N/A | N/A | N/A | N/A |
| **Env Bloat Overhead** | **Light (ONNX)**| Very High | Very High | Very High | None | None | High (dlib) | High (TF) |
| **APK Installer Size** | **~45 MB** | N/A | N/A | N/A | N/A | ~60 MB | N/A | N/A |
| **EXE Installer Size** | **~80 MB** | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| **Process RAM (Peak)** | **< 1.3 GB** | > 2 GB | > 4 GB | > 3 GB | None | Low | > 1.5 GB | > 2 GB |
| **Hardware Cost** | **Free ($0)** | $300–$1,000 | $400–$1,200 | $600–$1,600 | API-based | Subscription | Free ($0) | Free ($0) |

---

## References

| # | Reference |
|:---|:---|
| [1] | J. Deng et al., "**ArcFace**: Additive Angular Margin Loss for Deep Face Recognition," *CVPR*, 2019. |
| [2] | S. Chen et al., "**MobileFaceNets**: Efficient CNNs for Real-Time Face Verification on Mobile," *CCBR*, 2018. |
| [3] | Z. Yu et al., "Searching **Central Difference Convolutional Networks** for Face Anti-Spoofing," *CVPR*, 2020. |
| [4] | S. Pertuz et al., "Analysis of **Focus Measure Operators** for Shape-from-Focus," *Pattern Recognition*, 2013. |
| [5] | G. B. Huang et al., "**Labeled Faces in the Wild**," *UMass Amherst*, 2007. |

---

## Author

| | |
|:---|:---|
| **Name** | **Nguyen Chanh Hiep** |
| **Role** | 4th-year undergraduate student |
| **Faculty** | School of Digital Technology and Artificial Intelligence (DNC) |
| **University** | Nam Can Tho University, Vietnam |
| **Purpose** | Scientific research & Graduation thesis |

---

## Support

If this project is useful, please star this repository on GitHub to help more people discover it.

Contributions (issues, pull requests) are welcome.

---

<p align="center">
  <i>AuEdu — Open-source AI face recognition attendance system for education.<br>
  Phần mềm điểm danh khuôn mặt AI mã nguồn mở cho giáo dục.</i>
</p>
