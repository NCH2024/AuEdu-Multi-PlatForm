import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid
from datetime import datetime

class AdminAttendanceReportPage(ft.Container):
    """Trang báo cáo điểm danh toàn hệ thống dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.svc = AdminService.instance()

        # -- State --
        self.subjects_list = []
        self.classes_list = []

        # -- UI Elements --
        self.title_text = ft.Text("BÁO CÁO ĐIỂM DANH HỆ THỐNG", size=20, weight=ft.FontWeight.BOLD)
        
        # Thống kê nhanh
        self.stat_present = self._build_stat_card("CÓ MẶT", "0", ft.Icons.CHECK_CIRCLE_OUTLINED, ft.Colors.GREEN)
        self.stat_absent = self._build_stat_card("VẮNG MẶT", "0", ft.Icons.CANCEL_OUTLINED, ft.Colors.RED)
        self.stat_late = self._build_stat_card("ĐI TRỄ", "0", ft.Icons.ACCESS_TIME_OUTLINED, ft.Colors.ORANGE)

        # Bộ lọc
        self.class_filter = ft.Dropdown(
            label="Lớp", width=160, height=38,
            options=[ft.dropdown.Option("all", "Tất cả lớp")], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.class_filter.on_change = self.load_data

        self.subject_filter = ft.Dropdown(
            label="Môn học", width=220, height=38,
            options=[ft.dropdown.Option("all", "Tất cả môn")], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.subject_filter.on_change = self.load_data

        self.status_filter = ft.Dropdown(
            label="Trạng thái", width=120, height=38,
            options=[
                ft.dropdown.Option("all", "Tất cả"),
                ft.dropdown.Option("Có mặt", "Có mặt"),
                ft.dropdown.Option("Vắng", "Vắng"),
                ft.dropdown.Option("Đi trễ", "Đi trễ")
            ], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.status_filter.on_change = self.load_data

        self.search_field = ft.TextField(
            hint_text="Tìm MSSV/Tên...", width=200, height=38,
            prefix_icon=ft.Icons.SEARCH, border_radius=8, text_size=12,
            content_padding=ft.Padding(10, 0, 10, 0), on_submit=self.load_data
        )

        self.grid = AdminDataGrid(
            columns=[
                {"label": "NGÀY", "key": "ngay", "col": {"xs": 4, "sm": 1.2}},
                {"label": "MSSV", "key": "mssv", "col": {"xs": 4, "sm": 1.2}, "sortable": True},
                {"label": "HỌ TÊN", "key": "full_name", "col": {"xs": 8, "sm": 2.5}, "sortable": True},
                {"label": "LỚP", "key": "tenlop", "col": {"xs": 6, "sm": 1.5}},
                {"label": "MÔN HỌC", "key": "mon_hoc", "col": {"xs": 6, "sm": 2.5}},
                {"label": "T.THÁI", "key": "trang_thai", "col": {"xs": 6, "sm": 1.2}, "render": self.render_status},
                {"label": "TIN CẬY", "key": "confidence", "col": {"xs": 6, "sm": 0.9}},
            ],
            rows_per_page=30
        )

        self.content = ft.Column([
            ft.Row([self.title_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Row([self.stat_present, self.stat_absent, self.stat_late], spacing=15),
            ft.Container(height=15),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        self.search_field,
                        self.class_filter,
                        self.subject_filter,
                        self.status_filter,
                        ft.VerticalDivider(width=1, color=current_theme.divider_color),
                        ft.IconButton(ft.Icons.REFRESH_ROUNDED, on_click=self.refresh_data),
                        ft.IconButton(ft.Icons.FILE_DOWNLOAD_OUTLINED, tooltip="Xuất Excel", on_click=self.export_data)
                    ], spacing=10, wrap=True),
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
        st = item.get("trang_thai", "Vắng")
        color = ft.Colors.GREEN if st == "Có mặt" else (ft.Colors.ORANGE if st == "Đi trễ" else ft.Colors.RED)
        return ft.Container(
            padding=ft.Padding(8, 4, 8, 4), border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.1, color),
            content=ft.Text(st.upper(), size=9, weight=ft.FontWeight.BOLD, color=color)
        )

    def did_mount(self):
        self.app_page.run_task(self.initialize_page)

    async def initialize_page(self):
        await self.load_filters()
        await self.load_stats()
        await self.load_data()

    async def load_filters(self):
        try:
            self.classes_list = await self.svc.get_classes()
            self.class_filter.options = [ft.dropdown.Option("all", "Tất cả lớp")]
            for c in self.classes_list:
                self.class_filter.options.append(ft.dropdown.Option(str(c["id"]), c["tenlop"]))
            
            # Sửa lỗi 307: Dùng get_subjects() thay vì gọi URL trực tiếp
            self.subjects_list = await self.svc.get_subjects()
            self.subject_filter.options = [ft.dropdown.Option("all", "Tất cả môn")]
            for s in self.subjects_list:
                self.subject_filter.options.append(ft.dropdown.Option(str(s["id"]), s["tenhocphan"]))
            
            self.update()
        except Exception as e:
            print(f"Lỗi load filters: {e}")

    async def load_stats(self):
        try:
            stats = await self.svc.get("/api/admin/attendance/summary")
            self.stat_present.content.controls[1].controls[1].value = str(stats.get("present", 0))
            self.stat_absent.content.controls[1].controls[1].value = str(stats.get("absent", 0))
            self.stat_late.content.controls[1].controls[1].value = str(stats.get("late", 0))
            self.update()
        except: pass

    async def refresh_data(self, e):
        await self.initialize_page()

    async def load_data(self, e=None):
        try:
            # Sửa lỗi 422: Loại bỏ các giá trị rỗng hoặc "all" trước khi gửi
            params = {}
            if self.class_filter.value and self.class_filter.value != "all":
                params["class_id"] = self.class_filter.value
            
            if self.subject_filter.value and self.subject_filter.value != "all":
                # Đảm bảo là số nguyên hoặc chuỗi số hợp lệ
                params["subject_id"] = self.subject_filter.value
                
            if self.status_filter.value and self.status_filter.value != "all":
                params["status"] = self.status_filter.value
                
            if self.search_field.value:
                params["search"] = self.search_field.value

            data = await self.svc.get("/api/admin/attendance/report", params=params)
            self.grid.set_data(data)
            self.update()
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", str(ex), ft.Colors.RED)

    def export_data(self, e):
        show_top_notification(self.app_page, "Thông báo", "Tính năng xuất Excel đang được chuẩn bị...", ft.Colors.BLUE)
