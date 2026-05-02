"""
Trang quản lý Học Kỳ — Admin Panel.
Cung cấp CRUD hoàn chỉnh cho bảng Học Kỳ, tích hợp DatePicker
cho ngày bắt đầu/kết thúc, và liên kết quản lý tuần học.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class SemestersPage(ft.Container):
    """Trang quản lý danh sách Học Kỳ dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.alignment = ft.Alignment(-1, -1)

        # -- State --
        self.all_data: list = []
        self.filtered_data: list = []
        self.is_edit: bool = False
        self.svc = AdminService.instance()

        # -- UI Elements --
        self.title_text = ft.Text(
            "QUẢN LÝ HỌC KỲ", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.btn_add = ft.Button(
            "THÊM MỚI", icon=ft.Icons.CALENDAR_MONTH_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_add_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm học kỳ hoặc năm học...", prefix_icon=ft.Icons.SEARCH,
            height=38, expand=True, border_radius=8, text_size=13
        )
        self.search_field.on_change = self.filter_data

        # AdminDataGrid — bảng dữ liệu responsive
        self.grid = AdminDataGrid(
            columns=[
                {"label": "ID", "key": "id", "col": {"xs": 2, "sm": 1}, "sortable": True},
                {"label": "TÊN HỌC KỲ", "key": "tenhocky", "col": {"xs": 10, "sm": 3}, "sortable": True},
                {"label": "NĂM HỌC", "key": "namhoc", "col": {"xs": 12, "sm": 2}},
                {"label": "SỐ TUẦN", "key": "so_tuan_hoc", "col": {"xs": 4, "sm": 1}},
                {"label": "BẮT ĐẦU", "key": "start_date", "col": {"xs": 6, "sm": 1.5}},
                {"label": "KẾT THÚC", "key": "end_date", "col": {"xs": 6, "sm": 1.5}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 2}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field], alignment=ft.MainAxisAlignment.START, spacing=8),
                ft.Container(height=5),
                self.grid
            ], horizontal_alignment=ft.CrossAxisAlignment.START, expand=True, spacing=10),
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=12, bgcolor=current_theme.surface_color,
            padding=ft.Padding.all(12), expand=True
        )

        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)

        self.content = ft.Column([
            ft.Row([self.title_text, self.btn_add], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.progress_bar,
            ft.Container(height=5),
            self.table_container
        ], expand=True, spacing=0)

        # -- Form Dialog --
        self.form_id = ft.TextField(label="Mã định danh", disabled=True, border_radius=8, text_size=13, height=45)
        self.form_ten = ft.TextField(label="Tên Học Kỳ", border_radius=8, text_size=13, height=45)
        self.form_nam = ft.TextField(label="Năm Học", border_radius=8, text_size=13, height=45)
        self.form_so_tuan = ft.TextField(label="Số tuần học", value="15", border_radius=8, text_size=13, height=45)

        self.start_date_picker = ft.DatePicker(on_change=self.on_start_date_changed)
        self.end_date_picker = ft.DatePicker(on_change=self.on_end_date_changed)

        self.form_start = ft.TextField(label="Bắt đầu", border_radius=8, text_size=13, height=45, expand=True, read_only=True)
        self.btn_start = ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: self.app_page.open(self.start_date_picker))
        self.row_start = ft.Row([self.form_start, self.btn_start])

        self.form_end = ft.TextField(label="Kết thúc", border_radius=8, text_size=13, height=45, expand=True, read_only=True)
        self.btn_end = ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=lambda _: self.app_page.open(self.end_date_picker))
        self.row_end = ft.Row([self.form_end, self.btn_end])

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN HỌC KỲ", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(width=450, content=ft.Column([
                self.form_id, self.form_ten, self.form_nam, self.form_so_tuan,
                self.row_start, self.row_end
            ], tight=True, spacing=12)),
            actions=[
                ft.TextButton("HỦY", on_click=self.close_dialog),
                ft.Button("LƯU", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)
            ],
            shape=ft.RoundedRectangleBorder(radius=12)
        )

    # ─── Handlers ─────────────────────────────────────────────────

    def on_start_date_changed(self, e):
        """Cập nhật TextField khi chọn ngày bắt đầu từ DatePicker."""
        if self.start_date_picker.value:
            self.form_start.value = self.start_date_picker.value.strftime("%Y-%m-%d")
            self.update()

    def on_end_date_changed(self, e):
        """Cập nhật TextField khi chọn ngày kết thúc từ DatePicker."""
        if self.end_date_picker.value:
            self.form_end.value = self.end_date_picker.value.strftime("%Y-%m-%d")
            self.update()

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Kích hoạt tải dữ liệu khi trang được mount."""
        self.app_page.run_task(self.load_data)

    async def load_data(self):
        """Tải danh sách Học Kỳ từ AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            self.all_data = await self.svc.get_semesters(force=True)
            self.filter_data(None)
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi tải dữ liệu: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Filter & Table ───────────────────────────────────────────

    def filter_data(self, e):
        """Lọc danh sách theo từ khóa tìm kiếm."""
        q = self.search_field.value.lower() if self.search_field.value else ""
        self.filtered_data = [
            i for i in self.all_data
            if q in str(i.get("tenhocky", "")).lower() or q in str(i.get("namhoc", "")).lower()
        ]
        self.render_table()

    def render_actions(self, item):
        """Render cột thao tác (Quản lý tuần/Sửa/Xóa) cho mỗi hàng."""
        return ft.Row([
            ft.IconButton(ft.Icons.LIST_ALT_ROUNDED, tooltip="Quản lý tuần",
                          icon_color=ft.Colors.GREEN_400, icon_size=16,
                          on_click=lambda e, d=item: self.app_page.run_task(
                              self.app_page.push_route, f"/admin/weeks?semester_id={d['id']}"
                          )),
            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_size=16,
                          on_click=lambda e, d=item: self.open_edit_dialog(d)),
            ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_size=16,
                          on_click=lambda e, d=item: self.delete_data(d))
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

    def render_table(self):
        """Cập nhật dữ liệu cho AdminDataGrid."""
        self.grid.set_data(self.filtered_data)
        self.update()

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_ten.error_text = None
        self.form_nam.error_text = None

    def open_add_dialog(self, e):
        """Mở dialog thêm Học Kỳ mới."""
        self.is_edit = False
        self.form_id.value = "Tự động"
        self.form_ten.value = ""
        self.form_nam.value = ""
        self.form_so_tuan.value = "15"
        self.form_start.value = ""
        self.form_end.value = ""
        self._clear_errors()
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        """Mở dialog chỉnh sửa Học Kỳ đã chọn."""
        self.is_edit = True
        self.form_id.value = str(data["id"])
        self.form_ten.value = data["tenhocky"]
        self.form_nam.value = data["namhoc"]
        self.form_so_tuan.value = str(data.get("so_tuan_hoc", 15))
        self.form_start.value = data.get("start_date", "")
        self.form_end.value = data.get("end_date", "")
        self._clear_errors()
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def close_dialog(self, e=None):
        """Đóng dialog form."""
        self.dialog.open = False
        self.app_page.update()

    def save_data(self, e):
        """Validate form và gọi lưu dữ liệu."""
        has_error = False
        if not self.form_ten.value or not self.form_ten.value.strip():
            self.form_ten.error_text = "Vui lòng nhập tên học kỳ"
            has_error = True
        else:
            self.form_ten.error_text = None

        if not self.form_nam.value or not self.form_nam.value.strip():
            self.form_nam.error_text = "Vui lòng nhập năm học"
            has_error = True
        else:
            self.form_nam.error_text = None

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Học Kỳ qua AdminService."""
        try:
            payload = {
                "tenhocky": self.form_ten.value,
                "namhoc": self.form_nam.value,
                "so_tuan_hoc": int(self.form_so_tuan.value) if self.form_so_tuan.value.isdigit() else 15,
                "start_date": self.form_start.value,
                "end_date": self.form_end.value
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/semesters/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/semesters/", payload)

            self.svc.invalidate("semesters")
            self.close_dialog()
            show_top_notification(self.app_page, "Lưu dữ liệu thành công!", ft.Colors.GREEN)
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Học Kỳ."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Xóa học kỳ {data['tenhocky']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Học Kỳ qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/semesters/{id}")
            self.svc.invalidate("semesters")
            show_top_notification(self.app_page, "Đã xóa học kỳ thành công!", ft.Colors.GREEN)
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
