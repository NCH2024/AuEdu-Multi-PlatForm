import flet as ft
import flet_camera 
import asyncio
import base64
import platform 

try:
    import cv2
    import mediapipe as mp
    from mediapipe.python.solutions import face_detection as mp_face_detection 
except ImportError:
    cv2 = None
    mp = None
    mp_face_detection = None


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
        
        if mp_face_detection:
            self.face_detection = mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.6
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
            empty_black_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            # QUAN TRỌNG: Gắn expand=True vào trực tiếp thẻ Image
            self.camera_module = ft.Image(
                src=empty_black_image, 
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
                    await self.camera_module.initialize(
                        self.available_cameras[selected_idx], 
                        flet_camera.ResolutionPreset.MEDIUM
                    )
            else:
                if getattr(self, 'cap', None):
                    self.cap.release()
                    
                if not self.is_mobile and cv2:
                    # Chọn backend ổn định cho các hệ điều hành
                    backend = cv2.CAP_ANY
                    if platform.system() == "Windows":
                        # Trên Windows default thường thất bại → dùng DirectShow
                        backend = cv2.CAP_DSHOW
                    # FIX 2: Gọi cực kỳ đơn giản giống file test_cam.py nhưng có backend phù hợp
                    self.cap = cv2.VideoCapture(selected_idx, backend)

                    if self.cap.isOpened():
                        for _ in range(3):
                            self.cap.read()
                            await asyncio.sleep(0.1)
                        
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

    async def _desktop_camera_loop(self):
        while self.is_running:
            if getattr(self, 'is_paused', False):
                await asyncio.sleep(0.1)
                continue # Nếu đang dừng thì bỏ qua việc đọc khung hình
            
            if getattr(self, 'cap', None) and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    face_crop_base64 = None
                    
                    if mp_face_detection:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        results = self.face_detection.process(rgb_frame)
                        
                        if results.detections:
                            for detection in results.detections:
                                bboxC = detection.location_data.relative_bounding_box
                                ih, iw, _ = frame.shape
                                x, y = int(bboxC.xmin * iw), int(bboxC.ymin * ih)
                                w, h = int(bboxC.width * iw), int(bboxC.height * ih)
                                
                                padding_y = int(h * 0.2)
                                padding_x = int(w * 0.1)
                                start_y, end_y = max(0, y - padding_y), min(ih, y + h + padding_y)
                                start_x, end_x = max(0, x - padding_x), min(iw, x + w + padding_x)
                                
                                face_crop = frame[start_y:end_y, start_x:end_x]
                                
                                if face_crop.size > 0:
                                    _, buffer = cv2.imencode('.jpg', face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                                    face_crop_base64 = base64.b64encode(buffer).decode('utf-8')
                                
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                cv2.putText(frame, "Face Detected", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    _, buffer_display = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                    b64_str = base64.b64encode(buffer_display).decode('utf-8')
                    

                    self.camera_module.src = f"data:image/jpeg;base64,{b64_str}"
                    
                    try:
                        self.camera_module.update()
                    except Exception as e:
                        print(f"Lỗi update Flet UI: {e}")
                        
                    if face_crop_base64 and self.on_frame:
                        await self.on_frame(face_crop_base64)
                else:
                    print("Không đọc được frame từ Camera!")
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