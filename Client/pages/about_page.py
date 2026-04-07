import flet as ft
import asyncio
from flet import UrlLauncher

from components.options.alert_dialog import show_alert_dialog
from core.theme import current_theme

class AboutPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        self.content = self.build_ui()
        
    def apply_theme(self):
        """Vẽ lại màu sắc UI khi đổi Theme"""
        self.content = self.build_ui()
        if self.page: self.update()

    async def open_github(self, e):
        await UrlLauncher().launch_url("https://github.com/NCH2024/AuEdu-Multi-PlatForm.git")
        
    async def open_settings(self, e):
        await UrlLauncher().launch_url("app-settings:")
        
    async def open_mail(self, e):
        await UrlLauncher().launch_url(
            "mailto:chanhhiep.vn+auedu@gmail.com"
            "?subject=Hỗ trợ ứng dụng AuEdu"
            "&body=Chào nhà phát triển, mình cần hỗ trợ về..."
        )
        
    def build_ui(self):
        def make_card(content, padding_val):
            return ft.Container(
                content=content, padding=padding_val,
                bgcolor=current_theme.surface_color, border_radius=16,
                border=ft.Border.all(1, current_theme.divider_color)
            )

        info_card = make_card(
            padding_val=ft.Padding(20, 30, 20, 30),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                controls=[
                    ft.Image(src="splash.png", width=120, height=120, fit=ft.BoxFit.CONTAIN),
                    ft.Text("AuEdu Multi-Platform", size=22, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                    ft.Text("Phiên bản: 1.0.0 (Release Build)", size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500),
                    
                    ft.Divider(color=current_theme.divider_color, height=20),
                    
                    ft.Text("Phần mềm điểm danh tự động bằng công nghệ nhận dạng khuôn mặt AI. Được thiết kế chuyên biệt để mang lại trải nghiệm điểm danh độ trễ thấp và bảo mật cao.", text_align=ft.TextAlign.CENTER, size=13, color=current_theme.text_main),
                    
                    ft.Container(height=5),
                    ft.Text("Phát triển bởi: Nguyễn Chánh Hiệp (223408)", size=13, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                    ft.Text("Lớp 22TIN-TT", size=12, weight=ft.FontWeight.W_500, color=current_theme.secondary),
                    ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", size=12, weight=ft.FontWeight.W_400, color=current_theme.text_muted),
                    
                    ft.Container(height=10),
                    
                    ft.Button(
                        content=ft.Row([
                            ft.Icon(ft.Icons.UPDATE_ROUNDED, size=18, color=current_theme.bg_color), 
                            ft.Text("Kiểm tra cập nhật", color=current_theme.bg_color, weight=ft.FontWeight.BOLD, size=13)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=current_theme.secondary, height=45, width=220,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25)),
                        on_click=lambda e: show_alert_dialog(self, "Cập nhật", ft.Text("Phiên bản đang là phiên bản mới nhất!", size=13, color=current_theme.text_main))
                    )
                ]
            )
        )

        action_card = make_card(
            padding_val=ft.Padding(5, 10, 5, 10),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SECURITY_ROUNDED, color=current_theme.secondary),
                        title=ft.Text("Quyền ứng dụng", weight=ft.FontWeight.BOLD, size=13, color=current_theme.secondary),
                        subtitle=ft.Text("Xem các quyền truy cập Camera, Mạng...", size=11, color=current_theme.text_muted),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=current_theme.secondary),
                        on_click=self.open_settings
                    ),
                    ft.Divider(height=1, color=current_theme.divider_color),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color=current_theme.secondary),
                        title=ft.Text("Bản quyền phần mềm", weight=ft.FontWeight.BOLD, size=13, color=current_theme.secondary),
                        subtitle=ft.Text("Giấy phép sử dụng và điều khoản", size=11, color=current_theme.text_muted),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=current_theme.secondary),
                        on_click=lambda e: show_alert_dialog(self, "Giấy phép & Điều khoản", 
                                                             ft.Column(
                                                                 tight=True, spacing=5,
                                                                 controls=[
                                                                     ft.Text("Giấy Phép", size=14, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                                                                     ft.Text("• Được hội đồng Trường Công nghệ số và Trí tuệ nhân tạo chấp thuận sử dụng trong phạm vi dự án", size=12, color=current_theme.text_main),
                                                                     ft.Text("• Công bố rộng rãi và chấp nhận sử dụng từ người dùng thử nghiệm", size=12, color=current_theme.text_main),
                                                                     ft.Container(height=5),
                                                                     ft.Text("Điều khoản", size=14, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                                                                     ft.Text("• Xem điều khoản sử dụng tại đường dẫn GitHub của dự án!", size=12, color=current_theme.text_main),
                                                                 ]
                                                             ))
                    ),
                    ft.Divider(height=1, color=current_theme.divider_color),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DATA_OBJECT, color=current_theme.secondary),
                        title=ft.Text("GitHub dự án AuEdu", weight=ft.FontWeight.BOLD, size=13, color=current_theme.secondary),
                        subtitle=ft.Text("Kho lưu trữ dự án và thông tin chi tiết", size=11, color=current_theme.text_muted),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=current_theme.secondary),
                        on_click=self.open_github
                    ),
                    ft.Divider(height=1, color=current_theme.divider_color),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MAIL_OUTLINED, color=current_theme.secondary),
                        title=ft.Text("Liên hệ phát triển", weight=ft.FontWeight.BOLD, size=13, color=current_theme.secondary),
                        subtitle=ft.Text("Gửi thông tin và báo lỗi qua Mail", size=11, color=current_theme.text_muted),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=current_theme.secondary),
                        on_click=self.open_mail
                    )
                ]
            )
        )

        main_layout = ft.ResponsiveRow(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Column(col={"sm": 12, "md": 8, "lg": 6, "xl": 5}, spacing=15, controls=[info_card, action_card])
            ]
        )

        return ft.Column([ft.Container(height=5), main_layout, ft.Container(height=30)], scroll=ft.ScrollMode.AUTO, expand=True)

    def _show_snackbar(self, message: str):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message, color=current_theme.bg_color), bgcolor=current_theme.secondary, open=True))
        self.app_page.update()