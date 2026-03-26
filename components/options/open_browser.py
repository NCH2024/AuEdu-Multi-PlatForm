# components/options/open_browser.py
import flet as ft
from flet import UrlLauncher
from components.options.top_notification import TopNotification

async def open_browser(page: ft.Page, url: str, title: str = "Trình duyệt"):
    print(f"[DEBUG - Browser] Yêu cầu mở URL: {url} | Tiêu đề: {title}")
    
    if not url or str(url).strip() in ("", "None"):
        print("[DEBUG - Browser] Cảnh báo: URL rỗng hoặc None, hủy thao tác mở trình duyệt.")
        return

    url = str(url).strip()
    
    try:
        print(f"[DEBUG - Browser] Đang thực thi UrlLauncher().launch_url({url})...")
        # Sử dụng đúng chuẩn API của Flet 0.82.2 giống với about_page.py
        await UrlLauncher().launch_url(url)
        print("[DEBUG - Browser] Gọi UrlLauncher thành công.")
    except Exception as e:
        print(f"[LỖI CRITICAL - Browser] UrlLauncher thất bại. Chi tiết lỗi: {e}")