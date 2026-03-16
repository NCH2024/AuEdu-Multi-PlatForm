import flet as ft
from core.theme import PRIMARY_COLOR

class PageFrame(ft.Container):
    """
    Header tĩnh, nổi (floating), 1 hàng siêu gọn và chuyên nghiệp có menu 3 chấm.
    """
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

        session = self.app_page.session.store.get("user_session") or {}
        user_name = session.get("name", "Người dùng")

        async def go_to_settings(e):
            await self.app_page.push_route("/user/settings")

        async def handle_logout(e):
            """Xử lý sự kiện đăng xuất ngay trên Menu 3 chấm"""
            self.app_page.session.store.remove("user_session")
            await self.app_page.push_route("/login")

        # ---------------- HEADER NỔI 1 HÀNG CHUYÊN NGHIỆP ----------------
        self.header = ft.Container(
            top=15, left=15, right=15, # Tạo hiệu ứng nổi lơ lửng cách viền
            bgcolor=PRIMARY_COLOR,
            padding=ft.Padding(left=8, top=8, right=5, bottom=8),
            border_radius=15, # Bo góc thẻ nổi
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK_26, offset=ft.Offset(0, 4)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # --- CỤM TRÁI: Avatar và Tên bọc trong thẻ nền ---
                    ft.Container(
                        padding=ft.Padding(left=4, top=4, right=12, bottom=4),
                        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                        border_radius=20, # Bo tròn dạng viên thuốc
                        expand=True, # Cho phép co dãn nếu tên quá dài
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.CircleAvatar(
                                    content=ft.Icon(ft.Icons.PERSON, color=PRIMARY_COLOR, size=14),
                                    bgcolor=ft.Colors.WHITE,
                                    radius=14,
                                ),
                                ft.Text(
                                    user_name,
                                    size=12, # Chữ nhỏ lại theo ý em
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ]
                        )
                    ),
                    
                    # --- CỤM PHẢI: Badge Tiêu đề + Nút 3 chấm ---
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
                            # Nút 3 chấm thần thánh của Mobile App
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color=ft.Colors.WHITE,
                                icon_size=20,
                                tooltip="Tùy chọn",
                                items=[
                                    ft.PopupMenuItem(content=ft.Text("Cài đặt"), icon=ft.Icons.SETTINGS_OUTLINED, on_click=go_to_settings),
                                    ft.PopupMenuItem(content=ft.Text("Đăng xuất"), icon=ft.Icons.LOGOUT, on_click=handle_logout),
                                ]
                            ),
                        ]
                    )
                ]
            )
        )

        # ---------------- NỘI DUNG CUỘN ----------------
        col_kwargs = {"expand": True, "controls": []}
        if scrollable:
            col_kwargs.update({"scroll": ft.ScrollMode.AUTO})
            
        self.scroll_area = ft.Column(**col_kwargs)

        # Spacer nhường chỗ cho Header nổi (tăng lên 80px để nội dung không bị Header đè lên)
        self.scroll_area.controls.append(ft.Container(height=80))

        # Nội dung trang thực tế
        self.scroll_area.controls.append(
            ft.Container(
                content=main_content,
                padding=15,
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
            )
        )

        # Spacer chân trang nhường chỗ cho Bottom Navigation
        self.scroll_area.controls.append(ft.Container(height=100))

        self.content = ft.Stack(
            expand=True,
            controls=[
                self.scroll_area,
                self.header,
            ],
        )