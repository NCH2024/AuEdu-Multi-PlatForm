import flet as ft

PRIMARY_COLOR = "#0066FF" 
PRIMARY_COLOR_BLUR = ft.Colors.with_opacity(0.95, "#0066FF")
BG_COLOR = "#F5F7FA"      
TEXT_MAIN = ft.Colors.BLACK_87 
TEXT_MUTED = ft.Colors.GREY_600

GLASS_BG = ft.Colors.with_opacity(0.95, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.2, ft.Colors.GREY_300)

# ĐÃ SỬA: Thêm tham số margin=0 và border_radius=15 làm mặc định
def get_glass_container(content: ft.Control, width=None, height=None, padding=20, margin=0, border_radius=15, expand=False) -> ft.Container:
    glass_side = ft.BorderSide(1, GLASS_BORDER)
    
    return ft.Container(
        content=content,
        width=width,
        height=height,
        padding=padding,
        margin=margin,               # Cấp quyền tùy chỉnh Margin
        expand=expand,
        border_radius=border_radius, # Cấp quyền tùy chỉnh Bo góc
        bgcolor=GLASS_BG,
        border=ft.Border(top=glass_side, right=glass_side, bottom=glass_side, left=glass_side),
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=5, color=ft.Colors.BLACK_12, offset=ft.Offset(0, 2)
        )
    )