import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid

class AdminFacesPage(ft.Container):
    """Trang quản lý dữ liệu khuôn mặt dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.svc = AdminService.instance()

        # -- State --
        self.all_data = []
        self.classes_list = []

        # -- UI Elements --
        self.title_text = ft.Text("QUẢN LÝ DỮ LIỆU KHUÔN MẶT", size=20, weight=ft.FontWeight.BOLD)
        
        # Thống kê
        self.stat_total = self._build_stat_card("TỔNG SINH VIÊN", "0", ft.Icons.PEOPLE_ROUNDED, ft.Colors.BLUE)
        self.stat_trained = self._build_stat_card("ĐÃ CÓ DỮ LIỆU", "0", ft.Icons.FACE_ROUNDED, ft.Colors.GREEN)
        self.stat_pending = self._build_stat_card("CHƯA CÓ DỮ LIỆU", "0", ft.Icons.FACE_RETOUCHING_OFF_ROUNDED, ft.Colors.ORANGE)

        self.class_filter = ft.Dropdown(
            label="Lọc theo Lớp", width=200, height=38,
            options=[ft.dropdown.Option("all", "Tất cả lớp")], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.class_filter.on_change = self.load_data

        self.search_field = ft.TextField(
            hint_text="Tìm MSSV hoặc Tên...", width=250, height=38,
            prefix_icon=ft.Icons.SEARCH, border_radius=8, text_size=12,
            content_padding=ft.Padding(10, 0, 10, 0), on_submit=self.load_data
        )

        self.grid = AdminDataGrid(
            columns=[
                {"label": "MSSV", "key": "id", "col": {"xs": 4, "sm": 1.5}, "sortable": True},
                {"label": "HỌ TÊN", "key": "full_name", "col": {"xs": 8, "sm": 3}, "sortable": True},
                {"label": "LỚP", "key": "tenlop", "col": {"xs": 6, "sm": 2}},
                {"label": "TRẠNG THÁI", "key": "status", "col": {"xs": 6, "sm": 2}, "render": self.render_status},
                {"label": "NGÀY CẬP NHẬT", "key": "trained_at", "col": {"xs": 6, "sm": 2}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1.5}, "render": self.render_actions},
            ],
            rows_per_page=30
        )

        self.content = ft.Column([
            ft.Row([self.title_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Row([self.stat_total, self.stat_trained, self.stat_pending], spacing=15),
            ft.Container(height=15),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        self.search_field,
                        self.class_filter,
                        ft.VerticalDivider(width=1, color=current_theme.divider_color),
                        ft.IconButton(ft.Icons.REFRESH_ROUNDED, on_click=self.refresh_data)
                    ], spacing=10),
                    self.grid
                ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, expand=True),
                padding=15, border=ft.Border.all(1, current_theme.divider_color),
                border_radius=12, bgcolor=current_theme.surface_color, expand=True
            )
        ], expand=True)

    def _build_stat_card(self, title, value, icon, color):
        return ft.Container(
            expand=True, padding=15, border_radius=10,
            bgcolor=current_theme.surface_color,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=30),
                    padding=10, bgcolor=ft.Colors.with_opacity(0.1, color),
                    border_radius=8
                ),
                ft.Column([
                    ft.Text(title, size=11, color=current_theme.text_muted, weight=ft.FontWeight.W_500),
                    ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
                ], spacing=2)
            ], spacing=15)
        )

    def render_status(self, item):
        has_face = item.get("has_face", False)
        return ft.Container(
            padding=ft.Padding(8, 4, 8, 4), border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN if has_face else ft.Colors.RED),
            content=ft.Text(
                "ĐÃ CÓ" if has_face else "CHƯA CÓ",
                size=10, weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREEN if has_face else ft.Colors.RED
            )
        )

    def render_actions(self, item):
        return ft.Row([
            ft.IconButton(
                ft.Icons.FACE_RETOUCHING_NATURAL_ROUNDED, 
                tooltip="Đào tạo khuôn mặt", 
                icon_color=current_theme.primary,
                on_click=lambda e: self.app_page.run_task(self.go_to_training, item)
            ),
            ft.IconButton(
                ft.Icons.DELETE_SWEEP_ROUNDED, 
                tooltip="Xóa dữ liệu Face", 
                icon_color=ft.Colors.RED_400,
                visible=item.get("has_face", False),
                on_click=lambda e: self.app_page.run_task(self.reset_face, item)
            )
        ], spacing=0)

    def did_mount(self):
        self.app_page.run_task(self.initialize_page)

    async def initialize_page(self):
        await self.load_classes() # Phải load danh sách lớp trước để có options
        await self.load_stats()
        
        # Sau khi có options mới khôi phục trạng thái từ session
        saved_class = self.app_page.session.store.get("faces_filter_class")
        saved_search = self.app_page.session.store.get("faces_filter_search")
        
        if saved_class:
            self.class_filter.value = saved_class
        if saved_search:
            self.search_field.value = saved_search

        await self.load_data()

    async def load_classes(self):
        try:
            self.classes_list = await self.svc.get_classes()
            self.class_filter.options = [ft.dropdown.Option("all", "Tất cả lớp")]
            for c in self.classes_list:
                self.class_filter.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
        except: pass

    async def load_stats(self):
        try:
            stats = await self.svc.get("/api/admin/faces/stats")
            self.stat_total.content.controls[1].controls[1].value = str(stats["total_students"])
            self.stat_trained.content.controls[1].controls[1].value = str(stats["trained_students"])
            self.stat_pending.content.controls[1].controls[1].value = str(stats["pending_students"])
            self.update()
        except: pass

    async def refresh_data(self, e=None):
        await self.load_stats()
        await self.load_data()

    async def load_data(self, e=None):
        try:
            params = {
                "class_id": self.class_filter.value,
                "search": self.search_field.value
            }
            # Lưu trạng thái vào session
            self.app_page.session.store.set("faces_filter_class", self.class_filter.value)
            self.app_page.session.store.set("faces_filter_search", self.search_field.value)
            
            data = await self.svc.get("/api/admin/faces/list/", params=params)
            self.grid.set_data(data)
            self.update()
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", str(ex), ft.Colors.RED)

    async def go_to_training(self, item):
        """Chuyển sang trang đào tạo khuôn mặt với sinh viên đã chọn."""
        try:
            self.app_page.session.store.set("admin_train_sv_id", item["id"])
            await self.app_page.push_route("/admin/face-training")
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", str(e), ft.Colors.RED)

    async def reset_face(self, item):
        async def on_confirm():
            try:
                await self.svc.delete(f"/api/admin/faces/{item['id']}")
                show_top_notification(self.app_page, "Thành công", f"Đã xóa dữ liệu khuôn mặt của {item['full_name']}", ft.Colors.GREEN)
                await self.initialize_page()
            except Exception as ex:
                show_top_notification(self.app_page, "Lỗi", str(ex), ft.Colors.RED)
        
        from components.options.confirm_dialog import show_confirm_dialog
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Bạn có chắc muốn xóa dữ liệu khuôn mặt của {item['full_name']}? Sinh viên sẽ phải đào tạo lại từ đầu.", on_confirm)
