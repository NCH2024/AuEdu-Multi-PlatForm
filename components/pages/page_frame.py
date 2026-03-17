import flet as ft
import json
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR

class PageFrame(ft.Container):
    def __init__(self,
                 page: ft.Page,
                 page_title: str,
                 main_content: ft.Control,
                 *,
                 scrollable: bool = True):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = ft.Colors.TRANSPARENT

        self.user_name_text = ft.Text(
            "Đang tải...",
            size=12, 
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )

        async def go_to_settings(e):
            await self.app_page.push_route("/user/settings")
            
        async def handle_about(e):
            await self.app_page.push_route("/user/about")
                    
        async def handle_logout(e):
            prefs = ft.SharedPreferences()
            await prefs.remove("user_session")
            await self.app_page.push_route("/login")
            
        # ---------------- HEADER NỔI 1 HÀNG CHUYÊN NGHIỆP ----------------
        self.header = ft.Container(
            top=15, left=15, right=15, 
            bgcolor=SECONDARY_COLOR, 
            padding=ft.Padding(left=8, top=8, right=5, bottom=8),
            border_radius=15, 
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK_26, offset=ft.Offset(0, 4)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        padding=ft.Padding(left=4, top=4, right=12, bottom=4),
                        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                        border_radius=20, 
                        expand=True, 
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.CircleAvatar(
                                    content=ft.Icon(ft.Icons.PERSON, color=SECONDARY_COLOR, size=14),
                                    bgcolor=ft.Colors.WHITE,
                                    radius=14,
                                ),
                                self.user_name_text, 
                            ]
                        )
                    ),
                    
                    ft.Row(
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                padding=ft.Padding(10, 4, 10, 4),
                                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                                border_radius=12,
                                margin=ft.Margin(left=10, top=0, right=0, bottom=0),
                                content=ft.Text(
                                    page_title.upper(),
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                )
                            ),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=ft.Colors.WHITE,
                                icon_size=20,
                                tooltip="Tùy chọn",
                                items=[
                                    ft.PopupMenuItem(content=ft.Text("Cài đặt"), icon=ft.Icons.SETTINGS_OUTLINED, on_click=go_to_settings),
                                    ft.PopupMenuItem(content=ft.Text("Đăng xuất"), icon=ft.Icons.LOGOUT, on_click=handle_logout),
                                    ft.PopupMenuItem(content=ft.Text("Thông tin phần mềm"), icon=ft.Icons.INFO, on_click=handle_about),
                                ]
                            ),
                        ]
                    )
                ]
            )
        )

        col_kwargs = {"expand": True, "controls": []}
        if scrollable:
            col_kwargs.update({"scroll": ft.ScrollMode.AUTO})
            
        self.scroll_area = ft.Column(**col_kwargs)
        self.scroll_area.controls.append(ft.Container(height=80))
        self.scroll_area.controls.append(
            ft.Container(
                content=main_content,
                padding=15,
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
            )
        )
        self.scroll_area.controls.append(ft.Container(height=100))

        self.content = ft.Stack(
            expand=True,
            controls=[
                self.scroll_area,
                self.header,
            ],
        )
        
        self.app_page.run_task(self.load_user_info)

    async def load_user_info(self):
        # KẾT HỢP CHUẨN
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            try:
                session = json.loads(session_str)
                self.user_name_text.value = session.get("name", "Người dùng")
                self.user_name_text.update()
            except:
                pass