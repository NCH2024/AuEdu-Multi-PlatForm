import flet as ft
import asyncio
import json
from core.theme import current_theme
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown
from components.options.top_notification import show_top_notification
from core.config import get_supabase_client
from core.admin_service import AdminService
from core.helper import safe_json_load

class AdminTrainingPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = 0 # Không padding để camera dãn sát lề nếu cần
        self.svc = AdminService.instance()

        # State
        self.selected_student = None
        self.captured_frames = []
        self.is_training = False
        self.admin_id = "ADMIN_SYSTEM"

        # UI Components
        self.dd_camera = CustomDropdown(label="Nguồn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True, view_mode="training")
        
        self.camera_container = ft.Container(content=self.camera_view, visible=False, expand=True)
        self.status_text = ft.Text("HỆ THỐNG SẴN SÀNG", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400, size=12)
        self.progress_text = ft.Text("0/15", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)
        
        self.btn_start = ft.Button(
            "BẮT ĐẦU THU THẬP DỮ LIỆU", 
            icon=ft.Icons.FACE_RETOUCHING_NATURAL,
            on_click=self.start_training,
            disabled=True,
            height=50,
            style=ft.ButtonStyle(
                bgcolor=current_theme.accent, 
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=10)
            )
        )

        self.student_info = ft.Text("Đang chờ chọn sinh viên...", size=16, weight=ft.FontWeight.W_600, color=current_theme.secondary)

        # Layout chính
        self.content = ft.Column([
            # Top Bar
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                bgcolor=current_theme.surface_color,
                border=ft.Border(bottom=ft.BorderSide(1, current_theme.divider_color)),
                content=ft.Row([
                    ft.Row([
                        ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_size=18, on_click=lambda _: self.app_page.run_task(self.app_page.push_route, "/admin/faces")),
                        ft.Text("QUAY LẠI QUẢN LÝ", weight=ft.FontWeight.BOLD, size=14)
                    ]),
                    ft.Row([
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=ft.Colors.BLUE_600, size=20),
                        ft.Text("STUDIO ĐÀO TẠO KHUÔN MẶT (ADMIN)", weight=ft.FontWeight.W_700)
                    ], spacing=10)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ),
            
            # Camera View dãn hết cỡ
            ft.Container(
                expand=True,
                margin=20,
                content=ft.Stack([
                    # Khung đen nền
                    ft.Container(bgcolor=ft.Colors.BLACK, border_radius=20, expand=True),
                    
                    # Camera chính
                    ft.Container(
                        content=self.camera_container, 
                        border_radius=20, 
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                        expand=True,
                        left=0, right=0, top=0, bottom=0
                    ),
                    
                    # Overlay thông tin
                    ft.Container(
                        padding=30,
                        content=ft.Column([
                            ft.Row([
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("SINH VIÊN ĐANG CHỌN", size=10, color=ft.Colors.GREY_400),
                                        self.student_info,
                                    ], spacing=2),
                                    padding=15, bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
                                    border_radius=12, border=ft.Border.all(1, ft.Colors.GREY_800)
                                ),
                                ft.Container(
                                    content=self.dd_camera, width=200, 
                                    padding=5, bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
                                    border_radius=12
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            
                            ft.Container(expand=True), # Spacer
                            
                            ft.Row([
                                ft.Container(
                                    content=ft.Row([
                                        ft.Column([
                                            ft.Text("TIẾN ĐỘ THU THẬP", size=10, color=ft.Colors.GREY_400),
                                            self.progress_text,
                                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                        ft.VerticalDivider(color=ft.Colors.GREY_800),
                                        ft.Column([
                                            ft.Text("TRẠNG THÁI", size=10, color=ft.Colors.GREY_400),
                                            self.status_text,
                                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                    ], spacing=20),
                                    padding=20, bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
                                    border_radius=15, border=ft.Border.all(1, ft.Colors.GREY_800)
                                ),
                                self.btn_start
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        ], expand=True)
                    )
                ])
            )
        ], spacing=0)

    def did_mount(self):
        self.app_page.run_task(self.camera_view.load_available_cameras)
        self.app_page.run_task(self.initialize_page)

    async def initialize_page(self):
        prefs = ft.SharedPreferences()
        sess = await prefs.get("user_session")
        if sess:
            self.admin_id = safe_json_load(sess).get("id", "ADMIN_SYSTEM")

        sv_id = self.app_page.session.store.get("admin_train_sv_id")
        if sv_id:
            students = await self.svc.get_students()
            target = next((s for s in students if str(s["id"]) == str(sv_id)), None)
            
            if target:
                self.selected_student = target
                self.student_info.value = f"{target['full_name']} - MSSV: {target['id']}"
                self.student_info.color = ft.Colors.GREEN_400
                self.btn_start.disabled = False
                self.update()
            else:
                show_top_notification(self.app_page, "Lỗi", f"Không tìm thấy sinh viên ID: {sv_id}", ft.Colors.RED)

    async def start_training(self, e):
        self.is_training = True
        self.captured_frames.clear()
        self.btn_start.disabled = True
        self.camera_container.visible = True
        self.status_text.value = "ĐANG THU THẬP..."
        self.status_text.color = ft.Colors.ORANGE_400
        self.update()

        await self.camera_view.start_camera()
        await asyncio.sleep(1)

        count = 0
        while count < 15 and self.is_training:
            frame = await self.camera_view.get_current_frame_base64()
            if frame:
                self.captured_frames.append(frame)
                count += 1
                self.progress_text.value = f"{count}/15"
                self.update()
                await asyncio.sleep(0.4) # Chờ để thu thập frame tiếp theo
            else:
                await asyncio.sleep(0.1) # Tránh loop quá nhanh khi chưa có frame

        if count >= 15:
            self.status_text.value = "ĐANG XỬ LÝ..."
            self.status_text.color = ft.Colors.BLUE_400
            self.update()
            try:
                client = await get_supabase_client()
                res = await client.post("/training/face/enroll", json={
                    "sv_id": self.selected_student["id"],
                    "gv_id": self.admin_id,
                    "images": self.captured_frames
                })
                if res.status_code == 200:
                    show_top_notification(self.app_page, "Thành công", "Đã cập nhật khuôn mặt sinh viên", ft.Colors.GREEN)
                    await asyncio.sleep(1.5)
                    # Sau khi thành công, không tự động chuyển trang ngay lập tức để tránh mất dữ liệu tìm kiếm ở trang cũ quá nhanh
                    # Người dùng có thể nhấn nút "Quay lại" thủ công hoặc chúng ta sẽ xử lý lưu state ở trang FacesPage
                    self.status_text.value = "HOÀN TẤT - ĐÃ CẬP NHẬT"
                    self.status_text.color = ft.Colors.GREEN_400
                    self.update()
                else:
                    show_top_notification(self.app_page, "Lỗi Server", f"Lỗi: {res.text}", ft.Colors.RED)
            except Exception as ex:
                show_top_notification(self.app_page, "Lỗi Hệ Thống", str(ex), ft.Colors.RED)

        await self.camera_view.stop_camera()
        self.is_training = False
        self.camera_container.visible = False
        self.btn_start.disabled = False
        self.status_text.value = "HOÀN TẤT"
        self.status_text.color = ft.Colors.GREEN_400
        self.update()

    def will_unmount(self):
        self.app_page.run_task(self.camera_view.stop_camera)
