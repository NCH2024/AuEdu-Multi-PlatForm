import flet as ft
import flet_camera 
import asyncio
import base64
import platform 

try:
    import cv2
except ImportError:
    cv2 = None
    
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
except ImportError:
    mp = None
    mp_face_mesh = None
    


class CameraView(ft.Container):
    def __init__(self, page: ft.Page, dd_camera: ft.Dropdown, is_visible=False, on_frame=None):
        super().__init__()
        self.app_page = page
        self.dd_camera = dd_camera 
        self.on_frame = on_frame 
        
        self.is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        self.is_running = False 
        self.is_paused = False
        
        # Bổ sung 2 dòng này để CameraView tự bung và có viền đen tránh chớp sáng
        self.expand = True 
        self.bgcolor = ft.Colors.BLACK 
        
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
                self.content = ft.Row(
                    controls=[self.camera_module], expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH, spacing=0
                )
            else:
                self.camera_module.expand = False
                self.content = ft.Container(width=1, height=1, content=self.camera_module, clip_behavior=ft.ClipBehavior.HARD_EDGE)
            self.cap = None
            
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
                    if self.cap.isOpened():
                        self.is_running = True
                        self.app_page.run_task(self._desktop_camera_loop)
                    else:
                        print("Thất bại: OpenCV bên trong App không mở được Camera!")
        except Exception as e:
            print(f"Lỗi khởi động camera: {e}")

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
        while self.is_running:
            if getattr(self, 'is_paused', False):
                await asyncio.sleep(0.1)
                continue
            
            if getattr(self, 'cap', None) and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy() 
                    
                    face_crop_base64 = None
                    
                    # ==== XỬ LÝ NHẬN DIỆN LƯỚI KHUÔN MẶT BẰNG FACEMESH ====
                    if mp_face_mesh and hasattr(self, 'face_mesh'):
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        results = self.face_mesh.process(rgb_frame)
                        
                        if results.multi_face_landmarks:
                            for face_landmarks in results.multi_face_landmarks:
                                # 1. Vẽ lưới lên khung hình để test (Có thể comment lại sau khi App đã ổn định)
                                mp.solutions.drawing_utils.draw_landmarks(
                                    image=frame,
                                    landmark_list=face_landmarks,
                                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                                    landmark_drawing_spec=None,
                                    connection_drawing_spec=mp.solutions.drawing_styles.get_default_face_mesh_tesselation_style()
                                )
                                
                                # 2. LẤY KÍCH THƯỚC ẢNH VÀ TÍNH TOÁN TƯ THẾ (POSE) Ở ĐÂY
                                ih, iw, _ = frame.shape
                                self.current_pose = self._get_current_pose(face_landmarks.landmark, iw, ih)
                                
                                # 3. Cắt khuôn mặt để gửi qua API
                                x_min = int(min([lm.x for lm in face_landmarks.landmark]) * iw)
                                x_max = int(max([lm.x for lm in face_landmarks.landmark]) * iw)
                                y_min = int(min([lm.y for lm in face_landmarks.landmark]) * ih)
                                y_max = int(max([lm.y for lm in face_landmarks.landmark]) * ih)
                                
                                # Tính toán padding an toàn
                                pad_x, pad_y = int((x_max - x_min)*0.2), int((y_max - y_min)*0.2)
                                start_y, end_y = max(0, y_min - pad_y), min(ih, y_max + pad_y)
                                start_x, end_x = max(0, x_min - pad_x), min(iw, x_max + pad_x)
                                
                                face_crop = self.current_frame[start_y:end_y, start_x:end_x] # Cắt từ ảnh gốc chưa có lưới trắng
                                if face_crop.size > 0:
                                    _, buffer = cv2.imencode('.jpg', face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                                    face_crop_base64 = base64.b64encode(buffer).decode('utf-8')
                    # =======================================================
                    _, buffer_display = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                    b64_str = base64.b64encode(buffer_display).decode('utf-8')
                    
                    # Dùng lại src cũ của em - An toàn 100% trên 0.84.0
                    self.camera_module.src = f"data:image/jpeg;base64,{b64_str}"
                    
                    try:
                        self.camera_module.update()
                    except Exception:
                        pass
                        
                    if face_crop_base64 and self.on_frame:
                        await self.on_frame(face_crop_base64)
            await asyncio.sleep(0.06) 

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