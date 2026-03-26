# pages/user/browser_page.py
import flet as ft
from core.theme import current_theme
try:
    import flet_webview as fv
except ImportError:
    fv = None

class BrowserPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0
        
        self.url = self.app_page.session.get("browser_url") or "https://google.com"
        self.browser_title = self.app_page.session.get("browser_title") or "Trình duyệt AuEdu"
        self.content = self.build_ui()

    def build_ui(self):
        header = ft.Row([
            ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color=current_theme.text_main,
                on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/news")
            ),
            ft.Text(self.browser_title, size=16, weight=ft.FontWeight.BOLD, color=current_theme.text_main, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        ], alignment=ft.MainAxisAlignment.START)

        # Trình duyệt
        webview_content = ft.Container(expand=True, alignment=ft.Alignment(0,0))
        if fv is not None:
            webview_content.content = fv.WebView(url=self.url, expand=True)
        else:
            webview_content.content = ft.Text("Thiết bị không hỗ trợ WebView nội bộ.", color=ft.Colors.RED)

        return ft.Column([
            header,
            ft.Divider(height=1, color=current_theme.divider_color),
            webview_content
        ], expand=True, spacing=0)