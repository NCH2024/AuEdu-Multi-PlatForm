import flet as ft
import httpx
import json
from components.options.carousel_banner import CarouselBanner
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.config import get_supabase_client, SUPABASE_URL, SUPABASE_KEY

# Nhập hệ thống Theme phẳng mới của chúng ta
from core.theme import current_theme

class LoginPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        
        # 1. KHÔNG GIAN PHẲNG TUYỆT ĐỐI: Đặt ảnh nền thẳng vào lớp gốc
        self.expand = True
        self.padding = 0
        
        is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS] or (page.width and page.width < 768)
        self.min_width_carousel = 320 if is_mobile else 420
        
        # ẢNH NỀN HIỂN THỊ TRỰC TIẾP 100%
        self.image = ft.DecorationImage(
            src="images/background-mobile.png" if is_mobile else "images/background-desktop.png",
            fit=ft.BoxFit.COVER,
        )
        
        self.saved_accounts = []
        self.selected_account = None
        
        # 2. CÁC THÀNH PHẦN INPUT 
        # (Nền TextField được làm mờ nhẹ một chút xíu để chữ không bị lẫn vào chi tiết ảnh)
        input_bg = ft.Colors.with_opacity(0.85, current_theme.surface_color)
        
        self.tf_username = ft.TextField(
            label="Tên đăng nhập / Email", 
            prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
            border_radius=12, 
            color=current_theme.text_main,
            bgcolor=input_bg, 
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=current_theme.primary,
            filled=True,
            height=55,
            text_size=14,
            cursor_color=current_theme.primary
        )
        
        self.tf_password = ft.TextField(
            label="Mật khẩu", 
            prefix_icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
            password=True, 
            can_reveal_password=True, 
            border_radius=12, 
            color=current_theme.text_main,
            bgcolor=input_bg,
            border_color=ft.Colors.TRANSPARENT,
            focused_border_color=current_theme.primary,
            filled=True,
            height=55,
            text_size=14,
            cursor_color=current_theme.primary
        )
        
        self.btn_login = ft.Button(
            content=ft.Text("Đăng nhập", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=15),
            bgcolor=current_theme.primary, 
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(0, 18, 0, 18),
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
        
        self.app_page.run_task(self.load_cached_accounts)

    async def load_cached_accounts(self):
        prefs = ft.SharedPreferences()
        accounts_str = await prefs.get("saved_accounts")
        if accounts_str:
            self.saved_accounts = json.loads(accounts_str)
        self.build_ui()

    def build_ui(self):
        is_mobile = self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS] or (self.app_page.width and self.app_page.width < 768)

        if self.saved_accounts and not self.selected_account:
            login_form_content = self.build_multi_account_view()
        else:
            login_form_content = self.build_standard_login_form()

        # Dàn dọc trực tiếp các thành phần, ĐẶT THẲNG LÊN NỀN ẢNH (Không dùng lớp phủ)
        main_column = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=25,
            controls=[
                ft.Container(
                    content=login_form_content,
                    width=self.min_width_carousel + 40 if is_mobile else 420,
                    alignment=ft.Alignment(0,0)
                ),
                self.auto_slider_banner
            ]
        )

        # Container trong suốt dùng để căn giữa nội dung và tạo khoảng cách với lề
        content_wrapper = ft.Container(
            expand=True,
            alignment=ft.Alignment(0, 0),
            padding=ft.Padding(20, 20, 20, 20),
            content=main_column
        )

        # Nút X đóng ứng dụng riêng cho Windows
        btn_close_windows = ft.Container(visible=False)
        if self.app_page.platform == ft.PagePlatform.WINDOWS:
            btn_style_close = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=0),
                overlay_color=ft.Colors.RED_600,
                color={ft.ControlState.HOVERED: ft.Colors.WHITE, ft.ControlState.DEFAULT: current_theme.text_main},
                padding=10
            )
            async def handle_login_close(e):
                await self.app_page.window.close()
            
            btn_close_windows = ft.Container(
                top=0, right=0,
                content=ft.IconButton(ft.Icons.CLOSE, icon_size=16, style=btn_style_close, width=45, height=35, on_click=handle_login_close)
            )

        # GẮN VÀO ROOT
        if self.app_page.platform == ft.PagePlatform.WINDOWS:
            self.content = ft.WindowDragArea(
                content=ft.Stack(
                    controls=[content_wrapper, btn_close_windows],
                    expand=True,
                ), 
                expand=True
            )
        else:
            self.content = content_wrapper
            
        self.update()

    def build_multi_account_view(self):
        account_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=200)
        
        for acc in self.saved_accounts:
            acc_card = ft.Container(
                bgcolor=ft.Colors.with_opacity(0.85, current_theme.surface_color), border_radius=12, border=ft.Border.all(1, ft.Colors.TRANSPARENT),
                content=ft.ListTile(
                    leading=ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE), bgcolor=current_theme.primary),
                    title=ft.Text(acc["name"], weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14),
                    subtitle=ft.Text(acc["email"], size=12, color=current_theme.text_muted),
                    trailing=ft.IconButton(ft.Icons.CANCEL_OUTLINED, icon_color=ft.Colors.RED_400, data=acc["email"], tooltip="Gỡ tài khoản", on_click=self.request_remove_account),
                    on_click=lambda e, a=acc: self.select_account_to_login(a)
                )
            )
            account_list.controls.append(acc_card)

        btn_other_account = ft.Button(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=current_theme.surface_color, size=20), 
                    ft.Text("Đăng nhập bằng tài khoản khác", color=current_theme.surface_color, weight=ft.FontWeight.BOLD)
                ],
            ),
            bgcolor=current_theme.text_main, # Dùng màu tương phản với nền để tạo sự chú ý
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding(0, 15, 0, 15),
                overlay_color=ft.Colors.with_opacity(0.1, current_theme.surface_color)
            ),
            on_click=self.show_standard_form
        )

        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
            controls=[
                ft.Image(src="splash.png", width=120, height=120, fit=ft.BoxFit.CONTAIN),
                ft.Text("Chọn tài khoản của bạn", size=18, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
                ft.Container(height=10),
                account_list,
                ft.Divider(color=current_theme.divider_color),
                btn_other_account
            ]
        )

    def build_standard_login_form(self):
        btn_back = ft.Container()
        if self.saved_accounts:
            btn_back = ft.IconButton(
                icon=ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=current_theme.text_main,
                tooltip="Quay lại danh sách tài khoản", on_click=self.back_to_multi_account
            )

        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
            controls=[
                ft.Row([btn_back, ft.Container(expand=True)], alignment=ft.MainAxisAlignment.START),
                ft.Image(src="splash.png", width=130, height=130, fit=ft.BoxFit.CONTAIN),
                ft.Text("Hệ thống điểm danh khuôn mặt AI", size=15, color=current_theme.text_main, weight=ft.FontWeight.W_600),
                ft.Container(height=15),
                self.tf_username, self.tf_password, ft.Container(height=10),
                self.btn_login, ft.Container(height=10),
                ft.Text("Trường Công nghệ số & Trí tuệ nhân tạo DNC", size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)
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
        email_to_remove = e.control.data
        show_confirm_dialog(
            page=self.app_page,
            title="Gỡ tài khoản",
            message=f"Bạn có chắc chắn muốn gỡ tài khoản {email_to_remove} khỏi thiết bị này không?",
            on_confirm_callback=lambda: self.app_page.run_task(self.execute_remove_account, email_to_remove)
        )

    async def execute_remove_account(self, email_to_remove):
        self.saved_accounts = [acc for acc in self.saved_accounts if acc["email"] != email_to_remove]
        prefs = ft.SharedPreferences()
        await prefs.set("saved_accounts", json.dumps(self.saved_accounts))
        
        if not self.saved_accounts:
            self.selected_account = "NEW"
            self.tf_username.value = ""
            self.tf_username.disabled = False
            
        self.build_ui()
        show_top_notification(self.app_page, "Đã gỡ tài khoản", f"Tài khoản {email_to_remove} đã được gỡ khỏi thiết bị.", color=ft.Colors.GREEN_500, sound="S")

    # ==========================================
    # LOGIC BACKEND
    # ==========================================
    async def handle_login(self, e):
        email = self.tf_username.value 
        password = self.tf_password.value

        if not email or not password:
            show_top_notification(self.app_page, "Cảnh báo", "Vui lòng nhập Email và Mật khẩu!", color=ft.Colors.ORANGE_600, sound="E")
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
                    show_top_notification(self.app_page, "Đăng nhập thất bại", error_msg, color=ft.Colors.RED_600, sound="E")
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
                    show_top_notification(self.app_page, "Thành công", f"Chào mừng {ho_ten} trở lại!", duration_ms=4000, color=ft.Colors.GREEN_600, sound="S")
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