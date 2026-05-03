"""
Trang Cài Đặt Hệ Thống — Admin Panel.
Quản lý tập trung toàn bộ cấu hình:
  - Kết nối hệ thống (API URL, Supabase)
  - Tham số AI nhận diện (threshold, FIQA)
  - TTL Cache cho Client (home, schedule, stats)
  - Cài đặt phiên làm việc (session timeout)
  - Nhật ký hoạt động (Audit Log)
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService


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

        # -- Tab 0: Kết nối --
        self.base_api_url = ft.TextField(label="Base API URL (server_api_url)", hint_text="http://localhost:8000", border_radius=10)
        self.supabase_url = ft.TextField(label="Supabase URL", border_radius=10)
        self.supabase_key = ft.TextField(label="Supabase Key", password=True, can_reveal_password=True, border_radius=10)
        self.supabase_bucket = ft.TextField(label="Supabase Bucket Name", hint_text="auedu-bucket", border_radius=10)

        # -- Tab 1: Tham số AI --
        self.global_ai_threshold = ft.Slider(min=0.3, max=0.9, divisions=60, label="{value}")
        self.global_fiqa_threshold = ft.Slider(min=0, max=100, divisions=100, label="{value}")

        # -- Tab 2: TTL Cache --
        self.home_cache_ttl = ft.TextField(label="Home Cache TTL (giây)", value="300", border_radius=10, text_size=13)
        self.schedule_cache_ttl = ft.TextField(label="Schedule Cache TTL (giây)", value="21600", border_radius=10, text_size=13)
        self.stats_cache_ttl = ft.TextField(label="Stats Cache TTL (giây)", value="86400", border_radius=10, text_size=13)
        self.session_timeout = ft.TextField(label="Session Timeout (giây)", value="3600", border_radius=10, text_size=13)

        # -- Tab 3: Nhật ký --
        self.audit_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Thời gian", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Người dùng", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Hành động", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Chi tiết", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            heading_row_color=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=8,
        )

        # -- Save Button --
        self.save_btn = ft.Button(
            "LƯU CẤU HÌNH",
            icon=ft.Icons.SAVE_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=self.save_config,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=ft.Padding.all(15))
        )

        # -- Sidebar Menu --
        self.menu_items = [
            {"icon": ft.Icons.LAN_ROUNDED, "label": "Kết nối Hệ thống"},
            {"icon": ft.Icons.PSYCHOLOGY_ROUNDED, "label": "Tham số AI"},
            {"icon": ft.Icons.TIMER_ROUNDED, "label": "Cache & Phiên"},
            {"icon": ft.Icons.HISTORY_ROUNDED, "label": "Nhật ký Hoạt động"},
        ]

        self.sidebar_column = ft.Column(spacing=10, tight=True)
        self.content_area = ft.Container(expand=True, padding=30)

        self.main_row = ft.Row([
            ft.Container(
                content=self.sidebar_column, width=250,
                bgcolor=current_theme.surface_variant,
                padding=ft.Padding.all(20),
                border_radius=ft.BorderRadius.only(top_left=12, bottom_left=12)
            ),
            ft.VerticalDivider(width=1, color=current_theme.divider_color),
            self.content_area
        ], expand=True, spacing=0)

        header_container = ft.Container(
            padding=ft.Padding.only(left=20, top=10, right=20),
            content=ft.Row([
                ft.Text("CÀI ĐẶT HỆ THỐNG", size=24, weight=ft.FontWeight.BOLD, color=current_theme.text_main),
                self.save_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )

        self.content = ft.Column([
            header_container,
            ft.Container(height=10),
            ft.Container(
                content=self.main_row, expand=True, margin=20,
                border=ft.Border.all(1, current_theme.divider_color),
                border_radius=12, bgcolor=current_theme.surface_color,
            )
        ], expand=True)

    # ─── Lifecycle ────────────────────────────────────────────────

    def did_mount(self):
        """Kích hoạt render sidebar và tải cấu hình."""
        self.switch_tab(0)
        self.app_page.run_task(self.load_settings)
        self.app_page.run_task(self.load_audit_logs)

    # ─── Sidebar & Content Rendering ──────────────────────────────

    def switch_tab(self, index):
        """Chuyển tab sidebar và render lại nội dung tương ứng."""
        self.active_index = index
        self.render_sidebar()
        self.render_content()
        self.update()

    def render_sidebar(self):
        """Render danh sách menu sidebar với highlight tab đang chọn."""
        self.sidebar_column.controls.clear()
        for i, item in enumerate(self.menu_items):
            is_active = (i == self.active_index)
            self.sidebar_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(item["icon"],
                                color=current_theme.primary if is_active else current_theme.text_muted,
                                size=20),
                        ft.Text(item["label"],
                                weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                                color=current_theme.primary if is_active else current_theme.text_muted)
                    ], spacing=10),
                    padding=ft.Padding.symmetric(horizontal=15, vertical=12),
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.1, current_theme.primary) if is_active else ft.Colors.TRANSPARENT,
                    on_click=lambda e, idx=i: self.switch_tab(idx),
                    ink=True
                )
            )

    def render_content(self):
        """Render nội dung chính theo tab đang chọn."""
        if self.active_index == 0:
            self._render_connection_tab()
        elif self.active_index == 1:
            self._render_ai_tab()
        elif self.active_index == 2:
            self._render_cache_tab()
        elif self.active_index == 3:
            self._render_audit_tab()

    def _render_connection_tab(self):
        """Tab Kết nối Hệ thống: cấu hình API URL và Supabase."""
        self.content_area.content = ft.Column([
            ft.Text("Cấu hình Endpoint & Cloud", weight=ft.FontWeight.BOLD, size=18, color=current_theme.secondary),
            ft.Text("Thiết lập địa chỉ API Server và thông tin kết nối Supabase Cloud.", size=13, color=current_theme.text_muted),
            ft.Container(height=10),
            self.base_api_url,
            ft.Divider(height=30),
            ft.Text("Supabase Cloud Storage", weight=ft.FontWeight.BOLD, size=16),
            self.supabase_url,
            self.supabase_key,
            self.supabase_bucket,
        ], scroll=ft.ScrollMode.AUTO, spacing=15)

    def _render_ai_tab(self):
        """Tab Tham số AI: ngưỡng nhận diện và chất lượng ảnh."""
        self.content_area.content = ft.Column([
            ft.Text("Tham số AI Nhận diện", weight=ft.FontWeight.BOLD, size=18, color=current_theme.secondary),
            ft.Text("Điều chỉnh các ngưỡng tin cậy để tối ưu hóa độ chính xác của hệ thống.", size=13, color=current_theme.text_muted),
            ft.Container(height=10),
            ft.Text("Ngưỡng tin cậy nhận diện (Cosine Similarity):", weight=ft.FontWeight.BOLD),
            ft.Row([
                self.global_ai_threshold,
                ft.Text(f"{self.global_ai_threshold.value}", weight=ft.FontWeight.BOLD, color=current_theme.primary)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=30),
            ft.Text("Ngưỡng chất lượng ảnh (FIQA):", weight=ft.FontWeight.BOLD),
            ft.Row([
                self.global_fiqa_threshold,
                ft.Text(f"{self.global_fiqa_threshold.value}", weight=ft.FontWeight.BOLD, color=current_theme.primary)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Container(
                padding=ft.Padding.all(15), bgcolor=current_theme.surface_variant, border_radius=10,
                content=ft.Text("Lưu ý: Các thay đổi này sẽ áp dụng toàn cục cho tất cả các thiết bị đang kết nối.", size=12, italic=True)
            )
        ], scroll=ft.ScrollMode.AUTO, spacing=15)

    def _render_cache_tab(self):
        """Tab Cache & Phiên: quản lý TTL cache và session timeout."""
        self.content_area.content = ft.Column([
            ft.Text("Quản lý Cache & Phiên Làm Việc", weight=ft.FontWeight.BOLD, size=18, color=current_theme.secondary),
            ft.Text("Cấu hình thời gian sống (TTL) của cache trên Client và thời gian phiên đăng nhập.", size=13, color=current_theme.text_muted),
            ft.Container(height=10),
            ft.Text("Cache TTL (Time-To-Live)", weight=ft.FontWeight.BOLD, size=16),
            self.home_cache_ttl,
            self.schedule_cache_ttl,
            self.stats_cache_ttl,
            ft.Divider(height=30),
            ft.Text("Quản lý Phiên", weight=ft.FontWeight.BOLD, size=16),
            self.session_timeout,
            ft.Container(height=10),
            ft.Container(
                padding=ft.Padding.all(15), bgcolor=current_theme.surface_variant, border_radius=10,
                content=ft.Column([
                    ft.Text("💡 Gợi ý giá trị TTL:", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text("• Home: 300 giây (5 phút) — cân bằng UX và dữ liệu mới", size=11, color=current_theme.text_muted),
                    ft.Text("• Schedule: 21600 giây (6 giờ) — dữ liệu ít thay đổi", size=11, color=current_theme.text_muted),
                    ft.Text("• Stats: 86400 giây (24 giờ) — dữ liệu nặng, ít cập nhật", size=11, color=current_theme.text_muted),
                    ft.Text("• Session: 3600 giây (1 giờ) — auto-logout sau 1 giờ", size=11, color=current_theme.text_muted),
                ], spacing=4)
            )
        ], scroll=ft.ScrollMode.AUTO, spacing=15)

    def _render_audit_tab(self):
        """Tab Nhật ký Hoạt động: hiển thị audit logs gần nhất."""
        self.content_area.content = ft.Column([
            ft.Row([
                ft.Text("Nhật ký Hoạt động", weight=ft.FontWeight.BOLD, size=18, color=current_theme.secondary),
                ft.IconButton(ft.Icons.REFRESH_ROUNDED, on_click=lambda e: self.app_page.run_task(self.load_audit_logs))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text("Theo dõi các hành động quan trọng đã thực hiện trên hệ thống.", size=13, color=current_theme.text_muted),
            ft.Container(height=10),
            ft.Row([self.audit_table], scroll=ft.ScrollMode.AUTO, expand=True)
        ], spacing=15)

    # ─── Data Loading ─────────────────────────────────────────────

    async def load_settings(self):
        """Tải cấu hình từ AdminService và phân phối vào các form field."""
        try:
            configs = await self.svc.get_all_configs()
            config_map = {item["key"]: item["value"] for item in configs}

            # Tab 0: Kết nối
            self.base_api_url.value = config_map.get("server_api_url", "")
            self.supabase_url.value = config_map.get("supabase_url", "")
            self.supabase_key.value = config_map.get("supabase_key", "")
            self.supabase_bucket.value = config_map.get("supabase_bucket", "")

            # Tab 1: AI
            self.global_ai_threshold.value = float(config_map.get("ai_threshold", 0.6))
            self.global_fiqa_threshold.value = float(config_map.get("fiqa_threshold", 30))

            # Tab 2: Cache & Phiên
            self.home_cache_ttl.value = str(config_map.get("home_cache_ttl", "300"))
            self.schedule_cache_ttl.value = str(config_map.get("schedule_cache_ttl", "21600"))
            self.stats_cache_ttl.value = str(config_map.get("stats_cache_ttl", "86400"))
            self.session_timeout.value = str(config_map.get("session_timeout", "3600"))

            self.switch_tab(self.active_index)
        except Exception as e:
            print(f"[SystemSettings] Lỗi load settings: {e}")

    async def load_audit_logs(self):
        """Tải nhật ký hoạt động từ AdminService."""
        try:
            logs = await self.svc.get_audit_logs()
            self.audit_table.rows.clear()
            for log in logs:
                action = log.get("action", "N/A")
                action_color = ft.Colors.BLUE if action == "LOGIN" else ft.Colors.GREEN
                self.audit_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(log.get("time", "N/A"))),
                        ft.DataCell(ft.Text(log.get("user", "N/A"))),
                        ft.DataCell(
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                border_radius=6,
                                bgcolor=ft.Colors.with_opacity(0.1, action_color),
                                content=ft.Text(action, size=12, weight=ft.FontWeight.BOLD, color=action_color)
                            )
                        ),
                        ft.DataCell(ft.Text(log.get("details", "N/A"), width=300)),
                    ])
                )
            if self.active_index == 3:
                self.render_content()
                self.update()
        except Exception as e:
            print(f"[SystemSettings] Lỗi load audit: {e}")

    # ─── Save ─────────────────────────────────────────────────────

    async def save_config(self, e):
        """Lưu toàn bộ cấu hình qua AdminService.save_configs_batch()."""
        try:
            configs = [
                # Kết nối
                {"key": "server_api_url", "value": self.base_api_url.value},
                {"key": "supabase_url", "value": self.supabase_url.value},
                {"key": "supabase_key", "value": self.supabase_key.value},
                {"key": "supabase_bucket", "value": self.supabase_bucket.value},
                # AI
                {"key": "ai_threshold", "value": str(self.global_ai_threshold.value)},
                {"key": "fiqa_threshold", "value": str(self.global_fiqa_threshold.value)},
                # Cache & Phiên
                {"key": "home_cache_ttl", "value": self.home_cache_ttl.value},
                {"key": "schedule_cache_ttl", "value": self.schedule_cache_ttl.value},
                {"key": "stats_cache_ttl", "value": self.stats_cache_ttl.value},
                {"key": "session_timeout", "value": self.session_timeout.value},
            ]
            await self.svc.save_configs_batch(configs)
            show_top_notification(self.app_page, "Thông báo", "Đã cập nhật cấu hình hệ thống thành công!", ft.Colors.GREEN, sound="S")
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", f"Không thể lưu cấu hình: {ex}", ft.Colors.RED, sound="E")

    def apply_theme(self):
        """Cập nhật giao diện khi đổi theme."""
        self.switch_tab(self.active_index)
