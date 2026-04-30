import flet as ft
import asyncio
import datetime
import httpx
from core.theme import current_theme
from components.options.top_notification import show_top_notification

class AttendanceSchedulePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 20
        self.selected_classes = []
        
        # --- UI COMPONENTS ---
        self.title_field = ft.TextField(label="Tiêu đề Lịch Điểm Danh", expand=True)
        self.date_picker = ft.DatePicker(on_change=self.on_date_changed)
        self.date_btn = ft.Button(
            "Chọn Ngày", 
            icon=ft.Icons.CALENDAR_MONTH,
            on_click=lambda _: self.app_page.open(self.date_picker)
        )
        self.date_text = ft.Text("Chưa chọn", color=current_theme.text_muted)
        
        self.start_time_picker = ft.TimePicker(on_change=self.on_start_time_changed)
        self.start_btn = ft.Button(
            "Bắt đầu", icon=ft.Icons.ACCESS_TIME, on_click=lambda _: self.app_page.open(self.start_time_picker)
        )
        self.start_text = ft.Text("00:00", color=current_theme.text_muted)

        self.end_time_picker = ft.TimePicker(on_change=self.on_end_time_changed)
        self.end_btn = ft.Button(
            "Kết thúc", icon=ft.Icons.ACCESS_TIME_FILLED, on_click=lambda _: self.app_page.open(self.end_time_picker)
        )
        self.end_text = ft.Text("00:00", color=current_theme.text_muted)

        # Custom Multiple Select cho Lớp
        self.class_checkboxes = ft.Column(
            controls=[
                ft.Checkbox(label="Lớp CNTT-K62", value=False, on_change=self.on_class_toggle, data="cls_1"),
                ft.Checkbox(label="Lớp ATTT-K62", value=False, on_change=self.on_class_toggle, data="cls_2"),
                ft.Checkbox(label="Lớp KTPM-K62", value=False, on_change=self.on_class_toggle, data="cls_3"),
            ],
            scroll=ft.ScrollMode.AUTO,
            height=120
        )

        # Cấu hình AI
        self.ai_threshold_slider = ft.Slider(min=0.1, max=0.99, divisions=89, value=0.6, label="{value}")
        self.fiqa_threshold_slider = ft.Slider(min=0.1, max=0.99, divisions=89, value=0.5, label="{value}")
        self.anti_spoofing_switch = ft.Switch(label="Kích hoạt Anti-Spoofing (Chống giả mạo)", value=True)

        # Layout chính
        self.content = ft.Column([
            ft.Text("TẠO LỊCH ĐIỂM DANH MỚI", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Divider(color=current_theme.divider_color),
            
            ft.Row([self.title_field]),
            
            ft.Text("Thời gian", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Row([
                self.date_btn, self.date_text, 
                ft.VerticalDivider(width=20, color=current_theme.divider_color),
                self.start_btn, self.start_text,
                ft.VerticalDivider(width=20, color=current_theme.divider_color),
                self.end_btn, self.end_text
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            
            ft.Container(height=10),
            ft.Text("Chọn Lớp Tham Gia", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Container(
                content=self.class_checkboxes,
                border=ft.Border.all(1, current_theme.divider_color),
                border_radius=8,
                padding=10
            ),
            
            ft.Container(height=10),
            ft.Text("Thông Số AI Nhận Diện", weight=ft.FontWeight.BOLD, color=current_theme.text_main),
            ft.Row([
                ft.Column([ft.Text("Cosine Similarity Threshold:"), self.ai_threshold_slider], expand=True),
                ft.Column([ft.Text("FIQA Chất lượng ảnh:"), self.fiqa_threshold_slider], expand=True)
            ]),
            self.anti_spoofing_switch,
            
            ft.Container(height=20),
            ft.Button("LƯU LỊCH ĐIỂM DANH", icon=ft.Icons.SAVE, bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_schedule)
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def on_date_changed(self, e):
        if self.date_picker.value:
            self.date_text.value = self.date_picker.value.strftime("%Y-%m-%d")
            self.update()

    def on_start_time_changed(self, e):
        if self.start_time_picker.value:
            self.start_text.value = self.start_time_picker.value.strftime("%H:%M")
            self.update()

    def on_end_time_changed(self, e):
        if self.end_time_picker.value:
            self.end_text.value = self.end_time_picker.value.strftime("%H:%M")
            self.update()

    def on_class_toggle(self, e):
        if e.control.value:
            if e.control.data not in self.selected_classes:
                self.selected_classes.append(e.control.data)
        else:
            if e.control.data in self.selected_classes:
                self.selected_classes.remove(e.control.data)

    def save_schedule(self, e):
        self.app_page.run_task(self._save_schedule_async)

    async def _save_schedule_async(self):
        if not self.title_field.value or not self.date_text.value or not self.selected_classes:
            show_top_notification(self.app_page, "Vui lòng điền đầy đủ tiêu đề, ngày và chọn ít nhất 1 lớp!", ft.Colors.RED)
            return
            
        payload = {
            "title": self.title_field.value,
            "date": self.date_text.value,
            "start_time": self.start_text.value,
            "end_time": self.end_text.value,
            "class_ids": self.selected_classes,
            "ai_threshold": self.ai_threshold_slider.value,
            "fiqa_threshold": self.fiqa_threshold_slider.value,
            "anti_spoofing": self.anti_spoofing_switch.value
        }
        
        try:
            # GỌI API FASTAPI TẠI ĐÂY
            await asyncio.sleep(1) # Giả lập loading
            show_top_notification(self.app_page, "Đã tạo lịch điểm danh thành công!", ft.Colors.GREEN)
        except Exception as ex:
            show_top_notification(self.app_page, f"Lỗi hệ thống: {ex}", ft.Colors.RED)

    def apply_theme(self):
        self.content.controls[0].color = current_theme.text_main
        self.content.controls[1].color = current_theme.divider_color
        self.content.controls[3].color = current_theme.text_main
        self.date_text.color = current_theme.text_muted
        self.start_text.color = current_theme.text_muted
        self.end_text.color = current_theme.text_muted
        self.content.controls[6].color = current_theme.text_main
        self.content.controls[7].border = ft.Border.all(1, current_theme.divider_color)
        self.content.controls[9].color = current_theme.text_main
        self.content.controls[12].bgcolor = current_theme.primary
        self.update()
