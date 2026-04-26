# Client/core/device_manager.py
import flet as ft
import uuid

class DeviceManager:
    _instance = None

    # Singleton an toàn
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Khởi tạo các biến dữ liệu
        self.device_id = None
        self.client_version = "1.0.0"
        self.platform = "UNKNOWN"
        self.location = "Đang lấy vị trí..."
        self.is_mobile = False

    async def init_device(self, page: ft.Page):
        """Khởi tạo thông tin thiết bị (chỉ gọi 1 lần ở main.py)"""
        self.platform = page.platform.name if page.platform else "UNKNOWN"
        self.is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        
        prefs = ft.SharedPreferences()
        stored_id = await prefs.get("device_id")
        
        if not stored_id:
            # Tạo Device ID gắn cứng
            stored_id = f"{self.platform}_{uuid.uuid4().hex[:12]}"
            await prefs.set("device_id", stored_id)
            
        self.device_id = stored_id

    # ĐÃ XÓA HÀM request_startup_permissions VÌ KHÔNG CẦN THIẾT NỮA

    def update_location(self, current_location: str):
        """Cập nhật vị trí khi Geolocator đọc xong"""
        self.location = current_location

    def get_headers(self) -> dict:
        return {
            "X-Device-ID": self.device_id or "unknown_device",
            "X-Client-Version": self.client_version,
            "X-Platform": self.platform
        }

    def get_metadata_payload(self) -> dict:
        return {
            "device_id": self.device_id or "unknown_device",
            "client_version": self.client_version,
            "vitri": self.location
        }