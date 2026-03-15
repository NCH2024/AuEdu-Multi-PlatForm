import flet as ft

PRIMARY_COLOR = "#0066FF" 
PRIMARY_COLOR_BLUR = ft.Colors.with_opacity(0.75, "#0066FF")
BG_COLOR = "#F5F7FA"      
TEXT_MAIN = ft.Colors.BLACK_87 
TEXT_MUTED = ft.Colors.GREY_600

GLASS_BG = ft.Colors.with_opacity(0.4, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.2, ft.Colors.WHITE)

def get_glass_container(content: ft.Control, width=None, height=None, padding=20, expand=False) -> ft.Container:
    # CHUẨN MỚI 0.82.0: Phải khai báo từng cạnh (BorderSide) riêng biệt, không dùng hàm .all() ảo nữa
    glass_side = ft.BorderSide(1, GLASS_BORDER)
    
    return ft.Container(
        content=content,
        width=width,
        height=height,
        padding=padding,
        expand=expand,
        border_radius=15,
        bgcolor=GLASS_BG,
        blur=ft.Blur(sigma_x=10, sigma_y=10, tile_mode=ft.BlurTileMode.MIRROR),
        border=ft.Border(top=glass_side, right=glass_side, bottom=glass_side, left=glass_side),
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=15, color=ft.Colors.BLACK_12, offset=ft.Offset(0, 4)
        )
    )