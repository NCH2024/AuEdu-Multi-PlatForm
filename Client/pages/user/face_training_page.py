import flet as ft
import asyncio
import time
import json
import base64
import cv2
import numpy as np
from core.theme import current_theme
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown
from components.options.top_notification import show_top_notification
from core.config import get_supabase_client
from core.helper import safe_json_load

# FIQA Threshold – consistent với Server-side config
# Client mặc định 0.05 nếu không set trong .env
import os as _os
FIQA_THRESHOLD = float(_os.getenv("FIQA_THRESHOLD", "0.05"))

class FaceTrainingPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = 10

        self.is_desktop = self.app_page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]

        # --- STATE MANAGEMENT ---
        self.gv_id = "N/A"
        self.selected_student = None
        self.captured_frames = []
        self.is_training = False
        self.search_mode_val = "class"
        self.current_class_id = None
        self.target_frames = 15 # Thu thập 15 ảnh (Mean Aggregation)

        # --- STUDIO COMPONENTS ---
        self.dd_camera = CustomDropdown(label="Nguồn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True, view_mode="training")
        
        self.camera_container = ft.Container(content=self.camera_view, visible=False, expand=True, left=0, right=0, top=0, bottom=0)
        self.black_screen = ft.Container(bgcolor=ft.Colors.BLACK, expand=True, left=0, right=0, top=0, bottom=0)
        
        # UI Hướng dẫn (Alignment Guide)
        # Sử dụng BoxShadow siêu lớn để tạo lớp phủ mờ có lỗ thủng (Oval) ở giữa
        self.alignment_guide = ft.Container(
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=300, height=400, 
                border_radius=150, # Tạo hình Oval
                border=ft.Border.all(3, ft.Colors.GREEN_400),
                shadow=ft.BoxShadow(
                    spread_radius=3000,
                    blur_radius=0,
                    color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK)
                )
            ),
            left=0, right=0, top=0, bottom=0,
            visible=False
        )
        
        self.txt_status = ft.Text("Vui lòng nhìn thẳng và giữ yên khuôn mặt", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=15)
        self.txt_progress = ft.Text("0/15", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400, size=18)
        
        self.status_pill = ft.Container(
            content=ft.Column([
                self.txt_status,
                ft.Row([ft.Icon(ft.Icons.CAMERA, color=ft.Colors.WHITE), self.txt_progress], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            padding=ft.Padding(15, 10, 15, 10),
            border_radius=15,
            visible=False,
        )
        
        self.status_pill_wrapper = ft.Container(
            content=ft.Row([self.status_pill], alignment=ft.MainAxisAlignment.CENTER),
            bottom=20, left=0, right=0
        )

        # --- LEFT PANEL COMPONENTS ---
        self.search_tf = ft.TextField(
            label="Nhập Mã Sinh Viên", hint_text="Nhấn Enter để tìm",
            prefix_icon=ft.Icons.SEARCH,
            suffix=ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, icon_size=14, on_click=self.handle_search_student),
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
            content=ft.Row([ft.Icon(ft.Icons.FACE_RETOUCHING_NATURAL, color=ft.Colors.WHITE, size=18), ft.Text("BẮT ĐẦU THU THẬP", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13)], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=current_theme.accent, height=45, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self.start_training, disabled=True
        )
        
        self.txt_current_student = ft.Text("CHƯA CHỌN SINH VIÊN", color=ft.Colors.RED_500, weight=ft.FontWeight.BOLD, size=14)

        self.content = self.build_desktop_layout() if self.is_desktop else self.build_mobile_warning()

    def did_mount(self):
        if self.is_desktop:
            self.app_page.run_task(self.camera_view.load_available_cameras)
            self.app_page.run_task(self.initialize_page)
            self.update()
            
    async def initialize_page(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")
            
        await self.load_classes()

    def will_unmount(self):
        if self.is_desktop:
            self.app_page.run_task(self.camera_view.stop_camera)

    def apply_theme(self):
        self.bgcolor = current_theme.bg_color
        self.btn_start.bgcolor = current_theme.accent
        self.content = self.build_desktop_layout() if self.is_desktop else self.build_mobile_warning()
        if self.search_mode_val == "class":
            if self.current_class_id is None:
                self.app_page.run_task(self.load_classes)
            else:
                self.app_page.run_task(self.load_students_by_class, self.current_class_id)
        else:
            self.app_page.run_task(self.handle_search_student, None)

    def build_mobile_warning(self):
        return ft.Column(
            controls=[
            ft.Icon(ft.Icons.DESKTOP_MAC, size=80, color=current_theme.secondary),
            ft.Text("Tính năng này chỉ hỗ trợ trên PC!", size=18, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
            ft.Text("Vui lòng sử dụng AuEdu trên nền tảng Desktop (Windows/MacOS).", color=current_theme.text_main, text_align=ft.TextAlign.CENTER, size=12),
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
                    ft.Text("CAMERA THU THẬP", weight=ft.FontWeight.BOLD, size=14, color=current_theme.secondary),
                    ft.Container(content=self.dd_camera, width=150)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(
                    expand=True, border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    border=ft.Border.all(3, current_theme.secondary),
                    content=ft.Stack([
                        self.black_screen,     
                        self.camera_container,  
                        self.alignment_guide,
                        self.status_pill_wrapper
                    ])
                ),
                
                ft.Container(height=10),
                ft.Column([
                    ft.Row([ft.Text("Đang chọn:", size=13, color=current_theme.text_muted), self.txt_current_student], alignment=ft.MainAxisAlignment.CENTER),
                    self.btn_start
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ])
        )

        return ft.Column([top_bar, ft.Row([left_panel, right_panel], expand=True, spacing=15)])

    def handle_mode_change(self, e):
        self.search_mode_val = list(e.control.selected)[0]
        self.student_list_ui.controls.clear()
        if self.search_mode_val == "class":
            self.tab_content.content = self.student_list_ui
            self.app_page.run_task(self.load_classes)
        else:
            self.tab_content.content = ft.Column([self.search_tf, self.student_list_ui], expand=True)
        self.update()

    def _render_student_cards(self, svs):
        for sv in svs:
            status_color = ft.Colors.GREEN_600 if sv.get("has_data") else ft.Colors.RED_500
            status_text = "Đã có dữ liệu" if sv.get("has_data") else "Chưa có dữ liệu"
            
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
        
        self.txt_current_student.value = f"{sv['name']} - {sv['id']}"
        self.txt_current_student.color = ft.Colors.GREEN_600
        
        show_top_notification(self.app_page, "Đã chọn", f"Sinh viên: {sv['name']}", ft.Colors.BLUE_600)
        self.update()

    def check_quality(self, base64_str):
        # Hàm kiểm tra chất lượng ảnh dùng OpenCV theo tiêu chuẩn Mean Aggregation tại Client
        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
                
            img_data = base64.b64decode(base64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return False, "Không thể đọc ảnh"

            # Check 1: Độ mờ (Laplacian variance) - Chống rung/Anti-Motion Blur
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            if blur_score / 200.0 < FIQA_THRESHOLD:
                return False, "Ảnh quá mờ – FIQA=%.2f" % (blur_score / 200.0)

            # Check 2: Khoảng cách (Diện tích khuôn mặt)
            # Tích hợp MediaPipe (nếu có)
            try:
                import mediapipe as mp
                mp_face_detection = mp.solutions.face_detection
                with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
                    results = face_detection.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                    if not results.detections:
                        return False, "Không tìm thấy khuôn mặt!"
                    
                    max_area = 0
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        area = bbox.width * bbox.height
                        if area > max_area:
                            max_area = area
                    
                    if max_area < 0.15: # 15% diện tích frame
                        return False, "Vui lòng tiến gần lại camera"
            except ImportError:
                # Nếu client không có mediapipe, có thể giả lập vượt qua check 2 để đảm bảo app luôn chạy
                pass 

            return True, "Ảnh hợp lệ"
        except Exception as e:
            return False, f"Lỗi xử lý cv2: {str(e)}"

    async def start_training(self, e):
        self.is_training = True
        self.captured_frames.clear()
        self.btn_start.disabled = True
        
        self.camera_container.visible = True
        self.black_screen.visible = False
        self.alignment_guide.visible = True
        self.status_pill.visible = True
        self.txt_progress.value = f"0/{self.target_frames}"
        self.update()
        
        await self.camera_view.start_camera()
        await asyncio.sleep(2.0) # Đợi Camera khởi động ánh sáng

        captured_count = 0
        
        # Bắt đầu vòng lặp thu thập ảnh
        while captured_count < self.target_frames:
            if not self.is_training:
                break
                
            base64_frame = await self.camera_view.get_current_frame_base64()
            if base64_frame:
                is_valid, msg = self.check_quality(base64_frame)
                if is_valid:
                    self.captured_frames.append(base64_frame)
                    captured_count += 1
                    self.txt_progress.value = f"{captured_count}/{self.target_frames}"
                    self.txt_status.value = "Tốt, giữ nguyên tư thế..."
                    self.txt_status.color = ft.Colors.GREEN_400
                    self.update()
                    # Flet 0.84.0: Bỏ qua page.snack_bar, có thể không cần hiện SnackBar khi thành công để tránh rối
                    await asyncio.sleep(0.3)
                    # Auto-disable start button when target reached
                    if len(self.captured_frames) >= self.target_frames:
                        self.btn_start.disabled = True
                else:
                    self.txt_status.value = msg
                    self.txt_status.color = ft.Colors.RED_400
                    self.update()
                    # Loại bỏ show_top_notification vì đã có text hiển thị trực quan trên khung camera
                    await asyncio.sleep(0.5)
            else:
                await asyncio.sleep(0.2)

        if captured_count >= self.target_frames:
            self.txt_status.value = "Đang gửi dữ liệu..."
            self.txt_status.color = ft.Colors.YELLOW_400
            self.update()
            
            # GỬI LÊN DATABASE
            try:
                client = await get_supabase_client()
                res = await client.post("/training/face/enroll", json={
                    "sv_id": self.selected_student["id"],
                    "gv_id": self.gv_id,
                    "images": self.captured_frames
                })
                
                if res.status_code != 200:
                    error_detail = res.json().get("detail", "Lỗi không xác định từ Server")
                    raise ValueError(error_detail)

                self.selected_student["has_data"] = True
                prefs = ft.SharedPreferences()
                
                if self.search_mode_val == "class" and self.current_class_id:
                    await prefs.remove(f"cache_training_sv_{self.current_class_id}")
                    await self.load_students_by_class(self.current_class_id)
                elif self.search_mode_val == "mssv":
                    await self.handle_search_student(None)
                    
                show_top_notification(self.app_page, "Thành công", "Dữ liệu đã được cập nhật!", ft.Colors.BLUE_600, sound="S")
                
            except ValueError as ve:
                show_top_notification(self.app_page, "Cảnh báo dữ liệu", str(ve), ft.Colors.ORANGE_500, sound="E", duration_ms=6000)
            except Exception as ex:
                show_top_notification(self.app_page, "AuEdu - Lỗi API", str(ex), ft.Colors.RED_500, sound="E")

        # ==========================================
        # PHỤC HỒI GIAO DIỆN
        # ==========================================
        await self.camera_view.stop_camera()
        self.is_training = False
        self.camera_container.visible = False
        self.black_screen.visible = True
        self.alignment_guide.visible = False
        self.status_pill.visible = False
        self.btn_start.disabled = False
        self.update()

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
        
        if cached_data_str and last_sync_str and (current_time - float(last_sync_str) < 86400):
            classes_data = safe_json_load(cached_data_str)
        else:
            try:
                client = await get_supabase_client()
                res = await client.get(f"/training/giangvien/{self.gv_id}/lophoc")
                res.raise_for_status()
                classes_data = res.json()
                
                await prefs.set(cache_key_data, json.dumps(classes_data))
                await prefs.set(cache_key_time, str(current_time))
            except Exception as e:
                print(f"Lỗi load lớp: {e}")
                if cached_data_str: classes_data = safe_json_load(cached_data_str)
        
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
                print(f"Lỗi load sinh viên: {e}")
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