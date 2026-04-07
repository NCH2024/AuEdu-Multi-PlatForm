import flet as ft
from core.theme import current_theme
from core.helper import process_image_url

def build_news_image(raw_url: str, width: int, height: int, border_radius: int = 8) -> ft.Control:
    processed = process_image_url(raw_url)

    # 1. Lớp nền (Placeholder) hiển thị mặc định nếu ảnh lỗi hoặc đang load
    placeholder = ft.Container(
        width=width, height=height,
        border_radius=border_radius,
        bgcolor=current_theme.surface_variant,
        border=ft.Border.all(1, current_theme.divider_color),
        alignment=ft.Alignment(0, 0),
        content=ft.Icon(ft.Icons.IMAGE_OUTLINED, color=current_theme.text_muted, size=min(width, height) * 0.45)
    )

    if not processed or processed == "icon.png":
        return placeholder

    # 2. Lớp ảnh thực tế (TUYỆT ĐỐI KHÔNG DÙNG expand=True Ở ĐÂY)
    img = ft.Image(
        src=processed,
        width=width,
        height=height,
        fit=ft.BoxFit.COVER,
        gapless_playback=True
    )

    # 3. Gom vào Stack, ảnh thật sẽ đè lên ảnh nền. Rất an toàn và không bao giờ crash UI.
    return ft.Container(
        width=width, height=height,
        border_radius=border_radius,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Stack([placeholder, img])
    )