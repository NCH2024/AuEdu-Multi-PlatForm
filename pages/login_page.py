import flet as ft
import httpx
import json
from components.options.carousel_banner import CarouselBanner
from core.config import get_supabase_client, SUPABASE_URL, SUPABASE_KEY
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, TEXT_MAIN

class LoginPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0
        
        # Kiểm tra kích thước cho banner thông báo trên thiết bị
        def is_mobile(page: ft.Page):
            return page.platform in ["android", "ios"] or (page.width and page.width < 768)
        if is_mobile(self.app_page):
            self.min_width_carousel = 320
        else:
            self.min_width_carousel = 420
            

        # ==========================================
        # 1. CÁC THÀNH PHẦN INPUT ĐƯỢC LÀM MỚI TỐI ƯU
        # ==========================================
        self.tf_username = ft.TextField(
            label="Tên đăng nhập / Email", 
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            border_radius=12, 
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.WHITE),
            color=SECONDARY_COLOR,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ACCENT_COLOR,
            filled=True,
            height=55,
            text_size=14,
            cursor_color=SECONDARY_COLOR
        )
        
        self.tf_password = ft.TextField(
            label="Mật khẩu", 
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            password=True, 
            can_reveal_password=True, 
            border_radius=12, 
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.WHITE),
            color=SECONDARY_COLOR,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=ACCENT_COLOR,
            filled=True,
            height=55,
            text_size=14,
            cursor_color=SECONDARY_COLOR
        )
        
        self.btn_login = ft.Button(
            content=ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=15),
            bgcolor=SECONDARY_COLOR, 
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(0, 18, 0, 18),
                elevation=5,
                shadow_color=SECONDARY_COLOR
            ),
            width=320, 
            on_click=self.handle_login
        )

        # ==========================================
        # DỮ LIỆU BANNER (Em có thể thay đổi tùy ý)
        # ==========================================
        banner_data = [
            {
                "image": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=200&auto=format&fit=crop",
                "title": "Thông báo học vụ",
                "subtitle": "Kế hoạch nghỉ lễ và điều chỉnh lịch học học kỳ mới.",
                "url": "https://nctu.edu.vn"
            },
            {
                "image": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?q=80&w=200&auto=format&fit=crop",
                "title": "Cập nhật phần mềm",
                "subtitle": "Phiên bản mới giúp tăng tốc độ nhận dạng sinh viên lên 40%.",
                "url": "https://github.com/NCH2024/AuEdu-Multi-PlatForm.git"
            },
            {
                "image": "https://images.unsplash.com/photo-1555626906-fcf10d6851b4?q=80&w=200&auto=format&fit=crop",
                "title": "Hoạt động ngoại khóa",
                "subtitle": "Đăng ký tham gia giải chạy bộ thiện nguyện mùa hè.",
                "url": "https://nctu.edu.vn"
            }
        ]

        # Khởi tạo Component tự động trượt
        self.auto_slider_banner = CarouselBanner(
            page=self.app_page, 
            items=banner_data, 
            width=self.min_width_carousel, 
            height=80, 
            interval=4 # 4 giây chuyển ảnh một lần
        )
        
        
        # ==========================================
        # 2. KHUNG ĐĂNG NHẬP TRUNG TÂM (GLASS CARD)
        # ==========================================
        login_form = ft.Column(
            horizontal_alignment="center",
            alignment="center",
            spacing=5, # Khoảng cách giữa Form và Banner
            controls=[
                ft.Container(
                    width=420,
                    height=500,
                    padding=ft.Padding(40, 50, 40, 50),
                    alignment=ft.Alignment(0,0),
                    bgcolor=ft.Colors.with_opacity(0.80, ft.Colors.WHITE),
                    blur=5,
                    border_radius=24, 
                    border=ft.Border.all(2, ft.Colors.WHITE),                   
                    shadow=ft.BoxShadow(
                        spread_radius=2, 
                        blur_radius=20, 
                        color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK), 
                        offset=ft.Offset(0, 10)
                    ),
                    content=ft.Column(
                        horizontal_alignment="center",
                        spacing=5,
                        controls=[
                            ft.Container(
                                content=ft.Image(src="splash.png", width=100, height=100, fit="contain"),
                            ),
                            ft.Column(
                                horizontal_alignment="center",
                                spacing=0,
                                controls=[
                                    ft.Text("Hệ thống điểm danh khuôn mặt AI", size=14, color=ft.Colors.GREY_600, italic=True),
                                ]
                            ),
                            ft.Container(height=10),
                            self.tf_username,
                            self.tf_password,
                            ft.Container(height=15),
                            self.btn_login,
                            
                            ft.Container(height=5),
                            ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", 
                                    size=12, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500, text_align="center")
                        ]
                    )
                ),
                self.auto_slider_banner
            ]
        )

        # ==========================================
        # 3. BACKGROUND VÀ BỐ CỤC CHUNG
        # ==========================================
        background_image = ft.Image(
            src="images/background-desktop.png", 
            height=700,
            width=1060,
            fit=ft.BoxFit.COVER,
            filter_quality=ft.FilterQuality.HIGH,
            expand=True,
            # opacity=0.6 
        )
        
        # Xếp chồng: Ảnh nền -> Lớp phủ -> Khung đăng nhập căn giữa
        ui_content = ft.Stack(
            controls=[
                background_image,
                ft.Container(
                    content=login_form,
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                    padding=20
                )
            ],
            expand=True
        )
        self.content = ft.WindowDragArea(
            content=ui_content, 
            expand=True
        )
        

    # ==========================================
    # LOGIC BACKEND (GIỮ NGUYÊN 100%)
    # ==========================================
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
            self.btn_login.content = ft.ProgressRing(width=20, height=20, color=ft.Colors.WHITE, stroke_width=2)
            self.btn_login.disabled = True
            self.update()

            async with httpx.AsyncClient() as auth_client:
                auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
                auth_headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
                auth_body = {"email": email, "password": password}
                
                auth_resp = await auth_client.post(auth_url, headers=auth_headers, json=auth_body)
                
                if auth_resp.status_code != 200:
                    error_data = auth_resp.json()
                    error_msg = error_data.get("error_description", "Email hoặc mật khẩu không đúng!")
                    show_snackbar(error_msg, ft.Colors.RED_700)
                    self.reset_login_button()
                    return

                auth_data = auth_resp.json()
                user_id = auth_data["user"]["id"]

            async with await get_supabase_client() as db_client:
                params_gv = {"select": "*", "auth_id": f"eq.{user_id}"}
                res_gv = await db_client.get("/giangvien", params=params_gv)
                res_gv.raise_for_status()
                gv_data = res_gv.json()
                
                if gv_data:
                    giangvien = gv_data[0]
                    ho_ten = f"{giangvien.get('hodem', '')} {giangvien.get('ten', '')}".strip()
                    
                    # Dùng SharedPreferences kết hợp json theo chuẩn mới nhất
                    session_dict = {
                        "role": giangvien.get("vai_tro", "giangvien"), 
                        "name": ho_ten, 
                        "id": giangvien.get("id"),
                        "auth_id": user_id
                    }
                    prefs = ft.SharedPreferences()
                    await prefs.set("user_session", json.dumps(session_dict))
                    
                    await self.app_page.push_route("/user/home")
                else:
                    show_snackbar("Tài khoản chưa được liên kết với Giảng viên nào!", ft.Colors.ORANGE_700)
                    self.reset_login_button()
                    
        except Exception as ex:
            print(f"Lỗi Đăng nhập: {ex}")
            show_snackbar(f"Lỗi kết nối Server: {str(ex)}", ft.Colors.RED_700)
            self.reset_login_button()

    def reset_login_button(self):
        self.btn_login.content = ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=15)
        self.btn_login.disabled = False
        if getattr(self, "page", None):
            self.update()