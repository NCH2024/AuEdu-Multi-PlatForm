import flet as ft
import asyncio
import flet_audio as fta
from core.theme import current_theme

def show_top_notification(page: ft.Page, title: str, message: str, color=None, duration_ms: int = 3000, sound=None):
    """
    Hệ thống Top Notification thiết kế phẳng (Flat Design), không Shadow.
    Sử dụng màu viền và Icon để báo hiệu, đảm bảo chữ luôn dễ đọc trên mọi Theme.
    """
    # 1. Phát âm thanh (Nếu có)
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

    # 3. Giao diện phẳng (Flat Toast)
    toast = ft.Container(
        content=ft.Row([
            ft.Icon(icon_noti, color=theme_color, size=24),
            ft.Column([
                ft.Text(title, weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14),
                ft.Text(message, color=current_theme.text_muted, size=12),
            ], spacing=2, expand=True)
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        
        bgcolor=current_theme.surface_color,          
        border=ft.Border.all(1.5, theme_color),       
        padding=15, # FIX CẢNH BÁO: Dùng padding nguyên khối để tránh lỗi DeprecationWarning
        border_radius=12,
        width=350, 
        
        opacity=0, 
        animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        animate_position=ft.Animation(400, ft.AnimationCurve.EASE_OUT_BACK), 
        top=-100, 
    )

    def center_toast():
        # FIX LỖI WINDOW: Lấy kích thước theo chuẩn Flet 0.8x an toàn
        try:
            screen_width = page.window.width
        except AttributeError:
            screen_width = page.width
            
        if screen_width:
            toast.left = (screen_width - 350) / 2
        else:
            toast.left = 50 

    center_toast()
    page.overlay.append(toast)
    page.update()

    # 4. Luồng Animation bất đồng bộ
    async def animate_toast():
        toast.top = 20
        toast.opacity = 1
        page.update()

        await asyncio.sleep(duration_ms / 1000.0)

        toast.top = -100
        toast.opacity = 0
        page.update()

        await asyncio.sleep(0.5)
        if toast in page.overlay:
            page.overlay.remove(toast)
            page.update()
            
        if sound:
            try:
                if hasattr(page, 'services') and audio in page.services:
                    page.services.remove(audio)
                elif audio in page.overlay:
                    page.overlay.remove(audio)
            except: pass

    page.run_task(animate_toast)