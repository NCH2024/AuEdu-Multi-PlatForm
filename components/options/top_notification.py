import flet as ft
import flet_audio as fta
import asyncio
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR

class TopNotification(ft.Container):
    def __init__(self, page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=SECONDARY_COLOR):
        super().__init__()
        self.app_page = page
        self.top = -100 
        self.left = 0
        self.right = 0
        
        self.animate_position = ft.Animation(duration=500, curve=ft.AnimationCurve.EASE_OUT_BACK)
        self.animate_opacity = ft.Animation(duration=400, curve=ft.AnimationCurve.EASE_IN_OUT)
        self.opacity = 0
        self.duration_ms = duration_ms

        noti_width = (self.app_page.width - 40) if (self.app_page.width and self.app_page.width < 450) else 400

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=noti_width,
                    padding=15,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=15,
                    border=ft.Border(left=ft.BorderSide(6, color)),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK), offset=ft.Offset(0, 5)),
                    content=ft.Row(
                        spacing=15,
                        controls=[
                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, color=color, size=24),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87, size=14),
                                    ft.Text(message, color=ft.Colors.GREY_700, size=12)
                                ]
                            )
                        ]
                    )
                )
            ]
        )

    def did_mount(self):
        self.app_page.run_task(self.show_and_hide)

    async def show_and_hide(self):
        await asyncio.sleep(0.1)
        if not self.page: return 
        self.top = 20
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
    
    if hasattr(page, 'services'):
        page.services.append(audio)
    else:
        page.overlay.append(audio) 
        
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
    
    if hasattr(page, 'services'):
        page.services.append(audio)
    else:
        page.overlay.append(audio) 
        
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

def show_top_notification(page: ft.Page, title: str, message: str, duration_ms: int = 3000, color=SECONDARY_COLOR, sound=None):
    notif = TopNotification(page, title, message, duration_ms, color)
    page.overlay.append(notif)
    
    if sound == "S":
        play_sound_success(page)
    elif sound == "E":
        play_sound_error(page)
        
    page.update()