import flet as ft
from core.theme import PRIMARY_COLOR

class PageFrame(ft.Container):
    """
    Header tĩnh, cứng cáp, 1 hàng siêu gọn và chuyên nghiệp.
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

        # ---------------- HEADER 1 HÀNG CHUYÊN NGHIỆP ----------------
        self.header = ft.Container(
            top=0, left=0, right=0,
            bgcolor=PRIMARY_COLOR,
            padding=ft.Padding(left=15, top=10, right=5, bottom=10),
            # Giữ lại bóng đổ nhẹ để tạo chiều sâu cho khung
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color=ft.Colors.BLACK_26, offset=ft.Offset(0, 2)),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # --- CụM TRÁI: Avatar và Tên ---
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        expand=True, # Chiếm hết không gian còn lại
                        controls=[
                            ft.CircleAvatar(
                                content=ft.Icon(ft.Icons.PERSON, color=PRIMARY_COLOR, size=16),
                                bgcolor=ft.Colors.WHITE,
                                radius=16,
                            ),
                            ft.Text(
                                user_name,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True, # Ép tên dài phải có dấu ... chứ không làm vỡ khung
                            ),
                        ]
                    ),
                    
                    # --- CỤM PHẢI: Badge Tiêu đề + Nút Cài đặt ---
                    ft.Row(
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                padding=ft.Padding(10, 4, 10, 4),
                                bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.WHITE),
                                border_radius=12,
                                content=ft.Text(
                                    page_title.upper(),
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.WHITE,
                                )
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SETTINGS_OUTLINED,
                                icon_color=ft.Colors.WHITE,
                                icon_size=22,
                                on_click=go_to_settings,
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

        # Spacer nhường chỗ cho Header tĩnh (60px là vừa khít đẹp)
        self.scroll_area.controls.append(ft.Container(height=60))

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
        self.scroll_area.controls.append(ft.Container(height=80))

        self.content = ft.Stack(
            expand=True,
            controls=[
                self.scroll_area,
                self.header,
            ],
        )