import flet as ft
import asyncio
import math
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog
from core.config import get_supabase_client
from components.admin.data_grid import AdminDataGrid

class NotificationsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(15)
        self.alignment = ft.Alignment(-1, -1)

        self.all_data = []
        self.filtered_data = []
        self.current_page = 1
        self.page_size = 10
        self.is_edit = False
        
        self.sort_column_index = None
        self.sort_ascending = True

        # -- UI Elements --
        self.title_text = ft.Text("QUẢN LÝ THÔNG BÁO", size=20, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.btn_add = ft.Button("TẠO THÔNG BÁO", icon=ft.Icons.NOTIFICATION_ADD_ROUNDED, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.open_add_dialog, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.Padding.all(10)))
        
        self.search_field = ft.TextField(hint_text="Tìm tiêu đề thông báo...", prefix_icon=ft.Icons.SEARCH, height=38, expand=True, border_radius=8, text_size=13)
        self.search_field.on_change = self.filter_data
        
        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50")],
            value="10", width=70, height=38, border_radius=8, content_padding=ft.Padding.only(left=10, right=10, bottom=10), text_size=13
        )
        self.page_size_dropdown.on_change = self.change_page_size

        # AdminDataGrid
        self.grid = AdminDataGrid(
            columns=[
                {"label": "ID", "key": "id", "col": {"xs": 2, "sm": 1}, "sortable": True},
                {"label": "TIÊU ĐỀ", "key": "tieu_de", "col": {"xs": 10, "sm": 4}, "sortable": True},
                {"label": "NỘI DUNG", "key": "noi_dung", "col": {"xs": 12, "sm": 5}},
                {"label": "LINK", "key": "link_web", "col": {"xs": 6, "sm": 1}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 1}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
            rows_per_page=10
        )

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field], alignment=ft.MainAxisAlignment.START, spacing=8),
                ft.Container(height=5),
                self.grid
            ], horizontal_alignment=ft.CrossAxisAlignment.START, expand=True, spacing=10),
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=12,
            bgcolor=current_theme.surface_color,
            padding=12,
            expand=True
        )

        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)

        self.content = ft.Column([
            ft.Row([self.title_text, self.btn_add], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.progress_bar,
            ft.Container(height=5),
            self.table_container
        ], expand=True, spacing=0)

        # -- Form Dialog --
        self.form_id = ft.TextField(label="ID (Auto)", disabled=True, border_radius=8, text_size=13, height=45)
        self.form_tieu_de = ft.TextField(label="Tiêu đề thông báo", border_radius=8, text_size=13, height=45)
        self.form_noi_dung = ft.TextField(label="Nội dung thông báo", border_radius=8, text_size=13, multiline=True, min_lines=3)
        self.form_link = ft.TextField(label="Link đính kèm (Web)", border_radius=8, text_size=13, height=45)
        self.form_hinh_anh = ft.TextField(label="URL Hình ảnh", border_radius=8, text_size=13, height=45)
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN THÔNG BÁO", weight=ft.FontWeight.BOLD, size=18),
            content=ft.Container(width=500, content=ft.Column([self.form_id, self.form_tieu_de, self.form_noi_dung, self.form_link, self.form_hinh_anh], tight=True, spacing=12, scroll=ft.ScrollMode.AUTO)),
            actions=[ft.TextButton("HỦY", on_click=self.close_dialog), ft.Button("GỬI / LƯU", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)],
            shape=ft.RoundedRectangleBorder(radius=12)
        )

    def did_mount(self): self.app_page.run_task(self.load_data)
    
    async def load_data(self):
        self.progress_bar.visible = True
        self.update()
        try:
            client = await get_supabase_client()
            res = await client.get("/api/admin/notifications/")
            if res.status_code == 200: self.all_data = res.json(); self.filter_data(None)
            else: show_top_notification(self.app_page, "Lỗi", f"{res.text}", ft.Colors.RED, sound="E")
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải dữ liệu thông báo: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    def filter_data(self, e):
        q = self.search_field.value.lower() if self.search_field.value else ""
        self.filtered_data = [i for i in self.all_data if q in str(i.get("tieu_de", "")).lower()]
        self.current_page = 1; self.render_table()

    def render_actions(self, i):
        return ft.Row([
            ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_size=16, on_click=lambda e, d=i: self.open_edit_dialog(d)),
            ft.IconButton(ft.Icons.DELETE_ROUNDED, icon_size=16, on_click=lambda e, d=i: self.delete_data(d))
        ], spacing=0, alignment=ft.MainAxisAlignment.END)

    def render_table(self):
        self.grid.set_data(self.filtered_data)
        self.update()

    def change_page_size(self, e):
        self.grid.update_page_size(int(self.page_size_dropdown.value))

    def _clear_errors(self):
        self.form_tieu_de.error_text = None
        self.form_noi_dung.error_text = None

    def open_add_dialog(self, e):
        self.is_edit = False; self.form_id.value = "Tự động"
        self.form_tieu_de.value = ""; self.form_noi_dung.value = ""; self.form_link.value = ""; self.form_hinh_anh.value = ""
        self._clear_errors()
        if self.dialog not in self.app_page.overlay: self.app_page.overlay.append(self.dialog)
        self.dialog.open = True; self.app_page.update()

    def open_edit_dialog(self, d):
        self.is_edit = True; self.form_id.value = str(d["id"]); self.form_tieu_de.value = d["tieu_de"]
        self.form_noi_dung.value = d.get("noi_dung", ""); self.form_link.value = d.get("link_web", ""); self.form_hinh_anh.value = d.get("hinh_anh", "")
        self._clear_errors()
        if self.dialog not in self.app_page.overlay: self.app_page.overlay.append(self.dialog)
        self.dialog.open = True; self.app_page.update()

    def close_dialog(self, e=None): self.dialog.open = False; self.app_page.update()
    
    def save_data(self, e):
        has_error = False
        if not self.form_tieu_de.value or not self.form_tieu_de.value.strip():
            self.form_tieu_de.error_text = "Vui lòng nhập tiêu đề"; has_error = True
        else: self.form_tieu_de.error_text = None
        
        if not self.form_noi_dung.value or not self.form_noi_dung.value.strip():
            self.form_noi_dung.error_text = "Vui lòng nhập nội dung"; has_error = True
        else: self.form_noi_dung.error_text = None
        
        if has_error: self.app_page.update(); return
            
        self.app_page.run_task(self._save_data_async)
        
    async def _save_data_async(self):
        try:
            client = await get_supabase_client()
            payload = {
                "tieu_de": self.form_tieu_de.value, 
                "noi_dung": self.form_noi_dung.value, 
                "link_web": self.form_link.value,
                "hinh_anh": self.form_hinh_anh.value
            }
            res = await client.put(f"/api/admin/notifications/{self.form_id.value}", json=payload) if self.is_edit else await client.post("/api/admin/notifications/", json=payload)
            if res.status_code in [200, 201]:
                self.close_dialog()
                show_top_notification(self.app_page, "Thông báo", "Đã gửi thông báo thành công tới tất cả thiết bị!", ft.Colors.GREEN, sound="S")
                await self.load_data()
            else: show_top_notification(self.app_page, "Lỗi", f"{res.text}", ft.Colors.RED, sound="E")
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"{e}", ft.Colors.RED, sound="E")
            
    def delete_data(self, d):
        def on_confirm(): self.app_page.run_task(self._delete_data_async, d["id"])
        show_confirm_dialog(self.app_page, "XÁC NHẬN", f"Xóa thông báo {d['tieu_de']}?", on_confirm)
        
    async def _delete_data_async(self, id):
        try:
            client = await get_supabase_client()
            res = await client.delete(f"/api/admin/notifications/{id}")
            if res.status_code == 200:
                show_top_notification(self.app_page, "Thông báo", "Đã xóa thông báo thành công!", ft.Colors.GREEN, sound="S")
                await self.load_data()
            else: show_top_notification(self.app_page, "Lỗi", f"{res.text}", ft.Colors.RED, sound="E")
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"{e}", ft.Colors.RED, sound="E")

    def apply_theme(self): self.update()
