import flet as ft
import json
from pages.user.home_page import UserHomePage
from pages.user.attendance_page import AttendancePage
from pages.login_page import LoginPage 
from pages.user.settings_page import SettingsPage
from pages.user.schedule_page import SchedulePage
from pages.user.stats_page import StatsPage
from pages.about_page import AboutPage
from pages.user.attendance_session_page import AttendanceSessionPage
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, BG_COLOR

async def main(page: ft.Page):
    page.title = "AuEdu Multi-Platform"
    
    # Bật tính năng tràn viền và màu nền chung
    page.theme = ft.Theme(
        system_overlay_style=ft.SystemOverlayStyle(
            status_bar_color=ft.Colors.TRANSPARENT, 
            status_bar_icon_brightness=ft.Brightness.DARK, 
            system_navigation_bar_color=ft.Colors.TRANSPARENT,
            system_navigation_bar_icon_brightness=ft.Brightness.DARK
        )
    )
    
    page.theme_mode = ft.ThemeMode.LIGHT 
    page.padding = 0 
    page.bgcolor = BG_COLOR
    
    async def handle_routing(route_str: str):
        try:
            # KẾT HỢP CHUẨN: SharedPreferences + JSON
            prefs = ft.SharedPreferences()
            session_str = await prefs.get("user_session")
            session = json.loads(session_str) if session_str else None
            
            current_route = route_str if route_str else "/"
            
            

            if current_route == "/login":
                # Kích thước form đăng nhập
                page.window.width = 1060
                page.window.height = 700
                page.window.resizable = False
                page.window.maximizable = False

            # Rào chắn An ninh
            if not session and current_route != "/login":
                await page.push_route("/login")
                return
            if session and current_route == "/login":
                await page.push_route("/user/home")
                return

            page.views.clear()

            # Luôn lót nền Home nếu đã đăng nhập (chống văng app trên mobile)
            if session:
                page.views.append(ft.View(route="/user/home", controls=[UserHomePage(page)], padding=0, bgcolor=BG_COLOR))

            # Phân nhánh vẽ màn hình
            if current_route == "/login":
                page.views.append(ft.View(route="/login", controls=[LoginPage(page)], padding=0, bgcolor=BG_COLOR))
                
            elif current_route != "/user/home" and current_route != "/":
                if current_route == "/user/attendance":
                    page.views.append(ft.View(route="/user/attendance", controls=[AttendancePage(page)], padding=0, bgcolor=BG_COLOR))
                
                elif current_route == "/user/settings":
                    page.views.append(ft.View(route="/user/settings", controls=[SettingsPage(page)], padding=0, bgcolor=BG_COLOR))
                
                elif current_route == "/user/schedule":
                    page.views.append(ft.View(route="/user/schedule", controls=[SchedulePage(page)], padding=0, bgcolor=BG_COLOR))
                    
                elif current_route == "/user/stats":
                    page.views.append(ft.View(route="/user/stats", controls=[StatsPage(page)], padding=0, bgcolor=BG_COLOR)) 
                    
                elif current_route == "/user/about":
                    page.views.append(ft.View(route="/user/about", controls=[AboutPage(page)], padding=0, bgcolor=BG_COLOR)) 
                    
                elif current_route == "/user/attendance/session":
                    page.views.append(ft.View(route="/user/attendance/session", controls=[AttendanceSessionPage(page)], padding=0, bgcolor=ft.Colors.BLACK))        
         
            page.update()
            
        except Exception as ex:
            print(f"Lỗi routing: {ex}")

    async def route_change(e: ft.RouteChangeEvent): 
        await handle_routing(e.route)

    async def view_pop(e: ft.ViewPopEvent): 
        page.views.pop() 
        if len(page.views) > 0:
            top_view = page.views[-1]
            await page.push_route(top_view.route) 

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    await handle_routing(page.route)

if __name__ == "__main__":
    ft.run(main)