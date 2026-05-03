import flet as ft
import asyncio
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.config import get_supabase_client
from components.admin.data_grid import AdminDataGrid
from datetime import datetime, timedelta

class SystemHistoryPage(ft.Container):
    """Trang xem lịch sử hệ thống toàn diện dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        
        self._is_active = True
        self.metadata = {"actions": [], "entities": []}

        # -- UI Elements --
        self.title_text = ft.Text("LỊCH SỬ HOẠT ĐỘNG HỆ THỐNG", size=20, weight=ft.FontWeight.BOLD)
        
        # Thống kê nhanh / Badge Live
        self.live_badge = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=15,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.GREEN),
            content=ft.Row([
                ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.GREEN),
                ft.Text("ĐANG THEO DÕI TRỰC TIẾP", size=11, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD)
            ], spacing=8, tight=True)
        )

        # Bộ lọc
        self.action_filter = ft.Dropdown(
            label="Hành động", width=160, height=38,
            options=[ft.dropdown.Option("all", "Tất cả hành động")], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.action_filter.on_change = self.handle_filter_change

        self.entity_filter = ft.Dropdown(
            label="Đối tượng", width=160, height=38,
            options=[ft.dropdown.Option("all", "Tất cả đối tượng")], value="all",
            border_radius=8, text_size=12, content_padding=ft.Padding(10, 0, 10, 0)
        )
        self.entity_filter.on_change = self.handle_filter_change

        self.search_field = ft.TextField(
            hint_text="Tìm kiếm chi tiết/IP...", width=220, height=38,
            prefix_icon=ft.Icons.SEARCH, border_radius=8, text_size=12,
            content_padding=ft.Padding(10, 0, 10, 0), on_submit=self.handle_filter_change
        )

        # Lọc ngày (Hiện tại Flet chưa có DateRangePicker xịn, dùng 2 TextField tạm)
        self.date_from = ft.TextField(
            label="Từ ngày", hint_text="YYYY-MM-DD", width=130, height=38,
            border_radius=8, text_size=11, content_padding=ft.Padding(10, 0, 10, 0),
            on_submit=self.handle_filter_change
        )
        self.date_to = ft.TextField(
            label="Đến ngày", hint_text="YYYY-MM-DD", width=130, height=38,
            border_radius=8, text_size=11, content_padding=ft.Padding(10, 0, 10, 0),
            on_submit=self.handle_filter_change
        )
        
        self.exclude_admin_switch = ft.Switch(
            label="Loại trừ Admin", value=False, 
            label_position=ft.LabelPosition.RIGHT,
            scale=0.8
        )
        self.exclude_admin_switch.on_change = self.handle_filter_change

        self.grid = AdminDataGrid(
            columns=[
                {"label": "THỜI GIAN", "key": "time", "col": {"xs": 4, "sm": 1.5}},
                {"label": "NGƯỜI DÙNG", "key": "user", "col": {"xs": 4, "sm": 1.8}, "sortable": True},
                {"label": "HÀNH ĐỘNG", "key": "action", "col": {"xs": 4, "sm": 1.2}, "render": self.render_action},
                {"label": "ĐỐI TƯỢNG", "key": "entity", "col": {"xs": 4, "sm": 1.5}, "render": self.render_entity},
                {"label": "CHI TIẾT", "key": "details", "col": {"xs": 8, "sm": 4.5}},
                {"label": "ĐỊA CHỈ IP", "key": "ip_address", "col": {"xs": 4, "sm": 1.5}},
            ],
            rows_per_page=40
        )

        self.content = ft.Column([
            ft.Row([
                ft.Column([self.title_text, self.live_badge], spacing=5),
                ft.Row([
                    ft.IconButton(ft.Icons.REFRESH_ROUNDED, tooltip="Làm mới", on_click=self.refresh_data),
                    ft.IconButton(ft.Icons.DELETE_SWEEP_OUTLINED, icon_color=ft.Colors.RED_400, tooltip="Xóa bộ lọc", on_click=self.clear_filters),
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=15),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        self.search_field,
                        self.action_filter,
                        self.entity_filter,
                        self.date_from,
                        self.date_to,
                        self.exclude_admin_switch,
                        ft.FilledButton(
                            "Lọc dữ liệu", 
                            icon=ft.Icons.FILTER_LIST_ROUNDED,
                            on_click=self.handle_filter_change,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                        )
                    ], spacing=10, wrap=True),
                    ft.Divider(height=1, color=current_theme.divider_color),
                    self.grid
                ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, expand=True),
                padding=20, border=ft.Border.all(1, current_theme.divider_color),
                border_radius=12, bgcolor=current_theme.surface_color, expand=True
            )
        ], expand=True)

    def render_action(self, item):
        action = item.get("action", "N/A")
        colors = {
            "LOGIN": ft.Colors.BLUE,
            "LOGOUT": ft.Colors.BLUE_GREY,
            "CREATE": ft.Colors.GREEN,
            "UPDATE": ft.Colors.ORANGE,
            "DELETE": ft.Colors.RED,
            "ACCESS": ft.Colors.CYAN,
            "SESSION_START": ft.Colors.PURPLE,
            "SESSION_END": ft.Colors.PURPLE_300,
        }
        color = colors.get(action, ft.Colors.GREY)
        return ft.Container(
            padding=ft.Padding(8, 4, 8, 4), border_radius=6,
            bgcolor=ft.Colors.with_opacity(0.1, color),
            content=ft.Text(action, size=10, weight=ft.FontWeight.BOLD, color=color)
        )

    def render_entity(self, item):
        entity = item.get("entity") or "System"
        return ft.Text(entity, size=12, color=current_theme.secondary, weight=ft.FontWeight.W_500)

    def did_mount(self):
        self._is_active = True
        self.app_page.run_task(self.initialize_page)
        self.app_page.run_task(self.refresh_loop)

    def did_unmount(self):
        self._is_active = False
        super().did_unmount()

    async def refresh_loop(self):
        while self._is_active:
            await asyncio.sleep(5)
            if not self._is_active: break
            # Nếu người dùng đang gõ hoặc đã chọn lọc thì không tự làm mới để tránh nhảy dữ liệu (hoặc chỉ làm mới nếu ở trang 1)
            if self.grid.current_page == 1 and not self.search_field.value and self.action_filter.value == "all" and self.entity_filter.value == "all":
                await self.load_data(silent=True)

    async def initialize_page(self):
        await self.load_metadata()
        await self.load_data()

    async def load_metadata(self):
        try:
            client = await get_supabase_client()
            res = await client.get("/api/admin/system/audit/metadata")
            if res.status_code == 200:
                data = res.json()
                self.metadata = data
                
                self.action_filter.options = [ft.dropdown.Option("all", "Tất cả hành động")]
                for a in data.get("actions", []):
                    self.action_filter.options.append(ft.dropdown.Option(a, a))
                
                self.entity_filter.options = [ft.dropdown.Option("all", "Tất cả đối tượng")]
                for e in data.get("entities", []):
                    self.entity_filter.options.append(ft.dropdown.Option(e, e))
                
                self.update()
        except Exception as e:
            print(f"Metadata error: {e}")

    async def load_data(self, silent=False):
        try:
            client = await get_supabase_client()
            params = {"limit": 100} # Lấy 100 bản ghi mới nhất khi xem lịch sử
            
            if self.action_filter.value != "all":
                params["action"] = self.action_filter.value
            if self.entity_filter.value != "all":
                params["entity"] = self.entity_filter.value
            if self.date_from.value:
                params["date_from"] = self.date_from.value
            if self.date_to.value:
                params["date_to"] = self.date_to.value
            if self.exclude_admin_switch.value:
                params["exclude_admins"] = "true"
            
            res = await client.get("/api/admin/system/audit", params=params)
            if res.status_code == 200:
                data = res.json()
                # Local search filter if search field has value
                if self.search_field.value:
                    search = self.search_field.value.lower()
                    data = [
                        d for d in data 
                        if search in str(d.get("details", "")).lower() or 
                           search in str(d.get("ip_address", "")).lower() or
                           search in str(d.get("user", "")).lower()
                    ]
                
                self.grid.set_data(data)
                if not silent:
                    self.update()
        except Exception as e:
            if not silent:
                show_top_notification(self.app_page, "Lỗi", f"Không thể tải dữ liệu: {e}", ft.Colors.RED)

    async def handle_filter_change(self, e):
        await self.load_data()

    async def refresh_data(self, e):
        await self.initialize_page()

    async def clear_filters(self, e):
        self.action_filter.value = "all"
        self.entity_filter.value = "all"
        self.search_field.value = ""
        self.date_from.value = ""
        self.date_to.value = ""
        self.exclude_admin_switch.value = False
        await self.load_data()
