import flet as ft
from core.theme import current_theme, get_flat_container
from core.config import get_supabase_client, SERVER_API_URL
from core.helper import safe_json_load
import httpx

class StudentSearchPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = ft.Padding(15, 10, 15, 10)

        # Quản lý trạng thái: SEARCH (Tìm kiếm) hoặc DETAIL (Chi tiết)
        self.view_mode = "SEARCH" 
        self.gv_id = "N/A"
        self.search_results = []
        self.student_history = []
        self.selected_student = None

        self.is_mobile = self.app_page.width < 600

        # --- UI COMPONENTS ---
        self.search_tf = ft.TextField(
            hint_text="Nhập Tên hoặc Mã Sinh Viên rồi nhấn Enter...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=30,
            content_padding=15,
            text_size=13,
            expand=True,
            bgcolor=current_theme.surface_color,
            border_color=current_theme.divider_color,
            on_submit=lambda e: self.app_page.run_task(self.handle_search, e.control.value)
        )

        self.loading = ft.ProgressBar(visible=False, color=current_theme.primary)
        self.main_content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

        self.render_view()
        self.app_page.run_task(self.init_data)

    def apply_theme(self):
        self.bgcolor = current_theme.bg_color
        self.search_tf.bgcolor = current_theme.surface_color
        self.search_tf.border_color = current_theme.divider_color
        self.render_view()
        self.update()

    async def init_data(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            data = safe_json_load(session_str)
            self.gv_id = data.get("id", "N/A")

    # ==========================================
    # LOGIC API & DATA
    # ==========================================
    async def handle_search(self, keyword):
        if not keyword or not keyword.strip() or self.gv_id == "N/A": return
        
        self.view_mode = "SEARCH"
        self.loading.visible = True
        self.update()

        url = f"{SERVER_API_URL.rstrip('/')}/search-students"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, params={"gv_id": self.gv_id, "keyword": keyword})
                self.search_results = res.json() if res.status_code == 200 else []
        except Exception as e:
            print(f"Lỗi tìm kiếm: {e}")
            self.search_results = []
            
        self.loading.visible = False
        self.render_view()
        self.update()

    async def load_student_detail(self, student_info):
        self.view_mode = "DETAIL"
        self.selected_student = student_info
        self.loading.visible = True
        self.update()

        # ĐÃ GIỮ NGUYÊN ĐƯỜNG DẪN API CỦA EM
        url = f"{SERVER_API_URL.rstrip('/')}/student/{student_info['id']}/history"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, params={"gv_id": self.gv_id})
                self.student_history = res.json() if res.status_code == 200 else []
        except Exception as e:
            print(f"Lỗi tải lịch sử cá nhân: {e}")
            self.student_history = []

        self.loading.visible = False
        self.render_view()
        self.update()

    # ==========================================
    # BUILD LAYOUTS
    # ==========================================
    def build_search_view(self):
        # 1. Thanh tìm kiếm
        search_bar = ft.Row([self.search_tf], alignment=ft.MainAxisAlignment.CENTER)

        # 2. Lưới kết quả
        grid = ft.ResponsiveRow(spacing=15, run_spacing=15)
        
        if not self.search_results:
            return ft.Column([
                search_bar,
                ft.Container(height=30),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_SEARCH, size=50, color=current_theme.divider_color),
                        ft.Text("Hãy nhập từ khóa để bắt đầu tìm kiếm", color=current_theme.text_muted, italic=True)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0), padding=50
                )
            ])

        for sv in self.search_results:
            ho_ten = f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip()
            
            card = ft.Container(
                col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
                bgcolor=current_theme.surface_variant,
                border_radius=12, padding=15,
                border=ft.Border.all(1, current_theme.divider_color),
                ink=True, on_click=lambda e, s=sv: self.app_page.run_task(self.load_student_detail, s),
                content=ft.Column([
                    ft.Row([
                        ft.CircleAvatar(
                            content=ft.Text(sv.get("ten", "A")[0], weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            bgcolor=current_theme.accent, radius=20
                        ),
                        ft.Column([
                            ft.Text(ho_ten, weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"MSSV: {sv['id']}", size=12, color=current_theme.secondary)
                        ], spacing=2, expand=True)
                    ]),
                    ft.Divider(height=10, color=current_theme.divider_color),
                    ft.Row([
                        ft.Icon(ft.Icons.CLASS_, size=14, color=current_theme.text_muted),
                        ft.Text(sv.get("ten_lop", "Không rõ"), size=11, color=current_theme.text_muted, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                    ], spacing=5)
                ], spacing=10)
            )
            grid.controls.append(card)

        return ft.Column([search_bar, ft.Container(height=10), grid], expand=True)

    def build_detail_view(self):
        sv = self.selected_student
        
        # --- LOGIC NHÓM DỮ LIỆU VÀ TÍNH TỶ LỆ CHUẨN ---
        grouped_data = {}
        for item in self.student_history:
            subject = item.get('ten_mon', 'Không xác định')
            if subject not in grouped_data:
                grouped_data[subject] = []
            grouped_data[subject].append(item)

        history_sections = []
        for subject, records in grouped_data.items():
            # Lấy tổng số buổi thiết lập từ record đầu tiên của nhóm
            total_planned = records[0].get('tong_so_buoi', 15) # Mặc định 15 nếu lỗi
            
            # Chỉ đếm những buổi "Có mặt" thực tế
            actual_present = sum(1 for r in records if r['trang_thai'] == 'Có mặt')
            
            # TỶ LỆ CHUẨN: Tính trên tổng số buổi của học phần
            sub_rate = int((actual_present / total_planned * 100)) if total_planned > 0 else 0

            rows = []
            for r in records:
                is_absent = r['trang_thai'] != "Có mặt"
                rows.append(
                    ft.Container(
                        padding=12, border_radius=8, bgcolor=current_theme.surface_color,
                        margin=ft.Margin(0, 0, 0, 5),
                        border=ft.Border(left=ft.BorderSide(3, ft.Colors.RED_500 if is_absent else ft.Colors.GREEN_600)),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(r.get('ngay', ''), weight=ft.FontWeight.W_600, size=12),
                                ft.Text(r.get('gio_quet', ''), size=10, color=current_theme.text_muted)
                            ], width=75),
                            ft.Text(f"Phòng {r.get('phong_hoc', '')}", size=12, expand=True),
                            ft.Container(
                                content=ft.Text(r['trang_thai'], color=ft.Colors.RED_500 if is_absent else ft.Colors.GREEN_600, size=10, weight=ft.FontWeight.BOLD),
                                padding=ft.Padding(6, 2, 6, 2), border_radius=4,
                                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_500 if is_absent else ft.Colors.GREEN_600)
                            )
                        ])
                    )
                )

            history_sections.append(
                ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BOOKMARK_ROUNDED, size=16, color=current_theme.primary),
                        ft.Text(subject.upper(), size=12, weight=ft.FontWeight.BOLD, color=current_theme.primary, expand=True),
                        # Hiển thị rõ: Có mặt / Tổng buổi thiết lập
                        ft.Text(f"Chuyên cần: {actual_present}/{total_planned} ({sub_rate}%)", 
                                size=11, weight=ft.FontWeight.W_600, color=current_theme.secondary)
                    ], spacing=8),
                    ft.Column(rows, spacing=0),
                    ft.Container(height=10)
                ])
            )

        # UI Header & Profile (Giữ nguyên phong cách tối ưu Padding)
        profile_header = ft.Container(
            bgcolor=current_theme.surface_variant, border_radius=12, padding=15,
            border=ft.Border.all(1, current_theme.divider_color),
            content=ft.Row([
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color=ft.Colors.WHITE), bgcolor=current_theme.secondary, radius=30),
                ft.Column([
                    ft.Text(f"{sv.get('hodem', '')} {sv.get('ten', '')}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"MSSV: {sv['id']} | {sv.get('gioitinh', 'N/A')}", size=12, color=current_theme.text_muted)
                ], spacing=2, expand=True)
            ])
        )

        return ft.Column([
            ft.TextButton("Quay lại tìm kiếm", icon=ft.Icons.ARROW_BACK_IOS_NEW, on_click=lambda _: self._go_back_to_search(), style=ft.ButtonStyle(color=current_theme.text_muted)),
            profile_header,
            ft.Text("CHI TIẾT THEO HỌC PHẦN", size=12, weight=ft.FontWeight.W_800, color=current_theme.text_muted),
            ft.Column(history_sections, spacing=5)
        ], spacing=15, scroll=ft.ScrollMode.AUTO)

    def _go_back_to_search(self):
        self.view_mode = "SEARCH"
        self.render_view()
        self.update()

    def render_view(self):
        self.is_mobile = self.app_page.width < 600
        
        back_btn = ft.TextButton(
            "Quay về", icon=ft.Icons.CHEVRON_LEFT, 
            on_click=lambda _: self.app_page.run_task(self.app_page.push_route, "/user/attendance"),
            style=ft.ButtonStyle(color=current_theme.text_main, padding=0)
        )
        
        title = ft.Text("Tra cứu chi tiết", size=14 if self.is_mobile else 16, weight=ft.FontWeight.BOLD)

        header = ft.Row([back_btn, title], spacing=10)

        self.main_content_area.controls.clear()
        if self.view_mode == "SEARCH":
            self.main_content_area.controls.append(self.build_search_view())
        else:
            self.main_content_area.controls.append(self.build_detail_view())

        self.content = ft.Column([header, self.loading, ft.Divider(height=1), self.main_content_area], expand=True, spacing=10)