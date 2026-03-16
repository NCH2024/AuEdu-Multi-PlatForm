import flet as ft
from components.pages.base_dashboard import BaseDashboard
from components.pages.page_frame import PageFrame
from core.theme import get_glass_container, PRIMARY_COLOR
from core.config import get_supabase_client

class UserHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        session_data = self.app_page.session.store.get("user_session") or {}
        self.gv_name = session_data.get("name", "Giảng viên")
        self.gv_id = session_data.get("id", "N/A")

        self.dt_phancong = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("LỚP", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("HỌC PHẦN", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("SỐ BUỔI", weight=ft.FontWeight.BOLD)),
            ],
            rows=[], 
            heading_row_color=ft.Colors.BLACK_12,
            border_radius=8
        )
        
        self.col_thongbao = ft.Column(scroll=ft.ScrollMode.AUTO, height=450, spacing=10)

        self.content = self.build_ui()
        self.app_page.run_task(self.load_data)

    def build_ui(self):
        info_card = get_glass_container(
            content=ft.Column([
                ft.Text("THÔNG TIN GIẢNG VIÊN", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                ft.Divider(color=ft.Colors.BLACK_12),
                ft.Text(f"Giảng Viên: {self.gv_name}", size=16, weight=ft.FontWeight.W_500),
                ft.Text(f"Mã cán bộ: {self.gv_id}", size=16),
                ft.Text("Khoa: Công nghệ thông tin", size=16),
                ft.Text("Thông tin khác: Giảng viên được thiết lập mẫu trong quá trình xây dựng phần mềm.", 
                        size=14, italic=True, color=ft.Colors.GREY_700),
            ])
        )

        schedule_card = get_glass_container(
            content=ft.Column([
                ft.Text("PHÂN CÔNG ĐIỂM DANH CÁC LỚP", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                ft.Text("Xem nhanh lịch mà bạn được phân công:", size=13, color=ft.Colors.GREY_700),
                ft.Divider(color=ft.Colors.BLACK_12),
                self.dt_phancong 
            ])
        )

        left_column = ft.Column([info_card, schedule_card], spacing=20)

        news_card = get_glass_container(
            content=ft.Column([
                ft.Text("THÔNG BÁO", weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                ft.Text("Cán bộ giảng viên hãy lưu ý thông báo mới nhất!", size=13, color=ft.Colors.GREY_700),
                ft.Divider(color=ft.Colors.BLACK_12),
                self.col_thongbao 
            ])
        )

        dashboard_content = ft.ResponsiveRow([
            ft.Column([left_column], col={"sm": 12, "md": 6}),
            ft.Column([news_card], col={"sm": 12, "md": 6}),
        ], expand=True)

        framed_layout = PageFrame(page=self.app_page, page_title="TRANG CHỦ", main_content=dashboard_content)
        return BaseDashboard(page=self.app_page, active_route="/user/home", main_content=framed_layout)

    async def load_data(self):
        try:
            # Sử dụng httpx client từ config của em
            async with await get_supabase_client() as client:
                # 1. Lấy dữ liệu Thông báo (REST API: select, order, limit)
                # Tương đương: .select("*").order("created_at", desc=True).limit(5)
                params_tb = {
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": "5"
                }
                res_tb = await client.get("/thongbao", params=params_tb)
                res_tb.raise_for_status() # Kiểm tra lỗi HTTP
                thongbao_data = res_tb.json()

                self.col_thongbao.controls.clear()
                if thongbao_data:
                    for item in thongbao_data:
                        raw_date = item.get("created_at", "N/A")[:10] 
                        title = item.get("tieu_de", "Không có tiêu đề")
                        
                        news_item = ft.Container(
                            bgcolor=ft.Colors.WHITE_70, padding=ft.Padding(15, 15, 15, 15), border_radius=8,
                            content=ft.Column([
                                ft.Text(title, weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLACK_87),
                                ft.Text(f"Ngày đăng: {raw_date}", size=12, color=ft.Colors.GREY_600),
                                ft.Button(content=ft.Text("Xem chi tiết", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_600, height=30)
                            ], spacing=5)
                        )
                        self.col_thongbao.controls.append(news_item)
                else:
                    self.col_thongbao.controls.append(ft.Text("Chưa có thông báo nào.", italic=True, color=ft.Colors.GREY_500))

                # 2. Lấy dữ liệu Phân công giảng dạy (Join bảng lop và hocphan)
                # Tương đương: .select("lop(tenlop), hocphan(tenhocphan, sobuoi)").eq("giangvien_id", self.gv_id)
                if self.gv_id != "N/A":
                    params_tkb = {
                        "select": "lop(tenlop),hocphan(tenhocphan,sobuoi)",
                        "giangvien_id": f"eq.{self.gv_id}"
                    }
                    res_tkb = await client.get("/thoikhoabieu", params=params_tkb)
                    res_tkb.raise_for_status()
                    tkb_data = res_tkb.json()
                    
                    self.dt_phancong.rows.clear()
                    if tkb_data:
                        for row in tkb_data:
                            ten_lop = row.get("lop", {}).get("tenlop", "N/A") if row.get("lop") else "N/A"
                            ten_hp = row.get("hocphan", {}).get("tenhocphan", "N/A") if row.get("hocphan") else "N/A"
                            so_buoi = str(row.get("hocphan", {}).get("sobuoi", 0)) if row.get("hocphan") else "0"
                            
                            self.dt_phancong.rows.append(
                                ft.DataRow(cells=[
                                    ft.DataCell(ft.Text(ten_lop)),
                                    ft.DataCell(ft.Text(ten_hp)),
                                    ft.DataCell(ft.Text(so_buoi)),
                                ])
                            )
                    else:
                        self.dt_phancong.rows.append(
                            ft.DataRow(cells=[ft.DataCell(ft.Text("Chưa có lịch")), ft.DataCell(ft.Text("-")), ft.DataCell(ft.Text("-"))])
                        )

            # Cập nhật giao diện sau khi tải xong toàn bộ
            self.update()

        except Exception as e:
            print(f"Lỗi tải dữ liệu Trang chủ (HTTPX): {e}")
            