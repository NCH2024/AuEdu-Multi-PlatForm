import flet as ft
import httpx
import asyncio
from core.config import get_supabase_client, SUPABASE_URL, SUPABASE_KEY

class LoginPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        self.tf_username = ft.TextField(
            label="Tên đăng nhập", 
            border_radius=8, 
            bgcolor=ft.Colors.WHITE,
            color=ft.Colors.BLACK_87,
            border_color=ft.Colors.TRANSPARENT,
            filled=True,
            height=50,
            text_size=14
        )
        
        self.tf_password = ft.TextField(
            label="Mật khẩu", 
            password=True, 
            can_reveal_password=True, 
            border_radius=8, 
            bgcolor=ft.Colors.WHITE,
            color=ft.Colors.BLACK_87,
            border_color=ft.Colors.TRANSPARENT,
            filled=True,
            height=50,
            text_size=14
        )
        
        # ĐÃ SỬA: Cập nhật thành ft.Button và dùng content theo đúng em đã fix!
        self.btn_login = ft.Button(
            content=ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor="#008000", 
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            height=45,
            width=320, 
            on_click=self.handle_login
        )

        self.left_panel = ft.Container(
            width=400, 
            bgcolor="#041E3A", 
            padding=40,
            content=ft.Column(
                controls=[
                    ft.Text("KHOA CÔNG NGHỆ THÔNG TIN\nTRƯỜNG ĐẠI HỌC NAM CẦN THƠ", 
                            color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16),
                    ft.Text("-------------------------", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    ft.Text("ĐỒ ÁN CƠ SỞ 2", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, size=14),
                    
                    ft.Container(height=50), 
                    
                    ft.Text("PHẦN MỀM ĐIỂM DANH", size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text("(Bằng công nghệ nhận dạng khuôn mặt)", size=12, color=ft.Colors.WHITE_70, italic=True),
                    
                    ft.Container(height=40),
                    self.tf_username,
                    ft.Container(height=10),
                    self.tf_password,
                    ft.Container(height=20),
                    self.btn_login,
                    
                    ft.Container(expand=True), 
                    
                    ft.Text("Sinh viên: NGUYỄN CHÁNH HIỆP\nMã số sinh viên: 223408\nLớp: 22TIN-TT\n\nTháng 6/2025", 
                            color=ft.Colors.WHITE_70, size=13, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        self.right_panel = ft.Container(
            expand=True,
            bgcolor=ft.Colors.GREY_200,
            content=ft.Column(
                [ft.Icon(ft.Icons.IMAGE_OUTLINED, size=100, color=ft.Colors.GREY_400), ft.Text("Khu vực chèn ảnh nền Cổng DNC", color=ft.Colors.GREY_500)],
                alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        self.desktop_layout = ft.Row([self.left_panel, self.right_panel], expand=True, spacing=0)
        self.mobile_layout = ft.Column([self.left_panel], expand=True, spacing=0)

        safe_width = self.app_page.width or 1000
        self.content = self.mobile_layout if safe_width < 768 else self.desktop_layout
        self.app_page.on_resized = self.handle_resize

    async def handle_resize(self, e):
        safe_width = self.app_page.width or 1000
        if safe_width < 768:
            self.left_panel.width = None
            self.left_panel.expand = True
            self.content.content = self.mobile_layout
        else:
            self.left_panel.width = 400
            self.left_panel.expand = False
            self.content.content = self.desktop_layout
        self.update()

    async def handle_login(self, e):
        email = self.tf_username.value 
        password = self.tf_password.value
        
        def show_snackbar(message: str, bg_color: str):
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=bg_color)
            self.app_page.overlay.append(snack)
            snack.open = True
            self.app_page.update()

        if not email or not password:
            show_snackbar("Vui lòng nhập Email và Mật khẩu!", ft.Colors.RED_700)
            return

        try:
            # 1. Bật hiệu ứng loading
            self.btn_login.content = ft.ProgressRing(width=20, height=20, color=ft.Colors.WHITE, stroke_width=2)
            self.btn_login.disabled = True
            self.update()

            # 2. Xử lý Backend bằng HTTPX (Gửi yêu cầu tới Supabase Auth)
            # API Auth: POST /auth/v1/token?grant_type=password
            async with httpx.AsyncClient() as auth_client:
                auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
                auth_headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json"
                }
                auth_body = {
                    "email": email,
                    "password": password
                }
                
                auth_resp = await auth_client.post(auth_url, headers=auth_headers, json=auth_body)
                
                # Kiểm tra nếu đăng nhập thất bại (Sai pass, sai mail)
                if auth_resp.status_code != 200:
                    error_data = auth_resp.json()
                    error_msg = error_data.get("error_description", "Email hoặc mật khẩu không đúng!")
                    show_snackbar(error_msg, ft.Colors.RED_700)
                    self.reset_login_button()
                    return

                auth_data = auth_resp.json()
                user_id = auth_data["user"]["id"]

            # 3. Lấy thông tin Giảng viên bằng get_supabase_client (REST API)
            async with await get_supabase_client() as db_client:
                # Query: /giangvien?auth_id=eq.{user_id}&select=*
                params_gv = {
                    "select": "*",
                    "auth_id": f"eq.{user_id}"
                }
                res_gv = await db_client.get("/giangvien", params=params_gv)
                res_gv.raise_for_status()
                gv_data = res_gv.json()
                
                if gv_data:
                    # ĐĂNG NHẬP THÀNH CÔNG
                    giangvien = gv_data[0]
                    ho_ten = f"{giangvien.get('hodem', '')} {giangvien.get('ten', '')}".strip()
                    
                    self.app_page.session.store.set("user_session", {
                        "role": giangvien.get("vai_tro", "giangvien"), 
                        "name": ho_ten, 
                        "id": giangvien.get("id"),
                        "auth_id": user_id
                    })
                    
                    await self.app_page.push_route("/user/home")
                else:
                    show_snackbar("Tài khoản chưa được liên kết với Giảng viên nào!", ft.Colors.ORANGE_700)
                    self.reset_login_button()
                    
        except Exception as ex:
            print(f"Lỗi Đăng nhập (HTTPX): {ex}")
            show_snackbar(f"Lỗi kết nối Server: {str(ex)}", ft.Colors.RED_700)
            self.reset_login_button()

    def reset_login_button(self):
        """Khôi phục trạng thái nút bấm khi có lỗi."""
        self.btn_login.content = ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
        self.btn_login.disabled = False
        if getattr(self, "page", None):
            self.update()