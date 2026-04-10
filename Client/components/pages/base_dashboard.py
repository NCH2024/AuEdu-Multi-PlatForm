import flet as ft
import flet_geolocator as ftg
import json
import asyncio
import datetime
import httpx 
import flet_geolocator as geo
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
        
        # ___ Khởi tạo quyền truy cập vị trí _____
        self.geo = ftg.Geolocator(
            on_error=lambda e: print(f"[Geolocator Error] {e.data}")
        )
        # ─── KHỐI TIÊU ĐỀ TRANG ───
        self._page_title_raw_text = ft.Text(
            "TỔNG QUAN", size=13, 
            weight=ft.FontWeight.BOLD, 
            color=theme_module.current_theme.surface_color 
        )
        self.page_title_container = ft.Container(
            content=self._page_title_raw_text,
            bgcolor=theme_module.current_theme.primary, 
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=16, 
            alignment=ft.Alignment(0, 0)
        )
        
        # ─── KHỐI THỜI GIAN & VỊ TRÍ (CỤM PILL) ───
        self.clock_text = ft.Text("00:00:00", size=13, weight=ft.FontWeight.BOLD, color=theme_module.current_theme.primary)
        self.location_text = ft.Text("Đang định vị...", size=12, color=theme_module.current_theme.text_muted)
        
        # Các thành phần trang trí bên trong cụm
        self.clock_icon = ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=16, color=theme_module.current_theme.primary)
        self.loc_icon = ft.Icon(ft.Icons.LOCATION_ON_ROUNDED, size=15, color=theme_module.current_theme.text_muted)
        self.time_loc_divider = ft.Container(width=1, height=14, bgcolor=theme_module.current_theme.divider_color, margin=ft.Margin(6, 0, 6, 0))
        
        # Container bọc toàn bộ lại
        self.time_location_container = ft.Container(
            content=ft.Row([
                self.clock_icon,
                self.clock_text,
                self.time_loc_divider,
                self.loc_icon,
                self.location_text
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=theme_module.current_theme.surface_variant,
            border=ft.Border.all(1, theme_module.current_theme.divider_color),
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=20, # Bo tròn viên thuốc
            visible=False # Mặc định ẩn, sẽ bật lên khi ở trên Desktop
        )

        self.content_area = ft.Container(expand=True, padding=5, alignment=ft.Alignment.TOP_CENTER)
        
        self.sidebar_controls = []
        self.bottom_nav_controls = []
        
        self.content = ft.Container()

    def did_mount(self):
        self.app_page.run_task(self.init_app_settings)
        self.app_page.run_task(self._update_clock)
        
        if self._is_desktop_platform():
            self.app_page.run_task(self._update_location)

    def _is_desktop_platform(self):
        return self.app_page.platform in [
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ]

    async def _update_clock(self):
        while True:
            # Chỉ cập nhật nếu cụm time_location đang hiển thị
            if getattr(self, "page", None) and self.time_location_container.visible:
                now = datetime.datetime.now()
                self.clock_text.value = now.strftime("%H:%M:%S")
                try:
                    self.clock_text.update()
                except Exception:
                    pass
            await asyncio.sleep(1)

    async def _update_location(self):
        """Lấy vị trí chính xác bằng ftg.Geolocator + Nominatim"""
        await asyncio.sleep(2)
        
        headers = {"User-Agent": "AuEdu_PC_App (hiepnc.software@gmail.com)"}
        NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=12"

        try:
            # 1. Kiểm tra dịch vụ vị trí hệ thống
            if not await self.geo.is_location_service_enabled():
                self.location_text.value = "GPS đang tắt"
                self.location_text.update()
                return

            # 2. Kiểm tra và xin quyền
            p = await self.geo.get_permission_status()
            if p != ftg.GeolocatorPermissionStatus.ALWAYS and p != ftg.GeolocatorPermissionStatus.WHILE_IN_USE:
                p = await self.geo.request_permission()
            
            if p not in [ftg.GeolocatorPermissionStatus.ALWAYS, ftg.GeolocatorPermissionStatus.WHILE_IN_USE]:
                self.location_text.value = "Cần cấp quyền"
                self.location_text.update()
                return

            # 3. Lấy tọa độ hiện tại
            pos = await self.geo.get_current_position()
            if not pos: return

            # 4. Reverse Geocode để lấy tên địa danh
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(NOMINATIM_URL.format(lat=pos.latitude, lon=pos.longitude), headers=headers)
                if res.status_code == 200:
                    addr = res.json().get("address", {})
                    # Ưu tiên Huyện/Xã -> Tỉnh
                    district = addr.get("city_district") or addr.get("district") or addr.get("suburb") or addr.get("town") or addr.get("village")
                    state = addr.get("city") or addr.get("state")
                    
                    location_str = f"{district}, {state}" if district and state else (district or state or "Việt Nam")
                    self.location_text.value = location_str
                    self.location_text.update()

        except Exception as e:
            print(f"Lỗi định vị: {e}")
            self.location_text.value = "Lỗi định vị"
            self.location_text.update()
    
    async def init_app_settings(self):
        prefs = ft.SharedPreferences()
        is_dark = await prefs.get("app_is_dark") == "True"
        palette = await prefs.get("app_palette") or "BLUE"
        
        theme_module.current_theme.update_theme(is_dark=is_dark, palette_type=palette)
        
        self.app_page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        self.app_page.bgcolor = theme_module.current_theme.bg_color
        
        self.user_name_text.color = theme_module.current_theme.text_main
        
        # Cập nhật màu Title
        self._page_title_raw_text.color = theme_module.current_theme.surface_color
        self.page_title_container.bgcolor = theme_module.current_theme.primary
        
        # Cập nhật màu cụm Thời gian - Vị trí
        self.clock_text.color = theme_module.current_theme.primary
        self.clock_icon.color = theme_module.current_theme.primary
        self.location_text.color = theme_module.current_theme.text_muted
        self.loc_icon.color = theme_module.current_theme.text_muted
        self.time_loc_divider.bgcolor = theme_module.current_theme.divider_color
        
        self.time_location_container.bgcolor = theme_module.current_theme.surface_variant
        self.time_location_container.border = ft.Border.all(1, theme_module.current_theme.divider_color)

        saved_content = self.content_area.content
        self.content = self.build_layout()
        if saved_content is not None:
            self.content_area.content = saved_content

        self.update()
        self.app_page.update()

        session_str = await prefs.get("user_session")
        if session_str:
            try:
                session = json.loads(session_str)
                self.user_name_text.value = session.get("name", "Người dùng")
                self.user_name_text.update()
            except Exception:
                pass

    async def _apply_theme_to_current_page(self):
        current_page = self.content_area.content
        if current_page is not None and hasattr(current_page, "apply_theme"):
            current_page.apply_theme()

    async def toggle_dark_mode(self, e):
        prefs = ft.SharedPreferences()
        new_is_dark = not theme_module.current_theme.is_dark
        await prefs.set("app_is_dark", "True" if new_is_dark else "False")
        await self.init_app_settings()
        await self._apply_theme_to_current_page()

    async def change_palette(self, p_type):
        prefs = ft.SharedPreferences()
        await prefs.set("app_palette", p_type)
        for item in self.app_page.overlay[:]:
            if isinstance(item, ft.AlertDialog) and item.open:
                item.open = False
        await self.init_app_settings()
        await self._apply_theme_to_current_page()

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
        
        if dialog not in self.app_page.overlay:
            self.app_page.overlay.append(dialog)
        dialog.open = True
        self.app_page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.app_page.update()

    def set_content(self, title: str, new_content: ft.Control, route: str):
        self._page_title_raw_text.value = title.upper() 
        self.content_area.content = new_content
        self.active_route = route
        self.build_navigation()

        if hasattr(self, "sidebar") and getattr(self.sidebar, "content", None):
            self.sidebar.content.controls[0].controls = self.sidebar.content.controls[0].controls[:1] + self.sidebar_controls

        if hasattr(self, "bottom_nav") and getattr(self.bottom_nav, "content", None):
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
            color=theme_module.current_theme.text_main, 
            padding=0 
        )
        btn_style_close = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            overlay_color=ft.Colors.RED_600,
            color={ft.ControlState.HOVERED: ft.Colors.WHITE, ft.ControlState.DEFAULT: theme_module.current_theme.text_main},
            padding=0
        )

        async def handle_minimize(e):
            self.app_page.window.minimized = True
            self.app_page.update()

        async def handle_maximize(e):
            self.app_page.window.maximized = not self.app_page.window.maximized
            e.control.icon = ft.Icons.FILTER_NONE if self.app_page.window.maximized else ft.Icons.CROP_SQUARE
            e.control.update()
            self.app_page.update()

        async def handle_close(e):
            await self.app_page.window.close()

        btn_width = 38
        btn_height = 30
        current_max_icon = ft.Icons.FILTER_NONE if self.app_page.window.maximized else ft.Icons.CROP_SQUARE

        return ft.WindowDragArea(
            ft.Container(
                height=btn_height, 
                bgcolor=theme_module.current_theme.bg_color,
                padding=ft.Padding(15, 0, 0, 0),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row([
                            ft.Icon(ft.Icons.AUTO_AWESOME, color=theme_module.current_theme.text_main, size=16),
                            ft.Text("AuEdu PC", color=theme_module.current_theme.text_main, size=12, weight=ft.FontWeight.BOLD)
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Row(
                            spacing=0, 
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.IconButton(ft.Icons.REMOVE, icon_size=16, style=btn_style_normal, width=btn_width, height=btn_height, on_click=handle_minimize),
                                ft.IconButton(current_max_icon, icon_size=16, style=btn_style_normal, width=btn_width, height=btn_height, on_click=handle_maximize),
                                ft.IconButton(ft.Icons.CLOSE, icon_size=16, style=btn_style_close, width=btn_width, height=btn_height, on_click=handle_close),
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
            show_confirm_dialog(
                self.app_page, "Xác nhận đăng xuất",
                "Bạn có chắc chắn muốn đăng xuất?",
                lambda: self.app_page.run_task(self._do_normal_logout)
            )

        is_mobile = (self.app_page.width and self.app_page.width < 768) or \
                    self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        self.btn_menu_toggle = ft.IconButton(
            icon=ft.Icons.MENU_ROUNDED,
            icon_color=theme_module.current_theme.text_main,
            on_click=self.toggle_sidebar, visible=not is_mobile
        )
        self.user_name_text.visible = not is_mobile
        
        # Hiển thị khối thời gian & vị trí nếu không phải mobile
        self.time_location_container.visible = not is_mobile

        popup_items = [
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.PALETTE_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Đổi màu giao diện", color=theme_module.current_theme.text_main)]),
                on_click=self.open_theme_dialog
            ),
        ]

        if is_mobile:
            popup_items.append(
                ft.PopupMenuItem(
                    content=ft.Row([ft.Icon(ft.Icons.DARK_MODE_OUTLINED, color=theme_module.current_theme.text_main), ft.Text("Chế độ Sáng/Tối", color=theme_module.current_theme.text_main)]),
                    on_click=self.toggle_dark_mode
                )
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
                    # Cột trái (Nút menu và Tiêu đề)
                    ft.Row(spacing=5, controls=[
                        self.btn_menu_toggle,
                        ft.Container(width=5),
                        self.page_title_container
                    ], expand=1),
                    
                    # Cột giữa (Hiển thị nguyên 1 viên thuốc chứa CẢ thời gian và vị trí)
                    ft.Row([
                        self.time_location_container 
                    ], alignment=ft.MainAxisAlignment.CENTER, expand=1),
                    
                    # Cột phải (Avatar và Menu tùy chọn)
                    ft.Row(spacing=5, alignment=ft.MainAxisAlignment.END, controls=[
                        ft.Container(
                            ink=True, on_click=go_to_profile, border_radius=50,
                            padding=ft.Padding(3, 3, 3, 3),
                            bgcolor=ft.Colors.with_opacity(0.08, theme_module.current_theme.text_main),
                            content=ft.Row(spacing=8, controls=[
                                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=theme_module.current_theme.bg_color, size=16), bgcolor=theme_module.current_theme.secondary, radius=16),
                                self.user_name_text,
                                ft.Container(width=3, visible=not is_mobile),
                            ])
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT, icon_color=theme_module.current_theme.text_main, icon_size=25,
                            items=popup_items
                        )
                    ], expand=1)
                ]
            )
        )

        windows_title_bar = self.build_windows_title_bar()
        top_bar_area = ft.Column(spacing=0, controls=[windows_title_bar, header_content])

        if not hasattr(self, "content_area") or self.content_area is None:
            self.content_area = ft.Container(
                expand=True,
                padding=10,
                alignment=ft.Alignment.TOP_CENTER
            )
        main_view_stack = ft.Column(
            expand=True, spacing=0,
            controls=[top_bar_area, self.content_area]
        )

        self.build_navigation()

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
                                ft.Icon(
                                    ft.Icons.LIGHT_MODE_ROUNDED if theme_module.current_theme.is_dark else ft.Icons.DARK_MODE_ROUNDED,
                                    color=on_secondary_color, size=22
                                ),
                                ft.Text(
                                    "Chế độ: " + ("Sáng" if theme_module.current_theme.is_dark else "Tối"),
                                    size=14, color=on_secondary_color, weight=ft.FontWeight.W_600,
                                    visible=self.is_sidebar_expanded
                                )
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

        self.desktop_layout = ft.Row(
            controls=[self.sidebar, ft.Container(content=main_view_stack, expand=True, padding=0)],
            expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START
        )
        self.mobile_layout = ft.Stack(
            controls=[ft.Container(content=main_view_stack, expand=True, padding=0), self.bottom_nav],
            expand=True
        )

        return ft.SafeArea(content=self.mobile_layout if is_mobile else self.desktop_layout)

    def build_navigation(self):
        self.sidebar_controls.clear()
        self.bottom_nav_controls.clear()

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
                    ink=True, on_click=create_nav_click(item["route"]),
                    tooltip=item["label"] if not self.is_sidebar_expanded else None
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
            self.time_location_container.visible = False # Ẩn toàn bộ khối thời gian/vị trí trên Mobile
        else:
            self.content.content = self.desktop_layout
            self.btn_menu_toggle.visible = True
            self.user_name_text.visible = True
            self.time_location_container.visible = True # Bật toàn bộ khối trên PC

        if getattr(self, "page", None):
            self.update()