import flet as ft
import json
import core.theme as theme_module
from components.options.confirm_dialog import show_confirm_dialog 

class BaseDashboard(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.active_route = ""
        self.is_sidebar_expanded = False
        
        
        self.menu_items = [
            {"label": "Tổng quan", "icon": ft.Icons.DASHBOARD_ROUNDED, "route": "/user/home"},
            {"label": "Điểm danh", "icon": ft.Icons.CAMERA_ALT_ROUNDED, "route": "/user/attendance"},
            {"label": "Lịch học", "icon": ft.Icons.CALENDAR_MONTH_ROUNDED, "route": "/user/schedule"},
            {"label": "Thống kê", "icon": ft.Icons.PIE_CHART_ROUNDED, "route": "/user/stats"},
        ]

        self.user_name_text = ft.Text("Đang tải...", size=13, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.page_title_text = ft.Text("TỔNG QUAN", size=15, weight=ft.FontWeight.BOLD, color=theme_module.current_theme.primary)
        self.content_area = ft.Container(expand=True, padding=ft.Padding(10, 10, 10, 10), alignment=ft.Alignment.TOP_CENTER)
        
        self.sidebar_controls = []
        self.bottom_nav_controls = []
        
        self.content = ft.Container() 

    def did_mount(self):
        self.app_page.run_task(self.init_app_settings)

    async def init_app_settings(self):
        prefs = ft.SharedPreferences()
        is_dark = await prefs.get("app_is_dark") == "True"
        palette = await prefs.get("app_palette") or "BLUE"
        
        # GỌI HÀM UPDATE (KHÔNG TẠO MỚI) ĐỂ ĐỒNG BỘ TOÀN BỘ APP
        theme_module.current_theme.update_theme(is_dark=is_dark, palette_type=palette)
        
        self.app_page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        self.app_page.bgcolor = theme_module.current_theme.bg_color
        
        self.user_name_text.color = theme_module.current_theme.text_main
        self.page_title_text.color = theme_module.current_theme.primary
        
        self.content = self.build_layout()
        self.update()
        self.app_page.update()
        
        session_str = await prefs.get("user_session")
        if session_str:
            try:
                session = json.loads(session_str)
                self.user_name_text.value = session.get("name", "Người dùng")
                self.user_name_text.update()
            except: pass

   # ==========================================
    # LOGIC CHUYỂN ĐỔI THEME VÀ MÀU SẮC SIÊU MƯỢT
    # ==========================================
    async def toggle_dark_mode(self, e):
        prefs = ft.SharedPreferences()
        new_is_dark = not theme_module.current_theme.is_dark
        await prefs.set("app_is_dark", "True" if new_is_dark else "False")
        await self.init_app_settings()
        
        # KIỂM TRA: Nếu trang hiện tại có hàm apply_theme thì gọi nó thay vì load lại trang
        if hasattr(self.content_area.content, 'apply_theme'):
            self.content_area.content.apply_theme()

    async def change_palette(self, p_type):
        prefs = ft.SharedPreferences()
        await prefs.set("app_palette", p_type)
        for item in self.app_page.overlay[:]:
            if isinstance(item, ft.AlertDialog) and item.open:
                item.open = False
        await self.init_app_settings()
        
        # KIỂM TRA: Nếu trang hiện tại có hàm apply_theme thì gọi nó thay vì load lại trang
        if hasattr(self.content_area.content, 'apply_theme'):
            self.content_area.content.apply_theme()

    def open_theme_dialog(self, e):
        def build_palette_option(name, primary, secondary, accent, p_type):
            is_active = theme_module.current_theme.palette_type == p_type
            return ft.Container(
                padding=15, border_radius=12, 
                border=ft.Border.all(2, primary if is_active else theme_module.current_theme.divider_color),
                bgcolor=theme_module.current_theme.surface_variant if is_active else theme_module.current_theme.surface_color,
                ink=True, on_click=lambda e: self.app_page.run_task(self.change_palette, p_type),
                content=ft.Row([
                    ft.Text(name, expand=True, weight=ft.FontWeight.BOLD, color=theme_module.current_theme.text_main),
                    ft.Row([
                        ft.Container(width=24, height=24, bgcolor=primary, border_radius=12),
                        ft.Container(width=24, height=24, bgcolor=secondary, border_radius=12),
                        ft.Container(width=24, height=24, bgcolor=accent, border_radius=12),
                    ], spacing=5)
                ])
            )

        dialog = ft.AlertDialog(
            title=ft.Text("CHỌN MÀU GIAO DIỆN", weight=ft.FontWeight.BOLD, color=theme_module.current_theme.text_main, size=16),
            content=ft.Column(
                tight=True, spacing=10,
                controls=[
                    build_palette_option("Hồng Phấn (Ngọt ngào)", "#EC4899", "#BE185D", "#F472B6", "PINK"),
                    build_palette_option("Xanh Dương Tươi (Mặc định)", "#2563EB", "#1D4ED8", "#3B82F6", "BLUE"),
                    build_palette_option("Xanh Lá Pastel", "#10B981", "#047857", "#34D399", "GREEN"),
                    build_palette_option("Đen Trắng (Tối giản)", "#111827", "#000000", "#6B7280", "MONO"),
                ]
            ),
            actions=[ft.TextButton("Đóng", on_click=lambda e: self._close_dialog(dialog))],
            bgcolor=theme_module.current_theme.surface_color,
            shape=ft.RoundedRectangleBorder(radius=16)
        )
        self.app_page.overlay.append(dialog)
        dialog.open = True
        self.app_page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.app_page.update()

    # ==========================================
    # QUẢN LÝ GIAO DIỆN
    # ==========================================
    def set_content(self, title: str, new_content: ft.Control, route: str):
        self.page_title_text.value = title.upper()
        self.content_area.content = new_content
        self.active_route = route
        self.build_navigation()
        
        # BẢO VỆ CHỐNG CRASH: Chỉ cập nhật Sidebar/BottomNav khi chúng thực sự đã được tạo ra
        if hasattr(self, "sidebar") and getattr(self.sidebar, "content", None):
            self.sidebar.content.controls[0].controls = self.sidebar.content.controls[0].controls[:1] + self.sidebar_controls
            
        if hasattr(self, "bottom_nav") and getattr(self.bottom_nav, "content", None):
            # SỬA LỖI TẠI ĐÂY: Đổi từ .content.content.controls thành .content.controls
            self.bottom_nav.content.controls = self.bottom_nav_controls
            
        if getattr(self, "page", None): 
            self.update()

    def toggle_sidebar(self, e):
        self.is_sidebar_expanded = not self.is_sidebar_expanded
        self.btn_menu_toggle.icon = ft.Icons.MENU_OPEN_ROUNDED if self.is_sidebar_expanded else ft.Icons.MENU_ROUNDED
        self.sidebar.width = 220 if self.is_sidebar_expanded else 70
        self.build_navigation()
        self.sidebar.content.controls[0].controls = self.sidebar.content.controls[0].controls[:1] + self.sidebar_controls
        self.update()

    async def _do_normal_logout(self):
        prefs = ft.SharedPreferences()
        await prefs.remove("user_session")
        await self.app_page.push_route("/login")

    def build_windows_title_bar(self):
        if self.app_page.platform != ft.PagePlatform.WINDOWS:
            return ft.Container(height=0, visible=False)
            
        btn_style_normal = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color=ft.Colors.with_opacity(0.1, theme_module.current_theme.text_main),
            color=theme_module.current_theme.text_main, padding=10
        )
        
        btn_style_close = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color=ft.Colors.RED_600,
            color={ft.ControlState.HOVERED: ft.Colors.WHITE, ft.ControlState.DEFAULT: theme_module.current_theme.text_main},
            padding=10
        )

        async def handle_minimize(e):
            self.app_page.window.minimized = True
            self.app_page.update()

        async def handle_maximize(e):
            self.app_page.window.maximized = not self.app_page.window.maximized
            self.app_page.update()

        async def handle_close(e):
            await self.app_page.window.close()
            
        # THANH TIÊU ĐỀ: Dùng đúng màu bg_color tĩnh
        return ft.WindowDragArea(
            ft.Container(
                height=25,
                bgcolor=theme_module.current_theme.bg_color,
                padding=ft.Padding(15, 0, 0, 0), 
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, color=theme_module.current_theme.text_main, size=16),
                            ft.Text("AuEdu PC", color=theme_module.current_theme.text_main, size=12, weight=ft.FontWeight.BOLD)
                        ]),
                        ft.Row(
                            spacing=0,
                            alignment=ft.Alignment(0,0),
                            controls=[
                                ft.IconButton(ft.Icons.MINIMIZE, icon_size=16, style=btn_style_normal, width=34, height=25,on_click=handle_minimize),
                                ft.IconButton(ft.Icons.CROP_SQUARE, icon_size=16, style=btn_style_normal, width=34, height=25, on_click=handle_maximize),
                                ft.IconButton(ft.Icons.CLOSE, icon_size=16, style=btn_style_close, width=34, height=25, on_click=handle_close),
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
            show_confirm_dialog(self.app_page, "Xác nhận đăng xuất", "Bạn có chắc chắn muốn đăng xuất?", lambda: self.app_page.run_task(self._do_normal_logout))

        is_mobile = (self.app_page.width and self.app_page.width < 768) or self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        self.btn_menu_toggle = ft.IconButton(
            icon=ft.Icons.MENU_ROUNDED, 
            icon_color=theme_module.current_theme.text_main, 
            on_click=self.toggle_sidebar, visible=not is_mobile 
        )
        self.user_name_text.visible = not is_mobile

        popup_items = [
            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.PALETTE_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Đổi màu giao diện", color=theme_module.current_theme.text_main)]), on_click=self.open_theme_dialog),
        ]
        
        if is_mobile:
            popup_items.append(
                ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.DARK_MODE_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Chế độ Sáng/Tối", color=theme_module.current_theme.text_main)]), on_click=self.toggle_dark_mode)
            )
            
        popup_items.extend([
            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Hồ sơ tài khoản", color=theme_module.current_theme.text_main)]), on_click=go_to_profile),
            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Cài đặt phần mềm", color=theme_module.current_theme.text_main)]), on_click=go_to_settings),
            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Thông tin phần mềm", color=theme_module.current_theme.text_main)]), on_click=handle_about),
            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.LOGOUT, color=ft.Colors.RED_500), ft.Text("Đăng xuất", color=ft.Colors.RED_500)]), on_click=handle_normal_logout),
        ])

        header_content = ft.Container(
            padding=ft.Padding.all(1), 
            bgcolor=theme_module.current_theme.surface_color,
            border=ft.Border(bottom=ft.BorderSide(1, theme_module.current_theme.divider_color)),
            alignment=ft.Alignment.TOP_CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=5, controls=[
                        self.btn_menu_toggle, 
                        ft.Container(
                            width=5
                        ),
                        self.page_title_text
                        ]),
                    ft.Row(spacing=5, controls=[
                        ft.Container(
                            ink=True, on_click=go_to_profile, border_radius=50,
                            padding=ft.Padding(3, 3, 3, 3),
                            bgcolor=ft.Colors.with_opacity(0.08, theme_module.current_theme.text_main),
                            content=ft.Row(spacing=8, controls=[
                                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=theme_module.current_theme.bg_color, size=16), bgcolor=theme_module.current_theme.secondary, radius=16),
                                self.user_name_text,
                                ft.Container(width=3, visible=False if is_mobile else True),
                            ])
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT, icon_color=theme_module.current_theme.text_main, icon_size=25,
                            items=popup_items
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
                self.content_area, 
            ]
        )
        
        main_view_stack = ft.Column(
            expand=True, spacing=0,
            controls=[top_bar_area, scroll_wrapper]
        )

        self.build_navigation()

        # ⚠️ NÂNG CẤP: Tính toán màu tương phản cho các item trong Sidebar
        on_secondary_color = ft.Colors.BLACK_87 if theme_module.current_theme.is_dark else ft.Colors.WHITE
        on_secondary_bg_overlay = ft.Colors.with_opacity(0.1, ft.Colors.BLACK) if theme_module.current_theme.is_dark else ft.Colors.with_opacity(0.1, ft.Colors.WHITE)

        self.sidebar = ft.Container(
            width=220 if self.is_sidebar_expanded else 70, 
            bgcolor=theme_module.current_theme.secondary,
            animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=8, alignment=ft.MainAxisAlignment.START,
                        controls=[
                            ft.Container(
                                padding=ft.Padding(0, 20, 0, 20), alignment=ft.Alignment.CENTER,
                                # Đổi logo tạm nếu cần cho hiển thị rõ (giữ icon-1.png gốc)
                                content=ft.Image(src="icon-1.png", width=35, height=35, fit=ft.BoxFit.CONTAIN)
                            )
                        ] + self.sidebar_controls
                    ),
                    ft.Container(
                        padding=ft.Padding(16, 12, 16, 12) if self.is_sidebar_expanded else ft.Padding(0, 12, 0, 12),
                        margin=ft.Margin(10, 0, 10, 15), border_radius=12,
                        ink=True, on_click=self.toggle_dark_mode,
                        bgcolor=on_secondary_bg_overlay,
                        visible=not is_mobile,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.START if self.is_sidebar_expanded else ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.LIGHT_MODE_ROUNDED if theme_module.current_theme.is_dark else ft.Icons.DARK_MODE_ROUNDED, color=on_secondary_color, size=22),
                                ft.Text("Chế độ: " + ("Sáng" if theme_module.current_theme.is_dark else "Tối"), size=14, color=on_secondary_color, weight=ft.FontWeight.W_600, visible=self.is_sidebar_expanded)
                            ]
                        )
                    )
                ]
            )
        )

        self.bottom_nav = ft.Container(
            bottom=0, left=0, right=0, 
            bgcolor=theme_module.current_theme.secondary,
            content=ft.Row(controls=self.bottom_nav_controls, alignment=ft.MainAxisAlignment.SPACE_AROUND, height=60)
        )

        self.desktop_layout = ft.Row(controls=[self.sidebar, ft.Container(content=main_view_stack, expand=True, padding=0)], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)
        self.mobile_layout = ft.Stack(controls=[ft.Container(content=main_view_stack, expand=True, padding=0), self.bottom_nav], expand=True)

        return ft.SafeArea(content=self.mobile_layout if is_mobile else self.desktop_layout)

    def build_navigation(self):
        self.sidebar_controls.clear()
        self.bottom_nav_controls.clear()

        # Đổi màu icon và text tương phản hoàn toàn với màu nền Sidebar
        on_secondary_color = ft.Colors.BLACK_87 if theme_module.current_theme.is_dark else ft.Colors.WHITE
        on_secondary_color_muted = ft.Colors.BLACK_54 if theme_module.current_theme.is_dark else ft.Colors.WHITE_54
        on_secondary_bg_active = ft.Colors.with_opacity(0.15, ft.Colors.BLACK) if theme_module.current_theme.is_dark else ft.Colors.with_opacity(0.15, ft.Colors.WHITE)

        for item in self.menu_items:
            is_active = self.active_route == item["route"]
            def create_nav_click(route):
                async def on_click(e):
                    if self.active_route != route:
                        await self.app_page.push_route(route)
                return on_click

            icon_color = on_secondary_color if is_active else on_secondary_color_muted
            text_color = on_secondary_color if is_active else on_secondary_color_muted
            bg_active = on_secondary_bg_active if is_active else ft.Colors.TRANSPARENT

            nav_content = ft.Row(
                alignment=ft.MainAxisAlignment.START if self.is_sidebar_expanded else ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(item["icon"], color=icon_color, size=22),
                    ft.Text(item["label"], size=14, color=text_color, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL, visible=self.is_sidebar_expanded)
                ]
            )

            self.sidebar_controls.append(
                ft.Container(
                    content=nav_content,
                    padding=ft.Padding(16, 12, 16, 12) if self.is_sidebar_expanded else ft.Padding(0, 12, 0, 12), 
                    border_radius=12, margin=ft.Margin(10, 0, 10, 0), bgcolor=bg_active,
                    ink=True, on_click=create_nav_click(item["route"]), tooltip=item["label"] if not self.is_sidebar_expanded else None 
                )
            )
            
            self.bottom_nav_controls.append(
                ft.Container(
                    expand=True,
                    content=ft.Column([
                        ft.Icon(item["icon"], color=icon_color, size=24),
                        ft.Text(item["label"], size=11, color=text_color, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    ink=True, on_click=create_nav_click(item["route"])
                )
            )

    async def handle_resize(self, e):
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