import flet as ft
import json
import asyncio
import time
import datetime
from flet import UrlLauncher
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification
from core.theme import current_theme
from core.config import get_supabase_client

class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0 

        self.gv_name = "Giảng viên"
        self.gv_id = "N/A"
        self.thongbao_data = []
        self.tkb_data = []
        self.today_data = None
        self.is_loading = True

        # Khởi tạo UI chuẩn theo cấu trúc của AboutPage
        self.content = self.build_ui()
        self.app_page.run_task(self.load_data)

    def apply_theme(self):
        self.content = self.build_ui()
        if self.page: self.update()

    def create_skeleton(self, width=None, height=20, expand=False, is_circle=False, border_radius=4):
        return ft.Container(width=width, height=height, expand=expand, bgcolor=current_theme.divider_color, border_radius=height/2 if is_circle else border_radius)

    def get_news_click_handler(self, item):
        async def on_click(e):
            link = item.get("link_web")
            if link and str(link).strip() != "":
                # Gọi UrlLauncher chuẩn xác bằng await như AboutPage
                await UrlLauncher().launch_url(str(link).strip()) 
            else:
                def close_dlg(e):
                    dlg.open = False
                    self.app_page.update()
                
                img_src = item.get("hinh_anh")
                if not img_src or str(img_src).strip() == "" or not str(img_src).startswith("http"):
                    img_src = "icon.png"

                dlg_content = ft.Column([
                    ft.Image(src=img_src, width=300, height=150, fit=ft.BoxFit.COVER, border_radius=8),
                    ft.Text(item.get("noi_dung", "Nội dung chưa cập nhật"), size=13, color=current_theme.text_main)
                ], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO)

                dlg = ft.AlertDialog(title=ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary), content=dlg_content, actions=[ft.TextButton("Đóng lại", on_click=close_dlg)], shape=ft.RoundedRectangleBorder(radius=12), bgcolor=current_theme.surface_color)
                self.app_page.overlay.append(dlg)
                dlg.open = True
                self.app_page.update()
        return on_click

    def build_ui(self):
        now = datetime.datetime.now()
        greeting = "Chào buổi sáng" if now.hour < 12 else "Chào buổi chiều" if now.hour < 18 else "Chào buổi tối"
        
        def make_pro_card(content, padding=20, ink=False, on_click=None):
            return ft.Container(
                content=content, padding=padding, border_radius=16,
                bgcolor=current_theme.surface_color, border=ft.Border.all(1, current_theme.divider_color),
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color=ft.Colors.with_opacity(0.03, ft.Colors.BLACK), offset=ft.Offset(0, 4)),
                ink=ink, on_click=on_click
            )

        header_section = ft.Row([
            ft.Column([
                ft.Text(f"{greeting},", size=14, color=current_theme.text_muted, weight=ft.FontWeight.W_500),
                ft.Text(f"GV. {self.gv_name} 👋", size=24, weight=ft.FontWeight.W_800, color=current_theme.text_main),
                ft.Text(f"Hôm nay là {now.strftime('%d/%m/%Y')} • Chúc bạn ngày mới hiệu quả!", size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500)
            ], spacing=0, expand=True),
            ft.Container(padding=10, border_radius=12, bgcolor=current_theme.surface_variant, content=ft.Icon(ft.Icons.CALENDAR_TODAY_ROUNDED, color=current_theme.secondary, size=24))
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        def create_stat_card(icon, title, value, color_theme, route):
            return ft.Container(col={"xs": 6, "sm": 6, "md": 3, "lg": 3}, content=make_pro_card(padding=15, ink=True, on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r), content=ft.Column([ft.Row([ft.Container(width=36, height=36, border_radius=10, bgcolor=ft.Colors.with_opacity(0.1, color_theme), content=ft.Icon(icon, color=color_theme, size=18), alignment=ft.Alignment(0,0)), ft.Text(str(value) if not self.is_loading else "...", size=22, weight=ft.FontWeight.BOLD, color=current_theme.text_main, expand=True, text_align=ft.TextAlign.RIGHT)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=5), ft.Text(title, size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_600)], spacing=0)))

        total_classes = len(self.tkb_data) if self.tkb_data else 0
        today_total = len(self.today_data["classes"]) if self.today_data and "classes" in self.today_data else 0
        today_done = sum(1 for c in self.today_data["classes"] if c.get("da_diem_danh")) if today_total > 0 else 0
        news_count = len(self.thongbao_data) if self.thongbao_data else 0

        stats_row = ft.ResponsiveRow([create_stat_card(ft.Icons.CLASS_OUTLINED, "Tổng lớp học kỳ", total_classes, current_theme.primary, "/user/schedule"), create_stat_card(ft.Icons.EVENT_NOTE_ROUNDED, "Ca dạy hôm nay", today_total, ft.Colors.ORANGE_500, "/user/attendance"), create_stat_card(ft.Icons.CHECK_CIRCLE_OUTLINE, "Đã điểm danh", today_done, ft.Colors.GREEN_500, "/user/stats"), create_stat_card(ft.Icons.CAMPAIGN_OUTLINED, "Thông báo mới", news_count, ft.Colors.RED_400, "/user/news")], run_spacing=15, spacing=15)

        progress_val = (today_done / today_total) if today_total > 0 else 1.0
        progress_text = f"Hoàn thành {today_done}/{today_total} ca dạy" if today_total > 0 else "Hôm nay bạn được nghỉ ngơi!"
        progress_section = ft.Column([ft.Row([ft.Text("Tiến độ hôm nay", size=13, weight=ft.FontWeight.BOLD, color=current_theme.text_main), ft.Text(f"{int(progress_val * 100)}%", size=13, weight=ft.FontWeight.BOLD, color=current_theme.secondary)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.ProgressBar(value=progress_val, color=current_theme.secondary, bgcolor=current_theme.surface_variant, height=8, border_radius=4), ft.Text(progress_text, size=11, color=current_theme.text_muted, italic=True)], spacing=5)

        today_timeline = ft.Column(spacing=0)
        if self.is_loading:
            for _ in range(2): today_timeline.controls.append(ft.Container(padding=10, content=ft.Row([self.create_skeleton(width=40, height=40, is_circle=True), ft.Column([self.create_skeleton(width=200, height=14), self.create_skeleton(width=100, height=12)], spacing=5)])))
        elif not self.today_data or not self.today_data.get("classes"):
            today_timeline.controls.append(ft.Container(padding=ft.Padding(0, 30, 0, 30), alignment=ft.Alignment(0,0), content=ft.Column([ft.Icon(ft.Icons.COFFEE_ROUNDED, color=current_theme.divider_color, size=50), ft.Text("Trống lịch. Thời gian tuyệt vời để nạp lại năng lượng!", size=13, color=current_theme.text_muted, italic=True)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)))
        else:
            now_time = datetime.datetime.now().time()
            for idx, c in enumerate(self.today_data["classes"]):
                is_done = c.get("da_diem_danh", False)
                status_color = current_theme.divider_color
                status_text = "Sắp diễn ra"
                badge_bg = current_theme.surface_variant
                badge_text_color = current_theme.text_muted
                
                if c.get("thoigianbd") and c.get("thoigiankt"):
                    try:
                        start_t = datetime.datetime.strptime(c["thoigianbd"], "%H:%M:%S").time()
                        end_t = datetime.datetime.strptime(c["thoigiankt"], "%H:%M:%S").time()
                        if start_t <= now_time <= end_t:
                            status_color = current_theme.accent; status_text = "Đang diễn ra"; badge_bg = ft.Colors.with_opacity(0.1, current_theme.accent); badge_text_color = current_theme.accent
                        elif now_time > end_t:
                            status_color = ft.Colors.GREEN_600 if is_done else ft.Colors.RED_500; status_text = "Hoàn thành" if is_done else "Chưa điểm danh!"; badge_bg = ft.Colors.with_opacity(0.1, status_color); badge_text_color = status_color
                    except: pass

                is_last = (idx == len(self.today_data["classes"]) - 1)
                
                timeline_card_content = ft.Container(expand=True, padding=15, margin=ft.Margin(0, 0, 0, 15), border_radius=12, bgcolor=current_theme.surface_variant, border=ft.Border.all(1, current_theme.divider_color), ink=True, on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/attendance"), content=ft.Column([ft.Row([ft.Text(c['ten_hp'], weight=ft.FontWeight.BOLD, size=14, color=current_theme.text_main, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Container(padding=ft.Padding(8, 2, 8, 2), border_radius=10, bgcolor=badge_bg, content=ft.Text(status_text, size=10, weight=ft.FontWeight.BOLD, color=badge_text_color))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Row([ft.Icon(ft.Icons.CLASS_, size=14, color=current_theme.text_muted), ft.Text(f"Lớp: {c['ten_lop']}", size=12, color=current_theme.text_muted), ft.Container(width=10), ft.Icon(ft.Icons.ROOM, size=14, color=current_theme.text_muted), ft.Text(f"Phòng: P.{c['phong_hoc']}", size=12, color=current_theme.text_muted)], spacing=4)], spacing=6))
                timeline_item = ft.Row([ft.Column([ft.Text(c.get("thoigianbd", "N/A")[:5], size=13, weight=ft.FontWeight.W_800, color=current_theme.text_main), ft.Container(width=12, height=12, border_radius=6, border=ft.Border.all(3, status_color), bgcolor=current_theme.surface_color), ft.Container(width=2, height=40, bgcolor=status_color if not is_last else ft.Colors.TRANSPARENT, margin=ft.Margin(0, -2, 0, -2))], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, width=50), timeline_card_content], vertical_alignment=ft.CrossAxisAlignment.START, spacing=10)
                today_timeline.controls.append(timeline_item)

        timeline_section = make_pro_card(ft.Column([ft.Row([ft.Icon(ft.Icons.MAP_ROUNDED, color=current_theme.secondary, size=20), ft.Text("LỊCH TRÌNH TRONG NGÀY", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14)]), ft.Divider(color=current_theme.divider_color, height=20), progress_section, ft.Container(height=10), today_timeline], spacing=0))

        def create_action_btn(icon, text, bg_color, text_color, route):
            return ft.Container(col={"xs": 6, "sm": 6, "md": 6, "lg": 6}, content=ft.Container(padding=15, border_radius=12, bgcolor=bg_color, ink=True, on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r), border=ft.Border.all(1, current_theme.divider_color) if bg_color == current_theme.surface_color else None, content=ft.Column([ft.Icon(icon, color=text_color, size=28), ft.Text(text, color=text_color, weight=ft.FontWeight.W_700, size=13)], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.START)))
        quick_actions_section = make_pro_card(ft.Column([ft.Row([ft.Icon(ft.Icons.BOLT_ROUNDED, color=ft.Colors.AMBER_500, size=20), ft.Text("TRUY CẬP NHANH", weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14)]), ft.Container(height=5), ft.ResponsiveRow([create_action_btn(ft.Icons.DOCUMENT_SCANNER_ROUNDED, "Điểm danh ngay", current_theme.secondary, ft.Colors.WHITE, "/user/attendance"), create_action_btn(ft.Icons.EDIT_CALENDAR_ROUNDED, "Lịch giảng dạy", current_theme.surface_color, current_theme.secondary, "/user/schedule"), create_action_btn(ft.Icons.ANALYTICS_ROUNDED, "Báo cáo tiến độ", current_theme.surface_color, current_theme.secondary, "/user/stats"), create_action_btn(ft.Icons.MANAGE_ACCOUNTS_ROUNDED, "Hồ sơ của tôi", current_theme.surface_color, current_theme.secondary, "/user/profile")], run_spacing=10, spacing=10)], spacing=5))

        news_list = ft.Column(spacing=0)
        if self.is_loading:
            for _ in range(3): news_list.controls.append(ft.Container(height=70, padding=10, content=ft.Row([self.create_skeleton(width=50, height=50, border_radius=8), ft.Column([self.create_skeleton(width=150, height=14), self.create_skeleton(width=80, height=10)], spacing=5)])))
        elif self.thongbao_data:
            for item in self.thongbao_data:
                img_src = item.get("hinh_anh")
                if not img_src or str(img_src).strip() == "" or not str(img_src).startswith("http"): img_src = "icon.png"
                img_widget = ft.Image(src=img_src, width=50, height=50, fit=ft.BoxFit.COVER, border_radius=8)

                news_list.controls.append(
                    ft.Container(
                        padding=ft.Padding(0, 12, 0, 12), border=ft.Border(bottom=ft.BorderSide(1, current_theme.divider_color)),
                        ink=True, on_click=self.get_news_click_handler(item),
                        content=ft.Row([
                            img_widget,
                            ft.Column([ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.W_600, size=13, color=current_theme.text_main, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS), ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=current_theme.text_muted), ft.Text(item.get("created_at", "N/A")[:10], size=11, color=current_theme.text_muted)], spacing=4)], spacing=4, expand=True),
                            ft.Icon(ft.Icons.OPEN_IN_NEW_ROUNDED if item.get("link_web") and str(item.get("link_web")).strip() != "" else ft.Icons.ARROW_FORWARD_IOS_ROUNDED, size=16, color=current_theme.text_muted)
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
                    )
                )
        else: news_list.controls.append(ft.Container(padding=20, alignment=ft.Alignment(0,0), content=ft.Text("Không có thông báo mới.", size=12, color=current_theme.text_muted, italic=True)))

        news_section = make_pro_card(ft.Column([ft.Row([ft.Row([ft.Icon(ft.Icons.CAMPAIGN_ROUNDED, color=ft.Colors.RED_400, size=20), ft.Text("BẢNG TIN HỌC VỤ", weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14)]), ft.Container(content=ft.Text("Xem tất cả", size=12, color=current_theme.secondary, weight=ft.FontWeight.BOLD), ink=True, on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/news"))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(height=5), news_list], spacing=0))

        dashboard_layout = ft.Column([header_section, ft.Container(height=10), stats_row, ft.Container(height=10), ft.ResponsiveRow([ft.Column([timeline_section], col={"xs": 12, "md": 12, "lg": 7, "xl": 8}), ft.Column([quick_actions_section, ft.Container(height=10), news_section], col={"xs": 12, "md": 12, "lg": 5, "xl": 4})], spacing=20, run_spacing=20)], spacing=0)
        
        # Trả về đối tượng giao diện thay vì set trực tiếp để không bị lỗi bất đồng bộ
        return ft.Column([ft.Container(height=10), dashboard_layout, ft.Container(height=40)], scroll=ft.ScrollMode.AUTO, expand=True)

    def render_data_to_ui(self, thongbao, tkb, today):
        self.thongbao_data = thongbao
        self.tkb_data = tkb
        self.today_data = today
        self.is_loading = False
        self.apply_theme()

    async def load_data(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_name = session_data.get("name", "Giảng viên")
            self.gv_id = session_data.get("id", "N/A")

        cached_news = safe_json_load(await prefs.get("cached_news"))
        cached_schedule = safe_json_load(await prefs.get(f"cached_home_schedule_{self.gv_id}"))
        cached_today = safe_json_load(await prefs.get(f"cached_today_{self.gv_id}"))
        last_sync = float(await prefs.get(f"last_sync_home_{self.gv_id}") or 0)
        
        current_time = time.time()
        if cached_news is not None and cached_schedule is not None and cached_today is not None:
            self.render_data_to_ui(cached_news, cached_schedule, cached_today)

        if current_time - last_sync < 0: return 
        try:
            async with await get_supabase_client() as client:
                res_tb = await client.get("/thongbao", params={"select": "*", "order": "created_at.desc", "limit": "3"})
                res_tb.raise_for_status()
                fresh_news = res_tb.json()

                fresh_schedule = []
                fresh_today = {"classes": []}

                if self.gv_id != "N/A":
                    res_tkb = await client.get("/thoikhoabieu", params={"select": "id,lop_id,lop(tenlop),hocphan(tenhocphan,sobuoi),hocky(namhoc,tenhocky)", "giangvien_id": f"eq.{self.gv_id}"})
                    res_tkb.raise_for_status()
                    all_tkb = res_tkb.json()

                    if all_tkb:
                        valid_hks = [s["hocky"] for s in all_tkb if s.get("hocky")]
                        if valid_hks:
                            namhocs = sorted(list(set(hk["namhoc"] for hk in valid_hks)), reverse=True)
                            fresh_schedule = [s for s in all_tkb if s.get("hocky") and s["hocky"]["namhoc"] == namhocs[0] and s["hocky"]["tenhocky"] == [hk for hk in valid_hks if hk["namhoc"] == namhocs[0]][0]["tenhocky"]]

                    today_date = datetime.datetime.now(datetime.timezone.utc).astimezone().date()
                    if all_tkb:
                        res_tiet = await client.get("/tkb_tiet", params={"select": "id,tkb_id,thu,phong_hoc,tiet(thoigianbd,thoigiankt)", "tkb_id": f"in.({','.join([str(x['id']) for x in all_tkb])})", "thu": f"eq.{today_date.weekday() + 2}", "order": "tiet(thoigianbd).asc"})
                        res_tiet.raise_for_status()
                        tiet_list = res_tiet.json()

                        if tiet_list:
                            res_dd = await client.get("/diemdanh", params={"select": "tkb_tiet_id", "tkb_tiet_id": f"in.({','.join([str(t['id']) for t in tiet_list])})", "ngay_diem_danh": f"eq.{today_date.isoformat()}"})
                            res_dd.raise_for_status()
                            dd_map = {str(d["tkb_tiet_id"]) for d in res_dd.json()}
                            
                            for t in tiet_list:
                                tkb_info = next((x for x in all_tkb if x["id"] == t["tkb_id"]), None)
                                if tkb_info: 
                                    fresh_today["classes"].append({
                                        "id": t["id"], "ten_hp": tkb_info.get("hocphan", {}).get("tenhocphan", "N/A"), "ten_lop": tkb_info.get("lop", {}).get("tenlop", "N/A"), "phong_hoc": t.get("phong_hoc", "N/A"), "thoigianbd": t.get("tiet", {}).get("thoigianbd"), "thoigiankt": t.get("tiet", {}).get("thoigiankt"), "da_diem_danh": str(t["id"]) in dd_map
                                    })

            await prefs.set("cached_news", json.dumps(fresh_news))
            await prefs.set(f"cached_home_schedule_{self.gv_id}", json.dumps(fresh_schedule))
            await prefs.set(f"cached_today_{self.gv_id}", json.dumps(fresh_today))
            await prefs.set(f"last_sync_home_{self.gv_id}", str(current_time))

            self.render_data_to_ui(fresh_news, fresh_schedule, fresh_today)
        except Exception as e: 
            show_top_notification(self.app_page, "Lỗi kết nối", "Không thể cập nhật bảng tin!", color=ft.Colors.ORANGE)
            print("HOME ERROR:", e)