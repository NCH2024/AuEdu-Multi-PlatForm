"""
Trang thiết lập Lịch Điểm Danh — Admin Panel.
Cho phép admin cấu hình TKB hàng tuần: chọn môn, lớp, giảng viên,
thứ/tiết/phòng, cấu hình AI, sau đó xem trước và lưu hàng loạt.
"""

import flet as ft
import datetime
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService


class AttendanceSchedulePage(ft.Container):
    """Trang thiết lập thời khóa biểu hàng tuần cho lịch điểm danh."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(20)
        self.alignment = ft.Alignment(-1, -1)

        # -- State --
        self.subjects: list = []
        self.classes: list = []
        self.semesters: list = []
        self.weeks: list = []
        self.preview_data: list = []
        self.svc = AdminService.instance()

        # --- UI COMPONENTS ---
        self.subject_dropdown = ft.Dropdown(label="Chọn môn học", expand=True)
        self.subject_dropdown.on_change = self.on_subject_change
        self.semester_dropdown = ft.Dropdown(label="Học kỳ", width=200)
        self.semester_dropdown.on_change = self.on_semester_change
        self.week_dropdown = ft.Dropdown(label="Tuần bắt đầu", expand=True)
        self.class_dropdown = ft.Dropdown(label="Chọn lớp", expand=True)
        self.teacher_dropdown = ft.Dropdown(label="Giảng viên phụ trách", expand=True)

        self.room_field = ft.TextField(label="Phòng học (VD: A1-101)", value="Phòng Lab AI", expand=True)
        self.start_period = ft.TextField(label="Tiết BĐ", value="1", width=80)
        self.end_period = ft.TextField(label="Tiết KT", value="3", width=80)

        # Checkboxes chọn thứ trong tuần
        self.days_checkboxes = [
            ft.Checkbox(label="Thứ 2", data=0, value=False),
            ft.Checkbox(label="Thứ 3", data=1, value=False),
            ft.Checkbox(label="Thứ 4", data=2, value=False),
            ft.Checkbox(label="Thứ 5", data=3, value=False),
            ft.Checkbox(label="Thứ 6", data=4, value=False),
            ft.Checkbox(label="Thứ 7", data=5, value=False),
            ft.Checkbox(label="Chủ Nhật", data=6, value=False),
        ]

        self.ai_threshold_slider = ft.Slider(min=0.3, max=0.9, value=0.6, label="Cosine: {value}", expand=True)
        self.anti_spoofing_switch = ft.Switch(label="Anti-Spoofing", value=True)

        self.preview_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("STT")),
                ft.DataColumn(ft.Text("Ngày học")),
                ft.DataColumn(ft.Text("Thứ")),
                ft.DataColumn(ft.Text("Phòng")),
                ft.DataColumn(ft.Text("Tiết")),
            ],
            rows=[]
        )

        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)

        # Layout chính
        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH_ROUNDED, color=current_theme.primary, size=30),
                ft.Text("THIẾT LẬP THỜI KHÓA BIỂU HÀNG TUẦN", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ]),
            self.progress_bar,
            ft.Divider(color=current_theme.divider_color),

            ft.Row([self.subject_dropdown, self.semester_dropdown]),
            ft.Row([self.week_dropdown, self.class_dropdown, self.teacher_dropdown]),

            ft.Text("Chọn các thứ học trong tuần:", weight=ft.FontWeight.BOLD),
            ft.Row(self.days_checkboxes, wrap=True, spacing=10),

            ft.Row([self.room_field, self.start_period, self.end_period]),

            ft.ExpansionTile(
                title=ft.Text("Cấu hình AI nâng cao", size=14, weight=ft.FontWeight.W_500),
                controls=[
                    ft.Row([self.ai_threshold_slider, self.anti_spoofing_switch],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]
            ),

            ft.Container(height=10),
            ft.Row([
                ft.Button("XEM TRƯỚC LỊCH", icon=ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
                          bgcolor=ft.Colors.BLUE_GREY_700, color=ft.Colors.WHITE,
                          on_click=self.generate_preview),
                ft.Button("LƯU TOÀN BỘ LỊCH", icon=ft.Icons.SAVE_ROUNDED,
                          bgcolor=current_theme.primary, color=ft.Colors.WHITE,
                          on_click=self.save_batch_schedule),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),

            ft.Divider(color=current_theme.divider_color),
            ft.Text("DANH SÁCH BUỔI HỌC DỰ KIẾN:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Row([self.preview_table], scroll=ft.ScrollMode.AUTO)
                ], scroll=ft.ScrollMode.AUTO, expand=True),
                border=ft.Border.all(1, current_theme.divider_color),
                border_radius=8, padding=10, expand=True
            )
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Kích hoạt tải dữ liệu ban đầu."""
        self.app_page.run_task(self.initialize_data)

    async def initialize_data(self):
        """Tải song song danh sách môn, học kỳ, lớp, giảng viên từ AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            # Load Subjects
            self.subjects = await self.svc.get_subjects()
            self.subject_dropdown.options = [
                ft.dropdown.Option(str(s["id"]), f"{s['tenhocphan']} ({s['sobuoi']} buổi)")
                for s in self.subjects
            ]

            # Load Semesters
            self.semesters = await self.svc.get_semesters()
            self.semester_dropdown.options = [
                ft.dropdown.Option(str(s["id"]), f"{s['tenhocky']} ({s['namhoc']})")
                for s in self.semesters
            ]
            if self.semesters:
                self.semester_dropdown.value = str(self.semesters[-1]["id"])
                await self.load_weeks(self.semester_dropdown.value)

            # Load Classes
            self.classes = await self.svc.get_classes()
            self.class_dropdown.options = [
                ft.dropdown.Option(str(c["id"]), c["tenlop"])
                for c in self.classes
            ]

            # Load Teachers
            teachers = await self.svc.get_teachers()
            self.teacher_dropdown.options = [
                ft.dropdown.Option(str(t["id"]), f"{t.get('hodem', '')} {t.get('ten', '')}")
                for t in teachers
            ]

            self.update()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi khởi tạo: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Handlers ─────────────────────────────────────────────────

    async def on_semester_change(self, e):
        """Khi đổi học kỳ, tải lại danh sách tuần."""
        await self.load_weeks(self.semester_dropdown.value)

    def on_subject_change(self, e):
        """Placeholder cho xử lý khi đổi môn học (VD: cập nhật số buổi mặc định)."""
        pass

    async def load_weeks(self, semester_id):
        """Tải danh sách tuần học theo học kỳ, cập nhật dropdown."""
        self.progress_bar.visible = True
        self.update()
        try:
            self.weeks = await self.svc.get_weeks(semester_id, force=True)
            self.week_dropdown.options = [
                ft.dropdown.Option(
                    str(w["id"]),
                    f"{w['ten_tuan']} (Từ {w['ngay_bat_dau']})",
                    data=w['ngay_bat_dau']
                )
                for w in self.weeks
            ]
            if self.weeks:
                self.week_dropdown.value = str(self.weeks[0]["id"])
            else:
                self.week_dropdown.options = []
            self.update()
        except Exception as e:
            show_top_notification(self.app_page, f"Lỗi tải tuần: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    # ─── Preview ──────────────────────────────────────────────────

    def generate_preview(self, e):
        """Tạo danh sách buổi học dự kiến dựa trên cấu hình đã chọn."""
        if not self.subject_dropdown.value or not self.week_dropdown.value \
           or not self.class_dropdown.value or not self.teacher_dropdown.value:
            show_top_notification(self.app_page, "Vui lòng chọn đủ Môn, Tuần, Lớp và Giảng viên!", ft.Colors.ORANGE)
            return

        selected_days = [cb.data for cb in self.days_checkboxes if cb.value]
        if not selected_days:
            show_top_notification(self.app_page, "Vui lòng chọn ít nhất một thứ trong tuần!", ft.Colors.ORANGE)
            return

        subject = next((s for s in self.subjects if str(s["id"]) == self.subject_dropdown.value), None)
        total_sessions = subject["sobuoi"] if subject else 15

        start_week = next((w for w in self.weeks if str(w["id"]) == self.week_dropdown.value), None)
        start_date = datetime.datetime.strptime(start_week["ngay_bat_dau"], "%Y-%m-%d").date()

        self.preview_data = []
        current_date = start_date
        sessions_count = 0

        # Duyệt từng ngày cho đến khi đủ số buổi
        while sessions_count < total_sessions:
            wd = current_date.weekday()
            if wd in selected_days:
                sessions_count += 1
                day_name = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"][wd]
                self.preview_data.append({
                    "stt": sessions_count,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "day_name": day_name,
                    "room": self.room_field.value,
                    "period": f"{self.start_period.value}-{self.end_period.value}"
                })
            current_date += datetime.timedelta(days=1)

            # Giới hạn an toàn — tối đa 1 năm
            if (current_date - start_date).days > 365:
                break

        self.render_preview_table()

    def render_preview_table(self):
        """Render bảng xem trước lịch học dự kiến."""
        self.preview_table.rows.clear()
        for item in self.preview_data:
            self.preview_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(item["stt"]))),
                ft.DataCell(ft.Text(item["date"], weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(item["day_name"])),
                ft.DataCell(ft.Text(item["room"])),
                ft.DataCell(ft.Text(item["period"])),
            ]))
        self.update()

    # ─── Save ─────────────────────────────────────────────────────

    def save_batch_schedule(self, e):
        """Validate rồi gọi lưu TKB hàng loạt."""
        if not self.preview_data:
            show_top_notification(self.app_page, "Vui lòng 'Xem trước lịch' trước khi lưu!", ft.Colors.ORANGE)
            return
        self.app_page.run_task(self._save_batch_async)

    async def _save_batch_async(self):
        """Gửi request POST /thoikhoabieu/setup_batch qua AdminService."""
        self.progress_bar.visible = True
        self.update()
        try:
            selected_days = [cb.data for cb in self.days_checkboxes if cb.value]

            payload = {
                "hocphan_id": int(self.subject_dropdown.value),
                "hocky_id": int(self.semester_dropdown.value),
                "lop_id": self.class_dropdown.value,
                "giangvien_id": int(self.teacher_dropdown.value),
                "ai_threshold": self.ai_threshold_slider.value,
                "anti_spoofing": self.anti_spoofing_switch.value,
                "fiqa_threshold": 0.5,
                "slots": [
                    {
                        "thu": day,
                        "start_tiet": int(self.start_period.value),
                        "end_tiet": int(self.end_period.value),
                        "phong_hoc": self.room_field.value
                    } for day in selected_days
                ]
            }

            await self.svc.create("/api/schedule/thoikhoabieu/setup_batch", payload)
            show_top_notification(self.app_page, "Đã thiết lập Thời khóa biểu thành công!", ft.Colors.GREEN)
            self.preview_data = []
            self.render_preview_table()
        except Exception as ex:
            show_top_notification(self.app_page, f"Lỗi hệ thống: {ex}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.update()
