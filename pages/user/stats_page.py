import flet as ft

from components.options.custom_dropdown import CustomDropdown
from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR

class StatsPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        # Khởi tạo các Control để có thể truy xuất sau này
        self.dd_lop = CustomDropdown(label="Chọn một lớp", options=[ft.dropdown.Option("Tất cả")])
        self.btn_refresh = ft.Button(
            content=ft.Text("Làm mới", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
            bgcolor=SECONDARY_COLOR,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            height=40
        )
        
        # Gắn UI vào content
        self.content = self.build_ui()

    def did_mount(self):
        # Anh để sẵn hàm này cho em. 
        # Sau này em viết hàm load_data từ Supabase thì gọi nó ở đây nhé!
        pass

    def build_ui(self):
        toolbar = ft.Row([self.dd_lop, self.btn_refresh], alignment=ft.MainAxisAlignment.END)

        def create_stat_card(icon_name, number_text, label_text, sub_text=""):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon_name, color=SECONDARY_COLOR, size=24)], alignment=ft.MainAxisAlignment.START),
                    ft.Text(number_text, size=22, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                    ft.Text(label_text, size=13, weight=ft.FontWeight.W_500, color=ft.Colors.BLACK_87),
                    ft.Text(sub_text, size=11, color=ft.Colors.GREY_600)
                ], spacing=2),
                bgcolor=ft.Colors.WHITE, padding=15, border_radius=8
            )

        overview_card = get_glass_container(
            content=ft.Column([
                ft.Text("TỔNG QUAN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                ft.ResponsiveRow([
                    ft.Column([create_stat_card(ft.Icons.LIBRARY_BOOKS_OUTLINED, "1", "Tổng số lớp điểm danh", "100% (1 Lớp)")], col={"sm": 6, "md": 3}),
                    ft.Column([create_stat_card(ft.Icons.ACCESS_ALARM_ROUNDED, "6 Tuần", "Thời gian còn lại của học kỳ", "")], col={"sm": 6, "md": 3}),
                    ft.Column([create_stat_card(ft.Icons.INSERT_CHART_OUTLINED, "100%", "Lịch theo tiến độ", "")], col={"sm": 6, "md": 3}),
                    ft.Column([create_stat_card(ft.Icons.SETTINGS_OUTLINED, "NÂNG CAO", "Chức năng dành cho người quản trị", "")], col={"sm": 6, "md": 3}),
                ])
            ])
        )

        chart_card = get_glass_container(
            content=ft.Column([
                ft.Text("THỐNG KÊ THEO LỚP HỌC PHẦN", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                ft.Container(content=ft.Text("Khu vực Biểu đồ Cột (BarChart)", color=ft.Colors.GREY_400), height=200, alignment=ft.Alignment(0,0), bgcolor=ft.Colors.WHITE, border_radius=8),
                ft.ResponsiveRow([
                    ft.Column([ft.Container(content=ft.Text("Buổi hoàn thành\n(PieChart)", color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER), height=150, alignment=ft.Alignment(0,0), bgcolor=ft.Colors.WHITE, border_radius=8)], col={"sm": 6}),
                    ft.Column([ft.Container(content=ft.Text("Tỉ lệ SV đi học\n(PieChart)", color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER), height=150, alignment=ft.Alignment(0,0), bgcolor=ft.Colors.WHITE, border_radius=8)], col={"sm": 6}),
                ])
            ])
        )

        report_card = get_glass_container(
            content=ft.Column([
                ft.Text("Lịch học theo tiến độ", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=14, text_align=ft.TextAlign.CENTER),
                ft.Container(content=ft.Text("Khu vực Lịch (Calendar)", color=ft.Colors.GREY_400), height=250, alignment=ft.Alignment(0,0), bgcolor=ft.Colors.WHITE, border_radius=8),
                ft.Container(height=10),
                ft.Button(content=ft.Text("XUẤT DANH SÁCH THỐNG KÊ", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=ACCENT_COLOR, height=45),
                ft.Button(content=ft.Text("TẠO BÁO CÁO", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=SECONDARY_COLOR, height=45)
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH) 
        )

        main_layout = ft.Column([
            toolbar,
            overview_card,
            ft.ResponsiveRow([
                ft.Column([chart_card], col={"sm": 12, "md": 7}),
                ft.Column([report_card], col={"sm": 12, "md": 5}),
            ])
        ])

        return main_layout