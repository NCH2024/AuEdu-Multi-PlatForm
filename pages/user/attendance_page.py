import flet as ft
import datetime
import asyncio
import json
import time

from components.pages.base_dashboard import BaseDashboard
from components.pages.page_frame import PageFrame
from components.options.custom_dropdown import CustomDropdown
from components.options.camera_view import CameraView
from components.options.top_notification import show_top_notification
from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from core.config import get_supabase_client
from core.helper import hash_data, safe_json_load

class AttendancePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        self.gv_id = "N/A" 
        self.tkb_data = [] 
        self.all_students_data = []
        self.current_limit = 5

        self.dd_row_limit = CustomDropdown(
            label="Hiển thị", 
            options=[
                ft.dropdown.Option("5"), ft.dropdown.Option("10"), 
                ft.dropdown.Option("20"), ft.dropdown.Option("50"), 
                ft.dropdown.Option("100")
            ], 
            value="5", 
            on_change=self.handle_limit_change
        )
        self.btn_load_more = ft.TextButton(
            content=ft.Text("Xem thêm 10 dòng 🔽", color=SECONDARY_COLOR, weight=ft.FontWeight.BOLD), 
            visible=False, 
            on_click=self.handle_load_more
        )

        self.dd_lop = CustomDropdown(label="Lớp", options=[], col={"sm": 6, "md": 3}, on_change=self.handle_lop_change)
        self.dd_hocphan = CustomDropdown(label="Học phần", options=[], col={"sm": 6, "md": 3})
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        self.dd_ngay = CustomDropdown(label="Ngày", options=[ft.dropdown.Option(today_str)], value=today_str, col={"sm": 6, "md": 3})
        self.dd_buoi = CustomDropdown(label="Buổi", options=[ft.dropdown.Option("Sáng"), ft.dropdown.Option("Chiều"), ft.dropdown.Option("Tối")], col={"sm": 6, "md": 3})
        
        self.dd_camera = CustomDropdown(label="Chọn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera)
        
        self.test_progress = ft.ProgressBar(visible=False, color=ACCENT_COLOR, height=2)
        self.test_status_text = ft.Text("", size=11, color=ft.Colors.GREY_700, italic=True, visible=False)

        self.dt_sinhvien = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Mã SV", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)), 
                ft.DataColumn(ft.Text("Họ Tên", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
                ft.DataColumn(ft.Text("Giới tính", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)), 
                ft.DataColumn(ft.Text("Lớp", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
                ft.DataColumn(ft.Text("Trạng thái", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)), 
                ft.DataColumn(ft.Text("Thời gian", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)),
            ], 
            rows=[], 
            heading_row_color=ft.Colors.with_opacity(0.1, SECONDARY_COLOR), 
            border_radius=8, 
            data_row_max_height=40,
        )

        # Đã loại bỏ hoàn toàn LoadingOverlay vì Cache load quá nhanh!
        self.content = self.build_ui()
        self.app_page.run_task(self.initialize_page)

    async def initialize_page(self):
        # Đọc Session để lấy ID Giảng Viên
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.gv_id = session_data.get("id", "N/A")
            
        try:
            # Load danh sách Dropdown bằng cơ chế Cache mới
            await self.load_dropdowns()
        except Exception as e:
            self._show_error_snackbar(f"Lỗi tải dữ liệu lớp: {e}")

        try:
            # Gọi Camera chạy ngầm
            await self.camera_view.load_available_cameras()
        except Exception as e:
            self._show_error_snackbar(f"Lỗi khởi tạo thiết bị: {e}")
        
        if getattr(self, "page", None):
            self.update()          

    def build_ui(self):
        nang_cao_content = ft.Column([
            ft.Button(content=ft.Text("Lịch sử điểm danh", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_GREY_600),
            ft.Button(content=ft.Text("Tra cứu sinh viên", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_GREY_600)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        nang_cao_tile = ft.ExpansionTile(title=ft.Text("Chức năng nâng cao", weight=ft.FontWeight.BOLD, size=13), controls=[nang_cao_content], collapsed_text_color=SECONDARY_COLOR, text_color=SECONDARY_COLOR)

        self.rg_mode = ft.RadioGroup(
            value="1", 
            content=ft.Column([ft.Radio(value="1", label="Từng sinh viên"), ft.Radio(value="all", label="Cả lớp")])
        )
        
        diem_danh_content = ft.Column([
            self.rg_mode, 
            ft.Button(
                content=ft.Text("Điểm danh ngay", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
                bgcolor=SECONDARY_COLOR,
                on_click=self.handle_start_session 
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        
        diem_danh_tile = ft.ExpansionTile(title=ft.Text("Thao tác điểm danh", weight=ft.FontWeight.BOLD, size=13), controls=[diem_danh_content], expanded=True, collapsed_text_color=SECONDARY_COLOR, text_color=SECONDARY_COLOR)

        sinh_trac_content = ft.Column([
            ft.Button(content=ft.Text("Đào tạo khuôn mặt", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_700),
            ft.Button(content=ft.Text("Dữ liệu khuôn mặt", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_700)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        sinh_trac_tile = ft.ExpansionTile(title=ft.Text("Sinh trắc học", weight=ft.FontWeight.BOLD, size=13), controls=[sinh_trac_content], collapsed_text_color=SECONDARY_COLOR, text_color=SECONDARY_COLOR)

        thiet_bi_content = ft.Column([
            self.dd_camera,
            self.camera_view,
            ft.Row([
                ft.Button(content=ft.Text("Lưu", color=ft.Colors.WHITE), bgcolor=ACCENT_COLOR, expand=True), 
                ft.Button(content=ft.Text("Kiểm tra", color=ft.Colors.WHITE), bgcolor=SECONDARY_COLOR, expand=True, on_click=self.handle_test_camera)
            ]),
            self.test_progress,
            self.test_status_text,
            ft.Text("Yêu cầu lưu cấu hình trước khi kiểm tra thiết bị.", size=10, color=ft.Colors.GREY_600)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        
        thiet_bi_tile = ft.ExpansionTile(title=ft.Text("Thiết lập Camera", weight=ft.FontWeight.BOLD, size=13), controls=[thiet_bi_content], expanded=True, collapsed_text_color=SECONDARY_COLOR, text_color=SECONDARY_COLOR)
        
        side_column = get_glass_container(content=ft.Column([diem_danh_tile, thiet_bi_tile, sinh_trac_tile, nang_cao_tile], spacing=0))

        table_header = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("DANH SÁCH LỚP", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=14), ft.Container(content=self.dd_row_limit, width=90)])
        combined_attendance_card = get_glass_container(
            content=ft.Column([
                ft.Text("BỘ LỌC THÔNG TIN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=12),
                ft.ResponsiveRow([self.dd_lop, self.dd_hocphan, self.dd_ngay, self.dd_buoi]),
                ft.Row([ft.Button(content=ft.Text("Truy xuất danh sách", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600), bgcolor=ACCENT_COLOR, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=self.handle_load_students)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(color=ft.Colors.BLACK_12, height=30),
                table_header,
                ft.Row([self.dt_sinhvien], scroll=ft.ScrollMode.AUTO),
                ft.Row([self.btn_load_more], alignment=ft.MainAxisAlignment.CENTER) 
            ])
        )

        main_layout = ft.ResponsiveRow([
            ft.Column([combined_attendance_card], col={"sm": 12, "md": 8}),
            ft.Column([side_column], col={"sm": 12, "md": 4}),
        ])

        framed_layout = PageFrame(page=self.app_page, page_title="ĐIỂM DANH SINH VIÊN", main_content=main_layout)
        return BaseDashboard(page=self.app_page, active_route="/user/attendance", main_content=framed_layout)

    # ==========================================
    # LOGIC RENDER DROPDOWN ĐỘC LẬP
    # ==========================================
    def render_dropdowns(self, tkb_data, tiet_data):
        if not tkb_data: return
        self.tkb_data = tkb_data 

        today = datetime.datetime.now()
        thu_today = today.weekday() + 2 
        
        default_lop_id = None
        default_hp_id = None

        if tiet_data:
            for t in tiet_data:
                if t["thu"] == thu_today:
                    for tkb in self.tkb_data:
                        if str(tkb["id"]) == str(t["tkb_id"]):
                            default_lop_id = tkb["lop_id"]
                            default_hp_id = tkb["hocphan_id"]
                            break
                    if default_lop_id: break

        lops = {row["lop_id"]: row["lop"]["tenlop"] for row in self.tkb_data}
        self.dd_lop.options = [ft.dropdown.Option(key=str(k), text=v) for k, v in lops.items()]

        if default_lop_id and str(default_lop_id) in [str(k) for k in lops.keys()]:
            self.dd_lop.value = str(default_lop_id)
        elif lops:
            self.dd_lop.value = str(list(lops.keys())[0])
        else:
            self.dd_lop.value = None

        self._sync_handle_lop_change(auto_hp_id=default_hp_id)
        
        if getattr(self, "page", None):
            self.update()

    def _sync_handle_lop_change(self, auto_hp_id=None):
        lop_id = self.dd_lop.value
        hps = {row["hocphan_id"]: row["hocphan"]["tenhocphan"] for row in self.tkb_data if str(row["lop_id"]) == str(lop_id)}
        self.dd_hocphan.options = [ft.dropdown.Option(key=str(k), text=v) for k, v in hps.items()]

        if auto_hp_id and str(auto_hp_id) in [str(k) for k in hps.keys()]:
            self.dd_hocphan.value = str(auto_hp_id)
        elif hps:
            self.dd_hocphan.value = str(list(hps.keys())[0])
        else:
            self.dd_hocphan.value = None

    async def handle_lop_change(self, e, auto_hp_id=None):
        self._sync_handle_lop_change(auto_hp_id)
        if getattr(self, "page", None):
            self.update()

    # ==========================================
    # ÁP DỤNG THUẬT TOÁN CACHE HASH 
    # ==========================================
    async def load_dropdowns(self):
        if self.gv_id == "N/A": return
        
        prefs = ft.SharedPreferences()

        # ==============================
        # LOAD CACHE
        # ==============================
        cached_tkb = safe_json_load(await prefs.get(f"cached_tkb_{self.gv_id}"))
        cached_tiet = safe_json_load(await prefs.get(f"cached_tiet_{self.gv_id}"))

        last_sync = float(await prefs.get(f"last_sync_attendance_{self.gv_id}") or 0)

        cached_tkb_hash = await prefs.get(f"tkb_hash_{self.gv_id}")
        cached_tiet_hash = await prefs.get(f"tiet_hash_{self.gv_id}")

        current_time = time.time()
        TTL = 300  # 5 phút

        # ==============================
        # STEP 1: HIỂN THỊ CACHE NGAY
        # ==============================
        if cached_tkb is not None and cached_tiet is not None:
            self.render_dropdowns(cached_tkb, cached_tiet)

        # ==============================
        # STEP 2: CHECK TTL
        # ==============================
        if current_time - last_sync < TTL:
            # print("ATTENDANCE: Cache còn hạn, bỏ qua bước gọi API!")
            return

        # ==============================
        # STEP 3: CALL API (BACKGROUND)
        # ==============================
        try:
            async with await get_supabase_client() as client:
                
                # ---- TKB ----
                params_tkb = {"select": "id,lop_id,hocphan_id,lop(tenlop),hocphan(tenhocphan)", "giangvien_id": f"eq.{self.gv_id}"}
                res_tkb = await client.get("/thoikhoabieu", params=params_tkb)
                res_tkb.raise_for_status()
                fresh_tkb = res_tkb.json()

                # ---- TIẾT ----
                fresh_tiet = []
                if fresh_tkb:
                    tkb_ids = [str(item['id']) for item in fresh_tkb]
                    params_tiet = {"select": "tkb_id,thu", "tkb_id": f"in.({','.join(tkb_ids)})"}
                    res_tiet = await client.get("/tkb_tiet", params=params_tiet)
                    res_tiet.raise_for_status()
                    fresh_tiet = res_tiet.json()

            # ==============================
            # STEP 4: HASH COMPARE
            # ==============================
            new_tkb_hash = hash_data(fresh_tkb)
            new_tiet_hash = hash_data(fresh_tiet)

            is_changed = (
                new_tkb_hash != cached_tkb_hash or
                new_tiet_hash != cached_tiet_hash
            )

            # ==============================
            # STEP 5: UPDATE CACHE
            # ==============================
            await prefs.set(f"cached_tkb_{self.gv_id}", json.dumps(fresh_tkb))
            await prefs.set(f"cached_tiet_{self.gv_id}", json.dumps(fresh_tiet))

            await prefs.set(f"tkb_hash_{self.gv_id}", new_tkb_hash)
            await prefs.set(f"tiet_hash_{self.gv_id}", new_tiet_hash)

            await prefs.set(f"last_sync_attendance_{self.gv_id}", str(current_time))

            # ==============================
            # STEP 6: UPDATE UI IF CHANGED
            # ==============================
            if is_changed or cached_tkb is None:
                print("ATTENDANCE [SYNC] ... đang đồng bộ dữ liệu lớp học mới ...")
                self.render_dropdowns(fresh_tkb, fresh_tiet)
            else:
                print("ATTENDANCE [SYNC] Dữ liệu chuẩn xác")

        except Exception as e:
            show_top_notification(self.app_page, "ATTENDANCE [Không thể kết nối]", "Vui lòng kiểm tra mạng!", 4000, color=ft.Colors.RED)
            print("ATTENDANCE ERROR:", e)

    # ==========================================
    # CÁC HÀM XỬ LÝ KHÁC
    # ==========================================
    async def handle_limit_change(self, e):
        self.current_limit = int(self.dd_row_limit.value)
        self.render_table()
        if getattr(self, "page", None): self.update()

    async def handle_load_more(self, e):
        self.current_limit += 10
        self.render_table()
        if getattr(self, "page", None): self.update()

    def render_table(self):
        self.dt_sinhvien.rows.clear()
        display_data = self.all_students_data[:self.current_limit]
        
        if not display_data:
            self.dt_sinhvien.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Không có dữ liệu")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))
        else:
            for sv in display_data:
                ho_ten = f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip()
                trang_thai = ft.Text("Chưa điểm danh", color=ft.Colors.ORANGE_700, weight=ft.FontWeight.W_500)
                
                self.dt_sinhvien.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(sv["id"]))),
                        ft.DataCell(ft.Text(ho_ten, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(sv.get("gioitinh", "N/A"))),
                        ft.DataCell(ft.Text(self.dd_lop.value)),
                        ft.DataCell(trang_thai),
                        ft.DataCell(ft.Text("-")),
                    ])
                )
        
        self.btn_load_more.visible = self.current_limit < len(self.all_students_data)

    async def handle_load_students(self, e):
        lop_id = self.dd_lop.value
        if not lop_id: return

        try:
            e.control.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE, stroke_width=2)
            e.control.disabled = True
            if getattr(self, "page", None): self.update()

            async with await get_supabase_client() as client:
                params = {"select": "*", "class_id": f"eq.{lop_id}", "order": "id.asc"}
                res = await client.get("/sinhvien", params=params)
                res.raise_for_status()
                
                if not getattr(self, "page", None): return 

                self.all_students_data = res.json()
                self.current_limit = int(self.dd_row_limit.value)
                self.render_table()

        except Exception as ex:
            print(f"Lỗi handle_load_students: {ex}")
            if getattr(self, "page", None):
                self._show_error_snackbar(f"Lỗi truy xuất dữ liệu: {ex}")
        finally:
            if getattr(self, "page", None):
                e.control.content = ft.Text("Truy xuất danh sách", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)
                e.control.disabled = False
                self.update()
            
    async def handle_start_session(self, e):
        if not getattr(self, "page", None): return
        
        e.control.disabled = True
        e.control.update()

        mode = self.rg_mode.value if hasattr(self, 'rg_mode') else "1"
        
        prefs = ft.SharedPreferences()
        await prefs.set("attendance_mode", str(mode))

        await self.camera_view.stop_camera()
        await self.app_page.push_route("/user/attendance/session")

    async def handle_test_camera(self, e):
        if not getattr(self, "page", None): return
        
        self.test_progress.visible = True
        self.test_status_text.value = "Đang kết nối cảm biến..."
        self.test_status_text.visible = True
        self.update()

        async def run_test():
            is_ok = await self.camera_view.test_sensor()
            if not getattr(self, "page", None): return

            self.test_progress.visible = False
            self.test_status_text.value = "Sẵn sàng" if is_ok else "Lỗi kết nối"
            self.test_status_text.color = ft.Colors.GREEN if is_ok else ft.Colors.RED
            try:
                self.update()
            except:
                pass

        self.app_page.run_task(run_test)

    def _show_error_snackbar(self, message: str):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.RED_700, open=True))
        self.app_page.update()