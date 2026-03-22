import flet as ft
import json
import asyncio
import time
import datetime
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification
from core.theme import current_theme
from core.config import get_supabase_client


class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0 # Loại bỏ margin dư thừa

        # ==========================================
        # KHO LƯU TRỮ DỮ LIỆU (STATE)
        # ==========================================
        self.gv_name = "Giảng viên"
        self.gv_id = "N/A"
        self.thongbao_data = []
        self.tkb_data = []
        self.today_data = None
        self.is_loading = True

        # Vẽ UI ngay lập tức với giao diện Xương (Skeleton)
        self.build_ui()
        self.app_page.run_task(self.load_data)

    def apply_theme(self):
        """Hàm này được Dashboard gọi khi đổi màu/sáng tối. Nó vẽ lại UI cực mượt."""
        self.build_ui()
        if self.page: self.update()

    def create_skeleton(self, width=None, height=20, expand=False, is_circle=False, border_radius=4):
        return ft.Container(
            width=width, height=height, expand=expand,
            bgcolor=current_theme.divider_color, 
            border_radius=height/2 if is_circle else border_radius
        )
    # ==========================================
    # LOGIC VẼ GIAO DIỆN PHẲNG (KHÔNG NESTED CONTAINER)
    # ==========================================
    def build_ui(self):
        # 1. HỒ SƠ GIẢNG VIÊN
        info_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=current_theme.secondary, size=20), ft.Text("HỒ SƠ CỦA TÔI", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13)]),
            ft.Divider(color=current_theme.divider_color, height=1),
            ft.Row([
                ft.Container(width=50, height=50, border_radius=25, bgcolor=current_theme.primary, content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=25), alignment=ft.Alignment(0,0)),
                ft.Column([
                    ft.Text(f"GV. {self.gv_name}", size=16, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                    ft.Text(f"Mã cán bộ: {self.gv_id}  •  Khoa: CNTT", size=12, color=current_theme.text_muted),
                ], spacing=2)
            ]) if not self.is_loading else ft.Row([self.create_skeleton(width=50, height=50, is_circle=True), ft.Column([self.create_skeleton(width=150, height=18), self.create_skeleton(width=100, height=14)], spacing=5)])
        ], spacing=15)

        # 2. HÔM NAY CỦA BẠN
        today_content_col = ft.Column(spacing=8)
        if self.is_loading:
            today_content_col.controls.extend([self.create_skeleton(width=200, height=16), self.create_skeleton(height=60, border_radius=8)])
        elif not self.today_data or not self.today_data.get("classes"):
            today_content_col.controls.append(ft.Row([ft.Icon(ft.Icons.NIGHTLIGHT_ROUND, color=current_theme.text_muted, size=18), ft.Text("Hôm nay bạn không có lịch lên lớp. Hãy nghỉ ngơi nhé!", size=13, color=current_theme.text_main, italic=True, expand=True)]))
        else:
            classes = self.today_data["classes"]
            today_content_col.controls.append(ft.Text(f"Bạn có {len(classes)} ca dạy hôm nay.", weight=ft.FontWeight.W_500, size=13, color=current_theme.text_main))
            now_time = datetime.datetime.now().time()
            current_class = None
            reminders = []
            
            for c in classes:
                if c.get("thoigianbd") and c.get("thoigiankt"):
                    try:
                        start_t = datetime.datetime.strptime(c["thoigianbd"], "%H:%M:%S").time()
                        end_t = datetime.datetime.strptime(c["thoigiankt"], "%H:%M:%S").time()
                        if start_t <= now_time <= end_t: current_class = c
                        elif now_time > end_t and not c["da_diem_danh"]: reminders.append(f"⚠️ Quên điểm danh: Lớp {c['ten_lop']} ({c['ten_hp']})")
                        elif start_t > now_time:
                            if (datetime.datetime.combine(datetime.date.today(), start_t) - datetime.datetime.combine(datetime.date.today(), now_time)).total_seconds() < 1800 and not c["da_diem_danh"]: reminders.append(f"⏳ Sắp diễn ra: Lớp {c['ten_lop']} - Nhớ điểm danh nhé!")
                    except: pass
                        
            if current_class:
                today_content_col.controls.append(
                    ft.Container(bgcolor=current_theme.surface_color, padding=12, border_radius=8, border=ft.Border.all(1, current_theme.divider_color), content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, color=current_theme.accent, size=16), ft.Text("ĐANG DIỄN RA", color=current_theme.accent, weight=ft.FontWeight.BOLD, size=11)]),
                        ft.Text(f"{current_class['ten_hp']} - Lớp {current_class['ten_lop']}", weight=ft.FontWeight.BOLD, size=14, color=current_theme.text_main),
                        ft.Row([ft.Icon(ft.Icons.ROOM, size=12, color=current_theme.text_muted), ft.Text(f"Phòng: {current_class['phong_hoc']}", size=12, color=current_theme.text_muted)], spacing=4)
                    ], spacing=3))
                )
            if reminders:
                today_content_col.controls.append(ft.Container(bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_500), padding=10, border_radius=8, content=ft.Column([ft.Text(r, size=12, color=ft.Colors.RED_700 if "Quên" in r else ft.Colors.ORANGE_800, weight=ft.FontWeight.W_500) for r in reminders], spacing=4)))
            elif not current_class:
                today_content_col.controls.append(ft.Text("Mọi việc hôm nay đang ổn thỏa!", size=12, color=ft.Colors.GREEN_700, italic=True))

        today_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.WB_SUNNY_ROUNDED, color=current_theme.accent, size=22), ft.Text("HÔM NAY CỦA BẠN", weight=ft.FontWeight.BOLD, color=current_theme.accent, size=13)]),
            ft.Divider(color=current_theme.divider_color, height=1), today_content_col
        ], spacing=15)

        # 3. PHÂN CÔNG LỚP DẠY
        col_phancong = ft.Column(spacing=0)
        if self.is_loading:
            for _ in range(3): col_phancong.controls.append(ft.Row([self.create_skeleton(width=40, height=40, border_radius=8), ft.Column([self.create_skeleton(width=150, height=16), self.create_skeleton(width=100, height=12)], spacing=8, expand=True), self.create_skeleton(width=20, height=20, is_circle=True)]))
        elif self.tkb_data:
            for index, row in enumerate(self.tkb_data):
                if index > 0: col_phancong.controls.append(ft.Divider(height=1, color=current_theme.divider_color))
                col_phancong.controls.append(
                    ft.Container(padding=ft.Padding(0, 10, 0, 10), ink=True, on_click=lambda e: self.app_page.run_task(self.handle_go_to_schedule), content=ft.Row([
                        ft.Container(width=40, height=40, border_radius=8, bgcolor=current_theme.surface_variant, content=ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=current_theme.accent, size=20), alignment=ft.Alignment(0,0)),
                        ft.Column([ft.Text(row.get("hocphan", {}).get("tenhocphan", "N/A"), weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(f"Lớp: {row.get('lop', {}).get('tenlop', 'N/A')}  •  Số buổi: {row.get('hocphan', {}).get('sobuoi', 0)}", size=12, color=current_theme.text_muted)], spacing=2, expand=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=current_theme.text_muted)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                )
        else: col_phancong.controls.append(ft.Container(content=ft.Text("Kỳ này giảng viên không có lịch dạy.", italic=True, size=12, color=current_theme.text_muted), padding=15, alignment=ft.Alignment(0,0)))

        schedule_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, color=current_theme.secondary, size=20), ft.Column([ft.Text("PHÂN CÔNG CÁC LỚP", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13), ft.Text("Học kỳ hiện tại", size=11, color=current_theme.text_muted)], spacing=0)]),
            ft.Divider(color=current_theme.divider_color, height=1), col_phancong 
        ], spacing=10)

        # 4. THÔNG BÁO MỚI
        col_thongbao = ft.Column(spacing=0)
        if self.is_loading:
            for _ in range(3): col_thongbao.controls.append(ft.Column([ft.Row([self.create_skeleton(width=20, height=20, is_circle=True), self.create_skeleton(width=200, height=16, expand=True)]), ft.Row([self.create_skeleton(width=80, height=12), self.create_skeleton(width=80, height=12)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)], spacing=10))
        elif self.thongbao_data:
            for index, item in enumerate(self.thongbao_data):
                if index > 0: col_thongbao.controls.append(ft.Divider(height=1, color=current_theme.divider_color))
                col_thongbao.controls.append(
                    ft.Container(padding=ft.Padding(0, 12, 0, 12), content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.FIBER_NEW_ROUNDED, color=ft.Colors.RED_400, size=22), ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.BOLD, size=14, color=current_theme.text_main, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)], alignment=ft.MainAxisAlignment.START, cross_alignment=ft.CrossAxisAlignment.START),
                        ft.Container(height=2),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=13, color=current_theme.text_muted), ft.Text(item.get("created_at", "N/A")[:10], size=11, color=current_theme.text_muted)], spacing=3), ft.Text("Đọc tiếp >", color=current_theme.accent, size=12, weight=ft.FontWeight.BOLD)])
                    ], spacing=5))
                )
        else: col_thongbao.controls.append(ft.Container(content=ft.Text("Chưa có thông báo nào.", italic=True, size=12, color=current_theme.text_muted), padding=15, alignment=ft.Alignment(0,0)))

        news_content = ft.Column([
            ft.Row([ft.Icon(ft.Icons.CAMPAIGN, color=current_theme.secondary, size=22), ft.Column([ft.Text("THÔNG BÁO MỚI", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13), ft.Text("Cập nhật học vụ quan trọng", size=11, color=current_theme.text_muted)], spacing=0)]),
            ft.Divider(color=current_theme.divider_color, height=1), col_thongbao 
        ], spacing=10)

        # RÁP GIAO DIỆN CHÍNH
        def make_card(content, use_variant=False):
            return ft.Container(content=content, padding=20, bgcolor=current_theme.surface_variant if use_variant else current_theme.surface_color, border_radius=16, border=ft.Border.all(1, current_theme.divider_color))

        left_column = ft.Column([make_card(info_content), make_card(today_content, use_variant=True), make_card(schedule_content)], spacing=15)
        right_column = ft.Column([make_card(news_content)], spacing=15)

        dashboard_layout = ft.ResponsiveRow([
            ft.Column([left_column], col={"xs": 12, "md": 12, "lg": 6, "xl": 7}),
            ft.Column([right_column], col={"xs": 12, "md": 12, "lg": 6, "xl": 5}),
        ], spacing=15, run_spacing=15)

        self.content = ft.Column([ft.Container(height=5), dashboard_layout, ft.Container(height=30)], scroll=ft.ScrollMode.AUTO, expand=True)

    async def handle_go_to_schedule(self):
        await self.app_page.push_route("/user/schedule")

    def render_data_to_ui(self, thongbao, tkb, today):
        self.thongbao_data = thongbao
        self.tkb_data = tkb
        self.today_data = today
        self.is_loading = False
        self.apply_theme() # Dùng chung hàm vẽ UI cho gọn

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

        if current_time - last_sync < 300: return

        try:
            async with await get_supabase_client() as client:
                res_tb = await client.get("/thongbao", params={"select": "*", "order": "created_at.desc", "limit": "5"})
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
                                if tkb_info: fresh_today["classes"].append({"id": t["id"], "ten_hp": tkb_info.get("hocphan", {}).get("tenhocphan", "N/A"), "ten_lop": tkb_info.get("lop", {}).get("tenlop", "N/A"), "phong_hoc": t.get("phong_hoc", "N/A"), "thoigianbd": t.get("tiet", {}).get("thoigianbd"), "thoigiankt": t.get("tiet", {}).get("thoigiankt"), "da_diem_danh": str(t["id"]) in dd_map})

            await prefs.set("cached_news", json.dumps(fresh_news))
            await prefs.set(f"cached_home_schedule_{self.gv_id}", json.dumps(fresh_schedule))
            await prefs.set(f"cached_today_{self.gv_id}", json.dumps(fresh_today))
            await prefs.set(f"last_sync_home_{self.gv_id}", str(current_time))

            self.render_data_to_ui(fresh_news, fresh_schedule, fresh_today)
        except Exception as e: 
            show_top_notification(self.app_page, "HONE [Mất kết nối]", "Không có kết nối mạng, vui lòng thử lại", color=ft.Colors.ORANGE)
            print("HOME ERROR:", e)