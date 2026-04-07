import flet as ft
import asyncio
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR, get_glass_container
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown

class AttendanceSessionPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = ft.Colors.BLACK

        self.mode = "1"
        self.mode_name = "Từng sinh viên"

        self.dd_camera = CustomDropdown(
            label="Chọn nguồn Camera", 
            options=[], 
            on_change=self.handle_camera_change 
        )
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True)

        self.settings_sheet = ft.BottomSheet(
            content=ft.Container(
                padding=ft.Padding(20, 30, 20, 30),
                bgcolor=ft.Colors.WHITE,
                border_radius=ft.BorderRadius(top_left=20, top_right=20, bottom_left=0, bottom_right=0),
                content=ft.Column(
                    tight=True,
                    spacing=20,
                    controls=[
                        ft.Text("⚙️ TÙY CHỌN CAMERA", weight=ft.FontWeight.BOLD, size=16, color=SECONDARY_COLOR, text_align=ft.TextAlign.CENTER),
                        self.dd_camera,
                        ft.Button(
                            content=ft.Text("Đóng lại", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), 
                            width=float('inf'), height=45, bgcolor=ft.Colors.RED_500, 
                            on_click=lambda e: self.close_settings()
                        )
                    ]
                )
            )
        )
        self.app_page.overlay.append(self.settings_sheet)
        self.content = self.build_ui()

    def did_mount(self):
        async def delayed_init():
            await asyncio.sleep(0.1)
            if self.page:
                
                # KẾT HỢP CHUẨN
                prefs = ft.SharedPreferences()
                mode = await prefs.get("attendance_mode")
                if mode:
                    self.mode = str(mode)
                    self.mode_name = "Từng sinh viên" if self.mode == "1" else "Quét cả lớp"
                await self.init_camera_session()
        
        self.app_page.run_task(delayed_init)

    def will_unmount(self):
        self.app_page.run_task(self.camera_view.stop_camera)

    async def init_camera_session(self):
        await asyncio.sleep(0.5) 
        if getattr(self, "page", None) is None: return
        
        await self.camera_view.load_available_cameras()
        await self.camera_view.start_camera()

    async def handle_camera_change(self, e):
        await self.camera_view.start_camera()

    async def handle_flip_camera(self, e):
        if not self.camera_view.is_mobile or len(self.camera_view.available_cameras) < 2:
            return
        current_idx = int(self.dd_camera.value) if self.dd_camera.value else 0
        new_idx = 1 if current_idx == 0 else 0 
        self.dd_camera.value = str(new_idx)
        self.dd_camera.update()
        await self.camera_view.start_camera()

    def open_settings(self):
        self.settings_sheet.open = True
        self.settings_sheet.update()

    def close_settings(self):
        self.settings_sheet.open = False
        self.settings_sheet.update()

    def build_ui(self):
        camera_frame = ft.Container(
            expand=4, 
            bgcolor=ft.Colors.BLACK,
            border_radius=ft.BorderRadius(bottom_left=20, bottom_right=20, top_left=0, top_right=0),
            alignment=ft.Alignment(0, 0),
            content=self.camera_view 
        )

        self.scanned_list = ft.ListView(expand=3, spacing=10, padding=ft.Padding(15, 20, 15, 80))
        
        for i in range(5):
            card = ft.Container(
                bgcolor=ft.Colors.WHITE, border_radius=12, padding=12,
                border=ft.Border(left=ft.BorderSide(6, SECONDARY_COLOR)),
                content=ft.Row([
                    ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE), bgcolor=SECONDARY_COLOR, radius=20),
                    ft.Column([
                        ft.Text(f"Nguyễn Văn Sinh Viên {i+1}", weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLACK_87),
                        ft.Text(f"MSSV: 22340{i} • Điểm danh: 08:30:1{i}", size=12, color=ft.Colors.GREY_600)
                    ], spacing=2, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_500, size=24)
                ])
            )
            self.scanned_list.controls.append(card)

        async def handle_exit(e):
            await self.camera_view.stop_camera()
            await self.app_page.push_route("/user/attendance")

        btn_settings_floating = ft.Container(
            top=15, right=15, 
            content=get_glass_container(
                padding=5,
                content=ft.IconButton(icon=ft.Icons.SETTINGS_ROUNDED, icon_color=SECONDARY_COLOR, tooltip="Cài đặt", on_click=lambda e: self.open_settings())
            )
        )

        floating_controls = ft.Container(
            bottom=20, left=0, right=0, 
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    get_glass_container(
                        padding=10,
                        content=ft.Row(
                            spacing=20,
                            controls=[
                                ft.FloatingActionButton(icon=ft.Icons.FLIP_CAMERA_ANDROID, bgcolor=SECONDARY_COLOR, shape=ft.CircleBorder(), tooltip="Lật hình ảnh", on_click=self.handle_flip_camera),
                                ft.FloatingActionButton(icon=ft.Icons.PAUSE_ROUNDED, bgcolor=ACCENT_COLOR, shape=ft.CircleBorder(), tooltip="Tạm dừng"),
                                ft.FloatingActionButton(icon=ft.Icons.EXIT_TO_APP_ROUNDED, bgcolor=ft.Colors.RED_600, shape=ft.CircleBorder(), tooltip="Thoát", on_click=handle_exit)
                            ]
                        )
                    )
                ]
            )
        )

        return ft.Stack(
            expand=True,
            controls=[
                ft.Column([camera_frame, self.scanned_list], spacing=0, expand=True),
                btn_settings_floating, 
                floating_controls 
            ]
        )