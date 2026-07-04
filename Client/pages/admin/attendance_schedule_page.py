"""
Trang thiết lập Lịch Điểm Danh (Nâng cấp) — Admin Panel.
Sử dụng giao diện lưới trực quan để sắp lịch và kiểm tra xung đột.
"""

import flet as ft
import datetime
import json
import asyncio
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
from components.admin.schedule_grid import ScheduleGrid

class AttendanceSchedulePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(20)
        self.alignment = ft.Alignment(-1, -1)

        self.svc = AdminService.instance()
        
        # -- Data Storage --
        self.subjects = []
        self.classes = []
        self.semesters = []
        self.weeks = []
        self.periods = []
        
        # -- State --
        self.busy_slots = []
        self.draft_items = [] # List of {hocphan_id, lop_id, phong_hoc, slots: [{"thu", "tiet_id"}]}
        self.current_selection = [] # List of {"thu", "tiet_id"} for the currently active subject/class/room

        # --- UI COMPONENTS ---
        self.semester_dropdown = ft.Dropdown(label="Học kỳ", width=180, text_size=13)
        self.semester_dropdown.on_change = self.on_context_change
        
        self.dept_dropdown = ft.Dropdown(label="Khoa / Bộ môn", expand=True, text_size=13)
        self.dept_dropdown.on_change = self.on_dept_change
        
        self.teacher_search = ft.TextField(label="Tìm GV (Tên/Mã)", expand=True, text_size=13, on_change=self.on_teacher_search)
        self.teacher_dropdown = ft.Dropdown(label="Chọn Giảng viên", expand=True, text_size=13)
        self.teacher_dropdown.on_change = self.on_context_change
        
        self.week_dropdown = ft.Dropdown(label="Chọn tuần xem nhanh", expand=True)
        self.week_dropdown.on_change = self.on_week_dropdown_change
        
        self.btn_apply_context = ft.Button(
            "XEM LỊCH TRỰC QUAN", 
            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
            bgcolor=current_theme.primary,
            color=ft.Colors.WHITE,
            on_click=self.on_context_change
        )
        
        self.week_label = ft.Text("Tuần --", weight=ft.FontWeight.BOLD, size=16)
        self.week_info_text = ft.Text("Chọn học kỳ để xem", size=12, color=current_theme.text_muted)
        
        self.subject_dropdown = ft.Dropdown(label="Môn học", expand=True)
        self.subject_dropdown.on_change = self.on_subject_change
        self.class_dropdown = ft.Dropdown(label="Lớp học", expand=True)
        self.room_field = ft.TextField(label="Phòng học", value="Phòng Lab AI", expand=True)
        
        self.sobuoi_text = ft.Text("Số buổi: --", weight=ft.FontWeight.BOLD, color=current_theme.primary, size=13)
        self.auto_create_checkbox = ft.Checkbox(
            label="Chế độ Auto (Lặp cả kỳ)", 
            value=True,
            on_change=self.on_auto_mode_change,
            scale=0.9
        )
        self.mode_label = ft.Text("Chế độ: Toàn bộ học kỳ", size=11, italic=True, color=ft.Colors.BLUE_400)
        
        self.btn_preview_auto = ft.Button(
            "XEM REVIEW AUTO", 
            icon=ft.Icons.PREVIEW_ROUNDED,
            bgcolor=current_theme.secondary,
            color=ft.Colors.WHITE,
            on_click=self.on_preview_auto,
            visible=False
        )
        
        self.grid_container = ft.Container(expand=True, content=ft.Text("Đang tải lưới lịch..."))
        self.grid = None
        
        self.draft_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        self.existing_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Môn học")),
                ft.DataColumn(ft.Text("Lớp")),
                ft.DataColumn(ft.Text("Phòng")),
                ft.DataColumn(ft.Text("Thứ/Tiết")),
                ft.DataColumn(ft.Text("Xóa")),
            ],
            rows=[]
        )
        
        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)
        
        # Layout build
        self.content = self.build_ui()

    def build_ui(self):
        header = ft.Row([
            ft.Icon(ft.Icons.CALENDAR_VIEW_MONTH_ROUNDED, color=current_theme.primary, size=30),
            ft.Text("QUẢN LÝ LỊCH GIẢNG DẠY (TRỰC QUAN)", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main, expand=True),
            ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="Làm mới dữ liệu", on_click=self.refresh_all_data)
        ])

        context_panel = ft.Container(
            padding=15,
            border_radius=12,
            border=ft.Border.all(1, current_theme.divider_color),
            bgcolor=current_theme.surface_color,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.HUB_ROUNDED, color=current_theme.primary, size=18),
                    ft.Text("BỐ CẢNH LẬP LỊCH", weight=ft.FontWeight.BOLD, size=13),
                ]),
                ft.Row([
                    self.semester_dropdown,
                    self.dept_dropdown,
                    ft.Row([self.teacher_search, self.teacher_dropdown], expand=True, spacing=10),
                    self.btn_apply_context
                ], spacing=15)
            ], spacing=10)
        )

        week_nav_panel = ft.Container(
            padding=15,
            border_radius=12,
            bgcolor=current_theme.surface_variant,
            content=ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.CHEVRON_LEFT_ROUNDED, on_click=self.prev_week),
                    ft.Column([
                        self.week_label,
                        self.week_info_text
                    ], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT_ROUNDED, on_click=self.next_week),
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                self.week_dropdown
            ], spacing=10)
        )

        config_panel = ft.Container(
            width=300,
            padding=20,
            border_radius=12,
            bgcolor=current_theme.surface_variant,
            content=ft.Column([
                ft.Text("CẤU HÌNH TIẾT HỌC", weight=ft.FontWeight.W_800, size=14, color=current_theme.secondary),
                self.subject_dropdown,
                ft.Row([self.sobuoi_text, self.auto_create_checkbox], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.mode_label,
                self.class_dropdown,
                self.room_field,
                self.btn_preview_auto,
                ft.Divider(),
                ft.Text("Mẹo: Chế độ Auto giúp bạn sắp lịch một lần cho cả kỳ. Nếu tắt Auto, lịch chỉ áp dụng cho tuần đang xem.", 
                        size=11, color=current_theme.text_muted, italic=True),
            ], spacing=15)
        )

        grid_panel = ft.Column([
            ft.Row([
                ft.Text("LƯỚI LỊCH TRÌNH", weight=ft.FontWeight.BOLD, size=16),
                ft.Row([
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREY_600), border_radius=3),
                    ft.Text("Đã có lịch", size=11),
                    ft.Container(width=12, height=12, bgcolor=ft.Colors.with_opacity(0.15, current_theme.primary), border_radius=3, border=ft.Border.all(1, current_theme.primary)),
                    ft.Text("Đang chọn", size=11),
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.grid_container
        ], expand=True)

        draft_panel = ft.Container(
            padding=12,
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=12,
            bgcolor=current_theme.surface_color,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LIST_ALT_ROUNDED, color=current_theme.primary, size=18),
                    ft.Text("DANH SÁCH CHỜ", weight=ft.FontWeight.BOLD, size=13),
                ]),
                ft.Container(
                    height=300,
                    content=self.draft_container
                ),
                ft.Row([
                    ft.TextButton("XÓA HẾT", icon=ft.Icons.DELETE_SWEEP_ROUNDED, on_click=self.clear_draft),
                    ft.Button("LƯU LỊCH", icon=ft.Icons.SAVE_ROUNDED, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_all)
                ], alignment=ft.MainAxisAlignment.END, spacing=5)
            ], spacing=5)
        )

        existing_panel = ft.Container(
            padding=15,
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=12,
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.EVENT_AVAILABLE_ROUNDED, color=current_theme.secondary),
                    ft.Text("LỊCH HỌC HIỆN CÓ TRONG HỌC KỲ", weight=ft.FontWeight.BOLD, size=16),
                ]),
                ft.Row([self.existing_table], scroll=ft.ScrollMode.AUTO),
            ], spacing=10)
        )

        return ft.Column([
            header,
            self.progress_bar,
            ft.Divider(color=current_theme.divider_color),
            context_panel,
            ft.Container(height=5),
            ft.Row([
                ft.Column([
                    config_panel,
                    ft.Container(height=10),
                    week_nav_panel,
                    ft.Container(height=10),
                    draft_panel
                ], width=320),
                grid_panel
            ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Divider(),
            existing_panel
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    # ─── Data Loading ─────────────────────────────────────────────

    def did_mount(self):
        self.app_page.run_task(self.initialize_data)

    async def initialize_data(self):
        self.progress_bar.visible = True
        self.update()
        try:
            results = await asyncio.gather(
                self.svc.get_subjects(),
                self.svc.get_semesters(),
                self.svc.get_classes(),
                self.svc.get_all_teachers(),
                self.svc.get_all_periods()
            )
            self.subjects, self.semesters, self.classes, self.all_teachers, self.periods = results
            self.depts = await self.svc.get_departments()

            self.dept_dropdown.options = [ft.dropdown.Option(str(d["id"]), d["tenkhoa"]) for d in self.depts]
            self.subject_dropdown.options = [ft.dropdown.Option(str(s["id"]), s["tenhocphan"]) for s in self.subjects]
            self.semester_dropdown.options = [ft.dropdown.Option(str(s["id"]), f"{s['tenhocky']} ({s['namhoc']})") for s in self.semesters]
            self.class_dropdown.options = [ft.dropdown.Option(str(c["id"]), c["tenlop"]) for c in self.classes]
            self.teacher_dropdown.options = [ft.dropdown.Option(str(t["id"]), f"{t.get('hodem','')} {t['ten']}") for t in self.all_teachers]
            # Initialize Grid first
            self.grid = ScheduleGrid(self.periods, on_slot_click=self.on_slot_click)
            self.grid_container.content = self.grid

            if self.semesters:
                self.semester_dropdown.value = str(self.semesters[-1]["id"])
                await self.load_weeks(self.semester_dropdown.value)
                self.update_week_display()

            await self.fetch_busy_slots()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Khởi tạo dữ liệu thất bại: {e}", ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    async def load_weeks(self, semester_id):
        try:
            self.weeks = await self.svc.get_weeks(semester_id, force=True)
            if self.weeks:
                # Sắp xếp tuần theo thứ tự ngày bắt đầu
                self.weeks.sort(key=lambda x: x.get("ngay_bat_dau", ""))
                self.week_dropdown.options = [
                    ft.dropdown.Option(str(w["id"]), f"Tuần {w['ten_tuan']}") for w in self.weeks
                ]
                self.week_dropdown.value = str(self.weeks[0]["id"])
            else:
                self.week_dropdown.options = [
                    ft.dropdown.Option("", "Chưa có tuần học")
                ]
                self.week_dropdown.value = ""
                show_top_notification(
                    self.app_page, 
                    "Thông báo", 
                    "Học kỳ này chưa được tạo tuần học! Hãy vào trang Quản lý Học kỳ để tạo tuần học.", 
                    ft.Colors.ORANGE, 
                    sound="E"
                )
            
            # Cập nhật trực tiếp control dropdown để Flet vẽ lại options
            self.week_dropdown.update()
            self.update_week_display()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải tuần học: {e}", ft.Colors.RED, sound="E")
        self.update()

    def update_week_display(self):
        if not self.weeks:
            self.week_label.value = "Chưa có tuần học"
            self.week_info_text.value = "Vui lòng tạo tuần học cho học kỳ này"
            if hasattr(self, "grid") and self.grid:
                self.grid.set_selected_week(None)
            self.week_label.update()
            self.week_info_text.update()
            self.update()
            return
        if not self.week_dropdown.value:
            self.week_label.value = "Tuần --"
            self.week_info_text.value = "Chọn tuần để xem"
            if hasattr(self, "grid") and self.grid:
                self.grid.set_selected_week(None)
            self.week_label.update()
            self.week_info_text.update()
            self.update()
            return
        w = next((w for w in self.weeks if str(w["id"]) == self.week_dropdown.value), None)
        if w:
            self.week_label.value = f"Tuần {w['ten_tuan']}"
            self.week_info_text.value = f"{w['ngay_bat_dau']} -> {w['ngay_ket_thuc']}"
            if hasattr(self, "grid") and self.grid:
                self.grid.set_selected_week(w)
        else:
            self.week_label.value = "Tuần --"
            self.week_info_text.value = "Chọn tuần để xem"
            if hasattr(self, "grid") and self.grid:
                self.grid.set_selected_week(None)
        
        # Cập nhật trực tiếp các control nhãn
        self.week_label.update()
        self.week_info_text.update()
        self.update()

    async def prev_week(self, e):
        if not self.week_dropdown.value or not self.weeks: return
        curr_idx = next((i for i, w in enumerate(self.weeks) if str(w["id"]) == self.week_dropdown.value), 0)
        if curr_idx > 0:
            self.week_dropdown.value = str(self.weeks[curr_idx - 1]["id"])
            self.update_week_display()
            await self.fetch_busy_slots()

    async def next_week(self, e):
        if not self.week_dropdown.value or not self.weeks: return
        curr_idx = next((i for i, w in enumerate(self.weeks) if str(w["id"]) == self.week_dropdown.value), 0)
        if curr_idx < len(self.weeks) - 1:
            self.week_dropdown.value = str(self.weeks[curr_idx + 1]["id"])
            self.update_week_display()
            await self.fetch_busy_slots()

    async def on_week_dropdown_change(self, e):
        self.update_week_display()
        # Khi đổi tuần, phải load lại slot bận của tuần đó
        await self.fetch_busy_slots()

    async def fetch_busy_slots(self):
        if not self.semester_dropdown.value: return
        
        self.progress_bar.visible = True
        self.update()
        try:
            # Lấy các slot bận của Giảng viên hiện tại trong học kỳ này, có lọc theo tuần
            gv_id = int(self.teacher_dropdown.value) if self.teacher_dropdown.value else None
            week_id = int(self.week_dropdown.value) if self.week_dropdown.value else None
            
            busy = await self.svc.get_busy_slots(
                int(self.semester_dropdown.value), 
                gv_id=gv_id,
                week_id=week_id
            )
            
            # Đánh dấu target_gv_id để grid biết cái nào là của mình
            for b in busy: b["target_gv_id"] = gv_id
            
            self.busy_slots = busy
            if self.grid:
                self.grid.set_busy_slots(self.busy_slots)
            
            # Cập nhật bảng Lịch hiện có
            self.render_existing_table()
        except Exception as e:
            print(f"fetch_busy_slots error: {e}")
        finally:
            self.progress_bar.visible = False
            self.update()

    def render_existing_table(self):
        self.existing_table.rows.clear()
        
        # Nhóm busy_slots theo tkb_id để hiển thị gọn
        schedules = {}
        for s in self.busy_slots:
            tid = s["tkb_id"]
            if tid not in schedules:
                schedules[tid] = {
                    "hocphan": s["hocphan"],
                    "lop": s["lop"],
                    "phong": s["phong_hoc"],
                    "slots": []
                }
            schedules[tid]["slots"].append(f"T{s['thu']}-Tiết {s['tiet_id']}")
        
        day_names = {2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7", 8: "CN"}
        
        for tid, info in schedules.items():
            self.existing_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(info["hocphan"], weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(info["lop"])),
                ft.DataCell(ft.Text(info["phong"])),
                ft.DataCell(ft.Text(", ".join(info["slots"][:3]) + ("..." if len(info["slots"]) > 3 else ""), size=11)),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED, icon_color=ft.Colors.RED_700, 
                                          on_click=lambda e, t=tid: self.confirm_delete_schedule(t)))
            ]))
        self.update()

    def confirm_delete_schedule(self, tkb_id):
        def close_dlg(e):
            dlg.open = False
            self.app_page.update()

        async def do_delete(e):
            close_dlg(e)
            self.progress_bar.visible = True
            self.update()
            try:
                await self.svc.delete_schedule(tkb_id)
                show_top_notification(self.app_page, "Thành công", "Đã xóa lịch học!", ft.Colors.GREEN)
                await self.fetch_busy_slots()
            except Exception as ex:
                msg = str(ex).replace("Exception: ", "")
                show_top_notification(self.app_page, "Lỗi khi xóa", msg, ft.Colors.RED)
            finally:
                self.progress_bar.visible = False
                self.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Xác nhận xóa"),
            content=ft.Text("Bạn có chắc chắn muốn xóa lịch học này? Hành động này không thể hoàn tác và sẽ bị chặn nếu đã có dữ liệu điểm danh."),
            actions=[
                ft.TextButton("Hủy", on_click=close_dlg),
                ft.Button("Xác nhận xóa", bgcolor=ft.Colors.RED, color=ft.Colors.WHITE, on_click=do_delete)
            ]
        )
        self.app_page.overlay.append(dlg)
        dlg.open = True
        self.app_page.update()

    # ─── Handlers ─────────────────────────────────────────────────

    async def on_subject_change(self, e):
        if not self.subject_dropdown.value:
            self.sobuoi_text.value = "Số buổi: --"
        else:
            sub = next((s for s in self.subjects if str(s["id"]) == self.subject_dropdown.value), None)
            if sub:
                self.sobuoi_text.value = f"Số buổi: {sub.get('sobuoi', '??')}"
        self.update()

    async def on_context_change(self, e):
        """Khi đổi Học kỳ / Giảng viên -> Cần load lại các slot bận."""
        try:
            if e and e.control == self.semester_dropdown:
                await self.load_weeks(self.semester_dropdown.value)
                
            await self.fetch_busy_slots()
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", f"Đã xảy ra lỗi: {ex}", ft.Colors.RED, sound="E")

    def on_dept_change(self, e):
        """Lọc danh sách giảng viên theo khoa."""
        if not self.dept_dropdown.value: return
        dept_id = self.dept_dropdown.value # ID của khoa là String (VD: 'CNTT')
        filtered = [t for t in self.all_teachers if t.get("khoa_id") == dept_id]
        self.teacher_dropdown.options = [ft.dropdown.Option(str(t["id"]), f"{t.get('hodem','')} {t['ten']}") for t in filtered]
        self.teacher_dropdown.value = None
        self.update()

    def on_teacher_search(self, e):
        """Tìm giảng viên theo tên/mã."""
        q = self.teacher_search.value.lower()
        dept_id = self.dept_dropdown.value # String ID
        
        filtered = self.all_teachers
        if dept_id:
            filtered = [t for t in filtered if t.get("khoa_id") == dept_id]
        
        if q:
            filtered = [t for t in filtered if q in t["ten"].lower() or q in t.get("hodem","").lower() or q in str(t.get("ma_gv","")).lower()]
            
        self.teacher_dropdown.options = [ft.dropdown.Option(str(t["id"]), f"{t.get('hodem','')} {t['ten']}") for t in filtered]
        if len(filtered) == 1:
            self.teacher_dropdown.value = str(filtered[0]["id"])
        self.update()

    def on_auto_mode_change(self, e):
        self.mode_label.value = "Chế độ: Toàn bộ học kỳ" if self.auto_create_checkbox.value else "Chế độ: Chỉ tuần hiện tại"
        self.mode_label.color = ft.Colors.BLUE_400 if self.auto_create_checkbox.value else ft.Colors.ORANGE_400
        
        # Nếu tắt Auto, xóa nháp cũ để tránh nhầm lẫn (hoặc giữ lại tùy logic)
        if not self.auto_create_checkbox.value:
            self.clear_draft(None)
        
        self.update()

    def on_slot_click(self, thu, tiet_id):
        if not self.subject_dropdown.value or not self.class_dropdown.value:
            show_top_notification(self.app_page, "Lưu ý", "Vui lòng chọn Môn học và Lớp học trước!", ft.Colors.ORANGE)
            return

        self.btn_preview_auto.visible = self.auto_create_checkbox.value

        # Kiểm tra xem slot này đã bị bận chưa
        if any(s["thu"] == thu and s["tiet_id"] == tiet_id for s in self.busy_slots):
            show_top_notification(self.app_page, "Xung đột", "Tiết này đã có lịch giảng dạy (Bận)!", ft.Colors.RED)
            return

        # Khóa các dropdown ngữ cảnh khi bắt đầu chọn
        self.semester_dropdown.disabled = True
        self.teacher_dropdown.disabled = True
        self.week_dropdown.disabled = True
        
        # Kiểm tra xem slot này đã có trong nháp chưa
        # Ta cần tìm xem trong draft_items có item nào khớp {hocphan, lop, phong} không
        hp_id = int(self.subject_dropdown.value)
        lop_id = self.class_dropdown.value
        phong = self.room_field.value
        
        target_item = next((item for item in self.draft_items if item["hocphan_id"] == hp_id and item["lop_id"] == lop_id and item["phong_hoc"] == phong), None)
        
        if not target_item:
            target_item = {
                "hocphan_id": hp_id,
                "lop_id": lop_id,
                "phong_hoc": phong,
                "tuan_hoc_id": None if self.auto_create_checkbox.value else int(self.week_dropdown.value),
                "ten_hp": next(s["tenhocphan"] for s in self.subjects if s["id"] == hp_id),
                "ten_lop": next(c["tenlop"] for c in self.classes if c["id"] == lop_id),
                "slots": []
            }
            self.draft_items.append(target_item)
            
        # Toggle slot
        slot_exists = next((s for s in target_item["slots"] if s["thu"] == thu and s["tiet_id"] == tiet_id), None)
        if slot_exists:
            target_item["slots"].remove(slot_exists)
            # Nếu item không còn slot nào thì xóa item
            if not target_item["slots"]:
                self.draft_items.remove(target_item)
        else:
            # Kiểm tra xem slot này có bị trùng trong chính danh sách nháp (item khác) không
            other_conflict = False
            for other in self.draft_items:
                if any(s["thu"] == thu and s["tiet_id"] == tiet_id for s in other["slots"]):
                    if other != target_item:
                        show_top_notification(self.app_page, "Xung đột nháp", "Tiết này bạn đã chọn cho một lớp/môn khác trong danh sách nháp!", ft.Colors.RED)
                        other_conflict = True
                        break
            if not other_conflict:
                target_item["slots"].append({"thu": thu, "tiet_id": tiet_id})

        self.render_draft_ui()

    def render_draft_ui(self):
        # Cập nhật Grid
        all_draft_slots = []
        for item in self.draft_items:
            for s in item["slots"]:
                all_draft_slots.append({
                    "thu": s["thu"],
                    "tiet_id": s["tiet_id"],
                    "subject": item["ten_hp"],
                    "color": current_theme.primary # Có thể đổi màu theo môn
                })
        self.grid.set_draft_slots(all_draft_slots)
        
        # Cập nhật Card Nháp
        self.draft_container.controls.clear()
        for idx, item in enumerate(self.draft_items):
            self.draft_container.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item["ten_hp"], weight=ft.FontWeight.BOLD, size=13, expand=True),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=ft.Colors.RED_400, icon_size=18, 
                                              on_click=lambda e, i=idx: self.remove_draft_item(i))
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Lớp: {item['ten_lop']}", size=12),
                            ft.Row([
                                ft.Icon(ft.Icons.PLACE_OUTLINED, size=12, color=current_theme.text_muted),
                                ft.Text(item["phong_hoc"], size=11, color=current_theme.text_muted),
                                ft.VerticalDivider(width=10),
                                ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=12, color=current_theme.primary),
                                ft.Text(f"{len(item['slots'])} tiết" + (" (Cả kỳ)" if not item["tuan_hoc_id"] else " (Tuần lẻ)"), 
                                        size=11, weight=ft.FontWeight.W_500, color=current_theme.primary)
                            ], spacing=5)
                        ], spacing=3)
                    ),
                    elevation=2
                )
            )
        
        # Nếu hết nháp thì mở khóa dropdown
        if not self.draft_items:
            self.semester_dropdown.disabled = False
            self.teacher_dropdown.disabled = False
            self.week_dropdown.disabled = False

        self.update()

    def remove_draft_item(self, idx):
        self.draft_items.pop(idx)
        self.render_draft_ui()

    def clear_draft(self, e):
        self.draft_items = []
        self.btn_preview_auto.visible = False
        self.render_draft_ui()

    async def on_preview_auto(self, e):
        """
        Hiển thị review lịch tự động dựa trên số buổi.
        Logic: Tính số buổi/tuần -> Số tuần cần thiết -> List các ngày sẽ học.
        """
        if not self.draft_items: return
        
        # Lấy item nháp hiện tại (giả sử chỉ đang chỉnh 1 item)
        item = self.draft_items[-1]
        hp_id = item["hocphan_id"]
        sub = next((s for s in self.subjects if s["id"] == hp_id), None)
        total_sessions = sub.get("sobuoi", 0) if sub else 0
        
        if total_sessions == 0:
            show_top_notification(self.app_page, "Lỗi", "Môn học này chưa cấu hình tổng số buổi!", ft.Colors.RED)
            return
            
        # Tính số buổi mỗi tuần (nhóm theo buổi Sáng/Chiều/Tối của từng thứ)
        sessions_per_week = [] # List of (thu, buoi_type)
        for s in item["slots"]:
            pid = s["tiet_id"]
            buoi = ""
            if 1 <= pid <= 5: buoi = "Sáng"
            elif 7 <= pid <= 12: buoi = "Chiều"
            elif 13 <= pid <= 16: buoi = "Tối"
            
            if buoi and (s["thu"], buoi) not in sessions_per_week:
                sessions_per_week.append((s["thu"], buoi))
        
        count_per_week = len(sessions_per_week)
        if count_per_week == 0:
            show_top_notification(self.app_page, "Lưu ý", "Vui lòng chọn ít nhất một tiết học!", ft.Colors.ORANGE)
            return
            
        # Lấy ngày bắt đầu của tuần đang chọn
        curr_week = next((w for w in self.weeks if str(w["id"]) == self.week_dropdown.value), self.weeks[0])
        start_dt = datetime.datetime.strptime(curr_week["ngay_bat_dau"], "%Y-%m-%d")
        
        # Sinh danh sách các buổi học
        preview_rows = []
        sessions_done = 0
        current_week_dt = start_dt
        
        day_names = {2: "Thứ 2", 3: "Thứ 3", 4: "Thứ 4", 5: "Thứ 5", 6: "Thứ 6", 7: "Thứ 7", 8: "Chủ Nhật"}
        
        # Sort sessions_per_week by day and session type
        sessions_per_week.sort(key=lambda x: (x[0], 0 if x[1]=="Sáng" else (1 if x[1]=="Chiều" else 2)))

        while sessions_done < total_sessions:
            for thu, buoi in sessions_per_week:
                if sessions_done >= total_sessions: break
                
                # Tính ngày cụ thể: start_dt (Monday) + (thu - 2)
                session_date = current_week_dt + datetime.timedelta(days=(thu - 2))
                preview_rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"Buổi {sessions_done + 1}")),
                    ft.DataCell(ft.Text(session_date.strftime("%d/%m/%Y"))),
                    ft.DataCell(ft.Text(day_names.get(thu))),
                    ft.DataCell(ft.Text(buoi, color=current_theme.secondary, weight=ft.FontWeight.BOLD)),
                ]))
                sessions_done += 1
            
            # Sang tuần sau
            current_week_dt += datetime.timedelta(days=7)
            if len(preview_rows) > 100: break # Safety limit

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.AUTORENEW_ROUNDED, color=current_theme.primary),
                ft.Text(f"REVIEW LỊCH AUTO: {item['ten_hp']}", size=16, weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Container(
                width=550, height=500,
                content=ft.Column([
                    ft.Container(
                        padding=10, bgcolor=ft.Colors.with_opacity(0.1, current_theme.primary),
                        border_radius=8,
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=current_theme.primary),
                            ft.Text(f"Môn học yêu cầu {total_sessions} buổi. Hệ thống sẽ lặp lại {count_per_week} tiết/tuần cho đến khi đủ.", size=12)
                        ])
                    ),
                    ft.Divider(height=20),
                    ft.DataTable(
                        heading_row_color=ft.Colors.with_opacity(0.05, current_theme.text_main),
                        columns=[
                            ft.DataColumn(ft.Text("#")),
                            ft.DataColumn(ft.Text("Ngày dự kiến")),
                            ft.DataColumn(ft.Text("Thứ")),
                            ft.DataColumn(ft.Text("Buổi")),
                        ],
                        rows=preview_rows
                    )
                ], scroll=ft.ScrollMode.AUTO, spacing=15)
            ),
            actions=[
                ft.Button("ĐÓNG REVIEW", on_click=lambda e: self.close_dlg(dlg), bgcolor=current_theme.surface_variant)
            ]
        )
        self.app_page.overlay.append(dlg)
        dlg.open = True
        self.app_page.update()

    def close_dlg(self, dlg):
        dlg.open = False
        self.app_page.update()

    async def save_all(self, e):
        if not self.draft_items:
            show_top_notification(self.app_page, "Cảnh báo", "Chưa có tiết học nào được sắp lịch!", ft.Colors.ORANGE)
            return
            
        if not self.teacher_dropdown.value:
            show_top_notification(self.app_page, "Lỗi", "Vui lòng chọn giảng viên phụ trách!", ft.Colors.RED)
            return

        self.progress_bar.visible = True
        self.update()
        try:
            payload = {
                "hocky_id": int(self.semester_dropdown.value),
                "giangvien_id": int(self.teacher_dropdown.value),
                "items": [
                    {
                        "hocphan_id": item["hocphan_id"],
                        "lop_id": item["lop_id"],
                        "phong_hoc": item["phong_hoc"],
                        "tuan_hoc_id": item.get("tuan_hoc_id"),
                        "slots": item["slots"]
                    } for item in self.draft_items
                ]
            }
            
            res = await self.svc.setup_schedule_batch(payload)
            show_top_notification(self.app_page, "Thành công", f"Đã lưu thành công {res.get('total')} lịch học!", ft.Colors.GREEN)
            
            self.clear_draft(None)
            await self.fetch_busy_slots()
        except Exception as ex:
            # Backend sẽ trả về chi tiết xung đột nếu có
            error_msg = str(ex).replace("Exception: ", "")
            show_top_notification(self.app_page, "Lỗi chèn dữ liệu", error_msg, ft.Colors.RED)
        finally:
            self.progress_bar.visible = False
            self.update()

    async def refresh_all_data(self, e):
        self.svc.invalidate_all()
        await self.initialize_data()
        show_top_notification(self.app_page, "Thông tin", "Đã làm mới dữ liệu!", ft.Colors.BLUE)

    def apply_theme(self):
        self.update()
