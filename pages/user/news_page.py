import flet as ft
from core.theme import current_theme
from core.config import get_supabase_client
from components.options.open_browser import open_browser
from components.options.news_image import build_news_image


class NewsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(20)

        self.news_data = []
        self.offset = 0
        self.limit_initial = 10
        self.limit_more = 5
        self.has_more = True
        self.is_loading = False

        self.list_view = ft.ListView(spacing=12, expand=True)

        self.load_more_btn = ft.Container(
            padding=ft.Padding.all(12),
            border_radius=ft.BorderRadius.all(10),
            bgcolor=ft.Colors.with_opacity(0.1, current_theme.secondary),
            ink=True, on_click=self.on_load_more,
            alignment=ft.Alignment(0, 0),
            content=ft.Text("Xem thêm thông báo", color=current_theme.secondary,
                            weight=ft.FontWeight.BOLD),
            visible=False
        )

        self.loading_indicator = ft.Container(
            content=ft.ProgressRing(width=24, height=24, color=current_theme.secondary,
                                    stroke_width=3),
            alignment=ft.Alignment(0, 0),
            visible=True,
            margin=ft.Margin.all(16)
        )

        self.content = self.build_ui()

    def did_mount(self):
        self.app_page.run_task(self.load_news_data)

    def apply_theme(self):
        self.load_more_btn.bgcolor = ft.Colors.with_opacity(0.1, current_theme.secondary)
        self.load_more_btn.content.color = current_theme.secondary
        self.loading_indicator.content.color = current_theme.secondary
        self.content = self.build_ui()
        self.render_news()
        if self.page:
            self.update()

    def build_ui(self):
        header = ft.Row([
            ft.IconButton(
                ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED,
                icon_color=current_theme.text_main,
                on_click=lambda e: self.app_page.run_task(
                    self.app_page.push_route, "/user/home"
                )
            ),
            ft.Text("Tất cả thông báo", size=20,
                    weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        ], alignment=ft.MainAxisAlignment.START)

        return ft.Column([
            header,
            ft.Container(height=10),
            self.list_view,
            self.loading_indicator,
            self.load_more_btn,
            ft.Container(height=40)
        ], expand=True)

    def _build_detail_dialog(self, item: dict) -> ft.AlertDialog:
        img_widget = build_news_image(item.get("hinh_anh"), width=320, height=160, border_radius=10)

        dlg = ft.AlertDialog(
            title=ft.Text(str(item.get("tieu_de", "Thông báo")), weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary),
            # FIX: Thay vì dùng Scroll bên trong Column, cấu hình Dialog hỗ trợ cuộn (scrollable)
            content=ft.Container(
                width=360,
                # Đặt chiều cao tối đa để không tràn màn hình
                height=400, 
                content=ft.ListView(
                    controls=[
                        img_widget,
                        ft.Container(height=10),
                        ft.Text(str(item.get("noi_dung", "Nội dung chưa cập nhật")), size=14, color=current_theme.text_main)
                    ], spacing=0
                )
            ),
            actions=[ft.TextButton("Đóng lại", on_click=lambda e: self.app_page.close(dlg))],
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=current_theme.surface_color
        )
        return dlg

    def get_click_handler(self, item: dict):
        async def on_click(e):
            try:
                link = item.get("link_web")
                has_link = bool(link and str(link).strip() not in ("", "None"))
                if has_link:
                    await open_browser(self.app_page, str(link).strip(),
                                       item.get("tieu_de", "Thông báo"))
                else:
                    dlg = self._build_detail_dialog(item)
                    self.app_page.open(dlg)
            except Exception as ex:
                print(f"Lỗi click news: {ex}")
        return on_click

    def _build_news_card(self, item: dict) -> ft.Container:
        tieu_de = str(item.get("tieu_de", "Không có tiêu đề"))
        created_at = item.get("created_at", "")
        date_str = str(created_at)[:10] if created_at and len(str(created_at)) >= 10 else "N/A"
        link_web = item.get("link_web", "")
        has_link = bool(link_web and str(link_web).strip() not in ("", "None"))

        img_widget = build_news_image(item.get("hinh_anh"), width=80, height=80,
                                      border_radius=8)

        meta_controls = [
            ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, size=12, color=current_theme.text_muted),
            ft.Text(date_str, size=12, color=current_theme.text_muted),
        ]
        if has_link:
            meta_controls.append(
                ft.Container(
                    margin=ft.Margin.only(left=8),
                    padding=ft.Padding(6, 2, 6, 2),
                    border_radius=6,
                    bgcolor=ft.Colors.with_opacity(0.12, current_theme.accent),
                    content=ft.Text("Có đường dẫn", size=10,
                                    color=current_theme.accent, weight=ft.FontWeight.BOLD)
                )
            )

        return ft.Container(
            padding=ft.Padding.all(14),
            bgcolor=current_theme.surface_color,
            border_radius=14,
            border=ft.Border.all(1, current_theme.divider_color),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=8,
                color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK),
                offset=ft.Offset(0, 3)
            ),
            ink=True,
            on_click=self.get_click_handler(item),
            content=ft.Row([
                img_widget,
                ft.Container(width=12),
                ft.Column([
                    ft.Text(
                        tieu_de,
                        weight=ft.FontWeight.W_600, size=14,
                        color=current_theme.text_main,
                        max_lines=3,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    ft.Container(height=4),
                    ft.Row(meta_controls, spacing=4,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=0, expand=True, alignment=ft.MainAxisAlignment.CENTER),
                ft.Icon(
                    ft.Icons.OPEN_IN_NEW_ROUNDED if has_link
                    else ft.Icons.CHEVRON_RIGHT_ROUNDED,
                    size=18, color=current_theme.text_muted
                )
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        )

    def render_news(self):
        self.list_view.controls.clear()

        if not self.news_data:
            self.list_view.controls.append(ft.Container(
                padding=ft.Padding.all(40),
                alignment=ft.Alignment(0, 0),
                content=ft.Column([
                    ft.Icon(ft.Icons.NOTIFICATIONS_OFF_OUTLINED,
                            color=current_theme.divider_color, size=48),
                    ft.Container(height=8),
                    ft.Text("Không có thông báo nào.", size=14,
                            color=current_theme.text_muted, italic=True)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
            ))
        else:
            for item in self.news_data:
                try:
                    self.list_view.controls.append(self._build_news_card(item))
                except Exception as e:
                    print(f"Lỗi render card: {e}")
                    continue

        if self.page:
            self.update()

    async def fetch_data(self, fetch_limit: int, fetch_offset: int) -> list:
        try:
            client = await get_supabase_client()
            res = await client.get(
                "/thongbao",
                params={
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": str(fetch_limit),
                    "offset": str(fetch_offset)
                }
            )
            res.raise_for_status()
            data = res.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"NEWS fetch lỗi: {e}")
            return []

    async def load_news_data(self):
        try:
            self.is_loading = True
            self.loading_indicator.visible = True
            self.load_more_btn.visible = False
            if self.page:
                self.update()

            data = await self.fetch_data(self.limit_initial, 0)
            self.news_data = data
            self.offset = len(data)
            self.has_more = len(data) >= self.limit_initial

            self.loading_indicator.visible = False
            self.load_more_btn.visible = self.has_more
            self.is_loading = False
            self.render_news()

        except Exception as e:
            print(f"Lỗi load_news_data: {e}")
            self.loading_indicator.visible = False
            if self.page:
                self.update()

    async def on_load_more(self, e):
        if not self.is_loading and self.has_more:
            await self.load_more_data()

    async def load_more_data(self):
        try:
            self.is_loading = True
            self.load_more_btn.content = ft.ProgressRing(
                width=16, height=16,
                color=current_theme.secondary, stroke_width=2
            )
            if self.page:
                self.update()

            new_data = await self.fetch_data(self.limit_more, self.offset)
            if new_data:
                self.news_data.extend(new_data)
                self.offset += len(new_data)
                self.has_more = len(new_data) >= self.limit_more
            else:
                self.has_more = False

            self.load_more_btn.content = ft.Text(
                "Xem thêm thông báo",
                color=current_theme.secondary, weight=ft.FontWeight.BOLD
            )
            self.load_more_btn.visible = self.has_more
            self.is_loading = False
            self.render_news()

        except Exception as e:
            print(f"Lỗi load_more: {e}")
            self.is_loading = False
            self.load_more_btn.content = ft.Text("Lỗi, thử lại", color=ft.Colors.RED_500)
            if self.page:
                self.update()