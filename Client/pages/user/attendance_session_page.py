import flet as ft
import asyncio
import json
import websockets
import base64
import traceback
from datetime import datetime
from core.theme import current_theme, get_flat_container
from components.options.camera_view import CameraView
from components.options.custom_dropdown import CustomDropdown

class AttendanceSessionPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color 
        self.padding = 0

        self.mode = "1"
        self.is_desktop = self.app_page.platform not in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
        
        self.show_grid = False 
        self.is_paused = False 
        
        # Lấy dữ liệu từ trang trước truyền sang
        self.tkb_tiet_id = self.app_page.session.store.get("current_tkb_tiet_id") or "1" 
        self.mode = self.app_page.session.store.get("current_attendance_mode") or "1"
        
        # NHẬN DANH SÁCH SINH VIÊN THỰC TẾ
        self.real_students = self.app_page.session.store.get("current_student_list") or []
        self.attendance_date = self.app_page.session.store.get("current_attendance_date") or datetime.now().date().isoformat()
        
        # Danh sách chứa các sinh viên VỪA MỚI QUÉT ĐƯỢC trong phiên này
        self.scanned_session_students = []
        
        self.ws = None
        self.ws_connected = False

        self.dd_camera = CustomDropdown(label="Chọn nguồn Camera", options=[], on_change=self.handle_camera_change)
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera, is_visible=True, on_frame=self.send_frame_to_server)
        
        # OVERLAY: Màn đen phủ lên khi tạm dừng
        self.pause_overlay = ft.Container(
            left=0, right=0, top=0, bottom=0,
            bgcolor=ft.Colors.BLACK_87, # Sử dụng đúng chuẩn màu của bạn
            visible=False,
            alignment=ft.Alignment.CENTER, # Sử dụng đúng chuẩn Căn lề của bạn
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.MOTION_PHOTOS_PAUSE, color=ft.Colors.WHITE, size=50),
                    ft.Text("ĐÃ TẠM DỪNG", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=18),
                    ft.Text("Bạn có thể bấm nút \"Tiếp tục\"\nđể tiếp tục điểm danh", color=ft.Colors.WHITE_70, size=13, text_align=ft.TextAlign.CENTER)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            )
        )

        self.settings_sheet = ft.BottomSheet(
            content=ft.Container(
                padding=ft.Padding(20, 30, 20, 30),
                bgcolor=current_theme.surface_color,
                content=ft.Column(tight=True, spacing=20, controls=[
                    ft.Text("⚙️ TÙY CHỌN CAMERA", weight=ft.FontWeight.BOLD, size=16, color=current_theme.text_main, text_align=ft.TextAlign.CENTER),
                    self.dd_camera,
                    ft.Button("Đóng lại", width=float('inf'), height=45, bgcolor=ft.Colors.RED_500, color=ft.Colors.WHITE, on_click=lambda e: self.close_settings())
                ])
            )
        )
        self.app_page.overlay.append(self.settings_sheet)

        self.mock_students = [
            {"id": "223401", "name": "Nguyễn Văn A", "status": 1, "time": "08:30:10"},
            {"id": "223402", "name": "Trần Thị B", "status": 0, "time": ""},
            {"id": "223403", "name": "Lê Văn C", "status": 2, "time": ""},
            {"id": "223404", "name": "Phạm D", "status": 3, "time": "08:45:00"},
        ]

        self.header_title = ft.Text("Đã quét", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=15)
        self.toggle_btn = ft.IconButton(
            icon=ft.Icons.GRID_VIEW_ROUNDED, icon_color=current_theme.accent, tooltip="Chuyển chế độ xem", on_click=self.toggle_view_mode
        )
        self.list_grid_container = ft.Container(expand=True) 

    def did_mount(self):
        self.list_grid_container.content = self.build_scanned_list()
        self.content = self.build_ui()
        self.update()
        
        async def delayed_init():
            prefs = ft.SharedPreferences()
            saved_cam = await prefs.get("selected_camera")
            await self.camera_view.load_available_cameras()
            if saved_cam:
                self.dd_camera.value = str(saved_cam)
                self.dd_camera.update()
                
            await self.connect_websocket() 
            await self.init_camera_session()
            
        self.app_page.run_task(delayed_init)

    def will_unmount(self):
        self.app_page.run_task(self.camera_view.stop_camera)
        if self.ws and self.ws_connected:
            self.app_page.run_task(self.ws.close)

        try:
            if hasattr(self.app_page, "views") and len(self.app_page.views) > 0:
                self.app_page.floating_action_button = None
                self.app_page.update()
        except Exception:
            pass

    async def init_camera_session(self):
        await self.camera_view.start_camera()
        
        # Bật vòng lặp chụp và gửi ảnh cho riêng nền tảng Mobile
        if not self.is_desktop:
            self.app_page.run_task(self.mobile_streaming_loop)
            
    async def mobile_streaming_loop(self):
        """Vòng lặp chạy ngầm, cứ 1.5 giây chụp 1 tấm gửi Server để điểm danh trên điện thoại"""
        while self.ws_connected:
            if not self.is_paused:
                try:
                    pic_bytes = await self.camera_view.camera_module.take_picture()
                    if pic_bytes:
                        b64 = base64.b64encode(pic_bytes).decode('utf-8')
                        await self.send_frame_to_server(f"data:image/jpeg;base64,{b64}")
                except Exception:
                    pass
            # Cấu hình 1.5s/frame để máy mát, tiết kiệm pin cho Mobile
            await asyncio.sleep(1.5)
        
    async def connect_websocket(self):
        # URL này theo IP của máy (VD: ws://192.168.1.X:8000)
        ws_url = f"ws://localhost:8000/api/ws/attendance/{self.tkb_tiet_id}" 
        try:
            self.ws = await websockets.connect(ws_url)
            self.ws_connected = True
            print("[Client] Đã kết nối WebSocket thành công!")
            # Khởi chạy luồng lắng nghe ngầm mà không làm đơ giao diện
            self.app_page.run_task(self.receive_ws_messages)
        except Exception as e:
            print(f"[Client] Lỗi kết nối WebSocket: {e}")
            self.ws_connected = False

    async def receive_ws_messages(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                # Giả sử Server trả về: {"status": "success", "students": [{"id": "223401", "name": "Nguyễn Văn A", "time": "08:30"}]}
                if data.get("status") == "success":
                    recognized_students = data.get("students", [])
                    await self.update_scanned_ui(recognized_students)
                    
        except websockets.exceptions.ConnectionClosed:
            print("[Client] Mất kết nối WebSocket. Đang thử lại...")
            self.ws_connected = False
        except Exception as e:
            print(f"[Client] Lỗi xử lý tin nhắn: {e}")

    async def handle_camera_change(self, e=None):
        prefs = ft.SharedPreferences()
        await prefs.set("selected_camera", str(self.dd_camera.value))
        if not self.is_paused:
            await self.camera_view.stop_camera()
            await self.camera_view.start_camera()

    async def handle_flip_camera(self, e):
        if self.is_desktop or len(self.camera_view.available_cameras) < 2: return
        current_idx = int(self.dd_camera.value) if self.dd_camera.value else 0
        self.dd_camera.value = str(1 if current_idx == 0 else 0)
        self.dd_camera.update()
        await self.handle_camera_change()

    async def toggle_pause_camera(self, e):
        self.is_paused = not self.is_paused
        
        # Cập nhật Giao diện nút Pause
        self.btn_pause_icon.name = ft.Icons.PLAY_CIRCLE_FILLED if self.is_paused else ft.Icons.PAUSE_CIRCLE_FILLED
        self.btn_pause_icon.color = ft.Colors.GREEN_500 if self.is_paused else ft.Colors.AMBER
        self.btn_pause_text.value = "Tiếp tục" if self.is_paused else "Tạm dừng"
        self.btn_pause_text.color = ft.Colors.GREEN_500 if self.is_paused else ft.Colors.AMBER
        self.btn_pause_container.update()

        # Hiện mảng đen Overlay
        self.pause_overlay.visible = self.is_paused
        self.pause_overlay.update()

        if self.is_paused:
            await self.camera_view.stop_camera()
        else:
            await self.camera_view.start_camera()

    async def handle_exit(self, e):
        await self.camera_view.stop_camera()
        await self.app_page.push_route("/user/attendance")

    def toggle_view_mode(self, e):
        self.show_grid = not self.show_grid
        self.header_title.value = "Tiến độ lớp" if self.show_grid else "Đã quét"
        self.toggle_btn.icon = ft.Icons.FORMAT_LIST_BULLETED_ROUNDED if self.show_grid else ft.Icons.GRID_VIEW_ROUNDED
        self.list_grid_container.content = self.build_student_grid() if self.show_grid else self.build_scanned_list()
        
        self.header_title.update()
        self.toggle_btn.update()
        self.list_grid_container.update()

    def open_settings(self):
        self.settings_sheet.open = True
        self.settings_sheet.update()

    def close_settings(self):
        self.settings_sheet.open = False
        self.settings_sheet.update()
        
    def minimize_window(self, e):
        try: self.app_page.window.minimized = True
        except: self.app_page.window_minimized = True
        self.app_page.update()

    def toggle_maximize(self, e):
        try: self.app_page.window.maximized = not self.app_page.window.maximized
        except: self.app_page.window_maximized = not getattr(self.app_page, "window_maximized", False)
        self.app_page.update()

    def build_student_grid(self):
        grid_items = []
        for idx, sv in enumerate(self.real_students, start=1):
            status = sv.get("trang_thai_diem_danh", "Chưa điểm danh")
            
            if status == "Có mặt": 
                bg, border, txt = ft.Colors.TRANSPARENT, ft.Border.all(2, ft.Colors.GREEN_600), ft.Colors.GREEN_600
            elif status == "Vắng": 
                bg, border, txt = ft.Colors.RED_500, None, ft.Colors.WHITE
            else: # Chưa điểm danh
                bg, border, txt = current_theme.surface_variant, ft.Border.all(1, current_theme.divider_color), current_theme.text_main

            grid_items.append(ft.Container(
                width=35, height=35, border_radius=20, bgcolor=bg, border=border, alignment=ft.Alignment.CENTER,
                content=ft.Text(str(idx), color=txt, weight=ft.FontWeight.BOLD, size=12)
            ))
        return ft.GridView(runs_count=5 if self.is_desktop else 6, max_extent=40, spacing=8, run_spacing=8, controls=grid_items)

    def build_scanned_list(self):
        scanned_list = ft.ListView(spacing=10, expand=True)
        
        if not self.scanned_session_students:
            scanned_list.controls.append(
                ft.Container(
                    padding=20, alignment=ft.Alignment.CENTER,
                    content=ft.Text("Chưa có sinh viên nào được quét trong phiên này.", size=12, color=current_theme.text_muted, italic=True)
                )
            )
            return scanned_list

        for sv in self.scanned_session_students:
            card = ft.Container(
                bgcolor=current_theme.surface_variant, border_radius=12, padding=10,
                border=ft.Border(left=ft.BorderSide(6, ft.Colors.GREEN_500)),
                content=ft.Row([
                    ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE), bgcolor=current_theme.divider_color, radius=18),
                    ft.Column([
                        ft.Text(sv["name"], weight=ft.FontWeight.BOLD, size=13, color=current_theme.text_main),
                        ft.Text(f"MSSV: {sv['id']} • {sv['time']}", size=11, color=current_theme.text_muted)
                    ], spacing=2, expand=True),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_500, size=20)
                ])
            )
            scanned_list.controls.append(card)
        return scanned_list
    
    async def update_scanned_ui(self, recognized_students):
        updated = False
        for rec_sv in recognized_students:
            # Tìm sinh viên trong danh sách thực tế
            for sv in self.real_students: 
                if str(sv["id"]) == str(rec_sv["id"]) and sv.get("trang_thai_diem_danh") != "Có mặt":
                    sv["trang_thai_diem_danh"] = "Có mặt" 
                    
                    # Thêm vào đầu danh sách thẻ (người mới nhất nổi lên trên)
                    self.scanned_session_students.insert(0, {
                        "id": sv["id"],
                        "name": f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip(),
                        "time": rec_sv.get("time", datetime.now().strftime("%H:%M:%S"))
                    })
                    updated = True
        
        if updated:
            if self.show_grid:
                self.list_grid_container.content = self.build_student_grid()
            else:
                self.list_grid_container.content = self.build_scanned_list()
            
            try:
                self.list_grid_container.update()
            except Exception:
                pass

    def build_ui(self):
        # 1. KHU VỰC CAMERA
        # Ép trực tiếp CameraView bám chặt 4 góc của Stack
        self.camera_view.left = 0
        self.camera_view.right = 0
        self.camera_view.top = 0
        self.camera_view.bottom = 0

        camera_stack = ft.Stack(
            expand=True,
            controls=[
                self.camera_view, 
                self.pause_overlay 
            ]
        )

        camera_card = get_flat_container(
            content=camera_stack,
            padding=0, expand=True
        )
        # Rất quan trọng: Cắt phần hình ảnh dư thừa nếu nó tràn ra khỏi viền bo góc
        camera_card.clip_behavior = ft.ClipBehavior.HARD_EDGE 

        # 2. THANH NAVIGATION DƯỚI CÙNG
        def create_nav_btn(icon_name, label, color, on_click_event):
            return ft.Container(
                on_click=on_click_event, ink=True, border_radius=0, 
                padding=ft.Padding(0,0,0,0), expand=True,
                content=ft.Column([
                    ft.Icon(icon_name, color=color, size=24),
                    ft.Text(label, size=11, color=color, weight=ft.FontWeight.BOLD)
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        self.btn_pause_icon = ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=ft.Colors.AMBER, size=30)
        self.btn_pause_text = ft.Text("Tạm dừng", size=11, color=ft.Colors.AMBER, weight=ft.FontWeight.BOLD)
        
        self.btn_pause_container = ft.Container(
            on_click=self.toggle_pause_camera, ink=True, border_radius=8, 
            padding=ft.Padding(2, 5, 2, 5), expand=True,
            content=ft.Column([self.btn_pause_icon, self.btn_pause_text], spacing=2, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

        nav_buttons = [
            create_nav_btn(ft.Icons.SETTINGS_ROUNDED, "Cài đặt", current_theme.text_muted, lambda e: self.open_settings()),
            self.btn_pause_container,
            create_nav_btn(ft.Icons.EXIT_TO_APP_ROUNDED, "Thoát", ft.Colors.RED_500, self.handle_exit)
        ]
        
        if not self.is_desktop:
            nav_buttons.insert(1, create_nav_btn(ft.Icons.FLIP_CAMERA_ANDROID, "Đổi Cam", current_theme.text_muted, self.handle_flip_camera))

        bottom_nav = get_flat_container(
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_EVENLY, controls=nav_buttons),
            padding=ft.Padding(0,0,0,0), expand=False
        )

        # 3. PANEL BÊN CHỨA DANH SÁCH & GRID
        panel_content = ft.Column([
            ft.Row([self.header_title, self.toggle_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=current_theme.divider_color),
            self.list_grid_container
        ], expand=True)

        if self.is_desktop:
            # GIAO DIỆN PC
            desktop_top_bar = ft.WindowDragArea(
                ft.Container(
                    height=32, bgcolor=current_theme.bg_color, border_radius=8,
                    padding=ft.Padding(10, 0, 5, 0),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row([ft.Icon(ft.Icons.CAMERA_ALT_ROUNDED, size=16, color=current_theme.accent), ft.Text("AUEDU - CAMERA [Điểm danh]", color=current_theme.text_main, weight=ft.FontWeight.BOLD, size=13)]),
                            ft.Row([
                                ft.IconButton(ft.Icons.MINIMIZE, icon_size=16, icon_color=current_theme.text_muted, on_click=self.minimize_window, tooltip="Thu nhỏ"),
                                ft.IconButton(ft.Icons.CROP_SQUARE, icon_size=16, icon_color=current_theme.text_muted, on_click=self.toggle_maximize, tooltip="Phóng to"),
                                ft.IconButton(ft.Icons.CLOSE, icon_size=16, icon_color=ft.Colors.RED_500, on_click=self.handle_exit, tooltip="Đóng")
                            ], spacing=0)
                        ]
                    )
                )
            )

            left_panel = get_flat_container(content=panel_content, padding=5, expand=False)
            left_panel.width = 350

            main_layout = ft.Column([
                desktop_top_bar,
                ft.Row([
                    left_panel, 
                    ft.Column([camera_card, bottom_nav], expand=True) 
                ], expand=True, spacing=10)
            ], expand=True, spacing=5)
        else:
            # GIAO DIỆN MOBILE
            bottom_panel = get_flat_container(content=panel_content, padding=5, expand=False)
            bottom_panel.height = 250

            main_layout = ft.Column([
                camera_card,   
                bottom_panel,  
                bottom_nav     
            ], expand=True, spacing=2)

        return ft.Container(content=main_layout, padding=2 if self.is_desktop else 5, expand=True)
    
    async def send_frame_to_server(self, frame_base64: str):
        if self.ws_connected and self.ws:
            payload = {
                "image": frame_base64,
                "mode": self.mode,
                "tkb_tiet_id": self.tkb_tiet_id,
                "date": self.attendance_date
            }
            try:
                # Gửi bất đồng bộ lên Server
                await self.ws.send(json.dumps(payload))
            except Exception as e:
                print(f"[Client] Lỗi khi gửi frame: {e}")
                self.ws_connected = False