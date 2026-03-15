import flet as ft
from core.theme import *

class PageFrame(ft.Container):
    """
    Header + nội dung cuộn. Tham số `scrollable` quyết định có scroll nội bộ hay không.
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

        # ---------------- Header ----------------
        self.row1 = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    page_title.upper(),
                    size=12,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.BLACK_87,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            ],
        )
        self.row2 = ft.Container(
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            animate_size=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            opacity=1,
            height=40,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.CircleAvatar(
                                content=ft.Icon(
                                    ft.Icons.PERSON,
                                    color=ft.Colors.WHITE,
                                    size=18,
                                ),
                                bgcolor=ft.Colors.BLACK_87,
                                radius=16,
                            ),
                            ft.Text(
                                user_name,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLACK_87,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS_OUTLINED,
                        icon_color=ft.Colors.BLACK_87,
                        icon_size=24,
                        on_click=go_to_settings,
                    ),
                ],
            ),
        )
        self.header = ft.Container(
            top=0,
            left=0,
            right=0,
            bgcolor=PRIMARY_COLOR_BLUR,
            blur=ft.Blur(
                sigma_x=15,
                sigma_y=15,
                tile_mode=ft.BlurTileMode.MIRROR,
            ),
            padding=ft.Padding(left=15, top=10, right=15, bottom=10),
            border_radius=ft.BorderRadius.vertical(bottom=15),
            content=ft.Column(
                spacing=5,
                controls=[self.row1, self.row2],
            ),
        )

        # ---------------- Nội dung cuộn ----------------
        col_kwargs = {"expand": True, "controls": []}
        if scrollable:
            col_kwargs.update(
                {"scroll": ft.ScrollMode.AUTO, "on_scroll": self._handle_scroll}
            )
        self.scroll_area = ft.Column(**col_kwargs)

        # Spacer để header không che
        self.scroll_area.controls.append(ft.Container(height=80))

        # Nội dung thực tế
        self.scroll_area.controls.append(
            ft.Container(
                content=main_content,
                padding=15,
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
            )
        )

        # ---------------- Stack ----------------
        self.content = ft.Stack(
            expand=True,
            controls=[
                self.scroll_area,
                self.header,
            ],
        )

    # ------------------------------------------------------------------
    async def _handle_scroll(self, e: ft.OnScrollEvent):
        if e.pixels > 5 and self.row2.opacity == 1:
            self.row2.opacity = 0
            self.row2.height = 0
        elif e.pixels <= 5 and self.row2.opacity == 0:
            self.row2.opacity = 1
            self.row2.height = 40
        # Không cần self.row2.update() – auto‑update sẽ thực thi khi hàm trả về
