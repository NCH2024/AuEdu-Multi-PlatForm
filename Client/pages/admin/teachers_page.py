"""
Trang Quản lý Giảng viên — Admin Panel.
Cho phép CRUD thông tin giảng viên và tạo tài khoản Supabase Auth.
"""

import flet as ft
from core.theme import current_theme
from components.options.top_notification import show_top_notification
from core.admin_service import AdminService
from components.admin.data_grid import AdminDataGrid


class TeachersPage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.padding = ft.Padding.all(20)
        self.svc = AdminService.instance()

        # -- State --
        self.teachers_data = []
        self.departments = []
        self.selected_item = None

        # -- UI Elements --
        self.title_text = ft.Text("QUẢN LÝ GIẢNG VIÊN", size=24, weight=ft.FontWeight.BOLD)
        
        self.btn_add = ft.Button(
            "THÊM GIẢNG VIÊN", icon=ft.Icons.ADD_ROUNDED,
            bgcolor=current_theme.primary, color=ft.Colors.WHITE,
            on_click=lambda _: self.open_edit_dialog()
        )

        self.btn_refresh = ft.IconButton(
            ft.Icons.REFRESH_ROUNDED,
            tooltip="Làm mới dữ liệu",
            on_click=self.refresh_data
        )

        self.grid = AdminDataGrid(
            columns=[
                {"label": "ID", "key": "id", "col": {"xs": 2, "sm": 1}},
                {"label": "HỌ TÊN", "key": "full_name", "col": {"xs": 6, "sm": 3}, "sortable": True},
                {"label": "KHOA", "key": "ten_khoa", "col": {"xs": 6, "sm": 3}},
                {"label": "VAI TRÒ", "key": "vai_tro", "col": {"xs": 6, "sm": 2}},
                {"label": "THAO TÁC", "key": "actions", "col": {"xs": 12, "sm": 3}, "render": self.render_actions},
            ],
            on_row_click=self.open_edit_dialog,
        )

        self.progress_bar = ft.ProgressBar(visible=False, color=current_theme.primary, height=2)

        # -- Form Elements --
        self.form_hodem = ft.TextField(label="Họ đệm", expand=True)
        self.form_ten = ft.TextField(label="Tên", expand=True)
        self.form_gender = ft.Dropdown(
            label="Giới tính",
            options=[ft.dropdown.Option("Nam"), ft.dropdown.Option("Nữ")],
            expand=True
        )
        self.form_dept = ft.Dropdown(label="Khoa/Phòng ban", expand=True)
        self.form_phone = ft.TextField(label="Số điện thoại", expand=True)
        self.form_address = ft.TextField(label="Địa chỉ", expand=True)
        self.form_role = ft.Dropdown(
            label="Vai trò",
            options=[
                ft.dropdown.Option("giangvien", "Giảng viên"),
                ft.dropdown.Option("admin", "Quản trị viên"),
            ],
            value="giangvien",
            expand=True
        )

        self.edit_dialog = ft.AlertDialog(
            title=ft.Text("THÔNG TIN GIẢNG VIÊN"),
            content=ft.Column([
                ft.Row([self.form_hodem, self.form_ten]),
                ft.Row([self.form_gender, self.form_role]),
                self.form_dept,
                self.form_phone,
                self.form_address,
            ], tight=True, width=500),
            actions=[
                ft.TextButton("HỦY", on_click=lambda _: self.close_dialog(self.edit_dialog)),
                ft.Button("LƯU", bgcolor=current_theme.primary, color=ft.Colors.WHITE, on_click=self.save_data)
            ]
        )

        # -- Auth Dialog --
        self.form_auth_email = ft.TextField(label="Email đăng nhập", hint_text="example@edu.vn")
        self.form_auth_pass = ft.TextField(label="Mật khẩu tạm thời", password=True, can_reveal_password=True)
        
        self.auth_dialog = ft.AlertDialog(
            title=ft.Text("TẠO TÀI KHOẢN XÁC THỰC"),
            content=ft.Column([
                ft.Text("Tạo tài khoản trên Supabase Auth để giảng viên có thể đăng nhập."),
                self.form_auth_email,
                self.form_auth_pass
            ], tight=True, width=400),
            actions=[
                ft.TextButton("HỦY", on_click=lambda _: self.close_dialog(self.auth_dialog)),
                ft.Button("XÁC NHẬN TẠO", bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, on_click=self.confirm_create_auth)
            ]
        )

        self.content = ft.Column([
            ft.Row([
                ft.Row([ft.Icon(ft.Icons.PERSON_SEARCH_ROUNDED, color=current_theme.primary), self.title_text]),
                ft.Row([self.btn_refresh, self.btn_add])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.progress_bar,
            ft.Divider(color=current_theme.divider_color),
            self.grid
        ], expand=True)

    def did_mount(self):
        self.app_page.run_task(self.load_data)

    async def load_data(self):
        self.progress_bar.visible = True
        self.update()
        try:
            # Load departments for dropdown
            self.departments = await self.svc.get_departments()
            self.form_dept.options = [
                ft.dropdown.Option(d["id"], d["tenkhoa"]) for d in self.departments
            ]

            # Load teachers
            self.all_teachers = await self.svc.get_all_teachers()
            self.teachers_data = []
            for item in self.all_teachers:
                item["full_name"] = f"{item.get('hodem', '')} {item.get('ten', '')}".strip()
                # Fix: Handle case where 'khoa' is None safely
                khoa_obj = item.get("khoa") or {}
                item["ten_khoa"] = khoa_obj.get("ten_khoa") or khoa_obj.get("tenkhoa") or "N/A"
                self.teachers_data.append(item)
            
            self.grid.set_data(self.teachers_data)
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể tải dữ liệu: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    async def refresh_data(self, e):
        self.svc.invalidate("teachers")
        self.svc.invalidate("departments")
        await self.load_data()
        show_top_notification(self.app_page, "Thông tin", "Đã làm mới dữ liệu thành công!", ft.Colors.BLUE, sound="S")

    def render_actions(self, item):
        return ft.Row([
            ft.IconButton(
                ft.Icons.KEY_ROUNDED, 
                tooltip="Tạo tài khoản đăng nhập",
                icon_color=ft.Colors.GREEN_400 if not item.get("auth_id") else ft.Colors.GREY_400,
                icon_size=18,
                on_click=lambda e, d=item: self.open_auth_dialog(d)
            ),
            ft.IconButton(
                ft.Icons.EDIT_ROUNDED, 
                icon_size=18,
                on_click=lambda e, d=item: self.open_edit_dialog(d)
            ),
            ft.IconButton(
                ft.Icons.DELETE_ROUNDED, 
                icon_size=18, icon_color=ft.Colors.RED_400,
                on_click=lambda e, d=item: self.delete_data(d)
            )
        ], spacing=0)

    def open_edit_dialog(self, item=None):
        self.selected_item = item
        if item:
            self.form_hodem.value = item.get("hodem", "")
            self.form_ten.value = item.get("ten", "")
            self.form_gender.value = item.get("gioitinh", "Nam")
            self.form_dept.value = item.get("khoa_id")
            self.form_phone.value = item.get("sodienthoai", "")
            self.form_address.value = item.get("diachi", "")
            self.form_role.value = item.get("vai_tro", "giangvien")
        else:
            self.form_hodem.value = ""
            self.form_ten.value = ""
            self.form_gender.value = "Nam"
            self.form_dept.value = None
            self.form_phone.value = ""
            self.form_address.value = ""
            self.form_role.value = "giangvien"
        
        if self.edit_dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.edit_dialog)
        self.edit_dialog.open = True
        self.app_page.update()

    def open_auth_dialog(self, item):
        if item.get("auth_id"):
            show_top_notification(self.app_page, "Cảnh báo", "Giảng viên này đã có tài khoản xác thực!", ft.Colors.ORANGE, sound="E")
            return
        
        self.selected_item = item
        self.form_auth_email.value = ""
        self.form_auth_pass.value = ""
        
        if self.auth_dialog not in self.app_page.overlay:
            self.app_page.overlay.append(self.auth_dialog)
        self.auth_dialog.open = True
        self.app_page.update()

    def close_dialog(self, dialog):
        dialog.open = False
        self.app_page.update()

    async def save_data(self, e):
        if not self.form_ten.value or not self.form_dept.value:
            show_top_notification(self.app_page, "Cảnh báo", "Vui lòng nhập tên và chọn khoa!", ft.Colors.ORANGE, sound="E")
            return

        payload = {
            "hodem": self.form_hodem.value,
            "ten": self.form_ten.value,
            "gioitinh": self.form_gender.value,
            "khoa_id": self.form_dept.value,
            "sodienthoai": self.form_phone.value,
            "diachi": self.form_address.value,
            "vai_tro": self.form_role.value
        }

        self.close_dialog(self.edit_dialog)
        self.progress_bar.visible = True
        self.update()
        try:
            if self.selected_item:
                await self.svc.update_teacher(self.selected_item["id"], payload)
                show_top_notification(self.app_page, "Thông báo", "Đã cập nhật thông tin giảng viên thành công!", ft.Colors.GREEN, sound="S")
            else:
                await self.svc.create_teacher(payload)
                show_top_notification(self.app_page, "Thông báo", "Đã thêm giảng viên mới thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", f"Không thể lưu dữ liệu: {ex}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    async def confirm_create_auth(self, e):
        if not self.form_auth_email.value or not self.form_auth_pass.value:
            show_top_notification(self.app_page, "Cảnh báo", "Vui lòng nhập email và mật khẩu hợp lệ!", ft.Colors.ORANGE, sound="E")
            return

        self.close_dialog(self.auth_dialog)
        self.progress_bar.visible = True
        self.update()
        try:
            await self.svc.create_teacher_auth(
                self.selected_item["id"], 
                self.form_auth_email.value, 
                self.form_auth_pass.value
            )
            show_top_notification(self.app_page, "Thông báo", "Đã tạo tài khoản và liên kết thành công!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as ex:
            show_top_notification(self.app_page, "Lỗi", f"Tạo tài khoản thất bại: {ex}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    async def delete_data(self, item):
        self.progress_bar.visible = True
        self.update()
        try:
            await self.svc.delete_teacher(item["id"])
            show_top_notification(self.app_page, "Thông báo", "Đã xóa giảng viên khỏi hệ thống!", ft.Colors.GREEN, sound="S")
            await self.load_data()
        except Exception as e:
            show_top_notification(self.app_page, "Lỗi", f"Không thể xóa giảng viên: {e}", ft.Colors.RED, sound="E")
        finally:
            self.progress_bar.visible = False
            self.update()

    def apply_theme(self):
        self.update()
