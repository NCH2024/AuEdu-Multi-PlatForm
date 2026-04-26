import flet as ft
import asyncio
import flet_audio as fta
from core.theme import current_theme

def show_top_notification(page: ft.Page, title: str, message: str, color=None, duration_ms: int = 3000, sound=None):
    """
    Hệ thống Top Notification:
    - Mobile: Nhẹ, mượt, tự động co giãn theo chiều rộng màn hình.
    - PC: Thiết kế "Floating Flat" cao cấp, điểm nhấn viền trái.
    - An toàn luồng (Thread-safe) cho Flet 0.84.0
    """
    # 1. Phát âm thanh (Nếu có)
    audio = None
    if sound:
        sound_path = "assets/sounds/sound-success.mp3" if sound == "S" else "assets/sounds/sound-error.mp3"
        audio = fta.Audio(src=sound_path, autoplay=True)
        if hasattr(page, 'services'):
            page.services.append(audio)
        else:
            page.overlay.append(audio)

    # 2. Xử lý màu sắc tinh tế theo Theme
    theme_color = color if color else current_theme.primary
    
    icon_noti = ft.Icons.CHECK_CIRCLE if theme_color in [ft.Colors.GREEN_600, ft.Colors.GREEN] else ft.Icons.INFO
    if sound == "E" or theme_color in [ft.Colors.RED_500, ft.Colors.RED]:
         icon_noti = ft.Icons.ERROR

    # 3. Phân loại nền tảng & Lấy kích thước an toàn
    screen_width = page.width if page.width else 400
    is_mobile = screen_width < 768

    # Tự động co giãn: Chừa mỗi bên 16px nếu là mobile
    toast_width = screen_width - 32 if is_mobile else 380
    toast_left = 16 if is_mobile else (screen_width - toast_width) / 2

    # Cấu hình phong cách (PC Cao cấp vs Mobile Tối giản)
    if is_mobile:
        toast_border = ft.Border.all(1, theme_color)
        toast_radius = 16
        toast_padding = ft.Padding(12, 10, 12, 10)
    else:
        # PC: Viền trái dày tạo điểm nhấn (Left Accent), viền mờ xung quanh tạo khối phẳng
        toast_border = ft.Border(
            left=ft.BorderSide(10, theme_color), 
            top=ft.BorderSide(1, theme_color), 
            right=ft.BorderSide(1, theme_color), 
            bottom=ft.BorderSide(1, theme_color)
        )
        toast_radius = 10
        toast_padding = ft.Padding(5, 10, 5, 10)

    # 4. Tạo đối tượng Giao diện
    toast = ft.Container(
        content=ft.Row([
            ft.Icon(icon_noti, color=theme_color, size=30 if not is_mobile else 22),
            ft.Column([
                ft.Text(title, weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14),
                ft.Text(message, color=current_theme.text_muted, size=12),
            ], spacing=2, expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        
        bgcolor=current_theme.surface_color,          
        border=toast_border,       
        padding=toast_padding, 
        border_radius=toast_radius,
        width=toast_width, 
        left=toast_left,
        
        opacity=0, 
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        animate_position=ft.Animation(400, ft.AnimationCurve.EASE_OUT_BACK), 
        top=-100, 
    )

    page.overlay.append(toast)
    try:
        page.update()
    except Exception:
        pass

    # 5. Luồng Animation bất đồng bộ an toàn
    async def animate_toast():
        try:
            # Animation Trượt xuống
            toast.top = 40 if is_mobile else 40
            toast.opacity = 1
            if getattr(page, "page", None) and toast in page.overlay:
                page.update()

            # Chờ hiển thị
            await asyncio.sleep(duration_ms / 1000.0)

            # Animation Trượt lên
            toast.top = -100
            toast.opacity = 0
            if getattr(page, "page", None) and toast in page.overlay:
                page.update()

            # Chờ animation hoàn tất
            await asyncio.sleep(0.5) 

            # Dọn dẹp DOM an toàn
            if getattr(page, "page", None):
                if toast in page.overlay:
                    page.overlay.remove(toast)
                if audio:
                    if hasattr(page, 'services') and audio in page.services:
                        page.services.remove(audio)
                    elif audio in page.overlay:
                        page.overlay.remove(audio)
                page.update()
        except Exception as e:
            # Bắt lỗi im lặng để không làm văng luồng của Flet
            pass

    # Khởi chạy luồng
    page.run_task(animate_toast)