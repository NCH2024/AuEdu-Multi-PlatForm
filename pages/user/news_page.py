import flet as ft
from core.theme import current_theme
from core.config import get_supabase_client
from core.helper import process_image_url
from components.options.open_browser import open_browser

class NewsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 20

        self.news_data = []
        self.offset = 0
        self.limit_initial = 10
        self.limit_more = 5
        self.has_more = True
        self.is_loading = False

        # LABEL TEST: Kiểm tra xem Route có mở thành công trang này không
        self.test_label = ft.Text("Đang kiểm tra Route NewsPage...", size=20, color=ft.Colors.RED_500, weight=ft.FontWeight.BOLD)
        
        # Gán nội dung ban đầu là label test
        self.content = ft.Container(content=self.test_label, alignment=ft.Alignment(0,0), expand=True)

    def did_mount(self):
        # Khi trang đã được "neo" an toàn vào Route, ta mới dựng UI thật và gọi dữ liệu
        self.build_initial_ui()
        self.app_page.run_task(self.load_news_data)

    def build_initial_ui(self):
        self.list_view = ft.Column(spacing=15)
        self.load_more_btn = ft.Container(
            padding=10, border_radius=8, bgcolor=ft.Colors.with_opacity(0.1, current_theme.secondary),
            ink=True, on_click=self.on_load_more, alignment=ft.Alignment(0,0),
            content=ft.Text("Xem thêm thông báo", color=current_theme.secondary, weight=ft.FontWeight.BOLD),
            visible=False
        )
        self.loading_indicator = ft.Container(content=ft.ProgressRing(width=20, height=20, color=current_theme.secondary), alignment=ft.Alignment(0,0), visible=True, margin=10)

        header = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=current_theme.text_main, on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/home")),
            ft.Text("Tất cả thông báo", size=20, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        ], alignment=ft.MainAxisAlignment.START)

        # Ghi đè label test bằng UI hoàn chỉnh
        self.content = ft.Column([
            header,
            ft.Container(height=10),
            self.list_view,
            ft.Container(content=self.loading_indicator, alignment=ft.Alignment(0,0)),
            ft.Container(content=self.load_more_btn, alignment=ft.Alignment(0,0)),
            ft.Container(height=40)
        ], scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.update()

    def get_click_handler(self, item):
        async def on_click(e):
            link = item.get("link_web")
            if link and str(link).strip() != "":
                await open_browser(self.app_page, link, item.get("tieu_de", "Thông báo"))
            else:
                def close_dlg(e):
                    dlg.open = False
                    self.app_page.update()
                
                img_src = process_image_url(item.get("hinh_anh"))

                dlg_content = ft.Column([
                    ft.Image(src=img_src, width=300, height=150, fit=ft.BoxFit.COVER, border_radius=8),
                    ft.Text(item.get("noi_dung", "Nội dung chưa cập nhật"), size=13, color=current_theme.text_main)
                ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO)

                dlg = ft.AlertDialog(
                    title=ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary),
                    content=dlg_content, actions=[ft.TextButton("Đóng lại", on_click=close_dlg)], shape=ft.RoundedRectangleBorder(radius=12), bgcolor=current_theme.surface_color
                )
                self.app_page.overlay.append(dlg)
                dlg.open = True
                self.app_page.update()
        return on_click

    def render_news(self):
        self.list_view.controls.clear()
        for item in self.news_data:
            img_src = process_image_url(item.get("hinh_anh"))
            img_widget = ft.Image(src=img_src, width=80, height=80, fit=ft.BoxFit.COVER, border_radius=8)

            card = ft.Container(
                padding=15, border_radius=12, bgcolor=current_theme.surface_color, border=ft.Border.all(1, current_theme.divider_color),
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color=ft.Colors.with_opacity(0.03, ft.Colors.BLACK), offset=ft.Offset(0, 4)),
                ink=True, on_click=self.get_click_handler(item),
                content=ft.Row([
                    img_widget,
                    ft.Column([
                        ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.W_600, size=14, color=current_theme.text_main, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=current_theme.text_muted), ft.Text(item.get("created_at", "N/A")[:10], size=12, color=current_theme.text_muted)], spacing=4)
                    ], spacing=6, expand=True),
                    ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED if item.get("link_web") and str(item.get("link_web")).strip() != "" else ft.Icons.ARROW_FORWARD_IOS_ROUNDED, size=18, color=current_theme.text_muted)
                ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=15)
            )
            self.list_view.controls.append(card)
        if self.page: self.update() 

    async def fetch_data(self, fetch_limit, fetch_offset):
        try:
            async with await get_supabase_client() as client:
                res = await client.get("/thongbao", params={"select": "*", "order": "created_at.desc", "limit": str(fetch_limit), "offset": str(fetch_offset)})
                res.raise_for_status()
                return res.json()
        except Exception as e:
            print("NEWS ERROR:", e)
            return []

    async def load_news_data(self):
        self.is_loading = True
        self.loading_indicator.visible = True
        self.load_more_btn.visible = False
        if self.page: self.update()

        data = await self.fetch_data(self.limit_initial, 0)
        self.news_data = data
        self.offset = len(data)
        
        if len(data) < self.limit_initial:
            self.has_more = False

        self.loading_indicator.visible = False
        self.load_more_btn.visible = self.has_more
        self.is_loading = False
        self.render_news()

    async def on_load_more(self, e):
        if not self.is_loading and self.has_more:
            await self.load_more_data()

    async def load_more_data(self):
        self.is_loading = True
        self.load_more_btn.content = ft.ProgressRing(width=15, height=15, color=current_theme.secondary)
        if self.page: self.update()

        new_data = await self.fetch_data(self.limit_more, self.offset)
        
        if new_data:
            self.news_data.extend(new_data)
            self.offset += len(new_data)
            if len(new_data) < self.limit_more:
                self.has_more = False
        else:
            self.has_more = False

        self.load_more_btn.content = ft.Text("Xem thêm thông báo", color=current_theme.secondary, weight=ft.FontWeight.BOLD)
        self.load_more_btn.visible = self.has_more
        self.is_loading = False
        self.render_news()