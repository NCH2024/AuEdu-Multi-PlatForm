"""
Trang quản lý Học Phần — Admin Panel.
Cung cấp CRUD hoàn chỉnh cho bảng Học Phần (môn học),
hiển thị bằng AdminDataGrid với tìm kiếm và phân trang.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class SubjectsPage(ft.Container):
    """Trang quản lý danh sách Học Phần dành cho Admin."""

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
            "QUẢN LÝ HỌC PHẦN", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.btn_add = ft.Button(
            "THÊM MỚI", icon=ft.Icons.BOOK_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_add_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm tên học phần...", prefix_icon=ft.Icons.SEARCH,
            height=38, expand=True, border_radius=8, text_size=13
        )
        self.search_field.on_change = self.filter_data

        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("15"), ft.dropdown.Option("30"), ft.dropdown.Option("50"), ft.dropdown.Option("100")],
            value="15", width=80, height=38,
            content_padding=ft.Padding.only(left=10, right=10, bottom=10),
            border_radius=8, text_size=13
        )
        self.page_size_dropdown.on_change = self.change_page_size

        # AdminDataGrid — bảng dữ liệu responsive
        self.grid = AdminDataGrid(
            columns=[
                {"label": "ID", "key": "id", "col": {"xs": 2, "sm": 1}, "sortable": True},
                {"label": "TÊN HỌC PHẦN", "key": "tenhocphan", "col": {"xs": 10, "sm": 4}, "sortable": True},
                {"label": "MÃ HP", "key": "mahocphan", "col": {"xs": 6, "sm": 2}},
                {"label": "SỐ TC", "key": "sotinchi", "col": {"xs": 3, "sm": 1}},
                {"label": "SỐ BUỔI", "key": "sobuoi", "col": {"xs": 3, "sm": 1}},
                {"label": "LOẠI", "key": "loai", "col": {"xs": 6, "sm": 2}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.search_field,
                    ft.VerticalDivider(width=1, color=current_theme.divider_color),
                    ft.Text("Hiển thị:", size=12, color=current_theme.text_muted),
                    self.page_size_dropdown,
                ], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Container(height=5),
                self.grid
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, expand=True, spacing=10),
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
        self.form_ten = ft.TextField(label="Tên Học Phần", border_radius=8, text_size=13, height=45)
        self.form_tinchi = ft.TextField(label="Số Tín Chỉ", border_radius=8, text_size=13, height=45)
        self.form_sobuoi = ft.TextField(label="Số Buổi Học", border_radius=8, text_size=13, height=45)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN HỌC PHẦN", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(width=400, content=ft.Column([
                self.form_id, self.form_ten, self.form_tinchi, self.form_sobuoi
            ], tight=True, spacing=12)),
            actions=[
                ft.TextButton("HỦY", on_click=self.close_dialog),
                ft.Button("LƯU", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)
            ],
            shape=ft.RoundedRectangleBorder(radius=12)
        )

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Kích hoạt tải dữ liệu khi trang được mount."""
        self.app_page.run_task(self.load_data)

    async def load_data(self):
        """Tải danh sách Học Phần từ AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            self.all_data = await self.svc.get_subjects(force=True)
            self.filter_data(None)
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách học phần: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Filter & Table ───────────────────────────────────────────

    def filter_data(self, e):
        """Lọc danh sách theo từ khóa tìm kiếm."""
        q = self.search_field.value.lower() if self.search_field.value else ""
        self.filtered_data = [
            i for i in self.all_data
            if q in str(i.get("tenhocphan", "")).lower()
        ]
        self.render_table()

    def change_page_size(self, e):
        """Thay đổi số lượng dòng hiển thị trên mỗi trang."""
        if self.page_size_dropdown.value:
            self.grid.update_page_size(int(self.page_size_dropdown.value))

    def render_actions(self, item):
        """Render cột thao tác (Sửa/Xóa) cho mỗi hàng."""
        return ft.Row([
            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_size=16, on_click=lambda e, d=item: self.open_edit_dialog(d)),
            ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_size=16, on_click=lambda e, d=item: self.delete_data(d))
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

    def render_table(self):
        """Cập nhật dữ liệu cho AdminDataGrid."""
        self.grid.set_data(self.filtered_data)
        self.update()

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_ten.error_text = None
        self.form_tinchi.error_text = None
        self.form_sobuoi.error_text = None

    def open_add_dialog(self, e):
        """Mở dialog thêm Học Phần mới."""
        self.is_edit = False
        self.form_id.value = "Tự động"
        self.form_ten.value = ""
        self.form_tinchi.value = "3"
        self.form_sobuoi.value = "15"
        self._clear_errors()
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        """Mở dialog chỉnh sửa Học Phần đã chọn."""
        self.is_edit = True
        self.form_id.value = str(data["id"])
        self.form_ten.value = data["tenhocphan"]
        self.form_tinchi.value = str(data.get("sotinchi", ""))
        self.form_sobuoi.value = str(data.get("sobuoi", ""))
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
            self.form_ten.error_text = "Vui lòng nhập tên học phần"
            has_error = True
        else:
            self.form_ten.error_text = None

        if not self.form_tinchi.value or not self.form_tinchi.value.isdigit():
            self.form_tinchi.error_text = "Số tín chỉ phải là số"
            has_error = True
        else:
            self.form_tinchi.error_text = None

        if not self.form_sobuoi.value or not self.form_sobuoi.value.isdigit():
            self.form_sobuoi.error_text = "Số buổi học phải là số"
            has_error = True
        else:
            self.form_sobuoi.error_text = None

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Học Phần qua AdminService."""
        try:
            payload = {
                "tenhocphan": self.form_ten.value,
                "sotinchi": int(self.form_tinchi.value),
                "sobuoi": int(self.form_sobuoi.value)
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/subjects/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/subjects/", payload)

            self.svc.invalidate("subjects")
            self.close_dialog()
            show_top_notification(self.app_page, "Thông báo", "Lưu thông tin học phần thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"{e}", ft.Colors.RED, sound="E")

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Học Phần."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Xóa học phần {data['tenhocphan']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Học Phần qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/subjects/{id}")
            self.svc.invalidate("subjects")
            show_top_notification(self.app_page, "Thông báo", "Đã xóa học phần thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"{e}", ft.Colors.RED, sound="E")

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
