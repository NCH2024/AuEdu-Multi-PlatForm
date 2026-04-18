import flet as ft
from flet import UrlLauncher # Import chuẩn mới
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
        
        # UI Elements cần update dữ liệu
        self.dd_lop = CustomDropdown(label="Lớp học phần phân tích", options=[])
        
        # Khởi tạo các nhãn Text để dễ dàng gán dữ liệu sau này
        self.txt_total_sv = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_avg_att = ft.Text("0%", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_warnings = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.txt_conducted = ft.Text("0", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main)

        # Cấu hình biểu đồ chuẩn mới
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

    async def init_data(self):
        """Khởi tạo: Lấy gv_id và danh sách lớp để đưa vào Dropdown"""
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")

        if self.gv_id == "N/A": return

        client = await get_supabase_client()
        try:
            # Lấy TKB của GV
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
                
                # Bắt đầu tải thống kê cho lớp mặc định
                await self.load_class_stats()
                
        except Exception as e:
            print(f"Lỗi khởi tạo Stats: {e}")

    async def load_class_stats(self):
        """Logic Cache cho từng lớp học (tkb_id)"""
        tkb_id = self.dd_lop.value
        if not tkb_id: return
        
        prefs = ft.SharedPreferences()
        cache_key = f"stats_tkb_{tkb_id}"
        sync_key = f"sync_tkb_{tkb_id}"

        cached_str = await prefs.get(cache_key)
        last_sync = float(await prefs.get(sync_key) or 0)
        current_time = time.time()

        # Giữ Cache 1 ngày (86400s) cho thống kê chi tiết lớp học
        if cached_str and (current_time - last_sync < 86400):
            data = safe_json_load(cached_str)
            self.render_stats_to_ui(data)
        else:
            await self.fetch_stats_from_api(tkb_id, prefs, cache_key, sync_key, current_time)

    async def fetch_stats_from_api(self, tkb_id, prefs, cache_key, sync_key, current_time):
        """Thực hiện các query đếm dữ liệu thông qua REST API Supabase"""
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

            warning_threshold = sobuoi * 0.3
            warnings = 0
            sv_attendance = {sv["id"]: 0 for sv in sv_list}
            
            for d in dd_list:
                if d["trang_thai"] == "Có mặt" and d["sv_id"] in sv_attendance:
                    sv_attendance[d["sv_id"]] += 1
                    
            for sv_id, attended in sv_attendance.items():
                if (total_conducted - attended) > warning_threshold:
                    warnings += 1

            bar_data = []
            for i, date in enumerate(unique_dates[-5:]):
                att_day = len([d for d in dd_list if d["ngay_diem_danh"] == date and d["trang_thai"] == "Có mặt"])
                pct = int((att_day / total_students) * 100) if total_students > 0 else 0
                bar_data.append({"label": f"B.{i+1}", "val": pct})

            pie_absent = total_possible - present_count

            final_data = {
                "total_sv": total_students,
                "avg_att": avg_attendance,
                "warnings": warnings,
                "conducted": total_conducted,
                "bar_data": bar_data,
                "pie_data": {"present": present_count, "absent": pie_absent}
            }

            await asyncio.gather(
                prefs.set(cache_key, json.dumps(final_data)),
                prefs.set(sync_key, str(current_time))
            )

            self.render_stats_to_ui(final_data)

        except Exception as ex:
            print(f"Lỗi tính toán dữ liệu API: {ex}")

    def render_stats_to_ui(self, data):
        """Bơm dữ liệu từ state vào các Control hiển thị"""
        self.txt_total_sv.value = str(data["total_sv"])
        self.txt_avg_att.value = f"{data['avg_att']}%"
        self.txt_warnings.value = str(data["warnings"])
        self.txt_conducted.value = f"{data['conducted']} Buổi"
        
        self.txt_warnings.color = ft.Colors.RED_500 if data["warnings"] > 0 else ft.Colors.ORANGE_500

        groups_list = []
        labels = []
        for i, item in enumerate(data.get("bar_data", [])):
            groups_list.append(
                fch.BarChartGroup(
                    x=i, 
                    rods=[fch.BarChartRod(from_y=0, to_y=item["val"], color=current_theme.secondary, width=25, border_radius=4)]
                )
            )
            labels.append(fch.ChartAxisLabel(value=i, label=ft.Text(item["label"], size=12, color=current_theme.text_muted)))
            
        self.bar_chart.groups = groups_list
        self.bar_chart.bottom_axis = fch.ChartAxis(labels=labels) if labels else fch.ChartAxis()

        p_val, a_val = data["pie_data"]["present"], data["pie_data"]["absent"]
        if p_val == 0 and a_val == 0:
            self.pie_chart.sections = [fch.PieChartSection(100, title="Chưa có DL", color=current_theme.divider_color, radius=40)]
        else:
            self.pie_chart.sections = [
                fch.PieChartSection(p_val, title="Có mặt", color=ft.Colors.GREEN_400, radius=45),
                fch.PieChartSection(a_val, title="Vắng", color=ft.Colors.RED_400, radius=40),
            ]

        self.update()

    # --- CÁC HÀM XUẤT EXCEL (ĐÃ SỬA SANG TRANG ĐỆM HTML) ---
    def show_downloading_noti(self):
        """Hiện thông báo nhỏ trong app Flet để báo hiệu đang mở Web"""
        self.app_page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CLOUD_DOWNLOAD_OUTLINED, color=ft.Colors.WHITE),
                ft.Text("Đang mở trình duyệt để tải tệp Excel...", color=ft.Colors.WHITE)
            ]),
            bgcolor=current_theme.secondary,
            behavior=ft.SnackBarBehavior.FLOATING,
            duration=3000
        )
        self.app_page.snack_bar.open = True
        self.app_page.update()

    async def download_detailed(self, e):
        if self.dd_lop.value:
            self.show_downloading_noti()
            # GỌI ĐẾN API TRANG ĐỆM BROWSER
            await UrlLauncher().launch_url(f"{SERVER_API_URL}/export/browser/detailed/{self.dd_lop.value}")

    async def download_overview(self, e):
        if self.gv_id != "N/A":
            self.show_downloading_noti()
            # GỌI ĐẾN API TRANG ĐỆM BROWSER
            await UrlLauncher().launch_url(f"{SERVER_API_URL}/export/browser/overview/{self.gv_id}")

    async def download_warning(self, e):
        if self.dd_lop.value:
            self.show_downloading_noti()
            # GỌI ĐẾN API TRANG ĐỆM BROWSER
            await UrlLauncher().launch_url(f"{SERVER_API_URL}/export/browser/warning/{self.dd_lop.value}")

    def build_ui(self):
        toolbar = ft.Row([
            ft.Column([
                ft.Text("PHÂN TÍCH HỌC VỤ", size=20, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                ft.Text("Làm mới 24h/lần theo lớp học phần", size=11, italic=True, color=current_theme.text_muted)
            ], spacing=2),
            ft.Row([
                self.dd_lop, 
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="Làm mới ngay", on_click=lambda _: self.app_page.run_task(self.load_class_stats))
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        def make_kpi(title, text_control, icon, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=color, size=20), ft.Text(title, size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500)], spacing=10),
                    text_control,
                ], spacing=5),
                bgcolor=current_theme.surface_variant, padding=20, border_radius=12, expand=True
            )

        kpi_row = ft.ResponsiveRow([
            ft.Column([make_kpi("Tổng sinh viên", self.txt_total_sv, ft.Icons.PEOPLE_ALT_ROUNDED, ft.Colors.BLUE)], col={"sm": 6, "md": 3}),
            ft.Column([make_kpi("Chuyên cần", self.txt_avg_att, ft.Icons.CHECK_CIRCLE_ROUNDED, ft.Colors.GREEN)], col={"sm": 6, "md": 3}),
            ft.Column([make_kpi("Cảnh báo học vụ", self.txt_warnings, ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.ORANGE)], col={"sm": 6, "md": 3}),
            ft.Column([make_kpi("Số buổi đã dạy", self.txt_conducted, ft.Icons.SCHOOL_ROUNDED, ft.Colors.PURPLE)], col={"sm": 6, "md": 3}),
        ], spacing=15)

        charts_row = ft.ResponsiveRow([
            ft.Column([
                ft.Container(
                    bgcolor=current_theme.surface_variant, padding=20, border_radius=12,
                    content=ft.Column([
                        ft.Text("Tỷ lệ đi học các buổi gần nhất (%)", weight=ft.FontWeight.BOLD),
                        ft.Container(self.bar_chart, height=200, padding=10)
                    ])
                )
            ], col={"sm": 12, "lg": 8}),
            
            ft.Column([
                ft.Container(
                    bgcolor=current_theme.surface_variant, padding=20, border_radius=12,
                    content=ft.Column([
                        ft.Text("Trạng thái tổng quan", weight=ft.FontWeight.BOLD),
                        ft.Container(self.pie_chart, height=200, alignment=ft.Alignment(0,0))
                    ])
                )
            ], col={"sm": 12, "lg": 4}),
        ], spacing=15)

        # --- SỬA LỖI STYLE BUTTON VÀ PADDING ---
        export_section = ft.Container(
            content=ft.Row([
                ft.Text("Công cụ báo cáo Excel:", weight=ft.FontWeight.W_500),
                ft.TextButton("Chi tiết điểm danh", icon=ft.Icons.FILE_DOWNLOAD, on_click=self.download_detailed),
                ft.TextButton("Tổng quan học kỳ", icon=ft.Icons.ANALYTICS, on_click=self.download_overview),
                ft.TextButton(
                    "Cảnh báo học vụ", 
                    icon=ft.Icons.ERROR_OUTLINE, 
                    style=ft.ButtonStyle(color=ft.Colors.RED_400), # Chuẩn flet mới
                    on_click=self.download_warning
                ),
            ], spacing=20),
            padding=ft.Padding(0, 10, 0, 0) # Chuẩn thay thế padding.only()
        )

        return ft.Column([toolbar, ft.Divider(height=1, color=current_theme.divider_color), kpi_row, charts_row, export_section], scroll=ft.ScrollMode.AUTO, spacing=25)