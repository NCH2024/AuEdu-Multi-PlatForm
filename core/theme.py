import flet as ft

# Bộ màu chủ đạo theo yêu cầu: Xanh Pastel & Xanh Đen (Dark Blue)
PRIMARY_COLOR = "#AEC6CF"         # Xanh dương pastel (Màu nền chính, nhẹ nhàng)
SECONDARY_COLOR = "#0450DF"       # Xanh đen (Điểm nhấn, chữ tiêu đề, icon quan trọng)
ACCENT_COLOR = "#0A456D"          # Xanh dương đậm hơn một chút để làm nút bấm

PRIMARY_COLOR_BLUR = ft.Colors.with_opacity(0.75, PRIMARY_COLOR)
BG_COLOR = "#F5F7FA"              # Màu nền sáng cho toàn ứng dụng
TEXT_MAIN = SECONDARY_COLOR       # Chữ chính dùng xanh đen cho dễ đọc
TEXT_MUTED = ft.Colors.GREY_600

GLASS_BG = ft.Colors.with_opacity(0.75, ft.Colors.WHITE)
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

def adaptive_container(page: ft.Page, content: ft.Control, width=None, height=None, padding=20, margin=0, border_radius=15, expand=False) -> ft.Container:
    """
    Hàm tự động trả về UI phù hợp với nền tảng phần cứng.
    - Mobile: Trả về khối phẳng (Flat Design), không bóng mờ, siêu nhẹ.
    - PC/Mac: Trả về khối kính mờ (Glassmorphism) đẹp mắt.
    """
    # Flet 0.82.2 hỗ trợ check platform rất chuẩn xác
    if page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]:
        # TRÊN ĐIỆN THOẠI: Không dùng blur, dùng nền solid viền mỏng
        return ft.Container(
            content=content,
            width=width,
            height=height,
            padding=padding, # Trên mobile có thể em sẽ muốn truyền padding nhỏ hơn (ví dụ 10-12)
            margin=margin,
            expand=expand,
            border_radius=border_radius,
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.BLACK_12),
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=4, 
                color=ft.Colors.with_opacity(0.05, SECONDARY_COLOR), 
                offset=ft.Offset(0, 2)
            )
        )
    else:
        # TRÊN PC (Windows/Mac): Dùng nguyên bản Glassmorphism
        return get_glass_container(
            content=content, 
            width=width, 
            height=height, 
            padding=padding, 
            margin=margin, 
            border_radius=border_radius, 
            expand=expand
        )