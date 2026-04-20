import flet as ft
from flet import UrlLauncher
import flet_charts as fch
import json
import time
import asyncio
from core.helper import safe_json_load
from core.theme import current_theme
from core.config import get_supabase_client, SERVER_API_URL
from components.options.custom_dropdown import CustomDropdown

class StatsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 20
        self.bgcolor = current_theme.bg_color

        self.gv_id = "N/A"
        self.tkb_list = []
        
        # UI Elements
        self.dd_lop = CustomDropdown(label="Lớp học phần phân tích", options=[])
        
        self.txt_total_sv = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_avg_att = ft.Text("0%", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_warnings = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_conducted = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)

        # Cấu hình biểu đồ
        self.bar_chart = fch.BarChart(
            groups=[], 
            border=ft.Border.all(0),
            left_axis=fch.ChartAxis(),
            bottom_axis=fch.ChartAxis(),
            horizontal_grid_lines=fch.ChartGridLines(color=current_theme.divider_color, width=1),
        )
        
        self.pie_chart = fch.PieChart(sections=[], center_space_radius=40, sections_space=2)

        self.content = self.build_ui()
        self.app_page.run_task(self.init_data)

    # --- HÀM CẬP NHẬT THEME QUAN TRỌNG ---
    def apply_theme(self):
        """Hàm này giúp trang cập nhật màu sắc ngay lập tức khi đổi Dark/Light Mode"""
        self.bgcolor = current_theme.bg_color
        
        # Cập nhật màu sắc tĩnh của biểu đồ (vì biểu đồ không tự refresh màu grid)
        self.bar_chart.horizontal_grid_lines.color = current_theme.divider_color
        
        # Cập nhật màu sắc cho các nhãn văn bản
        self.txt_total_sv.color = current_theme.text_main
        self.txt_avg_att.color = current_theme.text_main
        # self.txt_warnings thường có màu đỏ/cam riêng nên có thể giữ nguyên
        self.txt_conducted.color = current_theme.text_main
        
        # Build lại toàn bộ UI Layout
        self.content = self.build_ui()
        self.update()

    async def init_data(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")

        if self.gv_id == "N/A": return

        client = await get_supabase_client()
        try:
            res = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan,sobuoi)",
                "giangvien_id": f"eq.{self.gv_id}"
            })
            if res.status_code == 200:
                self.tkb_list = res.json()
                
            if self.tkb_list:
                self.dd_lop.options = [
                    ft.dropdown.Option(key=str(t["id"]), text=f"{t['lop']['tenlop']} - {t['hocphan']['tenhocphan']}")
                    for t in self.tkb_list
                ]
                self.dd_lop.value = str(self.tkb_list[0]["id"])
                self.dd_lop.on_change = lambda e: self.app_page.run_task(self.load_class_stats)
                self.update()
                await self.load_class_stats()
                
        except Exception as e:
            print(f"Lỗi khởi tạo Stats: {e}")

    async def load_class_stats(self):
        tkb_id = self.dd_lop.value
        if not tkb_id: return
        
        prefs = ft.SharedPreferences()
        cache_key = f"stats_tkb_{tkb_id}"
        sync_key = f"sync_tkb_{tkb_id}"
        cached_str = await prefs.get(cache_key)
        last_sync = float(await prefs.get(sync_key) or 0)
        
        if cached_str and (time.time() - last_sync < 86400):
            data = safe_json_load(cached_str)
            self.render_stats_to_ui(data)
        else:
            await self.fetch_stats_from_api(tkb_id, prefs, cache_key, sync_key, time.time())

    async def fetch_stats_from_api(self, tkb_id, prefs, cache_key, sync_key, current_time):
        client = await get_supabase_client()
        try:
            selected_tkb = next((t for t in self.tkb_list if str(t["id"]) == tkb_id), None)
            if not selected_tkb: return
            
            lop_id = selected_tkb["lop_id"]
            sobuoi = selected_tkb["hocphan"]["sobuoi"] or 15

            res_sv = await client.get("/sinhvien", params={"select": "id", "class_id": f"eq.{lop_id}"})
            sv_list = res_sv.json()
            total_students = len(sv_list)

            res_tiet = await client.get("/tkb_tiet", params={"select": "id", "tkb_id": f"eq.{tkb_id}"})
            tiet_list = res_tiet.json()
            
            dd_list = []
            if tiet_list:
                tiet_ids_str = ",".join([str(t["id"]) for t in tiet_list])
                res_dd = await client.get("/diemdanh", params={
                    "select": "sv_id,trang_thai,ngay_diem_danh",
                    "tkb_tiet_id": f"in.({tiet_ids_str})"
                })
                dd_list = res_dd.json()

            unique_dates = sorted(list(set([d["ngay_diem_danh"] for d in dd_list])))
            total_conducted = len(unique_dates)
            present_count = len([d for d in dd_list if d["trang_thai"] == "Có mặt"])
            total_possible = total_students * total_conducted
            avg_attendance = int((present_count / total_possible) * 100) if total_possible > 0 else 0

            warnings = 0
            sv_attendance = {sv["id"]: 0 for sv in sv_list}
            for d in dd_list:
                if d["trang_thai"] == "Có mặt" and d["sv_id"] in sv_attendance:
                    sv_attendance[d["sv_id"]] += 1
            for sv_id, attended in sv_attendance.items():
                if (total_conducted - attended) > (sobuoi * 0.3):
                    warnings += 1

            bar_data = []
            for i, date in enumerate(unique_dates[-5:]):
                att_day = len([d for d in dd_list if d["ngay_diem_danh"] == date and d["trang_thai"] == "Có mặt"])
                pct = int((att_day / total_students) * 100) if total_students > 0 else 0
                bar_data.append({"label": f"B.{i+1}", "val": pct})

            final_data = {
                "total_sv": total_students, "avg_att": avg_attendance, "warnings": warnings,
                "conducted": total_conducted, "bar_data": bar_data,
                "pie_data": {"present": present_count, "absent": total_possible - present_count}
            }

            await asyncio.gather(
                prefs.set(cache_key, json.dumps(final_data)),
                prefs.set(sync_key, str(current_time))
            )
            self.render_stats_to_ui(final_data)
        except: pass

    def render_stats_to_ui(self, data):
        self.txt_total_sv.value = str(data["total_sv"])
        self.txt_avg_att.value = f"{data['avg_att']}%"
        self.txt_warnings.value = str(data["warnings"])
        self.txt_conducted.value = f"{data['conducted']} Buổi"
        self.txt_warnings.color = ft.Colors.RED_500 if data["warnings"] > 0 else ft.Colors.ORANGE_500

        groups_list = []
        labels = []
        for i, item in enumerate(data.get("bar_data", [])):
            groups_list.append(fch.BarChartGroup(x=i, rods=[fch.BarChartRod(from_y=0, to_y=item["val"], color=current_theme.secondary, width=20, border_radius=4)]))
            labels.append(fch.ChartAxisLabel(value=i, label=ft.Text(item["label"], size=10, color=current_theme.text_muted)))
            
        self.bar_chart.groups = groups_list
        self.bar_chart.bottom_axis = fch.ChartAxis(labels=labels)

        p_val, a_val = data["pie_data"]["present"], data["pie_data"]["absent"]
        if p_val == 0 and a_val == 0:
            self.pie_chart.sections = [fch.PieChartSection(100, title="Trống", color=current_theme.divider_color, radius=35)]
        else:
            self.pie_chart.sections = [
                fch.PieChartSection(p_val, title="Có mặt", color=ft.Colors.GREEN_400, radius=40),
                fch.PieChartSection(a_val, title="Vắng", color=ft.Colors.RED_400, radius=35),
            ]
        self.update()

    async def download_detailed(self, e): await UrlLauncher().launch_url(f"{SERVER_API_URL.rstrip('/')}/export/browser/detailed/{self.dd_lop.value}")
    async def download_overview(self, e): await UrlLauncher().launch_url(f"{SERVER_API_URL.rstrip('/')}/export/browser/overview/{self.gv_id}")
    async def download_warning(self, e): await UrlLauncher().launch_url(f"{SERVER_API_URL.rstrip('/')}/export/browser/warning/{self.dd_lop.value}")

    def build_ui(self):
        # Toolbar tinh chỉnh Dropdown không bị cắt
        toolbar = ft.Container(
            content=ft.Row([
                ft.Text("Làm mới 24h/lần theo lớp học phần", size=11, italic=True, color=current_theme.text_muted),
                ft.Row([
                    ft.Container(self.dd_lop, width=220), # Ràng buộc chiều rộng Dropdown
                    ft.IconButton(ft.Icons.REFRESH_ROUNDED, on_click=lambda _: self.app_page.run_task(self.load_class_stats))
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
            padding=ft.Padding(0, 0, 0, 10)
        )

        def make_kpi(title, text_control, icon, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=color, size=18), ft.Text(title, size=11, color=current_theme.text_muted)], spacing=8),
                    text_control,
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=current_theme.surface_variant, padding=12, border_radius=12, expand=True
            )

        # Lưới KPI 2x2
        kpi_grid = ft.ResponsiveRow([
            ft.Column([make_kpi("Tổng SV", self.txt_total_sv, ft.Icons.PEOPLE_ALT_ROUNDED, ft.Colors.BLUE)], col=6),
            ft.Column([make_kpi("Chuyên cần", self.txt_avg_att, ft.Icons.CHECK_CIRCLE_ROUNDED, ft.Colors.GREEN)], col=6),
            ft.Column([make_kpi("Cảnh báo", self.txt_warnings, ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.ORANGE)], col=6),
            ft.Column([make_kpi("Buổi dạy", self.txt_conducted, ft.Icons.SCHOOL_ROUNDED, ft.Colors.PURPLE)], col=6),
        ], spacing=10, run_spacing=10)

        # Cụm nút xếp dọc dãn rộng dạng viên nang
        export_section = ft.Container(
            bgcolor=current_theme.surface_variant, padding=20, border_radius=16,
            content=ft.Column([
                ft.Text("CÔNG CỤ XUẤT BẢN", size=12, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                ft.Column([
                    ft.ElevatedButton(
                        "Chi tiết điểm danh", icon=ft.Icons.FILE_DOWNLOAD, on_click=self.download_detailed,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30), padding=ft.Padding(0, 15, 0, 15), color=current_theme.text_main)
                    ),
                    ft.ElevatedButton(
                        "Tổng quan học kỳ", icon=ft.Icons.ANALYTICS, on_click=self.download_overview,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30), padding=ft.Padding(0, 15, 0, 15), color=current_theme.text_main)
                    ),
                    ft.ElevatedButton(
                        "Cảnh báo học vụ", icon=ft.Icons.ERROR_OUTLINE, on_click=self.download_warning,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30), padding=ft.Padding(0, 15, 0, 15), color=ft.Colors.RED_500)
                    ),
                ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
            ], spacing=15)
        )

        left_column = ft.Column([kpi_grid, export_section], spacing=15)

        right_column = ft.Column([
            ft.Container(
                bgcolor=current_theme.surface_variant, padding=20, border_radius=12,
                content=ft.Column([
                    ft.Text("Chuyên cần 5 buổi gần nhất (%)", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(self.bar_chart, height=180)
                ])
            ),
            ft.Container(
                bgcolor=current_theme.surface_variant, padding=20, border_radius=12,
                content=ft.Column([
                    ft.Text("Trạng thái lớp học", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(self.pie_chart, height=180, alignment=ft.Alignment(0,0))
                ])
            )
        ], spacing=15)

        # Responsive layout: Desktop (5:7) / Mobile (Stack)
        main_layout = ft.ResponsiveRow([
            ft.Column([left_column], col={"sm": 12, "lg": 5}),
            ft.Column([right_column], col={"sm": 12, "lg": 7}),
        ], spacing=20)

        return ft.Column([toolbar, ft.Divider(height=1, color=current_theme.divider_color), main_layout], scroll=ft.ScrollMode.AUTO, spacing=15)