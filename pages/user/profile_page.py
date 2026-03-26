import flet as ft
import json
import datetime
import asyncio
import time

from core.theme import current_theme
from core.config import get_supabase_client
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification

class ProfilePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = 0

        # Controls tái sử dụng — không tạo lại khi apply_theme
        self.avatar_icon = ft.Icon(ft.Icons.PERSON, size=50, color=ft.Colors.WHITE)
        self.name_text = ft.Text("Đang tải...", size=20, weight=ft.FontWeight.BOLD, color=current_theme.secondary)
        self.role_text = ft.Text("...", size=14, weight=ft.FontWeight.W_500, color=current_theme.accent)

        self.id_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.gender_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.phone_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.address_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.khoa_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.join_date_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=current_theme.text_main)
        self.total_classes_val = ft.Text("...", size=30, weight=ft.FontWeight.BOLD, color=current_theme.secondary)

        self.content = self.build_ui()

    def did_mount(self):
        self.app_page.run_task(self.load_profile_data)

    def apply_theme(self):
        # Cập nhật màu trực tiếp trên control hiện có
        self.name_text.color = current_theme.secondary
        self.role_text.color = current_theme.accent
        self.total_classes_val.color = current_theme.secondary
        for ctrl in [self.id_val, self.gender_val, self.phone_val, self.address_val, self.khoa_val, self.join_date_val]:
            ctrl.color = current_theme.text_main

        # Rebuild layout vì màu nền các card thay đổi
        self.content = self.build_ui()
        if self.page: self.update()

    def build_ui(self):
        async def handle_update_click(e):
            await self.app_page.push_route("/user/settings")

        def make_card(content):
            return ft.Container(
                content=content, padding=20,
                bgcolor=current_theme.surface_color, border_radius=16,
                border=ft.Border.all(1, current_theme.divider_color)
            )

        def create_info_row(icon_name, label, value_control):
            return ft.Container(
                padding=ft.Padding(0, 10, 0, 10),
                border=ft.Border(bottom=ft.BorderSide(1, current_theme.divider_color)),
                content=ft.Row([
                    ft.Row([
                        ft.Icon(icon_name, size=20, color=current_theme.text_muted),
                        ft.Text(label, size=14, color=current_theme.text_muted)
                    ], width=130),
                    ft.Container(content=value_control, expand=True)
                ])
            )

        personal_info_card = make_card(
            content=ft.Column([
                ft.Row([
                    ft.CircleAvatar(content=self.avatar_icon, bgcolor=current_theme.secondary, radius=40),
                    ft.Container(width=10),
                    ft.Column([
                        self.name_text,
                        ft.Container(
                            padding=ft.Padding(10, 4, 10, 4),
                            bgcolor=ft.Colors.with_opacity(0.1, current_theme.accent),
                            border_radius=12, content=self.role_text
                        )
                    ], spacing=2)
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),

                ft.Divider(color=current_theme.divider_color, height=30),
                ft.Text("Chi tiết liên hệ & Định danh", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.Container(height=5),

                create_info_row(ft.Icons.BADGE_OUTLINED, "Mã Cán Bộ:", self.id_val),
                create_info_row(ft.Icons.WC_ROUNDED, "Giới tính:", self.gender_val),
                create_info_row(ft.Icons.PHONE_ANDROID_ROUNDED, "Điện thoại:", self.phone_val),
                create_info_row(ft.Icons.HOME_OUTLINED, "Địa chỉ:", self.address_val),
                create_info_row(ft.Icons.ACCOUNT_BALANCE_OUTLINED, "Đơn vị (Khoa):", self.khoa_val),
                create_info_row(ft.Icons.CALENDAR_TODAY_ROUNDED, "Ngày tham gia:", self.join_date_val),
            ], spacing=10)
        )

        stats_card = make_card(
            content=ft.Column([
                ft.Text("HOẠT ĐỘNG GIẢNG DẠY", weight=ft.FontWeight.BOLD, color=current_theme.secondary, size=13),
                ft.Divider(color=current_theme.divider_color),
                ft.Container(
                    bgcolor=current_theme.surface_variant, padding=20, border_radius=12,
                    border=ft.Border.all(1, current_theme.divider_color),
                    content=ft.Row([
                        ft.Container(
                            padding=15, bgcolor=ft.Colors.with_opacity(0.1, current_theme.secondary), border_radius=12,
                            content=ft.Icon(ft.Icons.CLASS_OUTLINED, color=current_theme.secondary, size=30)
                        ),
                        ft.Container(width=15),
                        ft.Column([
                            ft.Text("Tổng số lớp phụ trách", size=13, color=current_theme.text_muted),
                            self.total_classes_val
                        ], spacing=0)
                    ])
                ),
                ft.Container(height=15),
                ft.Button(
                    content=ft.Row([ft.Icon(ft.Icons.EDIT_DOCUMENT, color=current_theme.bg_color, size=18), ft.Text("Cập nhật thông tin", color=current_theme.bg_color, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=current_theme.accent, height=45,
                    on_click=handle_update_click
                )
            ], spacing=10)
        )

        main_layout = ft.ResponsiveRow([
            ft.Column([personal_info_card], col={"sm": 12, "md": 7}),
            ft.Column([stats_card], col={"sm": 12, "md": 5}),
        ], expand=True, spacing=15, run_spacing=15)

        return ft.Column([ft.Container(height=5), main_layout, ft.Container(height=30)], scroll=ft.ScrollMode.AUTO, expand=True)

    def render_data_to_ui(self, info, total_classes):
        ho_ten = f"{info.get('hodem', '')} {info.get('ten', '')}".strip()
        self.name_text.value = ho_ten

        role = info.get("vai_tro", "giangvien")
        self.role_text.value = "Quản trị viên hệ thống" if role == "admin" else "Giảng viên"

        self.id_val.value = str(info.get("id", "N/A"))
        self.gender_val.value = info.get("gioitinh", "Chưa cập nhật")
        self.phone_val.value = info.get("sodienthoai", "Chưa cập nhật")
        self.address_val.value = info.get("diachi", "Chưa cập nhật")

        if info.get("khoa") and isinstance(info["khoa"], dict) and info["khoa"].get("tenkhoa"):
            self.khoa_val.value = info["khoa"]["tenkhoa"]
        else:
            self.khoa_val.value = "Chưa cập nhật"

        raw_date = info.get("created_at")
        if raw_date:
            try:
                parsed_date = datetime.datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                self.join_date_val.value = parsed_date.strftime("%d/%m/%Y")
            except Exception:
                self.join_date_val.value = raw_date[:10]
        else:
            self.join_date_val.value = "Không xác định"

        self.total_classes_val.value = f"{total_classes} Lớp"

        if getattr(self, "page", None):
            self.update()

    async def load_profile_data(self):
        try:
            prefs = ft.SharedPreferences()
            session_str = await prefs.get("user_session")
            if not session_str: return

            session_data = safe_json_load(session_str)
            gv_id = session_data.get("id")
            if not gv_id or gv_id == "N/A": return

            cached_profile = safe_json_load(await prefs.get(f"cached_profile_{gv_id}"))
            cached_total_classes = await prefs.get(f"cached_total_classes_{gv_id}")
            last_sync = float(await prefs.get(f"last_sync_profile_{gv_id}") or 0)
            cached_profile_hash = await prefs.get(f"profile_hash_{gv_id}")

            current_time = time.time()
            TTL = 86400  # 1 ngày

            # Hiển thị cache ngay
            if cached_profile is not None and cached_total_classes is not None:
                self.render_data_to_ui(cached_profile, cached_total_classes)

            if current_time - last_sync < TTL:
                return

            # ✅ Singleton client, KHÔNG dùng async with
            client = await get_supabase_client()

            # ✅ Fetch profile và TKB song song
            res_gv, res_tkb = await asyncio.gather(
                client.get("/giangvien", params={"select": "*, khoa(tenkhoa)", "id": f"eq.{gv_id}"}),
                client.get("/thoikhoabieu", params={"select": "id", "giangvien_id": f"eq.{gv_id}"}),
                return_exceptions=True
            )

            if isinstance(res_gv, Exception): raise res_gv
            if isinstance(res_tkb, Exception): raise res_tkb

            res_gv.raise_for_status()
            res_tkb.raise_for_status()

            gv_data = res_gv.json()
            fresh_profile = gv_data[0] if gv_data else {}
            fresh_total_classes = len(res_tkb.json())

            new_profile_hash = hash_data({"profile": fresh_profile, "total": fresh_total_classes})
            is_changed = (new_profile_hash != cached_profile_hash)

            # ✅ Lưu cache song song
            await asyncio.gather(
                prefs.set(f"cached_profile_{gv_id}", json.dumps(fresh_profile)),
                prefs.set(f"cached_total_classes_{gv_id}", str(fresh_total_classes)),
                prefs.set(f"profile_hash_{gv_id}", new_profile_hash),
                prefs.set(f"last_sync_profile_{gv_id}", str(current_time)),
            )

            if is_changed or cached_profile is None:
                print("PROFILE [SYNC] Cập nhật dữ liệu mới...")
                self.render_data_to_ui(fresh_profile, fresh_total_classes)
            else:
                print("PROFILE [SYNC] Dữ liệu không thay đổi")

        except Exception as e:
            print(f"load_profile_data lỗi: {e}")
            if getattr(self, "page", None):
                show_top_notification(self.app_page, "Lỗi mạng", "Không thể tải hồ sơ mới nhất!", 4000, color=current_theme.primary)