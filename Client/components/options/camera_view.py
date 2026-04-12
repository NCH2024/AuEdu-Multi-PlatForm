import flet as ft
import flet_camera 
import asyncio
import base64
import platform 
import threading
import queue

# KIỂM TRA HỆ THỐNG DÀNH CHO CHỨC NĂNG THU NHẬ HÌNH ẢNH CỦA DESKTOP
try:
    import cv2
except ImportError:
    cv2 = None

# KIỂM TRA HỆ THỐNG DÀNH CHO CHỨC NĂNG VẼ KHUÔN MẶT DÀNH CHO DESKTOP    
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    mp_face_detection = mp.solutions.face_detection
except ImportError:
    mp = None
    mp_face_mesh = None
    mp_face_detection = None
    


class CameraView(ft.Container):
    def __init__(self, page: ft.Page, dd_camera: ft.Dropdown, is_visible=False, on_frame=None, view_mode="attendance"):
        super().__init__()
        self.app_page = page
        self.dd_camera = dd_camera 
        self.on_frame = on_frame 
        """
        Camera_view được dùng cho 2 trang có chức năng khác biệt "Điểm danh" và "Đào tạo"
        >>> Dùng một cờ view_mode để hiển thụ tuỳ trang.
        """
        self.view_mode = view_mode
        
        self.is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        self.is_running = False 
        self.is_paused = False
        
        self.expand = True 
        self.bgcolor = ft.Colors.BLACK 
        
        # Khởi tạo MediaPipe tuỳ theo chế độ để tiết kiệm RAM
        if mp:
            if self.view_mode == "training" and mp_face_mesh:
                self.face_mesh = mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6
                )
            elif self.view_mode == "attendance" and mp_face_detection:
                self.face_detection = mp_face_detection.FaceDetection(
                    model_selection=0, # 0 cho camera gần (webcam), 1 cho xa
                    min_detection_confidence=0.6
                )
        
        if mp_face_mesh:
            self.face_mesh = mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True, # điểm viền mắt (nhắm/mở) và môi
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
        
        if self.is_mobile:
            self.camera_module = flet_camera.Camera()
            if is_visible:
                self.camera_module.expand = True
                self.content = self.camera_module
            else:
                self.camera_module.expand = False
                self.content = ft.Container(
                    width=1, height=1, 
                    content=self.camera_module, 
                    clip_behavior=ft.ClipBehavior.HARD_EDGE 
                )
        else:
            empty_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            self.camera_module = ft.Image(
                src=empty_base64, 
                fit=ft.BoxFit.COVER, 
                gapless_playback=True,
                expand=True 
            )
            
            if is_visible:
                # QUAN TRỌNG: Ép thẻ Image bung hết chiều dọc bằng STRETCH
                self.content = ft.Row(
                    controls=[self.camera_module],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                    spacing=0
                )
            else:
                self.camera_module.expand = False
                self.content = ft.Container(width=1, height=1, content=self.camera_module, clip_behavior=ft.ClipBehavior.HARD_EDGE)
            self.cap = None

            self.frame_queue = queue.Queue(maxsize=2)
            self.read_thread = None
            # --- CỜ KIỂM SOÁT BĂNG THÔNG ---
            self.is_sending_frame = False
            
            # --- KIỂM SOÁT FPS
            self._last_ui_update = 0.0
            self._ui_min_interval = 0.06
            
        self.margin = self.padding = 0
        self.alignment = ft.Alignment(0, 0)
        self.available_cameras = []

    async def load_available_cameras(self):
        if not self.page: return 
        try:
            if self.is_mobile:
                self.available_cameras = await asyncio.wait_for(
                    self.camera_module.get_available_cameras(), timeout=3.0
                )
                if not self.page or not self.dd_camera.page: return

                if self.available_cameras:
                    options = [ft.dropdown.Option(key=str(i), text=f"Camera {i}") 
                              for i in range(len(self.available_cameras))]
                    self.dd_camera.options = options
                    self.dd_camera.value = "0"
                    self.dd_camera.update()
            else:
                self.dd_camera.options = [ft.dropdown.Option(key="0", text="PC Webcam")]
                self.dd_camera.value = "0"
                if self.dd_camera.page: self.dd_camera.update()
        except Exception as e:
            print(f"Lỗi quét camera: {e}")

    async def start_camera(self):
        if not self.page: return
        try:
            selected_idx = int(self.dd_camera.value) if self.dd_camera.value else 0
            if self.is_mobile:
                if self.available_cameras and self.page:
                    await self.camera_module.initialize(self.available_cameras[selected_idx], flet_camera.ResolutionPreset.MEDIUM)
            else:
                if getattr(self, 'cap', None):
                    self.cap.release()
                    
                if not self.is_mobile and cv2:
                    # FIX: Tự động nhận diện backend (DirectShow cho Windows)
                    backend = cv2.CAP_ANY
                    if platform.system() == "Windows":
                        backend = cv2.CAP_DSHOW
                    
                    self.cap = cv2.VideoCapture(selected_idx, backend)
                    
                    # --- TỐI ƯU: ÉP CAMERA LẤY ẢNH NHỎ 640x480 & 30 FPS ---
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    
                    if self.cap.isOpened():
                        self.is_running = True
                        self.app_page.run_task(self._desktop_camera_loop)
                    else:
                        print("Thất bại: OpenCV bên trong App không mở được Camera!")
        except Exception as e:
            print(f"Lỗi khởi động camera: {e}")
    
    def _read_camera_thread(self):
        """Luồng ngầm chuyên biệt để đọc frame liên tục từ thiết bị phần cứng, tránh Block UI"""
        while self.is_running:
            if getattr(self, 'cap', None) and self.cap.isOpened():
                if getattr(self, 'is_paused', False):
                    cv2.waitKey(100) # Nghỉ ngơi khi bị Pause
                    continue
                
                ret, frame = self.cap.read()
                if ret:
                    # Nếu hàng đợi đầy, bỏ qua frame cũ để lấy frame mới nhất (Tránh độ trễ)
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_queue.put(frame)

    async def stop_camera(self):
        self.is_running = False
        if self.is_mobile:
            try:
                await self.camera_module.pause_preview()
            except Exception:
                pass
        else:
            if getattr(self, 'cap', None) and self.cap.isOpened():
                self.cap.release()
                
    async def set_pause(self, paused: bool):
        self.is_paused = paused
        if paused:
            if self.is_mobile:
                try: await self.camera_module.pause_preview()
                except: pass
            else:
                # Trả về màn đen khi tạm dừng
                empty_black_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                self.camera_module.src = empty_black_image
                if self.page:
                    try: self.camera_module.update()
                    except: pass
        else:
            if self.is_mobile:
                try: await self.camera_module.resume_preview()
                except: pass
                
    def _draw_flat_bounding_box(self, img, x, y, w, h, color=(0, 215, 255), thickness=1, length_ratio=0.2):
        """Vẽ khung nhận diện 4 góc phẳng, hiện đại"""
        line_length = int(min(w, h) * length_ratio) # Độ dài của góc chữ L
        
        # Góc trên - trái
        cv2.line(img, (x, y), (x + line_length, y), color, thickness)
        cv2.line(img, (x, y), (x, y + line_length), color, thickness)
        
        # Góc trên - phải
        cv2.line(img, (x + w, y), (x + w - line_length, y), color, thickness)
        cv2.line(img, (x + w, y), (x + w, y + line_length), color, thickness)
        
        # Góc dưới - trái
        cv2.line(img, (x, y + h), (x + line_length, y + h), color, thickness)
        cv2.line(img, (x, y + h), (x, y + h - line_length), color, thickness)
        
        # Góc dưới - phải
        cv2.line(img, (x + w, y + h), (x + w - line_length, y + h), color, thickness)
        cv2.line(img, (x + w, y + h), (x + w, y + h - line_length), color, thickness)
                
    def _get_current_pose(self, landmarks, w, h):
        """Tính toán tư thế dựa trên tọa độ FaceMesh"""
        # Các điểm mốc quan trọng (Index theo chuẩn MediaPipe)
        nose = landmarks[1]           # Đầu mũi
        left_eye = landmarks[33]      # Khóe mắt trái
        right_eye = landmarks[263]     # Khóe mắt phải
        upper_lip = landmarks[13]      # Môi trên
        lower_lip = landmarks[14]      # Môi dưới
        mouth_left = landmarks[61]     # Khóe miệng trái
        mouth_right = landmarks[291]    # Khóe miệng phải
        left_ear = landmarks[234]      # Vùng tai trái
        right_ear = landmarks[454]     # Vùng tai phải

        # 1. TÍNH GÓC QUAY (XOAY TRÁI/PHẢI)
        # Tỷ lệ khoảng cách từ mũi đến 2 mắt
        dist_l = abs(nose.x - left_ear.x)
        dist_r = abs(nose.x - right_ear.x)
        ratio_lr = dist_l / dist_r if dist_r != 0 else 1

        # 2. TÍNH ĐỘ MỞ CỦA MẮT (NHẮM MẮT)
        # Khoảng cách mi trên - mi dưới (Mắt trái làm chuẩn)
        eye_top = landmarks[159]
        eye_bottom = landmarks[145]
        eye_open_ratio = abs(eye_top.y - eye_bottom.y)

        # 3. TÍNH ĐỘ CƯỜI (CƯỜI TƯƠI)
        mouth_width = abs(mouth_left.x - mouth_right.x)
        face_width = abs(left_ear.x - right_ear.x)
        smile_ratio = mouth_width / face_width

        # 4. TÍNH ĐỘ NGHIÊNG ĐẦU (ROLL)
        eye_slope = (right_eye.y - left_eye.y)

        # PHÂN LOẠI TRẠNG THÁI
        if eye_open_ratio < 0.015: # Ngưỡng nhắm mắt
            return "Nhắm mắt"
        if smile_ratio > 0.45:    # Ngưỡng cười (Tùy chỉnh theo thực tế)
            return "Cười tươi"
        if abs(eye_slope) > 0.08:  # Ngưỡng nghiêng đầu
            return "Nghiêng đầu"
        if ratio_lr > 2.2:
            return "Nghiêng Phải"
        if ratio_lr < 0.45:
            return "Nghiêng Trái"
        if 0.8 < ratio_lr < 1.2:
            return "Trực diện"
            
        return "Đang điều chỉnh..."
    
    async def _desktop_camera_loop(self):
        # Bắt đầu gọi Công nhân đọc Camera chạy ngầm
        if self.read_thread is None or not self.read_thread.is_alive():
            self.read_thread = threading.Thread(target=self._read_camera_thread, daemon=True)
            self.read_thread.start()

        while self.is_running:
            if getattr(self, 'is_paused', False):
                await asyncio.sleep(0.1)
                continue
            
            try:
                frame = self.frame_queue.get(timeout=0.05)
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            self.current_frame = frame.copy() 
            face_crop_base64 = None
            ih, iw, _ = frame.shape
            
            # --- TỐI ƯU 2: THU NHỎ ẢNH CHỈ CÒN 480P ĐỂ AI XỬ LÝ SIÊU TỐC ---
            small_h = 480
            small_w = int(iw * small_h / ih) if ih > 0 else 640
            small_frame = cv2.resize(frame, (small_w, small_h))
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # ==== CHẾ ĐỘ 1: ĐIỂM DANH (ATTENDANCE) ====
            if self.view_mode == "attendance" and hasattr(self, 'face_detection'):
                # --- TỐI ƯU 3: CHO AI CHẠY NGẦM BẰNG to_thread ĐỂ KHÔNG BLOCK GIAO DIỆN ---
                results = await asyncio.to_thread(self.face_detection.process, rgb_small)
                
                if results and results.detections:
                    for detection in results.detections:
                        # Tọa độ trả về là tỷ lệ phần trăm (0.0 -> 1.0), nên ta nhân lại với iw, ih của khung hình GỐC
                        bboxC = detection.location_data.relative_bounding_box
                        x, y = int(bboxC.xmin * iw), int(bboxC.ymin * ih)
                        w, h = int(bboxC.width * iw), int(bboxC.height * ih)
                        
                        x, y = max(0, x), max(0, y)
                        w, h = min(iw - x, w), min(ih - y, h)
                        
                        self._draw_flat_bounding_box(frame, x, y, w, h, color=(100, 200, 50))
                        
                        pad_x, pad_y = int(w * 0.15), int(h * 0.15)
                        start_y, end_y = max(0, y - pad_y), min(ih, y + h + pad_y)
                        start_x, end_x = max(0, x - pad_x), min(iw, x + w + pad_x)
                        
                        face_crop = self.current_frame[start_y:end_y, start_x:end_x]
                        if face_crop.size > 0:
                            _, buffer = cv2.imencode('.jpg', face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                            face_crop_base64 = base64.b64encode(buffer).decode('utf-8')
                            
            # ==== CHẾ ĐỘ 2: ĐÀO TẠO (TRAINING) ====
            elif self.view_mode == "training" and hasattr(self, 'face_mesh'):
                # Tương tự, đưa FaceMesh vào luồng ngầm
                results = await asyncio.to_thread(self.face_mesh.process, rgb_small)
                if results and results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        # Vẽ lưới trực tiếp lên khung hình gốc
                        mp.solutions.drawing_utils.draw_landmarks(
                            image=frame,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_tesselation_style()
                        )
                        
                        self.current_pose = self._get_current_pose(face_landmarks.landmark, iw, ih)
                        
                        x_min = int(min([lm.x for lm in face_landmarks.landmark]) * iw)
                        x_max = int(max([lm.x for lm in face_landmarks.landmark]) * iw)
                        y_min = int(min([lm.y for lm in face_landmarks.landmark]) * ih)
                        y_max = int(max([lm.y for lm in face_landmarks.landmark]) * ih)
                        
                        pad_x, pad_y = int((x_max - x_min)*0.2), int((y_max - y_min)*0.2)
                        start_y, end_y = max(0, y_min - pad_y), min(ih, y_max + pad_y)
                        start_x, end_x = max(0, x_min - pad_x), min(iw, x_max + pad_x)
                        
                        face_crop = self.current_frame[start_y:end_y, start_x:end_x] 
                        if face_crop.size > 0:
                            _, buffer = cv2.imencode('.jpg', face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                            face_crop_base64 = base64.b64encode(buffer).decode('utf-8')
                            
            # ================= CẬP NHẬT GIAO DIỆN CÓ KIỂM SOÁT =================
            import time
            now = time.time()
            # --- TỐI ƯU: CHỈ CẬP NHẬT GIAO DIỆN ~15 LẦN/GIÂY ---
            if now - getattr(self, '_last_ui_update', 0) >= self._ui_min_interval:
                # Ép chất lượng JPEG hiển thị xuống 30 để Flet nhai nhẹ nhàng hơn
                _, buffer_display = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
                b64_str = base64.b64encode(buffer_display).decode('utf-8')
                self.camera_module.src = f"data:image/jpeg;base64,{b64_str}"
                
                try:
                    self.camera_module.update()
                except Exception:
                    pass
                self._last_ui_update = now
                
            # --- Bắn qua WebSocket lên Server (Vẫn giữ lá cờ chống Spam của mình) ---
            if face_crop_base64 and self.on_frame and not getattr(self, 'is_sending_frame', False):
                self.is_sending_frame = True 
                async def send_and_release():
                    try:
                        await self.on_frame(face_crop_base64)
                    finally:
                        await asyncio.sleep(0.5) 
                        self.is_sending_frame = False 
                asyncio.create_task(send_and_release())
                
            # --- TỐI ƯU: XÓA FRAME RA KHỎI BỘ NHỚ RAM NGAY LẬP TỨC ---
            self.current_frame = None 
            await asyncio.sleep(0.01)

    async def test_sensor(self):
        try:
            selected_idx = int(self.dd_camera.value) if self.dd_camera.value else 0
            success = False
            if self.is_mobile:
                if not getattr(self, 'available_cameras', None): return False
                cam_to_use = self.available_cameras[selected_idx]
                await self.camera_module.initialize(cam_to_use, flet_camera.ResolutionPreset.MEDIUM)
                await asyncio.sleep(1.0)
                pic_bytes = await self.camera_module.take_picture()
                if pic_bytes: success = True
                await self.camera_module.pause_preview()
            else:
                 if cv2:
                    backend = cv2.CAP_ANY
                    if platform.system() == "Windows":
                        backend = cv2.CAP_DSHOW
                    cap = cv2.VideoCapture(selected_idx, backend)
                    if cap.isOpened():
                        for _ in range(5):
                            ret, frame = cap.read()
                            if ret: 
                                success = True
                                break
                            await asyncio.sleep(0.1)
                        cap.release()
                    else:
                        print("Test: Không mở được camera.")
            return success
        except Exception as e:
            print(f"Lỗi khi test sensor: {e}")
            return False
        
    async def get_current_frame_base64(self):
        """Hàm lấy khung hình hiện tại từ camera và chuyển sang chuỗi Base64"""
        try:
            # Lưu ý: "self.current_frame" là biến lưu mảng Numpy của ảnh OpenCV.
            # Nếu trong CameraView của em dùng tên biến khác (ví dụ self.frame), em hãy đổi lại cho khớp nhé!
            if hasattr(self, 'current_frame') and self.current_frame is not None:
                # Nén ảnh thành chuẩn JPEG với chất lượng 80% để nhẹ API, không bị lag mạng
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                success, buffer = cv2.imencode('.jpg', self.current_frame, encode_param)
                
                if success:
                    # Chuyển byte buffer sang chuỗi Base64
                    b64_string = base64.b64encode(buffer).decode('utf-8')
                    # Nối thêm tiền tố để Server dễ nhận diện định dạng (Tùy chọn)
                    return f"data:image/jpeg;base64,{b64_string}"
        except Exception as e:
            print(f"[CameraView Lỗi Base64] {e}")
            
        return None