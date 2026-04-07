import flet as ft
from core.theme import current_theme

class SplashPage(ft.Container):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = current_theme.bg_color

        self.content = ft.Container(   
            expand=True,
            alignment=ft.Alignment(0,0),  
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=24,
                controls=[
                    # LOGO
                    ft.Image(
                        src="splash-1.png",
                        width=210,
                        height=210,
                        fit=ft.BoxFit.CONTAIN,
                    ),

                    # LOADING
                    ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=30,
                        controls=[
                            ft.ProgressRing(
                                width=36,
                                height=36,
                                stroke_width=8,
                                color=current_theme.primary
                            ),
                            ft.Text(
                                "AuEdu Đang khởi động...",
                                size=13,
                                color=current_theme.primary,
                            )
                        ]
                    )
                ]
            )
        )