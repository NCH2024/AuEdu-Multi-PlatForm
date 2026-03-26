# components/options/open_browser.py
import flet as ft
from flet import UrlLauncher

async def open_browser(page: ft.Page, url: str, title: str = "Trình duyệt"):
    if not url or str(url).strip() == "" or str(url).strip() == "None":
        return

    url = str(url).strip()
    supported_platforms = [ft.PagePlatform.IOS, ft.PagePlatform.ANDROID, ft.PagePlatform.MACOS]
    
    # Nếu là Mobile/Mac và có thư viện webview
    if page.platform in supported_platforms:
        # Lưu trữ URL và Title vào session để lấy ở trang BrowserPage
        page.session.set("browser_url", url)
        page.session.set("browser_title", title)
        await page.push_route("/user/browser")
    else:
        # Fallback mở trình duyệt mặc định của Windows/Web
        try:
            await UrlLauncher().launch_url(url)
        except Exception as e:
            print(f"Lỗi mở URL: {e}")