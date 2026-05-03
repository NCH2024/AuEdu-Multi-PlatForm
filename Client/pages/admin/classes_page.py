"""
Trang quản lý Lớp Học — Admin Panel.
Cung cấp CRUD hoàn chỉnh cho bảng Lớp, tích hợp bộ lọc Khoa,
Học kỳ, phân trang qua AdminDataGrid.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class ClassesPage(ft.Container):
    """Trang quản lý danh sách Lớp Học dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.alignment = ft.Alignment(-1, -1)

        # -- State --
        self.all_data: list = []
        self.filtered_data: list = []
        self.depts_list: list = []
        self.semesters_list: list = []
        self.is_edit: bool = False
        self.svc = AdminService.instance()

        # -- UI Elements --
        self.title_text = ft.Text(
            "QUẢN LÝ LỚP HỌC", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.btn_add = ft.Button(
            "THÊM MỚI", icon=ft.Icons.ADD_BUSINESS_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_add_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm mã hoặc tên lớp...", prefix_icon=ft.Icons.SEARCH,
            height=38, expand=True, border_radius=8, text_size=13
        )
        self.search_field.on_change = self.filter_data

        self.dept_filter = ft.Dropdown(
            label="Khoa", width=180, height=38,
            options=[ft.dropdown.Option("all", "Tất cả khoa")], value="all",
            border_radius=8, content_padding=ft.Padding.only(left=10, right=10, bottom=10), text_size=13
        )
        self.dept_filter.on_change = self.filter_data

        self.semester_filter = ft.Dropdown(
            label="Học kỳ", width=150, height=38,
            options=[ft.dropdown.Option("all", "Tất cả")], value="all",
            border_radius=8, content_padding=ft.Padding.only(left=10, right=10, bottom=10), text_size=13
        )
        self.semester_filter.on_change = self.filter_data

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
                {"label": "MÃ LỚP", "key": "id", "col": {"xs": 4, "sm": 2}, "sortable": True},
                {"label": "TÊN LỚP", "key": "tenlop", "col": {"xs": 8, "sm": 4}, "sortable": True},
                {"label": "KHOA", "key": "tenkhoa", "col": {"xs": 6, "sm": 3}},
                {"label": "KHÓA", "key": "khoahoc", "col": {"xs": 3, "sm": 1}},
                {"label": "NĂM HỌC", "key": "namhoc", "col": {"xs": 3, "sm": 1}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.search_field, 
                    self.dept_filter, 
                    self.semester_filter,
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
            ft.Row([
                self.title_text, 
                ft.Row([
                    ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="Làm mới dữ liệu", on_click=self.refresh_all_data),
                    self.btn_add
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.progress_bar,
            ft.Container(height=5),
            self.table_container
        ], expand=True, spacing=0)

        # -- Form Dialog --
        self.form_id = ft.TextField(label="Mã Lớp (ID)", border_radius=8, text_size=13, height=45)
        self.form_ten = ft.TextField(label="Tên Lớp", border_radius=8, text_size=13, height=45)
        self.form_dept = ft.Dropdown(label="Khoa", options=[], border_radius=8, text_size=13, height=45)
        self.form_semester = ft.Dropdown(label="Học kỳ", options=[], border_radius=8, text_size=13, height=45)
        self.form_nambd = ft.TextField(label="Năm BĐ", border_radius=8, expand=True, text_size=13, height=45)
        self.form_namkt = ft.TextField(label="Năm KT", border_radius=8, expand=True, text_size=13, height=45)
        self.form_khoahoc = ft.TextField(label="Khóa", border_radius=8, text_size=13, height=45)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN LỚP HỌC", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(
                width=450,
                content=ft.Column([
                    self.form_id, self.form_ten, self.form_dept, self.form_semester,
                    ft.Row([self.form_nambd, self.form_namkt]),
                    self.form_khoahoc
                ], tight=True, spacing=12, scroll=ft.ScrollMode.AUTO)
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
        """Tải song song danh sách Khoa, Học kỳ và Lớp."""
        self.progress_bar.visible = True
        self.update()
        try:
            await self.load_depts()
            await self.load_semesters()
            await self.load_data()
        finally:
            self.progress_bar.visible = False
            self.update()

    async def refresh_all_data(self, e):
        """Xóa cache và tải lại toàn bộ danh mục."""
        self.svc.invalidate("classes")
        self.svc.invalidate("departments")
        self.svc.invalidate("semesters")
        await self.initialize_data()
        show_top_notification(self.app_page, "Thông tin", "Đã làm mới danh mục thành công!", ft.Colors.BLUE, sound="S")

    def change_page_size(self, e):
        """Thay đổi số lượng dòng hiển thị trên mỗi trang."""
        if self.page_size_dropdown.value:
            self.grid.update_page_size(int(self.page_size_dropdown.value))

    async def load_depts(self):
        """Tải danh sách Khoa từ AdminService, cập nhật bộ lọc và form."""
        try:
            self.depts_list = await self.svc.get_departments()
            self.dept_filter.options = [ft.dropdown.Option("all", "Tất cả")]
            self.form_dept.options = []
            for d in self.depts_list:
                self.dept_filter.options.append(ft.dropdown.Option(d["id"], d["tenkhoa"]))
                self.form_dept.options.append(ft.dropdown.Option(d["id"], d["tenkhoa"]))
            self.update()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách Khoa: {e}", ft.Colors.RED, sound="E")

    async def load_semesters(self):
        """Tải danh sách Học kỳ từ AdminService, cập nhật bộ lọc và form."""
        try:
            self.semesters_list = await self.svc.get_semesters()
            self.semester_filter.options = [ft.dropdown.Option("all", "Tất cả")]
            self.form_semester.options = []
            for s in self.semesters_list:
                label = f"{s['tenhocky']} ({s['namhoc']})"
                self.semester_filter.options.append(ft.dropdown.Option(str(s["id"]), label))
                self.form_semester.options.append(ft.dropdown.Option(str(s["id"]), label))
            self.update()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách Học kỳ: {e}", ft.Colors.RED, sound="E")

    async def load_data(self):
        """Tải danh sách Lớp từ AdminService."""
        try:
            self.all_data = await self.svc.get_classes(force=True)
            self.filter_data(None)
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách Lớp: {e}", ft.Colors.RED, sound="E")

    # ─── Filter & Table ───────────────────────────────────────────

    def filter_data(self, e):
        """Lọc danh sách theo từ khóa, Khoa và Học kỳ."""
        query = self.search_field.value.lower() if self.search_field.value else ""
        dept_id = str(self.dept_filter.value) if self.dept_filter.value else "all"
        sem_id = str(self.semester_filter.value) if self.semester_filter.value else "all"
        self.filtered_data = [
            i for i in self.all_data
            if (query in str(i.get("id", "")).lower() or query in str(i.get("tenlop", "")).lower()) and
               (dept_id == "all" or str(i.get("khoa_id")) == dept_id) and
               (sem_id == "all" or str(i.get("semester_id")) == sem_id)
        ]
        self.render_table()

    def render_actions(self, item):
        """Render cột thao tác (Sửa/Xóa) cho mỗi hàng."""
        return ft.Row([
            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_size=16, on_click=lambda e, d=item: self.open_edit_dialog(d)),
            ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_size=16, on_click=lambda e, d=item: self.delete_data(d))
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

    def render_table(self):
        """Chuyển đổi dữ liệu và đưa vào AdminDataGrid."""
        display_data = []
        for i in self.filtered_data:
            d = i.copy()
            # Tra tên khoa từ khoa_id (đúng field name của server)
            d["tenkhoa"] = next(
                (dept["tenkhoa"] for dept in self.depts_list if dept["id"] == i.get("khoa_id")),
                "N/A"
            )
            d["namhoc"] = f"{i.get('nambd', '?')}-{i.get('namkt', '?')}"
            display_data.append(d)

        self.grid.set_data(display_data)
        self.update()

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_ten.error_text = None
        self.form_dept.error_text = None
        self.form_semester.error_text = None

    def open_add_dialog(self, e):
        """Mở dialog thêm Lớp mới."""
        self.is_edit = False
        self.form_id.value = ""
        self.form_id.disabled = False
        self.form_ten.value = ""
        self.form_nambd.value = ""
        self.form_namkt.value = ""
        self.form_khoahoc.value = ""
        self.form_dept.value = None
        self.form_semester.value = None
        self._clear_errors()
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        """Mở dialog chỉnh sửa Lớp đã chọn."""
        self.is_edit = True
        self.form_id.value = str(data["id"])
        self.form_id.disabled = True
        self.form_ten.value = data["tenlop"]
        # Dùng khoa_id (đúng field name trên server)
        self.form_dept.value = data.get("khoa_id")
        self.form_semester.value = str(data.get("semester_id")) if data.get("semester_id") else None
        self.form_nambd.value = str(data.get("nambd", "")) if data.get("nambd") is not None else ""
        self.form_namkt.value = str(data.get("namkt", "")) if data.get("namkt") is not None else ""
        self.form_khoahoc.value = str(data.get("khoahoc", "")) if data.get("khoahoc") is not None else ""
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
            self.form_ten.error_text = "Vui lòng nhập tên lớp"
            has_error = True
        else:
            self.form_ten.error_text = None

        if not self.form_dept.value:
            self.form_dept.error_text = "Vui lòng chọn Khoa"
            has_error = True
        else:
            self.form_dept.error_text = None

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Lớp qua AdminService."""
        try:
            nambd_val = int(self.form_nambd.value) if self.form_nambd.value and self.form_nambd.value.isdigit() else None
            namkt_val = int(self.form_namkt.value) if self.form_namkt.value and self.form_namkt.value.isdigit() else None
            khoahoc_val = int(self.form_khoahoc.value) if self.form_khoahoc.value and self.form_khoahoc.value.isdigit() else None

            payload = {
                "id": self.form_id.value,
                "tenlop": self.form_ten.value,
                # Dùng khoa_id — khớp với model server
                "khoa_id": self.form_dept.value,
                "semester_id": int(self.form_semester.value) if self.form_semester.value and self.form_semester.value.isdigit() else None,
                "nambd": nambd_val,
                "namkt": namkt_val,
                "khoahoc": khoahoc_val
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/classes/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/classes/", payload)

            self.svc.invalidate("classes")
            self.close_dialog()
            show_top_notification(self.app_page, "Thông báo", "Lưu thông tin lớp học thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể lưu dữ liệu lớp học: {e}", ft.Colors.RED, sound="E")

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Lớp."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Xóa lớp {data['tenlop']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Lớp qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/classes/{id}")
            self.svc.invalidate("classes")
            show_top_notification(self.app_page, "Thông báo", "Đã xóa lớp học thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể xóa lớp học: {e}", ft.Colors.RED, sound="E")

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
