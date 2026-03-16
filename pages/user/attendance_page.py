import flet as ft
import datetime
import asyncio
from components.pages.base_dashboard import BaseDashboard
from components.pages.page_frame import PageFrame
from components.options.custom_dropdown import CustomDropdown
from components.options.loading_data import LoadingOverlay
from components.options.camera_view import CameraView
from core.theme import get_glass_container, PRIMARY_COLOR
from core.config import *

class AttendancePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        session_data = self.app_page.session.store.get("user_session") or {}
        self.gv_id = session_data.get("id", "N/A")

        self.tkb_data = [] 
        self.all_students_data = []
        self.current_limit = 5

        # Khởi tạo các thành phần giao diện dữ liệu
        self.dd_row_limit = CustomDropdown(
            label="Hiển thị", 
            options=[
                ft.dropdown.Option("5"), 
                ft.dropdown.Option("10"), 
                ft.dropdown.Option("20"), 
                ft.dropdown.Option("50"), 
                ft.dropdown.Option("100")
            ], 
            value="5", 
            on_change=self.handle_limit_change
        )
        self.btn_load_more = ft.TextButton(
            content=ft.Text("Xem thêm 10 dòng 🔽", color=PRIMARY_COLOR, weight=ft.FontWeight.BOLD), 
            visible=False, 
            on_click=self.handle_load_more
        )

        self.dd_lop = CustomDropdown(label="Lớp", options=[], col={"sm": 6, "md": 3}, on_change=self.handle_lop_change)
        self.dd_hocphan = CustomDropdown(label="Học phần", options=[], col={"sm": 6, "md": 3})
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        self.dd_ngay = CustomDropdown(label="Ngày", options=[ft.dropdown.Option(today_str)], value=today_str, col={"sm": 6, "md": 3})
        self.dd_buoi = CustomDropdown(label="Buổi", options=[ft.dropdown.Option("Sáng"), ft.dropdown.Option("Chiều"), ft.dropdown.Option("Tối")], col={"sm": 6, "md": 3})
        
        # Khởi tạo thành phần điều khiển thiết bị
        self.dd_camera = CustomDropdown(label="Chọn Camera", options=[])
        self.camera_view = CameraView(page=self.app_page, dd_camera=self.dd_camera)
        
        # Trạng thái tiến trình kiểm tra thiết bị
        self.test_progress = ft.ProgressBar(visible=False, color=ft.Colors.BLUE_600, height=2)
        self.test_status_text = ft.Text("", size=11, color=ft.Colors.GREY_700, italic=True, visible=False)

        self.dt_sinhvien = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Mã SV", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Họ Tên", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Giới tính", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Lớp", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Trạng thái", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Thời gian", weight=ft.FontWeight.BOLD)),
            ], 
            rows=[], 
            heading_row_color=ft.Colors.BLACK_12, 
            border_radius=8, 
            data_row_max_height=40,
        )

        self.loading_overlay = LoadingOverlay(message="Đang tải dữ liệu điểm danh...")

        main_ui = self.build_ui()
        self.content = ft.Stack(controls=[main_ui, self.loading_overlay], expand=True)

        self.app_page.run_task(self.initialize_page)

    async def initialize_page(self):
        """Khởi tạo dữ liệu và thiết bị khi tải trang."""
        await asyncio.sleep(0.4)
        
        try:
            await self.load_dropdowns()
        except Exception as e:
            self._show_error_snackbar(f"Lỗi tải dữ liệu lớp: {e}")

        try:
            await self.camera_view.load_available_cameras()
        except Exception as e:
            self._show_error_snackbar(f"Lỗi khởi tạo thiết bị: {e}")
        
        self.loading_overlay.visible = False
        if getattr(self, "app_page", None):
            self.update()          # chỉ update nếu đã được gắn vào page

    def build_ui(self):
        """Xây dựng bố cục giao diện."""
        
        nang_cao_content = ft.Column([
            ft.Button(content=ft.Text("Lịch sử điểm danh", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_GREY_600),
            ft.Button(content=ft.Text("Tra cứu sinh viên", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_GREY_600)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        nang_cao_tile = ft.ExpansionTile(title=ft.Text("Chức năng nâng cao", weight=ft.FontWeight.BOLD, size=13), controls=[nang_cao_content], collapsed_text_color=PRIMARY_COLOR, text_color=PRIMARY_COLOR)

        # Gán biến self.rg_mode để lấy giá trị sau này (mặc định chọn value="1")
        self.rg_mode = ft.RadioGroup(
            value="1", 
            content=ft.Column([ft.Radio(value="1", label="Từng sinh viên"), ft.Radio(value="all", label="Cả lớp")])
        )
        
        diem_danh_content = ft.Column([
            self.rg_mode, 
            ft.Button(
                content=ft.Text("Điểm danh ngay", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
                bgcolor=ft.Colors.BLUE_600,
                on_click=self.handle_start_session # Gán sự kiện click
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        
        # Thay thế initially_expanded bằng expanded theo API mới của Flet
        diem_danh_tile = ft.ExpansionTile(title=ft.Text("Thao tác điểm danh", weight=ft.FontWeight.BOLD, size=13), controls=[diem_danh_content], expanded=True, collapsed_text_color=PRIMARY_COLOR, text_color=PRIMARY_COLOR)

        sinh_trac_content = ft.Column([
            ft.Button(content=ft.Text("Đào tạo khuôn mặt", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_700),
            ft.Button(content=ft.Text("Dữ liệu khuôn mặt", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_700)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        sinh_trac_tile = ft.ExpansionTile(title=ft.Text("Sinh trắc học", weight=ft.FontWeight.BOLD, size=13), controls=[sinh_trac_content], collapsed_text_color=PRIMARY_COLOR, text_color=PRIMARY_COLOR)

        thiet_bi_content = ft.Column([
            self.dd_camera,
            self.camera_view,
            ft.Row([
                ft.Button(content=ft.Text("Lưu", color=ft.Colors.WHITE), bgcolor=ft.Colors.BLUE_500, expand=True), 
                ft.Button(content=ft.Text("Kiểm tra", color=ft.Colors.WHITE), bgcolor=ft.Colors.TEAL_600, expand=True, on_click=self.handle_test_camera)
            ]),
            self.test_progress,
            self.test_status_text,
            ft.Text("Yêu cầu lưu cấu hình trước khi kiểm tra thiết bị.", size=10, color=ft.Colors.GREY_600)
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        
        # Thay thế initially_expanded bằng expanded
        thiet_bi_tile = ft.ExpansionTile(title=ft.Text("Thiết lập Camera", weight=ft.FontWeight.BOLD, size=13), controls=[thiet_bi_content], expanded=True, collapsed_text_color=PRIMARY_COLOR, text_color=PRIMARY_COLOR)
        
        side_column = get_glass_container(content=ft.Column([diem_danh_tile, thiet_bi_tile, sinh_trac_tile, nang_cao_tile], spacing=0))

        table_header = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("DANH SÁCH LỚP", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=14), ft.Container(content=self.dd_row_limit, width=90)])
        combined_attendance_card = get_glass_container(
            content=ft.Column([
                ft.Text("BỘ LỌC THÔNG TIN", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=12),
                ft.ResponsiveRow([self.dd_lop, self.dd_hocphan, self.dd_ngay, self.dd_buoi]),
                ft.Row([ft.Button(content=ft.Text("Truy xuất danh sách", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600), bgcolor=ft.Colors.BLUE_500, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)), on_click=self.handle_load_students)], alignment=ft.MainAxisAlignment.CENTER),
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

    async def load_dropdowns(self):
        """Tải dữ liệu phân công giảng dạy bằng httpx."""
        if self.gv_id == "N/A": return
        
        try:
            async with await get_supabase_client() as client:
                # 1. Truy vấn Thời khóa biểu (Join với lớp và học phần)
                params_tkb = {
                    "select": "id,lop_id,hocphan_id,lop(tenlop),hocphan(tenhocphan)",
                    "giangvien_id": f"eq.{self.gv_id}"
                }
                res_tkb = await client.get("/thoikhoabieu", params=params_tkb)
                res_tkb.raise_for_status()
                self.tkb_data = res_tkb.json()

                if not self.tkb_data: return

                # 2. Truy vấn Tiết học để xác định lớp mặc định của ngày hôm nay
                today = datetime.datetime.now()
                thu_today = today.weekday() + 2 
                tkb_ids = [str(item['id']) for item in self.tkb_data]
                
                # Filter IN trong PostgREST: column=in.(val1,val2,...)
                params_tiet = {
                    "select": "tkb_id,thu",
                    "tkb_id": f"in.({','.join(tkb_ids)})"
                }
                res_tiet = await client.get("/tkb_tiet", params=params_tiet)
                res_tiet.raise_for_status()
                tiet_data = res_tiet.json()

                default_lop_id = None
                default_hp_id = None

                if tiet_data:
                    for t in tiet_data:
                        if t["thu"] == thu_today:
                            for tkb in self.tkb_data:
                                if tkb["id"] == t["tkb_id"]:
                                    default_lop_id = tkb["lop_id"]
                                    default_hp_id = tkb["hocphan_id"]
                                    break
                            if default_lop_id: break

                # 3. Cập nhật giao diện Dropdown
                lops = {row["lop_id"]: row["lop"]["tenlop"] for row in self.tkb_data}
                self.dd_lop.options = [ft.dropdown.Option(key=k, text=v) for k, v in lops.items()]

                if default_lop_id and default_lop_id in lops:
                    self.dd_lop.value = default_lop_id
                else:
                    self.dd_lop.value = list(lops.keys())[0]

                await self.handle_lop_change(None, auto_hp_id=default_hp_id)

        except Exception as e:
            print(f"Lỗi load_dropdowns (HTTPX): {e}")
            if getattr(self, "page", None):
                self._show_error_snackbar(f"Lỗi tải dữ liệu lớp: {e}")

    async def handle_lop_change(self, e, auto_hp_id=None):
        """Cập nhật dropdown học phần khi thay đổi lớp."""
        lop_id = self.dd_lop.value
        hps = {row["hocphan_id"]: row["hocphan"]["tenhocphan"] for row in self.tkb_data if row["lop_id"] == lop_id}
        self.dd_hocphan.options = [ft.dropdown.Option(key=str(k), text=v) for k, v in hps.items()]

        if auto_hp_id and str(auto_hp_id) in [str(k) for k in hps.keys()]:
            self.dd_hocphan.value = str(auto_hp_id)
        elif hps:
            self.dd_hocphan.value = str(list(hps.keys())[0])
        else:
            self.dd_hocphan.value = None
        self.update()

    async def handle_limit_change(self, e):
        """Thay đổi giới hạn số lượng sinh viên hiển thị."""
        self.current_limit = int(self.dd_row_limit.value)
        self.render_table()
        self.update()

    async def handle_load_more(self, e):
        """Mở rộng danh sách sinh viên hiển thị."""
        self.current_limit += 10
        self.render_table()
        self.update()

    def render_table(self):
        """Hiển thị dữ liệu lên bảng."""
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
        """Truy xuất danh sách sinh viên bằng httpx."""
        lop_id = self.dd_lop.value
        if not lop_id: return

        try:
            # Hiện loading trên nút
            e.control.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE, stroke_width=2)
            e.control.disabled = True
            if getattr(self, "page", None): self.update()

            async with await get_supabase_client() as client:
                # Query: .select("*").eq("class_id", lop_id).order("id")
                params = {
                    "select": "*",
                    "class_id": f"eq.{lop_id}",
                    "order": "id.asc"
                }
                res = await client.get("/sinhvien", params=params)
                res.raise_for_status()
                
                if not self.page: return # Chống lỗi bóng ma

                self.all_students_data = res.json()
                self.current_limit = int(self.dd_row_limit.value)
                self.render_table()

        except Exception as ex:
            print(f"Lỗi handle_load_students (HTTPX): {ex}")
            if getattr(self, "page", None):
                self._show_error_snackbar(f"Lỗi truy xuất dữ liệu: {ex}")
        finally:
            if getattr(self, "page", None):
                e.control.content = ft.Text("Truy xuất danh sách", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)
                e.control.disabled = False
                self.update()
            
    async def handle_start_session(self, e):
        """Chuyển trang ngay lập tức và CẮT ĐỨT mọi tác vụ cũ."""
        if not self.page: return
        
        e.control.disabled = True
        e.control.update()

        # Lưu mode
        mode = self.rg_mode.value if hasattr(self, 'rg_mode') else "1"
        self.app_page.session.store.set("attendance_mode", mode)

        # CỰC KỲ QUAN TRỌNG: Dọn dẹp camera trước khi chuyển trang để nhả ID
        await self.camera_view.stop_camera()
        
        # Chuyển trang
        await self.app_page.push_route("/user/attendance/session")

    async def handle_test_camera(self, e):
        """Vẫn giữ nguyên logic cũ vì nó không liên quan đến Supabase."""
        if not self.page: return
        
        self.test_progress.visible = True
        self.test_status_text.value = "Đang kết nối cảm biến..."
        self.test_status_text.visible = True
        self.update()

        async def run_test():
            is_ok = await self.camera_view.test_sensor()
            if not self.page: return

            self.test_progress.visible = False
            self.test_status_text.value = "Sẵn sàng" if is_ok else "Lỗi kết nối"
            self.test_status_text.color = ft.Colors.GREEN if is_ok else ft.Colors.RED
            try:
                self.update()
            except:
                pass

        self.app_page.run_task(run_test)

    def _show_error_snackbar(self, message: str):
        """Hỗ trợ hiển thị thông báo lỗi."""
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.RED_700, open=True))
        self.app_page.update()