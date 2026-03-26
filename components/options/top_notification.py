import flet as ft
import flet_audio as fta
import asyncio
from core.theme import current_theme

class TopNotification(ft.Container):
    def __init__(self, page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=None):
        super().__init__()
        self.app_page = page
        self.top = -100 
        self.left = 0
        self.right = 0
        
        self.animate_position = ft.Animation(duration=500, curve=ft.AnimationCurve.EASE_OUT_BACK)
        self.animate_opacity = ft.Animation(duration=400, curve=ft.AnimationCurve.EASE_IN_OUT)
        self.opacity = 0
        self.duration_ms = duration_ms

        theme_color = color if color else current_theme.primary
        noti_width = (self.app_page.width - 40) if (self.app_page.width and self.app_page.width < 450) else 400

        # Xử lý màu chữ thông minh tương phản với màu nền của thông báo
        is_light_bg = theme_color in [ft.Colors.YELLOW, ft.Colors.AMBER, "#FBCFE8", "#93C5FD", "#6EE7B7", "#FFFFFF", "#D1D5DB", "#A7F3D0", "#F3F4F6", ft.Colors.WHITE]
        text_color = ft.Colors.BLACK_87 if is_light_bg else ft.Colors.WHITE

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=noti_width, padding=15,
                    bgcolor=theme_color,  # Sử dụng màu sắc làm nền chính luôn
                    border_radius=15,
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=ft.Colors.with_opacity(0.4, theme_color), offset=ft.Offset(0, 5)),
                    content=ft.Row(
                        spacing=15,
                        controls=[
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=text_color, size=26),
                            ft.Column(
                                expand=True, spacing=2,
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD, color=text_color, size=14),
                                    ft.Text(message, color=ft.Colors.with_opacity(0.9, text_color), size=12)
                                ]
                            )
                        ]
                    )
                )
            ]
        )

    def did_mount(self): self.app_page.run_task(self.show_and_hide)

    async def show_and_hide(self):
        await asyncio.sleep(0.1)
        if not self.page: return 
        self.top = 30
        self.opacity = 1
        try: self.update()
        except: pass

        await asyncio.sleep(self.duration_ms / 1000.0)

        if not self.page: return 
        self.top = -100
        self.opacity = 0
        try: self.update()
        except: pass
        
        await asyncio.sleep(0.6)
        try:
            if self in self.app_page.overlay:
                self.app_page.overlay.remove(self)
                self.app_page.update()
        except: pass
        
def play_sound_success(page):
    audio = fta.Audio(src="assets/sounds/sound-success.mp3", autoplay=True)
    if hasattr(page, 'services'): page.services.append(audio)
    else: page.overlay.append(audio) 
        
    async def clean_up_audio():
        await asyncio.sleep(2) 
        try:
            if hasattr(page, 'services') and audio in page.services:
                page.services.remove(audio)
                page.update()
            elif audio in page.overlay:
                page.overlay.remove(audio)
                page.update()
        except: pass
    page.run_task(clean_up_audio)
    
def play_sound_error(page):
    audio = fta.Audio(src="assets/sounds/sound-error.mp3", autoplay=True)
    if hasattr(page, 'services'): page.services.append(audio)
    else: page.overlay.append(audio) 
        
    async def clean_up_audio():
        await asyncio.sleep(2) 
        try:
            if hasattr(page, 'services') and audio in page.services:
                page.services.remove(audio)
                page.update()
            elif audio in page.overlay:
                page.overlay.remove(audio)
                page.update()
        except: pass
    page.run_task(clean_up_audio)

def show_top_notification(page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=None, sound=None):
    notif = TopNotification(page, title, message, duration_ms, color)
    page.overlay.append(notif)
    if sound == "S": play_sound_success(page)
    elif sound == "E": play_sound_error(page)
    page.update()