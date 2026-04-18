import flet as ft
import json
import time
import asyncio
import datetime
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification
from components.options.open_browser import open_browser
from components.options.news_image import build_news_image
from core.theme import current_theme
from core.config import get_supabase_client
from services.home_service import HomeService

class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        # Kiểm tra nền tảng để quyết định hiển thị Layout Desktop hay Mobile
        self.is_desktop = self.app_page.platform in [
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ]

        self.gv_name = "Giảng viên"
        self.gv_id = "N/A"
        self.thongbao_data = []
        self.tkb_data = []
        self.today_data = None
        self.is_loading = True

        self._name_text = None

        self.content = self.build_ui()
        self.app_page.run_task(self.load_data)

    def apply_theme(self):
        self.content = self.build_ui()
        if self.page:
            self.update()

    def create_skeleton(self, width=None, height=20, expand=False, is_circle=False, border_radius=4):
        return ft.Container(
            width=width, height=height, expand=expand,
            bgcolor=current_theme.divider_color,
            border_radius=height / 2 if is_circle else border_radius
        )

    def get_news_click_handler(self, item):
        async def on_click(e):
            try:
                link = item.get("link_web")
                has_link = bool(link and str(link).strip() not in ("", "None"))

                if has_link:
                    await open_browser(self.app_page, link, item.get("tieu_de", "Thông báo"))
                else:
                    def close_dlg(ev):
                        dlg.open = False
                        self.app_page.update()

                    img_widget = build_news_image(item.get("hinh_anh"), width=320, height=160, border_radius=10)

                    dlg = ft.AlertDialog(
                        title=ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.BOLD, size=16, color=current_theme.secondary),
                        scrollable=True,
                        content=ft.Container(
                            width=340,
                            content=ft.Column(
                                tight=True, 
                                spacing=10,
                                controls=[
                                    img_widget,
                                    ft.Text(item.get("noi_dung", "Nội dung chưa cập nhật"), size=13, color=current_theme.text_main)
                                ]
                            )
                        ),
                        actions=[ft.TextButton("Đóng lại", on_click=close_dlg)],
                        shape=ft.RoundedRectangleBorder(radius=12),
                        bgcolor=current_theme.surface_color,
                        content_padding=20
                    )
                    
                    if dlg not in self.app_page.overlay:
                        self.app_page.overlay.append(dlg)
                    dlg.open = True
                    self.app_page.update()
            except Exception as ex:
                print(f"[LỖI CRITICAL - HomePage] {ex}")
        return on_click

    def _build_timeline_controls(self):
        controls = []
        if self.is_loading:
            for _ in range(2):
                controls.append(ft.Container(
                    padding=10,
                    content=ft.Row([
                        self.create_skeleton(width=40, height=40, is_circle=True),
                        ft.Column([
                            self.create_skeleton(width=200, height=14),
                            self.create_skeleton(width=100, height=12)
                        ], spacing=5)
                    ])
                ))
            return controls

        if not self.today_data or not self.today_data.get("classes"):
            controls.append(ft.Container(
                padding=ft.Padding(0, 30, 0, 30), alignment=ft.Alignment(0, 0),
                content=ft.Column([
                    ft.Icon(ft.Icons.COFFEE_ROUNDED, color=current_theme.divider_color, size=50),
                    ft.Text("Trống lịch. Thời gian tuyệt vời để nạp lại năng lượng!", size=13, color=current_theme.text_muted, italic=True)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            ))
            return controls

        now_time = datetime.datetime.now().time()
        classes = self.today_data["classes"]
        for idx, c in enumerate(classes):
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
                        status_color = current_theme.accent
                        status_text = "Đang diễn ra"
                        badge_bg = ft.Colors.with_opacity(0.1, current_theme.accent)
                        badge_text_color = current_theme.accent
                    elif now_time > end_t:
                        status_color = ft.Colors.GREEN_600 if is_done else ft.Colors.RED_500
                        status_text = "Hoàn thành" if is_done else "Chưa điểm danh!"
                        badge_bg = ft.Colors.with_opacity(0.1, status_color)
                        badge_text_color = status_color
                except Exception:
                    pass

            is_last = (idx == len(classes) - 1)
            timeline_card_content = ft.Container(
                expand=True, padding=15, margin=ft.Margin(0, 0, 0, 15), border_radius=12,
                bgcolor=current_theme.surface_variant,
                border=ft.Border.all(1, current_theme.divider_color),
                ink=True,
                on_click=lambda e: self.app_page.run_task(self.app_page.push_route, "/user/attendance"),
                content=ft.Column([
                    ft.Row([
                        ft.Text(c["ten_hp"], weight=ft.FontWeight.BOLD, size=14, color=current_theme.text_main, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(padding=ft.Padding(8, 2, 8, 2), border_radius=10, bgcolor=badge_bg,
                                     content=ft.Text(status_text, size=10, weight=ft.FontWeight.BOLD, color=badge_text_color))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Icon(ft.Icons.CLASS_, size=14, color=current_theme.text_muted),
                        ft.Text(f"Lớp: {c['ten_lop']}", size=12, color=current_theme.text_muted),
                        ft.Container(width=10),
                        ft.Icon(ft.Icons.ROOM, size=14, color=current_theme.text_muted),
                        ft.Text(f"Phòng: P.{c['phong_hoc']}", size=12, color=current_theme.text_muted)
                    ], spacing=4)
                ], spacing=6)
            )
            timeline_item = ft.Row([
                ft.Column([
                    ft.Text(c.get("thoigianbd", "N/A")[:5], size=13, weight=ft.FontWeight.W_800, color=current_theme.text_main),
                    ft.Container(width=12, height=12, border_radius=6, border=ft.Border.all(3, status_color), bgcolor=current_theme.surface_color),
                    ft.Container(width=2, height=40, bgcolor=status_color if not is_last else ft.Colors.TRANSPARENT, margin=ft.Margin(0, -2, 0, -2))
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4, width=50),
                timeline_card_content
            ], vertical_alignment=ft.CrossAxisAlignment.START, spacing=10)
            controls.append(timeline_item)

        return controls

    def _build_news_controls(self):
        controls = []
        if self.is_loading:
            for _ in range(3):
                controls.append(ft.Container(
                    height=70, padding=10,
                    content=ft.Row([
                        self.create_skeleton(width=50, height=50, border_radius=8),
                        ft.Column([
                            self.create_skeleton(width=150, height=14),
                            self.create_skeleton(width=80, height=10)
                        ], spacing=5)
                    ])
                ))
            return controls

        if self.thongbao_data:
            for item in self.thongbao_data:
                img_widget = build_news_image(item.get("hinh_anh"), width=80, height=80, border_radius=8)
                has_link = bool(item.get("link_web") and str(item.get("link_web")).strip() not in ("", "None"))
                created_at = item.get("created_at", "")
                date_str = str(created_at)[:10] if created_at and len(str(created_at)) >= 10 else "N/A"
                controls.append(ft.Container(
                    padding=ft.Padding(0, 12, 0, 12),
                    border=ft.Border(bottom=ft.BorderSide(1, current_theme.divider_color)),
                    ink=True, on_click=self.get_news_click_handler(item),
                    content=ft.Row([
                        img_widget,
                        ft.Container(width=10),
                        ft.Column([
                            ft.Text(item.get("tieu_de", ""), weight=ft.FontWeight.W_600, size=13, color=current_theme.text_main, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([
                                ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=current_theme.text_muted),
                                ft.Text(date_str, size=11, color=current_theme.text_muted)
                            ], spacing=4)
                        ], spacing=4, expand=True),
                        ft.Icon(
                            ft.Icons.OPEN_IN_NEW_ROUNDED if has_link else ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                            size=16, color=current_theme.text_muted
                        )
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
                ))
        else:
            controls.append(ft.Container(
                padding=20, alignment=ft.Alignment(0, 0),
                content=ft.Text("Không có thông báo mới.", size=12, color=current_theme.text_muted, italic=True)
            ))

        return controls

    def _build_desktop_insights(self):
        """Khối dữ liệu phân tích chỉ hiển thị trên nền tảng Desktop"""
        
        # Đếm số lượng môn học độc lập đang dạy trong kỳ
        mon_hoc_set = set()
        lop_hoc_set = set()
        if self.tkb_data:
            for item in self.tkb_data:
                mon_hoc_set.add(item.get("hocphan", {}).get("tenhocphan", ""))
                lop_hoc_set.add(item.get("lop", {}).get("tenlop", ""))

        def mini_stat(icon, title, value, color):
            return ft.Container(
                expand=True, padding=15, border_radius=12,
                bgcolor=current_theme.surface_variant,
                content=ft.Row([
                    ft.Icon(icon, color=color, size=24),
                    ft.Column([
                        ft.Text(title, size=11, color=current_theme.text_muted, weight=ft.FontWeight.BOLD),
                        ft.Text(str(value), size=18, color=current_theme.text_main, weight=ft.FontWeight.W_800)
                    ], spacing=2)
                ], alignment=ft.MainAxisAlignment.START, spacing=15)
            )

        return self.make_pro_card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.PIE_CHART_ROUNDED, color=current_theme.primary, size=20),
                ft.Text("TỔNG QUAN HỌC KỲ (DESKTOP INSIGHTS)", weight=ft.FontWeight.BOLD, color=current_theme.primary, size=14)
            ]),
            ft.Divider(color=current_theme.divider_color, height=20),
            ft.Row([
                mini_stat(ft.Icons.LIBRARY_BOOKS_ROUNDED, "Học phần phụ trách", len(mon_hoc_set) if not self.is_loading else "-", current_theme.primary),
                mini_stat(ft.Icons.SUPERVISOR_ACCOUNT_ROUNDED, "Lớp học phụ trách", len(lop_hoc_set) if not self.is_loading else "-", ft.Colors.ORANGE_500),
                mini_stat(ft.Icons.FACT_CHECK_ROUNDED, "Tuân thủ điểm danh", "100%", ft.Colors.GREEN_500), # Mock data cho trực quan
            ], spacing=15)
        ], spacing=0))

    # Đã gỡ bỏ shadow để giữ đúng nguyên tắc thiết kế phẳng (Flat Design)
    def make_pro_card(self, content, padding=20, ink=False, on_click=None):
        return ft.Container(
            content=content, padding=padding, border_radius=12,
            bgcolor=current_theme.surface_color,
            border=ft.Border.all(1, current_theme.divider_color),
            ink=ink, on_click=on_click
        )
        
    def _build_desktop_class_table(self):
        """Bảng danh sách lớp học phụ trách - Chỉ hiển thị trên Desktop"""
        
        # Nếu đang tải hoặc không có dữ liệu thì ẩn khối này đi cho gọn
        if self.is_loading or not self.tkb_data:
            return ft.Container()

        # Tạo các hàng (Rows) cho bảng từ dữ liệu TKB đã fetch
        rows = []
        for item in self.tkb_data:
            ten_hp = item.get("hocphan", {}).get("tenhocphan", "N/A")
            so_buoi = item.get("hocphan", {}).get("sobuoi", "N/A")
            ten_lop = item.get("lop", {}).get("tenlop", "N/A")

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(ten_hp, weight=ft.FontWeight.W_600, color=current_theme.text_main)),
                        ft.DataCell(ft.Text(ten_lop, color=current_theme.text_muted)),
                        ft.DataCell(ft.Text(f"{so_buoi} buổi", color=current_theme.text_muted)),
                    ]
                )
            )

        # Khởi tạo DataTable
        class_table = ft.DataTable(
            expand=True,
            columns=[
                ft.DataColumn(ft.Text("HỌC PHẦN", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("LỚP HỌC", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("THỜI LƯỢNG", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
            ],
            rows=rows,
            heading_row_height=40,
            data_row_max_height=50,
            column_spacing=40,
            horizontal_margin=20,
            divider_thickness=1,
            # Bỏ bóng và dùng màu nền phẳng
            heading_row_color=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=8,
        )

        return self.make_pro_card(
            padding=0, # Set padding 0 để bảng tràn đẹp ra sát viền card
            content=ft.Column([
                ft.Container(
                    padding=ft.Padding(20, 20, 20, 5),
                    content=ft.Row([
                        ft.Icon(ft.Icons.TABLE_CHART_ROUNDED, color=current_theme.primary, size=20),
                        ft.Text("DANH SÁCH HỌC PHẦN GIẢNG DẠY KỲ NÀY", weight=ft.FontWeight.BOLD, color=current_theme.primary, size=14)
                    ])
                ),
                ft.Container(
                    padding=ft.Padding(20, 10, 20, 20),
                    content=ft.Row([class_table], scroll=ft.ScrollMode.AUTO) # Bọc trong Row scroll để an toàn nếu màn hình nhỏ lại
                )
            ], spacing=0)
        )

    def build_ui(self):
        now = datetime.datetime.now()
        greeting = "Chào buổi sáng" if now.hour < 12 else "Chào buổi chiều" if now.hour < 18 else "Chào buổi tối"

        total_classes = len(self.tkb_data) if self.tkb_data else 0
        today_total = len(self.today_data["classes"]) if self.today_data and "classes" in self.today_data else 0
        today_done = sum(1 for c in self.today_data["classes"] if c.get("da_diem_danh")) if today_total > 0 else 0
        news_count = len(self.thongbao_data) if self.thongbao_data else 0
        progress_val = (today_done / today_total) if today_total > 0 else 1.0
        progress_text = f"Hoàn thành {today_done}/{today_total} ca dạy" if today_total > 0 else "Hôm nay bạn được nghỉ ngơi!"

        # ── Header ──
        self._name_text = ft.Text(f"GV. {self.gv_name}", size=24, weight=ft.FontWeight.W_800, color=current_theme.text_main)
        greeting_text = ft.Text(f"{greeting},", size=14, color=current_theme.text_muted, weight=ft.FontWeight.W_500)
        date_text = ft.Text(f"Hôm nay là {now.strftime('%d/%m/%Y')} • Chúc bạn ngày mới hiệu quả!", size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500)
        calendar_icon = ft.Container(padding=10, border_radius=12, bgcolor=current_theme.surface_variant, content=ft.Icon(ft.Icons.CALENDAR_TODAY_ROUNDED, color=current_theme.secondary, size=24))
        header_section = ft.Row([
            ft.Column([greeting_text, self._name_text, date_text], spacing=0, expand=True),
            calendar_icon
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # ── Stats cards ──
        def create_stat_card(icon, title, value, color_theme, route):
            return ft.Container(
                col={"xs": 6, "sm": 6, "md": 3, "lg": 3},
                content=self.make_pro_card(
                    padding=15, ink=True,
                    on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                width=36, height=36, border_radius=10,
                                bgcolor=ft.Colors.with_opacity(0.1, color_theme),
                                content=ft.Icon(icon, color=color_theme, size=18),
                                alignment=ft.Alignment(0, 0)
                            ),
                            ft.Text(
                                str(value) if not self.is_loading else "...",
                                size=22, weight=ft.FontWeight.BOLD, color=current_theme.text_main,
                                expand=True, text_align=ft.TextAlign.RIGHT
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=5),
                        ft.Text(title, size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_600)
                    ], spacing=0)
                )
            )

        stats_row = ft.ResponsiveRow([
            create_stat_card(ft.Icons.CLASS_OUTLINED, "Tổng lớp học kỳ", total_classes, current_theme.primary, "/user/schedule"),
            create_stat_card(ft.Icons.EVENT_NOTE_ROUNDED, "Ca dạy hôm nay", today_total, ft.Colors.ORANGE_500, "/user/attendance"),
            create_stat_card(ft.Icons.CHECK_CIRCLE_OUTLINE, "Đã điểm danh", today_done, ft.Colors.GREEN_500, "/user/stats"),
            create_stat_card(ft.Icons.CAMPAIGN_OUTLINED, "Thông báo mới", news_count, ft.Colors.RED_400, "/user/news"),
        ], run_spacing=5, spacing=5)

        # ── Progress ──
        progress_label = ft.Text(f"{int(progress_val * 100)}%", size=13, weight=ft.FontWeight.BOLD, color=current_theme.secondary)
        progress_bar = ft.ProgressBar(value=progress_val, color=current_theme.secondary, bgcolor=current_theme.surface_variant, height=8, border_radius=4)
        progress_text_ctrl = ft.Text(progress_text, size=11, color=current_theme.text_muted, italic=True)

        progress_section = ft.Column([
            ft.Row([
                ft.Text("Tiến độ hôm nay", size=13, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
                progress_label
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            progress_bar,
            progress_text_ctrl
        ], spacing=5)

        # ── Timeline ──
        today_timeline = ft.Column(controls=self._build_timeline_controls(), spacing=0)

        timeline_section = self.make_pro_card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.MAP_ROUNDED, color=current_theme.secondary, size=20),
                ft.Text("LỊCH TRÌNH TRONG NGÀY", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14)
            ]),
            ft.Divider(color=current_theme.divider_color, height=20),
            progress_section,
            ft.Container(height=10),
            today_timeline
        ], spacing=0))

        # ── Quick actions ──
        def create_action_btn(icon, text, bg_color, text_color, route):
            return ft.Container(
                col={"xs": 6, "sm": 6, "md": 6, "lg": 6},
                content=ft.Container(
                    padding=15, border_radius=12, bgcolor=bg_color, ink=True,
                    on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r),
                    border=ft.Border.all(1, current_theme.divider_color) if bg_color == current_theme.surface_color else None,
                    content=ft.Column([
                        ft.Icon(icon, color=text_color, size=28),
                        ft.Text(text, color=text_color, weight=ft.FontWeight.W_700, size=13)
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.START)
                )
            )

        quick_actions_section = self.make_pro_card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.BOLT_ROUNDED, color=ft.Colors.AMBER_500, size=20),
                ft.Text("TRUY CẬP NHANH", weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14)
            ]),
            ft.Container(height=5),
            ft.ResponsiveRow([
                create_action_btn(ft.Icons.DOCUMENT_SCANNER_ROUNDED, "Điểm danh ngay", current_theme.secondary, ft.Colors.WHITE, "/user/attendance"),
                create_action_btn(ft.Icons.EDIT_CALENDAR_ROUNDED, "Lịch giảng dạy", current_theme.surface_color, current_theme.secondary, "/user/schedule"),
                create_action_btn(ft.Icons.ANALYTICS_ROUNDED, "Báo cáo tiến độ", current_theme.surface_color, current_theme.secondary, "/user/stats"),
                create_action_btn(ft.Icons.MANAGE_ACCOUNTS_ROUNDED, "Hồ sơ của tôi", current_theme.surface_color, current_theme.secondary, "/user/profile"),
            ], run_spacing=5, spacing=5)
        ], spacing=0))

        # ── News ──
        news_list = ft.Column(controls=self._build_news_controls(), spacing=0)

        news_section = self.make_pro_card(ft.Column([
            ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.CAMPAIGN_ROUNDED, color=ft.Colors.RED_400, size=20),
                    ft.Text("BẢNG TIN HỌC VỤ", weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14)
                ]),
            ], alignment=ft.Alignment(-1,-1)),
            ft.Container(height=5),
            news_list
        ], spacing=0))

        # ── MAIN LAYOUT BUILDER ──
        layout_controls = [
            header_section,
            ft.Container(height=5),
            stats_row,
            ft.Container(height=5),
        ]

        # Xây dựng cột bên trái (Chứa Lịch trình, NẾU là desktop thì thêm Bảng danh sách lớp)
        left_col_controls = [timeline_section]
        if self.is_desktop:
            left_col_controls.append(self._build_desktop_class_table())

        # Xây dựng cột bên phải (Chứa Truy cập nhanh và Bảng tin)
        right_col_controls = [quick_actions_section,  news_section]

        # Layout cột linh hoạt cho Timeline & Quick Actions
        layout_controls.append(
            ft.ResponsiveRow([
                ft.Column(left_col_controls, col={"xs": 12, "md": 12, "lg": 7, "xl": 8}),
                ft.Column(right_col_controls, col={"xs": 12, "md": 12, "lg": 5, "xl": 4}),
            ], spacing=5, run_spacing=5)
        )

        dashboard_layout = ft.Column(layout_controls, spacing=0)

        return ft.Column(
            [dashboard_layout],
            scroll=ft.ScrollMode.AUTO, expand=True
        )

    def render_data_to_ui(self, thongbao, tkb, today):
        self.thongbao_data = thongbao
        self.tkb_data = tkb
        self.today_data = today
        self.is_loading = False
        self.apply_theme()



    # ══════════════════════════════════════════════════════════════════
    # CÁC HÀM FETCH RIÊNG BIỆT — để asyncio.gather chạy song song
    # ══════════════════════════════════════════════════════════════════
    async def _fetch_news(self, client) -> list:
        """Fetch thông báo mới nhất."""
        try:
            res = await client.get("/thongbao", params={
                "select": "*",
                "order": "created_at.desc",
                "limit": "3"
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"_fetch_news lỗi: {e}")
            return []

    async def _fetch_schedule(self, client) -> list:
        """Fetch thời khoá biểu của giảng viên."""
        if self.gv_id == "N/A":
            return []
        try:
            res = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan,sobuoi),hocky(namhoc,tenhocky)",
                "giangvien_id": f"eq.{self.gv_id}"
            })
            res.raise_for_status()
            all_tkb = res.json()
            if not all_tkb:
                return []
            # Lọc học kỳ mới nhất
            valid_hks = [s["hocky"] for s in all_tkb if s.get("hocky")]
            if not valid_hks:
                return all_tkb
            namhocs = sorted(set(hk["namhoc"] for hk in valid_hks), reverse=True)
            latest_hk = [hk for hk in valid_hks if hk["namhoc"] == namhocs[0]][0]["tenhocky"]
            return [s for s in all_tkb if s.get("hocky") and s["hocky"]["namhoc"] == namhocs[0] and s["hocky"]["tenhocky"] == latest_hk]
        except Exception as e:
            print(f"_fetch_schedule lỗi: {e}")
            return []

    async def _fetch_today(self, client) -> dict:
        """
        Fetch lịch dạy hôm nay + trạng thái điểm danh.
        Cần all_tkb nên nhận qua tham số riêng để tránh fetch lại.
        """
        if self.gv_id == "N/A":
            return {"classes": []}
        try:
            # Lấy TKB của GV (fetch nhẹ, chỉ lấy id)
            res_all = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan)",
                "giangvien_id": f"eq.{self.gv_id}"
            })
            res_all.raise_for_status()
            all_tkb = res_all.json()
            if not all_tkb:
                return {"classes": []}

            today_date = datetime.datetime.now(datetime.timezone.utc).astimezone().date()
            thu_hom_nay = today_date.weekday() + 2  # Flet dùng 2=Thứ 2 … 8=CN

            tkb_ids_str = ",".join(str(x["id"]) for x in all_tkb)
            res_tiet = await client.get("/tkb_tiet", params={
                "select": "id,tkb_id,thu,phong_hoc,tiet(thoigianbd,thoigiankt)",
                "tkb_id": f"in.({tkb_ids_str})",
                "thu": f"eq.{thu_hom_nay}",
                "order": "tiet(thoigianbd).asc"
            })
            res_tiet.raise_for_status()
            tiet_list = res_tiet.json()

            if not tiet_list:
                return {"classes": []}

            tiet_ids_str = ",".join(str(t["id"]) for t in tiet_list)
            res_dd = await client.get("/diemdanh", params={
                "select": "tkb_tiet_id",
                "tkb_tiet_id": f"in.({tiet_ids_str})",
                "ngay_diem_danh": f"eq.{today_date.isoformat()}"
            })
            res_dd.raise_for_status()
            dd_map = {str(d["tkb_tiet_id"]) for d in res_dd.json()}

            tkb_dict = {x["id"]: x for x in all_tkb}
            classes = []
            for t in tiet_list:
                tkb_info = tkb_dict.get(t["tkb_id"])
                if tkb_info:
                    classes.append({
                        "id": t["id"],
                        "ten_hp": tkb_info.get("hocphan", {}).get("tenhocphan", "N/A"),
                        "ten_lop": tkb_info.get("lop", {}).get("tenlop", "N/A"),
                        "phong_hoc": t.get("phong_hoc", "N/A"),
                        "thoigianbd": t.get("tiet", {}).get("thoigianbd"),
                        "thoigiankt": t.get("tiet", {}).get("thoigiankt"),
                        "da_diem_danh": str(t["id"]) in dd_map
                    })
            return {"classes": classes}

        except Exception as e:
            print(f"_fetch_today lỗi: {e}")
            return {"classes": []}

    # ══════════════════════════════════════════════════════════════════
    # LOAD DATA: asyncio.gather chạy song song tất cả fetch
    # ══════════════════════════════════════════════════════════════════
    async def load_data(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_name = session_data.get("name", "Giảng viên")
            self.gv_id = session_data.get("id", "N/A")
            
            if self._name_text:
                self._name_text.value = f"GV. {self.gv_name}"
                try:
                    self._name_text.update()
                except Exception:
                    pass

        try:
            # Chỉ cần gọi đúng 1 dòng này, Service và CacheManager sẽ tự lo phần còn lại!
            # Đặt TTL = 300 (5 phút)
            news_result, schedule_result, today_result = await HomeService.get_all_home_data(self.gv_id, ttl=300)

            # Xử lý kết quả (nếu lỗi ở API nào thì gán mảng rỗng cho API đó)
            fresh_news = news_result if isinstance(news_result, list) else []
            fresh_schedule = schedule_result if isinstance(schedule_result, list) else []
            fresh_today = today_result if isinstance(today_result, dict) else {"classes": []}

            # Render lại UI phẳng của em
            self.render_data_to_ui(fresh_news, fresh_schedule, fresh_today)

        except Exception as e:
            show_top_notification(self.app_page, "Lỗi hệ thống", "Không thể tải dữ liệu!", color=ft.Colors.ORANGE)
            print(f"HOME load_data ERROR: {e}")