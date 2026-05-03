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

# FIQA Threshold
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
        self.target_frames = 15 

        # --- COMPONENTS ---
        self.dd_camera = CustomDropdown(label="Nguồn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True, view_mode="training")
        
        self.camera_container = ft.Container(content=self.camera_view, visible=False, expand=True, left=0, right=0, top=0, bottom=0)
        self.black_screen = ft.Container(bgcolor=ft.Colors.BLACK, expand=True, left=0, right=0, top=0, bottom=0)
        
        self.alignment_guide = ft.Container(
            alignment=ft.Alignment(0, 0),
            content=ft.Container(
                width=300, height=400, 
                border_radius=150, 
                border=ft.Border.all(3, ft.Colors.GREEN_400),
                shadow=ft.BoxShadow(spread_radius=3000, color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK))
            ),
            left=0, right=0, top=0, bottom=0, visible=False
        )
        
        self.txt_status = ft.Text("Vui lòng nhìn thẳng và giữ yên khuôn mặt", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=15)
        self.txt_progress = ft.Text("0/15", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400, size=18)
        
        self.status_pill = ft.Container(
            content=ft.Column([
                self.txt_status,
                ft.Row([ft.Icon(ft.Icons.CAMERA, color=ft.Colors.WHITE), self.txt_progress], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            padding=ft.Padding(15, 10, 15, 10), border_radius=15, visible=False
        )
        
        self.status_pill_wrapper = ft.Container(
            content=ft.Row([self.status_pill], alignment=ft.MainAxisAlignment.CENTER),
            bottom=20, left=0, right=0
        )

        self.search_tf = ft.TextField(
            label="Nhập Mã Sinh Viên", hint_text="Nhấn Enter để tìm",
            prefix_icon=ft.Icons.SEARCH,
            suffix=ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, icon_size=14, on_click=self.handle_search_student),
            border_radius=8, height=45, text_size=12, content_padding=10, on_submit=self.handle_search_student
        )
        
        self.student_list_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=6)

        self.search_mode = ft.SegmentedButton(
            selected=["class"], on_change=self.handle_mode_change,
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

    def build_mobile_warning(self):
        return ft.Column([ft.Icon(ft.Icons.DESKTOP_MAC, size=80)], alignment=ft.MainAxisAlignment.CENTER)

    def build_desktop_layout(self):
        top_bar = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.app_page.run_task(self.app_page.push_route, "/user/attendance")),
            ft.Text("Quay lại Điểm danh", weight=ft.FontWeight.BOLD, size=13)
        ])

        left_panel = ft.Container(
            width=330, padding=15, border_radius=12, bgcolor=current_theme.surface_color,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Column([
                ft.Text("CHỌN SINH VIÊN", weight=ft.FontWeight.BOLD, size=14),
                ft.Row([self.search_mode], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=self.student_list_ui, expand=True)
            ])
        )

        right_panel = ft.Container(
            expand=True, padding=10, border_radius=12, bgcolor=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Column([
                ft.Row([ft.Text("CAMERA THU THẬP", weight=ft.FontWeight.BOLD), ft.Container(content=self.dd_camera, width=150)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(expand=True, content=ft.Stack([self.black_screen, self.camera_container, self.alignment_guide, self.status_pill_wrapper])),
                ft.Row([ft.Text("Đang chọn:"), self.txt_current_student], alignment=ft.MainAxisAlignment.CENTER),
                self.btn_start
            ])
        )

        return ft.Column([top_bar, ft.Row([left_panel, right_panel], expand=True, spacing=15)])

    def handle_mode_change(self, e):
        self.search_mode_val = list(e.control.selected)[0]
        self.student_list_ui.controls.clear()
        if self.search_mode_val == "class":
            self.app_page.run_task(self.load_classes)
        else:
            self.student_list_ui.controls.append(self.search_tf)
        self.update()

    async def load_classes(self):
        if self.gv_id == "N/A": return
        try:
            client = await get_supabase_client()
            res = await client.get(f"/training/giangvien/{self.gv_id}/lophoc")
            classes = res.json()
            self.student_list_ui.controls.clear()
            for c in classes:
                self.student_list_ui.controls.append(ft.ListTile(title=ft.Text(c["name"]), on_click=lambda e, cid=c["id"]: self.app_page.run_task(self.load_students_by_class, cid)))
            self.update()
        except: pass

    async def load_students_by_class(self, class_id):
        try:
            client = await get_supabase_client()
            res = await client.get(f"/training/lop/{class_id}/sinhvien")
            svs = res.json()
            self.student_list_ui.controls.clear()
            self.student_list_ui.controls.append(ft.TextButton("<- Quay lại", on_click=lambda _: self.app_page.run_task(self.load_classes)))
            for sv in svs:
                self.student_list_ui.controls.append(ft.ListTile(title=ft.Text(sv["name"]), subtitle=ft.Text(sv["id"]), on_click=lambda e, s=sv: self.select_student(s)))
            self.update()
        except: pass

    async def handle_search_student(self, e):
        kw = self.search_tf.value
        if not kw: return
        try:
            client = await get_supabase_client()
            res = await client.get(f"/training/giangvien/{self.gv_id}/timkiem", params={"keyword": kw})
            svs = res.json()
            self.student_list_ui.controls.clear()
            self.student_list_ui.controls.append(self.search_tf)
            for sv in svs:
                self.student_list_ui.controls.append(ft.ListTile(title=ft.Text(sv["name"]), on_click=lambda e, s=sv: self.select_student(s)))
            self.update()
        except: pass

    def select_student(self, sv):
        self.selected_student = sv
        self.btn_start.disabled = False
        self.txt_current_student.value = f"{sv['name']} - {sv['id']}"
        self.txt_current_student.color = ft.Colors.GREEN_600
        self.update()

    async def start_training(self, e):
        self.is_training = True
        self.captured_frames.clear()
        self.camera_container.visible = True
        self.black_screen.visible = False
        self.status_pill.visible = True
        self.update()
        await self.camera_view.start_camera()
        
        count = 0
        while count < self.target_frames and self.is_training:
            frame = await self.camera_view.get_current_frame_base64()
            if frame:
                self.captured_frames.append(frame)
                count += 1
                self.txt_progress.value = f"{count}/15"
                self.update()
                await asyncio.sleep(0.3)
            else:
                await asyncio.sleep(0.1) # Tránh treo máy khi camera chưa sẵn sàng frame
        
        if count >= self.target_frames:
            try:
                client = await get_supabase_client()
                await client.post("/training/face/enroll", json={
                    "sv_id": self.selected_student["id"],
                    "gv_id": self.gv_id,
                    "images": self.captured_frames
                })
                show_top_notification(self.app_page, "Thành công", "Đã cập nhật khuôn mặt", ft.Colors.BLUE)
            except: pass

        await self.camera_view.stop_camera()
        self.is_training = False
        self.camera_container.visible = False
        self.black_screen.visible = True
        self.status_pill.visible = False
        self.update()