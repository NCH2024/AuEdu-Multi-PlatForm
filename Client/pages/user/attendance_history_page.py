import flet as ft
from core.theme import current_theme, get_flat_container
from core.config import get_supabase_client, SERVER_API_URL
from core.helper import safe_json_load
from components.options.custom_dropdown import CustomDropdown
from components.options.top_notification import show_top_notification # Đã import hiệu ứng thông báo
import httpx

class AttendanceHistoryPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = current_theme.bg_color
        self.padding = ft.Padding(15, 10, 15, 10)

        self.view_mode = "LIST" 
        self.history_data = []
        self.tkb_list = []
        self.gv_id = "N/A"
        
        self.is_mobile = self.app_page.width < 600

        self.dd_lop = CustomDropdown(label="Lớp học phần", options=[])
        self.loading = ft.ProgressBar(visible=False, color=current_theme.primary)
        self.main_content_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

        self.render_view()
        self.app_page.run_task(self.init_data)

    def apply_theme(self):
        self.bgcolor = current_theme.bg_color
        self.render_view()
        self.update()

    async def init_data(self):
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            data = safe_json_load(session_str)
            self.gv_id = data.get("id", "N/A")

        client = await get_supabase_client()
        res = await client.get("/thoikhoabieu", params={
            "giangvien_id": f"eq.{self.gv_id}", 
            "select": "id,lop(tenlop),hocphan(tenhocphan)"
        })
        if res.status_code == 200:
            self.tkb_list = res.json()
            if self.tkb_list:
                self.dd_lop.options = [
                    ft.dropdown.Option(key=str(t["id"]), text=f"{t['lop']['tenlop']} - {t['hocphan']['tenhocphan']}") 
                    for t in self.tkb_list
                ]
                self.dd_lop.value = str(self.tkb_list[0]["id"])
                self.dd_lop.on_change = lambda _: self.app_page.run_task(self.load_history_list)
                await self.load_history_list()

    async def load_history_list(self):
        self.view_mode = "LIST"
        self.loading.visible = True
        self.update()

        url = f"{SERVER_API_URL.rstrip('/')}/api/attendance/history/{self.dd_lop.value}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            self.history_data = res.json() if res.status_code == 200 else []
            
        self.render_view()
        self.loading.visible = False
        self.update()

    async def switch_to_detail(self, item):
        self.view_mode = "DETAIL"
        self.selected_item = item
        self.loading.visible = True
        self.update()

        url = f"{SERVER_API_URL.rstrip('/')}/api/attendance/details/{item['tkb_tiet_id']}/{item['date']}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            details = res.json() if res.status_code == 200 else []

        self.render_view(details)
        self.loading.visible = False
        self.update()

    def build_history_grid(self):
        grid = ft.ResponsiveRow(spacing=10, run_spacing=10)
        if not self.history_data:
            return ft.Container(content=ft.Text("Chưa có lịch sử điểm danh."), alignment=ft.Alignment(0,0), padding=50)

        for item in self.history_data:
            card = ft.Column([
                get_flat_container(
                    content=ft.ListTile(
                        leading=ft.Icon(ft.Icons.EVENT_REPEAT, color=current_theme.primary),
                        title=ft.Text(f"Ngày {item['date']}", weight=ft.FontWeight.BOLD, size=14),
                        subtitle=ft.Text(f"Sĩ số: {item['present']} / {item['total']}", size=12),
                        trailing=ft.Icon(ft.Icons.ARROW_FORWARD_IOS, size=12),
                        on_click=lambda e, i=item: self.app_page.run_task(self.switch_to_detail, i)
                    )
                )
            ], col={"sm": 12, "md": 6, "lg": 4}) 
            grid.controls.append(card)
        return grid

    def build_detail_view(self, details):
        back_btn = ft.TextButton(
            " Quay lại danh sách", icon=ft.Icons.ARROW_BACK_IOS_NEW, 
            on_click=lambda _: self.app_page.run_task(self.load_history_list),
            style=ft.ButtonStyle(color=current_theme.text_muted, padding=0)
        )
        
        total = len(details)
        present = sum(1 for sv in details if sv['trang_thai'] == "Có mặt")
        summary_text = ft.Text(f"Sĩ số: {present}/{total} SV", weight=ft.FontWeight.BOLD, color=current_theme.secondary)

        list_view = ft.ResponsiveRow(spacing=15, run_spacing=15)

        for index, sv in enumerate(details, start=1):
            is_absent = sv['trang_thai'] != "Có mặt"
            status_color = ft.Colors.RED_500 if is_absent else ft.Colors.GREEN_600
            bg_color = current_theme.surface_variant if is_absent else current_theme.surface_color

            ho_ten = f"{sv.get('hodem', '')} {sv.get('ten', '')}".strip()
            info_text = f"{sv.get('gioitinh', 'N/A')} | Sinh: {sv.get('ngaysinh', 'N/A')}"

            card = ft.Container(
                col={"xs": 12, "sm": 12, "md": 6, "lg": 6, "xl": 4},
                bgcolor=bg_color, border_radius=12, padding=12,
                border=ft.Border.all(1, ft.Colors.RED_200 if is_absent else current_theme.divider_color),
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(str(index), color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14),
                        width=40, height=40, border_radius=20,
                        bgcolor=status_color, alignment=ft.Alignment.CENTER
                    ),
                    ft.Column([
                        ft.Text(ho_ten, weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"MSSV: {sv['id']}", size=12, color=current_theme.secondary, weight=ft.FontWeight.W_600),
                        ft.Text(info_text, size=11, color=current_theme.text_muted),
                        ft.Row([
                            ft.Icon(ft.Icons.ACCESS_TIME, size=12, color=current_theme.text_muted),
                            ft.Text(f"Giờ: {sv['time']}", size=11, color=current_theme.text_muted)
                        ], spacing=4),
                        ft.Row([
                            ft.Icon(ft.Icons.LOCATION_ON, size=12, color=current_theme.text_muted),
                            ft.Text(sv['vitri'], size=11, color=current_theme.text_muted, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                        ], spacing=4)
                    ], expand=True, spacing=3),
                    ft.Column([
                        ft.Container(
                            padding=ft.Padding(8, 4, 8, 4), border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.1, status_color),
                            content=ft.Text(sv['trang_thai'], color=status_color, size=11, weight=ft.FontWeight.BOLD)
                        ),
                        ft.Switch(
                            value=not is_absent,
                            active_color=ft.Colors.GREEN_500,
                            scale=0.7, tooltip="Chỉnh sửa thủ công",
                            # Kèm tên sinh viên vào hàm để hiện thông báo rõ ràng
                            on_change=lambda e, sid=sv['id'], name=ho_ten: self.app_page.run_task(self.update_status, sid, e.control.value, name)
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.END, alignment=ft.MainAxisAlignment.CENTER)
                ])
            )
            list_view.controls.append(card)

        return ft.Column([
            ft.Row([back_btn, summary_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            list_view
        ], spacing=15)

    # --- HÀM XỬ LÝ CẬP NHẬT KÈM HIỆU ỨNG THÔNG BÁO ---
    async def update_status(self, sv_id, is_present, ho_ten):
        status = "Có mặt" if is_present else "Vắng"
        url = f"{SERVER_API_URL.rstrip('/')}/api/attendance/update-manual"
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.patch(url, json={
                    "sv_id": sv_id, 
                    "tkb_tiet_id": self.selected_item['tkb_tiet_id'], 
                    "date": self.selected_item['date'], 
                    "new_status": status
                })
                
                # NẾU CÓ LỖI, BẮT LẤY CÂU CHỮ TỪ SERVER
                if res.status_code != 200:
                    error_detail = res.json().get("detail", "Lỗi không xác định")
                    raise Exception(error_detail)
            
            show_top_notification(
                self.app_page, 
                title="Cập nhật thành công", 
                message=f"{ho_ten}: {status}", 
                color=ft.Colors.GREEN_600, 
                sound="S"
            )
            await self.switch_to_detail(self.selected_item)

        except Exception as e:
            print(f"Lỗi cập nhật: {e}")
            show_top_notification(
                self.app_page, 
                title="Lỗi máy chủ", 
                message=f"Chi tiết: {str(e)[:60]}...", # Hiển thị nguyên nhân thực sự lên màn hình
                color=ft.Colors.RED_500, 
                sound="E"
            )
            await self.switch_to_detail(self.selected_item)

    def render_view(self, details=None):
        self.is_mobile = self.app_page.width < 600
        
        back_btn = ft.TextButton(
            "Quay về", icon=ft.Icons.CHEVRON_LEFT, 
            on_click=lambda _: self.app_page.run_task(self.app_page.push_route, "/user/attendance"),
            style=ft.ButtonStyle(color=current_theme.text_main, padding=0)
        )
        refresh_btn = ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self.app_page.run_task(self.load_history_list))

        if self.is_mobile:
            header = ft.Column([
                ft.Row([back_btn, refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(self.dd_lop, visible=(self.view_mode == "LIST"), padding=ft.Padding(0, 0, 0, 5))
            ], spacing=5)
        else:
            header = ft.Row([
                back_btn,
                ft.Row([
                    ft.Container(self.dd_lop, width=300, visible=(self.view_mode == "LIST")),
                    refresh_btn
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.main_content_area.controls.clear()
        if self.view_mode == "LIST":
            self.main_content_area.controls.append(self.build_history_grid())
        else:
            self.main_content_area.controls.append(self.build_detail_view(details or []))

        self.content = ft.Column([header, self.loading, ft.Divider(height=1), self.main_content_area], expand=True, spacing=10)