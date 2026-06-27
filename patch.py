import sys
import re

with open('Client/components/pages/base_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = re.compile(r'        headers = \{\"User-Agent\": \"AuEdu_PC_App \(chanhhiep\.vn@gmail\.com\)\"\}.*?except Exception as e:\s*print\(f\"Lỗi định vị: \{e\}\"\)\s*self\.location_text\.value = cached_location if cached_location else \"Lỗi kết nối\"\s*if getattr\(self\.location_text, \"page\", None\):\s*self\.location_text\.update\(\)', re.DOTALL)

replacement = '''        headers = {"User-Agent": "AuEdu_PC_App (chanhhiep.vn@gmail.com)"}
        NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&accept-language=vi"

        try:
            from core.device_manager import DeviceManager
            is_mobile = DeviceManager.get_instance().is_mobile
            
            pos = None
            # Chỉ dùng GPS thiết bị nếu là Mobile (Android/iOS)
            if is_mobile:
                try:
                    if await self.geo.is_location_service_enabled():
                        p = await self.geo.get_permission_status()
                        if p != GeolocatorPermissionStatus.ALWAYS and p != GeolocatorPermissionStatus.WHILE_IN_USE:
                            p = await self.geo.request_permission()
                        
                        if p in [GeolocatorPermissionStatus.ALWAYS, GeolocatorPermissionStatus.WHILE_IN_USE]:
                            pos = await self.geo.get_current_position()
                except Exception as e:
                    print(f"Lỗi đọc GPS trên mobile: {e}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Nếu có tọa độ GPS (từ điện thoại)
                if pos:
                    res = await client.get(NOMINATIM_URL.format(lat=pos.latitude, lon=pos.longitude), headers=headers)
                    if res.status_code == 200:
                        addr = res.json().get("address", {})
                        
                        ward = addr.get("village") or addr.get("suburb") or addr.get("quarter") or addr.get("hamlet") or addr.get("road")
                        district = addr.get("county") or addr.get("district") or addr.get("town") or addr.get("city_district")
                        province = addr.get("city") or addr.get("state") or addr.get("province")
                        
                        parts = []
                        if ward and ward not in parts: parts.append(ward)
                        if district and district not in parts: parts.append(district)
                        if province and province not in parts: parts.append(province)
                        
                        location_str = ", ".join(parts) if parts else "Việt Nam"
                        
                        DeviceManager.get_instance().update_location(location_str)
                        self.location_text.value = location_str
                        if getattr(self.location_text, "page", None): self.location_text.update()
                        
                        await prefs.set("app_location", location_str)
                        await prefs.set("app_lat", str(pos.latitude))
                        await prefs.set("app_lon", str(pos.longitude))
                        await prefs.set("last_sync_app_location", str(current_time))
                        
                        if self.geo in self.app_page.services:
                            self.app_page.services.remove(self.geo)
                            if getattr(self.app_page, "page", None): self.app_page.update()
                        return

                # Fallback: Chạy trên PC hoặc Mobile mất GPS -> Dùng IP-API
                print("Fallback to IP-API for location...")
                res = await client.get("http://ip-api.com/json/?lang=vi")
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        ward = data.get("city")
                        province = data.get("regionName")
                        
                        parts = []
                        if ward and ward not in parts: parts.append(ward)
                        if province and province not in parts: parts.append(province)
                        
                        location_str = ", ".join(parts) if parts else "Việt Nam"
                        
                        DeviceManager.get_instance().update_location(location_str)
                        self.location_text.value = location_str
                        if getattr(self.location_text, "page", None): self.location_text.update()
                        
                        await prefs.set("app_location", location_str)
                        await prefs.set("app_lat", str(data.get("lat", "")))
                        await prefs.set("app_lon", str(data.get("lon", "")))
                        await prefs.set("last_sync_app_location", str(current_time))
                        
                        # Xóa geo_service nếu không dùng đến
                        if getattr(self, 'geo', None) and self.geo in getattr(self.app_page, 'services', []):
                            self.app_page.services.remove(self.geo)
                            if getattr(self.app_page, "page", None): self.app_page.update()
                        return
                
                self.location_text.value = cached_location if cached_location else "Vị trí không xác định"
                if getattr(self.location_text, "page", None): self.location_text.update()

        except Exception as e:
            print(f"Lỗi định vị: {e}")
            self.location_text.value = cached_location if cached_location else "Lỗi kết nối"
            if getattr(self.location_text, "page", None): self.location_text.update()'''

new_content = pattern.sub(replacement, content)

if content == new_content:
    print("Error: Pattern not matched!")
else:
    with open('Client/components/pages/base_dashboard.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patch applied successfully.")
