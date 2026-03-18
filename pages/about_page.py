import flet as ft
import asyncio
from flet import UrlLauncher

from components.options.alert_dialog import show_alert_dialog
from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR

class AboutPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        self.content = self.build_ui()
        
    async def open_github(e):
        await UrlLauncher().launch_url(
            "https://github.com/NCH2024/AuEdu-Multi-PlatForm.git"
        )
        
    async def open_settings(e):
        await UrlLauncher().launch_url(
            "app-settings:"
        )
        
    async def open_mail(e):
        await UrlLauncher().launch_url(
            "mailto:chanhhiep.vn+auedu@gmail.com"
            "?subject=Hỗ trợ ứng dụng AuEdu"
            "&body=Chào nhà phát triển, mình cần hỗ trợ về..."
        )
        
    def build_ui(self):
        # ==========================================
        # KHỐI 1: LOGO VÀ THÔNG TIN CHÍNH
        # ==========================================
        info_card = get_glass_container(
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                controls=[
                    # Logo bo tròn góc nhẹ nhàng
                    ft.Container(
                        content=ft.Image(src="splash.png", width=150, height=150, fit=ft.BoxFit.CONTAIN),
                    ),
                    
                    ft.Text("AuEdu Multi FlatForm", size=22, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ft.Text("Phiên bản: 1.0.0 (Release Build)", size=13, color=ft.Colors.GREY_600, weight=ft.FontWeight.W_500),
                    
                    ft.Divider(color=ft.Colors.BLACK_12, height=20),
                    
                    ft.Text("Phần mềm điểm danh tự động bằng công nghệ nhận dạng khuôn mặt AI. Được thiết kế chuyên biệt để mang lại trải nghiệm điểm danh độ trễ thấp và bảo mật cao.", 
                            text_align=ft.TextAlign.CENTER, size=13, color=ft.Colors.BLACK_87),
                    
                    ft.Container(height=5),
                    ft.Text("Phát triển bởi: Nguyễn Chánh Hiệp (223408)", size=14, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ft.Text("Lớp 22TIN-TT", size=12, weight=ft.FontWeight.W_500, color=SECONDARY_COLOR),
                    ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", size=12, weight=ft.FontWeight.W_400, color=ft.Colors.GREY_600),
                    
                    ft.Container(height=10),
                    
                    # Nút Kiểm tra cập nhật nổi bật
                    ft.Button(
                        content=ft.Row([
                            ft.Icon(ft.Icons.UPDATE_ROUNDED, size=18, color=ft.Colors.WHITE), 
                            ft.Text("Kiểm tra cập nhật", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=SECONDARY_COLOR,
                        height=45,
                        width=250,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=25)),
                        on_click=lambda e: show_alert_dialog(self, "Cập nhật", 
                                                             ft.Text("Phiên bản đang là phiên bản mới nhất!", size=14))
                    )
                ]
            )
        )

        # ==========================================
        # KHỐI 2: CÁC NÚT TÙY CHỌN (Quyền & Giấy phép)
        # ==========================================
        action_card = get_glass_container(
            padding=10,
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.SECURITY_ROUNDED, color=SECONDARY_COLOR),
                        title=ft.Text("Quyền ứng dụng", weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Xem các quyền truy cập Camera, Mạng...", size=12),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_settings
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, color=SECONDARY_COLOR),
                        title=ft.Text("Bản quyền phần mềm", weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Giấy phép sử dụng và điều khoản", size=12),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=lambda e: show_alert_dialog(self, "Giấy phép & Điều khoản", 
                                                             ft.Column(
                                                                tight=True,
                                                                controls=[
                                                                    ft.Text("Giấy Phép", 
                                                                            size=16, 
                                                                            weight=ft.FontWeight.BOLD,
                                                                            color=SECONDARY_COLOR),
                                                                    ft.Text("• Được hội đồng Trường Công nghệ số và Trí tuệ nhân tạo chấp thuận sử dụng trong phạm vi dự án", size=14),
                                                                    ft.Text("• Công bố rộng rãi và chấp nhận sử dụng từ người dùng thử nghiệm", size=14),
                                                                    ft.Container(height=5),
                                                                    ft.Text("Điều khoản", 
                                                                            size=16, 
                                                                            weight=ft.FontWeight.BOLD,
                                                                            color=SECONDARY_COLOR),
                                                                    ft.Text("• Xem điều khoản sữ dụng tại đường dẫn GitHub của dự án!", size=14),
                                                                    
                                                                ]
                                                             ))
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.DATA_OBJECT, color=SECONDARY_COLOR),
                        title=ft.Text("GitHub dự án AuEdu", weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Kho lưu trữ dự án và thông tin chi tiết phát hành phiên bản phần mềm", size=12),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_github
                    ),
                    ft.Divider(height=1, color=ft.Colors.BLACK_12),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.MAIL_OUTLINED, color=SECONDARY_COLOR),
                        title=ft.Text("Liên hệ với nhà phát triển", weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                        subtitle=ft.Text("Gửi thông tin và báo lỗi phần mềm qua địa chỉ Mail liên hệ", size=12),
                        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=SECONDARY_COLOR),
                        on_click=self.open_mail
                    )
                ]
            )
        )

        # Lắp ráp bố cục tổng thể
        main_layout = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                info_card,
                action_card
            ]
        )

        return main_layout


    def _show_snackbar(self, message: str):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=SECONDARY_COLOR, open=True))
        self.app_page.update()