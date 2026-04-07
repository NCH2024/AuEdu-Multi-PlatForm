import flet as ft

class LoadingOverlay(ft.Container):
    def __init__(self, message="Đang đồng bộ dữ liệu..."):
        super().__init__()
        self.expand = True
        self.bgcolor = ft.Colors.with_opacity(0.85, ft.Colors.WHITE)
        
        # ĐÃ SỬA: Dùng Class OOP chuẩn của Flet 0.82.0 thay vì gọi thuộc tính thường
        self.alignment = ft.Alignment(0, 0)
        
        self.content = ft.Column(
            controls=[
                ft.ProgressRing(width=45, height=45, stroke_width=4, color=ft.Colors.BLUE_600),
                ft.Container(height=10),
                ft.Text(message, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800, size=15)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )