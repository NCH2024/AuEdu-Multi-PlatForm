import flet as ft

from components.options.custom_dropdown import CustomDropdown
from core.theme import current_theme

class StatsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        # Khởi tạo các Control để có thể truy xuất sau này
        self.dd_lop = CustomDropdown(label="Chọn một lớp", options=[ft.dropdown.Option("Tất cả")])
        self.btn_refresh = ft.Button(
            content=ft.Text("Làm mới", color=current_theme.bg_color, weight=ft.FontWeight.BOLD), 
            bgcolor=current_theme.secondary,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            height=40
        )
        
        # Gắn UI vào content
        self.content = self.build_ui()

    def apply_theme(self):
        """Vẽ lại màu sắc UI khi đổi Theme siêu mượt"""
        # Nhuộm màu lại cho nút tĩnh
        self.btn_refresh.content.color = current_theme.bg_color
        self.btn_refresh.bgcolor = current_theme.secondary
        
        self.content = self.build_ui()
        if self.page: self.update()

    def did_mount(self):
        # Anh để sẵn hàm này cho em. 
        # Sau này em viết hàm load_data từ Supabase thì gọi nó ở đây nhé!
        pass

    def build_ui(self):
        toolbar = ft.Row([self.dd_lop, self.btn_refresh], alignment=ft.MainAxisAlignment.END)

        def make_card(content):
            return ft.Container(
                content=content, padding=20, 
                bgcolor=current_theme.surface_color, border_radius=16, 
                border=ft.Border.all(1, current_theme.divider_color)
            )

        def create_stat_card(icon_name, number_text, label_text, sub_text=""):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon_name, color=current_theme.secondary, size=24)], alignment=ft.MainAxisAlignment.START),
                    ft.Text(number_text, size=22, weight=ft.FontWeight.BOLD, color=current_theme.secondary),
                    ft.Text(label_text, size=13, weight=ft.FontWeight.W_500, color=current_theme.text_main),
                    ft.Text(sub_text, size=11, color=current_theme.text_muted)
                ], spacing=2),
                bgcolor=current_theme.surface_variant, padding=15, border_radius=12,
                border=ft.Border.all(1, current_theme.divider_color)
            )

        overview_card = make_card(
            content=ft.Column([
                ft.Text("TỔNG QUAN", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.ResponsiveRow([
                    ft.Column([create_stat_card(ft.Icons.LIBRARY_BOOKS_OUTLINED, "1", "Tổng số lớp điểm danh", "100% (1 Lớp)")], col={"sm": 12, "md": 6, "lg": 3, "xl": 3}),
                    ft.Column([create_stat_card(ft.Icons.ACCESS_ALARM_ROUNDED, "6 Tuần", "Thời gian còn lại của học kỳ", "")], col={"sm": 12, "md": 6, "lg": 3, "xl": 3}),
                    ft.Column([create_stat_card(ft.Icons.INSERT_CHART_OUTLINED, "100%", "Lịch theo tiến độ", "")], col={"sm": 12, "md": 6, "lg": 3, "xl": 3}),
                    ft.Column([create_stat_card(ft.Icons.SETTINGS_OUTLINED, "NÂNG CAO", "Chức năng quản trị", "")], col={"sm": 12, "md": 6, "lg": 3, "xl": 3}),
                ], run_spacing=15)
            ])
        )

        chart_card = make_card(
            content=ft.Column([
                ft.Text("THỐNG KÊ THEO LỚP HỌC PHẦN", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.Container(content=ft.Text("Khu vực Biểu đồ Cột (BarChart)", color=current_theme.text_muted), height=200, alignment=ft.Alignment(0,0), bgcolor=current_theme.surface_variant, border_radius=12, border=ft.Border.all(1, current_theme.divider_color)),
                ft.ResponsiveRow([
                    ft.Column([ft.Container(content=ft.Text("Buổi hoàn thành\n(PieChart)", color=current_theme.text_muted, text_align=ft.TextAlign.CENTER), height=150, alignment=ft.Alignment(0,0), bgcolor=current_theme.surface_variant, border_radius=12, border=ft.Border.all(1, current_theme.divider_color))], col={"sm": 12, "md": 6}),
                    ft.Column([ft.Container(content=ft.Text("Tỉ lệ SV đi học\n(PieChart)", color=current_theme.text_muted, text_align=ft.TextAlign.CENTER), height=150, alignment=ft.Alignment(0,0), bgcolor=current_theme.surface_variant, border_radius=12, border=ft.Border.all(1, current_theme.divider_color))], col={"sm": 12, "md": 6}),
                ], run_spacing=15)
            ], spacing=15)
        )

        report_card = make_card(
            content=ft.Column([
                ft.Text("Lịch học theo tiến độ", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14, text_align=ft.TextAlign.CENTER),
                ft.Container(content=ft.Text("Khu vực Lịch (Calendar)", color=current_theme.text_muted), height=250, alignment=ft.Alignment(0,0), bgcolor=current_theme.surface_variant, border_radius=12, border=ft.Border.all(1, current_theme.divider_color)),
                ft.Container(height=10),
                ft.Button(content=ft.Text("XUẤT DANH SÁCH THỐNG KÊ", color=current_theme.bg_color, weight=ft.FontWeight.BOLD), bgcolor=current_theme.accent, height=45),
                ft.Button(content=ft.Text("TẠO BÁO CÁO", color=current_theme.bg_color, weight=ft.FontWeight.BOLD), bgcolor=current_theme.secondary, height=45)
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10) 
        )

        main_layout = ft.Column([
            ft.Container(height=5),
            toolbar,
            overview_card,
            ft.ResponsiveRow([
                ft.Column([chart_card], col={"sm": 12, "md": 12, "lg": 7, "xl": 7}),
                ft.Column([report_card], col={"sm": 12, "md": 12, "lg": 5, "xl": 5}),
            ], spacing=15, run_spacing=15),
            ft.Container(height=30)
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=15)

        return main_layout