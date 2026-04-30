import flet as ft
import asyncio
import httpx
from core.theme import current_theme
from components.options.top_notification import show_top_notification

class SystemSettingsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 20
        
        # UI Components
        self.base_api_url = ft.TextField(label="Đường dẫn API Backend", expand=True)
        self.ws_url = ft.TextField(label="Đường dẫn WebSocket", expand=True)
        
        self.global_ai_threshold = ft.Slider(min=0.1, max=0.99, divisions=89, label="{value}")
        self.global_fiqa_threshold = ft.Slider(min=0.1, max=0.99, divisions=89, label="{value}")
        self.strict_mode = ft.Switch(label="Chế độ bảo mật nghiêm ngặt (Yêu cầu xác thực mạng nội bộ)")

        self.save_btn = ft.Button("LƯU CẤU HÌNH", icon=ft.Icons.SAVE, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_config)

        self.content = ft.Column([
            ft.Text("CÀI ĐẶT HỆ THỐNG", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Divider(color=current_theme.divider_color),
            
            ft.Text("Cấu hình Kết nối", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Row([self.base_api_url, self.ws_url]),
            
            ft.Container(height=10),
            ft.Text("Cấu hình AI Mặc định (Global)", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Text("Cosine Similarity Threshold:", color=current_theme.text_muted),
            self.global_ai_threshold,
            
            ft.Text("FIQA Threshold:", color=current_theme.text_muted),
            self.global_fiqa_threshold,
            
            self.strict_mode,
            
            ft.Container(height=20),
            self.save_btn
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def did_mount(self):
        self.app_page.run_task(self.load_config)

    async def load_config(self):
        try:
            await asyncio.sleep(0.5)
            # Dummy data cho đến khi có API
            self.base_api_url.value = "http://localhost:8000/api"
            self.ws_url.value = "ws://localhost:8000/ws"
            self.global_ai_threshold.value = 0.6
            self.global_fiqa_threshold.value = 0.5
            self.strict_mode.value = True
            
            self.update()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi tải cấu hình: {e}", ft.Colors.RED)

    def save_config(self, e):
        self.app_page.run_task(self._save_config_async)

    async def _save_config_async(self):
        self.save_btn.disabled = True
        self.update()
        try:
            await asyncio.sleep(1)
            show_top_notification(self.app_page, "Cập nhật cấu hình thành công!", ft.Colors.GREEN)
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi lưu cấu hình: {e}", ft.Colors.RED)
        finally:
            self.save_btn.disabled = False
            self.update()

    def apply_theme(self):
        self.content.controls[0].color = current_theme.text_main
        self.content.controls[1].color = current_theme.divider_color
        self.content.controls[2].color = current_theme.text_main
        self.content.controls[5].color = current_theme.text_main
        self.content.controls[6].color = current_theme.text_muted
        self.content.controls[8].color = current_theme.text_muted
        self.save_btn.bgcolor = current_theme.primary
        self.update()
