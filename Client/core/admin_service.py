# Client/core/admin_service.py
"""
AdminService — Singleton quản lý tập trung mọi API call phía Admin.

Đặc điểm:
  - Memory-only cache (không dùng SharedPreferences — admin luôn dùng PC)
  - Tự động invalidate cache sau mỗi thao tác CRUD
  - TTL cấu hình sẵn cho từng loại dữ liệu tham chiếu (reference data)
  - Dữ liệu realtime (students, audit, stats) không cache

Sử dụng:
    from core.admin_service import AdminService
    svc = AdminService.instance()
    departments = await svc.get_departments()
"""

from typing import Any, Dict, List, Optional
from core.base_service import BaseService
from core.config import get_supabase_client


# ─── TTL mặc định (giây) ──────────────────────────────────────
_TTL_REFERENCE = 300      # 5 phút — cho departments, semesters, classes, subjects, teachers
_TTL_WEEKS     = 120      # 2 phút — weeks phụ thuộc semester, thay đổi thường hơn
_TTL_CONFIG    = 600      # 10 phút — system_config


class AdminService(BaseService):
    """
    Singleton Service Layer cho Admin Panel.
    Mọi trang admin gọi API thông qua class này thay vì trực tiếp dùng httpx.
    """

    _instance: Optional["AdminService"] = None

    @classmethod
    def instance(cls) -> "AdminService":
        """Trả về singleton instance. Tạo mới nếu chưa có."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()

    # ─── Helper nội bộ ────────────────────────────────────────────

    async def _fetch_list(self, url: str) -> List[dict]:
        """
        Fetch danh sách từ API endpoint.
        Trả về list rỗng nếu request lỗi.
        """
        try:
            client = await get_supabase_client()
            res = await client.get(url)
            if res.status_code == 200:
                return res.json()
            print(f"[AdminService] GET {url} → {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[AdminService] GET {url} error: {e}")
        return []

    async def _cached_fetch(self, cache_key: str, url: str, ttl: float, force: bool = False) -> List[dict]:
        """
        Fetch có cache: kiểm tra memory cache trước, nếu hết hạn hoặc force thì fetch mới.
        
        Args:
            cache_key: Tên key trong memory cache
            url: API endpoint
            ttl: Thời gian sống cache (giây)
            force: Bỏ qua cache, luôn fetch mới
        """
        if not force and self._is_cache_valid(cache_key, ttl):
            return self._get_from_cache(cache_key)

        data = await self._fetch_list(url)
        if data:  # Chỉ cache nếu có dữ liệu
            self._set_cache(cache_key, data)
        return data

    # ─── REFERENCE DATA (có cache) ────────────────────────────────

    async def get_departments(self, force: bool = False) -> List[dict]:
        """Lấy danh sách Khoa. Cache 5 phút."""
        return await self._cached_fetch("departments", "/api/admin/departments/", _TTL_REFERENCE, force)

    async def get_semesters(self, force: bool = False) -> List[dict]:
        """Lấy danh sách Học kỳ. Cache 5 phút."""
        return await self._cached_fetch("semesters", "/api/admin/semesters/", _TTL_REFERENCE, force)

    async def get_classes(self, force: bool = False) -> List[dict]:
        """Lấy danh sách Lớp học. Cache 5 phút."""
        return await self._cached_fetch("classes", "/api/admin/classes/", _TTL_REFERENCE, force)

    async def get_subjects(self, force: bool = False) -> List[dict]:
        """Lấy danh sách Học phần. Cache 5 phút."""
        return await self._cached_fetch("subjects", "/api/admin/subjects/", _TTL_REFERENCE, force)

    async def get_all_teachers(self, force: bool = False) -> List[dict]:
        """Lấy danh sách Giảng viên. Cache 5 phút."""
        return await self._cached_fetch("teachers", "/api/admin/teachers/giangvien", _TTL_REFERENCE, force)

    async def create_teacher(self, payload: dict) -> dict:
        res = await self.create("/api/admin/teachers/giangvien", payload)
        self.invalidate("teachers")
        return res

    async def update_teacher(self, id: int, payload: dict) -> dict:
        res = await self.update(f"/api/admin/teachers/giangvien/{id}", payload)
        self.invalidate("teachers")
        return res

    async def delete_teacher(self, id: int) -> dict:
        res = await self.delete(f"/api/admin/teachers/giangvien/{id}")
        self.invalidate("teachers")
        return res

    async def create_teacher_auth(self, id: int, email: str, password: str) -> dict:
        """Tạo tài khoản Supabase Auth cho giảng viên."""
        return await self.create(f"/api/admin/teachers/giangvien/{id}/create-auth", {"email": email, "password": password})

    async def get_weeks(self, semester_id: str, force: bool = False) -> List[dict]:
        """Lấy danh sách Tuần học theo học kỳ. Cache 2 phút."""
        cache_key = f"weeks_{semester_id}"
        url = f"/api/schedule/tuan_hoc?hocky_id=eq.{semester_id}"
        return await self._cached_fetch(cache_key, url, _TTL_WEEKS, force)

    async def get_all_periods(self, force: bool = False) -> List[dict]:
        """Lấy cấu hình các tiết học (periods). Cache 5 phút."""
        return await self._cached_fetch("periods", "/api/schedule/tiet", _TTL_REFERENCE, force)

    # ─── REALTIME DATA (không cache) ──────────────────────────────

    async def get_students(self) -> List[dict]:
        """Lấy danh sách Sinh viên — không cache (dữ liệu lớn, thay đổi thường xuyên)."""
        return await self._fetch_list("/api/admin/system/sinhvien")

    async def get_system_stats(self) -> dict:
        """Lấy thống kê tổng quan cho Dashboard Admin — không cache."""
        try:
            client = await get_supabase_client()
            res = await client.get("/api/admin/system/stats")
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"[AdminService] get_system_stats error: {e}")
        return {}

    async def get_audit_logs(self, limit: int = 20) -> List[dict]:
        """Lấy nhật ký hoạt động — không cache (cần realtime)."""
        try:
            client = await get_supabase_client()
            res = await client.get("/api/admin/system/audit", params={"limit": limit})
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"[AdminService] get_audit_logs error: {e}")
        return []

    # ─── SCHEDULING (Dữ liệu thời gian thực) ───────────────────────

    async def get_busy_slots(self, hocky_id: int, gv_id: int = None, lop_id: str = None, phong: str = None, week_id: int = None) -> List[dict]:
        """Lấy danh sách tiết đã bận cho Grid UI."""
        params = {"hocky_id": hocky_id}
        if gv_id: params["giangvien_id"] = gv_id
        if lop_id: params["lop_id"] = lop_id
        if phong: params["phong_hoc"] = phong
        if week_id: params["week_id"] = week_id
        
        try:
            client = await get_supabase_client()
            res = await client.get("/api/schedule/busy_slots", params=params)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"[AdminService] get_busy_slots error: {e}")
        return []

    async def setup_schedule_batch(self, payload: dict) -> dict:
        """Lưu toàn bộ lịch đã sắp vào DB."""
        return await self.create("/api/schedule/thoikhoabieu/setup_batch", payload)

    async def delete_schedule(self, id: int) -> dict:
        """Xóa một lịch học (kiểm tra điểm danh ở backend)."""
        return await self.delete(f"/api/schedule/thoikhoabieu/{id}")

    async def get(self, url: str, params: dict = None) -> Any:
        """
        Gọi GET để lấy dữ liệu từ URL bất kỳ.
        Tự động lọc bỏ các tham số None hoặc rỗng để tránh lỗi 422.
        Giữ nguyên "all" vì có thể là giá trị hợp lệ của Server.
        """
        try:
            # Làm sạch params
            clean_params = {}
            if params:
                for k, v in params.items():
                    # Chỉ lọc None và chuỗi thực sự rỗng
                    if v is not None and str(v).strip() != "":
                        clean_params[k] = v

            client = await get_supabase_client()
            res = await client.get(url, params=clean_params)
            if res.status_code == 200:
                return res.json()
            raise Exception(f"HTTP {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[AdminService] GET {url} error: {e}")
            raise e

    # ─── CRUD Operations ──────────────────────────────────────────

    async def create(self, url: str, payload: dict) -> dict:
        """
        Gọi POST để tạo bản ghi mới.
        Trả về response JSON nếu thành công, raise Exception nếu lỗi.
        """
        client = await get_supabase_client()
        res = await client.post(url, json=payload)
        if res.status_code in (200, 201):
            return res.json()
        raise Exception(f"HTTP {res.status_code}: {res.text}")

    async def update(self, url: str, payload: dict) -> dict:
        """
        Gọi PUT để cập nhật bản ghi.
        Trả về response JSON nếu thành công, raise Exception nếu lỗi.
        """
        client = await get_supabase_client()
        res = await client.put(url, json=payload)
        if res.status_code == 200:
            return res.json()
        raise Exception(f"HTTP {res.status_code}: {res.text}")

    async def delete(self, url: str) -> dict:
        """
        Gọi DELETE để xóa bản ghi.
        Trả về response JSON nếu thành công, raise Exception nếu lỗi.
        """
        client = await get_supabase_client()
        res = await client.delete(url)
        if res.status_code == 200:
            return res.json()
        raise Exception(f"HTTP {res.status_code}: {res.text}")

    # ─── Config Management ────────────────────────────────────────

    async def get_all_configs(self) -> List[dict]:
        """Lấy toàn bộ config (bao gồm sensitive) — dành cho admin settings page."""
        return await self._cached_fetch("system_configs", "/api/admin/system-config/", _TTL_CONFIG)

    async def save_configs_batch(self, configs: List[dict]) -> dict:
        """
        Lưu hàng loạt config qua POST /batch.
        Sau khi lưu, invalidate cache config để lần đọc tiếp nhận giá trị mới.
        """
        client = await get_supabase_client()
        res = await client.post("/api/admin/system-config/batch", json=configs)
        if res.status_code == 200:
            self.invalidate("system_configs")
            # Reload config vào shared cache
            await self.load_system_config()
            return res.json()
        raise Exception(f"HTTP {res.status_code}: {res.text}")

    # ── ATTENDANCE ADMIN ──────────────────────────────────────────

    async def create_manual_attendance(self, payload: dict) -> dict:
        """Admin điểm danh thủ công cho sinh viên."""
        return await self.create("/api/admin/attendance/manual", payload)

    async def delete_attendance(self, id: int) -> dict:
        """Admin xóa bản ghi điểm danh."""
        return await self.delete(f"/api/admin/attendance/{id}")
