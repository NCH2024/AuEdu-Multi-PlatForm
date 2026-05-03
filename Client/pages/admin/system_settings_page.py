"""
Trang Cài Đặt Hệ Thống — Admin Panel (Nâng Cấp v3).
- Cập nhật giá trị Slider thời gian thực (Real-time update).
- Tối ưu hóa hiển thị con số bên cạnh Slider.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
import core.config as client_config

class SystemSettingsPage(ft.Container):
    """Trang quản lý cấu hình hệ thống tập trung dành cho Admin."""

    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0
        self.alignment = ft.Alignment(-1, -1)

        # -- State --
        self.active_index: int = 0
        self.svc = AdminService.instance()
        self.server_env = {}

        # -- UI Controls: Text labels to update on change --
        self.ai_val_text = ft.Text("0.45", size=18, weight=ft.FontWeight.BOLD, color=current_theme.primary)
        self.spoof_val_text = ft.Text("0.15", size=18, weight=ft.FontWeight.BOLD, color=current_theme.primary)
        self.fiqa_val_text = ft.Text("0.05", size=18, weight=ft.FontWeight.BOLD, color=current_theme.primary)

        # -- Tab 0: Kết nối --
        self.local_client_url = ft.Text("Đang tải...", color=current_theme.primary, weight=ft.FontWeight.BOLD, size=16)
        self.local_server_url = ft.Text("Đang tải...", color=current_theme.primary, weight=ft.FontWeight.BOLD, size=16)
        self.local_supabase_url = ft.Text("Đang tải...", color=current_theme.secondary, weight=ft.FontWeight.BOLD, size=14)

        # -- Tab 1: Tham số AI --
        self.global_ai_threshold = ft.Slider(
            min=0.3, max=0.9, divisions=60, label="{value}",
            on_change=lambda e: self._update_slider_val(self.ai_val_text, e.control.value)
        )
        self.global_fiqa_threshold = ft.Slider(
            min=0.0, max=1.0, divisions=100, label="{value}",
            on_change=lambda e: self._update_slider_val(self.fiqa_val_text, e.control.value)
        )
        self.anti_spoof_threshold = ft.Slider(
            min=0.01, max=0.5, divisions=49, label="{value}",
            on_change=lambda e: self._update_slider_val(self.spoof_val_text, e.control.value)
        )
        self.min_face_area = ft.TextField(label="Diện tích mặt tối thiểu (px^2)", border_radius=10, suffix=ft.Text("px²"), text_size=16)

        # -- Tab 2: TTL Cache --
        self.home_cache_ttl = ft.TextField(label="Home Cache TTL (giây)", value="300", border_radius=10, text_size=16)
        self.schedule_cache_ttl = ft.TextField(label="Schedule Cache TTL (giây)", value="21600", border_radius=10, text_size=16)
        self.stats_cache_ttl = ft.TextField(label="Stats Cache TTL (giây)", value="86400", border_radius=10, text_size=16)
        self.session_timeout = ft.TextField(label="Session Timeout (giây)", value="3600", border_radius=10, text_size=16)

        # -- Save Button --
        self.save_btn = ft.Button(
            "LƯU CẤU HÌNH",
            icon=ft.Icons.SAVE_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.save_config,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.Padding.all(20))
        )

        # -- Sidebar --
        self.menu_items = [
            {"icon": ft.Icons.LAN_ROUNDED, "label": "Kết nối Hệ thống"},
            {"icon": ft.Icons.PSYCHOLOGY_ROUNDED, "label": "Tham số AI"},
            {"icon": ft.Icons.TIMER_ROUNDED, "label": "Cache & Phiên"},
        ]
        self.sidebar_column = ft.Column(spacing=15, tight=True)
        self.content_area = ft.Container(expand=True, padding=ft.Padding.all(40))
        self.main_row = ft.Row([
            ft.Container(content=self.sidebar_column, width=280, bgcolor=current_theme.surface_variant, padding=ft.Padding.all(25), border_radius=ft.BorderRadius.only(top_left=12, bottom_left=12)),
            ft.VerticalDivider(width=1, color=current_theme.divider_color),
            self.content_area
        ], expand=True, spacing=0)

        self.content = ft.Column([
            ft.Container(padding=ft.Padding.only(left=30, top=20, right=30), content=ft.Row([ft.Text("CÀI ĐẶT HỆ THỐNG", size=28, weight=ft.FontWeight.BOLD, color=current_theme.text_main), self.save_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)),
            ft.Container(height=10),
            ft.Container(content=self.main_row, expand=True, margin=30, border=ft.Border.all(1, current_theme.divider_color), border_radius=15, bgcolor=current_theme.surface_color)
        ], expand=True)

    def _update_slider_val(self, text_control, val):
        """Cập nhật label text khi slider thay đổi."""
        text_control.value = f"{val:.2f}"
        text_control.update()

    def did_mount(self):
        self.switch_tab(0)
        self.app_page.run_task(self.load_settings)

    def switch_tab(self, index):
        self.active_index = index
        self.render_sidebar()
        self.render_content()
        self.update()

    def render_sidebar(self):
        self.sidebar_column.controls.clear()
        for i, item in enumerate(self.menu_items):
            is_active = (i == self.active_index)
            self.sidebar_column.controls.append(
                ft.Container(
                    content=ft.Row([ft.Icon(item["icon"], color=current_theme.primary if is_active else current_theme.text_muted, size=24), ft.Text(item["label"], size=16, weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL, color=current_theme.primary if is_active else current_theme.text_muted)], spacing=15),
                    padding=ft.Padding.symmetric(horizontal=20, vertical=15), border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.1, current_theme.primary) if is_active else ft.Colors.TRANSPARENT,
                    on_click=lambda e, idx=i: self.switch_tab(idx), ink=True
                )
            )

    def render_content(self):
        if self.active_index == 0: self._render_connection_tab()
        elif self.active_index == 1: self._render_ai_tab()
        elif self.active_index == 2: self._render_cache_tab()

    def _render_connection_tab(self):
        self.content_area.content = ft.Column([
            ft.Text("Kết nối Hệ thống (Cấu hình Cục bộ)", weight=ft.FontWeight.BOLD, size=22, color=current_theme.secondary),
            ft.Text("Thông tin nạp từ file .env. Phần này không thể thay đổi từ xa.", size=14, color=current_theme.text_muted),
            ft.Divider(height=40),
            ft.Container(
                padding=30, bgcolor=ft.Colors.with_opacity(0.05, current_theme.primary), border_radius=15, border=ft.Border.all(1, ft.Colors.with_opacity(0.2, current_theme.primary)),
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.SETTINGS_ETHERNET_ROUNDED, size=24, color=current_theme.primary), ft.Text("TRẠNG THÁI KẾT NỐI HIỆN TẠI", weight=ft.FontWeight.BOLD, size=18, color=current_theme.primary)]),
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    ft.Row([ft.Text("Địa chỉ Server API:", width=220, size=16), self.local_client_url]),
                    ft.Row([ft.Text("Trạng thái Server:", width=220, size=16), self.local_server_url]),
                    ft.Row([ft.Text("Supabase Project URL:", width=220, size=16), self.local_supabase_url]),
                    ft.Divider(height=20),
                    ft.Text("💡 Lưu ý: Cập nhật file .env trên máy chủ để thay đổi các thông số này.", size=13, italic=True, color=current_theme.text_muted)
                ], spacing=15)
            ),
        ], scroll=ft.ScrollMode.AUTO, spacing=20)

    def _render_ai_tab(self):
        self.content_area.content = ft.Column([
            ft.Text("Tham số AI & Hướng dẫn Cấu hình", weight=ft.FontWeight.BOLD, size=22, color=current_theme.secondary),
            ft.Text("Điều chỉnh độ nhạy của hệ thống nhận diện và chống giả mạo.", size=14, color=current_theme.text_muted),
            ft.Divider(height=40),
            ft.Row([
                ft.Column([
                    ft.Text("1. Ngưỡng nhận diện (Similarity):", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row([self.global_ai_threshold, self.ai_val_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text("2. Ngưỡng chống giả mạo (Anti-Spoof):", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row([self.anti_spoof_threshold, self.spoof_val_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text("3. Ngưỡng chất lượng ảnh (FIQA):", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row([self.global_fiqa_threshold, self.fiqa_val_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.min_face_area,
                ], expand=3, spacing=25),
                ft.VerticalDivider(width=40),
                ft.Container(
                    expand=2, padding=25, bgcolor=current_theme.surface_variant, border_radius=15,
                    content=ft.Column([
                        ft.Text("💡 HƯỚNG DẪN CẤU HÌNH", weight=ft.FontWeight.BOLD, size=16), ft.Divider(),
                        ft.Text("• Chống giả mạo (Anti-Spoof):", weight=ft.FontWeight.BOLD, size=13),
                        ft.Text("   - Thấp (0.05 - 0.1): Rất gắt, dễ chặn cả mặt thật.", size=12),
                        ft.Text("   - Chuẩn (0.15): Cân bằng tốt nhất.", size=12),
                        ft.Text("   - Cao (0.25+): Dễ bị vượt qua bởi điện thoại.", size=12),
                        ft.Text("\n• Nhận diện (Cosine):", weight=ft.FontWeight.BOLD, size=13),
                        ft.Text("   - 0.4 - 0.45: Mặc định chuẩn.", size=12),
                        ft.Text("   - > 0.5: Dễ nhận nhầm người khác.", size=12),
                        ft.Text("\n• Chất lượng (FIQA):", weight=ft.FontWeight.BOLD, size=13),
                        ft.Text("   - Khuyến nghị 0.05 để đảm bảo tốc độ.", size=12),
                    ], spacing=5)
                )
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        ], scroll=ft.ScrollMode.AUTO, spacing=20)

    def _render_cache_tab(self):
        self.content_area.content = ft.Column([
            ft.Text("Quản lý Cache & Phiên", weight=ft.FontWeight.BOLD, size=22, color=current_theme.secondary),
            ft.Text("Cấu hình thời gian lưu trữ dữ liệu tạm thời trên ứng dụng.", size=14, color=current_theme.text_muted),
            ft.Divider(height=40),
            ft.Row([
                ft.Column([self.home_cache_ttl, self.schedule_cache_ttl, self.stats_cache_ttl, ft.Divider(height=20), self.session_timeout], expand=3, spacing=25),
                ft.VerticalDivider(width=40),
                ft.Container(
                    expand=2, padding=25, bgcolor=current_theme.surface_variant, border_radius=15,
                    content=ft.Column([
                        ft.Text("💡 GỢI Ý GIÁ TRỊ CACHE (TTL)", weight=ft.FontWeight.BOLD, size=16), ft.Divider(),
                        ft.Text("• Home Cache (300s): Giảm tải Server.", size=12),
                        ft.Text("\n• Schedule Cache (21600s): Nên để thời gian dài.", size=12),
                        ft.Text("\n• Stats Cache (86400s): Nên để 1 ngày.", size=12),
                    ], spacing=5)
                )
            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
        ], scroll=ft.ScrollMode.AUTO, spacing=25)

    async def load_settings(self):
        try:
            self.local_client_url.value = client_config.SERVER_API_URL
            self.local_supabase_url.value = client_config.SUPABASE_URL
            self.server_env = await self.svc.get_server_env()
            self.local_server_url.value = self.server_env.get("server_status", "Không rõ") + " (Server Online)"
            configs = await self.svc.get_all_configs()
            config_map = {item["key"]: item["value"] for item in configs}

            self.global_ai_threshold.value = float(config_map.get("ai_threshold", 0.45))
            self.ai_val_text.value = f"{self.global_ai_threshold.value:.2f}"

            self.global_fiqa_threshold.value = float(config_map.get("fiqa_threshold", 0.05))
            self.fiqa_val_text.value = f"{self.global_fiqa_threshold.value:.2f}"

            self.anti_spoof_threshold.value = float(config_map.get("anti_spoof_threshold", 0.15))
            self.spoof_val_text.value = f"{self.anti_spoof_threshold.value:.2f}"

            self.min_face_area.value = str(config_map.get("min_face_area", "900"))
            self.home_cache_ttl.value = str(config_map.get("home_cache_ttl", "300"))
            self.schedule_cache_ttl.value = str(config_map.get("schedule_cache_ttl", "21600"))
            self.stats_cache_ttl.value = str(config_map.get("stats_cache_ttl", "86400"))
            self.session_timeout.value = str(config_map.get("session_timeout", "3600"))

            self.switch_tab(self.active_index)
        except Exception as e:
            print(f"[SystemSettings] Lỗi load settings: {e}")

    async def save_config(self, e):
        try:
            configs = [
                {"key": "ai_threshold", "value": str(self.global_ai_threshold.value)},
                {"key": "fiqa_threshold", "value": str(self.global_fiqa_threshold.value)},
                {"key": "anti_spoof_threshold", "value": str(self.anti_spoof_threshold.value)},
                {"key": "min_face_area", "value": self.min_face_area.value},
                {"key": "home_cache_ttl", "value": self.home_cache_ttl.value},
                {"key": "schedule_cache_ttl", "value": self.schedule_cache_ttl.value},
                {"key": "stats_cache_ttl", "value": self.stats_cache_ttl.value},
                {"key": "session_timeout", "value": self.session_timeout.value},
            ]
            await self.svc.save_configs_batch(configs)
            show_top_notification(self.app_page, "Thông báo", "Đã cập nhật cấu hình hệ thống thành công!", ft.Colors.GREEN, sound="S")
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", f"Không thể lưu cấu hình: {ex}", ft.Colors.RED, sound="E")

    def apply_theme(self): self.switch_tab(self.active_index)
