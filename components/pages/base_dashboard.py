import flet as ft
from core.theme import get_glass_container, PRIMARY_COLOR

class BaseDashboard(ft.Container):
    def __init__(self, page: ft.Page, active_route: str, main_content: ft.Control):
        super().__init__()
        self.app_page = page
        self.active_route = active_route
        self.main_content = main_content
        self.expand = True
        
        # ĐÃ KHẮC PHỤC LỖI MẤT HÌNH: 
        # Sử dụng thuộc tính "image" kết hợp ft.DecorationImage để gắn ảnh nền
        self.image = ft.DecorationImage(
            src="images/background.jpg", # Đảm bảo file nằm trong thư mục assets/images/
            fit=ft.BoxFit.COVER,
            opacity=0.8 
        )
        
        self.menu_items = [
            {"label": "Tổng quan", "icon": ft.Icons.DASHBOARD_ROUNDED, "route": "/user/home"},
            {"label": "Điểm danh", "icon": ft.Icons.CAMERA_ALT_ROUNDED, "route": "/user/attendance"},
            {"label": "Lịch điểm danh", "icon": ft.Icons.CALENDAR_MONTH_ROUNDED, "route": "/user/schedule"},
            {"label": "Thống kê", "icon": ft.Icons.PIE_CHART_ROUNDED, "route": "/user/stats"},
            # {"label": "Cài đặt", "icon": ft.Icons.SETTINGS_ROUNDED, "route": "/user/settings"},
        ]

        self.content = self.build_layout()
        self.app_page.on_resized = self.handle_resize

    def build_layout(self):
        """Khởi tạo bố cục khung sườn cho Dashboard."""
        
        async def handle_logout(e):
            """Xử lý sự kiện đăng xuất người dùng."""
            self.app_page.session.store.remove("user_session") 
            await self.app_page.push_route("/login")

        btn_logout = ft.Button(
            content=ft.Text("Đăng xuất", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
            bgcolor=ft.Colors.BLUE_400,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5)),
            on_click=handle_logout
        )

        self.sidebar = get_glass_container(
            width=250,
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("AuEdu", size=32, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                            btn_logout
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.Padding(left=0, top=10, right=0, bottom=20),
                        alignment=ft.Alignment(0, 0)
                    )
                ] + [self._create_sidebar_item(item) for item in self.menu_items],
                spacing=5
            )
        )

        self.bottom_nav = get_glass_container(
            padding=10,
            content=ft.Row(
                controls=[self._create_bottom_nav_item(item) for item in self.menu_items],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        # Căn chỉnh top_center để nội dung đổ từ trên xuống
        self.content_area = ft.Container(
            content=self.main_content, 
            expand=True, 
            padding=0,
            alignment=ft.Alignment.TOP_CENTER
        )
        
        # Bắt buộc đặt vertical_alignment=START để thẻ nội dung dính lên mép trên màn hình Desktop
        self.desktop_layout = ft.Row(
            controls=[self.sidebar, self.content_area], 
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START 
        )
        
        # Màn hình Mobile thì tự động đổ từ trên xuống do là Column
        self.mobile_layout = ft.Column(
            controls=[self.content_area, self.bottom_nav], 
            expand=True
        )

        initial_layout = self.mobile_layout if (self.app_page.width and self.app_page.width < 768) else self.desktop_layout
        
        # ĐÃ SỬA: Đảm bảo SafeArea không có màu nền đè lên Container cha
        return ft.SafeArea(content=initial_layout)

    def _create_sidebar_item(self, item):
        """Khởi tạo thành phần nút bấm trên Sidebar (Desktop)."""
        is_active = self.active_route == item["route"]
        
        async def on_nav_click(e): 
            await self.app_page.push_route(item["route"])
            
        return ft.Container(
            content=ft.Row([
                ft.Icon(item["icon"], color=PRIMARY_COLOR if is_active else ft.Colors.BLACK_87),
                ft.Text(item["label"], color=PRIMARY_COLOR if is_active else ft.Colors.BLACK_87, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL)
            ]),
            padding=15, 
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(0.1, PRIMARY_COLOR) if is_active else ft.Colors.TRANSPARENT,
            ink=True, 
            on_click=on_nav_click 
        )

    def _create_bottom_nav_item(self, item):
        """Khởi tạo thành phần nút bấm trên Bottom Navigation (Mobile)."""
        is_active = self.active_route == item["route"]
        
        async def on_nav_click(e): 
            await self.app_page.push_route(item["route"])
            
        return ft.Container(
            content=ft.Column([
                ft.Icon(item["icon"], color=PRIMARY_COLOR if is_active else ft.Colors.BLACK_87),
                ft.Text(item["label"], size=11, color=PRIMARY_COLOR if is_active else ft.Colors.BLACK_87, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            ink=True, 
            padding=5, 
            border_radius=10, 
            on_click=on_nav_click 
        )

    async def handle_resize(self, e):
        """Xử lý sự kiện thay đổi kích thước cửa sổ để chuyển đổi layout."""
        if self.app_page.width and self.app_page.width < 768:
            self.content.content = self.mobile_layout
        else:
            self.content.content = self.desktop_layout
        self.update()