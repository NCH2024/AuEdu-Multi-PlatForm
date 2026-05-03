"""
Trang quản lý Học Kỳ — Admin Panel.
Cung cấp CRUD hoàn chỉnh cho bảng Học Kỳ, tích hợp DatePicker
cho ngày bắt đầu/kết thúc, và liên kết quản lý tuần học.
"""

import flet as ft
from core.theme import current_theme
import datetime
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
        self.calendar_weeks = []

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
        self.form_id = ft.TextField(label="Mã định danh", disabled=True, border_radius=8, text_size=12, height=38)
        self.form_ten = ft.TextField(label="Tên Học Kỳ", border_radius=8, text_size=12, height=38, hint_text="VD: Học kỳ 1")
        
        self.form_nien_khoa = ft.TextField(label="Niên khóa", border_radius=8, text_size=12, height=38, hint_text="VD: 2025-2026")
        self.form_loai = ft.Dropdown(
            label="Loại Học kỳ", border_radius=8, text_size=12, height=38,
            options=[ft.dropdown.Option("Chính"), ft.dropdown.Option("Hè"), ft.dropdown.Option("Phụ")],
            value="Chính"
        )
        
        self.cal_year_dropdown = ft.Dropdown(
            label="Năm tính lịch tuần", border_radius=8, text_size=12, height=38, expand=True,
            options=[ft.dropdown.Option(str(y)) for y in range(datetime.datetime.now().year - 5, datetime.datetime.now().year + 6)]
        )
        self.cal_year_dropdown.on_change = self.on_year_change
        
        self.btn_refresh_weeks = ft.IconButton(
            ft.Icons.SYNC_ROUNDED, tooltip="Nạp lại danh sách tuần",
            on_click=self.on_year_change
        )
        
        self.form_so_tuan = ft.TextField(label="Số tuần học", value="0", border_radius=8, text_size=12, height=40, read_only=True, prefix_icon=ft.Icons.TIMER_ROUNDED, expand=True)
        self.duration_info = ft.Text("", size=11, italic=True, color=current_theme.primary)

        self.week_start_dropdown = ft.Dropdown(label="Tuần bắt đầu", expand=True, text_size=12)
        self.week_start_dropdown.on_change = self.on_week_selection_change
        self.week_end_dropdown = ft.Dropdown(label="Tuần kết thúc", expand=True, text_size=12)
        self.week_end_dropdown.on_change = self.on_week_selection_change

        self.form_start = ft.TextField(label="Ngày Bắt đầu", border_radius=8, text_size=12, height=40, expand=True, read_only=True)
        self.form_end = ft.TextField(label="Ngày Kết thúc", border_radius=8, text_size=12, height=40, expand=True, read_only=True)

        self.btn_calculate = ft.Button(
            "XÁC NHẬN & TÍNH NGÀY",
            icon=ft.Icons.CALCULATE_ROUNDED,
            on_click=self.on_calculate_click,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            bgcolor=current_theme.secondary,
            color=ft.Colors.WHITE
        )
        
        self.calc_warning = ft.Text("(!) Vui lòng nhấn nút trên sau khi chọn tuần để cập nhật ngày.", size=11, color=ft.Colors.ORANGE_700, visible=False)

        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN HỌC KỲ", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(width=650, content=ft.Column([
                ft.Row([self.form_id, self.form_ten], spacing=10),
                ft.Row([self.form_nien_khoa, self.form_loai], spacing=10),
                ft.Divider(height=1, color=current_theme.divider_color),
                ft.Text("Thiết lập thời gian học (Chọn tuần trong năm):", size=11, weight=ft.FontWeight.W_500),
                ft.Row([self.cal_year_dropdown, self.btn_refresh_weeks], spacing=10),
                ft.Row([
                    self.week_start_dropdown,
                    ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=16, color=current_theme.text_muted),
                    self.week_end_dropdown
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=ft.Column([self.btn_calculate, self.calc_warning], horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.Alignment(0, 0)),
                ft.Row([self.form_so_tuan, self.duration_info], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.form_start, self.form_end])
            ], tight=True, spacing=12, scroll=ft.ScrollMode.AUTO)),
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

    def get_calendar_weeks(self, year_str: str):
        """Tính toán 52 tuần trong năm dựa trên chuỗi năm học (VD: 2024-2025 -> lấy 2024)."""
        try:
            year = int(year_str.split("-")[0])
        except:
            year = datetime.datetime.now().year
            
        start_date = datetime.date(year, 1, 1)
        # Di chuyển đến thứ 2 đầu tiên
        while start_date.weekday() != 0:
            start_date += datetime.timedelta(days=1)
        
        weeks = []
        for i in range(1, 53):
            end_date = start_date + datetime.timedelta(days=6)
            weeks.append({
                "id": i,
                "label": f"Tuần {i:02} ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})",
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            })
            start_date = end_date + datetime.timedelta(days=1)
        return weeks

    def _populate_week_options(self):
        """Tính toán và cập nhật options cho dropdown dựa trên năm hiện tại."""
        self.calendar_weeks = self.get_calendar_weeks(self.cal_year_dropdown.value)
        opts = [ft.dropdown.Option(str(w["id"]), w["label"]) for w in self.calendar_weeks]
        self.week_start_dropdown.options = opts
        self.week_end_dropdown.options = opts

    def on_year_change(self, e):
        """Khi thay đổi năm, reset các lựa chọn cũ và cập nhật options mới."""
        self._populate_week_options()
        
        # Reset các giá trị để tránh sai lệch ngày giữa các năm
        self.week_start_dropdown.value = None
        self.week_end_dropdown.value = None
        self.form_start.value = ""
        self.form_end.value = ""
        self.form_so_tuan.value = "0"
        self.duration_info.value = "Hệ thống đã nạp lại danh sách tuần."
        self.calc_warning.visible = False
        
        # Cập nhật trực tiếp các control để Flet 0.84.0 nhận biết
        self.week_start_dropdown.update()
        self.week_end_dropdown.update()
        self.app_page.update()

    def on_week_selection_change(self, e):
        """Khi chọn tuần bắt đầu/kết thúc, làm sạch các trường ngày để yêu cầu tính toán lại."""
        self.form_start.value = ""
        self.form_end.value = ""
        self.form_so_tuan.value = "0"
        self.calc_warning.visible = True
        self.app_page.update()

    def on_calculate_click(self, e):
        """Tính toán ngày bắt đầu/kết thúc dựa trên tuần đã chọn."""
        if not self.week_start_dropdown.value or not self.week_end_dropdown.value:
            show_top_notification(self.app_page, "Cảnh báo", "Vui lòng chọn cả tuần bắt đầu và kết thúc!", ft.Colors.ORANGE)
            return
            
        w_start_id = int(self.week_start_dropdown.value)
        w_end_id = int(self.week_end_dropdown.value)
        
        if w_start_id > w_end_id:
            show_top_notification(self.app_page, "Lỗi", "Tuần bắt đầu không thể lớn hơn tuần kết thúc!", ft.Colors.RED)
            return

        w_start = next((w for w in self.calendar_weeks if w["id"] == w_start_id), None)
        w_end = next((w for w in self.calendar_weeks if w["id"] == w_end_id), None)
        
        if w_start and w_end:
            self.form_start.value = w_start["start"]
            self.form_end.value = w_end["end"]
            
            # Tính số tuần
            start_dt = datetime.datetime.strptime(w_start["start"], "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(w_end["end"], "%Y-%m-%d")
            diff_days = (end_dt - start_dt).days + 1
            num_weeks = int(diff_days / 7)
            self.form_so_tuan.value = str(num_weeks)
            self.duration_info.value = f"Thời lượng: {num_weeks} tuần (~{num_weeks*7} ngày)"
            self.calc_warning.visible = False
            
            show_top_notification(self.app_page, "Đã tính toán", f"Phạm vi: {num_weeks} tuần học.", ft.Colors.GREEN)
            self.app_page.update()

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
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải danh sách học kỳ: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    async def refresh_all_data(self, e):
        """Xóa cache và tải lại học kỳ."""
        self.svc.invalidate("semesters")
        await self.load_data()
        show_top_notification(self.app_page, "Thông tin", "Đã làm mới dữ liệu học kỳ thành công!", ft.Colors.BLUE, sound="S")

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
        self.form_nien_khoa.error_text = None

    def open_add_dialog(self, e):
        """Mở dialog thêm Học Kỳ mới."""
        self.is_edit = False
        self.form_id.value = "Tự động"
        self.form_ten.value = ""
        self.form_nien_khoa.value = f"{datetime.datetime.now().year}-{datetime.datetime.now().year+1}"
        self.form_loai.value = "Chính"
        self.cal_year_dropdown.value = str(datetime.datetime.now().year)
        self._populate_week_options() # Populate weeks
        self.week_start_dropdown.value = None
        self.week_end_dropdown.value = None
        self.form_so_tuan.value = "0"
        self.duration_info.value = ""
        self.form_start.value = ""
        self.form_end.value = ""
        self.calc_warning.visible = False
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
        self.form_nien_khoa.value = data["namhoc"]
        self.form_loai.value = data.get("loai_hocky", "Chính")
        
        # Thử lấy năm từ ngày bắt đầu để set cho cal_year_dropdown
        if data.get("start_date"):
            try:
                start_year = data["start_date"].split("-")[0]
                self.cal_year_dropdown.value = start_year
            except:
                self.cal_year_dropdown.value = str(datetime.datetime.now().year)
        else:
            self.cal_year_dropdown.value = str(datetime.datetime.now().year)

        self._populate_week_options() # Cập nhật danh sách tuần mà không reset giá trị
        
        self.form_so_tuan.value = str(data.get("so_tuan_hoc", 15))
        self.form_start.value = data.get("start_date", "")
        self.form_end.value = data.get("end_date", "")
        
        # Thử tìm tuần tương ứng với ngày hiện tại (nếu có)
        if self.form_start.value and self.calendar_weeks:
            w_start = next((w for w in self.calendar_weeks if w["start"] == self.form_start.value), None)
            if w_start: self.week_start_dropdown.value = str(w_start["id"])
        
        if self.form_end.value and self.calendar_weeks:
            w_end = next((w for w in self.calendar_weeks if w["end"] == self.form_end.value), None)
            if w_end: self.week_end_dropdown.value = str(w_end["id"])

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

        if not self.form_nien_khoa.value or not self.form_nien_khoa.value.strip():
            self.form_nien_khoa.error_text = "Vui lòng nhập niên khóa"
            has_error = True
        else:
            self.form_nien_khoa.error_text = None

        if not self.form_start.value or not self.form_end.value:
            show_top_notification(self.app_page, "Lỗi", "Vui lòng nhấn 'TÍNH TOÁN NGÀY' trước khi lưu!", ft.Colors.RED)
            has_error = True

        if has_error:
            self.app_page.update()
            return

        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        """Gửi request tạo/cập nhật Học Kỳ qua AdminService."""
        try:
            payload = {
                "tenhocky": self.form_ten.value,
                "namhoc": self.form_nien_khoa.value,
                "loai_hocky": self.form_loai.value,
                "so_tuan_hoc": int(self.form_so_tuan.value) if self.form_so_tuan.value.isdigit() else 15,
                "start_date": self.form_start.value,
                "end_date": self.form_end.value
            }
            res = None
            if self.is_edit:
                res = await self.svc.update(f"/api/admin/semesters/{self.form_id.value}", payload)
                target_id = self.form_id.value
            else:
                res = await self.svc.create("/api/admin/semesters/", payload)
                target_id = res.get("id") if res else None
            
            self.svc.invalidate("semesters")
            self.close_dialog()
            show_top_notification(self.app_page, "Thông báo", "Lưu thông tin học kỳ thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
            
            # Tự động gọi API tạo/cập nhật tuần nếu có ngày bắt đầu
            if target_id and self.form_start.value:
                try:
                    week_payload = {
                        "start_date": self.form_start.value,
                        "start_week_index": int(self.week_start_dropdown.value) if self.week_start_dropdown.value else 1
                    }
                    await self.svc.create(f"/api/admin/semesters/{target_id}/generate_weeks", week_payload)
                    show_top_notification(self.app_page, "AuEdu Hệ thống", f"Đã tự động khởi tạo/cập nhật {self.form_so_tuan.value} tuần học!", ft.Colors.BLUE)
                except Exception as e_week:
                    print(f"Error generating weeks: {e_week}")
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi hệ thống", str(e), ft.Colors.RED, sound="E")

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
            show_top_notification(self.app_page, "Thông báo", "Đã xóa học kỳ thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
