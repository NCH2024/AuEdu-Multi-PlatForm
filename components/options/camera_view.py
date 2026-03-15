import flet as ft
import flet_camera 
import cv2
import asyncio

class CameraView(ft.Container):
    def __init__(self, page: ft.Page, dd_camera: ft.Dropdown):
        super().__init__()
        self.app_page = page
        self.dd_camera = dd_camera 
        
        self.is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        
        # ==========================================
        # ẨN : Vẫn tồn tại trên DOM để chống lỗi, nhưng vô hình
        # ==========================================
        if self.is_mobile:
            self.camera_module = flet_camera.Camera(expand=True)
            self.content = self.camera_module
        else:
            self.camera_module = ft.Container() # Desktop không cần UI
            self.content = self.camera_module
            
        self.width = 1
        self.height = 1
        self.opacity = 0 # Làm cho nó tàng hình hoàn toàn
        self.margin = 0
        self.padding = 0

        self.available_cameras = []

    # Hàm quét thiết bị (Giữ nguyên như cũ)
    async def load_available_cameras(self):
        try:
            if self.is_mobile:
                self.available_cameras = await self.camera_module.get_available_cameras()
                if self.available_cameras:
                    options = []
                    for i, cam in enumerate(self.available_cameras):
                        lens_dir = str(getattr(cam, 'lens_direction', '')).lower()
                        name = f"Camera trước ({cam.name})" if 'front' in lens_dir else f"Camera sau ({cam.name})" if 'back' in lens_dir else f"Camera ngoài ({cam.name})"
                        options.append(ft.dropdown.Option(key=str(i), text=name))
                    self.dd_camera.options = options
                    self.dd_camera.value = "1" if len(self.available_cameras) > 1 else "0"
            else:
                self.dd_camera.options = [ft.dropdown.Option(key="0", text="PC Webcam Mặc định")]
                self.dd_camera.value = "0"
            self.dd_camera.update()
        except Exception as e:
            raise Exception(f"Lỗi nhận diện thiết bị: {e}")

    # ==========================================
    # HÀM KIỂM TRA CẢM BIẾN NGẦM (Thay thế cho start_camera cũ)
    # ==========================================
    async def test_sensor(self):
        try:
            selected_idx = int(self.dd_camera.value) if self.dd_camera.value else 0
            success = False

            if self.is_mobile:
                if not self.available_cameras: return False
                cam_to_use = self.available_cameras[selected_idx]
                
                # 1. Khởi động cảm biến
                await self.camera_module.initialize(cam_to_use, flet_camera.ResolutionPreset.MEDIUM)
                
                # 2. Đợi 1 giây để ống kính lấy sáng và Focus
                await asyncio.sleep(1.0)
                
                # 3. Trích xuất thử 1 tấm ảnh
                pic_bytes = await self.camera_module.take_picture()
                if pic_bytes: 
                    success = True
                    
                # 4. Tắt cảm biến
                await self.camera_module.pause_preview()
            else:
                # Test trên Desktop bằng OpenCV
                cap = cv2.VideoCapture(selected_idx)
                if cap.isOpened():
                    # Đọc thử 3 khung hình liên tiếp để chắc chắn luồng video không bị nghẽn
                    for _ in range(3):
                        ret, frame = cap.read()
                        if ret: success = True
                        await asyncio.sleep(0.1)
                    cap.release()
                    
            return success
        except Exception as e:
            print(f"Lỗi test_sensor: {e}")
            return False