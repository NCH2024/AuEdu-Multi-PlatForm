import flet as ft
import asyncio
import math
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from components.options.confirm_dialog import show_confirm_dialog

class ClassesPage(ft.Container):
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
        self.title_text = ft.Text("QUẢN LÝ LỚP HỌC", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.btn_add = ft.Button("Thêm Mới", icon=ft.Icons.ADD, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.open_add_dialog)
        
        self.search_field = ft.TextField(hint_text="Tìm kiếm theo Mã hoặc Tên lớp...", icon=ft.Icons.SEARCH, height=40, expand=True, on_change=self.filter_data)
        self.page_size_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("50")],
            value="10", width=80, height=40, on_select=self.change_page_size, content_padding=5
        )

        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Mã Lớp (ID)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Mã Phụ", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Tên Lớp", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Mã Khoa", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Khóa học", weight=ft.FontWeight.BOLD)),
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
        self.form_id = ft.TextField(label="Mã Lớp (ID)")
        self.form_code = ft.TextField(label="Mã Phụ (Code)")
        self.form_ten = ft.TextField(label="Tên Lớp")
        self.form_khoa = ft.TextField(label="Mã Khoa")
        self.form_khoahoc = ft.TextField(label="Khóa học (VD: 62)")
        
        self.dialog = ft.AlertDialog(
            title=ft.Text("Thông tin Lớp học"),
            content=ft.Column([self.form_id, self.form_code, self.form_ten, self.form_khoa, self.form_khoahoc], tight=True),
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
            {"id": "L01", "code": "62PM1", "tenlop": "Công nghệ Phần mềm 1", "khoa_id": "K01", "khoahoc": 62},
            {"id": "L02", "code": "62PM2", "tenlop": "Công nghệ Phần mềm 2", "khoa_id": "K01", "khoahoc": 62},
            {"id": "L03", "code": "63HTTT", "tenlop": "Hệ thống thông tin 1", "khoa_id": "K01", "khoahoc": 63},
        ]
        self.filtered_data = self.all_data.copy()
        self.current_page = 1
        self.render_table()

    def filter_data(self, e):
        query = self.search_field.value.lower()
        self.filtered_data = [item for item in self.all_data if query in item["id"].lower() or query in item["tenlop"].lower()]
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
                    ft.DataCell(ft.Text(item["id"])),
                    ft.DataCell(ft.Text(item.get("code", ""))),
                    ft.DataCell(ft.Text(item["tenlop"])),
                    ft.DataCell(ft.Text(item["khoa_id"])),
                    ft.DataCell(ft.Text(str(item.get("khoahoc", "")))),
                    ft.DataCell(ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT, icon_color=ft.Colors.BLUE, on_click=lambda e, d=item: self.open_edit_dialog(d)),
                        ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=lambda e, d=item: self.delete_data(d))
                    ]))
                ])
            )
        self.update()

    def open_add_dialog(self, e):
        self.form_id.value = ""
        self.form_id.disabled = False
        self.form_code.value = ""
        self.form_ten.value = ""
        self.form_khoa.value = ""
        self.form_khoahoc.value = ""
        self.app_page.overlay.append(self.dialog)
        self.dialog.open = True
        self.app_page.update()

    def open_edit_dialog(self, data):
        self.form_id.value = data["id"]
        self.form_id.disabled = True
        self.form_code.value = data.get("code", "")
        self.form_ten.value = data["tenlop"]
        self.form_khoa.value = data["khoa_id"]
        self.form_khoahoc.value = str(data.get("khoahoc", ""))
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
        show_top_notification(self.app_page, "Đã lưu lớp học thành công!", ft.Colors.GREEN)
        await self.load_data()

    def delete_data(self, data):
        def on_confirm():
            self.app_page.run_task(self._delete_data_async, data["id"])
        show_confirm_dialog(self.app_page, "Xác nhận", f"Xóa lớp {data['tenlop']}?", on_confirm)

    async def _delete_data_async(self, id):
        await asyncio.sleep(0.3)
        show_top_notification(self.app_page, "Đã xóa lớp thành công!", ft.Colors.GREEN)
        await self.load_data()

    def apply_theme(self):
        self.title_text.color = current_theme.text_main
        self.table_container.border = ft.Border.all(1, current_theme.divider_color)
        self.table_container.bgcolor = current_theme.surface_color
        self.btn_add.bgcolor = current_theme.primary
        self.update()
