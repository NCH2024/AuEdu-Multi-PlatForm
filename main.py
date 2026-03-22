import flet as ft
import json

# Import các View
from components.pages.base_dashboard import BaseDashboard
from pages.user.home_page import UserHomePage
from pages.user.attendance_page import AttendancePage
from pages.login_page import LoginPage 
from pages.user.settings_page import SettingsPage
from pages.user.schedule_page import SchedulePage
from pages.user.stats_page import StatsPage
from pages.about_page import AboutPage
from pages.user.profile_page import ProfilePage
from pages.user.news_page import NewsPage
from pages.user.attendance_session_page import AttendanceSessionPage

from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, BG_COLOR

async def main(page: ft.Page):
    page.title = "AuEdu Multi-Platform"
    
    # --- CẤU HÌNH WINDOWS / MAC / MOBILE CHO FLET 0.82.2 ---
    if page.platform == ft.PagePlatform.MACOS:
        # Trên Mac: Ẩn thanh tiêu đề nhưng giữ lại 3 nút đèn giao thông (Apple chuẩn mực)
        page.window.title_bar_style = ft.WindowTitleBarStyle.HIDDEN
    elif page.platform == ft.PagePlatform.WINDOWS:
        # Trên Windows: Ẩn hoàn toàn viền để lát nữa mình tự vẽ thanh Header tuỳ chỉnh
        page.window.title_bar_hidden = True
    
    # Cấu hình thanh Status Bar cho Mobile (em đã làm rất tốt chỗ này)
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
    
    dashboard = BaseDashboard(page)
    
    async def handle_routing(route_str: str):
        try:
            prefs = ft.SharedPreferences()
            session_str = await prefs.get("user_session")
            session = json.loads(session_str) if session_str else None
            
            current_route = route_str if route_str else "/"

            if current_route == "/login":
                page.window.width = 1060
                page.window.height = 700
                page.window.resizable = False
                page.window.maximizable = False
            else:
                page.window.resizable = True
                page.window.maximizable = True

            # CHỐNG LỖI TRẮNG TRANG Ở ĐÂY
            if not session and current_route != "/login":
                await page.push_route("/login")
                return
            
            # Gộp chung "/" và "/login" để ép nhảy vào Home nếu đã đăng nhập
            if session and current_route in ["/login", "/"]:
                await page.push_route("/user/home")
                return

            # Xử lý các màn hình tách biệt khỏi Dashboard (Login, Màn hình quét Camera)
            if current_route == "/login":
                page.views.clear()
                page.views.append(ft.View(route="/login", controls=[LoginPage(page)], padding=0, bgcolor=BG_COLOR))
            
            elif current_route == "/user/attendance/session":
                page.views.clear()
                page.views.append(ft.View(route="/user/attendance/session", controls=[AttendanceSessionPage(page)], padding=0, bgcolor=ft.Colors.BLACK))        
            
            # Xử lý cơ chế thay ruột SPA trong Dashboard
            else:
                if not page.views or page.views[-1].route != "/dashboard_layout":
                    page.views.clear()
                    page.views.append(ft.View(route="/dashboard_layout", controls=[dashboard], padding=0, bgcolor=BG_COLOR))
                    page.update()

                if current_route == "/user/home":
                    dashboard.set_content("TRANG CHỦ", UserHomePage(page), current_route)
                elif current_route == "/user/attendance":
                    dashboard.set_content("ĐIỂM DANH SINH VIÊN", AttendancePage(page), current_route)
                elif current_route == "/user/settings":
                    dashboard.set_content("CÀI ĐẶT PHẦN MỀM", SettingsPage(page), current_route)
                elif current_route == "/user/schedule":
                    dashboard.set_content("LỊCH HỌC / LỊCH THI", SchedulePage(page), current_route)
                elif current_route == "/user/stats":
                    dashboard.set_content("THỐNG KÊ ĐIỂM DANH", StatsPage(page), current_route)
                elif current_route == "/user/about":
                    dashboard.set_content("THÔNG TIN PHẦN MỀM", AboutPage(page), current_route)
                elif current_route == "/user/profile":
                    dashboard.set_content("HỒ SƠ TÀI KHOẢN", ProfilePage(page), current_route)
                elif current_route == "/user/news":
                    dashboard.set_content("THÔNG BÁO", NewsPage(page), current_route)

            page.update()
            
        except Exception as ex:
            print(f"Lỗi routing: {ex}")

    async def route_change(e: ft.RouteChangeEvent): await handle_routing(e.route)
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