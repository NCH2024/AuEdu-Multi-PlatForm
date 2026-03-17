import flet as ft

# Bộ màu chủ đạo theo yêu cầu: Xanh Pastel & Xanh Đen (Dark Blue)
PRIMARY_COLOR = "#AEC6CF"         # Xanh dương pastel (Màu nền chính, nhẹ nhàng)
SECONDARY_COLOR = "#0556A1"       # Xanh đen (Điểm nhấn, chữ tiêu đề, icon quan trọng)
ACCENT_COLOR = "#85C1E9"          # Xanh dương đậm hơn một chút để làm nút bấm

PRIMARY_COLOR_BLUR = ft.Colors.with_opacity(0.85, PRIMARY_COLOR)
BG_COLOR = "#F5F7FA"              # Màu nền sáng cho toàn ứng dụng
TEXT_MAIN = SECONDARY_COLOR       # Chữ chính dùng xanh đen cho dễ đọc
TEXT_MUTED = ft.Colors.GREY_600

GLASS_BG = ft.Colors.with_opacity(0.85, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.3, PRIMARY_COLOR)

def get_glass_container(content: ft.Control, width=None, height=None, padding=20, margin=0, border_radius=15, expand=False) -> ft.Container:
    glass_side = ft.BorderSide(1, GLASS_BORDER)
    
    return ft.Container(
        content=content,
        width=width,
        height=height,
        padding=padding,
        margin=margin,               
        expand=expand,
        border_radius=border_radius, 
        bgcolor=GLASS_BG,
        border=ft.Border(top=glass_side, right=glass_side, bottom=glass_side, left=glass_side),
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=8, color=ft.Colors.with_opacity(0.1, SECONDARY_COLOR), offset=ft.Offset(0, 4)
        )
    )