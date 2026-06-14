"""
Trang quản lý Sinh Viên — Admin Panel.
Cung cấp CRUD hoàn chỉnh, tìm kiếm theo tên/MSSV/email,
lọc theo Lớp và Khóa, phân trang qua AdminDataGrid.
"""

import flet as ft
import asyncio
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
        self.class_by_id: dict = {}
        self._filter_seq: int = 0
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
        self.btn_batch_add = ft.Button(
            "BỔ SUNG NHANH", icon=ft.Icons.GROUP_ADD_ROUNDED,
            bgcolor=ft.Colors.BLUE_400, color=ft.Colors.WHITE,
            on_click=self.open_batch_dialog,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10))
        )

        self.search_field = ft.TextField(
            hint_text="Tìm kiếm sinh viên...",
            width=250, height=38, border_radius=8,
            content_padding=ft.Padding.only(left=10, right=10), text_size=13
        )
        self.search_field.on_change = self.debounce_filter_data

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
            options=[ft.dropdown.Option("15"), ft.dropdown.Option("30"), ft.dropdown.Option("50"), ft.dropdown.Option("100")],
            value="30", width=80, height=38,
            content_padding=ft.Padding.only(left=10, right=10, bottom=10),
            border_radius=8, text_size=13
        )
        self.page_size_dropdown.on_change = self.change_page_size

        # AdminDataGrid — bảng dữ liệu responsive
        self.grid = AdminDataGrid(
            columns=[
                {"label": "MSSV", "key": "student_id", "col": {"xs": 12, "sm": 1}, "sortable": True},
                {"label": "MÃ H.SƠ", "key": "ma_ho_so", "col": {"xs": 12, "sm": 1}},
                {"label": "HỌ TÊN", "key": "full_name", "col": {"xs": 12, "sm": 2.2}, "sortable": True},
                {"label": "LỚP", "key": "tenlop", "col": {"xs": 6, "sm": 1.2}, "sortable": True},
                {"label": "G.TÍNH", "key": "gioitinh", "col": {"xs": 6, "sm": 0.8}},
                {"label": "NGÀY SINH", "key": "ngaysinh", "col": {"xs": 6, "sm": 1.2}},
                {"label": "QUÊ QUÁN", "key": "nguyen_quan", "col": {"xs": 6, "sm": 1.5}},
                {"label": "DÂN TỘC", "key": "dan_toc", "col": {"xs": 6, "sm": 0.8}},
                {"label": "SĐT", "key": "dien_thoai", "col": {"xs": 6, "sm": 1.2}},
                {"label": "T.THÁI", "key": "trang_thai", "col": {"xs": 6, "sm": 1.1}},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=22
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.search_field,
                    self.class_filter,
                    self.course_filter,
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
                    self.btn_batch_add,
                    self.btn_add
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.progress_bar,
            ft.Container(height=5),
            self.table_container
        ], expand=True, spacing=0)

        # -- Form Dialog Fields (KHÔNG có form_full_name — tự ghép từ hodem+ten) --
        self.form_id = ft.TextField(label="ID (Hệ thống)", disabled=True, border_radius=8, text_size=13, height=45)
        self.form_student_id = ft.TextField(label="MSSV (Mã HS-SV)", border_radius=8, expand=True, text_size=13, height=45)
        self.form_ma_ho_so = ft.TextField(label="Mã hồ sơ", border_radius=8, expand=True, text_size=13, height=45)
        self.form_ho = ft.TextField(label="Họ đệm", border_radius=8, expand=True, text_size=13, height=45)
        self.form_ten = ft.TextField(label="Tên", border_radius=8, expand=True, text_size=13, height=45)
        self.form_email = ft.TextField(label="Email", border_radius=8, text_size=13, height=45)
        self.form_lop = ft.Dropdown(label="Lớp", options=[], border_radius=8, text_size=13, height=45)
        self.form_gioitinh = ft.Dropdown(
            label="Giới tính",
            options=[ft.dropdown.Option("Nam"), ft.dropdown.Option("Nữ")],
            border_radius=8, text_size=13, height=45
        )
        self.form_ngaysinh = ft.TextField(label="Ngày sinh (YYYY-MM-DD)", border_radius=8, text_size=13, height=45)
        self.form_noi_sinh = ft.TextField(label="Nơi sinh", border_radius=8, text_size=13, height=45)
        self.form_dan_toc = ft.TextField(label="Dân tộc", border_radius=8, text_size=13, height=45)
        self.form_ton_giao = ft.TextField(label="Tôn giáo", border_radius=8, text_size=13, height=45)
        self.form_nguyen_quan = ft.TextField(label="Nguyên quán", border_radius=8, text_size=13, height=45)
        self.form_ho_khau = ft.TextField(label="Hộ khẩu thường trú", border_radius=8, text_size=13, height=45)
        self.form_ngay_vao_doan = ft.TextField(label="Ngày vào Đoàn (YYYY-MM-DD)", border_radius=8, text_size=13, height=45)
        self.form_bac_dao_tao = ft.TextField(label="Bậc đào tạo", border_radius=8, text_size=13, height=45)
        self.form_ho_ten_cha = ft.TextField(label="Họ tên cha", border_radius=8, text_size=13, height=45)
        self.form_nghe_nghiep_cha = ft.TextField(label="Nghề nghiệp cha", border_radius=8, text_size=13, height=45)
        self.form_ho_ten_me = ft.TextField(label="Họ tên mẹ", border_radius=8, text_size=13, height=45)
        self.form_nghe_nghiep_me = ft.TextField(label="Nghề nghiệp mẹ", border_radius=8, text_size=13, height=45)
        self.form_dien_thoai = ft.TextField(label="Điện thoại", border_radius=8, text_size=13, height=45)
        self.form_trang_thai = ft.Dropdown(
            label="Trạng thái",
            options=[ft.dropdown.Option("Đang học"), ft.dropdown.Option("Nghỉ học"), ft.dropdown.Option("Tốt nghiệp")],
            border_radius=8, text_size=13, height=45
        )
        self.form_ngay_ra_quyet_dinh = ft.TextField(label="Ngày quyết định (YYYY-MM-DD)", border_radius=8, text_size=13, height=45)
        self.form_diachi = ft.TextField(label="Địa chỉ liên hệ", border_radius=8, multiline=True, min_lines=2, text_size=13)
        self.form_ghichu = ft.TextField(label="Ghi chú", border_radius=8, multiline=True, min_lines=2, text_size=13)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN SINH VIÊN CHI TIẾT", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(
                width=800,
                content=ft.Column([
                    ft.Text("Thông tin cơ bản", weight=ft.FontWeight.BOLD, color=current_theme.primary),
                    ft.Row([self.form_student_id, self.form_ma_ho_so, self.form_gioitinh]),
                    ft.Row([self.form_ho, self.form_ten]),
                    ft.Row([self.form_email, self.form_dien_thoai]),
                    ft.Row([self.form_ngaysinh, self.form_noi_sinh]),
                    ft.Divider(),
                    ft.Text("Thông tin lý lịch", weight=ft.FontWeight.BOLD, color=current_theme.primary),
                    ft.Row([self.form_dan_toc, self.form_ton_giao]),
                    ft.Row([self.form_nguyen_quan, self.form_ho_khau]),
                    ft.Row([self.form_ngay_vao_doan, self.form_bac_dao_tao]),
                    ft.Divider(),
                    ft.Text("Thông tin gia đình", weight=ft.FontWeight.BOLD, color=current_theme.primary),
                    ft.Row([self.form_ho_ten_cha, self.form_nghe_nghiep_cha]),
                    ft.Row([self.form_ho_ten_me, self.form_nghe_nghiep_me]),
                    ft.Divider(),
                    ft.Text("Học tập & Liên hệ", weight=ft.FontWeight.BOLD, color=current_theme.primary),
                    ft.Row([self.form_lop, self.form_trang_thai, self.form_ngay_ra_quyet_dinh]),
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

        # -- Batch Help Content --
        batch_help = ft.ExpansionTile(
            title=ft.Text("HƯỚNG DẪN COPY TỪ EXCEL (XEM TẠI ĐÂY)", size=13, weight=ft.FontWeight.BOLD, color=current_theme.primary),
            subtitle=ft.Text("Click để xem cấu trúc 24 cột chuẩn", size=11),
            maintain_state=True,
            controls=[
                ft.Container(
                    padding=15,
                    bgcolor=ft.Colors.WHITE,
                    content=ft.Column([
                        ft.Text("Thứ tự 24 cột chuẩn (theo file quản lý):", weight=ft.FontWeight.BOLD, size=12),
                        ft.Text(
                            "1. STT | 2. Mã hồ sơ | 3. MSSV (BẮT BUỘC) | 4. Họ đệm | 5. Tên | 6. Giới tính | "
                            "7. Ngày sinh (DD/MM/YYYY) | 8. Nơi sinh | 9. Dân tộc | 10. Tôn giáo | 11. Nguyên quán | "
                            "12. Hộ khẩu | 13. Ngày vào Đoàn | 14. Lớp học | 15. Khóa học | 16. Bậc đào tạo | "
                            "17. Họ tên cha | 18. Nghề nghiệp (Cha) | 19. Họ tên mẹ | 20. Nghề nghiệp (Mẹ) | "
                            "21. Điện thoại | 22. Trạng thái | 23. Ngày quyết định | 24. Ghi chú",
                            size=11, color=current_theme.text_muted
                        ),
                        ft.Divider(),
                        ft.Text("Cách thực hiện:", weight=ft.FontWeight.BOLD, size=12),
                        ft.Text("1. Mở file Excel, bôi đen vùng dữ liệu (không cần bôi đen dòng tiêu đề).", size=11),
                        ft.Text("2. Nhấn Ctrl + C để copy.", size=11),
                        ft.Text("3. Dán (Ctrl + V) vào ô nhập liệu bên dưới.", size=11),
                        ft.Text("4. Chọn lớp tiếp nhận và nhấn 'TIẾN HÀNH THÊM'.", size=11),
                        ft.Text("Lưu ý: MSSV phải là số và không được trùng lặp trong hệ thống.", size=11, color=ft.Colors.RED_700, italic=True),
                    ], spacing=8)
                )
            ]
        )

        # -- Batch Dialog --
        self.batch_class_dropdown = ft.Dropdown(label="Chọn Lớp tiếp nhận", border_radius=8)
        self.batch_text_area = ft.TextField(
            label="Dán dữ liệu từ Excel vào đây",
            hint_text="Dán dữ liệu tại đây...",
            multiline=True, min_lines=8, max_lines=12, border_radius=8, text_size=12
        )
        self.batch_dialog = ft.AlertDialog(
            title=ft.Text("BỔ SUNG SINH VIÊN HÀNG LOẠT", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(
                width=750,
                content=ft.Column([
                    batch_help,
                    ft.Text("Bước 1: Chọn lớp sẽ tiếp nhận sinh viên mới", size=12, weight=ft.FontWeight.BOLD),
                    self.batch_class_dropdown,
                    ft.Text("Bước 2: Dán dữ liệu đã copy từ Excel", size=12, weight=ft.FontWeight.BOLD),
                    self.batch_text_area,
                ], tight=True, spacing=15, scroll=ft.ScrollMode.AUTO)
            ),
            actions=[
                ft.TextButton("HỦY", on_click=self.close_batch_dialog),
                ft.Button("TIẾN HÀNH THÊM", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_batch_data)
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

    async def refresh_all_data(self, e):
        """Xóa cache và tải lại toàn bộ."""
        self.svc.invalidate("classes")
        await self.initialize_data()
        show_top_notification(self.app_page, "Thông tin", "Đã làm mới dữ liệu sinh viên!", ft.Colors.BLUE)

    def change_page_size(self, e):
        """Thay đổi số lượng dòng hiển thị trên mỗi trang."""
        if self.page_size_dropdown.value:
            self.grid.update_page_size(int(self.page_size_dropdown.value))

    async def load_classes(self):
        """Tải danh sách lớp phục vụ bộ lọc và form nhập liệu."""
        try:
            self.classes_list = await self.svc.get_classes()
            self.class_by_id = {str(c["id"]): c for c in self.classes_list}
            self.class_filter.options = [ft.dropdown.Option("all", "Tất cả lớp")]
            self.form_lop.options = []
            courses = set()
            for c in self.classes_list:
                self.class_filter.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
                self.form_lop.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
                if c.get("khoahoc"):
                    courses.add(str(c["khoahoc"]))
            self.course_filter.options = [ft.dropdown.Option("all", "Tất cả")]
            self.batch_class_dropdown.options = []
            for crs in sorted(list(courses)):
                self.course_filter.options.append(ft.dropdown.Option(crs, f"K{crs}"))
            
            for c in self.classes_list:
                self.batch_class_dropdown.options.append(ft.dropdown.Option(c["id"], c["tenlop"]))
            
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
        """Lọc danh sách theo từ khóa, lớp và khóa học, tích hợp sắp xếp thông minh."""
        query = self.search_field.value.lower() if self.search_field.value else ""
        c_id = str(self.class_filter.value) if self.class_filter.value else "all"
        course = str(self.course_filter.value) if self.course_filter.value else "all"

        self.filtered_data = []
        for item in self.all_data:
            # Tìm kiếm theo MSSV (chính là id), tên, họ, email
            mssv = str(item.get("id") or "").lower()
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
                class_info = self.class_by_id.get(item_class_id)
                match_course = str(class_info.get("khoahoc")) == course if class_info else False

            if match_search and match_class and match_course:
                self.filtered_data.append(item)

        # --- Logic Sắp xếp Thông minh ---
        def get_class_name(item):
            class_id = str(item.get("class_id"))
            c = self.class_by_id.get(class_id)
            return c["tenlop"] if c else "zzz"

        if c_id == "all":
            # Nếu load hàng loạt: Sắp theo Lớp trước, sau đó theo Tên
            self.filtered_data.sort(key=lambda x: (get_class_name(x), str(x.get("ten", "")).lower()))
        else:
            # Nếu đã chọn lớp: Chỉ cần sắp theo Tên (A-Z)
            self.filtered_data.sort(key=lambda x: str(x.get("ten", "")).lower())

        self.current_page = 1
        self.render_table()

    def debounce_filter_data(self, e):
        self._filter_seq += 1
        self.app_page.run_task(self._debounced_filter_data, self._filter_seq)

    async def _debounced_filter_data(self, seq: int):
        await asyncio.sleep(0.3)
        if seq == self._filter_seq and getattr(self, "page", None):
            self.filter_data(None)

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
            class_info = self.class_by_id.get(str(item.get("class_id")))
            d["tenlop"] = class_info["tenlop"] if class_info else "N/A"
            d["student_id"] = str(item.get("id", "N/A")) # Hiển thị ID chính là MSSV
            # Auto-gen full_name từ họ đệm + tên (không dùng trường riêng)
            d["full_name"] = f"{item.get('hodem', '')} {item.get('ten', '')}".strip()
            display_data.append(d)

        # Mặc định sắp xếp theo Tên (A-Z) nếu chưa có sort key
        if not self.grid.sort_key:
            display_data.sort(key=lambda x: x.get("ten", "").lower())

        self.grid.set_data(display_data)

    # ─── Dialog CRUD ──────────────────────────────────────────────

    def _clear_errors(self):
        """Xóa thông báo lỗi trên form nhập liệu."""
        self.form_student_id.error_text = None
        self.form_ho.error_text = None
        self.form_ten.error_text = None

    def _clear_form(self):
        """Reset toàn bộ giá trị form về mặc định."""
        self.form_student_id.value = ""
        self.form_ma_ho_so.value = ""
        self.form_ho.value = ""
        self.form_ten.value = ""
        self.form_email.value = ""
        self.form_lop.value = None
        self.form_gioitinh.value = "Nam"
        self.form_ngaysinh.value = ""
        self.form_noi_sinh.value = ""
        self.form_dan_toc.value = "Kinh"
        self.form_ton_giao.value = "Không"
        self.form_nguyen_quan.value = ""
        self.form_ho_khau.value = ""
        self.form_ngay_vao_doan.value = ""
        self.form_bac_dao_tao.value = "Đại học"
        self.form_ho_ten_cha.value = ""
        self.form_nghe_nghiep_cha.value = ""
        self.form_ho_ten_me.value = ""
        self.form_nghe_nghiep_me.value = ""
        self.form_dien_thoai.value = ""
        self.form_trang_thai.value = "Đang học"
        self.form_ngay_ra_quyet_dinh.value = ""
        self.form_diachi.value = ""
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
        self.form_student_id.value = str(data.get("id", ""))
        self.form_student_id.disabled = True
        self.form_ma_ho_so.value = data.get("ma_ho_so", "")
        self.form_ho.value = data.get("hodem", "")
        self.form_ten.value = data.get("ten", "")
        self.form_email.value = data.get("email", "")
        self.form_lop.value = data.get("class_id")
        self.form_gioitinh.value = data.get("gioitinh", "Nam")
        self.form_ngaysinh.value = data.get("ngaysinh", "")
        self.form_noi_sinh.value = data.get("noi_sinh", "")
        self.form_dan_toc.value = data.get("dan_toc", "")
        self.form_ton_giao.value = data.get("ton_giao", "")
        self.form_nguyen_quan.value = data.get("nguyen_quan", "")
        self.form_ho_khau.value = data.get("ho_khau", "")
        self.form_ngay_vao_doan.value = data.get("ngay_vao_doan", "")
        self.form_bac_dao_tao.value = data.get("bac_dao_tao", "")
        self.form_ho_ten_cha.value = data.get("ho_ten_cha", "")
        self.form_nghe_nghiep_cha.value = data.get("nghe_nghiep_cha", "")
        self.form_ho_ten_me.value = data.get("ho_ten_me", "")
        self.form_nghe_nghiep_me.value = data.get("nghe_nghiep_me", "")
        self.form_dien_thoai.value = data.get("dien_thoai", "")
        self.form_trang_thai.value = data.get("trang_thai", "Đang học")
        self.form_ngay_ra_quyet_dinh.value = data.get("ngay_ra_quyet_dinh", "")
        self.form_diachi.value = data.get("diachi", "")
        self.form_ghichu.value = data.get("ghichu", "")
        if self.dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def close_dialog(self, e=None):
        """Đóng dialog form."""
        self.dialog.open = False
        self.app_page.update()

    def open_batch_dialog(self, e):
        """Mở dialog thêm nhanh danh sách."""
        self.batch_text_area.value = ""
        self.batch_class_dropdown.value = self.class_filter.value if self.class_filter.value != "all" else None
        if self.batch_dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.batch_dialog)
        self.batch_dialog.open = True
        self.app_page.update()

    def close_batch_dialog(self, e=None):
        self.batch_dialog.open = False
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
                "id": int(self.form_student_id.value),
                "ma_ho_so": self.form_ma_ho_so.value or None,
                "hodem": self.form_ho.value,
                "ten": self.form_ten.value,
                "full_name": f"{self.form_ho.value} {self.form_ten.value}".strip(),
                "email": self.form_email.value or None,
                "class_id": self.form_lop.value,
                "gioitinh": self.form_gioitinh.value,
                "ngaysinh": self.form_ngaysinh.value or None,
                "noi_sinh": self.form_noi_sinh.value or None,
                "dan_toc": self.form_dan_toc.value or None,
                "ton_giao": self.form_ton_giao.value or None,
                "nguyen_quan": self.form_nguyen_quan.value or None,
                "ho_khau": self.form_ho_khau.value or None,
                "ngay_vao_doan": self.form_ngay_vao_doan.value or None,
                "bac_dao_tao": self.form_bac_dao_tao.value or None,
                "ho_ten_cha": self.form_ho_ten_cha.value or None,
                "nghe_nghiep_cha": self.form_nghe_nghiep_cha.value or None,
                "ho_ten_me": self.form_ho_ten_me.value or None,
                "nghe_nghiep_me": self.form_nghe_nghiep_me.value or None,
                "dien_thoai": self.form_dien_thoai.value or None,
                "trang_thai": self.form_trang_thai.value or "Đang học",
                "ngay_ra_quyet_dinh": self.form_ngay_ra_quyet_dinh.value or None,
                "diachi": self.form_diachi.value or None,
                "ghichu": self.form_ghichu.value or None
            }
            if self.is_edit:
                await self.svc.update(f"/api/admin/system/{self.form_id.value}", payload)
            else:
                await self.svc.create("/api/admin/system/", payload)

            self.close_dialog()
            show_top_notification(self.app_page, "Thông báo", "Lưu thông tin sinh viên thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    def save_batch_data(self, e):
        """Xử lý dữ liệu từ text area và gọi API batch."""
        if not self.batch_class_dropdown.value:
            show_top_notification(self.app_page, "Lỗi", "Vui lòng chọn lớp tiếp nhận!", ft.Colors.ORANGE)
            return
        if not self.batch_text_area.value or not self.batch_text_area.value.strip():
            show_top_notification(self.app_page, "Lỗi", "Vui lòng nhập danh sách sinh viên!", ft.Colors.ORANGE)
            return

        self.app_page.run_task(self._save_batch_async)

    async def _save_batch_async(self):
        try:
            class_id = self.batch_class_dropdown.value
            if not class_id:
                show_top_notification(self.app_page, "Lỗi", "Vui lòng chọn Lớp tiếp nhận!", ft.Colors.RED)
                return

            lines = self.batch_text_area.value.strip().split("\n")
            items = []
            
            def parse_dt(txt):
                if not txt or txt.strip() == "" or txt.lower() == "none": return None
                txt = txt.strip().replace('"', '') # Loại bỏ dấu ngoặc kép nếu có
                try:
                    # Xử lý dấu phân cách
                    sep = "-" if "-" in txt else "/"
                    p = txt.split(sep)
                    if len(p) != 3: return None
                    
                    # p[2] thường là năm
                    y = p[2].strip()
                    if len(y) == 2: y = "20" + y # 24 -> 2024
                    
                    # Thông minh: Tìm xem đâu là ngày, đâu là tháng
                    v1, v2 = int(p[0]), int(p[1])
                    
                    if v1 > 12: # Chắc chắn v1 là ngày (DD/MM/YYYY)
                        d, m = v1, v2
                    elif v2 > 12: # Chắc chắn v2 là ngày (MM/DD/YYYY)
                        m, d = v1, v2
                    else: # Cả 2 đều <= 12, ưu tiên định dạng VN: DD/MM/YYYY
                        d, m = v1, v2
                        
                    return f"{y}-{str(m).zfill(2)}-{str(d).zfill(2)}"
                except: return None

            for line in lines:
                line = line.strip()
                if not line or len(line) < 5: continue
                
                sep = "\t" if "\t" in line else "|"
                parts = [p.strip().replace('"', '') for p in line.split(sep)]
                
                # Cấu trúc 24 cột chuẩn
                if len(parts) < 4: continue # Ít nhất phải có MSSV và Tên
                
                try:
                    # Cột 3 là MSSV (index 2)
                    mssv_raw = parts[2] if len(parts) > 2 else None
                    if not mssv_raw or not mssv_raw.isdigit(): continue
                    mssv_int = int(mssv_raw)

                    items.append({
                        "id": mssv_int,
                        "ma_ho_so": parts[1] if len(parts) > 1 else None,
                        "hodem": parts[3] if len(parts) > 3 else "Trống",
                        "ten": parts[4] if len(parts) > 4 else "Trống",
                        "full_name": f"{parts[3]} {parts[4]}".strip() if len(parts) > 4 else "Trống",
                        "gioitinh": parts[5] if len(parts) > 5 else "Nam",
                        "ngaysinh": parse_dt(parts[6]) if len(parts) > 6 else None,
                        "noi_sinh": parts[7] if len(parts) > 7 else None,
                        "dan_toc": parts[8] if len(parts) > 8 else None,
                        "ton_giao": parts[9] if len(parts) > 9 else None,
                        "nguyen_quan": parts[10] if len(parts) > 10 else None,
                        "ho_khau": parts[11] if len(parts) > 11 else None,
                        "ngay_vao_doan": parse_dt(parts[12]) if len(parts) > 12 else None,
                        "class_id": class_id,
                        "bac_dao_tao": parts[15] if len(parts) > 15 else None,
                        "ho_ten_cha": parts[16] if len(parts) > 16 else None,
                        "nghe_nghiep_cha": parts[17] if len(parts) > 17 else None,
                        "ho_ten_me": parts[18] if len(parts) > 18 else None,
                        "nghe_nghiep_me": parts[19] if len(parts) > 19 else None,
                        "dien_thoai": parts[20] if len(parts) > 20 else None,
                        "trang_thai": parts[21] if len(parts) > 21 else "Đang học",
                        "ngay_ra_quyet_dinh": parse_dt(parts[22]) if len(parts) > 22 else None,
                        "ghichu": parts[23] if len(parts) > 23 else None,
                    })
                except Exception as ex:
                    print(f"Lỗi parse dòng: {line} -> {ex}")
                    continue
            
            if not items:
                show_top_notification(self.app_page, "Lỗi", "Không tìm thấy dữ liệu hợp lệ!", ft.Colors.ORANGE)
                return

            self.progress_bar.visible = True
            self.update()

            res = await self.svc.create("/api/admin/system/batch", {"items": items})
            
            if isinstance(res, dict) and res.get("error") == "DUPLICATE_MSSV":
                dup_list = res.get("duplicate_ids", [])
                show_top_notification(self.app_page, "TRÙNG MSSV", f"Lỗi: {len(dup_list)} sinh viên đã tồn tại: {dup_list[:5]}...", ft.Colors.RED)
                return

            if isinstance(res, dict) and "detail" in res:
                # Lỗi 422 từ FastAPI
                show_top_notification(self.app_page, "Lỗi dữ liệu", "Dữ liệu không hợp lệ (422). Kiểm tra terminal server.", ft.Colors.RED)
                return

            self.close_batch_dialog()
            show_top_notification(self.app_page, "Thành công", f"Đã thêm mới {len(items)} sinh viên!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            print(f"BATCH ERROR: {e}")
            show_top_notification(self.app_page, f"Lỗi hệ thống: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Delete ───────────────────────────────────────────────────

    def delete_data(self, data):
        """Mở hộp thoại xác nhận xóa Sinh Viên."""
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN XÓA", f"Xóa sinh viên {data['ten']}?", on_confirm)

    async def _delete_data_async(self, id):
        """Gửi request xóa Sinh Viên qua AdminService."""
        try:
            await self.svc.delete(f"/api/admin/system/{id}")
            show_top_notification(self.app_page, "Thông báo", "Đã xóa sinh viên thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể xóa sinh viên: {e}", ft.Colors.RED, sound="E")

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
