import flet as ft
import asyncio
import time
import json
import random
from core.theme import current_theme, get_flat_container
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown
from components.options.top_notification import show_top_notification
from core.config import get_supabase_client
from core.helper import safe_json_load

class FaceTrainingPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = 10

        self.is_desktop = self.app_page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        # --- STATE MANAGEMENT (Bộ nhớ giao diện) ---
        self.gv_id = "N/A"  # Lưu ID giảng viên hiện tại
        self.selected_student = None
        self.captured_frames = []
        self.is_training = False
        self.search_mode_val = "class"
        self.current_class_id = None

        # --- QUẢN LÝ TRẠNG THÁI TIMELINE ---
        self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải"]
        self.step_states = ["pending"] * 3 
        self.step_ui_elements = [] 

        # --- STUDIO COMPONENTS ---
        self.dd_camera = CustomDropdown(label="Nguồn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True, view_mode="training")
        
        self.camera_container = ft.Container(content=self.camera_view, visible=False, expand=True, left=0, right=0, top=0, bottom=0)
        self.black_screen = ft.Container(bgcolor=ft.Colors.BLACK, expand=True, left=0, right=0, top=0, bottom=0)
        
        # ==== UI VIÊN NANG (PILL) THÔNG BÁO TRẠNG THÁI ====
        self.txt_countdown = ft.Text("--", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)
        self.txt_pose_status = ft.Text("Chờ nhận diện...", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)
        
        self.status_pill = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.TIMER, color=ft.Colors.WHITE, size=16),
                self.txt_countdown,
                ft.Container(width=1, height=15, bgcolor=ft.Colors.WHITE_54),
                self.txt_pose_status
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            bgcolor=ft.Colors.RED_500, # Đỏ mặc định
            padding=ft.Padding(15, 8, 15, 8),
            border_radius=20,
            visible=False,
        )
        
        # Wrapper để căn giữa viên nang ở mép dưới Camera
        self.status_pill_wrapper = ft.Container(
            content=ft.Row([self.status_pill], alignment=ft.MainAxisAlignment.CENTER),
            bottom=15, left=0, right=0
        )
        
        # ---- STEP TRAINING ----
        # Khởi tạo 2 Row riêng biệt
        self.step_row_3 = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        self.step_row_6 = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=15, visible=False)
        
        # Gom vào wrapper
        self.step_wrapper = ft.Container(
            content=ft.Column([self.step_row_3, self.step_row_6]), 
            alignment=ft.Alignment(0, 0)
        )
        
        self.training_mode = ft.SegmentedButton(
            selected=["3"], 
            allow_empty_selection=False,
            on_change=self.handle_mode_change_training,
            segments=[
                ft.Segment(value="3", label=ft.Text("Cơ bản (3 góc)", size=11), icon=ft.Icon(ft.Icons.FILTER_3, size=14)),
                ft.Segment(value="6", label=ft.Text("Chuyên sâu (6 góc)", size=11), icon=ft.Icon(ft.Icons.FILTER_6, size=14)),
            ]
        )
        self.step_wrapper = ft.Container(alignment=ft.Alignment(0, 0))

        # --- LEFT PANEL COMPONENTS ---
        self.search_tf = ft.TextField(
            label="Nhập Mã Sinh Viên", hint_text="Nhấn Enter để tìm",
            prefix_icon=ft.Icons.SEARCH,
            suffix=ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, icon_size=14, on_click=self.handle_search_student, tooltip="Tìm kiếm"),
            border_radius=8, height=45, text_size=12, content_padding=10,
            on_submit=self.handle_search_student
        )
        
        self.student_list_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=6)

        self.search_mode = ft.SegmentedButton(
            selected=["class"], 
            allow_empty_selection=False,
            on_change=self.handle_mode_change,
            segments=[
                ft.Segment(value="class", label=ft.Text("Theo Lớp", size=11), icon=ft.Icon(ft.Icons.CLASS_, size=14)),
                ft.Segment(value="mssv", label=ft.Text("Mã SV", size=11), icon=ft.Icon(ft.Icons.PERSON_SEARCH, size=14)),
            ]
        )

        self.btn_start = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.FACE_RETOUCHING_NATURAL, color=ft.Colors.WHITE, size=18), ft.Text("BẮT ĐẦU ĐÀO TẠO", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=current_theme.accent, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self.start_training, disabled=True
        )

        self.step_indicator_row = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=15)
        self.step_wrapper = ft.Container(content=self.step_indicator_row, alignment=ft.Alignment(0, 0))

        self.content = self.build_desktop_layout() if self.is_desktop else self.build_mobile_warning()

    def did_mount(self):
        if self.is_desktop:
            self.app_page.run_task(self.camera_view.load_available_cameras)
            self.step_indicator_row.controls = self.build_step_indicators()
            # Bắt đầu khởi tạo trang và gọi API
            self.app_page.run_task(self.initialize_page)
            self.update()
            
    async def initialize_page(self):
        # Lấy session giảng viên đang đăng nhập
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")
            
        await self.load_classes()

    def will_unmount(self):
        if self.is_desktop:
            self.app_page.run_task(self.camera_view.stop_camera)

    # ══════════════════════════════════════════════════════════════════
    # APPLY THEME - ĐỒNG BỘ THEME MƯỢT MÀ KHÔNG TẢI LẠI TRANG
    # ══════════════════════════════════════════════════════════════════
    def apply_theme(self):
        self.bgcolor = current_theme.bg_color
        self.btn_start.bgcolor = current_theme.accent
        self.step_indicator_row.controls = self.build_step_indicators()
        self._update_step_ui()
        self.content = self.build_desktop_layout() if self.is_desktop else self.build_mobile_warning()
        
        # Phục hồi giao diện
        if self.search_mode_val == "class":
            if self.current_class_id is None:
                self.app_page.run_task(self.load_classes)
            else:
                self.app_page.run_task(self.load_students_by_class, self.current_class_id)
        else:
            self.app_page.run_task(self.handle_search_student, None)

    # ══════════════════════════════════════════════════════════════════
    # BUILD LAYOUT
    # ══════════════════════════════════════════════════════════════════
    def build_mobile_warning(self):
        return ft.Column(
            controls=[
            ft.Icon(ft.Icons.DESKTOP_MAC, size=80, color=current_theme.secondary),
            ft.Text("Tính năng này chỉ hỗ trợ trên PC!", size=18, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
            ft.Text("Vui lòng sữ dụng AuEdu trên nền tảng Desktop (Windows/MacOS).", color=current_theme.text_main, text_align=ft.TextAlign.CENTER, size=12),
            ft.Divider(height=10, color=current_theme.divider_color),
            ft.Container(height=150),
            ft.Text("Bạn đang gặp vấn đề?", size=13, weight=ft.FontWeight.BOLD, color=current_theme.text_muted, text_align=ft.TextAlign.LEFT),
            ft.Text("› Khuôn mặt sinh viên không khớp?\n› Không có dữ liệu nhận dạng cho sinh viên?\n› Hệ thống bị nghẽn hoặc treo? ...", size=13, color=current_theme.text_muted, text_align=ft.TextAlign.LEFT ),
            ft.Text("››› Vui lòng kết nối lại nếu mạng chập chờn hoặc liên hệ phòng QLSV/ Quản trị hệ thống để xử lý kịp thời!", size=13, color=current_theme.text_muted, text_align=ft.TextAlign.LEFT ),
            ], 
            alignment=ft.MainAxisAlignment.CENTER, 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        

    def build_desktop_layout(self):
        top_bar = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/attendance"), icon_size=20),
            ft.Text("Về lại trang điểm danh", weight=ft.FontWeight.BOLD, size=13, color=current_theme.text_main)
        ])

        self.tab_content = ft.Container(content=self.student_list_ui, expand=True, padding=5)
        
        left_panel = ft.Container(
            width=330, padding=15, border_radius=12, bgcolor=current_theme.surface_color,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Column([
                ft.Text("CHỌN SINH VIÊN", weight=ft.FontWeight.BOLD, size=14, color=current_theme.secondary),
                ft.Row([self.search_mode], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=2),
                self.tab_content
            ])
        )

        right_panel = ft.Container(
            expand=True, padding=10, border_radius=12, bgcolor=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Column([
                ft.Row([
                    ft.Text("CAMERA NHẬN DIỆN", weight=ft.FontWeight.BOLD, size=14, color=current_theme.secondary),
                    ft.Row([
                        self.training_mode, 
                        ft.Container(content=self.dd_camera, width=150)
                    ], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    expand=True, border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border=ft.Border.all(3, current_theme.secondary),
                    content=ft.Stack([
                        self.black_screen,     
                        self.camera_container,  
                        ft.Container(
                            alignment=ft.Alignment(0, 0),
                            content=ft.Container(
                                width=550, height=420, border_radius=210, 
                                border=ft.Border.all(2, ft.Colors.WHITE_54) 
                            )
                        ),
                        self.status_pill_wrapper
                    ])
                ),
                
                ft.Container(height=5),
                self.step_wrapper, 
                ft.Container(height=5),
                self.btn_start
            ])
        )

        return ft.Column([top_bar, ft.Row([left_panel, right_panel], expand=True, spacing=15)])

    def build_step_indicators(self):
        self.step_ui_elements.clear()
        indicators = []
        for i, text in enumerate(self.step_texts):
            step_circle = ft.Container(
                content=ft.Text(str(i+1), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=11),
                width=30, height=30, border_radius=15, 
                bgcolor=ft.Colors.BLACK_54,
                alignment=ft.Alignment(0, 0), 
                animate=ft.Animation(300, "easeInOut")
            )
            step_col = ft.Column([
                step_circle,
                ft.Text(text, size=11, color=current_theme.text_muted)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            
            self.step_ui_elements.append((step_circle, step_col.controls[1]))
            indicators.append(step_col)
            
        return indicators

    def _update_step_ui(self):
        for i, (circle, text_ui) in enumerate(self.step_ui_elements):
            state = self.step_states[i]
            
            if state == "pending":
                circle.bgcolor = ft.Colors.BLACK_54
                circle.content = ft.Text(str(i+1), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=11)
                text_ui.color = current_theme.text_muted
                text_ui.weight = ft.FontWeight.NORMAL
            
            elif state == "active":
                circle.bgcolor = current_theme.accent
                circle.content = ft.Text(str(i+1), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=11)
                text_ui.color = current_theme.secondary
                text_ui.weight = ft.FontWeight.BOLD
                
            elif state == "success":
                circle.bgcolor = ft.Colors.YELLOW_700
                circle.content = ft.Icon(ft.Icons.CHECK, color=ft.Colors.BLACK, size=16)
                text_ui.color = ft.Colors.YELLOW_700
                text_ui.weight = ft.FontWeight.BOLD
                
            elif state == "error":
                circle.bgcolor = ft.Colors.RED_500
                circle.content = ft.Icon(ft.Icons.CLOSE, color=ft.Colors.WHITE, size=16)
                text_ui.color = ft.Colors.RED_500
                text_ui.weight = ft.FontWeight.BOLD

        self.update()

    def handle_mode_change_training(self, e):
        mode = list(e.control.selected)[0]
        
        if mode == "6":
            self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải", "Cười tươi", "Nhắm mắt", "Nghiêng đầu"]
        else:
            self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải"]
            
        self.step_states = ["pending"] * len(self.step_texts)
        
        # 1. Tạo một Row hoàn toàn mới mỗi khi đổi mode
        new_row = ft.Row(
            controls=self.build_step_indicators(),
            wrap=True, 
            alignment=ft.MainAxisAlignment.CENTER, 
            spacing=15
        )
        
        # 2. Gán thẳng Row mới vào content của Wrapper
        self.step_wrapper.content = new_row
        self._update_step_ui()
        
        if getattr(self, "page", None):
            self.step_wrapper.update()

    # ══════════════════════════════════════════════════════════════════
    # LOGIC CHỌN SINH VIÊN (KẾT HỢP MEMORY STATE)
    # ══════════════════════════════════════════════════════════════════
    def handle_mode_change(self, e):
        self.search_mode_val = list(e.control.selected)[0]
        self.student_list_ui.controls.clear()
        if self.search_mode_val == "class":
            self.tab_content.content = self.student_list_ui
            self.app_page.run_task(self.load_classes)
        else:
            self.tab_content.content = ft.Column([self.search_tf, self.student_list_ui], expand=True)
        self.update()

    def load_dummy_classes(self):
        self.current_class_id = None # Xóa trạng thái lớp hiện tại
        self.student_list_ui.controls.clear()
        classes = [{"id": 1, "name": "D20CQCN01-N", "siso": 50}, {"id": 2, "name": "D20CQAT01-N", "siso": 45}]
        for c in classes:
            self.student_list_ui.controls.append(
                ft.Card(
                    elevation=1, margin=0,
                    content=ft.Container(
                        bgcolor=current_theme.surface_color, border_radius=8, padding=2,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER_SHARED, color=current_theme.secondary, size=20),
                            title=ft.Text(c["name"], weight=ft.FontWeight.BOLD, size=13),
                            subtitle=ft.Text(f"Sĩ số: {c['siso']} sinh viên", size=11),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16),
                            on_click=lambda e, cid=c["id"]: self.load_students_by_class(cid)
                        )
                    )
                )
            )
        self.update()


    def _render_student_cards(self, svs):
        for sv in svs:
            status_color = ft.Colors.GREEN_600 if sv["has_data"] else ft.Colors.RED_500
            status_text = "Đã có dữ liệu" if sv["has_data"] else "Chưa có dữ liệu"
            
            # Ghi nhớ viền Highlight nếu sinh viên đang được chọn (để không bị mất khi đổi Theme)
            is_selected = self.selected_student and self.selected_student["id"] == sv["id"]
            border_style = ft.Border.all(2, current_theme.accent) if is_selected else ft.Border.all(1, ft.Colors.TRANSPARENT)
            
            card = ft.Container(
                padding=8, border_radius=6, border=border_style,
                bgcolor=current_theme.surface_color,
                on_click=lambda e, s=sv: self.select_student(s, e.control),
                content=ft.Row([
                    ft.CircleAvatar(content=ft.Text(sv["name"][0], size=14), bgcolor=current_theme.surface_variant, color=current_theme.secondary, radius=16),
                    ft.Column([
                        ft.Text(sv["name"], weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(sv["id"], size=11, color=current_theme.text_muted)
                    ], expand=True, spacing=2),
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=6, vertical=3), border_radius=10, bgcolor=status_color,
                        content=ft.Text(status_text, size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
                    )
                ])
            )
            self.student_list_ui.controls.append(card)
        self.update()

    def select_student(self, sv, control):
        for c in self.student_list_ui.controls:
            if isinstance(c, ft.Container): c.border = ft.Border.all(1, ft.Colors.TRANSPARENT)
        
        control.border = ft.Border.all(2, current_theme.accent)
        self.selected_student = sv
        self.btn_start.disabled = False
        show_top_notification(self.app_page, "Đã chọn", f"Sinh viên: {sv['name']}", ft.Colors.BLUE_600)
        self.update()

    # ══════════════════════════════════════════════════════════════════
    # LOGIC ĐÀO TẠO THEO TIMELINE
    # ══════════════════════════════════════════════════════════════════
    async def start_training(self, e):
        self.is_training = True
        self.captured_frames.clear()
        self.btn_start.disabled = True
        self.training_mode.disabled = True 
        
        self.camera_container.visible = True
        self.black_screen.visible = False
        self.status_pill.visible = True # Bật hiển thị viên nang
        self.update()
        
        await self.camera_view.start_camera()
        await asyncio.sleep(1)

        target_frames = len(self.step_texts)
        for i in range(target_frames):
            requested_pose = self.step_texts[i]
            self.step_states[i] = "active"
            self._update_step_ui()
            
            # Đổi chữ ở nút to bên dưới cho rõ ràng
            self.btn_start.content = ft.Text(f"ĐANG XỬ LÝ: {requested_pose.upper()}", weight="bold", color="white", size=13)
            self.update()
            
            is_matched = False
            timeout = 15 
            start_wait = time.time()
            
            while not is_matched:
                current_pose = getattr(self.camera_view, "current_pose", "N/A")
                
                # ==== KIỂM TRA TƯ THẾ ====
                if current_pose == requested_pose:
                    # Chuyển viên nang sang màu Primary (Xanh/Cam tùy theme)
                    self.status_pill.bgcolor = current_theme.accent
                    self.txt_pose_status.value = f"Tuyệt vời! Giữ nguyên"
                    self.update()
                    
                    # Vòng lặp đếm ngược 1s liên tục kiểm tra lại tư thế
                    for countdown in range(1, 0, -1):
                        self.txt_countdown.value = f"{countdown}s"
                        self.update()
                        
                        cp = getattr(self.camera_view, "current_pose", "N/A")
                        if cp != requested_pose:
                            break # Nếu mặt bị lệch trong lúc đếm -> Hủy đếm ngược
                        await asyncio.sleep(0.5)
                    else:
                        # Nếu vòng for chạy mượt mà không bị break => Hoàn thành!
                        is_matched = True
                else:
                    # Sai tư thế -> Viên nang Đỏ
                    self.status_pill.bgcolor = ft.Colors.RED_500
                    self.txt_pose_status.value = f"Đang thấy: {current_pose}"
                    self.txt_countdown.value = "--"
                    self.update()
                
                if not is_matched:
                    if time.time() - start_wait > timeout:
                        show_top_notification(self.app_page, "Hết thời gian", f"Không nhận diện được {requested_pose}", ft.Colors.ORANGE_500, sound="E")
                        break
                    await asyncio.sleep(0.2)

            # CHỤP ẢNH KHI MATCH
            if is_matched:
                base64_frame = await self.camera_view.get_current_frame_base64()
                if base64_frame:
                    self.captured_frames.append(base64_frame)
                    self.step_states[i] = "success"
                    show_top_notification(self.app_page, "Đã bắt", requested_pose, ft.Colors.GREEN_600, sound="S")
                else:
                    self.step_states[i] = "error"
            else:
                self.step_states[i] = "error"

            self._update_step_ui()
            await asyncio.sleep(0.5)

        # GỬI LÊN DATABASE
        try:
            client = await get_supabase_client()
            res = await client.post("/training/face/enroll", json={
                "sv_id": self.selected_student["id"],
                "gv_id": self.gv_id,
                "images": self.captured_frames
            })
            res.raise_for_status()
            
            self.selected_student["has_data"] = True
            prefs = ft.SharedPreferences()
            
            if self.search_mode_val == "class" and self.current_class_id:
                await prefs.remove(f"cache_training_sv_{self.current_class_id}")
                await self.load_students_by_class(self.current_class_id)
            elif self.search_mode_val == "mssv":
                await self.handle_search_student(None)
                
            show_top_notification(self.app_page, "Thành công", "Dữ liệu đã được cập nhật!", ft.Colors.BLUE_600, sound="S")
            
        except Exception as ex:
            show_top_notification(self.app_page, "AuEdu - Lỗi API", str(ex), ft.Colors.RED_500, sound="E")

        # ==========================================
        # PHỤC HỒI GIAO DIỆN SAU KHI KẾT THÚC
        # ==========================================
        await self.camera_view.stop_camera()
        self.camera_container.visible = False
        self.black_screen.visible = True
        self.status_pill.visible = False
        
        self.btn_start.disabled = False
        self.training_mode.disabled = False
        
        # 1. Reset mảng trạng thái về Pending
        self.step_states = ["pending"] * len(self.step_texts)
        self._update_step_ui()
        
        # 2. Đổi lại chữ và Icon cho nút bấm ban đầu
        self.btn_start.content = ft.Row([
            ft.Icon(ft.Icons.FACE_RETOUCHING_NATURAL, color=ft.Colors.WHITE, size=18), 
            ft.Text("BẮT ĐẦU ĐÀO TẠO", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        self.update()
        
    # ══════════════════════════════════════════════════════════════════
    # API FETCH LỚP & SINH VIÊN KÈM CACHE (1 NGÀY = 86400s)
    # ══════════════════════════════════════════════════════════════════
    async def load_classes(self):
        if self.gv_id == "N/A": return
        self.current_class_id = None
        self.student_list_ui.controls.clear()
        
        prefs = ft.SharedPreferences()
        cache_key_data = f"cache_training_class_{self.gv_id}"
        cache_key_time = f"last_sync_training_class_{self.gv_id}"
        
        cached_data_str = await prefs.get(cache_key_data)
        last_sync_str = await prefs.get(cache_key_time)
        current_time = time.time()
        
        classes_data = []
        
        # 1. Kiểm tra Cache (86400 giây = 24 giờ)
        if cached_data_str and last_sync_str and (current_time - float(last_sync_str) < 86400):
            classes_data = safe_json_load(cached_data_str)
        else:
            # 2. Gọi API nếu không có cache hoặc hết hạn
            try:
                client = await get_supabase_client()
                res = await client.get(f"/training/giangvien/{self.gv_id}/lophoc")
                res.raise_for_status()
                classes_data = res.json()
                
                # Lưu Cache
                await prefs.set(cache_key_data, json.dumps(classes_data))
                await prefs.set(cache_key_time, str(current_time))
            except Exception as e:
                print(f"Lỗi load lớp (Face Training): {e}")
                if cached_data_str: classes_data = safe_json_load(cached_data_str)
        
        # 3. Render giao diện
        for c in classes_data:
            self.student_list_ui.controls.append(
                ft.Card(
                    elevation=1, margin=0,
                    content=ft.Container(
                        bgcolor=current_theme.surface_color, border_radius=8, padding=2,
                        content=ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER_SHARED, color=current_theme.secondary, size=20),
                            title=ft.Text(c.get("name", "N/A"), weight=ft.FontWeight.BOLD, size=13),
                            subtitle=ft.Text(f"Mã Lớp: {c.get('id', '')}", size=11),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16),
                            on_click=lambda e, cid=c["id"]: self.app_page.run_task(self.load_students_by_class, cid)
                        )
                    )
                )
            )
        self.update()

    async def load_students_by_class(self, class_id):
        self.current_class_id = class_id
        self.student_list_ui.controls.clear()
        self.student_list_ui.controls.append(
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=14), ft.Text("Quay lại danh sách", size=12)]),
                on_click=lambda e: self.app_page.run_task(self.load_classes), style=ft.ButtonStyle(padding=5)
            )
        )
        self.update()
        
        prefs = ft.SharedPreferences()
        cache_key_data = f"cache_training_sv_{class_id}"
        cache_key_time = f"last_sync_training_sv_{class_id}"
        
        cached_data_str = await prefs.get(cache_key_data)
        last_sync_str = await prefs.get(cache_key_time)
        current_time = time.time()
        
        students_data = []
        
        if cached_data_str and last_sync_str and (current_time - float(last_sync_str) < 86400):
            students_data = safe_json_load(cached_data_str)
        else:
            try:
                client = await get_supabase_client()
                res = await client.get(f"/training/lop/{class_id}/sinhvien")
                res.raise_for_status()
                students_data = res.json()
                
                await prefs.set(cache_key_data, json.dumps(students_data))
                await prefs.set(cache_key_time, str(current_time))
            except Exception as e:
                print(f"Lỗi load sinh viên (Face Training): {e}")
                if cached_data_str: students_data = safe_json_load(cached_data_str)
                
        self._render_student_cards(students_data)

    async def handle_search_student(self, e):
        keyword = self.search_tf.value
        if not keyword or self.gv_id == "N/A": return
        
        self.student_list_ui.controls.clear()
        self.student_list_ui.controls.append(
            ft.Row([ft.ProgressRing(width=20, height=20, color=current_theme.accent), ft.Text("Đang tìm...", size=12)], alignment=ft.MainAxisAlignment.CENTER)
        )
        self.update()
        
        # Tìm kiếm thì không nên lưu cache lâu vì phụ thuộc vào từ khóa gõ
        try:
            client = await get_supabase_client()
            res = await client.get(f"/training/giangvien/{self.gv_id}/timkiem", params={"keyword": keyword})
            res.raise_for_status()
            students_data = res.json()
            
            self.student_list_ui.controls.clear()
            if not students_data:
                self.student_list_ui.controls.append(ft.Text("Không tìm thấy sinh viên nào.", italic=True, size=12, color=current_theme.text_muted))
            else:
                self._render_student_cards(students_data)
        except Exception as ex:
            print(f"Lỗi tìm kiếm: {ex}")
            self.student_list_ui.controls.clear()
            self.student_list_ui.controls.append(ft.Text("Có lỗi xảy ra khi tìm kiếm.", color=ft.Colors.RED_500, size=12))
            
        self.update()