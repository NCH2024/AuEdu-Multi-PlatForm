import flet as ft
import json
import asyncio
import time
import datetime
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from core.config import get_supabase_client


class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        self.gv_name = ""
        self.gv_id = "N/A"

        # TỐI ƯU HIỆU NĂNG: Khai báo Container với nền trắng/màu trơn ngay từ đầu.
        # Không cần các wrapper lồng nhau nữa.
        self.info_container = ft.Container(padding=20, bgcolor=ft.Colors.WHITE, border_radius=16)
        self.today_container = ft.Container(padding=20, bgcolor=ft.Colors.BLUE_50, border_radius=16) 
        self.schedule_container = ft.Container(padding=20, bgcolor=ft.Colors.WHITE, border_radius=16)
        self.news_container = ft.Container(padding=20, bgcolor=ft.Colors.WHITE, border_radius=16)

        self.content = self.build_ui()
        
        self.app_page.run_task(self.load_data)

    def create_skeleton(self, width=None, height=20, expand=False, is_circle=False, border_radius=4):
        # Dùng màu xám trơn thay vì tính toán opacity liên tục
        return ft.Container(
            width=width,
            height=height,
            expand=expand,
            bgcolor=ft.Colors.GREY_200,
            border_radius=height/2 if is_circle else border_radius
        )

    def build_ui(self):
        # 1. LỜI CHÀO & THÔNG TIN GIẢNG VIÊN (SKELETON)
        self.info_container.content = ft.Column(
            spacing=15, 
            controls=[
                ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=SECONDARY_COLOR, size=20), ft.Text("HỒ SƠ CỦA TÔI", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13)]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1), 
                ft.Row([
                    self.create_skeleton(width=50, height=50, is_circle=True),
                    ft.Column([
                        self.create_skeleton(width=150, height=18),
                        self.create_skeleton(width=100, height=14),
                    ], spacing=5)
                ])
            ]
        )

        # 2. HÔM NAY CỦA BẠN (SKELETON)
        self.today_container.content = ft.Column(
            spacing=15,
            controls=[
                ft.Row([ft.Icon(ft.Icons.WB_SUNNY_ROUNDED, color=ACCENT_COLOR, size=22), ft.Text("HÔM NAY CỦA BẠN", weight=ft.FontWeight.BOLD, color=ACCENT_COLOR, size=13)]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                self.create_skeleton(width=200, height=16),
                self.create_skeleton(height=60, border_radius=8),
            ]
        )

        # 3. XƯƠNG CHỜ CHO LỊCH DẠY
        skeleton_schedule_col = ft.Column(spacing=15)
        for _ in range(3):
            skeleton_schedule_col.controls.append(
                ft.Row([
                    self.create_skeleton(width=40, height=40, border_radius=8),
                    ft.Column([
                        self.create_skeleton(width=150, height=16),
                        self.create_skeleton(width=100, height=12)
                    ], spacing=8, expand=True),
                    self.create_skeleton(width=20, height=20, is_circle=True)
                ])
            )

        self.schedule_container.content = ft.Column(
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH, color=SECONDARY_COLOR, size=20), 
                    ft.Column([
                        ft.Text("PHÂN CÔNG CÁC LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                        ft.Text("Học kỳ hiện tại", size=11, color=ft.Colors.GREY_600)
                    ], spacing=0)
                ]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                skeleton_schedule_col
            ]
        )

        # 4. XƯƠNG CHỜ CHO THÔNG BÁO
        skeleton_news = ft.Column(spacing=15) 
        for _ in range(3): 
            skeleton_news.controls.append(
                ft.Column([
                    ft.Row([self.create_skeleton(width=20, height=20, is_circle=True), self.create_skeleton(width=200, height=16, expand=True)]),
                    ft.Row([self.create_skeleton(width=80, height=12), self.create_skeleton(width=80, height=12)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=10)
            )

        self.news_container.content = ft.Column(
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.CAMPAIGN, color=SECONDARY_COLOR, size=22), 
                    ft.Column([
                        ft.Text("THÔNG BÁO MỚI", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                        ft.Text("Cập nhật học vụ quan trọng", size=11, color=ft.Colors.GREY_600)
                    ], spacing=0)
                ]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                skeleton_news
            ]
        )

        # BỐ CỤC CHÍNH (Đưa thẳng các Container đã thiết lập vào bố cục, bỏ qua bước tạo Card trung gian)
        left_column = ft.Column([self.info_container, self.today_container, self.schedule_container], spacing=15)
        dashboard_content = ft.ResponsiveRow([
            ft.Column([left_column], col={"xs": 12, "md": 12, "lg": 6, "xl": 7}),
            ft.Column([self.news_container], col={"xs": 12, "md": 12, "lg": 6, "xl": 5}),
        ], spacing=15, run_spacing=15) 

        return ft.Container(
            content=ft.Column([dashboard_content], scroll=ft.ScrollMode.AUTO), 
            padding=ft.Padding(0, 10, 0, 0) if hasattr(ft, 'Padding') else 10,
            expand=True
        )

    async def handle_go_to_schedule(self, e):
        await self.app_page.push_route("/user/schedule")

    def render_data_to_ui(self, thongbao_data, tkb_data, today_data):
        
        # 1. BUILD DANH SÁCH THÔNG BÁO (Thiết kế phẳng, dùng Divider)
        col_thongbao = ft.Column(spacing=0)
        if thongbao_data:
            for index, item in enumerate(thongbao_data):
                raw_date = item.get("created_at", "N/A")[:10] 
                title = item.get("tieu_de", "Không có tiêu đề")
                
                # Chèn đường kẻ ngang giữa các dòng (trừ dòng đầu tiên)
                if index > 0:
                    col_thongbao.controls.append(ft.Divider(height=1, color=ft.Colors.BLACK_12))
                
                news_item = ft.Container(
                    padding=ft.Padding(0, 12, 0, 12),
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.FIBER_NEW_ROUNDED, color=ft.Colors.RED_400, size=22),
                            ft.Text(title, weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ], alignment=ft.MainAxisAlignment.START, cross_alignment=ft.CrossAxisAlignment.START),
                        ft.Container(height=2),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row([ft.Icon(ft.Icons.ACCESS_TIME, size=13, color=ft.Colors.GREY_500), ft.Text(raw_date, size=11, color=ft.Colors.GREY_500)], spacing=3),
                                ft.Text("Đọc tiếp >", color=ACCENT_COLOR, size=12, weight=ft.FontWeight.BOLD)
                            ]
                        )
                    ], spacing=5) 
                )
                col_thongbao.controls.append(news_item)
        else:
            col_thongbao.controls.append(ft.Container(content=ft.Text("Chưa có thông báo nào.", italic=True, size=12, color=ft.Colors.GREY_500), padding=15, alignment=ft.Alignment(0,0)))

        # 2. BUILD THẺ HÔM NAY CỦA BẠN (TODAY CARD - Lược bớt viền dư thừa)
        today_content_col = ft.Column(spacing=8)
        now_time = datetime.datetime.now().time()
        
        if not today_data or not today_data.get("classes"):
            today_content_col.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.NIGHTLIGHT_ROUND, color=ft.Colors.GREY_600, size=18),
                    ft.Text("Hôm nay bạn không có lịch lên lớp. Hãy nghỉ ngơi nhé!", size=13, color=ft.Colors.GREY_700, italic=True, expand=True)
                ])
            )
        else:
            classes = today_data["classes"]
            today_content_col.controls.append(ft.Text(f"Bạn có {len(classes)} ca dạy trong ngày hôm nay.", weight=ft.FontWeight.W_500, size=13, color=SECONDARY_COLOR))
            
            current_class = None
            reminders = []
            
            for c in classes:
                start_str = c.get("thoigianbd")
                end_str = c.get("thoigiankt")
                if start_str and end_str:
                    try:
                        start_t = datetime.datetime.strptime(start_str, "%H:%M:%S").time()
                        end_t = datetime.datetime.strptime(end_str, "%H:%M:%S").time()
                        
                        if start_t <= now_time <= end_t:
                            current_class = c
                        elif now_time > end_t and not c["da_diem_danh"]:
                            reminders.append(f"⚠️ Quên điểm danh: Lớp {c['ten_lop']} ({c['ten_hp']})")
                        elif start_t > now_time:
                            td_now = datetime.datetime.combine(datetime.date.today(), now_time)
                            td_start = datetime.datetime.combine(datetime.date.today(), start_t)
                            if (td_start - td_now).total_seconds() < 1800 and not c["da_diem_danh"]:
                                reminders.append(f"⏳ Sắp diễn ra: Lớp {c['ten_lop']} - Nhớ điểm danh nhé!")
                    except Exception:
                        pass
                        
            if current_class:
                today_content_col.controls.append(
                    ft.Container(
                        bgcolor=ft.Colors.WHITE, padding=12, border_radius=8, 
                        # Viền cực mờ, sang trọng hơn
                        border=ft.Border.all(1, ft.Colors.BLACK_12),
                        content=ft.Column([
                            ft.Row([ft.Icon(ft.Icons.PLAY_CIRCLE_FILL, color=ACCENT_COLOR, size=16), ft.Text("ĐANG DIỄN RA", color=ACCENT_COLOR, weight=ft.FontWeight.BOLD, size=11)]),
                            ft.Text(f"{current_class['ten_hp']} - Lớp {current_class['ten_lop']}", weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                            ft.Row([ft.Icon(ft.Icons.ROOM, size=12, color=ft.Colors.GREY_600), ft.Text(f"Phòng: {current_class['phong_hoc']}", size=12, color=ft.Colors.GREY_700)], spacing=4)
                        ], spacing=3)
                    )
                )
            
            if reminders:
                reminder_col = ft.Column(spacing=4)
                for r in reminders:
                    reminder_col.controls.append(ft.Text(r, size=12, color=ft.Colors.RED_700 if "Quên" in r else ft.Colors.ORANGE_800, weight=ft.FontWeight.W_500))
                today_content_col.controls.append(
                    ft.Container(
                        bgcolor=ft.Colors.RED_50, padding=10, border_radius=8,
                        content=reminder_col
                    )
                )
            elif not current_class:
                today_content_col.controls.append(ft.Text("Mọi việc hôm nay đang ổn thỏa, không có nhắc nhở nào!", size=12, color=ft.Colors.GREEN_700, italic=True))


        # 3. BUILD DANH SÁCH LỊCH PHÂN CÔNG (Danh sách phẳng)
        col_phancong = ft.Column(spacing=0) 
        if tkb_data:
            for index, row in enumerate(tkb_data):
                if index > 0:
                    col_phancong.controls.append(ft.Divider(height=1, color=ft.Colors.BLACK_12))
                
                ten_lop = row.get("lop", {}).get("tenlop", "N/A") if row.get("lop") else "N/A"
                ten_hp = row.get("hocphan", {}).get("tenhocphan", "N/A") if row.get("hocphan") else "N/A"
                so_buoi = str(row.get("hocphan", {}).get("sobuoi", 0)) if row.get("hocphan") else "0"
                
                schedule_card = ft.Container(
                    padding=ft.Padding(0, 10, 0, 10), ink=True, on_click=self.handle_go_to_schedule, 
                    content=ft.Row([
                        ft.Container(width=40, height=40, border_radius=8, bgcolor=ft.Colors.BLUE_50, content=ft.Icon(ft.Icons.MENU_BOOK_ROUNDED, color=ACCENT_COLOR, size=20), alignment=ft.Alignment(0,0)),
                        ft.Column([
                            ft.Text(ten_hp, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"Lớp: {ten_lop}  •  Số buổi: {so_buoi}", size=12, color=ft.Colors.GREY_600)
                        ], spacing=2, expand=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=ft.Colors.GREY_400)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
                col_phancong.controls.append(schedule_card)
        else:
            col_phancong.controls.append(ft.Container(content=ft.Text("Kỳ này giảng viên không có lịch dạy.", italic=True, size=12, color=ft.Colors.GREY_500), padding=15, alignment=ft.Alignment(0,0)))

        # 4. ĐÁNH TRÁO CÁC UI LÊN GIAO DIỆN
        self.info_container.content = ft.Column(
            spacing=15,
            controls=[
                ft.Row([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, color=SECONDARY_COLOR, size=20), ft.Text("HỒ SƠ CỦA TÔI", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13)]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                ft.Row([
                    ft.Container(width=50, height=50, border_radius=25, bgcolor=PRIMARY_COLOR, content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE, size=25), alignment=ft.Alignment(0,0)),
                    ft.Column([
                        ft.Text(f"GV. {self.gv_name}", size=16, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                        ft.Text(f"Mã cán bộ: {self.gv_id}  •  Khoa: CNTT", size=12, color=ft.Colors.GREY_600),
                    ], spacing=2)
                ])
            ]
        )

        self.today_container.content = ft.Column(
            spacing=15,
            controls=[
                ft.Row([ft.Icon(ft.Icons.WB_SUNNY_ROUNDED, color=ACCENT_COLOR, size=22), ft.Text("HÔM NAY CỦA BẠN", weight=ft.FontWeight.BOLD, color=ACCENT_COLOR, size=13)]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                today_content_col
            ]
        )
        
        self.schedule_container.content = ft.Column(
            spacing=10,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH, color=SECONDARY_COLOR, size=20), 
                    ft.Column([ft.Text("PHÂN CÔNG CÁC LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13), ft.Text("Học kỳ hiện tại", size=11, color=ft.Colors.GREY_600)], spacing=0)
                ]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                col_phancong 
            ]
        )

        self.news_container.content = ft.Column(
            spacing=10,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.CAMPAIGN, color=SECONDARY_COLOR, size=22), 
                    ft.Column([ft.Text("THÔNG BÁO MỚI", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13), ft.Text("Cập nhật học vụ quan trọng", size=11, color=ft.Colors.GREY_600)], spacing=0)
                ]),
                ft.Divider(color=ft.Colors.BLACK_12, height=1),
                col_thongbao 
            ]
        )

        self.update()

    async def load_data(self):
        prefs = ft.SharedPreferences()

        # LẤY SESSION
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_name = session_data.get("name", "Giảng viên")
            self.gv_id = session_data.get("id", "N/A")

        # CACHE
        cached_news = safe_json_load(await prefs.get("cached_news"))
        cached_schedule = safe_json_load(await prefs.get(f"cached_home_schedule_{self.gv_id}"))
        cached_today = safe_json_load(await prefs.get(f"cached_today_{self.gv_id}"))

        last_sync = float(await prefs.get(f"last_sync_home_{self.gv_id}") or 0)

        cached_news_hash = await prefs.get("news_hash")
        cached_schedule_hash = await prefs.get(f"home_schedule_hash_{self.gv_id}")
        cached_today_hash = await prefs.get(f"today_hash_{self.gv_id}")

        current_time = time.time()
        TTL = 300  

        # LOAD CACHE NGAY
        if cached_news is not None and cached_schedule is not None and cached_today is not None:
            self.render_data_to_ui(cached_news, cached_schedule, cached_today)

        if current_time - last_sync < TTL:
            return

        try:
            async with await get_supabase_client() as client:

                # NEWS
                res_tb = await client.get(
                    "/thongbao",
                    params={"select": "*", "order": "created_at.desc", "limit": "5"},
                )
                res_tb.raise_for_status()
                fresh_news = res_tb.json()

                # SCHEDULE + TODAY
                fresh_schedule = []
                fresh_today = {"classes": []}

                if self.gv_id != "N/A":

                    # LẤY TOÀN BỘ TKB
                    res_tkb = await client.get(
                        "/thoikhoabieu",
                        params={
                            "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan,sobuoi),hocky(namhoc,tenhocky)",
                            "giangvien_id": f"eq.{self.gv_id}",
                        },
                    )
                    res_tkb.raise_for_status()
                    all_tkb = res_tkb.json()

                    if all_tkb:
                        valid_hks = [s["hocky"] for s in all_tkb if s.get("hocky")]
                        if valid_hks:
                            namhocs = sorted(list(set(hk["namhoc"] for hk in valid_hks)), reverse=True)
                            latest_namhoc = namhocs[0]

                            hks_in_year = [hk for hk in valid_hks if hk["namhoc"] == latest_namhoc]
                            latest_hk = hks_in_year[0]["tenhocky"]

                            fresh_schedule = [
                                s for s in all_tkb
                                if s.get("hocky")
                                and s["hocky"]["namhoc"] == latest_namhoc
                                and s["hocky"]["tenhocky"] == latest_hk
                            ]

                    # TODAY
                    today_date = datetime.datetime.now(datetime.timezone.utc).astimezone().date()
                    thu_now = today_date.weekday() + 2  

                    if all_tkb:
                        tkb_ids = [str(x["id"]) for x in all_tkb]

                        res_tiet = await client.get(
                            "/tkb_tiet",
                            params={
                                "select": "id,tkb_id,thu,phong_hoc,tiet(thoigianbd,thoigiankt)",
                                "tkb_id": f"in.({','.join(tkb_ids)})",
                                "thu": f"eq.{thu_now}",
                                "order": "tiet(thoigianbd).asc"
                            },
                        )
                        res_tiet.raise_for_status()
                        tiet_list = res_tiet.json()

                        if tiet_list:
                            tiet_ids = [str(t["id"]) for t in tiet_list]

                            res_dd = await client.get(
                                "/diemdanh",
                                params={
                                    "select": "tkb_tiet_id",
                                    "tkb_tiet_id": f"in.({','.join(tiet_ids)})",
                                    "ngay_diem_danh": f"eq.{today_date.isoformat()}",
                                },
                            )
                            res_dd.raise_for_status()
                            dd_data = res_dd.json()

                            dd_map = {str(d["tkb_tiet_id"]) for d in dd_data}

                            for t in tiet_list:
                                tkb_info = next((x for x in all_tkb if x["id"] == t["tkb_id"]), None)

                                if tkb_info:
                                    fresh_today["classes"].append({
                                        "id": t["id"],
                                        "ten_hp": tkb_info.get("hocphan", {}).get("tenhocphan", "N/A"),
                                        "ten_lop": tkb_info.get("lop", {}).get("tenlop", "N/A"),
                                        "phong_hoc": t.get("phong_hoc", "N/A"),
                                        "thoigianbd": t.get("tiet", {}).get("thoigianbd"),
                                        "thoigiankt": t.get("tiet", {}).get("thoigiankt"),
                                        "da_diem_danh": str(t["id"]) in dd_map
                                    })

            # HASH
            new_news_hash = hash_data(fresh_news)
            new_schedule_hash = hash_data(fresh_schedule)
            new_today_hash = hash_data(fresh_today)

            is_changed = (
                new_news_hash != cached_news_hash
                or new_schedule_hash != cached_schedule_hash
                or new_today_hash != cached_today_hash
            )

            # SAVE CACHE
            await prefs.set("cached_news", json.dumps(fresh_news))
            await prefs.set(f"cached_home_schedule_{self.gv_id}", json.dumps(fresh_schedule))
            await prefs.set(f"cached_today_{self.gv_id}", json.dumps(fresh_today))

            await prefs.set("news_hash", new_news_hash)
            await prefs.set(f"home_schedule_hash_{self.gv_id}", new_schedule_hash)
            await prefs.set(f"today_hash_{self.gv_id}", new_today_hash)

            await prefs.set(f"last_sync_home_{self.gv_id}", str(current_time))

            # RENDER
            if is_changed or cached_news is None:
                print("HOME [SYNC] cập nhật dữ liệu mới")
                self.render_data_to_ui(fresh_news, fresh_schedule, fresh_today)
            else:
                print("HOME [SYNC] dữ liệu không đổi")

        except Exception as e:
            if getattr(self, "page", None):
                show_top_notification(
                    self.app_page,
                    "HOME [Không thể kết nối]",
                    "Vui lòng kiểm tra mạng!",
                    4000,
                    color=ft.Colors.RED,
                )
            print("HOME ERROR:", e)