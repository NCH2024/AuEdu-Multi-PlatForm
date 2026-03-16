import flet as ft
import flet_camera 
import asyncio
import base64

# Kiểm thử thue viện cv2 cho Desktop
try:
    import cv2
except ImportError:
    cv2 = None

class CameraView(ft.Container):
    def __init__(self, page: ft.Page, dd_camera: ft.Dropdown, is_visible=False):
        super().__init__()
        self.app_page = page
        self.dd_camera = dd_camera 
        
        self.is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        self.is_running = False 
        
        if self.is_mobile:
            self.camera_module = flet_camera.Camera()
            if is_visible:
                self.camera_module.expand = True
                self.content = self.camera_module
            else:
                self.camera_module.expand = False
                # Fix Màn hình đỏ: Ép cứng kích thước 1x1 và cắt bỏ phần tràn
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
            self.width = None
            self.height = None
        else:
            self.expand = False
            self.width = 1
            self.height = 1
            self.opacity = 0
            
        self.margin = 0
        self.padding = 0
        self.alignment = ft.Alignment(0, 0)
        self.available_cameras = []

    async def load_available_cameras(self):
        """Quét camera với sự thận trọng tối đa về ID Control."""
        # Nếu control chưa được dán lên page hoặc đã bị gỡ, tuyệt đối không gọi phần cứng
        if not self.page: return 
        
        try:
            if self.is_mobile:
                # Dùng asyncio.wait_for để không bị treo vô tận
                self.available_cameras = await asyncio.wait_for(
                    self.camera_module.get_available_cameras(), timeout=3.0
                )
                
                # Sau khi await, phải kiểm tra lại một lần nữa xem page còn đó không
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
            print(f"Bỏ qua quét camera do: {e}")

    async def start_camera(self):
        """Chỉ bật camera khi Control đã sẵn sàng."""
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
                    self.cap = cv2.VideoCapture(selected_idx)
                if cv2 and self.cap.isOpened():
                    self.is_running = True
                    self.app_page.run_task(self._desktop_camera_loop)
        except:
            pass

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
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    self.camera_module.src = frame_base64
                    try:
                        self.camera_module.update()
                    except Exception:
                        pass
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
                cap = cv2.VideoCapture(selected_idx)
                if cap.isOpened():
                    for _ in range(3):
                        ret, frame = cap.read()
                        if ret: success = True
                        await asyncio.sleep(0.1)
                    cap.release()
            return success
        except Exception:
            return False