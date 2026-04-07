import flet as ft
import json

from core.theme import current_theme

class SettingsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        self.user_name = "Đang tải..."
        self.content = self.build_ui()

    def apply_theme(self):
        """Vẽ lại màu sắc UI khi đổi Theme"""
        self.content = self.build_ui()
        if self.page: self.update()

    def did_mount(self):
        self.app_page.run_task(self.load_user_data)

    def build_ui(self):
        def make_card(content):
            return ft.Container(
                content=content, padding=20, 
                bgcolor=current_theme.surface_color, border_radius=16, 
                border=ft.Border.all(1, current_theme.divider_color)
            )

        ai_settings_card = make_card(
            content=ft.Column([
                ft.Text("THIẾT LẬP NHẬN DẠNG", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.Divider(color=current_theme.divider_color),
                
                ft.Text("Tỷ lệ chính xác nhận dạng khuôn mặt: (Khuyên dùng mức 0.6)", size=14, weight=ft.FontWeight.W_500, color=current_theme.secondary),
                ft.Slider(min=0, max=1, divisions=10, value=0.6, label="{value}", active_color=current_theme.accent, inactive_color=current_theme.divider_color, thumb_color=current_theme.primary),
                
                ft.Container(height=10),
                
                ft.Row([
                    ft.Text("Hiển thị hình ảnh nhận dạng trong thời gian thực:", expand=True, size=13, color=current_theme.text_main),
                    ft.Switch(value=True, active_color=current_theme.secondary, thumb_color=current_theme.surface_color)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Row([
                    ft.Text("Lưu trữ nhận dạng khuôn mặt nếu như dữ liệu đạt mức tốt nhất:", expand=True, size=13, color=current_theme.text_main),
                    ft.Switch(value=False, active_color=current_theme.secondary, thumb_color=current_theme.surface_color)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Row([
                    ft.Text("Cảnh báo âm thanh khi nhận dạng:", expand=True, size=13, color=current_theme.text_main),
                    ft.Switch(value=False, active_color=current_theme.secondary, thumb_color=current_theme.surface_color)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(height=15),
                ft.Row([
                    ft.Button(content=ft.Text("Cài lại", color=current_theme.text_main), bgcolor=current_theme.surface_variant),
                    ft.Button(content=ft.Text("LƯU", color=current_theme.bg_color, weight=ft.FontWeight.BOLD), bgcolor=current_theme.secondary)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ])
        )

        account_settings_card = make_card(
            content=ft.Column([
                ft.Text("THIẾT LẬP CHUNG", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.Row([
                    ft.Text("Username:", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
                    ft.Container(
                        content=ft.Text(self.user_name, color=current_theme.secondary, weight=ft.FontWeight.BOLD),
                        bgcolor=current_theme.surface_variant, padding=10, border_radius=8, expand=True,
                        border=ft.Border.all(1, current_theme.divider_color)
                    )
                ]),
                
                ft.Container(height=15),
                ft.Text("THIẾT LẬP MẬT KHẨU", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                
                ft.TextField(label="Nhập mật khẩu mới", password=True, can_reveal_password=True, bgcolor=current_theme.surface_variant, border_color=current_theme.divider_color, focused_border_color=current_theme.primary, color=current_theme.text_main, height=45, text_size=13),
                ft.TextField(label="Nhập lại mật khẩu mới", password=True, can_reveal_password=True, bgcolor=current_theme.surface_variant, border_color=current_theme.divider_color, focused_border_color=current_theme.primary, color=current_theme.text_main, height=45, text_size=13),
                
                ft.Container(height=10),
                ft.Row([
                    ft.Button(content=ft.Text("LƯU THAY ĐỔI", color=current_theme.bg_color, weight=ft.FontWeight.BOLD), bgcolor=current_theme.accent)
                ], alignment=ft.MainAxisAlignment.END)
            ])
        )

        settings_content = ft.ResponsiveRow([
            ft.Column([ai_settings_card], col={"sm": 12, "md": 7}),
            ft.Column([account_settings_card], col={"sm": 12, "md": 5}),
        ], expand=True, spacing=15, run_spacing=15) 
        
        return ft.Column([ft.Container(height=5), settings_content, ft.Container(height=30)], scroll=ft.ScrollMode.AUTO, expand=True)

    async def load_user_data(self):
        try:
            prefs = ft.SharedPreferences()
            session_str = await prefs.get("user_session")
            if session_str:
                session_data = json.loads(session_str)
                self.user_name = session_data.get("name", "Unknown")
                self.apply_theme() # Cập nhật lại UI sau khi có tên user
        except Exception as e:
            print(f"Lỗi tải dữ liệu Settings: {e}")