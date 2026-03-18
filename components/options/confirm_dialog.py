import flet as ft
from core.theme import SECONDARY_COLOR

def show_confirm_dialog(page: ft.Page, title: str, message: str, on_confirm_callback):
    """
    Hiển thị hộp thoại xác nhận (Có/Không). 
    Nếu bấm 'Có', sẽ gọi hàm on_confirm_callback.
    """
    def close_dialog(e):
        dialog.open = False
        page.update()

    def confirm_action(e):
        dialog.open = False
        page.update()
        if on_confirm_callback:
            on_confirm_callback()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.ORANGE_500), ft.Text(title, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=18)]),
        content=ft.Text(message, size=14, color=ft.Colors.BLACK_87),
        actions=[
            ft.TextButton("Hủy bỏ", on_click=close_dialog),
            ft.Button(
                content=ft.Text("Xác nhận", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD), 
                bgcolor=ft.Colors.RED_500, 
                on_click=confirm_action
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=15),
        content_padding=ft.Padding(24, 20, 24, 10),
    )
    
    page.overlay.append(dialog)
    dialog.open = True
    page.update()