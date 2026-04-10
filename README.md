# 🎓 AI Face Attendance System

Hệ thống **điểm danh bằng nhận diện khuôn mặt thời gian thực** dành cho môi trường giáo dục.
Dự án được thiết kế theo mô hình **Client – Server – AI Core**, tối ưu cho **độ trễ thấp**, **bảo mật khuôn mặt**, và **khả năng mở rộng**.

Ứng dụng cho phép giảng viên thực hiện điểm danh nhanh chóng bằng camera, đồng thời sử dụng **AI chống giả mạo (Face Anti-Spoofing)** để đảm bảo tính xác thực của khuôn mặt.

---
# REVIEW UI/UX
![Home page](https://github.com/NCH2024/AuEdu-Multi-PlatForm/blob/main/review/image.png)

![Attendent Page](https://github.com/NCH2024/AuEdu-Multi-PlatForm/blob/main/review/image2.png)

---

# 📌 Mục tiêu dự án

* Xây dựng hệ thống **điểm danh tự động bằng khuôn mặt**.
* Đảm bảo **nhận diện nhanh (real-time)** với độ trễ thấp.
* Tăng cường bảo mật bằng **AI chống giả mạo khuôn mặt**.
* Cung cấp **dashboard quản lý** cho giảng viên và quản trị viên.
* Hỗ trợ **Desktop và Mobile**.

---

# 🏗 Kiến trúc hệ thống

Hệ thống được chia thành **3 lớp chính**:

```
Client (Flet App)
      │
      │ WebSocket (Real-time Face Stream)
      ▼
Server API (FastAPI)
      │
      │ AI Processing
      ▼
AI Core (CUDA GPU)
      │
      ▼
Database (Supabase + pgvector)
```

### Luồng xử lý chính

1. Camera trên **Client** phát hiện khuôn mặt bằng MediaPipe.
2. Ảnh khuôn mặt được **cắt trực tiếp trên thiết bị**.
3. Ảnh đã cắt gửi liên tục về **Server qua WebSocket**.
4. Server chạy AI:

   * **MiniFASNet** kiểm tra giả mạo.
   * **MobileFaceNet** trích xuất vector khuôn mặt.
5. Vector được so sánh với dữ liệu trong **pgvector (Supabase)**.
6. Kết quả điểm danh trả về **real-time cho Client**.

---

# ⚙️ Tech Stack

## Front-end (Client)

* **Flet 0.82.0**

  * Desktop
  * Mobile

* **MediaPipe**

  * Phát hiện và cắt khuôn mặt trực tiếp trên thiết bị
  * Giảm tải xử lý cho server

---

## Communication

* **WebSockets**

  * Truyền ảnh khuôn mặt real-time
  * Độ trễ thấp
  * Hỗ trợ chế độ quét nhiều sinh viên liên tục

---

## Back-end (Server)

* **FastAPI**

  * Quản lý WebSocket
  * REST API
  * Routing & Authentication

---

## AI Core (CUDA Server)

### Face Anti-Spoofing

* **MiniFASNet**

  * Phát hiện ảnh giả mạo
  * Ngăn chặn:

    * ảnh in
    * màn hình điện thoại
    * video replay

### Face Recognition

* **MobileFaceNet**

  * Trích xuất **face embedding**
  * Tối ưu tốc độ cho real-time

---

## Database & Authentication

* **Supabase**

  * PostgreSQL
  * Authentication
  * Storage

* **pgvector**

  * Lưu **vector khuôn mặt**
  * So sánh vector để nhận diện danh tính

---

# 🎨 UI / UX Design

Ứng dụng được thiết kế theo phong cách:

### Windows Fluent UI

* `border_radius`
* card layout
* sidebar navigation

### Glassmorphism

Các thành phần sử dụng hiệu ứng kính mờ:

* Navigation Bar
* Popup thông báo
* Khung Camera
* Panel Dashboard

Sử dụng:

```
blur
bgcolor + opacity
```

Mục tiêu:

* Giao diện hiện đại
* Tối ưu hiệu suất
* Không gây lag khi chạy camera

---

# 📱 Cấu trúc trang (Routing / Pages)

## Trang dùng chung

### 🔐 Authentication

* Đăng nhập
* Đăng xuất

### 🧭 Dashboard Layout

Bao gồm:

* **Sidebar Menu**
* **Topbar**
* **Content Area**

### ⚙️ Cài đặt ứng dụng

* Chọn camera
* Cấu hình kết nối server
* Kiểm tra trạng thái kết nối

---

# 👨‍🏫 Phân hệ Giảng viên

Quyền truy cập dựa trên `vai_tro`.

## Tổng quan

Hiển thị:

* Thông tin cá nhân
* Thông báo từ Admin
* Lịch dạy hôm nay

---

## Thời khóa biểu

Hiển thị:

* lịch theo **tuần**
* lịch theo **tháng**

Giảng viên có thể:

* xem lớp sắp dạy
* mở nhanh trang điểm danh

---

## Điểm danh

Quy trình:

```
Chọn lớp
   ↓
Bật Camera
   ↓
Chọn chế độ quét
   ↓
Nhận diện Real-time
   ↓
Hiển thị kết quả
```

### Chế độ điểm danh

**1️⃣ Chế độ từng người**

* Sinh viên đứng trước camera
* Hệ thống xác nhận từng người

**2️⃣ Chế độ quét lớp**

* Camera quét nhiều khuôn mặt
* Nhận diện liên tục qua WebSocket

### Hiển thị kết quả

* Overlay nhận diện
* Popup kính mờ (Glass UI)
* Hiển thị:

  * tên
  * MSSV
  * trạng thái điểm danh

---

## Thống kê

Giảng viên xem:

* tỉ lệ đi học
* tỉ lệ vắng
* thống kê theo:

  * lớp
  * môn học
  * thời gian

---

# 🛠 Phân hệ Admin

## Tổng quan hệ thống

Dashboard hiển thị:

* số lượng sinh viên
* số lượng lớp
* trạng thái server
* trạng thái database

---

## Quản lý dữ liệu

Admin có thể quản lý:

* Sinh viên
* Giảng viên
* Lớp học
* Môn học
* Lịch học

---

## Quản lý dữ liệu khuôn mặt

* đăng ký khuôn mặt
* cập nhật khuôn mặt
* xóa dữ liệu khuôn mặt

---

# 📂 Dự kiến cấu trúc dự án

```
project-root
│
├── client
│   ├── pages
│   ├── components
│   ├── layouts
│   └── services
│
├── server
│   ├── api
│   ├── websocket
│   ├── ai_core
│   │   ├── anti_spoof
│   │   └── face_embedding
│   └── services
│
├── models
│
├── database
│
└── docs
```

---

# 🚀 Trạng thái dự án

Dự án hiện đang trong giai đoạn:

**🚧 Development (Early Stage)**

Các phần đang phát triển:

* Flet Client UI
* WebSocket streaming
* AI inference pipeline
* Supabase integration

---

# 📌 Định hướng phát triển

Các tính năng dự kiến:

* Face registration automation
* Offline recognition cache
* Multi-camera support
* Mobile optimization
* Analytics nâng cao

---

# 📄 License

Dự án hiện đang phục vụ cho mục đích **nghiên cứu và phát triển học thuật**.

---
