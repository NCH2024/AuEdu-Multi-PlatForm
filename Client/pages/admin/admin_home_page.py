import flet as ft
import json
import time
import asyncio
import datetime
import random
from core.helper import safe_json_load
from components.options.top_notification import show_top_notification
from core.theme import current_theme
from core.config import get_supabase_client

class AdminHomePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(0)

        self.admin_name = "Quản trị viên"
        self.stats_data = {}
        self.audit_logs = []
        self.is_loading = True

        self._name_text = None

        self.content = self.build_ui()
        self.app_page.run_task(self.load_data)

    def apply_theme(self):
        self.content = self.build_ui()
        if self.page:
            self.update()

    def create_skeleton(self, width=None, height=20, expand=False, is_circle=False, border_radius=4):
        return ft.Container(
            width=width, height=height, expand=expand,
            bgcolor=current_theme.divider_color,
            border_radius=height / 2 if is_circle else border_radius
        )

    def make_pro_card(self, content, padding=ft.Padding.all(20), ink=False, on_click=None):
        return ft.Container(
            content=content, padding=padding, border_radius=12,
            bgcolor=current_theme.surface_color,
            border=ft.Border.all(1, current_theme.divider_color),
            ink=ink, on_click=on_click
        )

    def _build_audit_table(self):
        if self.is_loading:
            return ft.Container(
                padding=20, 
                content=ft.Column([
                    self.create_skeleton(height=40),
                    self.create_skeleton(height=40),
                    self.create_skeleton(height=40)
                ], spacing=10)
            )

        rows = []
        for log in self.audit_logs:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(log.get("time", "N/A"), color=current_theme.text_main)),
                        ft.DataCell(ft.Text(log.get("user", "N/A"), color=current_theme.text_main)),
                        ft.DataCell(
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                border_radius=6,
                                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLUE if log.get("action") == "LOGIN" else ft.Colors.GREEN),
                                content=ft.Text(log.get("action", "N/A"), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE if log.get("action") == "LOGIN" else ft.Colors.GREEN)
                            )
                        ),
                        ft.DataCell(ft.Text(log.get("details", "N/A"), color=current_theme.text_muted)),
                    ]
                )
            )

        if not rows:
            return ft.Container(
                padding=20, alignment=ft.Alignment(0, 0),
                content=ft.Text("Chưa có nhật ký hoạt động nào.", color=current_theme.text_muted, italic=True)
            )

        audit_table = ft.DataTable(
            expand=True,
            columns=[
                ft.DataColumn(ft.Text("THỜI GIAN", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("NGƯỜI DÙNG", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("HÀNH ĐỘNG", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("CHI TIẾT", color=current_theme.text_muted, weight=ft.FontWeight.BOLD, size=12)),
            ],
            rows=rows,
            heading_row_height=40,
            data_row_max_height=50,
            column_spacing=40,
            horizontal_margin=20,
            divider_thickness=1,
            heading_row_color=current_theme.surface_variant,
            border=ft.Border.all(1, current_theme.divider_color),
            border_radius=8,
        )

        return ft.Container(
            padding=ft.Padding(20, 10, 20, 20),
            content=ft.Row([audit_table], scroll=ft.ScrollMode.AUTO)
        )

    def build_ui(self):
        now = datetime.datetime.now()
        greeting = "Chào buổi sáng" if now.hour < 12 else "Chào buổi chiều" if now.hour < 18 else "Chào buổi tối"

        self._name_text = ft.Text(f"QTV. {self.admin_name}", size=24, weight=ft.FontWeight.W_800, color=current_theme.text_main)
        greeting_text = ft.Text(f"{greeting},", size=14, color=current_theme.text_muted, weight=ft.FontWeight.W_500)
        date_text = ft.Text(f"Hôm nay là {now.strftime('%d/%m/%Y')} • Hệ thống đang hoạt động ổn định!", size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_500)
        
        shield_icon = ft.Container(padding=ft.Padding.all(10), border_radius=12, bgcolor=current_theme.surface_variant, content=ft.Icon(ft.Icons.SECURITY_ROUNDED, color=current_theme.secondary, size=24))
        header_section = ft.Row([
            ft.Column([greeting_text, self._name_text, date_text], spacing=0, expand=True),
            shield_icon
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        def create_stat_card(icon, title, value, color_theme, route):
            return ft.Container(
                col={"xs": 6, "sm": 6, "md": 3, "lg": 3},
                content=self.make_pro_card(
                    padding=ft.Padding.all(15), ink=True,
                    on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r),
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                width=36, height=36, border_radius=10,
                                bgcolor=ft.Colors.with_opacity(0.1, color_theme),
                                content=ft.Icon(icon, color=color_theme, size=18),
                                alignment=ft.Alignment(0, 0)
                            ),
                            ft.Text(
                                str(value) if not self.is_loading else "...",
                                size=22, weight=ft.FontWeight.BOLD, color=current_theme.text_main,
                                expand=True, text_align=ft.TextAlign.RIGHT
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=5),
                        ft.Text(title, size=12, color=current_theme.text_muted, weight=ft.FontWeight.W_600)
                    ], spacing=0)
                )
            )

        total_users = self.stats_data.get("total_users", 0)
        total_classes = self.stats_data.get("total_classes", 0)
        today_att = self.stats_data.get("today_att", 0)
        sys_load = self.stats_data.get("sys_load", "0%")

        stats_row = ft.ResponsiveRow([
            create_stat_card(ft.Icons.PEOPLE_ALT_ROUNDED, "Tổng số người dùng", total_users, current_theme.primary, "/admin/users"),
            create_stat_card(ft.Icons.CLASS_ROUNDED, "Số lớp học kì này", total_classes, ft.Colors.ORANGE_500, "/admin/reports"),
            create_stat_card(ft.Icons.CHECK_CIRCLE_ROUNDED, "Lượt điểm danh hôm nay", today_att, ft.Colors.GREEN_500, "/admin/reports"),
            create_stat_card(ft.Icons.SPEED_ROUNDED, "Tải hệ thống", sys_load, ft.Colors.RED_400, "/admin/settings"),
        ], run_spacing=5, spacing=5)

        audit_section = self.make_pro_card(
            padding=0,
            content=ft.Column([
                ft.Container(
                    padding=ft.Padding(20, 20, 20, 5),
                    content=ft.Row([
                        ft.Icon(ft.Icons.HISTORY_ROUNDED, color=current_theme.secondary, size=20),
                        ft.Text("NHẬT KÝ HOẠT ĐỘNG GẦN ĐÂY", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=14)
                    ])
                ),
                self._build_audit_table()
            ], spacing=0)
        )

        def create_action_btn(icon, text, bg_color, text_color, route):
            return ft.Container(
                col={"xs": 6, "sm": 6, "md": 6, "lg": 6},
                content=ft.Container(
                    padding=ft.Padding.all(15), border_radius=12, bgcolor=bg_color, ink=True,
                    on_click=lambda e, r=route: self.app_page.run_task(self.app_page.push_route, r),
                    border=ft.Border.all(1, current_theme.divider_color) if bg_color == current_theme.surface_color else None,
                    content=ft.Column([
                        ft.Icon(icon, color=text_color, size=28),
                        ft.Text(text, color=text_color, weight=ft.FontWeight.W_700, size=13)
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.START)
                )
            )

        quick_actions_section = self.make_pro_card(ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.BOLT_ROUNDED, color=ft.Colors.AMBER_500, size=20),
                ft.Text("TRUY CẬP NHANH", weight=ft.FontWeight.BOLD, color=current_theme.text_main, size=14)
            ]),
            ft.Container(height=5),
            ft.ResponsiveRow([
                create_action_btn(ft.Icons.BUSINESS_ROUNDED, "Quản lý Khoa", current_theme.secondary, ft.Colors.WHITE, "/admin/departments"),
                create_action_btn(ft.Icons.DATE_RANGE_ROUNDED, "Quản lý Học kỳ", current_theme.secondary, ft.Colors.WHITE, "/admin/semesters"),
                create_action_btn(ft.Icons.CLASS_ROUNDED, "Quản lý Lớp", current_theme.surface_color, current_theme.secondary, "/admin/classes"),
                create_action_btn(ft.Icons.BOOK_ROUNDED, "Quản lý Môn", current_theme.surface_color, current_theme.secondary, "/admin/subjects"),
                create_action_btn(ft.Icons.PEOPLE_ROUNDED, "Quản lý Sinh viên", current_theme.surface_color, current_theme.secondary, "/admin/students"),
                create_action_btn(ft.Icons.SCHEDULE_ROUNDED, "Lịch Điểm Danh", current_theme.surface_color, current_theme.secondary, "/admin/schedules"),
                create_action_btn(ft.Icons.NOTIFICATIONS_ROUNDED, "Quản lý TB", current_theme.surface_color, current_theme.secondary, "/admin/notifications"),
                create_action_btn(ft.Icons.SETTINGS_ROUNDED, "Cài đặt AI", current_theme.surface_color, current_theme.secondary, "/admin/settings"),
            ], run_spacing=5, spacing=5)
        ], spacing=0))

        layout_controls = [
            header_section,
            ft.Container(height=5),
            stats_row,
            ft.Container(height=5),
            ft.ResponsiveRow([
                ft.Column([audit_section], col={"xs": 12, "md": 12, "lg": 8}),
                ft.Column([quick_actions_section], col={"xs": 12, "md": 12, "lg": 4}),
            ], spacing=5, run_spacing=5)
        ]

        dashboard_layout = ft.Column(layout_controls, spacing=0)

        return ft.Column(
            [dashboard_layout],
            scroll=ft.ScrollMode.AUTO, expand=True
        )

    async def load_data(self):
        # 1. Load Admin Name từ session
        prefs = ft.SharedPreferences()
        session_str = await prefs.get("user_session")
        if session_str:
            session_data = safe_json_load(session_str)
            self.admin_name = session_data.get("name", "Quản trị viên")
            if self._name_text:
                self._name_text.value = f"QTV. {self.admin_name}"
                try:
                    self._name_text.update()
                except Exception:
                    pass

        # 2. Gọi API lấy Stats và Audit Logs
        try:
            client = await get_supabase_client()
            
            # Fetch Stats
            stats_res = await client.get("/api/admin/system/stats")
            if stats_res.status_code == 200:
                self.stats_data = stats_res.json()
            
            # Fetch Audit Logs
            audit_res = await client.get("/api/admin/system/audit?limit=5")
            if audit_res.status_code == 200:
                self.audit_logs = audit_res.json()

            self.is_loading = False
            self.apply_theme()

        except Exception as e:
            print(f"ADMIN load_data ERROR: {e}")
            show_top_notification(self.app_page, f"Lỗi kết nối máy chủ: {e}", ft.Colors.RED)
            self.is_loading = False
            self.apply_theme()
