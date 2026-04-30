import flet as ft
import asyncio
import math
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog

class SemestersPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 20

        self.all_data = []
        self.filtered_data = []
        self.current_page = 1
        self.page_size = 10

        # -- UI Elements --
        self.title_text = ft.Text("QUẢN LÝ HỌC KỲ", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.btn_add = ft.Button("Thêm Mới", icon=ft.Icons.ADD, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.open_add_dialog)
        
        self.search_field = ft.TextField(hint_text="Tìm kiếm theo Tên Học kỳ hoặc Năm học...", icon=ft.Icons.SEARCH, height=40, expand=True, on_change=self.filter_data)
        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50")],
            value="10", width=80, height=40, on_select=self.change_page_size, content_padding=5
        )

        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tên Học Kỳ", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Năm Học", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Bắt đầu", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Kết thúc", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Thao tác", weight=ft.FontWeight.BOLD)),
            ],
            rows=[]
        )

        self.btn_prev = ft.Button("< Trước", on_click=self.prev_page, disabled=True)
        self.btn_next = ft.Button("Sau >", on_click=self.next_page, disabled=True)
        self.page_text = ft.Text("Trang 1/1", weight=ft.FontWeight.BOLD)

        self.table_container = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field, ft.Text("Hiển thị:", weight=ft.FontWeight.BOLD), self.page_size_dropdown], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([self.data_table], scroll=ft.ScrollMode.AUTO, expand=True),
                ft.Row([self.btn_prev, self.page_text, self.btn_next], alignment=ft.MainAxisAlignment.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.START, expand=True),
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=12,
            bgcolor=current_theme.surface_color,
            padding=15,
            expand=True
        )

        self.content = ft.Column([
            ft.Row([self.title_text, self.btn_add], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            self.table_container
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.START)

        # -- Form Dialog --
        self.form_ten = ft.TextField(label="Tên Học Kỳ (VD: 1, 2, 3)")
        self.form_nam = ft.TextField(label="Năm Học (VD: 2023-2024)")
        self.form_start = ft.TextField(label="Ngày Bắt Đầu (YYYY-MM-DD)")
        self.form_end = ft.TextField(label="Ngày Kết Thúc (YYYY-MM-DD)")
        self.current_edit_id = None
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Thông tin Học Kỳ"),
            content=ft.Column([self.form_ten, self.form_nam, self.form_start, self.form_end], tight=True),
            actions=[
                ft.TextButton("Hủy", on_click=self.close_dialog),
                ft.Button("Lưu", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)
            ]
        )

    def did_mount(self):
        self.app_page.run_task(self.load_data)

    async def load_data(self):
        await asyncio.sleep(0.3)
        self.all_data = [
            {"id": 1, "tenhocky": "1", "namhoc": "2023-2024", "start_date": "2023-09-01", "end_date": "2024-01-15"},
            {"id": 2, "tenhocky": "2", "namhoc": "2023-2024", "start_date": "2024-02-01", "end_date": "2024-06-30"},
        ]
        self.filtered_data = self.all_data.copy()
        self.current_page = 1
        self.render_table()

    def filter_data(self, e):
        query = self.search_field.value.lower()
        self.filtered_data = [item for item in self.all_data if query in str(item["tenhocky"]).lower() or query in item["namhoc"].lower()]
        self.current_page = 1
        self.render_table()

    def change_page_size(self, e):
        self.page_size = int(self.page_size_dropdown.value)
        self.current_page = 1
        self.render_table()

    def prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_table()

    def next_page(self, e):
        max_page = max(1, math.ceil(len(self.filtered_data) / self.page_size))
        if self.current_page < max_page:
            self.current_page += 1
            self.render_table()

    def render_table(self):
        max_page = max(1, math.ceil(len(self.filtered_data) / self.page_size))
        self.btn_prev.disabled = self.current_page == 1
        self.btn_next.disabled = self.current_page == max_page
        self.page_text.value = f"Trang {self.current_page}/{max_page}"

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        page_data = self.filtered_data[start_idx:end_idx]

        self.data_table.rows.clear()
        for item in page_data:
            self.data_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(item["id"]))),
                    ft.DataCell(ft.Text(item["tenhocky"])),
                    ft.DataCell(ft.Text(item["namhoc"])),
                    ft.DataCell(ft.Text(item.get("start_date", ""))),
                    ft.DataCell(ft.Text(item.get("end_date", ""))),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT, icon_color=ft.Colors.BLUE, on_click=lambda e, d=item: self.open_edit_dialog(d)),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=lambda e, d=item: self.delete_data(d))
                    ]))
                ])
            )
        self.update()

    def open_add_dialog(self, e):
        self.current_edit_id = None
        self.form_ten.value = ""
        self.form_nam.value = ""
        self.form_start.value = ""
        self.form_end.value = ""
        self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        self.current_edit_id = data["id"]
        self.form_ten.value = data["tenhocky"]
        self.form_nam.value = data["namhoc"]
        self.form_start.value = data.get("start_date", "")
        self.form_end.value = data.get("end_date", "")
        self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def close_dialog(self, e=None):
        self.dialog.open = False
        self.app_page.update()

    def save_data(self, e):
        self.app_page.run_task(self._save_data_async)

    async def _save_data_async(self):
        self.close_dialog()
        await asyncio.sleep(0.3)
        show_top_notification(self.app_page, "Đã lưu học kỳ thành công!", ft.Colors.GREEN)
        await self.load_data()

    def delete_data(self, data):
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "Xác nhận", f"Xóa Học kỳ {data['tenhocky']} ({data['namhoc']})?", on_confirm)

    async def _delete_data_async(self, id):
        await asyncio.sleep(0.3)
        show_top_notification(self.app_page, "Đã xóa học kỳ thành công!", ft.Colors.GREEN)
        await self.load_data()

    def apply_theme(self):
        self.title_text.color = current_theme.text_main
        self.table_container.border = ft.Border.all(1, current_theme.divider_color)
        self.table_container.bgcolor = current_theme.surface_color
        self.btn_add.bgcolor = current_theme.primary
        self.update()
