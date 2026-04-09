import flet as ft
import flet_camera 
import asyncio
import base64

try:
    import cv2
except ImportError:
    cv2 = None

class CameraView(ft.Container):
    def __init__(self, page: ft.Page, dd_camera: ft.Dropdown, is_visible=False, on_frame=None):
        super().__init__()
        self.app_page = page
        self.dd_camera = dd_camera 
        self.on_frame = on_frame # Lưu callback lại
        
        self.is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        self.is_running = False 
        
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
            empty_black_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            self.camera_module = ft.Image(src=empty_black_image, fit=ft.BoxFit.CONTAIN, gapless_playback=True)
            
            if is_visible:
                self.camera_module.expand = True
                self.content = ft.Container(expand=True, bgcolor=ft.Colors.BLACK, alignment=ft.Alignment(0, 0), content=self.camera_module)
            else:
                self.camera_module.expand = False
                self.content = ft.Container(width=1, height=1, content=self.camera_module, clip_behavior=ft.ClipBehavior.HARD_EDGE)
            self.cap = None 
            
        if is_visible:
            self.expand = True
            self.opacity = 1
        else:
            self.expand = False
            self.width, self.height, self.opacity = 1, 1, 0
            
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
                if hasattr(self, 'cap') and self.cap:
                    self.cap.release()
                    
                if not self.is_mobile and cv2:
                    # FIX LỖI WINDOWS: Dùng CAP_DSHOW để camera mở nhanh và không bị kẹt
                    self.cap = cv2.VideoCapture(selected_idx, cv2.CAP_DSHOW)
                if cv2 and getattr(self, 'cap', None) and self.cap.isOpened():
                    self.is_running = True
                    self.app_page.run_task(self._desktop_camera_loop)
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

    async def _desktop_camera_loop(self):
        while self.is_running:
            if getattr(self, 'cap', None) and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Nén ảnh JPEG chất lượng thấp để gửi WebSocket cho nhanh (tránh nghẽn mạng)
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    self.camera_module.src = frame_base64
                    
                    try:
                        self.camera_module.update()
                    except Exception:
                        pass
                        
                    # BẮN ẢNH RA NGOÀI TRANG ĐIỂM DANH
                    if self.on_frame:
                        await self.on_frame(frame_base64)
                        
            await asyncio.sleep(0.1) # Tốc độ 10 FPS (Đủ để test AI, không làm nghẽn Server)