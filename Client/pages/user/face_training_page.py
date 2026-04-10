import flet as ft
import asyncio
import random
from core.theme import current_theme, get_flat_container
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown
from components.options.top_notification import show_top_notification

class FaceTrainingPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = 10

        self.is_desktop = self.app_page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        # --- STATE MANAGEMENT (Bộ nhớ giao diện) ---
        self.selected_student = None
        self.captured_frames = []
        self.is_training = False
        self.search_mode_val = "class"
        self.current_class_id = None # Ghi nhớ lớp đang xem để rebuild Theme mượt mà

        # --- QUẢN LÝ TRẠNG THÁI TIMELINE ---
        self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải"]
        self.step_states = ["pending"] * 3 
        self.step_ui_elements = [] 

        # --- STUDIO COMPONENTS ---
        self.dd_camera = CustomDropdown(label="Nguồn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True)
        
        self.camera_container = ft.Container(content=self.camera_view, visible=False, expand=True)
        self.black_screen = ft.Container(bgcolor=ft.Colors.BLACK, expand=True)
        
        self.dd_training_mode = ft.Dropdown(
            label="Chế độ đào tạo",
            options=[
                ft.dropdown.Option("3", "Cơ bản (3 góc)"),
                ft.dropdown.Option("6", "Chuyên sâu (6 góc)")
            ],
            value="3",
            width=180,
            height=45,
            text_size=12,
            border_radius=8
        )
        self.dd_training_mode.on_change = self.handle_mode_change_training

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
            self.load_dummy_classes() 
            self.step_indicator_row.controls = self.build_step_indicators()
            self.update()

    def will_unmount(self):
        if self.is_desktop:
            self.app_page.run_task(self.camera_view.stop_camera)

    # ══════════════════════════════════════════════════════════════════
    # APPLY THEME - ĐỒNG BỘ THEME MƯỢT MÀ KHÔNG TẢI LẠI TRANG
    # ══════════════════════════════════════════════════════════════════
    def apply_theme(self):
        # 1. Cập nhật nền chính & nút bấm
        self.bgcolor = current_theme.bg_color
        self.btn_start.bgcolor = current_theme.accent
        
        # 2. Xây dựng lại giao diện tĩnh với màu mới
        self.step_indicator_row.controls = self.build_step_indicators()
        self._update_step_ui()
        self.content = self.build_desktop_layout() if self.is_desktop else self.build_mobile_warning()
        
        # 3. Phục hồi danh sách sinh viên theo trạng thái đã nhớ (Memory State)
        if self.search_mode_val == "class":
            if self.current_class_id is None:
                self.load_dummy_classes()
            else:
                self.load_students_by_class(self.current_class_id)
        else:
            self.handle_search_student(None)
            
        self.update()

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
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: self.app_page.push_route("/user/attendance"), icon_size=20),
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
                        self.dd_training_mode, 
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
                        )
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
        if self.dd_training_mode.value == "6":
            self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải", "Cười tươi", "Nhắm mắt", "Nghiêng đầu"]
        else:
            self.step_texts = ["Trực diện", "Nghiêng Trái", "Nghiêng Phải"]
        
        self.step_states = ["pending"] * len(self.step_texts)
        self.step_indicator_row.controls = self.build_step_indicators()
        self._update_step_ui()
        self.update()

    # ══════════════════════════════════════════════════════════════════
    # LOGIC CHỌN SINH VIÊN (KẾT HỢP MEMORY STATE)
    # ══════════════════════════════════════════════════════════════════
    def handle_mode_change(self, e):
        self.search_mode_val = list(e.control.selected)[0]
        self.student_list_ui.controls.clear()
        if self.search_mode_val == "class":
            self.tab_content.content = self.student_list_ui
            self.load_dummy_classes()
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

    def load_students_by_class(self, class_id):
        self.current_class_id = class_id # Lưu vào State để rebuild
        self.student_list_ui.controls.clear()
        self.student_list_ui.controls.append(
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=14), ft.Text("Quay lại danh sách", size=12)]),
                on_click=lambda e: self.load_dummy_classes(), style=ft.ButtonStyle(padding=5)
            )
        )
        
        svs = [
            {"id": "N20DCCN001", "name": "Nguyễn Văn A", "has_data": True},
            {"id": "N20DCCN002", "name": "Trần Thị B", "has_data": False}
        ]
        self._render_student_cards(svs)

    def handle_search_student(self, e):
        sv_id = self.search_tf.value
        if not sv_id: return
        self.student_list_ui.controls.clear()
        svs = [{"id": sv_id, "name": "Bé Mèo Nhỏ", "has_data": False}]
        self._render_student_cards(svs)

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
                        padding=ft.padding.symmetric(horizontal=6, vertical=3), border_radius=10, bgcolor=status_color,
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
        self.dd_training_mode.disabled = True 
        
        self.step_states = ["pending"] * len(self.step_texts)
        self._update_step_ui()
        
        self.black_screen.visible = False
        self.camera_container.visible = True
        self.update()
        
        await self.camera_view.start_camera()
        
        target_frames = len(self.step_texts)
        for i in range(target_frames):
            self.step_states[i] = "active"
            self._update_step_ui()
            self.btn_start.content = ft.Text(f"ĐANG CHỤP: {self.step_texts[i].upper()} (3s)", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)
            self.update()
            
            await asyncio.sleep(2.5) 
            
            self.btn_start.content = ft.Row([ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE, stroke_width=2), ft.Text(f"ĐANG XỬ LÝ ẢNH...", color=ft.Colors.WHITE, size=13)], alignment=ft.MainAxisAlignment.CENTER)
            self.update()
            
            await asyncio.sleep(1.0) 
            self.captured_frames.append("base64_frame_data")
            
            if random.random() < 0.15:
                self.step_states[i] = "error"
                show_top_notification(self.app_page, "Lỗi góc ảnh", f"Góc {self.step_texts[i]} bị mờ, hệ thống sẽ bỏ qua!", ft.Colors.RED_500, sound="E")
            else:
                self.step_states[i] = "success"
                show_top_notification(self.app_page, "Thành công", f"Đã quét góc: {self.step_texts[i]}", ft.Colors.GREEN_600, sound="S")
            
            self._update_step_ui()

        self.btn_start.content = ft.Row([ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE, stroke_width=2), ft.Text("ĐANG CẬP NHẬT DATABASE...", color=ft.Colors.WHITE, size=13)], alignment=ft.MainAxisAlignment.CENTER)
        self.update()
        
        await self.camera_view.stop_camera()
        
        self.camera_container.visible = False
        self.black_screen.visible = True
        
        await asyncio.sleep(1.5) 
        
        show_top_notification(self.app_page, "Hoàn tất", f"Quá trình đào tạo kết thúc cho {self.selected_student['name']}", ft.Colors.GREEN_600, sound="S")
        
        self.btn_start.content = ft.Row([ft.Icon(ft.Icons.FACE_RETOUCHING_NATURAL, color=ft.Colors.WHITE, size=18), ft.Text("BẮT ĐẦU LẠI", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)], alignment=ft.MainAxisAlignment.CENTER)
        self.btn_start.disabled = False
        self.dd_training_mode.disabled = False
        self.is_training = False
        self.update()