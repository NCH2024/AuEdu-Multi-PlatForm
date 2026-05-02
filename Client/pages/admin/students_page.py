"""
Trang quản lý Sinh Viên — Admin Panel.
Cung cấp CRUD hoàn chỉnh, tìm kiếm theo tên/MSSV/email,
lọc theo Lớp và Khóa, phân trang qua AdminDataGrid.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class StudentsPage(ft.Container):
    """Trang quản lý danh sách Sinh Viên dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.alignment = ft.Alignment(-1, -1)

        # -- State --
        self.all_data: list = []
        self.filtered_data: list = []
        self.classes_list: list = []
        self.current_page: int = 1
        self.page_size: int = 10
        self.is_edit: bool = False
        self.svc = AdminService.instance()

        # -- UI Elements --
        self.title_text = ft.Text(
            "QUẢN LÝ SINH VIÊN", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.btn_add = ft.Button(
            "THÊM MỚI", icon=ft.Icons.PERSON_ADD_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_add_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm kiếm sinh viên...",
            width=250, height=38, border_radius=8,
            content_padding=ft.Padding.only(left=10, right=10), text_size=13
        )
        self.search_field.on_change = self.filter_data

        self.class_filter = ft.Dropdown(
            label="Lớp", width=180, height=38,
            options=[ft.dropdown.Option("all", "Tất cả lớp")], value="all",
            content_padding=ft.Padding.only(left=10, right=10, bottom=10),
            border_radius=8, text_size=13
        )
        self.class_filter.on_change = self.filter_data

        self.course_filter = ft.Dropdown(
            label="Khóa", width=100, height=38,
            options=[ft.dropdown.Option("all", "Tất cả")], value="all",
            content_padding=ft.Padding.only(left=10, right=10, bottom=10),
            border_radius=8, text_size=13
        )
        self.course_filter.on_change = self.filter_data

        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50")],
            value="10", width=70, height=38,
            content_padding=ft.Padding.only(left=10, right=10, bottom=10),
            border_radius=8, text_size=13
        )
        self.page_size_dropdown.on_change = self.change_page_size

        # AdminDataGrid — bảng dữ liệu responsive
        self.grid = AdminDataGrid(
            columns=[
                {"label": "MSSV", "key": "student_id", "col": {"xs": 12, "sm": 2}, "sortable": True},
                {"label": "HỌ TÊN", "key": "full_name", "col": {"xs": 12, "sm": 4}, "sortable": True},
                {"label": "LỚP", "key": "tenlop", "col": {"xs": 6, "sm": 2}, "sortable": True},
                {"label": "GIỚI TÍNH", "key": "gioitinh", "col": {"xs": 6, "sm": 1}},
                {"label": "EMAIL", "key": "email", "col": {"xs": 12, "sm": 2}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.search_field,
                    self.class_filter,
                    self.course_filter,
                ], alignment=ft.MainAxisAlignment.START, spacing=8),
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

        # -- Form Dialog Fields (KHÔNG có form_full_name — tự ghép từ hodem+ten) --
        self.form_id = ft.TextField(label="ID (Hệ thống)", disabled=True, border_radius=8, text_size=13, height=45)
        self.form_student_id = ft.TextField(label="Mã số sinh viên (MSSV)", border_radius=8, expand=True, text_size=13, height=45)
        self.form_ho = ft.TextField(label="Họ đệm", border_radius=8, expand=True, text_size=13, height=45)
        self.form_ten = ft.TextField(label="Tên", border_radius=8, expand=True, text_size=13, height=45)
        self.form_email = ft.TextField(label="Email", border_radius=8, text_size=13, height=45)
        self.form_lop = ft.Dropdown(label="Lớp", options=[], border_radius=8, text_size=13, height=45)
        self.form_gioitinh = ft.Dropdown(
            label="Giới tính",
            options=[ft.dropdown.Option("Nam"), ft.dropdown.Option("Nữ")],
            border_radius=8, text_size=13, height=45
        )
        self.form_diachi = ft.TextField(label="Địa chỉ", border_radius=8, multiline=True, min_lines=2, text_size=13)
        self.form_ngaysinh = ft.TextField(label="Ngày sinh (YYYY-MM-DD)", border_radius=8, text_size=13, height=45)
        self.form_ghichu = ft.TextField(label="Ghi chú", border_radius=8, multiline=True, min_lines=2, text_size=13)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN SINH VIÊN", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(
                width=550,
                content=ft.Column([
                    ft.Row([self.form_student_id, self.form_gioitinh]),
                    ft.Row([self.form_ho, self.form_ten]),
                    self.form_email,
                    ft.Row([self.form_lop, self.form_ngaysinh]),
                    self.form_diachi,
                    self.form_ghichu
                ], tight=True, scroll=ft.ScrollMode.AUTO, spacing=12)
            ),
            actions=[
                ft.TextButton("HỦY", on_click=self.close_dialog),
                ft.Button("LƯU", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)
            ],
            shape=ft.RoundedRectangleBorder(radius=12)
        )

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Kích hoạt tải dữ liệu khi trang được mount."""
        self.app_page.run_task(self.initialize_data)

    async def initialize_data(self):
        """Tải song song danh sách lớp và sinh viên."""
        self.progress_bar.visible = True
        self.update()
        try:
            await self.load_classes()
            await self.load_data()
        finally:
            self.progress_bar.visible = False
            self.update()

    async def load_classes(self):
        """Tải danh sách lớp phục vụ bộ lọc và form nhập liệu."""
        try:
            self.classes_list = await self.svc.get_classes()
            self.class_filter.options = [ft.dropdown.Option("all", "Tất cả lớp")]
            self.form_lop.options = []
            courses = set()
            for c in self.classes_list:
                self.class_filter.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
                self.form_lop.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
                if c.get("khoahoc"):
                    courses.add(str(c["khoahoc"]))
            self.course_filter.options = [ft.dropdown.Option("all", "Tất cả")]
            for crs in sorted(list(courses)):
                self.course_filter.options.append(ft.dropdown.Option(crs, f"K{crs}"))
            self.update()
        except Exception as e:
            print(f"[StudentsPage] Lỗi load classes: {e}")

    async def load_data(self):
        """Tải danh sách sinh viên từ AdminService (không cache)."""
        try:
            self.all_data = await self.svc.get_students()
            self.filter_data(None)
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    # ─── Filter & Table ───────────────────────────────────────────

    def filter_data(self, e):
        """Lọc danh sách theo từ khóa, lớp và khóa học."""
        query = self.search_field.value.lower() if self.search_field.value else ""
        c_id = str(self.class_filter.value) if self.class_filter.value else "all"
        course = str(self.course_filter.value) if self.course_filter.value else "all"

        self.filtered_data = []
        for item in self.all_data:
            # Tìm kiếm theo MSSV, tên, họ, email
            mssv = str(item.get("student_id") or item.get("id") or "").lower()
            match_search = (
                query in mssv or
                query in str(item.get("ten", "")).lower() or
                query in str(item.get("hodem", "")).lower() or
                query in str(item.get("email", "")).lower()
            )

            # Lọc theo lớp
            item_class_id = str(item.get("class_id")) if item.get("class_id") else None
            match_class = (c_id == "all" or item_class_id == c_id)

            # Lọc theo khóa
            match_course = True
            if course != "all":
                class_info = next((c for c in self.classes_list if str(c["id"]) == item_class_id), None)
                match_course = str(class_info.get("khoahoc")) == course if class_info else False

            if match_search and match_class and match_course:
                self.filtered_data.append(item)

        self.current_page = 1
        self.render_table()

    def change_page_size(self, e):
        """Thay đổi số dòng mỗi trang."""
        self.grid.update_page_size(int(self.page_size_dropdown.value))

    def render_actions(self, item):
        """Render cột thao tác (Sửa/Xóa) cho mỗi hàng."""
        return ft.Row([
            ft.IconButton(icon=ft.Icons.EDIT_ROUNDED, icon_size=16, icon_color=ft.Colors.BLUE_400,
                          on_click=lambda e, d=item: self.open_edit_dialog(d)),
            ft.IconButton(icon=ft.Icons.DELETE_ROUNDED, icon_size=16, icon_color=ft.Colors.RED_400,
                          on_click=lambda e, d=item: self.delete_data(d))
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

    def render_table(self):
        """Chuyển đổi dữ liệu và đưa vào AdminDataGrid."""
        display_data = []
        for item in self.filtered_data:
            d = item.copy()
            d["tenlop"] = next(
                (c["tenlop"] for c in self.classes_list if str(c["id"]) == str(item.get("class_id"))),
                "N/A"
            )
            d["student_id"] = item.get("student_id") or str(item.get("id", "N/A"))
            # Auto-gen full_name từ họ đệm + tên (không dùng trường riêng)
            d["full_name"] = f"{item.get('hodem', '')} {item.get('ten', '')}".strip()
            display_data.append(d)

        # Mặc định sắp xếp theo Tên (A-Z) nếu chưa có sort key
        if not self.grid.sort_key:
            display_data.sort(key=lambda x: x.get("ten", "").lower())

        self.grid.set_data(display_data)
        self.update()

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_student_id.error_text = None
        self.form_ho.error_text = None
        self.form_ten.error_text = None

    def _clear_form(self):
        """Reset toàn bộ giá trị form về mặc định."""
        self.form_student_id.value = ""
        self.form_ho.value = ""
        self.form_ten.value = ""
        self.form_email.value = ""
        self.form_lop.value = None
        self.form_gioitinh.value = "Nam"
        self.form_diachi.value = ""
        self.form_ngaysinh.value = ""
        self.form_ghichu.value = ""

    def open_add_dialog(self, e):
        """Mở dialog thêm Sinh Viên mới."""
        self.is_edit = False
        self._clear_form()
        self._clear_errors()
        self.form_id.value = ""
        self.form_student_id.disabled = False
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        """Mở dialog chỉnh sửa Sinh Viên đã chọn."""
        self.is_edit = True
        self._clear_errors()
        self.form_id.value = str(data.get("id", ""))
        self.form_student_id.value = data.get("student_id", "")
        self.form_student_id.disabled = True
        self.form_ho.value = data.get("hodem", "")
        self.form_ten.value = data.get("ten", "")
        self.form_email.value = data.get("email", "")
        self.form_lop.value = data.get("class_id")
        self.form_gioitinh.value = data.get("gioitinh", "Nam")
        self.form_diachi.value = data.get("diachi", "")
        self.form_ngaysinh.value = data.get("ngaysinh", "")
        self.form_ghichu.value = data.get("ghichu", "")
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
        if not self.form_student_id.value or not self.form_student_id.value.strip():
            self.form_student_id.error_text = "Vui lòng nhập MSSV"
            has_error = True
        else:
            self.form_student_id.error_text = None

        if not self.form_ho.value or not self.form_ho.value.strip():
            self.form_ho.error_text = "Vui lòng nhập họ đệm"
            has_error = True
        else:
            self.form_ho.error_text = None

        if not self.form_ten.value or not self.form_ten.value.strip():
            self.form_ten.error_text = "Vui lòng nhập tên"
            has_error = True
        else:
            self.form_ten.error_text = None

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Sinh Viên qua AdminService."""
        try:
            payload = {
                "student_id": self.form_student_id.value,
                "hodem": self.form_ho.value,
                "ten": self.form_ten.value,
                # full_name tự ghép từ hodem + ten, không cần trường riêng
                "full_name": f"{self.form_ho.value} {self.form_ten.value}".strip(),
                "email": self.form_email.value or None,
                "class_id": self.form_lop.value,
                "gioitinh": self.form_gioitinh.value,
                "diachi": self.form_diachi.value or None,
                "ngaysinh": self.form_ngaysinh.value if self.form_ngaysinh.value else None,
                "ghichu": self.form_ghichu.value or None
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/system/sinhvien/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/system/sinhvien/", payload)

            self.close_dialog()
            show_top_notification(self.app_page, "Thành công!", ft.Colors.GREEN)
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Sinh Viên."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN XÓA", f"Xóa sinh viên {data['ten']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Sinh Viên qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/system/sinhvien/{id}")
            show_top_notification(self.app_page, "Đã xóa sinh viên!", ft.Colors.GREEN)
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi xóa dữ liệu: {e}", ft.Colors.RED)

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
