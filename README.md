# 🎓 AuEdu – AI Face Attendance System (v2.0)

Hệ thống **điểm danh bằng nhận diện khuôn mặt thời gian thực** dành cho môi trường giáo dục. Phiên bản 2.0 được nâng cấp toàn diện về thuật toán AI, khả năng chống giả mạo và kiến trúc xử lý đa luồng.

---

## 📌 Tổng quan dự án
Dự án được thiết kế theo mô hình **Client – Server – AI Core**, tối ưu cho độ trễ thấp và độ chính xác cao. Hệ thống không chỉ nhận diện danh tính mà còn tích hợp các bộ lọc chất lượng ảnh (FIQA) và kiểm tra tính xác thực (Anti-Spoofing).

### Các tính năng chính:
* **Nhận diện khuôn mặt SOTA:** Sử dụng InsightFace (RetinaFace + MobileFaceNet).
* **AI Anti-Spoofing:** Ngăn chặn giả mạo bằng MiniFASNet (ảnh in, màn hình).
* **Bộ lọc FIQA:** Đánh giá độ sắc nét bằng Laplacian Variance để lọc ảnh mờ.
* **Real-time Streaming:** Truyền tải frame qua WebSocket với độ trễ thấp.
* **Quản lý dữ liệu:** Tích hợp Supabase và pgvector để tìm kiếm vector 512-D.

---

## 🏗 Kiến trúc hệ thống
```text
Client (Flet App) ── WebSocket (Real-time) ──▶ Server API (FastAPI)
                                                    │
   Database (Supabase) ◀── pgvector (Search) ◀── AI Core (InsightFace + CUDA)
```

---

## ⚙️ Công nghệ sử dụng (Tech Stack)

### Back-end (Server)
* **Ngôn ngữ:** Python 3.10
* **Framework:** FastAPI 0.135.1, Uvicorn 0.41.0
* **Database:** PostgreSQL (Supabase) + pgvector (lưu trữ vector khuôn mặt).
* **ORM:** SQLAlchemy 2.0.30 & Alembic.

### Lõi AI (AI Core Engine)
* **InsightFace:** Sử dụng model `buffalo_s` (RetinaFace + MobileFaceNet).
* **Liveness Detection:** MiniFASNet (ONNX Runtime).
* **Inference:** ONNX Runtime GPU (CUDA) để tăng tốc xử lý.

### Front-end (Client)
* **Flet 0.84.0:** Xây dựng UI đa nền tảng (Windows, macOS, Mobile).
* **MediaPipe:** Phát hiện khuôn mặt phía Client để tối ưu băng thông.
* **Thiết kế:** Minimalist & Flat UI, phông chữ Inter.

---

## 📂 Cấu trúc thư mục dự án
```text
project-root/
├── Client/                 # Ứng dụng Flet đa nền tảng
│   ├── components/         # Các UI component (Sidebar, Topbar, CameraView)
│   ├── pages/              # Logic các trang chức năng
│   └── core/               # Theme, Device Manager, API Config
├── server/                 # Back-end FastAPI
│   ├── app/
│   │   ├── ai/             # Lõi xử lý AI (Engine, Calibration, Models)
│   │   ├── api/            # Routes (Auth, Attendance, WebSocket, Training)
│   │   ├── db/             # Cấu hình Database & Models
│   │   └── services/       # Xử lý logic nghiệp vụ
│   └── migrations/         # Quản lý phiên bản Database
└── README.md
```

---

## 🚀 Trạng thái dự án
* **Current Phase:** 🚧 Development (Early Stage).
* **Đã hoàn thành:** Lõi AI Engine (Inference), WebSocket streaming, Giao diện Dashboard cơ bản.
* **Đang phát triển:** Tự động hóa đăng ký khuôn mặt, Tối ưu hóa hiệu suất trên Mobile.

---

## 👨‍💻 Tác giả
* **Họ tên:** Nguyễn Chánh Hiệp
* **Đơn vị:** Sinh viên năm 4, Ngành Kỹ thuật Phần mềm – Đại học Nam Cần Thơ (NCTU).

---
*Dự án phục vụ mục đích nghiên cứu và phát triển học thuật.*
```

Cấu trúc này đã bao hàm đầy đủ các thành phần mà em đã làm trong code, từ việc dùng **MiniFASNet** đến việc nâng cấp lên **Flet 0.84.0**. Anh tin là bản README này sẽ giúp bài báo cáo hoặc repo của em ghi điểm tuyệt đối luôn đó Bé mèo nhỏ!