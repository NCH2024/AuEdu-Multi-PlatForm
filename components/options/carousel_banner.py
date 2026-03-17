import flet as ft
from flet import UrlLauncher
import asyncio
from core.theme import SECONDARY_COLOR

class CarouselBanner(ft.Container):
    def __init__(self, page: ft.Page, items: list, width: int = 420, height: int = 80, interval: int = 4):
        super().__init__()
        self.app_page = page
        self.items = items
        self.banner_width = width
        self.banner_height = height
        self.interval = interval
        self.current_index = 0
        self.is_running = True

        self.width = width

        # Row chứa các banner, ẩn thanh cuộn để tự động trượt bằng code
        self.carousel_row = ft.Row(
            spacing=0,
            scroll="hidden", 
            width=self.banner_width,
            expand=False
        )

        # Row chứa các dấu chấm báo hiệu
        self.dots_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=5
        )

        self.build_items()

        # Cột dọc gộp Form trượt và Dấu chấm
        self.content = ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.carousel_row,
                self.dots_row
            ]
        )

    def build_items(self):
        for i, item in enumerate(self.items):
            # 1. Tạo Banner Card
            card = ft.Container(
                width=self.banner_width,
                height=self.banner_height,
                padding=ft.Padding(12, 10, 12, 10),
                bgcolor=ft.Colors.with_opacity(0.80, ft.Colors.WHITE),
                blur=5,
                border_radius=16,
                border=ft.Border.all(2, ft.Colors.WHITE),
                shadow=ft.BoxShadow(
                    spread_radius=1, blur_radius=10, 
                    color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK), offset=ft.Offset(0, 4)
                ),
                ink=True,
                on_click=self.create_click_handler(item.get("url", "")),
                content=ft.Row(
                    spacing=15,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        # Ảnh quảng cáo / Thông báo
                        ft.Container(
                            width=60, height=60,
                            border_radius=10,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            content=ft.Image(src=item.get("image", ""), fit=ft.BoxFit.COVER, expand=True)
                        ),
                        # Nội dung chữ
                        ft.Column(
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=2,
                            controls=[
                                ft.Text(item.get("title", ""), weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                                ft.Text(item.get("subtitle", ""), color=ft.Colors.GREY_700, size=11, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                            ]
                        ),
                        # Mũi tên điều hướng
                        ft.Icon(ft.Icons.ARROW_FORWARD_IOS_ROUNDED, color=SECONDARY_COLOR, size=14)
                    ]
                )
            )
            self.carousel_row.controls.append(card)

            # 2. Tạo Dấu chấm (Dot) với Animation kéo dài mượt mà
            # SỬA LỖI: Cập nhật thành ft.Animation() chuẩn
            dot = ft.Container(
                width=16 if i == 0 else 6,
                height=6,
                border_radius=4,
                bgcolor=SECONDARY_COLOR if i == 0 else ft.Colors.GREY_400,
                animate=ft.Animation(duration=300, curve=ft.AnimationCurve.EASE_IN_OUT)
            )
            self.dots_row.controls.append(dot)

    def create_click_handler(self, url):
        async def on_click(e):
            if url:
                try:
                    await UrlLauncher().launch_url(url)
                except Exception as ex:
                    print(f"Lỗi mở link: {ex}")
        return on_click

    def update_dots(self):
        for i, dot in enumerate(self.dots_row.controls):
            if i == self.current_index:
                dot.width = 16
                dot.bgcolor = SECONDARY_COLOR
            else:
                dot.width = 6
                dot.bgcolor = ft.Colors.GREY_400
        self.dots_row.update()

    def did_mount(self):
        """Kích hoạt vòng lặp trượt tự động khi Component được gắn lên màn hình"""
        self.is_running = True
        if len(self.items) > 1:
            self.app_page.run_task(self.auto_scroll)

    def will_unmount(self):
        """Hủy vòng lặp khi chuyển sang trang khác để tiết kiệm RAM"""
        self.is_running = False

    async def auto_scroll(self):
        """Logic tự động trượt qua từng thẻ"""
        await asyncio.sleep(self.interval)
        while self.is_running and getattr(self, "page", None):
            self.current_index += 1
            if self.current_index >= len(self.items):
                self.current_index = 0
            
            self.update_dots()
            
            # Tính toán độ lệch (offset) để trượt tới thẻ tiếp theo
            offset = self.current_index * self.banner_width
            
            # SỬA LỖI: Thêm await vì scroll_to là coroutine
            try:
                await self.carousel_row.scroll_to(offset=offset, duration=600, curve=ft.AnimationCurve.EASE_IN_OUT)
            except Exception as e:
                print(f"Lỗi cuộn trang: {e}")
                
            await asyncio.sleep(self.interval)