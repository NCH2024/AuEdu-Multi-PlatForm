"""
components/options/news_image.py
────────────────────────────────
Widget ảnh thông báo dùng chung cho cả home_page và news_page.

Xử lý đầy đủ các trường hợp:
  • URL từ website ngoài  (https://nctu.edu.vn/...jpg)
  • Kho Supabase Storage  (tên file không có http)
  • Google Drive          (/file/d/ID/view  hoặc  open?id=ID)
  • Trống / None          → placeholder icon
  • URL hợp lệ nhưng ảnh 404 / CORS → error_content fallback

Cách dùng:
    from components.options.news_image import build_news_image
    widget = build_news_image(url, width=80, height=80)
"""

import flet as ft
from core.theme import current_theme
from core.helper import process_image_url


def build_news_image(raw_url: str, width: int, height: int, border_radius: int = 8) -> ft.Control:
    """
    Trả về ft.Control hiển thị ảnh thông báo.
    Luôn có kích thước cố định (width x height) kể cả khi ảnh lỗi.
    """

    # ── Placeholder khi không có ảnh hoặc ảnh lỗi ──────────────────
    def _placeholder(icon=ft.Icons.IMAGE_OUTLINED):
        return ft.Container(
            width=width, height=height,
            border_radius=border_radius,
            bgcolor=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            alignment=ft.Alignment(0, 0),
            content=ft.Icon(icon, color=current_theme.text_muted, size=min(width, height) * 0.45)
        )

    # ── Xử lý URL ───────────────────────────────────────────────────
    processed = process_image_url(raw_url)  # helper đã xử lý Drive, Supabase, v.v.

    # Nếu helper trả về "icon.png" → ảnh gốc rỗng → placeholder
    if not processed or processed == "icon.png":
        return _placeholder()

    # ── Tạo ft.Image với error_content fallback ─────────────────────
    # Bọc trong Container để:
    #   1. Bo góc (clip_behavior)
    #   2. Có kích thước cố định ngay cả khi Image chưa load
    #   3. bgcolor làm nền trong khi ảnh đang tải
    img = ft.Image(
        src=processed,
        fit=ft.BoxFit.COVER,
        expand=True,
        gapless_playback=True,          # Không nháy khi src thay đổi
        error_content=_placeholder(ft.Icons.BROKEN_IMAGE_OUTLINED),
    )

    return ft.Container(
        width=width,
        height=height,
        border_radius=border_radius,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,  # Bo góc sắc nét
        bgcolor=current_theme.surface_variant,      # Màu nền khi đang tải
        content=img,
    )