import flet as ft
import json
from core.theme import get_glass_container, adaptive_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from components.options.confirm_dialog import show_confirm_dialog 

class BaseDashboard(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.active_route = ""
        
        # Biến trạng thái để kiểm soát độ rộng của Sidebar (Mặc định thu gọn)
        self.is_sidebar_expanded = False
        
        # Ảnh nền tổng thể
        self.image = ft.DecorationImage(
            src="images/background.jpg", 
            fit=ft.BoxFit.COVER, 
            opacity=0.8, 
            filter_quality=ft.FilterQuality.HIGH)
        
        self.menu_items = [
            {"label": "Tổng quan", "icon": ft.Icons.DASHBOARD_ROUNDED, "route": "/user/home"},
            {"label": "Điểm danh", "icon": ft.Icons.CAMERA_ALT_ROUNDED, "route": "/user/attendance"},
            {"label": "Lịch học", "icon": ft.Icons.CALENDAR_MONTH_ROUNDED, "route": "/user/schedule"},
            {"label": "Thống kê", "icon": ft.Icons.PIE_CHART_ROUNDED, "route": "/user/stats"},
        ]

        self.user_name_text = ft.Text("Đang tải...", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.page_title_text = ft.Text("TỔNG QUAN", size=12, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)
        
        self.content_area = ft.Container(expand=True, padding=ft.Padding(15, 5, 15, 15), alignment=ft.Alignment.TOP_CENTER)
        
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
    # LOGIC ĐÓNG/MỞ SIDEBAR THU GỌN
    # ==========================================
    def toggle_sidebar(self, e):
        self.is_sidebar_expanded = not self.is_sidebar_expanded
        # Đổi icon nút menu cho trực quan
        self.btn_menu_toggle.icon = ft.Icons.MENU_OPEN_ROUNDED if self.is_sidebar_expanded else ft.Icons.MENU_ROUNDED
        # Cập nhật độ rộng thanh menu (có kèm hiệu ứng animation mượt mà)
        self.sidebar.width = 200 if self.is_sidebar_expanded else 70
        
        # Vẽ lại ruột bên trong menu
        self.build_navigation()
        self.sidebar.content.controls = self.sidebar.content.controls[:1] + self.sidebar_controls
        self.update()

    # ==========================================
    # CÁC HÀM XỬ LÝ ĐĂNG XUẤT 
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
                    saved_accounts = [acc for acc in saved_accounts if acc.get("email") != email_to_remove]
                    await prefs.set("saved_accounts", json.dumps(saved_accounts))
            except: pass
        await prefs.remove("user_session")
        await self.app_page.push_route("/login")

    # ==========================================
    # CUSTOM TITLE BAR CHO WINDOWS
    # ==========================================
    def build_windows_title_bar(self):
        if self.app_page.platform != ft.PagePlatform.WINDOWS:
            return ft.Container(height=0, visible=False)
            
        # Nút thường (Thu nhỏ, Phóng to)
        btn_style_normal = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color=ft.Colors.with_opacity(0.1, SECONDARY_COLOR),
            padding=10
        )
        
        # Nút Đóng (Close) 
        btn_style_close = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color=ft.Colors.RED_600,
            color={ft.ControlState.HOVERED: ft.Colors.WHITE, ft.ControlState.DEFAULT: SECONDARY_COLOR},
            padding=10
        )

        # XỬ LÝ LỖI "NEVER AWAITED" TẠI ĐÂY
        async def handle_minimize(e):
            self.app_page.window.minimized = True
            self.app_page.update()

        async def handle_maximize(e):
            self.app_page.window.maximized = not self.app_page.window.maximized
            self.app_page.update()

        async def handle_close(e):
            await self.app_page.window.close() # Gọi await đàng hoàng cho Flet 0.82.2
            
        return ft.WindowDragArea(
            ft.Container(
                height=35,
                bgcolor=ft.Colors.WHITE, 
                padding=ft.Padding(15, 0, 0, 0), 
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, color=SECONDARY_COLOR, size=16),
                            ft.Text("AuEdu Multi-Platform", color=SECONDARY_COLOR, size=12, weight=ft.FontWeight.BOLD)
                        ]),
                        ft.Row(
                            spacing=0,
                            controls=[
                                ft.IconButton(ft.Icons.MINIMIZE, icon_size=16, icon_color=SECONDARY_COLOR, style=btn_style_normal, width=45, height=35, on_click=handle_minimize),
                                ft.IconButton(ft.Icons.CROP_SQUARE, icon_size=16, icon_color=SECONDARY_COLOR, style=btn_style_normal, width=45, height=35, on_click=handle_maximize),
                                ft.IconButton(ft.Icons.CLOSE, icon_size=16, style=btn_style_close, width=45, height=35, on_click=handle_close),
                            ]
                        )
                    ]
                )
            )
        )

    def build_layout(self):
        async def go_to_profile(e): await self.app_page.push_route("/user/profile")
        async def go_to_settings(e): await self.app_page.push_route("/user/settings")
        async def handle_about(e): await self.app_page.push_route("/user/about")
        
        def handle_normal_logout(e):
            show_confirm_dialog(self.app_page, "Xác nhận đăng xuất", "Bạn có chắc chắn muốn đăng xuất khỏi tài khoản này?", lambda: self.app_page.run_task(self._do_normal_logout))

        def handle_remove_logout(e):
            show_confirm_dialog(self.app_page, "Gỡ tài khoản", "Bạn có muốn đăng xuất và XÓA vĩnh viễn tài khoản này khỏi thiết bị?", lambda: self.app_page.run_task(self._do_remove_account_logout))

        # ---- KIỂM TRA MÀN HÌNH NHỎ HAY LỚN ----
        is_mobile = (self.app_page.width and self.app_page.width < 768) or self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        # 1. Nút Toggle Menu (Ẩn luôn nếu là Mobile)
        self.btn_menu_toggle = ft.IconButton(
            icon=ft.Icons.MENU_ROUNDED, 
            icon_color=SECONDARY_COLOR,
            on_click=self.toggle_sidebar,
            visible=not is_mobile # CHÌA KHÓA Ở ĐÂY
        )
        
        # 2. Ẩn luôn tên người dùng nếu là Mobile để nhường chỗ cho tiêu đề
        self.user_name_text.visible = not is_mobile

        header_content = ft.Container(
            padding=ft.Padding(5, 5, 15, 5), 
            bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
            border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.BLACK_12)),
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=5, controls=[
                        self.btn_menu_toggle,
                        self.page_title_text
                    ]),
                    ft.Row(spacing=5, controls=[
                        ft.Container(
                            padding=ft.Padding(4, 4, 12, 4) if not is_mobile else ft.Padding(4, 4, 4, 4), # Bo gọn lại nếu mất chữ
                            bgcolor=SECONDARY_COLOR,
                            border_radius=20, ink=True, on_click=go_to_profile,
                            content=ft.Row(spacing=8, controls=[
                                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=SECONDARY_COLOR, size=14), bgcolor=ft.Colors.WHITE, radius=14),
                                self.user_name_text
                            ])
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT, icon_color=SECONDARY_COLOR, icon_size=20,
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
        

        windows_title_bar = self.build_windows_title_bar()
        top_bar_area = ft.Column(spacing=0, controls=[windows_title_bar, header_content])

        scroll_wrapper = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START,
            controls=[
                ft.Container(height=10), 
                self.content_area,
                ft.Container(height=80) 
            ]
        )
        
        main_view_stack = ft.Column(expand=True, spacing=0, controls=[top_bar_area, scroll_wrapper])

        self.build_navigation()

        # SIDEBAR THÍCH ỨNG: Chuyển sang Dark Sidebar 
        self.sidebar = ft.Container(
            width=70, 
            border_radius=0, 
            padding=ft.Padding(5, 10, 5, 10),
            bgcolor=SECONDARY_COLOR, # Đổ nền màu đậm cho toàn bộ menu
            animate=ft.Animation(300, ft.AnimationCurve.DECELERATE), # Cú pháp animation chuẩn của em đây!
            content=ft.Column(
                spacing=5, alignment=ft.MainAxisAlignment.START,
                controls=[
                    ft.Container(
                        padding=ft.Padding(0, 15, 0, 15), alignment=ft.Alignment.CENTER,
                        content=ft.Image(src="icon.png", width=40, height=40, fit=ft.BoxFit.CONTAIN)
                    )
                ] + self.sidebar_controls
            )
        )
        # Thêm hiệu ứng trượt mượt mà cho thanh Sidebar
        self.sidebar.animate = ft.Animation(300, ft.AnimationCurve.DECELERATE)

        self.bottom_nav = ft.Container(
            bottom=0, left=0, right=0, 
            content=adaptive_container(
                page=self.app_page,
                padding=5, border_radius=0, 
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

            # Bố cục icon và chữ
            nav_content = ft.Row(
                alignment=ft.MainAxisAlignment.START if self.is_sidebar_expanded else ft.MainAxisAlignment.CENTER,
                controls=[
                    # ĐẢO MÀU: Icon và chữ thành màu Trắng. Chưa chọn thì mờ mờ (WHITE_54)
                    ft.Icon(item["icon"], color=ft.Colors.WHITE if is_active else ft.Colors.WHITE_54, size=22),
                    ft.Text(item["label"], size=13, color=ft.Colors.WHITE if is_active else ft.Colors.WHITE_54, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL, visible=self.is_sidebar_expanded)
                ]
            )

            self.sidebar_controls.append(
                ft.Container(
                    content=nav_content,
                    padding=ft.Padding(12, 10, 12, 10) if self.is_sidebar_expanded else ft.Padding(0, 10, 0, 10), 
                    border_radius=8, 
                    # Nền nút khi được chọn sẽ là màu trắng trong suốt (15%) để nổi bật trên nền xanh đen
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE) if is_active else ft.Colors.TRANSPARENT,
                    ink=True, on_click=create_nav_click(item["route"]),
                    tooltip=item["label"] if not self.is_sidebar_expanded else None 
                )
            )

            
            self.bottom_nav_controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(item["icon"], color=SECONDARY_COLOR if is_active else ft.Colors.GREY_500, size=22),
                        ft.Text(item["label"], size=10, color=SECONDARY_COLOR if is_active else ft.Colors.GREY_500, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    padding=ft.Padding(10, 5, 10, 5), border_radius=8, bgcolor=ft.Colors.TRANSPARENT,
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
        # Kiểm tra xem kích thước cửa sổ có rớt xuống chuẩn Mobile không
        is_mobile = self.app_page.width and self.app_page.width < 768
        
        if is_mobile:
            self.content.content = self.mobile_layout
            self.btn_menu_toggle.visible = False
            self.user_name_text.visible = False
        else:
            self.content.content = self.desktop_layout
            self.btn_menu_toggle.visible = True
            self.user_name_text.visible = True
            
        if getattr(self, "page", None):
            self.update()