import flet as ft
from components.pages.base_dashboard import BaseDashboard
from components.pages.page_frame import PageFrame
from core.theme import get_glass_container, PRIMARY_COLOR

class SettingsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        # Lấy tên user từ Session
        session_data = self.app_page.session.store.get("user_session") or {}
        user_name = session_data.get("name", "Unknown")

        # ==========================================
        # CỘT TRÁI: THIẾT LẬP NHẬN DẠNG (AI)
        # ==========================================
        ai_settings_card = get_glass_container(
            content=ft.Column([
                ft.Text("THIẾT LẬP NHẬN DẠNG", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=13),
                ft.Divider(color=ft.Colors.BLACK_12),
                
                ft.Text("Tỷ lệ chính xác nhận dạng khuôn mặt: (Khuyên dùng mức 0.6)", size=14, weight=ft.FontWeight.W_500),
                # Thanh trượt Slider chuẩn Flet
                ft.Slider(min=0, max=1, divisions=10, value=0.6, label="{value}", active_color=ft.Colors.BLUE_600),
                
                ft.Container(height=10),
                
                # Các công tắc Switch
                ft.Row([
                    ft.Text("Hiển thị hình ảnh nhận dạng trong thời gian thực:", expand=True, size=13),
                    ft.Switch(value=True, active_color=ft.Colors.GREEN_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Row([
                    ft.Text("Lưu trữ nhận dạng khuôn mặt nếu như dữ liệu đạt mức tốt nhất:", expand=True, size=13),
                    ft.Switch(value=False, active_color=ft.Colors.GREEN_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Row([
                    ft.Text("Cảnh báo âm thanh khi nhận dạng:", expand=True, size=13),
                    ft.Switch(value=False, active_color=ft.Colors.GREEN_600)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(height=15),
                ft.Row([
                    ft.Button(content=ft.Text("Cài lại", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_600),
                    ft.Button(content=ft.Text("LƯU", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.GREEN_500)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ])
        )

        # ==========================================
        # CỘT PHẢI: CÀI ĐẶT TÀI KHOẢN
        # ==========================================
        account_settings_card = get_glass_container(
            content=ft.Column([
                ft.Text("THIẾT LẬP CHUNG", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=13),
                ft.Row([
                    ft.Text("Username:", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(user_name, color=PRIMARY_COLOR, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.WHITE, padding=10, border_radius=5, expand=True
                    )
                ]),
                
                ft.Container(height=15),
                ft.Text("THIẾT LẬP MẬT KHẨU", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=13),
                
                ft.TextField(label="Nhập mật khẩu mới", password=True, can_reveal_password=True, bgcolor=ft.Colors.WHITE, height=45, text_size=13),
                ft.TextField(label="Nhập lại mật khẩu mới", password=True, can_reveal_password=True, bgcolor=ft.Colors.WHITE, height=45, text_size=13),
                
                ft.Container(height=10),
                ft.Row([
                    ft.Button(content=ft.Text("LƯU THAY ĐỔI", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_500)
                ], alignment=ft.MainAxisAlignment.END)
            ])
        )

        # Lắp ráp Responsive
        settings_content = ft.ResponsiveRow([
            ft.Column([ai_settings_card], col={"sm": 12, "md": 7}),
            ft.Column([account_settings_card], col={"sm": 12, "md": 5}),
        ], expand=True)

        # Bọc vào Khung PageFrame xịn sò của em
        framed_layout = PageFrame(
            page=self.app_page, 
            page_title="CÀI ĐẶT PHẦN MỀM",
            main_content=settings_content
        )

        self.content = BaseDashboard(page=self.app_page, active_route="/user/settings", main_content=framed_layout)