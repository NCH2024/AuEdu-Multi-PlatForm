import flet as ft
import asyncio
from flet import UrlLauncher

from components.options.alert_dialog import show_alert_dialog
from core.theme import adaptive_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR

class AboutPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        self.content = self.build_ui()
        
    async def open_github(self, e):
        await UrlLauncher().launch_url(
            "https://github.com/NCH2024/AuEdu-Multi-PlatForm.git"
        )
        
    async def open_settings(self, e):
        await UrlLauncher().launch_url(
            "app-settings:"
        )
        
    async def open_mail(self, e):
        await UrlLauncher().launch_url(
            "mailto:chanhhiep.vn+auedu@gmail.com"
            "?subject=Hỗ trợ ứng dụng AuEdu"
            "&body=Chào nhà phát triển, mình cần hỗ trợ về..."
        )
        
    def build_ui(self):
        info_card = adaptive_container(
            page=self.app_page,
            padding=ft.Padding(20, 30, 20, 30),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Container(
                        content=ft.Image(src="splash.png", width=120, height=120, fit=ft.BoxFit.CONTAIN),
                    ),
                    ft.Text("AuEdu Multi-Platform", size=22, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ft.Text("Phiên bản: 1.0.0 (Release Build)", size=12, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500),
                    
                    ft.Divider(color=ft.Colors.BLACK_12, height=20),
                    
                    ft.Text("Phần mềm điểm danh tự động bằng công nghệ nhận dạng khuôn mặt AI. Được thiết kế chuyên biệt để mang lại trải nghiệm điểm danh độ trễ thấp và bảo mật cao.", 
                            text_align=ft.TextAlign.CENTER, size=13, color=ft.Colors.BLACK_87),
                    
                    ft.Container(height=5),
                    ft.Text("Phát triển bởi: Nguyễn Chánh Hiệp (223408)", size=13, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ft.Text("Lớp 22TIN-TT", size=12, weight=ft.FontWeight.W_500, color=SECONDARY_COLOR),
                    ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", size=12, weight=ft.FontWeight.W_400, color=ft.Colors.GREY_600),
                    
                    ft.Container(height=10),
                    
                    ft.Button(
                        content=ft.Row([
                            ft.Icon(ft.Icons.UPDATE_ROUNDED, size=18, color=ft.Colors.WHITE), 
                            ft.Text("Kiểm tra cập nhật", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=SECONDARY_COLOR,
                        height=45,
                        width=220,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25)),
                        on_click=lambda e: show_alert_dialog(self, "Cập nhật", 
                                                             ft.Text("Phiên bản đang là phiên bản mới nhất!", size=13))
                    )
                ]
            )
        )

        action_card = adaptive_container(
            page=self.app_page,
            padding=ft.Padding(5, 10, 5, 10),
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SECURITY_ROUNDED, color=SECONDARY_COLOR),
                        title=ft.Text("Quyền ứng dụng", weight=ft.FontWeight.BOLD, size=13, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Xem các quyền truy cập Camera, Mạng...", size=11),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_settings
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color=SECONDARY_COLOR),
                        title=ft.Text("Bản quyền phần mềm", weight=ft.FontWeight.BOLD, size=13, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Giấy phép sử dụng và điều khoản", size=11),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=lambda e: show_alert_dialog(self, "Giấy phép & Điều khoản", 
                                                             ft.Column(
                                                                 tight=True,
                                                                 spacing=5,
                                                                 controls=[
                                                                     ft.Text("Giấy Phép", size=14, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                                                                     ft.Text("• Được hội đồng Trường Công nghệ số và Trí tuệ nhân tạo chấp thuận sử dụng trong phạm vi dự án", size=12),
                                                                     ft.Text("• Công bố rộng rãi và chấp nhận sử dụng từ người dùng thử nghiệm", size=12),
                                                                     ft.Container(height=5),
                                                                     ft.Text("Điều khoản", size=14, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                                                                     ft.Text("• Xem điều khoản sử dụng tại đường dẫn GitHub của dự án!", size=12),
                                                                 ]
                                                             ))
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DATA_OBJECT, color=SECONDARY_COLOR),
                        title=ft.Text("GitHub dự án AuEdu", weight=ft.FontWeight.BOLD, size=13, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Kho lưu trữ dự án và thông tin chi tiết", size=11),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_github
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MAIL_OUTLINED, color=SECONDARY_COLOR),
                        title=ft.Text("Liên hệ phát triển", weight=ft.FontWeight.BOLD, size=13, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Gửi thông tin và báo lỗi qua Mail", size=11),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_mail
                    )
                ]
            )
        )

        main_layout = ft.ResponsiveRow(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    col={"sm": 12, "md": 8, "lg": 6, "xl": 5},
                    spacing=15,
                    controls=[
                        info_card,
                        action_card
                    ]
                )
            ]
        )

        return main_layout

    def _show_snackbar(self, message: str):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=SECONDARY_COLOR, open=True))
        self.app_page.update()