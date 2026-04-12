import flet as ft
import datetime
import asyncio

from components.options.custom_dropdown import CustomDropdown
from components.options.camera_view import CameraView
from components.options.top_notification import show_top_notification
from components.options.alert_dialog import show_alert_dialog
from core.theme import current_theme
from core.config import get_supabase_client
from core.helper import safe_json_load

class AttendancePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        self.gv_id = "N/A"
        self.tkb_data = []
        self.tiet_data = []
        self.all_students_data = []

        self.current_limit = 50
        self.selected_tkb = None
        self.selected_date = None
        
        # Khai báo nút bấm PC
        self.btn_start_session = ft.Button(
            content=ft.Text("BẮT ĐẦU ĐIỂM DANH", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13), 
            bgcolor=current_theme.secondary, 
            on_click=self.handle_start_session, 
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=15),
            disabled=True # KHÓA MẶC ĐỊNH
        )

        # Khai báo nút bấm Mobile
        self.btn_start_session_mobile = ft.Button(
            content=ft.Text("BẮT ĐẦU ĐIỂM DANH", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13), 
            bgcolor=current_theme.secondary, 
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=15), 
            on_click=self.handle_start_session_mobile,
            disabled=True # KHÓA MẶC ĐỊNH
        )

        self.dd_row_limit = CustomDropdown(
            label="Hiển thị",
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50"), ft.dropdown.Option("100"), ft.dropdown.Option("200")],
            value="20"
        )
        self.dd_row_limit.on_change = self.handle_limit_change

        self.dd_camera = CustomDropdown(label="Chọn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera)

        self.test_progress = ft.ProgressBar(visible=False, color=current_theme.accent, height=2)
        self.test_status_text = ft.Text("", size=11, color=current_theme.text_muted, italic=True, visible=False)

        self.list_view = ft.ResponsiveRow(spacing=10, run_spacing=10)
        self.schedule_list_ui = ft.Column(scroll=ft.ScrollMode.AUTO, height=450, spacing=10)
        self.student_detail_content = ft.Column(tight=True, spacing=8, scroll=ft.ScrollMode.AUTO)

        self.mobile_rg_mode = ft.RadioGroup(value="1", content=ft.Column([ft.Radio(value="1", label="Từng sinh viên"), ft.Radio(value="all", label="Cả lớp")]))
        self.rg_mode = ft.RadioGroup(value="1", content=ft.Row([ft.Radio(value="1", label="Từng sinh viên"), ft.Radio(value="all", label="Cả lớp")], alignment=ft.MainAxisAlignment.CENTER))

        self.info_lop_text = ft.Text("Chưa chọn lớp", weight=ft.FontWeight.BOLD, size=14)
        self.info_mon_text = ft.Text("Vui lòng bấm nút để tìm và chọn lịch dạy", size=12)
        self.info_ngay_text = ft.Text("-", size=12, weight=ft.FontWeight.BOLD)

        self.attendance_bottom_sheet = ft.BottomSheet(
            ft.Container(
                padding=25, border_radius=20,
                content=ft.Column(
                    tight=True, spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        ft.Text("CHẾ ĐỘ ĐIỂM DANH", weight=ft.FontWeight.BOLD, size=14, color=current_theme.secondary, text_align=ft.TextAlign.CENTER),
                        self.mobile_rg_mode,
                        self.btn_start_session_mobile,
                    ]
                )
            )
        )

        self.schedule_dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, color=current_theme.secondary), ft.Text("Chọn lịch giảng dạy", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=16)], alignment=ft.MainAxisAlignment.CENTER),
            content=ft.Container(width=450, content=self.schedule_list_ui),
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[ft.TextButton("Đóng", on_click=lambda e: self.close_schedule_dialog())]
        )

        self.student_detail_dialog = ft.AlertDialog(
            title=ft.Text("Hồ sơ sinh viên", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=16),
            content=ft.Container(width=400, content=self.student_detail_content),
            shape=ft.RoundedRectangleBorder(radius=12),
            actions=[ft.TextButton("Đóng", on_click=lambda e: self.close_student_dialog())]
        )

        self.content = self.build_main_layout()

    def did_mount(self):
        is_mobile = self.app_page.width and self.app_page.width < 768
        if is_mobile:
            self.app_page.floating_action_button = ft.Container(
                margin=ft.Margin.only(bottom=80),
                content=ft.FloatingActionButton(
                    content=ft.Row([ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED, color=ft.Colors.WHITE), ft.Text("Điểm danh", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=current_theme.secondary, width=140, on_click=self.open_mobile_attendance_sheet,
                )
            )
            self.app_page.update()

        for overlay_ui in [self.attendance_bottom_sheet, self.schedule_dialog, self.student_detail_dialog]:
            if overlay_ui not in self.app_page.overlay:
                self.app_page.overlay.append(overlay_ui)

        self.app_page.run_task(self.initialize_page)

    def will_unmount(self):
        self.app_page.floating_action_button = None
        self.app_page.update()

    def apply_theme(self):
        self.info_lop_text.color = current_theme.secondary
        self.info_mon_text.color = current_theme.text_muted
        self.info_ngay_text.color = current_theme.accent

        self.test_progress.color = current_theme.accent
        self.test_status_text.color = current_theme.text_muted

        self.schedule_dialog.bgcolor = current_theme.surface_color
        self.student_detail_dialog.bgcolor = current_theme.surface_color
        self.attendance_bottom_sheet.content.bgcolor = current_theme.surface_color

        self.content = self.build_main_layout()
        self.render_table()
        self.build_schedule_cards()
        if self.page: self.update()

    def build_main_layout(self):
        is_mobile = self.app_page.width and self.app_page.width < 768
        btn_style_menu = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=12)

        self.info_lop_text.color = current_theme.secondary
        self.info_mon_text.color = current_theme.text_muted
        self.info_ngay_text.color = current_theme.accent

        def make_card(content):
            return ft.Container(content=content, padding=15, bgcolor=current_theme.surface_color, border_radius=16, border=ft.Border.all(1, current_theme.divider_color))

        nang_cao_content = ft.Column([
            ft.Button(content=ft.Text("Lịch sử điểm danh", color=ft.Colors.WHITE, size=12), bgcolor=ft.Colors.BLUE_GREY_600, expand=True, style=btn_style_menu),
            ft.Button(content=ft.Text("Tra cứu sinh viên", color=ft.Colors.WHITE, size=12), bgcolor=ft.Colors.BLUE_GREY_600, expand=True, style=btn_style_menu),
            ft.Button(
                content=ft.Text("Đào tạo khuôn mặt", color=ft.Colors.WHITE, size=12), 
                bgcolor=current_theme.secondary, 
                expand=True, 
                style=btn_style_menu,
                on_click=self.handle_start_trainning
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=8)
        nang_cao_tile = ft.ExpansionTile(title=ft.Text("Chức năng nâng cao", weight=ft.FontWeight.BOLD, size=13), controls=[ft.Container(content=nang_cao_content, padding=15)], collapsed_text_color=current_theme.secondary, text_color=current_theme.secondary, icon_color=current_theme.secondary, collapsed_icon_color=current_theme.secondary)

        diem_danh_content = ft.Column([
            ft.Container(content=self.rg_mode, padding=5),
            self.btn_start_session,
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        diem_danh_tile = ft.ExpansionTile(title=ft.Text("Thao tác điểm danh", weight=ft.FontWeight.BOLD, size=13), controls=[ft.Container(content=diem_danh_content, padding=15)], expanded=True, collapsed_text_color=current_theme.secondary, text_color=current_theme.secondary, icon_color=current_theme.secondary, collapsed_icon_color=current_theme.secondary, visible=not is_mobile)

        thiet_bi_content = ft.Column([
            self.dd_camera,
            ft.Container(content=self.camera_view, border_radius=8, clip_behavior=ft.ClipBehavior.HARD_EDGE),
            ft.Row([
                ft.Button(
                    content=ft.Text("Lưu", color=ft.Colors.WHITE, size=12), 
                    bgcolor=current_theme.accent, expand=True, style=btn_style_menu,
                    on_click=self.handle_save_camera
                ),
                ft.Button(content=ft.Text("Kiểm tra", color=ft.Colors.WHITE, size=12), bgcolor=current_theme.secondary, expand=True, on_click=self.handle_test_camera, style=btn_style_menu)
            ], spacing=8),
            self.test_progress, self.test_status_text,
            ft.Text("Yêu cầu lưu cấu hình trước khi kiểm tra thiết bị.", size=10, color=current_theme.text_muted, italic=True)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10)
        thiet_bi_tile = ft.ExpansionTile(title=ft.Text("Thiết lập Camera", weight=ft.FontWeight.BOLD, size=13), controls=[ft.Container(content=thiet_bi_content, padding=15)], expanded=True, collapsed_text_color=current_theme.secondary, text_color=current_theme.secondary, icon_color=current_theme.secondary, collapsed_icon_color=current_theme.secondary)

        side_column = make_card(ft.Column([diem_danh_tile, thiet_bi_tile, nang_cao_tile], spacing=0))

        filter_section = ft.Container(
            bgcolor=current_theme.surface_variant, border_radius=12, padding=15,
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.EVENT_NOTE, size=18, color=current_theme.secondary), ft.Text("THÔNG TIN LỚP HỌC HÔM NAY", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13)]),
                ft.Container(
                    padding=15, bgcolor=current_theme.surface_color, border_radius=8, border=ft.Border.all(1, current_theme.divider_color),
                    content=ft.Column([
                        self.info_lop_text,
                        ft.Row([ft.Text("Môn học: ", size=12, color=current_theme.text_muted), self.info_mon_text], spacing=2),
                        ft.Row([ft.Text("Ngày điểm danh: ", size=12, color=current_theme.text_muted), self.info_ngay_text], spacing=2),
                    ], spacing=3)
                ),
                ft.Container(height=5),
                ft.Row([
                    ft.Button(
                        content=ft.Row([ft.Icon(ft.Icons.SEARCH, color=ft.Colors.WHITE, size=16), ft.Text("TÌM VÀ CHỌN LỊCH DẠY", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=12)]),
                        bgcolor=current_theme.accent, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=15),
                        on_click=self.open_schedule_dialog, expand=True
                    )
                ])
            ])
        )

        table_header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row([ft.Icon(ft.Icons.PEOPLE_ALT_OUTLINED, size=18, color=current_theme.secondary), ft.Text("DANH SÁCH ĐIỂM DANH", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13)]),
                ft.Container(content=self.dd_row_limit, width=90)
            ]
        )

        combined_attendance_card = make_card(
            ft.Column([
                filter_section, ft.Container(height=10), table_header,
                ft.Column([self.list_view], scroll=ft.ScrollMode.AUTO, height=450)
            ], spacing=10)
        )

        dashboard_layout = ft.ResponsiveRow([
            ft.Column([combined_attendance_card], col={"xs": 12, "sm": 12, "md": 12, "lg": 8, "xl": 8}),
            ft.Column([side_column], col={"xs": 12, "sm": 12, "md": 12, "lg": 4, "xl": 4}),
        ], spacing=15, run_spacing=15)

        return ft.Column([ft.Container(height=5), dashboard_layout, ft.Container(height=30)], scroll=ft.ScrollMode.AUTO, expand=True)

    # ══════════════════════════════════════════════════════════════════
    # KHỞI TẠO: Chạy song song fetch schedule + camera
    # ══════════════════════════════════════════════════════════════════
    async def initialize_page(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")

        #Chạy song song, không tuần tự
        await asyncio.gather(
            self.load_all_schedules(),
            self.camera_view.load_available_cameras(),
            return_exceptions=True
        )

        # --- TỰ ĐỘNG TẢI LẠI TRẠNG THÁI NẾU ĐÃ CHỌN TRƯỚC ĐÓ ---
        saved_tkb = self.app_page.session.store.get("saved_selected_tkb")
        saved_date = self.app_page.session.store.get("saved_selected_date")
        
        if saved_tkb and saved_date:
            self.selected_tkb = saved_tkb
            self.selected_date = saved_date
            self.info_lop_text.value = saved_tkb.get("lop", {}).get("tenlop", "N/A")
            self.info_mon_text.value = saved_tkb.get("hocphan", {}).get("tenhocphan", "N/A")
            self.info_ngay_text.value = saved_date
            
            # Khóa nút lại trong lúc đợi API tải để chống Spam
            self.btn_start_session.disabled = True
            self.btn_start_session_mobile.disabled = True
            
            # Tự động fetch lại sinh viên và cập nhật giao diện
            await self.execute_load_students()

        if getattr(self, "page", None):
            self.app_page.update()

    async def load_all_schedules(self):
        if self.gv_id == "N/A": return
        try:
            # ✅ Dùng singleton client, KHÔNG dùng async with
            client = await get_supabase_client()

            res_tkb = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,hocphan_id,hocky_id,lop(tenlop),hocphan(tenhocphan),hocky(tenhocky,namhoc)",
                "giangvien_id": f"eq.{self.gv_id}"
            })
            res_tkb.raise_for_status()
            self.tkb_data = res_tkb.json()

            if self.tkb_data:
                tkb_ids = [str(item['id']) for item in self.tkb_data]
                res_tiet = await client.get("/tkb_tiet", params={
                    "select": "id,tkb_id,thu",
                    "tkb_id": f"in.({','.join(tkb_ids)})"
                })
                res_tiet.raise_for_status()
                self.tiet_data = res_tiet.json()

            self.build_schedule_cards()
        except Exception as e:
            print(f"load_all_schedules lỗi: {e}")

    def build_schedule_cards(self):
        self.schedule_list_ui.controls.clear()

        if not self.tkb_data:
            self.schedule_list_ui.controls.append(ft.Text("Không có lịch giảng dạy nào.", italic=True, color=current_theme.text_muted))
            return

        today = datetime.date.today()
        for tkb in self.tkb_data:
            ten_mon = tkb.get("hocphan", {}).get("tenhocphan", "N/A")
            ten_lop = tkb.get("lop", {}).get("tenlop", "N/A")
            hk_info = f"{tkb.get('hocky', {}).get('tenhocky', '')} ({tkb.get('hocky', {}).get('namhoc', '')})"

            thus = set([t["thu"] for t in self.tiet_data if str(t["tkb_id"]) == str(tkb["id"])])
            dates = []
            for i in range(-60, 60):
                d = today + datetime.timedelta(days=i)
                if (d.weekday() + 2) in thus: dates.append(d)
            dates.sort(reverse=True)

            if not dates: continue

            local_dd_date = ft.Dropdown(
                options=[ft.dropdown.Option(d.strftime("%d/%m/%Y")) for d in dates],
                value=dates[0].strftime("%d/%m/%Y") if dates else None,
                expand=True, height=40, text_size=12, content_padding=10, border_radius=6,
                border_color=current_theme.divider_color, bgcolor=current_theme.surface_color, color=current_theme.text_main,
                menu_height=250
            )

            def create_select_handler(current_tkb, dd):
                def on_click(e):
                    self.selected_tkb = current_tkb
                    self.selected_date = dd.value
                    self.info_lop_text.value = current_tkb.get("lop", {}).get("tenlop", "N/A")
                    self.info_mon_text.value = current_tkb.get("hocphan", {}).get("tenhocphan", "N/A")
                    self.info_ngay_text.value = self.selected_date
                    
                    # LƯU VÀO SESSION ĐỂ TỰ ĐỘNG LOAD LẠI KHI QUAY VỀ
                    self.app_page.session.store.set("saved_selected_tkb", current_tkb)
                    self.app_page.session.store.set("saved_selected_date", dd.value)
                    
                    self.close_schedule_dialog()
                    self.app_page.run_task(self.execute_load_students)
                return on_click

            btn_confirm = ft.Button(
                content=ft.Text("Xác nhận", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                bgcolor=current_theme.accent, height=40,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=create_select_handler(tkb, local_dd_date)
            )

            action_row = ft.ResponsiveRow([
                ft.Column([local_dd_date], col={"xs": 12, "sm": 8}),
                ft.Column([btn_confirm], col={"xs": 12, "sm": 4}, alignment=ft.MainAxisAlignment.CENTER)
            ], run_spacing=8)

            card = ft.Container(
                padding=15, border_radius=10, border=ft.Border.all(1, current_theme.divider_color), bgcolor=current_theme.surface_variant,
                content=ft.Column([
                    ft.Text(ten_mon, weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"Lớp: {ten_lop} - {hk_info}", size=12, color=current_theme.text_muted, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Divider(height=1, color=current_theme.divider_color),
                    action_row
                ], spacing=8)
            )
            self.schedule_list_ui.controls.append(card)

        if getattr(self, "page", None): self.schedule_dialog.update()

    def open_schedule_dialog(self, e=None):
        self.schedule_dialog.open = True
        self.app_page.update()

    def close_schedule_dialog(self):
        self.schedule_dialog.open = False
        self.app_page.update()

    def show_student_details(self, sv, index):
        ho_ten = f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip()
        status = sv.get("trang_thai_diem_danh", "Chưa điểm danh")
        color_status = ft.Colors.GREEN_600 if status == "Có mặt" else ft.Colors.RED_500 if status == "Vắng" else ft.Colors.ORANGE_500

        self.student_detail_content.controls = [
            ft.Row([
                ft.Container(content=ft.Text(str(index), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), width=40, height=40, border_radius=20, bgcolor=current_theme.accent, alignment=ft.Alignment.CENTER),
                ft.Column([
                    ft.Text(ho_ten, weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"Mã SV: {sv['id']}", size=12, color=current_theme.text_muted),
                ], spacing=2, expand=True)
            ], spacing=15),
            ft.Divider(height=10, color=current_theme.divider_color),
            ft.Text(f"• Giới tính: {sv.get('gioitinh', 'N/A')}", size=13, color=current_theme.text_main),
            ft.Text(f"• Ngày sinh: {sv.get('ngaysinh', 'N/A')}", size=13, color=current_theme.text_main),
            ft.Text(f"• Ghi chú: {sv.get('ghichu', 'Không có')}", size=13, color=current_theme.text_main),
            ft.Container(height=5),
            ft.Row([
                ft.Text("Trạng thái:", size=13, weight=ft.FontWeight.W_500, color=current_theme.text_main),
                ft.Text(status, color=color_status, size=14, weight=ft.FontWeight.BOLD)
            ])
        ]
        self.student_detail_dialog.open = True
        self.app_page.update()

    def close_student_dialog(self):
        self.student_detail_dialog.open = False
        self.app_page.update()

    def show_skeleton_loading(self):
        self.list_view.controls.clear()
        for _ in range(min(self.current_limit, 10)):
            self.list_view.controls.append(
                ft.Container(
                    col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                    bgcolor=current_theme.surface_variant, border_radius=12, padding=10, border=ft.Border.all(1, current_theme.divider_color),
                    content=ft.Row([
                        ft.Container(width=36, height=36, border_radius=18, bgcolor=current_theme.divider_color),
                        ft.Column([ft.Container(width=100, height=14, bgcolor=current_theme.divider_color, border_radius=4), ft.Container(width=60, height=12, bgcolor=current_theme.divider_color, border_radius=4)], spacing=4, expand=True),
                        ft.Container(width=20, height=20, border_radius=10, bgcolor=current_theme.divider_color)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
            )
        if getattr(self, "page", None): self.app_page.update()

    async def execute_load_students(self):
        if not self.selected_tkb or not self.selected_date: return
        try:
            self.show_skeleton_loading()
            date_obj = datetime.datetime.strptime(self.selected_date, "%d/%m/%Y").date()
            thu = date_obj.weekday() + 2
            tkb_id = self.selected_tkb["id"]
            lop_id = self.selected_tkb["lop_id"]

            # Singleton client
            client = await get_supabase_client()

            res_tiet = await client.get("/tkb_tiet", params={"select": "id", "tkb_id": f"eq.{tkb_id}", "thu": f"eq.{thu}"})
            res_tiet.raise_for_status()
            tkb_tiet_id = res_tiet.json()[0]["id"] if res_tiet.json() else None
            if not tkb_tiet_id: raise Exception("Không tìm thấy tiết học cho ngày này!")

            # Fetch sinh viên và điểm danh song song
            res_sv, res_dd = await asyncio.gather(
                client.get("/sinhvien", params={"select": "*", "class_id": f"eq.{lop_id}", "order": "id.asc"}),
                client.get("/diemdanh", params={"select": "sv_id,trang_thai", "tkb_tiet_id": f"eq.{tkb_tiet_id}", "ngay_diem_danh": f"eq.{date_obj.isoformat()}"}),
                return_exceptions=True
            )

            if not getattr(self, "page", None): return

            res_sv.raise_for_status()
            res_dd.raise_for_status()
            svs = res_sv.json()
            dd_map = {str(d["sv_id"]): d["trang_thai"] for d in res_dd.json()}

            self.all_students_data = []
            for sv in svs:
                sv["trang_thai_diem_danh"] = dd_map.get(str(sv["id"]), "Chưa điểm danh")
                self.all_students_data.append(sv)

            self.current_limit = int(self.dd_row_limit.value)
            self.render_table()
            
            # MỞ KHÓA NÚT BẤM KHI ĐÃ CÓ DANH SÁCH
            self.btn_start_session.disabled = False
            self.btn_start_session_mobile.disabled = False
            
            # Truyền toàn bộ dữ liệu thực sang trang Camera
            self.app_page.session.store.set("current_tkb_tiet_id", str(tkb_tiet_id))
            
            self.app_page.session.store.set("current_attendance_date", date_obj.isoformat()) 
            
            self.app_page.session.store.set("current_student_list", self.all_students_data)
            
            self.app_page.update()

        except Exception as ex:
            if getattr(self, "page", None): self._show_error_snackbar(f"Lỗi: {ex}")

    def render_table(self):
        self.list_view.controls.clear()
        display_data = self.all_students_data[:self.current_limit]

        if not display_data:
            self.list_view.controls.append(ft.Text("Không có dữ liệu sinh viên", italic=True, color=current_theme.text_muted))
        else:
            for index, sv in enumerate(display_data, start=1):
                ho_ten = f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip()
                status = sv.get("trang_thai_diem_danh", "Chưa điểm danh")
                color_status = ft.Colors.GREEN_600 if status == "Có mặt" else ft.Colors.RED_500 if status == "Vắng" else ft.Colors.ORANGE_500

                def create_click_handler(student, idx):
                    return lambda e: self.show_student_details(student, idx)

                card = ft.Container(
                    col={"xs": 12, "sm": 6, "md": 6, "lg": 6, "xl": 4},
                    bgcolor=current_theme.surface_color, border_radius=12, padding=10, border=ft.Border.all(1, current_theme.divider_color),
                    ink=True, on_click=create_click_handler(sv, index),
                    content=ft.Row([
                        ft.Container(content=ft.Text(str(index), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=13), width=36, height=36, border_radius=18, bgcolor=current_theme.accent, alignment=ft.Alignment.CENTER),
                        ft.Column([
                            ft.Text(ho_ten, weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(str(sv["id"]), size=11, color=current_theme.text_muted)
                        ], spacing=2, expand=True),
                        ft.Icon(ft.Icons.CHECK_CIRCLE if status == "Có mặt" else ft.Icons.INFO if status == "Chưa điểm danh" else ft.Icons.CANCEL, color=color_status, size=22)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
                self.list_view.controls.append(card)

        if getattr(self, "page", None): self.app_page.update()

    async def handle_limit_change(self, e):
        self.current_limit = int(self.dd_row_limit.value)
        self.render_table()

    def open_mobile_attendance_sheet(self, e):
        self.attendance_bottom_sheet.open = True
        self.app_page.update()

    async def handle_start_session(self, e):
        if not getattr(self, "page", None): return
        e.control.disabled = True
        e.control.update()
        mode = self.rg_mode.value if hasattr(self, 'rg_mode') else "1"
        prefs = ft.SharedPreferences()
        await prefs.set("attendance_mode", str(mode))
        await self.camera_view.stop_camera()
        await self.app_page.push_route("/user/attendance/session")
        
    async def handle_start_trainning(self, e):
        # is_mobile = (self.app_page.width and self.app_page.width < 768) or self.app_page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        # if is_mobile:
        #     show_alert_dialog( self, "AuEdu Thông báo", ft.Text("Chức năng 'ĐÀO TẠO DỮ LIỆU' chỉ khả dụng trên nền tảng Desktop (Windows/MaxOS)!\nVui lòng liên hệ quản trị nếu khuôn mặt sinh viên không khớp, hoặc bạn có thể dùng AuEdu trên PC để sữ dụng tính năng này.", size=13, color=current_theme.text_main))
        #     return
        if not getattr(self, "page", None): return
        e.control.disabled = True
        e.control.update()
        await self.app_page.push_route("/user/attendance/training")

    async def handle_start_session_mobile(self, e):
        if not getattr(self, "page", None): return
        e.control.disabled = True
        e.control.update()
        mode = self.mobile_rg_mode.value if hasattr(self, 'mobile_rg_mode') else "1"
        prefs = ft.SharedPreferences()
        await prefs.set("attendance_mode", str(mode))
        self.attendance_bottom_sheet.open = False
        self.app_page.update()
        await self.camera_view.stop_camera()
        await self.app_page.push_route("/user/attendance/session")

    async def handle_test_camera(self, e):
        if not getattr(self, "page", None): return
        self.test_progress.visible = True
        self.test_status_text.value = "Đang kết nối cảm biến..."
        self.test_status_text.visible = True
        self.app_page.update()

        async def run_test():
            is_ok = await self.camera_view.test_sensor()
            if not getattr(self, "page", None): return
            self.test_progress.visible = False
            self.test_status_text.value = "Sẵn sàng" if is_ok else "Lỗi kết nối"
            self.test_status_text.color = ft.Colors.GREEN_600 if is_ok else ft.Colors.RED_500
            show_top_notification(self.app_page, "AuEdu", "Camera hoạt động tốt!" if is_ok else "Opps! Có vẻ camera đang lỗi!", color=ft.Colors.GREEN if is_ok else ft.Colors.ORANGE, sound="S" if is_ok else "E")
            try: self.app_page.update()
            except: pass

        self.app_page.run_task(run_test)
        
    async def handle_save_camera(self, e):
        if not self.dd_camera.value:
            return
        prefs = ft.SharedPreferences()
        await prefs.set("selected_camera", str(self.dd_camera.value))
        # Hiển thị thông báo 
        show_top_notification(self.app_page, "AuEdu", "Đã lưu cài đặt Camera mặc định!", color=ft.Colors.GREEN_600, sound=None)
        self.app_page.update()

    def _show_error_snackbar(self, message: str):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.RED_700, open=True))
        self.app_page.update()