import flet as ft
from core.theme import current_theme

class ScheduleGrid(ft.Container):
    def __init__(self, periods: list, on_slot_click=None):
        super().__init__()
        self.periods = periods
        self.on_slot_click = on_slot_click
        
        self.busy_slots = [] # List of {"thu", "tiet_id", "hocphan", "lop", "color"}
        self.draft_slots = [] # List of {"thu", "tiet_id", "subject", "color"}
        
        self.padding = ft.Padding(0, 0, 0, 0)
        self.border_radius = 12
        self.bgcolor = current_theme.surface_color
        self.border = ft.Border.all(1, current_theme.divider_color)
        self.clip_behavior = ft.ClipBehavior.ANTI_ALIAS
        
        self.content = self.build_grid()

    def set_busy_slots(self, busy_slots):
        self.busy_slots = busy_slots
        self.content = self.build_grid()
        try:
            self.update()
        except: pass

    def set_draft_slots(self, draft_slots):
        self.draft_slots = draft_slots
        self.content = self.build_grid()
        try:
            self.update()
        except: pass

    def build_grid(self):
        # Header Row: Buổi | Tiết | Thứ 2 | Thứ 3 | ... | CN
        days = ["BUỔI", "TIẾT", "THỨ 2", "THỨ 3", "THỨ 4", "THỨ 5", "THỨ 6", "THỨ 7", "CHỦ NHẬT"]
        header = ft.Row([
            ft.Container(
                content=ft.Text(day, weight=ft.FontWeight.W_800, size=11, color=current_theme.text_muted),
                expand=1 if i > 1 else False,
                width=65 if i == 0 else (60 if i == 1 else None),
                alignment=ft.Alignment(0, 0),
                padding=10,
                bgcolor=current_theme.surface_variant
            ) for i, day in enumerate(days)
        ], spacing=0)

        rows = [header]
        
        # Rows for each period
        for p in self.periods:
            row_controls = []
            pid = int(p['id'])
            
            # BUỔI Cell
            buoi_text = ""
            buoi_color = ft.Colors.TRANSPARENT
            if 1 <= pid <= 5:
                buoi_text = "Sáng"
                buoi_color = ft.Colors.with_opacity(0.05, ft.Colors.AMBER_100)
            elif 7 <= pid <= 12:
                buoi_text = "Chiều"
                buoi_color = ft.Colors.with_opacity(0.05, ft.Colors.BLUE_100)
            elif 13 <= pid <= 16:
                buoi_text = "Tối"
                buoi_color = ft.Colors.with_opacity(0.05, ft.Colors.PURPLE_100)

            row_controls.append(ft.Container(
                width=65, height=60,
                bgcolor=buoi_color,
                content=ft.Text(buoi_text, size=10, weight=ft.FontWeight.BOLD, color=current_theme.text_muted),
                alignment=ft.Alignment(0, 0),
                border=ft.Border(right=ft.BorderSide(1, current_theme.divider_color), bottom=ft.BorderSide(1, current_theme.divider_color))
            ))

            # TIẾT Cell: Period number and time
            row_controls.append(ft.Container(
                width=60, height=60,
                bgcolor=current_theme.surface_variant if pid % 2 == 0 else current_theme.surface_color,
                content=ft.Column([
                    ft.Text(f"T{pid}", size=12, weight=ft.FontWeight.W_900, color=current_theme.secondary),
                    ft.Text(p['thoigianbd'][:5], size=10, color=current_theme.text_muted, weight=ft.FontWeight.W_600)
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
                border=ft.Border(right=ft.BorderSide(1, current_theme.divider_color), bottom=ft.BorderSide(1, current_theme.divider_color))
            ))
            
            # Days cells
            for thu in range(2, 9): # 2=Mon, ..., 8=Sun
                # Check if busy
                busy = next((s for s in self.busy_slots if s["thu"] == thu and s["tiet_id"] == p["id"]), None)
                # Check if draft
                draft = next((s for s in self.draft_slots if s["thu"] == thu and s["tiet_id"] == p["id"]), None)
                
                cell_content = None
                cell_bgcolor = ft.Colors.TRANSPARENT
                cell_ink = True
                
                # Closure to capture thu and tiet_id correctly
                def make_click_handler(t, pi):
                    return lambda e: self.on_slot_click(t, pi) if self.on_slot_click else None

                cell_on_click = make_click_handler(thu, p["id"])
                
                if busy:
                    cell_bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.GREY_600)
                    is_current_teacher = busy.get("giangvien_id") == busy.get("target_gv_id")
                    
                    cell_content = ft.Column([
                        ft.Icon(ft.Icons.LOCK_ROUNDED, size=12, color=current_theme.text_muted),
                        ft.Text(busy["hocphan"], size=8, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color=current_theme.text_muted),
                        ft.Text(busy["lop"], size=7, color=current_theme.text_muted)
                    ], spacing=1, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    cell_ink = False
                    cell_on_click = None # Busy slots are locked
                elif draft:
                    color = draft.get("color", current_theme.primary)
                    cell_bgcolor = ft.Colors.with_opacity(0.15, color)
                    cell_content = ft.Container(
                        padding=5,
                        border=ft.Border.all(1, color),
                        border_radius=4,
                        content=ft.Text(draft["subject"], size=9, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER, color=color)
                    )
                
                row_controls.append(ft.Container(
                    expand=1, height=60,
                    bgcolor=cell_bgcolor,
                    ink=cell_ink,
                    on_click=cell_on_click,
                    border=ft.Border(
                        right=ft.BorderSide(1, current_theme.divider_color) if thu < 8 else None,
                        bottom=ft.BorderSide(1, current_theme.divider_color)
                    ),
                    content=cell_content,
                    alignment=ft.Alignment(0, 0),
                    padding=4
                ))
            
            rows.append(ft.Row(row_controls, spacing=0))

        return ft.Column(rows, spacing=0, scroll=ft.ScrollMode.AUTO)
