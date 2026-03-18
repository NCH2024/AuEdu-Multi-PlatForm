import flet as ft
import httpx
import json
from components.options.carousel_banner import CarouselBanner
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.config import get_supabase_client, SUPABASE_URL, SUPABASE_KEY
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, TEXT_MAIN

class LoginPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0
        
        self.saved_accounts = []
        self.selected_account = None
        
        def is_mobile(page: ft.Page):
            return page.platform in ["android", "ios"] or (page.width and page.width < 768)
        
        if is_mobile(self.app_page):
            self.min_width_carousel = 320
        else:
            self.min_width_carousel = 420

        # ==========================================
        # 1. CÁC THÀNH PHẦN INPUT 
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
            }
        ]

        self.auto_slider_banner = CarouselBanner(
            page=self.app_page, items=banner_data, 
            width=self.min_width_carousel, height=80, interval=4
        )
        
        self.content = ft.Container(expand=True)
        self.app_page.run_task(self.load_cached_accounts)

    # ==========================================
    # QUẢN LÝ GIAO DIỆN
    # ==========================================
    async def load_cached_accounts(self):
        prefs = ft.SharedPreferences()
        accounts_str = await prefs.get("saved_accounts")
        if accounts_str:
            self.saved_accounts = json.loads(accounts_str)
        self.build_ui()

    def build_ui(self):
        if self.saved_accounts and not self.selected_account:
            login_form_content = self.build_multi_account_view()
        else:
            login_form_content = self.build_standard_login_form()

        login_form = ft.Column(
            horizontal_alignment="center", alignment="center", spacing=5,
            controls=[
                ft.Container(
                    width=420, 
                    # ĐÃ XÓA height=500 Ở ĐÂY ĐỂ KHUNG TỰ ĐỘNG CO GIÃN THEO NỘI DUNG
                    padding=ft.Padding(40, 50, 40, 50),
                    alignment=ft.Alignment(0,0),
                    bgcolor=ft.Colors.with_opacity(0.80, ft.Colors.WHITE), blur=5,
                    border_radius=24, border=ft.Border.all(2, ft.Colors.WHITE),                   
                    shadow=ft.BoxShadow(spread_radius=2, blur_radius=20, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK), offset=ft.Offset(0, 10)),
                    content=login_form_content
                ),
                self.auto_slider_banner
            ]
        )

        background_image = ft.Image(
            src="images/background-desktop.png", height=700, width=1060, fit=ft.BoxFit.COVER,
            filter_quality=ft.FilterQuality.HIGH, expand=True
        )
        
        ui_content = ft.Stack(
            controls=[
                background_image,
                ft.Container(content=login_form, alignment=ft.Alignment(0, 0), expand=True, padding=20)
            ],
            expand=True
        )
        self.content.content = ft.WindowDragArea(content=ui_content, expand=True)
        self.update()

    def build_multi_account_view(self):
        account_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=200)
        
        for acc in self.saved_accounts:
            acc_card = ft.Container(
                bgcolor=ft.Colors.WHITE, border_radius=12, border=ft.Border.all(1, ft.Colors.BLACK_12),
                content=ft.ListTile(
                    leading=ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE), bgcolor=SECONDARY_COLOR),
                    title=ft.Text(acc["name"], weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=14),
                    subtitle=ft.Text(acc["email"], size=12, color=ft.Colors.GREY_600),
                    trailing=ft.IconButton(ft.Icons.CANCEL_OUTLINED, icon_color=ft.Colors.RED_400, data=acc["email"], tooltip="Gỡ tài khoản", on_click=self.request_remove_account),
                    on_click=lambda e, a=acc: self.select_account_to_login(a)
                )
            )
            account_list.controls.append(acc_card)

        btn_other_account = ft.TextButton(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=ACCENT_COLOR, size=20), 
                    ft.Text("Đăng nhập bằng tài khoản khác", color=ACCENT_COLOR, weight=ft.FontWeight.BOLD)
                ]
            ),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                overlay_color=ft.Colors.with_opacity(0.1, ACCENT_COLOR)
            ),
            on_click=self.show_standard_form
        )

        return ft.Column(
            horizontal_alignment="center", spacing=10,
            controls=[
                ft.Image(src="splash.png", width=100, height=100, fit="contain"),
                ft.Text("Chọn tài khoản của bạn", size=16, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                ft.Container(height=5),
                account_list,
                ft.Divider(color=ft.Colors.BLACK_12),
                btn_other_account
            ]
        )

    def build_standard_login_form(self):
        btn_back = ft.Container()
        if self.saved_accounts:
            btn_back = ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=ft.Colors.GREY_600,
                tooltip="Quay lại danh sách tài khoản", on_click=self.back_to_multi_account
            )

        return ft.Column(
            horizontal_alignment="center", spacing=5,
            controls=[
                ft.Row([btn_back, ft.Container(expand=True)], alignment=ft.MainAxisAlignment.START),
                ft.Container(content=ft.Image(src="splash.png", width=100, height=100, fit="contain"), margin=ft.Margin(0, -30, 0, 0)),
                ft.Column(horizontal_alignment="center", spacing=0, controls=[ft.Text("Hệ thống điểm danh khuôn mặt AI", size=14, color=ft.Colors.GREY_600, italic=True)]),
                ft.Container(height=10),
                self.tf_username, self.tf_password, ft.Container(height=15),
                self.btn_login, ft.Container(height=5),
                ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", size=12, color=ft.Colors.GREY_500, weight=ft.FontWeight.W_500, text_align="center")
            ]
        )

    # ==========================================
    # LOGIC ĐIỀU HƯỚNG VÀ XÓA TÀI KHOẢN
    # ==========================================
    def select_account_to_login(self, account):
        self.selected_account = account
        self.tf_username.value = account["email"]
        self.tf_username.disabled = True
        self.tf_password.value = ""
        self.build_ui()
        
    def show_standard_form(self, e):
        self.selected_account = "NEW"
        self.tf_username.value = ""
        self.tf_username.disabled = False
        self.tf_password.value = ""
        self.build_ui()

    def back_to_multi_account(self, e):
        self.selected_account = None
        self.build_ui()

    def request_remove_account(self, e):
        """Mở hộp thoại xác nhận trước khi xóa"""
        email_to_remove = e.control.data
        show_confirm_dialog(
            page=self.app_page,
            title="Gỡ tài khoản",
            message=f"Bạn có chắc chắn muốn gỡ tài khoản {email_to_remove} khỏi thiết bị này không?",
            on_confirm_callback=lambda: self.app_page.run_task(self.execute_remove_account, email_to_remove)
        )

    async def execute_remove_account(self, email_to_remove):
        """Thực thi xóa tài khoản và hiện thông báo nổi"""
        self.saved_accounts = [acc for acc in self.saved_accounts if acc["email"] != email_to_remove]
        prefs = ft.SharedPreferences()
        await prefs.set("saved_accounts", json.dumps(self.saved_accounts))
        
        if not self.saved_accounts:
            self.selected_account = "NEW"
            self.tf_username.value = ""
            self.tf_username.disabled = False
            
        self.build_ui()
        show_top_notification(self.app_page, "Đã gỡ tài khoản", f"Tài khoản {email_to_remove} đã được gỡ khỏi thiết bị.", color=ft.Colors.GREEN_500)

    # ==========================================
    # LOGIC BACKEND
    # ==========================================
    async def handle_login(self, e):
        email = self.tf_username.value 
        password = self.tf_password.value

        if not email or not password:
            show_top_notification(self.app_page, "Cảnh báo", "Vui lòng nhập Email và Mật khẩu!", color=ft.Colors.ORANGE_600)
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
                    show_top_notification(self.app_page, "Đăng nhập thất bại", error_msg, color=ft.Colors.RED_600)
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
                    
                    session_dict = {
                        "email": email,
                        "role": giangvien.get("vai_tro", "giangvien"), 
                        "name": ho_ten, 
                        "id": giangvien.get("id"),
                        "auth_id": user_id
                    }
                    
                    prefs = ft.SharedPreferences()
                    await prefs.set("user_session", json.dumps(session_dict))
                    
                    existing_emails = [acc["email"] for acc in self.saved_accounts]
                    if email not in existing_emails:
                        self.saved_accounts.append(session_dict)
                        await prefs.set("saved_accounts", json.dumps(self.saved_accounts))
                    print(f"Tài khoản {ho_ten} đã đăng nhập thành công!")
                    show_top_notification(self.app_page, "Thành công", f"Chào mừng {ho_ten} trở lại!", duration_ms=4000, color=ft.Colors.GREEN_600)
                    await self.app_page.push_route("/user/home")
                else:
                    show_top_notification(self.app_page, "Lỗi phân quyền", "Tài khoản chưa được liên kết với Giảng viên nào!", color=ft.Colors.ORANGE_700)
                    self.reset_login_button()
                    
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi hệ thống", f"Lỗi kết nối Server: {str(ex)}", color=ft.Colors.RED_700)
            self.reset_login_button()

    def reset_login_button(self):
        self.btn_login.content = ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=15)
        self.btn_login.disabled = False
        if getattr(self, "page", None):
            self.update()