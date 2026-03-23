import flet as ft
from core.theme import current_theme
from flet import UrlLauncher

try:
    import flet_webview as fv
except ImportError:
    fv = None

async def open_browser(page: ft.Page, url: str, title: str = "Trình duyệt"):
    if not url or str(url).strip() == "" or str(url).strip() == "None":
        return

    url = str(url).strip()
    supported_platforms = [ft.PagePlatform.IOS, ft.PagePlatform.ANDROID, ft.PagePlatform.MACOS]
    
    if page.platform in supported_platforms and fv is not None:
        def close_wv(e):
            wv_dlg.open = False
            page.update()
            
        wv_dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Text(title, weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.IconButton(ft.Icons.CLOSE, icon_color=current_theme.text_main, on_click=close_wv)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            content=ft.Container(
                content=fv.WebView(url=url, expand=True),
                width=800, height=600,
                border_radius=8,
                clip_behavior=ft.ClipBehavior.HARD_EDGE
            ),
            content_padding=0,
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=current_theme.surface_color
        )
        page.overlay.append(wv_dlg)
        wv_dlg.open = True
        page.update()
    else:
        # Flet 0.82.2 hỗ trợ phương thức async launch_url trực tiếp trên đối tượng page
        try:
            await UrlLauncher().launch_url(url)
        except Exception as e:
            print(f"Lỗi mở URL: {e}")