import flet as ft
import traceback
from core.theme import current_theme
from core.config import get_supabase_client
from core.helper import process_image_url
from components.options.open_browser import open_browser

class NewsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        print("[DEBUG] NewsPage: Đang khởi tạo __init__")
        self.app_page = page
        self.expand = True
        self.padding = 20

        self.news_data = []
        self.offset = 0
        self.limit_initial = 10
        self.limit_more = 5
        self.has_more = True
        self.is_loading = False

        self.list_view = ft.Column(spacing=15)
        
        self.load_more_btn = ft.Container(
            padding=10, border_radius=8, bgcolor=ft.Colors.with_opacity(0.1, current_theme.secondary),
            ink=True, on_click=self.on_load_more, alignment=ft.Alignment(0,0),
            content=ft.Text("Xem thêm thông báo", color=current_theme.secondary, weight=ft.FontWeight.BOLD),
            visible=False
        )

        self.loading_indicator = ft.Container(
            content=ft.ProgressRing(width=20, height=20, color=current_theme.secondary), 
            alignment=ft.Alignment(0,0), 
            visible=True, 
            margin=10
        )

        self.content = self.build_ui()
        print("[DEBUG] NewsPage: Đã tạo xong UI rỗng")

    def did_mount(self):
        print("[DEBUG] NewsPage: did_mount kích hoạt -> Bắt đầu gọi load_news_data")
        self.app_page.run_task(self.load_news_data)

    def apply_theme(self):
        self.content = self.build_ui()
        if self.page: self.update()

    def build_ui(self):
        header = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW_ROUNDED, icon_color=current_theme.text_main, on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/home")),
            ft.Text("Tất cả thông báo (Debug Mode)", size=20, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        ], alignment=ft.MainAxisAlignment.START)

        return ft.Column([
            header,
            ft.Container(height=10),
            self.list_view,
            self.loading_indicator,
            self.load_more_btn,
            ft.Container(height=40)
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def create_safe_image(self, url, width, height, border_radius=8):
        fallback_ui = ft.Container(
            width=width, height=height, border_radius=border_radius, 
            bgcolor=current_theme.divider_color, alignment=ft.Alignment(0,0),
            content=ft.Icon(ft.Icons.BUG_REPORT, color=ft.Colors.RED) # Đổi icon bug để dễ nhận biết
        )
        if not url or str(url).strip() == "icon.png" or not str(url).startswith("http"):
            return fallback_ui
        return ft.Image(src=str(url), width=width, height=height, fit=ft.BoxFit.COVER, border_radius=border_radius, error_content=fallback_ui)

    def get_click_handler(self, item):
        async def on_click(e):
            print(f"[DEBUG] Người dùng vừa click vào thông báo: {item.get('id', 'N/A')}")
            try:
                link = item.get("link_web")
                if link and str(link).strip() != "" and str(link).strip() != "None":
                    await open_browser(self.app_page, link, item.get("tieu_de", "Thông báo"))
                else:
                    def close_dlg(e):
                        dlg.open = False
                        self.app_page.update()
                    try: img_src = process_image_url(item.get("hinh_anh"))
                    except Exception: img_src = ""

                    img_widget = self.create_safe_image(img_src, width=300, height=150)
                    dlg_content = ft.Column([
                        img_widget,
                        ft.Text(str(item.get("noi_dung", "Nội dung rỗng")), size=13, color=current_theme.text_main)
                    ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO)

                    dlg = ft.AlertDialog(
                        title=ft.Text(str(item.get("tieu_de", "Thông báo")), weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary),
                        content=dlg_content, actions=[ft.TextButton("Đóng lại", on_click=close_dlg)], 
                        shape=ft.RoundedRectangleBorder(radius=12), bgcolor=current_theme.surface_color
                    )
                    self.app_page.overlay.append(dlg)
                    dlg.open = True
                    self.app_page.update()
            except Exception as ex:
                print(f"[DEBUG ERROR] Lỗi khi xử lý click: {ex}")
                traceback.print_exc()
        return on_click

    def render_news(self):
        print(f"[DEBUG] Bắt đầu render_news(). Tổng số bản ghi đang có: {len(self.news_data)}")
        self.list_view.controls.clear()
        
        for idx, item in enumerate(self.news_data):
            try:
                print(f"[DEBUG] Đang xử lý bản ghi thứ {idx + 1} | Kiểu dữ liệu: {type(item)}")
                if not isinstance(item, dict):
                    print(f"[DEBUG WARNING] Bản ghi không phải là Dictionary: {item}")
                    continue # Bỏ qua nếu dữ liệu không phải dict

                print(f"      -> Dữ liệu thô: ID={item.get('id')}, Tiêu đề={str(item.get('tieu_de'))[:15]}...")

                try: img_src = process_image_url(item.get("hinh_anh"))
                except Exception as e_img:
                    print(f"      -> [LỖI ẢNH]: {e_img}")
                    img_src = ""
                
                img_widget = self.create_safe_image(img_src, width=80, height=80)
                
                tieu_de = str(item.get("tieu_de", "Không có tiêu đề"))
                created_at = item.get("created_at")
                created_at_str = str(created_at)[:10] if created_at and len(str(created_at)) >= 10 else "N/A"
                
                link_web = item.get("link_web")
                has_link = bool(link_web and str(link_web).strip() != "" and str(link_web).strip() != "None")

                card = ft.Container(
                    padding=15, border_radius=12, bgcolor=current_theme.surface_color, 
                    border=ft.Border.all(1, current_theme.divider_color),
                    ink=True, on_click=self.get_click_handler(item),
                    content=ft.Row([
                        img_widget,
                        ft.Column([
                            ft.Text(tieu_de, weight=ft.FontWeight.W_600, size=14, color=current_theme.text_main, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([
                                ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=current_theme.text_muted), 
                                ft.Text(created_at_str, size=12, color=current_theme.text_muted)
                            ], spacing=4)
                        ], spacing=6, expand=True),
                        ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED if has_link else ft.Icons.ARROW_FORWARD_IOS_ROUNDED, size=18, color=current_theme.text_muted)
                    ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=15)
                )
                self.list_view.controls.append(card)
                print(f"      -> Thêm thẻ {idx + 1} thành công vào list_view.")
                
            except Exception as e_card:
                print(f"[DEBUG ERROR] Lỗi render thẻ thứ {idx + 1}: {e_card}")
                traceback.print_exc()
                # Nếu thẻ phức tạp bị lỗi, in ra một thẻ báo lỗi màu đỏ để nhận diện
                self.list_view.controls.append(ft.Text(f"LỖI RENDER THẺ {idx + 1}", color=ft.Colors.RED_500))
        
        print(f"[DEBUG] Đã nạp xong {len(self.list_view.controls)} thẻ vào list_view. Chuẩn bị cập nhật giao diện...")
        if self.page: 
            self.update()
            print("[DEBUG] self.update() hoàn tất!")

    async def fetch_data(self, fetch_limit, fetch_offset):
        print(f"[DEBUG] Đang fetch API từ Supabase... Limit={fetch_limit}, Offset={fetch_offset}")
        try:
            async with await get_supabase_client() as client:
                res = await client.get("/thongbao", params={"select": "*", "order": "created_at.desc", "limit": str(fetch_limit), "offset": str(fetch_offset)})
                print(f"[DEBUG] Trạng thái API: {res.status_code}")
                res.raise_for_status()
                data = res.json()
                print(f"[DEBUG] Fetch thành công. Trả về kiểu: {type(data)}. Số lượng phần tử: {len(data) if isinstance(data, list) else 'N/A'}")
                return data
        except Exception as e:
            print(f"[DEBUG ERROR] Lỗi khi gọi API Supabase: {e}")
            traceback.print_exc()
            return []

    async def load_news_data(self):
        print("[DEBUG] Bắt đầu luồng load_news_data chính")
        try:
            self.is_loading = True
            self.loading_indicator.visible = True
            self.load_more_btn.visible = False
            if self.page: self.update()

            data = await self.fetch_data(self.limit_initial, 0)
            if not data or not isinstance(data, list): 
                print("[DEBUG WARNING] Dữ liệu trả về trống hoặc không phải List. Ép kiểu về []")
                data = []
            
            self.news_data = data
            self.offset = len(data)
            
            if len(data) < self.limit_initial:
                self.has_more = False

            self.loading_indicator.visible = False
            self.load_more_btn.visible = self.has_more
            self.is_loading = False
            
            print("[DEBUG] Chuẩn bị gọi render_news()")
            self.render_news()
        except Exception as e:
            print(f"[DEBUG ERROR] Lỗi to ở load_news_data: {e}")
            traceback.print_exc()
            self.loading_indicator.visible = False
            if self.page: self.update()

    async def on_load_more(self, e):
        print("[DEBUG] Nút Xem thêm được bấm")
        if not self.is_loading and self.has_more:
            await self.load_more_data()

    async def load_more_data(self):
        print("[DEBUG] Đang tải thêm dữ liệu...")
        try:
            self.is_loading = True
            self.load_more_btn.content = ft.ProgressRing(width=15, height=15, color=current_theme.secondary)
            if self.page: self.update()

            new_data = await self.fetch_data(self.limit_more, self.offset)
            
            if new_data and isinstance(new_data, list):
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
        except Exception as e:
            print(f"[DEBUG ERROR] Lỗi load_more_data: {e}")
            traceback.print_exc()
            self.is_loading = False
            self.load_more_btn.content = ft.Text("Lỗi, thử lại", color=ft.Colors.RED)
            if self.page: self.update()