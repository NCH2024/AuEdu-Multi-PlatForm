"""
Trang quản lý Khoa — Admin Panel.
Cung cấp CRUD hoàn chỉnh (Thêm/Sửa/Xóa) cho bảng Khoa,
hiển thị bằng AdminDataGrid với tìm kiếm và phân trang.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class DepartmentsPage(ft.Container):
    """Trang quản lý danh sách Khoa dành cho Admin."""

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
            "QUẢN LÝ KHOA", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.btn_add = ft.Button(
            "THÊM MỚI", icon=ft.Icons.ADD_HOME_WORK_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_add_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm mã hoặc tên khoa...", prefix_icon=ft.Icons.SEARCH,
            height=38, expand=True, border_radius=8, text_size=13
        )
        self.search_field.on_change = self.filter_data

        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50")],
            value="10", width=70, height=38, border_radius=8,
            content_padding=ft.Padding.only(left=10, right=10, bottom=10), text_size=13
        )
        self.page_size_dropdown.on_change = self.change_page_size

        # AdminDataGrid — bảng dữ liệu responsive
        self.grid = AdminDataGrid(
            columns=[
                {"label": "MÃ KHOA", "key": "id", "col": {"xs": 4, "sm": 2}, "sortable": True},
                {"label": "TÊN KHOA", "key": "tenkhoa", "col": {"xs": 8, "sm": 5}, "sortable": True},
                {"label": "EMAIL", "key": "email", "col": {"xs": 12, "sm": 4}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field], alignment=ft.MainAxisAlignment.START, spacing=8),
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
        self.form_id = ft.TextField(label="Mã Khoa (ID)", border_radius=8, text_size=13, height=45)
        self.form_ten = ft.TextField(label="Tên Khoa", border_radius=8, text_size=13, height=45)
        self.form_email = ft.TextField(label="Email", border_radius=8, text_size=13, height=45)
        self.form_description = ft.TextField(label="Mô tả", border_radius=8, multiline=True, min_lines=3, text_size=13)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN KHOA", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(width=450, content=ft.Column([
                self.form_id, self.form_ten, self.form_email, self.form_description
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
        """Tải danh sách Khoa từ AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            self.all_data = await self.svc.get_departments(force=True)
            self.filter_data(None)
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách Khoa: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Filter & Table ───────────────────────────────────────────

    def filter_data(self, e):
        """Lọc danh sách theo từ khóa tìm kiếm."""
        q = self.search_field.value.lower() if self.search_field.value else ""
        self.filtered_data = [
            i for i in self.all_data
            if q in str(i.get("id", "")).lower() or q in str(i.get("tenkhoa", "")).lower()
        ]
        self.render_table()

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

    def change_page_size(self, e):
        """Thay đổi số dòng mỗi trang."""
        self.grid.update_page_size(int(self.page_size_dropdown.value))

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_id.error_text = None
        self.form_ten.error_text = None

    def open_add_dialog(self, e):
        """Mở dialog thêm Khoa mới."""
        self.is_edit = False
        self.form_id.value = ""
        self.form_id.disabled = False
        self.form_ten.value = ""
        self.form_email.value = ""
        self.form_description.value = ""
        self._clear_errors()
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        """Mở dialog chỉnh sửa Khoa đã chọn."""
        self.is_edit = True
        self.form_id.value = str(data["id"])
        self.form_id.disabled = True
        self.form_ten.value = data["tenkhoa"]
        self.form_email.value = data.get("email", "")
        self.form_description.value = data.get("description", "")
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
            self.form_ten.error_text = "Vui lòng nhập tên khoa"
            has_error = True
        else:
            self.form_ten.error_text = None

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Khoa qua AdminService."""
        try:
            payload = {
                "id": self.form_id.value,
                "tenkhoa": self.form_ten.value,
                "email": self.form_email.value,
                "description": self.form_description.value
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/departments/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/departments/", payload)

            self.svc.invalidate("departments")
            self.close_dialog()
            show_top_notification(self.app_page, "Thông báo", "Lưu thông tin khoa thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Khoa."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Xóa khoa {data['tenkhoa']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Khoa qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/departments/{id}")
            self.svc.invalidate("departments")
            show_top_notification(self.app_page, "Thông báo", "Đã xóa khoa thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
