import flet as ft
import asyncio
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR

class TopNotification(ft.Container):
    def __init__(self, page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=SECONDARY_COLOR):
        super().__init__()
        self.app_page = page
        self.top = -100  # Ẩn phía trên màn hình
        self.left = 20
        self.right = 20
        
        self.animate_position = ft.Animation(duration=500, curve=ft.AnimationCurve.EASE_OUT_BACK)
        self.animate_opacity = ft.Animation(duration=400, curve=ft.AnimationCurve.EASE_IN_OUT)
        self.opacity = 0
        self.duration_ms = duration_ms

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=350,
                    padding=15,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=15,
                    border=ft.Border(left=ft.BorderSide(6, color)),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK), offset=ft.Offset(0, 5)),
                    content=ft.Row(
                        spacing=15,
                        controls=[
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=color, size=24),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87, size=14),
                                    ft.Text(message, color=ft.Colors.GREY_700, size=12)
                                ]
                            )
                        ]
                    )
                )
            ]
        )

    def did_mount(self):
        self.app_page.run_task(self.show_and_hide)

    async def show_and_hide(self):
        # Hiệu ứng trượt xuống
        await asyncio.sleep(0.1)
        self.top = 20
        self.opacity = 1
        self.update()

        # Chờ theo thời gian tùy chỉnh
        await asyncio.sleep(self.duration_ms / 1000.0)

        # Hiệu ứng trượt lên và mờ đi
        self.top = -100
        self.opacity = 0
        self.update()
        
        # Xóa khỏi bộ nhớ sau khi ẩn xong
        await asyncio.sleep(0.6)
        if self in self.app_page.overlay:
            self.app_page.overlay.remove(self)
            self.app_page.update()

def show_top_notification(page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=SECONDARY_COLOR):
    """Hàm gọi nhanh thông báo"""
    notif = TopNotification(page, title, message, duration_ms, color)
    page.overlay.append(notif)
    page.update()