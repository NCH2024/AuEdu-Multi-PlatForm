import flet as ft
import json
import asyncio
import time
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification
from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from core.config import get_supabase_client


class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        self.gv_name = ""
        self.gv_id = "N/A"

        # Các container tĩnh để "tráo đổi" giữa Skeleton và Dữ liệu thật
        self.info_container = ft.Container()
        self.schedule_container = ft.Container()
        self.news_container = ft.Container()

        self.content = self.build_ui()
        
        self.app_page.run_task(self.load_data)

    def create_skeleton(self, width=None, height=20, expand=False):
        """Hàm tạo dải màu xám giả lập dữ liệu đang tải"""
        return ft.Container(
            width=width,
            height=height,
            expand=expand,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
            border_radius=6
        )

    def build_ui(self):
        # ==========================================
        # 1. KHUNG XƯƠNG (SKELETON)
        # ==========================================
        self.info_container.content = ft.Column([
            ft.Text("THÔNG TIN GIẢNG VIÊN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Divider(color=ft.Colors.BLACK_12),
            self.create_skeleton(width=200, height=22),
            self.create_skeleton(width=150, height=20),
            self.create_skeleton(width=180, height=20),
            self.create_skeleton(width=250, height=15),
        ])
        info_card = get_glass_container(content=self.info_container)

        self.schedule_container.content = ft.Column([
            ft.Text("PHÂN CÔNG ĐIỂM DANH CÁC LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Text("Xem nhanh lịch mà bạn được phân công:", size=13, color=ft.Colors.GREY_700),
            ft.Divider(color=ft.Colors.BLACK_12),
            self.create_skeleton(height=35),
            self.create_skeleton(height=45),
            self.create_skeleton(height=45),
            self.create_skeleton(height=45),
        ])
        schedule_card = get_glass_container(content=self.schedule_container)

        skeleton_news = ft.Column(spacing=10)
        for _ in range(4):
            skeleton_news.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.WHITE), padding=15, border_radius=8,
                    content=ft.Column([
                        self.create_skeleton(width=250, height=18),
                        self.create_skeleton(width=120, height=14),
                        self.create_skeleton(width=90, height=30),
                    ], spacing=8)
                )
            )

        self.news_container.content = ft.Column([
            ft.Text("THÔNG BÁO", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Text("Cán bộ giảng viên hãy lưu ý thông báo mới nhất!", size=13, color=ft.Colors.GREY_700),
            ft.Divider(color=ft.Colors.BLACK_12),
            skeleton_news
        ])
        news_card = get_glass_container(content=self.news_container)

        # LẮP RÁP
        left_column = ft.Column([info_card, schedule_card], spacing=20)
        dashboard_content = ft.ResponsiveRow([
            ft.Column([left_column], col={"sm": 12, "md": 6}),
            ft.Column([news_card], col={"sm": 12, "md": 6}),
        ], expand=True)

        
        return dashboard_content

    def render_data_to_ui(self, thongbao_data, tkb_data):
        """Hàm gán dữ liệu thật vào giao diện"""
        # Build Thông báo
        col_thongbao = ft.Column(scroll=ft.ScrollMode.AUTO, height=450, spacing=10)
        if thongbao_data:
            for item in thongbao_data:
                raw_date = item.get("created_at", "N/A")[:10] 
                title = item.get("tieu_de", "Không có tiêu đề")
                
                news_item = ft.Container(
                    bgcolor=ft.Colors.WHITE_70, padding=ft.Padding(15, 15, 15, 15), border_radius=8,
                    content=ft.Column([
                        ft.Text(title, weight=ft.FontWeight.BOLD, size=14, color=SECONDARY_COLOR),
                        ft.Text(f"Ngày đăng: {raw_date}", size=12, color=ft.Colors.GREY_600),
                        ft.Button(content=ft.Text("Xem chi tiết", color=ft.Colors.WHITE, size=12), bgcolor=ACCENT_COLOR, height=30)
                    ], spacing=5)
                )
                col_thongbao.controls.append(news_item)
        else:
            col_thongbao.controls.append(ft.Text("Chưa có thông báo nào.", italic=True, color=ft.Colors.GREY_500))

        # Build Bảng Lịch phân công
        dt_phancong = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
                ft.DataColumn(ft.Text("HỌC PHẦN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
                ft.DataColumn(ft.Text("SỐ BUỔI", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
            ],
            rows=[], heading_row_color=ft.Colors.with_opacity(0.1, SECONDARY_COLOR), border_radius=8
        )

        if tkb_data:
            for row in tkb_data:
                ten_lop = row.get("lop", {}).get("tenlop", "N/A") if row.get("lop") else "N/A"
                ten_hp = row.get("hocphan", {}).get("tenhocphan", "N/A") if row.get("hocphan") else "N/A"
                so_buoi = str(row.get("hocphan", {}).get("sobuoi", 0)) if row.get("hocphan") else "0"
                
                dt_phancong.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(ten_lop, color=SECONDARY_COLOR)),
                        ft.DataCell(ft.Text(ten_hp, color=SECONDARY_COLOR)),
                        ft.DataCell(ft.Text(so_buoi, color=SECONDARY_COLOR)),
                    ])
                )
        else:
            dt_phancong.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Chưa có lịch")), ft.DataCell(ft.Text("-")), ft.DataCell(ft.Text("-"))]))

        # Đánh tráo các UI
        self.info_container.content = ft.Column([
            ft.Text("THÔNG TIN GIẢNG VIÊN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Divider(color=ft.Colors.BLACK_12),
            ft.Text(f"Giảng Viên: {self.gv_name}", size=16, weight=ft.FontWeight.W_500, color=SECONDARY_COLOR),
            ft.Text(f"Mã cán bộ: {self.gv_id}", size=16, color=SECONDARY_COLOR),
            ft.Text("Khoa: Công nghệ thông tin", size=16, color=SECONDARY_COLOR),
            ft.Text("Thông tin khác: Giảng viên được thiết lập mẫu trong quá trình xây dựng phần mềm.", size=14, italic=True, color=ft.Colors.GREY_700),
        ])
        
        self.schedule_container.content = ft.Column([
            ft.Text("PHÂN CÔNG ĐIỂM DANH CÁC LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Text("Xem nhanh lịch mà bạn được phân công:", size=13, color=ft.Colors.GREY_700),
            ft.Divider(color=ft.Colors.BLACK_12),
            dt_phancong
        ])

        self.news_container.content = ft.Column([
            ft.Text("THÔNG BÁO", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
            ft.Text("Cán bộ giảng viên hãy lưu ý thông báo mới nhất!", size=13, color=ft.Colors.GREY_700),
            ft.Divider(color=ft.Colors.BLACK_12),
            col_thongbao 
        ])

        self.update()

    async def load_data(self):
        prefs = ft.SharedPreferences()

        # ==============================
        # USER SESSION
        # ==============================
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_name = session_data.get("name", "Giảng viên")
            self.gv_id = session_data.get("id", "N/A")

        # ==============================
        # LOAD CACHE
        # ==============================
        cached_news = safe_json_load(await prefs.get("cached_news"))
        
        # ĐÃ ĐỔI TÊN KEY ĐỂ KHÔNG BỊ TRANG LỊCH GHI ĐÈ: cached_home_schedule
        cached_schedule = safe_json_load(await prefs.get(f"cached_home_schedule_{self.gv_id}"))

        last_sync = float(await prefs.get(f"last_sync_home_{self.gv_id}") or 0)

        cached_news_hash = await prefs.get("news_hash")
        # ĐÃ ĐỔI TÊN KEY: home_schedule_hash
        cached_schedule_hash = await prefs.get(f"home_schedule_hash_{self.gv_id}")

        current_time = time.time()
        TTL = 300  # 5 phút

        # ==============================
        # STEP 1: HIỂN THỊ CACHE NGAY
        # ==============================
        if cached_news is not None and cached_schedule is not None:
            self.render_data_to_ui(cached_news, cached_schedule)

        # ==============================
        # STEP 2: CHECK TTL
        # ==============================
        if current_time - last_sync < TTL:
            # Cache còn hạn -> không gọi API
            return

        # ==============================
        # STEP 3: CALL API (BACKGROUND)
        # ==============================
        try:
            async with await get_supabase_client() as client:

                # ---- NEWS ----
                res_tb = await client.get(
                    "/thongbao",
                    params={"select": "*", "order": "created_at.desc", "limit": "5"},
                )
                res_tb.raise_for_status()
                fresh_news = res_tb.json()

                # ---- SCHEDULE ----
                fresh_schedule = []
                if self.gv_id != "N/A":
                    res_tkb = await client.get(
                        "/thoikhoabieu",
                        params={
                            "select": "lop(tenlop),hocphan(tenhocphan,sobuoi)",
                            "giangvien_id": f"eq.{self.gv_id}",
                        },
                    )
                    res_tkb.raise_for_status()
                    fresh_schedule = res_tkb.json()

            # ==============================
            # STEP 4: HASH COMPARE
            # ==============================
            new_news_hash = hash_data(fresh_news)
            new_schedule_hash = hash_data(fresh_schedule)

            is_changed = (
                new_news_hash != cached_news_hash or
                new_schedule_hash != cached_schedule_hash
            )

            # ==============================
            # STEP 5: UPDATE CACHE
            # ==============================
            await prefs.set("cached_news", json.dumps(fresh_news))
            
            # CẬP NHẬT TÊN KEY LƯU MỚI TẠI ĐÂY
            await prefs.set(f"cached_home_schedule_{self.gv_id}", json.dumps(fresh_schedule))

            await prefs.set("news_hash", new_news_hash)
            
            # CẬP NHẬT TÊN KEY LƯU MỚI TẠI ĐÂY
            await prefs.set(f"home_schedule_hash_{self.gv_id}", new_schedule_hash)

            await prefs.set(f"last_sync_home_{self.gv_id}", str(current_time))

            # ==============================
            # STEP 6: UPDATE UI IF CHANGED
            # ==============================
            if is_changed or cached_news is None:
                print("HOME [SYNC] ... đang đồng bộ dữ liệu mới cho trang chủ ...")
                self.render_data_to_ui(fresh_news, fresh_schedule)
            else:
                print("HOME [SYNC] Dữ liệu chuẩn xác")

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