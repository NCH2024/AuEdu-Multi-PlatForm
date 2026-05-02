"""
Trang quản lý Tuần Học — Admin Panel.
Hiển thị danh sách tuần học theo học kỳ, hỗ trợ tạo tự động
dựa trên ngày bắt đầu và số tuần của học kỳ.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class WeeksPage(ft.Container):
    """Trang quản lý tuần học theo học kỳ đã chọn."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)

        # -- State --
        self.semester_id: str = None
        self.semester_info: dict = {}
        self.all_weeks: list = []
        self.svc = AdminService.instance()

        # -- UI Elements --
        self.title_text = ft.Text(
            "QUẢN LÝ TUẦN HỌC", size=20,
            weight=ft.FontWeight.BOLD, color=current_theme.text_main
        )
        self.subtitle_text = ft.Text("", size=14, color=current_theme.text_muted)

        self.btn_back = ft.IconButton(
            ft.Icons.ARROW_BACK_ROUNDED,
            on_click=lambda _: self.app_page.run_task(self.app_page.push_route, "/admin/semesters")
        )

        self.btn_generate = ft.Button(
            "TẠO TUẦN TỰ ĐỘNG",
            icon=ft.Icons.AUTO_RENEW_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.open_generate_dialog
        )

        self.grid = AdminDataGrid(
            columns=[
                {"label": "TÊN TUẦN", "key": "ten_tuan", "col": {"xs": 12, "sm": 4}},
                {"label": "NGÀY BẮT ĐẦU", "key": "ngay_bat_dau", "col": {"xs": 6, "sm": 4}},
                {"label": "NGÀY KẾT THÚC", "key": "ngay_ket_thuc", "col": {"xs": 6, "sm": 4}},
            ],
            rows_per_page=15
        )

        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)

        self.content = ft.Column([
            ft.Row([
                ft.Row([self.btn_back, self.title_text]),
                self.btn_generate
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.subtitle_text,
            self.progress_bar,
            ft.Divider(color=current_theme.divider_color),
            self.grid
        ], expand=True)

        # -- Generate Dialog --
        self.start_date_picker = ft.DatePicker(on_change=self.on_date_selected)
        self.form_start_date = ft.TextField(label="Ngày bắt đầu học kỳ", read_only=True, expand=True)
        self.btn_pick_date = ft.IconButton(
            ft.Icons.CALENDAR_MONTH,
            on_click=lambda _: self.app_page.open(self.start_date_picker)
        )

        self.gen_dialog = ft.AlertDialog(
            title=ft.Text("THIẾT LẬP TUẦN HỌC"),
            content=ft.Column([
                ft.Text("Hệ thống sẽ tự động rải số tuần dựa trên ngày bắt đầu này."),
                ft.Row([self.form_start_date, self.btn_pick_date])
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("HỦY", on_click=self.close_gen_dialog),
                ft.Button("XÁC NHẬN TẠO", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.generate_weeks)
            ]
        )

    # ─── Handlers ─────────────────────────────────────────────────

    def on_date_selected(self, e):
        """Cập nhật TextField khi chọn ngày từ DatePicker."""
        if self.start_date_picker.value:
            self.form_start_date.value = self.start_date_picker.value.strftime("%Y-%m-%d")
            self.update()

    def open_generate_dialog(self, e):
        """Mở dialog thiết lập tạo tuần tự động."""
        if self.gen_dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.gen_dialog)
        self.gen_dialog.open = True
        self.app_page.update()

    def close_gen_dialog(self, e=None):
        """Đóng dialog tạo tuần."""
        self.gen_dialog.open = False
        self.app_page.update()

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Parse semester_id từ URL route và tải dữ liệu."""
        import urllib.parse
        try:
            url = self.app_page.route
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            self.semester_id = params.get("semester_id", [None])[0]
            if self.semester_id:
                self.app_page.run_task(self.load_data)
        except Exception as ex:
            print(f"[WeeksPage] Lỗi parse URL: {ex}")

    async def load_data(self):
        """Tải thông tin học kỳ và danh sách tuần từ AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            # 1. Load semester info
            semesters = await self.svc.get_semesters()
            self.semester_info = next(
                (s for s in semesters if str(s["id"]) == self.semester_id), {}
            )
            self.subtitle_text.value = (
                f"Học kỳ: {self.semester_info.get('tenhocky')} "
                f"- Năm học: {self.semester_info.get('namhoc')}"
            )
            if self.semester_info.get("start_date"):
                self.form_start_date.value = self.semester_info["start_date"]

            # 2. Load weeks
            self.all_weeks = await self.svc.get_weeks(self.semester_id, force=True)
            self.all_weeks.sort(key=lambda x: x.get("ngay_bat_dau", ""))
            self.grid.set_data(self.all_weeks)

        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    async def generate_weeks(self, e):
        """Gọi API tạo tuần học tự động cho học kỳ đã chọn."""
        if not self.form_start_date.value:
            show_top_notification(self.app_page, "Vui lòng chọn ngày bắt đầu", ft.Colors.ORANGE)
            return

        self.close_gen_dialog()
        self.progress_bar.visible = True
        self.update()
        try:
            await self.svc.create(
                f"/api/admin/semesters/{self.semester_id}/generate_weeks",
                {"start_date": self.form_start_date.value}
            )
            self.svc.invalidate(f"weeks_{self.semester_id}")
            show_top_notification(self.app_page, "Đã tạo tuần học và cập nhật học kỳ!", ft.Colors.GREEN)
            await self.load_data()
        except Exception as ex:
            show_top_notification(self.app_page, f"Lỗi hệ thống: {ex}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
