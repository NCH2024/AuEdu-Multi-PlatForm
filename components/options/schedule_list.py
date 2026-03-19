import flet as ft
import datetime
import asyncio
from core.theme import PRIMARY_COLOR


class ScheduleDetailList(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True

        self.list_view = ft.ListView(
            spacing=0,
            expand=True,
            auto_scroll=False,
        )
        self.content = self.list_view

        self.date_refs = {}                
        self.current_highlighted_date = None
        self.date_offsets = {}             

    def render_data(self, display_schedules: list):
        self.list_view.controls.clear()
        self.date_refs.clear()
        self.date_offsets.clear()
        self.current_highlighted_date = None

        if not display_schedules:
            self.list_view.controls.append(
                ft.Container(
                    padding=40,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        "Không có lịch trình trong khoảng thời gian này.",
                        italic=True,
                        color=ft.Colors.GREY_500,
                    ),
                )
            )
            self.list_view.update()
            return

        grouped = {}
        for s in display_schedules:
            d = s["date"]
            grouped.setdefault(d, []).append(s)

        day_names = ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"]
        HEADER_HEIGHT = 45 
        CARD_HEIGHT = 120
        offset = 0

        for d in sorted(grouped):
            self.date_offsets[d] = offset

            header_text = ft.Container(
                bgcolor=PRIMARY_COLOR,
                border_radius=15,
                padding=ft.Padding(12, 4, 12, 4),
                content=ft.Text(
                    f"{day_names[d.weekday()]}, {d.strftime('%d/%m')}",
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                    size=12,
                ),
            )
            
            header = ft.Container(
                margin=ft.Margin(left=-15, top=10, right=0, bottom=5),
                content=ft.Row(
                    spacing=0,
                    controls=[
                        ft.Container(width=30, height=1, bgcolor=PRIMARY_COLOR),
                        header_text,
                    ],
                ),
            )
            self.list_view.controls.append(header)
            self.date_refs[d] = {"header_txt": header_text, "cards": []}
            offset += HEADER_HEIGHT

            for s in grouped[d]:
                card = ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border_radius=20,
                    border=ft.Border(
                        left=ft.BorderSide(8, s["type_color"]),
                        top=None,
                        right=None,
                        bottom=None,
                    ),
                    margin=ft.Margin(left=15, top=0, right=0, bottom=15),
                    padding=ft.Padding(15, 12, 15, 12),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                s["subject"],
                                weight=ft.FontWeight.BOLD,
                                size=14,
                                color=ft.Colors.BLACK_87,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Tiết :",
                                        color=ft.Colors.GREY_500,
                                        size=12,
                                        width=80,
                                    ),
                                    ft.Text(
                                        s["time"],
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLACK_87,
                                    ),
                                ]
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Phòng :",
                                        color=ft.Colors.GREY_500,
                                        size=12,
                                        width=80,
                                    ),
                                    ft.Text(
                                        s["room"],
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLACK_87,
                                    ),
                                ]
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        "Lớp :",
                                        color=ft.Colors.GREY_500,
                                        size=12,
                                        width=80,
                                    ),
                                    ft.Text(
                                        s["class_name"],
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLACK_87,
                                    ),
                                ]
                            ),
                        ],
                    ),
                )
                self.list_view.controls.append(card)
                self.date_refs[d]["cards"].append(card)
                offset += CARD_HEIGHT

        self.list_view.update()

    def highlight_and_scroll(self, target_date: datetime.date, page: ft.Page):
        if (
            self.current_highlighted_date
            and self.current_highlighted_date in self.date_refs
        ):
            old = self.date_refs[self.current_highlighted_date]
            old["header_txt"].bgcolor = PRIMARY_COLOR
            for c in old["cards"]:
                c.bgcolor = ft.Colors.WHITE

        if target_date in self.date_refs:
            new = self.date_refs[target_date]
            new["header_txt"].bgcolor = ft.Colors.RED_500
            for c in new["cards"]:
                c.bgcolor = ft.Colors.with_opacity(0.1, PRIMARY_COLOR)

            self.list_view.update()

            offset = self.date_offsets.get(target_date, 0)
            page.run_task(self._async_scroll, offset)

        self.current_highlighted_date = target_date

    async def _async_scroll(self, offset_val: float):
        await asyncio.sleep(0.1)
        try:
            if self.list_view.page: 
                await self.list_view.scroll_to(offset=offset_val, duration=400)
        except Exception:
            pass