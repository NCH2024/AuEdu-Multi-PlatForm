import flet as ft
from core.theme import PRIMARY_COLOR

def show_alert_dialog(self, title: str, message):
        # Hàm đóng hộp thoại
        def close_dialog(e):
            alert_dialog.open = False
            self.app_page.update()

        # Tạo hộp thoại
        alert_dialog = ft.AlertDialog(
            content=ft.Column(
                tight=True,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(title, weight=ft.FontWeight.BOLD, size=22, color=PRIMARY_COLOR)
                        ]
                    ),

                    ft.Divider(),

                    message,
                ]
            ),
            actions=[
                ft.TextButton("OK", on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
            shape=ft.RoundedRectangleBorder(radius=15),
        )
        # Đưa vào overlay và mở lên
        self.app_page.overlay.append(alert_dialog)
        alert_dialog.open = True
        self.app_page.update()