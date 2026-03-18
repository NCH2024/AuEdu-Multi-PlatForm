import flet as ft
import json
from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from components.options.confirm_dialog import show_confirm_dialog # Nhớ import hộp thoại xác nhận

class BaseDashboard(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.active_route = ""
        
        self.image = ft.DecorationImage(src="images/background.jpg", fit=ft.BoxFit.COVER, opacity=0.6)
        
        self.menu_items = [
            {"label": "Tổng quan", "icon": ft.Icons.DASHBOARD_ROUNDED, "route": "/user/home"},
            {"label": "Điểm danh", "icon": ft.Icons.CAMERA_ALT_ROUNDED, "route": "/user/attendance"},
            {"label": "Lịch điểm danh", "icon": ft.Icons.CALENDAR_MONTH_ROUNDED, "route": "/user/schedule"},
            {"label": "Thống kê", "icon": ft.Icons.PIE_CHART_ROUNDED, "route": "/user/stats"},
        ]

        self.user_name_text = ft.Text("Đang tải...", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.page_title_text = ft.Text("TỔNG QUAN", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        self.content_area = ft.Container(expand=True, padding=15, alignment=ft.Alignment.TOP_CENTER)
        
        self.sidebar_controls = []
        self.bottom_nav_controls = []

        self.content = self.build_layout()
        self.app_page.on_resized = self.handle_resize
        
    def did_mount(self):
        self.app_page.run_task(self.load_user_info)

    def set_content(self, title: str, new_content: ft.Control, route: str):
        self.page_title_text.value = title.upper()
        self.content_area.content = new_content
        self.active_route = route
        
        self.build_navigation()
        self.sidebar.content.controls = self.sidebar.content.controls[:1] + self.sidebar_controls
        self.bottom_nav.content.content.controls = self.bottom_nav_controls
        
        if getattr(self, "page", None):
            self.update()

    # ==========================================
    # CÁC HÀM XỬ LÝ ĐĂNG XUẤT CÓ XÁC NHẬN
    # ==========================================
    async def _do_normal_logout(self):
        prefs = ft.SharedPreferences()
        await prefs.remove("user_session")
        await self.app_page.push_route("/login")

    async def _do_remove_account_logout(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            try:
                session = json.loads(session_str)
                email_to_remove = session.get("email")
                
                accounts_str = await prefs.get("saved_accounts")
                if accounts_str:
                    saved_accounts = json.loads(accounts_str)
                    # Lọc bỏ tài khoản hiện tại ra khỏi danh sách đã lưu
                    saved_accounts = [acc for acc in saved_accounts if acc.get("email") != email_to_remove]
                    await prefs.set("saved_accounts", json.dumps(saved_accounts))
            except: pass
            
        await prefs.remove("user_session")
        await self.app_page.push_route("/login")

    def build_layout(self):
        async def go_to_profile(e): await self.app_page.push_route("/user/profile")
        async def go_to_settings(e): await self.app_page.push_route("/user/settings")
        async def handle_about(e): await self.app_page.push_route("/user/about")
        
        # Bắt sự kiện bấm đăng xuất
        def handle_normal_logout(e):
            show_confirm_dialog(self.app_page, "Xác nhận đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?", lambda: self.app_page.run_task(self._do_normal_logout))

        def handle_remove_logout(e):
            show_confirm_dialog(self.app_page, "Gỡ tài khoản", "Bạn có muốn đăng xuất và XÓA vĩnh viễn tài khoản này khỏi thiết bị?", lambda: self.app_page.run_task(self._do_remove_account_logout))

        header = ft.Container(
            top=15, left=15, right=15, bgcolor=SECONDARY_COLOR, padding=ft.Padding(8, 8, 5, 8),
            border_radius=15, shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK_26, offset=ft.Offset(0, 4)),
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    # BIẾN CỤM AVATAR THÀNH NÚT BẤM (Thêm ink=True và on_click)
                    ft.Container(
                        padding=ft.Padding(4, 4, 12, 4), bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                        border_radius=20, expand=False, ink=True, on_click=go_to_profile,
                        content=ft.Row(spacing=8, controls=[
                            ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=SECONDARY_COLOR, size=14), bgcolor=ft.Colors.WHITE, radius=14),
                            self.user_name_text
                        ])
                    ),
                    ft.Row(spacing=0, controls=[
                        ft.Container(
                            padding=ft.Padding(10, 4, 10, 4), bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                            border_radius=12, margin=ft.Margin(10, 0, 0, 0),
                            content=self.page_title_text
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT, icon_color=ft.Colors.WHITE, icon_size=20,
                            items=[
                                ft.PopupMenuItem(content=ft.Text("Hồ sơ tài khoản"), icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED, on_click=go_to_profile),
                                ft.PopupMenuItem(content=ft.Text("Cài đặt"), icon=ft.Icons.SETTINGS_OUTLINED, on_click=go_to_settings),
                                ft.PopupMenuItem(content=ft.Text("Thông tin phần mềm"), icon=ft.Icons.INFO, on_click=handle_about),
                                ft.PopupMenuItem(content=ft.Text("Đăng xuất"), icon=ft.Icons.LOGOUT, on_click=handle_normal_logout),
                                ft.PopupMenuItem(content=ft.Text("Đăng xuất & Gỡ tài khoản", color=ft.Colors.RED_500), icon=ft.Icons.PERSON_OFF_OUTLINED, on_click=handle_remove_logout),
                            ]
                        )
                    ])
                ]
            )
        )

        scroll_wrapper = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START,
            controls=[
                ft.Container(height=80), 
                self.content_area,
                ft.Container(height=100)
            ]
        )
        main_view_stack = ft.Stack(expand=True, controls=[scroll_wrapper, header])

        self.build_navigation()

        self.sidebar = get_glass_container(
            width=250, border_radius=0, 
            content=ft.Column(
                spacing=5, alignment=ft.MainAxisAlignment.START,
                controls=[
                    ft.Container(
                        padding=ft.Padding(0, 10, 0, 20), alignment=ft.Alignment.CENTER,
                        content=ft.Column([
                            ft.Image(src="icon.png", width=120, height=120, fit=ft.BoxFit.CONTAIN),
                            ft.Button(content=ft.Text("Đăng xuất", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=SECONDARY_COLOR, on_click=handle_normal_logout)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                ] + self.sidebar_controls
            )
        )

        self.bottom_nav = ft.Container(
            bottom=20, left=20, right=20, 
            content=get_glass_container(
                padding=10, border_radius=30, 
                content=ft.Row(controls=self.bottom_nav_controls, alignment=ft.MainAxisAlignment.SPACE_AROUND)
            )
        )

        self.desktop_layout = ft.Row(
            controls=[self.sidebar, ft.Container(content=main_view_stack, expand=True, padding=0)], 
            expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START 
        )
        
        self.mobile_layout = ft.Stack(
            controls=[ft.Container(content=main_view_stack, expand=True, padding=0), self.bottom_nav], 
            expand=True
        )

        return ft.SafeArea(content=self.mobile_layout if (self.app_page.width and self.app_page.width < 768) else self.desktop_layout)

    def build_navigation(self):
        self.sidebar_controls.clear()
        self.bottom_nav_controls.clear()

        for item in self.menu_items:
            is_active = self.active_route == item["route"]
            def create_nav_click(route):
                async def on_click(e):
                    if self.active_route != route:
                        await self.app_page.push_route(route)
                return on_click

            self.sidebar_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(item["icon"], color=SECONDARY_COLOR if is_active else ft.Colors.BLACK_87),
                        ft.Text(item["label"], color=SECONDARY_COLOR if is_active else ft.Colors.BLACK_87, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL)
                    ]),
                    padding=15, border_radius=10, bgcolor=PRIMARY_COLOR if is_active else ft.Colors.TRANSPARENT,
                    ink=True, on_click=create_nav_click(item["route"])
                )
            )
            
            self.bottom_nav_controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(item["icon"], color=SECONDARY_COLOR if is_active else ft.Colors.BLACK_87),
                        ft.Text(item["label"], size=11, color=SECONDARY_COLOR if is_active else ft.Colors.BLACK_87, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    padding=5, border_radius=10, bgcolor=PRIMARY_COLOR if is_active else ft.Colors.TRANSPARENT,
                    ink=True, on_click=create_nav_click(item["route"])
                )
            )

    async def load_user_info(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            try:
                session = json.loads(session_str)
                self.user_name_text.value = session.get("name", "Người dùng")
                if getattr(self, "page", None):
                    self.user_name_text.update()
            except: pass

    async def handle_resize(self, e):
        if self.app_page.width and self.app_page.width < 768:
            self.content.content = self.mobile_layout
        else:
            self.content.content = self.desktop_layout
        if getattr(self, "page", None):
            self.update()