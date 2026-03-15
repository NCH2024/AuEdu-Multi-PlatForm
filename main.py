import flet as ft
from pages.user.home_page import UserHomePage
from pages.user.attendance_page import AttendancePage
from pages.user.login_page import LoginPage 
from pages.user.settings_page import SettingsPage
from pages.user.schedule_page import SchedulePage
from pages.user.stats_page import StatsPage
from core.theme import PRIMARY_COLOR

async def main(page: ft.Page):
    page.title = "AuEdu Multi-Platform"
    
    page.theme = ft.Theme(
        system_overlay_style=ft.SystemOverlayStyle(
            # Nhuộm màu nền thanh trạng thái thành màu xanh chủ đạo
            status_bar_color= PRIMARY_COLOR, 
            
            # Ép các icon (pin, wifi, giờ) thành màu sáng (Trắng) để nổi bật trên nền xanh
            status_bar_icon_brightness=ft.Brightness.LIGHT, 
            
            # (Tùy chọn) Nhuộm luôn thanh điều hướng vuốt hất lên ở dưới đáy màn hình
            system_navigation_bar_color=ft.Colors.TRANSPARENT,
            system_navigation_bar_icon_brightness=ft.Brightness.DARK
        )
    )
    
    page.theme_mode = ft.ThemeMode.LIGHT 
    page.padding = 0 
    
    # TÁCH LÕI LOGIC: Hàm này chịu trách nhiệm kiểm tra session và vẽ UI
    async def handle_routing(route_str: str):
        try:
            session = page.session.store.get("user_session")
            current_route = route_str if route_str else "/"

            # Rào chắn An ninh
            if not session and current_route != "/login":
                await page.push_route("/login")
                return
            if session and current_route == "/login":
                await page.push_route("/user/home")
                return

            # Xóa màn hình cũ
            page.views.clear()

            # Luôn lót nền Home nếu đã đăng nhập (chống văng app trên mobile)
            if session:
                page.views.append(ft.View(route="/user/home", controls=[UserHomePage(page)], padding=0))

            # Phân nhánh vẽ màn hình
            if current_route == "/login":
                page.views.append(ft.View(route="/login", controls=[LoginPage(page)], padding=0))
                
            elif current_route != "/user/home" and current_route != "/":
                if current_route == "/user/attendance":
                    page.views.append(ft.View(route="/user/attendance", controls=[AttendancePage(page)], padding=0))
                
                elif current_route == "/user/settings":
                    page.views.append(ft.View(route="/user/settings", controls=[SettingsPage(page)], padding=0))
                
                elif current_route == "/user/schedule":
                    page.views.append(ft.View(route="/user/schedule", controls=[SchedulePage(page)], padding=0))
                    
                elif current_route == "/user/stats":
                    page.views.append(ft.View(route="/user/stats", controls=[StatsPage(page)], padding=0))         
         

            page.update()
            
        except Exception as ex:
            print(f"Lỗi routing: {ex}")

    # Bắt sự kiện khi người dùng chủ động chuyển trang
    async def route_change(e: ft.RouteChangeEvent): 
        await handle_routing(e.route)

    # Bắt sự kiện khi người dùng bấm nút Back cứng trên Mobile
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