import flet as ft
import math
from core.theme import current_theme

class AdminDataGrid(ft.Container):
    """
    Component Grid tùy chỉnh thay thế cho DataTable.
    Hỗ trợ dãn rộng 100%, Zebra style, Sorting và Pagination.
    """
    def __init__(self, 
                 columns, 
                 data=None, 
                 on_row_click=None, 
                 on_sort=None,
                 rows_per_page=25):
        super().__init__()
        self.grid_columns = columns # List of dict: {"label": str, "col": dict, "key": str, "sortable": bool}
        self.all_data = data if data else []
        self.filtered_data = []
        self.on_row_click = on_row_click
        self.on_sort_callback = on_sort
        
        self.rows_per_page = rows_per_page
        self.current_page = 1
        self.sort_key = None
        self.sort_ascending = True

        self.expand = True
        self.border = ft.Border.all(1, current_theme.divider_color)
        self.border_radius = 12
        self.bgcolor = current_theme.surface_color
        self.clip_behavior = ft.ClipBehavior.ANTI_ALIAS

        # UI Elements
        self.header_row = ft.Container(
            content=ft.ResponsiveRow(spacing=0),
            padding=ft.Padding(12, 8, 12, 8),
            bgcolor=current_theme.surface_variant,
            border=ft.Border(bottom=ft.BorderSide(1, current_theme.divider_color))
        )
        
        self.rows_container = ft.Column(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        
        # Thêm một Container bao ngoài rows_container để tạo hiệu ứng border/background nếu cần
        self.grid_body = ft.Container(
            content=self.rows_container,
            expand=True,
            bgcolor=ft.Colors.WHITE,
        )
        
        self.btn_prev = ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=self.prev_page, icon_size=18)
        self.btn_next = ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=self.next_page, icon_size=18)
        self.page_text = ft.Text("Trang 1/1", size=12, weight=ft.FontWeight.W_500)
        self.total_text = ft.Text("Tổng số: 0", size=11, color=current_theme.text_muted)

        self.footer = ft.Container(
            padding=ft.Padding(20, 10, 20, 10),
            border=ft.Border(top=ft.BorderSide(1, current_theme.divider_color)),
            content=ft.Row([
                self.total_text,
                ft.Row([self.btn_prev, self.page_text, self.btn_next], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        self.content = ft.Column([
            self.header_row,
            self.grid_body,
            self.footer
        ], spacing=0, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        self.build_header()

    def build_header(self):
        self.header_row.content.controls.clear()
        for col in self.grid_columns:
            header_cell = ft.Container(
                col=col.get("col", 1),
                content=ft.Row([
                    ft.Text(col["label"], size=11, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                    ft.Icon(ft.Icons.ARROW_DROP_UP if self.sort_key == col.get("key") and self.sort_ascending else ft.Icons.ARROW_DROP_DOWN, 
                            size=16, visible=(self.sort_key == col.get("key"))) if col.get("sortable") else ft.Container()
                ], spacing=4, alignment=ft.MainAxisAlignment.START),
                on_click=lambda e, k=col.get("key"), s=col.get("sortable"): self.sort_data(k) if s else None,
                padding=ft.Padding(0, 0, 10, 0)
            )
            self.header_row.content.controls.append(header_cell)

    def sort_data(self, key):
        if self.sort_key == key:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_key = key
            self.sort_ascending = True
        
        if self.on_sort_callback:
            self.on_sort_callback(key, self.sort_ascending)
        else:
            # Default internal sorting
            self.all_data.sort(key=lambda x: str(x.get(key, "")).lower(), reverse=not self.sort_ascending)
            self.render_rows()
        
        self.build_header()
        self.update()

    def set_data(self, data):
        self.all_data = data if data else []
        self.current_page = 1
        self.render_rows()

    def update_page_size(self, size):
        self.rows_per_page = size
        self.current_page = 1
        self.render_rows()

    def render_rows(self):
        self.rows_container.controls.clear()
        
        # Pagination
        start_idx = (self.current_page - 1) * self.rows_per_page
        end_idx = start_idx + self.rows_per_page
        page_data = self.all_data[start_idx:end_idx]
        
        max_page = max(1, math.ceil(len(self.all_data) / self.rows_per_page))
        self.page_text.value = f"Trang {self.current_page}/{max_page}"
        self.total_text.value = f"Tổng số: {len(self.all_data)}"
        self.btn_prev.disabled = self.current_page <= 1
        self.btn_next.disabled = self.current_page >= max_page

        if not page_data:
            self.rows_container.controls.append(
                ft.Container(
                    content=ft.Text("Không có dữ liệu hiển thị", color=current_theme.text_muted, italic=True),
                    padding=40, alignment=ft.Alignment(0, 0)
                )
            )
        else:
            for i, item in enumerate(page_data):
                is_zebra = (i % 2 != 0)
                row = ft.Container(
                    content=ft.ResponsiveRow(spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding(12, 6, 12, 6),
                    bgcolor=ft.Colors.with_opacity(0.02, current_theme.primary) if is_zebra else None,
                    data=is_zebra,
                    on_hover=lambda e: self.on_row_hover(e),
                    on_click=lambda e, d=item: self.on_row_click(d) if self.on_row_click else None
                )
                
                for col in self.grid_columns:
                    cell_val = item.get(col["key"], "")
                    # Nếu có custom renderer (cell_content)
                    if "render" in col:
                        cell_content = col["render"](item)
                    else:
                        cell_content = ft.Text(str(cell_val), size=12, color=current_theme.text_main, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
                    
                    row.content.controls.append(
                        ft.Container(
                            col=col.get("col", 1),
                            content=cell_content,
                            padding=ft.Padding(0, 0, 10, 0)
                        )
                    )
                self.rows_container.controls.append(row)
        
        if self.page: self.update()

    def on_row_hover(self, e):
        e.control.bgcolor = ft.Colors.with_opacity(0.08, current_theme.primary) if e.data == "true" else \
                            (ft.Colors.with_opacity(0.02, current_theme.primary) if e.control.data else None)
        e.control.update()

    def prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_rows()

    def next_page(self, e):
        max_page = math.ceil(len(self.all_data) / self.rows_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            self.render_rows()
