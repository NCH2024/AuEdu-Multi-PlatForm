import flet as ft
import json
import datetime
import time

from core.theme import get_glass_container, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from core.config import get_supabase_client
from core.helper import hash_data, safe_json_load
from components.options.top_notification import show_top_notification

class ProfilePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True

        # ==========================================
        # CÁC BIẾN UI TRẠNG THÁI
        # ==========================================
        self.avatar_icon = ft.Icon(ft.Icons.PERSON, size=50, color=ft.Colors.WHITE)
        self.name_text = ft.Text("Đang tải...", size=20, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)
        self.role_text = ft.Text("...", size=14, weight=ft.FontWeight.W_500, color=ACCENT_COLOR)
        
        self.id_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)
        self.gender_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)
        self.phone_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)
        self.address_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)
        self.khoa_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)
        self.join_date_val = ft.Text("...", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK_87)

        self.total_classes_val = ft.Text("...", size=30, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR)

        self.content = self.build_ui()

    def did_mount(self):
        self.app_page.run_task(self.load_profile_data)

    def build_ui(self):
        # Đã thêm hàm async ở đây để khắc phục Warning "was never awaited"
        async def handle_update_click(e):
            await self.app_page.push_route("/user/settings")

        def create_info_row(icon_name, label, value_control):
            return ft.Container(
                padding=ft.Padding(0, 10, 0, 10),
                border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.BLACK_12)),
                content=ft.Row([
                    ft.Row([
                        ft.Icon(icon_name, size=20, color=ft.Colors.GREY_600),
                        ft.Text(label, size=14, color=ft.Colors.GREY_600)
                    ], width=120),
                    ft.Container(content=value_control, expand=True)
                ])
            )

        # 1. CARD THÔNG TIN CÁ NHÂN
        personal_info_card = get_glass_container(
            content=ft.Column([
                ft.Row([
                    ft.CircleAvatar(content=self.avatar_icon, bgcolor=SECONDARY_COLOR, radius=40),
                    ft.Container(width=10),
                    ft.Column([
                        self.name_text,
                        ft.Container(
                            padding=ft.Padding(10, 4, 10, 4), bgcolor=ft.Colors.with_opacity(0.1, ACCENT_COLOR),
                            border_radius=12, content=self.role_text
                        )
                    ], spacing=2)
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                
                ft.Divider(color=ft.Colors.BLACK_12, height=30),
                ft.Text("Chi tiết liên hệ & Định danh", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                ft.Container(height=5),
                
                create_info_row(ft.Icons.BADGE_OUTLINED, "Mã Cán Bộ:", self.id_val),
                create_info_row(ft.Icons.WC_ROUNDED, "Giới tính:", self.gender_val),
                create_info_row(ft.Icons.PHONE_ANDROID_ROUNDED, "Điện thoại:", self.phone_val),
                create_info_row(ft.Icons.HOME_OUTLINED, "Địa chỉ:", self.address_val),
                create_info_row(ft.Icons.ACCOUNT_BALANCE_OUTLINED, "Đơn vị (Khoa):", self.khoa_val),
                create_info_row(ft.Icons.CALENDAR_TODAY_ROUNDED, "Ngày tham gia:", self.join_date_val),
                
            ], spacing=10)
        )

        # 2. CARD HOẠT ĐỘNG & THỐNG KÊ
        stats_card = get_glass_container(
            content=ft.Column([
                ft.Text("HOẠT ĐỘNG GIẢNG DẠY", weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR, size=13),
                ft.Divider(color=ft.Colors.BLACK_12),
                
                ft.Container(
                    bgcolor=ft.Colors.WHITE, padding=20, border_radius=12,
                    border=ft.Border.all(1, ft.Colors.BLACK_12),
                    content=ft.Row([
                        ft.Container(
                            padding=15, bgcolor=ft.Colors.with_opacity(0.1, SECONDARY_COLOR), border_radius=12,
                            content=ft.Icon(ft.Icons.CLASS_OUTLINED, color=SECONDARY_COLOR, size=30)
                        ),
                        ft.Container(width=15),
                        ft.Column([
                            ft.Text("Tổng số lớp phụ trách", size=13, color=ft.Colors.GREY_600),
                            self.total_classes_val
                        ], spacing=0)
                    ])
                ),
                
                ft.Container(height=15),
                ft.Button(
                    content=ft.Row([ft.Icon(ft.Icons.EDIT_DOCUMENT, color=ft.Colors.WHITE, size=18), ft.Text("Cập nhật thông tin", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER), 
                    bgcolor=ACCENT_COLOR, height=45,
                    on_click=handle_update_click # Gọi hàm an toàn ở đây
                )
            ], spacing=10)
        )

        return ft.ResponsiveRow([
            ft.Column([personal_info_card], col={"sm": 12, "md": 7}),
            ft.Column([stats_card], col={"sm": 12, "md": 5}),
        ], expand=True)

    def render_data_to_ui(self, info, total_classes):
        """Hàm gán dữ liệu vào giao diện"""
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
            except:
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

            # ==============================
            # BƯỚC 1: LOAD CACHE VÀ ĐỌC HASH
            # ==============================
            cached_profile = safe_json_load(await prefs.get(f"cached_profile_{gv_id}"))
            cached_total_classes = await prefs.get(f"cached_total_classes_{gv_id}")
            
            last_sync = float(await prefs.get(f"last_sync_profile_{gv_id}") or 0)
            cached_profile_hash = await prefs.get(f"profile_hash_{gv_id}")

            current_time = time.time()
            TTL = 86400  # 1 Ngày = 24 * 60 * 60 giây

            # HIỂN THỊ CACHE TỨC THÌ
            if cached_profile is not None and cached_total_classes is not None:
                self.render_data_to_ui(cached_profile, cached_total_classes)

            # BƯỚC 2: KIỂM TRA TTL
            if current_time - last_sync < TTL:
                # print("PROFILE: Cache còn hạn 1 ngày, bỏ qua gọi API!")
                return

            # ==============================
            # BƯỚC 3: CALL API (BACKGROUND)
            # ==============================
            async with await get_supabase_client() as client:
                params_gv = {"select": "*, khoa(tenkhoa)", "id": f"eq.{gv_id}"}
                res_gv = await client.get("/giangvien", params=params_gv)
                res_gv.raise_for_status()
                gv_data = res_gv.json()
                fresh_profile = gv_data[0] if gv_data else {}

                params_tkb = {"select": "id", "giangvien_id": f"eq.{gv_id}"}
                res_tkb = await client.get("/thoikhoabieu", params=params_tkb)
                res_tkb.raise_for_status()
                tkb_data = res_tkb.json()
                fresh_total_classes = len(tkb_data)

            # ==============================
            # BƯỚC 4: BĂM HASH SO SÁNH
            # ==============================
            new_profile_hash = hash_data({"profile": fresh_profile, "total": fresh_total_classes})
            is_changed = (new_profile_hash != cached_profile_hash)

            # ==============================
            # BƯỚC 5: CẬP NHẬT CACHE VÀ THỜI GIAN
            # ==============================
            await prefs.set(f"cached_profile_{gv_id}", json.dumps(fresh_profile))
            await prefs.set(f"cached_total_classes_{gv_id}", str(fresh_total_classes))
            await prefs.set(f"profile_hash_{gv_id}", new_profile_hash)
            await prefs.set(f"last_sync_profile_{gv_id}", str(current_time))

            # ==============================
            # BƯỚC 6: CẬP NHẬT UI NẾU CÓ THAY ĐỔI
            # ==============================
            if is_changed or cached_profile is None:
                print("PROFILE [SYNC] ... đang đồng bộ dữ liệu hồ sơ mới ...")
                self.render_data_to_ui(fresh_profile, fresh_total_classes)
            else:
                print("PROFILE [SYNC] Dữ liệu hồ sơ chuẩn xác")

        except Exception as e:
            print(f"Lỗi tải dữ liệu Hồ sơ: {e}")
            if getattr(self, "page", None):
                show_top_notification(self.app_page, "Lỗi mạng", "Không thể tải hồ sơ mới nhất!", 4000, color=ft.Colors.RED)