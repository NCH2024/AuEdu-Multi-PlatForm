import flet as ft
import datetime
import calendar
import asyncio
import json
import time

from components.options.schedule_list import ScheduleDetailList
from components.options.top_notification import show_top_notification
from core.theme import PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR
from core.config import get_supabase_client
from core.helper import hash_data, safe_json_load

class SchedulePage(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.app_page = page
        self.expand = True
        self.bgcolor = ft.Colors.TRANSPARENT

        self.gv_id = "N/A"
        self.view_mode = "week"                 
        self.selected_date = datetime.date.today()
        self.raw_schedule_data = []           
        self.tuan_hoc_data = []               
        self.calendar_day_refs = {}            

        self.is_updating_ui = False           

        self.date_picker = ft.DatePicker(
            first_date=datetime.date(2025, 1, 1),
            last_date=datetime.date(2030, 12, 31),
            on_change=self._handle_date_picker_change,
        )
        self.app_page.overlay.append(self.date_picker)

        self.toolbar_container = ft.Container()
        self.calendar_area_container = ft.Container()
        self.schedule_list = ScheduleDetailList()

        main_ui = self.build_ui()
        self.content = ft.Stack(
            controls=[main_ui],
            expand=True,
        )

    def did_mount(self):
        self.app_page.run_task(self.initialize_data)

    async def initialize_data(self):
        prefs = ft.SharedPreferences()
        
        session_str = await prefs.get("user_session")
        if session_str:
            session = safe_json_load(session_str)
            self.gv_id = session.get("id", "N/A")

        cached_tuan_hoc = safe_json_load(await prefs.get("cached_tuan_hoc"))
        cached_schedule = safe_json_load(await prefs.get(f"cached_schedule_{self.gv_id}"))

        last_sync = float(await prefs.get(f"last_sync_schedule_{self.gv_id}") or 0)
        cached_tuan_hoc_hash = await prefs.get("tuan_hoc_hash")
        cached_schedule_hash = await prefs.get(f"schedule_hash_{self.gv_id}")

        current_time = time.time()
        TTL = 21600  

        if cached_tuan_hoc is not None and cached_schedule is not None:
            self.tuan_hoc_data = cached_tuan_hoc
            self.raw_schedule_data = cached_schedule
            await self._async_rebuild_entire_ui()

        if current_time - last_sync < TTL:
            return

        try:
            async with await get_supabase_client() as client:
                res_th = await client.get("/tuan_hoc", params={"select": "*", "order": "id.asc"})
                res_th.raise_for_status()
                fresh_tuan_hoc = res_th.json()

                fresh_raw_schedule = []
                if self.gv_id != "N/A":
                    res_tkb = await client.get("/thoikhoabieu", params={"select": "id,hocphan(tenhocphan),lop(tenlop)", "giangvien_id": f"eq.{self.gv_id}"})
                    res_tkb.raise_for_status()
                    tkb_list = res_tkb.json()

                    if tkb_list:
                        tkb_dict = {
                            row["id"]: {
                                "hocphan": row["hocphan"]["tenhocphan"] if row.get("hocphan") else "N/A",
                                "lop": row["lop"]["tenlop"] if row.get("lop") else "N/A",
                            }
                            for row in tkb_list
                        }
                        tkb_ids_str = ",".join(map(str, tkb_dict.keys()))
                        res_tiet = await client.get("/tkb_tiet", params={"select": "tkb_id,tiet_id,thu,phong_hoc", "tkb_id": f"in.({tkb_ids_str})"})
                        res_tiet.raise_for_status()
                        tkb_tiet_data = res_tiet.json()

                        if tkb_tiet_data:
                            grouped = {}
                            for item in tkb_tiet_data:
                                key = (item["tkb_id"], item["thu"], item["phong_hoc"])
                                grouped.setdefault(key, []).append(item["tiet_id"])

                            for (tkb_id, thu, phong), tiets in grouped.items():
                                tiets.sort()
                                tiet_str = f"{tiets[0]} - {tiets[-1]}" if len(tiets) > 1 else str(tiets[0])
                                ten_mon = tkb_dict[tkb_id]["hocphan"]
                                card_color = "#FFC107" if any(k in ten_mon.lower() for k in ["thi", "bảo vệ"]) else "#00A884"
                                
                                fresh_raw_schedule.append({
                                    "thu": thu,
                                    "subject": ten_mon,
                                    "time": tiet_str,
                                    "room": phong if phong else "N/A",
                                    "class_name": tkb_dict[tkb_id]["lop"],
                                    "type_color": card_color,
                                })

            new_tuan_hoc_hash = hash_data(fresh_tuan_hoc)
            new_schedule_hash = hash_data(fresh_raw_schedule)

            is_changed = (
                new_tuan_hoc_hash != cached_tuan_hoc_hash or
                new_schedule_hash != cached_schedule_hash
            )

            await prefs.set("cached_tuan_hoc", json.dumps(fresh_tuan_hoc))
            await prefs.set(f"cached_schedule_{self.gv_id}", json.dumps(fresh_raw_schedule))

            await prefs.set("tuan_hoc_hash", new_tuan_hoc_hash)
            await prefs.set(f"schedule_hash_{self.gv_id}", new_schedule_hash)

            await prefs.set(f"last_sync_schedule_{self.gv_id}", str(current_time))

            if is_changed or cached_tuan_hoc is None:
                self.tuan_hoc_data = fresh_tuan_hoc
                self.raw_schedule_data = fresh_raw_schedule
                await self._async_rebuild_entire_ui()

        except Exception as e:
            show_top_notification(self.app_page, "SCHEDULE [Lỗi kết nối mạng]", "Không thể tải lịch học mới nhất!", 4000, color=ft.Colors.RED)

    async def _async_rebuild_entire_ui(self):
        if self.is_updating_ui: return
        self.is_updating_ui = True

        self.render_toolbar()
        self.render_calendar_area()
        self.render_schedule_cards()

        if getattr(self, "app_page", None):
            self.app_page.update()
        self.is_updating_ui = False

    async def _handle_year_change(self, e):
        try:
            self.selected_date = self.selected_date.replace(year=int(e.control.value))
            await self._async_rebuild_entire_ui()
        except Exception: pass

    async def _handle_month_change(self, e):
        try:
            self.selected_date = datetime.date(self.selected_date.year, int(e.control.value), 1)
            await self._async_rebuild_entire_ui()
        except Exception: pass

    async def _handle_week_change(self, e):
        try:
            selected_id = int(e.control.value)
            for t in self.tuan_hoc_data:
                if t["id"] == selected_id:
                    date_str = t["ngay_bat_dau"].split("T")[0]
                    self.selected_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    break
            await self._async_rebuild_entire_ui()
        except Exception: pass

    def _handle_custom_mode_change(self, e):
        target = e.control.data
        if self.view_mode != target:
            self.view_mode = target
            self.app_page.run_task(self._async_rebuild_entire_ui)

    def _open_date_picker(self, e):
        self.date_picker.open = True
        if getattr(self, "app_page", None):
            self.app_page.update()

    def _handle_date_picker_change(self, e):
        if self.date_picker.value:
            self.selected_date = self.date_picker.value.date()
            self.app_page.run_task(self._async_rebuild_entire_ui)

    def _set_selected_date_and_scroll(self, target_date: datetime.date):
        if target_date == self.selected_date: return

        old_ref = self.calendar_day_refs.get(self.selected_date)
        if old_ref:
            old_ref["bg"].bgcolor = ft.Colors.WHITE if self.view_mode == "week" else ft.Colors.TRANSPARENT
            old_ref["text"].color = ft.Colors.BLACK_87
            old_ref["text"].weight = ft.FontWeight.NORMAL if self.view_mode == "month" else ft.FontWeight.W_800
            if "day_text" in old_ref:
                old_ref["day_text"].color = ft.Colors.BLACK_54
            old_ref["bg"].update()

        self.selected_date = target_date
        new_ref = self.calendar_day_refs.get(self.selected_date)
        if new_ref:
            new_ref["bg"].bgcolor = SECONDARY_COLOR
            new_ref["text"].color = ft.Colors.WHITE
            new_ref["text"].weight = ft.FontWeight.W_500 if self.view_mode == "month" else ft.FontWeight.W_800
            if "day_text" in new_ref:
                new_ref["day_text"].color = ft.Colors.WHITE
            new_ref["bg"].update()

        self.schedule_list.highlight_and_scroll(target_date, self.app_page)

    def render_toolbar(self):
        def create_tab(text, value):
            active = self.view_mode == value
            return ft.Container(
                content=ft.Text(
                    text,
                    color=ft.Colors.WHITE if active else ft.Colors.GREY_600,
                    weight=ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL,
                    size=12,
                ),
                bgcolor=SECONDARY_COLOR if active else ft.Colors.TRANSPARENT,
                padding=ft.Padding(15, 6, 15, 6),
                border_radius=8,
                ink=True,
                data=value,
                on_click=self._handle_custom_mode_change,
            )

        segment_group = ft.Container(
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.BLACK_12),
            border_radius=8,
            padding=3,
            content=ft.Row(
                spacing=0,
                controls=[create_tab("Ngày", "day"), create_tab("Tuần", "week"), create_tab("Tháng", "month")],
            ),
        )

        controls_left = []

        if self.view_mode == "day":
            day_str = ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"][self.selected_date.weekday()]
            btn = ft.TextButton(
                content=ft.Row([
                        ft.Text(f"{day_str}, {self.selected_date.strftime('%d/%m/%Y')}", size=14, weight=ft.FontWeight.BOLD, color=SECONDARY_COLOR),
                        ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=SECONDARY_COLOR, size=20),
                    ], spacing=2),
                style=ft.ButtonStyle(padding=0),
                on_click=self._open_date_picker,
            )
            controls_left = [ft.Container(content=btn)]

        elif self.view_mode == "week":
            dd_year = ft.Dropdown(
                value=str(self.selected_date.year),
                options=[ft.dropdown.Option(key=str(y), text=str(y)) for y in range(2025, 2031)],
                text_size=14, border=ft.InputBorder.NONE, dense=True, width=100, menu_height=250,
            )
            dd_year.on_select = self._handle_year_change

            week_opts = [ft.dropdown.Option(key=str(t["id"]), text=t["ten_tuan"]) for t in self.tuan_hoc_data]
            current_week_id = None
            if self.tuan_hoc_data:
                for t in self.tuan_hoc_data:
                    start = datetime.datetime.strptime(t["ngay_bat_dau"].split("T")[0], "%Y-%m-%d").date()
                    end = datetime.datetime.strptime(t["ngay_ket_thuc"].split("T")[0], "%Y-%m-%d").date() if "ngay_ket_thuc" in t and t["ngay_ket_thuc"] else start + datetime.timedelta(days=6)
                    if start <= self.selected_date <= end:
                        current_week_id = str(t["id"])
                        break
                if not current_week_id: current_week_id = str(self.tuan_hoc_data[0]["id"])

            dd_week = ft.Dropdown(value=current_week_id, options=week_opts, text_size=14, border=ft.InputBorder.NONE, dense=True, width=120, menu_height=250)
            dd_week.on_select = self._handle_week_change
            controls_left = [dd_year, dd_week]

        elif self.view_mode == "month":
            dd_year = ft.Dropdown(
                value=str(self.selected_date.year),
                options=[ft.dropdown.Option(key=str(y), text=str(y)) for y in range(2025, 2031)],
                text_size=14, border=ft.InputBorder.NONE, dense=True, width=100, menu_height=250,
            )
            dd_year.on_select = self._handle_year_change

            dd_month = ft.Dropdown(
                value=str(self.selected_date.month),
                options=[ft.dropdown.Option(key=str(m), text=f"Tháng {m}") for m in range(1, 13)],
                text_size=14, border=ft.InputBorder.NONE, dense=True, width=120, menu_height=250,
            )
            dd_month.on_select = self._handle_month_change
            controls_left = [dd_year, dd_month]

        self.toolbar_container.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            wrap=True, 
            controls=[ft.Row(controls=controls_left, spacing=5), segment_group],
        )

    def render_calendar_area(self):
        self.calendar_day_refs.clear()

        if self.view_mode == "day":
            self.calendar_area_container.content = ft.Container(height=0)
            return

        if self.view_mode == "week":
            start_of_week = self.selected_date - datetime.timedelta(days=self.selected_date.weekday())
            day_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
            day_boxes = []

            for i in range(7):
                d = start_of_week + datetime.timedelta(days=i)
                is_selected = d == self.selected_date
                target_thu = d.weekday() + 2
                has_dot = any(item.get("thu") == target_thu for item in self.raw_schedule_data)

                txt_day = ft.Text(day_names[i], size=11, color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK_54)
                txt_num = ft.Text(
                    d.strftime("%d"), size=15, weight=ft.FontWeight.W_800,
                    color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK_87,
                )
                dot = ft.Container(width=5, height=5, border_radius=2.5, bgcolor=ft.Colors.AMBER_500 if has_dot else ft.Colors.TRANSPARENT)
                box = ft.Container(
                    expand=True,
                    bgcolor=SECONDARY_COLOR if is_selected else ft.Colors.WHITE,
                    border_radius=12, padding=ft.Padding(0, 10, 0, 10),
                    content=ft.Column(alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, controls=[txt_day, txt_num, dot]),
                )
                box.on_click = lambda e, date_val=d: self._set_selected_date_and_scroll(date_val)
                day_boxes.append(box)
                self.calendar_day_refs[d] = {"bg": box, "text": txt_num, "day_text": txt_day}

            self.calendar_area_container.content = ft.Row(controls=day_boxes, spacing=5, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            return

        now = self.selected_date
        cal = calendar.monthcalendar(now.year, now.month)
        day_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        
        header_controls = []
        for i, d_name in enumerate(day_names):
            header_controls.append(ft.Container(expand=True, alignment=ft.Alignment(0, 0), content=ft.Text(d_name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700 if i >= 5 else SECONDARY_COLOR)))
        header_row = ft.Row(controls=header_controls, spacing=0)

        weeks_controls = []
        for week in cal:
            week_row_controls = []
            for day in week:
                if day == 0:
                    week_row_controls.append(ft.Container(expand=True))
                else:
                    d_obj = datetime.date(now.year, now.month, day)
                    is_selected = d_obj == self.selected_date
                    target_thu = d_obj.weekday() + 2
                    has_dot = any(item.get("thu") == target_thu for item in self.raw_schedule_data)

                    txt_num = ft.Text(str(day), size=12, weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL, color=ft.Colors.WHITE if is_selected else ft.Colors.BLACK_87)
                    day_circle = ft.Container(
                        width=32, height=32, border_radius=16,
                        bgcolor=SECONDARY_COLOR if is_selected else ft.Colors.TRANSPARENT,
                        alignment=ft.Alignment(0, 0), content=txt_num,
                    )
                    dot = ft.Container(width=5, height=5, border_radius=2.5, bgcolor=ft.Colors.AMBER_500 if has_dot and not is_selected else ft.Colors.TRANSPARENT)
                    day_box = ft.Container(expand=True, height=45, content=ft.Column(alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2, controls=[day_circle, dot]))
                    day_box.on_click = lambda e, date_val=d_obj: self._set_selected_date_and_scroll(date_val)
                    week_row_controls.append(day_box)
                    self.calendar_day_refs[d_obj] = {"bg": day_circle, "text": txt_num}
            
            weeks_controls.append(ft.Row(controls=week_row_controls, spacing=0))

        self.calendar_area_container.content = ft.Container(
            bgcolor=ft.Colors.WHITE, padding=ft.Padding(5, 10, 5, 10), border_radius=12,
            content=ft.Column(spacing=5, controls=[header_row, ft.Divider(height=1, color=ft.Colors.BLACK_12), ft.Container(height=180, content=ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, controls=weeks_controls))])
        )
    
    def render_schedule_cards(self):
        display_schedules = []

        if self.view_mode == "day":
            thu = self.selected_date.weekday() + 2
            day_scheds = [item.copy() for item in self.raw_schedule_data if item.get("thu") == thu]
            for s in day_scheds: s["date"] = self.selected_date
            display_schedules.extend(day_scheds)

        elif self.view_mode == "week":
            start = self.selected_date - datetime.timedelta(days=self.selected_date.weekday())
            for i in range(7):
                d = start + datetime.timedelta(days=i)
                thu = d.weekday() + 2
                day_scheds = [item.copy() for item in self.raw_schedule_data if item.get("thu") == thu]
                for s in day_scheds: s["date"] = d
                display_schedules.extend(day_scheds)

        elif self.view_mode == "month":
            now = self.selected_date
            cal = calendar.monthcalendar(now.year, now.month)
            for week in cal:
                for day in week:
                    if day != 0:
                        d = datetime.date(now.year, now.month, day)
                        thu = d.weekday() + 2
                        day_scheds = [item.copy() for item in self.raw_schedule_data if item.get("thu") == thu]
                        for s in day_scheds: s["date"] = d
                        display_schedules.extend(day_scheds)

        self.schedule_list.render_data(display_schedules)

    def build_ui(self) -> ft.Control:
        main_layout = ft.Column(
            spacing=2, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, expand=True,
            controls=[
                self.toolbar_container,
                self.calendar_area_container,
                ft.Container(content=self.schedule_list, height=500), 
            ],
        )
        
        return main_layout