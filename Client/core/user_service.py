# Client/core/user_service.py
"""
UserService — Singleton quản lý tập trung mọi API call phía User (Giảng viên).

Đặc điểm:
  - 2-layer cache: Memory → SharedPreferences (hỗ trợ offline/mobile)
  - TTL đọc từ system_config thay vì hardcode
  - Giảm code lặp: thay vì mỗi trang tự implement 20-60 dòng cache logic,
    chỉ cần gọi 1 method

Sử dụng:
    from core.user_service import UserService
    svc = UserService.instance()
    svc.set_gv_id(gv_id)
    news = await svc.get_news()
    schedule = await svc.get_schedule()
"""

import flet as ft
import json
import time
import asyncio
from typing import Any, Dict, List, Optional
from core.base_service import BaseService
from core.config import get_supabase_client
from core.helper import hash_data, safe_json_load


# ─── TTL mặc định (giây) — sẽ bị ghi đè bởi system_config ────
_DEFAULT_TTL_NEWS       = 300       # 5 phút
_DEFAULT_TTL_SCHEDULE   = 21600     # 6 giờ
_DEFAULT_TTL_TODAY      = 300       # 5 phút
_DEFAULT_TTL_STATS      = 86400     # 24 giờ


class UserService(BaseService):
    """
    Singleton Service Layer cho các trang User (Giảng viên).
    Quản lý dữ liệu lịch dạy, điểm danh, thống kê với cache 2 tầng.
    """

    _instance: Optional["UserService"] = None

    @classmethod
    def instance(cls) -> "UserService":
        """Trả về singleton instance. Tạo mới nếu chưa có."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._gv_id: str = "N/A"

    # ─── Session ──────────────────────────────────────────────────

    def set_gv_id(self, gv_id: str) -> None:
        """Gán ID giảng viên cho phiên làm việc hiện tại."""
        self._gv_id = gv_id

    @property
    def gv_id(self) -> str:
        """ID giảng viên đang đăng nhập."""
        return self._gv_id

    def _get_ttl(self, config_key: str, default: float) -> float:
        """
        Đọc TTL từ system_config. Nếu chưa load config, trả về giá trị mặc định.
        Cho phép admin thay đổi TTL từ trang Cài đặt mà không cần sửa code.
        """
        val = self.get_config(config_key)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return default

    # ─── 2-Layer Cache Helper ─────────────────────────────────────

    async def _cached_fetch_with_prefs(
        self,
        cache_key: str,
        prefs_key: str,
        ttl_config_key: str,
        default_ttl: float,
        fetcher,
        force: bool = False
    ) -> Any:
        """
        Cache 2 tầng: Memory → SharedPreferences → API.
        
        Luồng xử lý:
          1. Kiểm tra memory cache — nếu còn hạn, trả về ngay
          2. Đọc SharedPreferences — nếu có + chưa hết TTL, dùng luôn
          3. Gọi API fetch mới → lưu cả 2 tầng

        Args:
            cache_key: Key trong memory cache
            prefs_key: Key trong SharedPreferences
            ttl_config_key: Key config để đọc TTL từ system_config
            default_ttl: TTL mặc định nếu chưa có config
            fetcher: Async function trả về data mới từ API
            force: Bỏ qua cache, luôn fetch mới
        """
        ttl = self._get_ttl(ttl_config_key, default_ttl)

        # Tầng 1: Memory cache
        if not force and self._is_cache_valid(cache_key, ttl):
            return self._get_from_cache(cache_key)

        prefs = ft.SharedPreferences()
        sync_key = f"last_sync_{cache_key}"

        # Tầng 2: SharedPreferences (offline / first-load nhanh)
        if not force:
            try:
                cached_str = await prefs.get(prefs_key)
                last_sync = float(await prefs.get(sync_key) or 0)
                if cached_str and (time.time() - last_sync < ttl):
                    data = safe_json_load(cached_str)
                    if data is not None:
                        self._set_cache(cache_key, data)
                        return data
            except Exception:
                pass

        # Tầng 3: Fetch từ API
        try:
            data = await fetcher()
            if data is not None:
                self._set_cache(cache_key, data)
                # Lưu xuống SharedPreferences không chặn UI
                current_time = str(time.time())
                await asyncio.gather(
                    prefs.set(prefs_key, json.dumps(data, default=str)),
                    prefs.set(sync_key, current_time),
                    return_exceptions=True
                )
            return data
        except Exception as e:
            print(f"[UserService] fetch {cache_key} error: {e}")
            # Fallback: trả về cache cũ nếu có
            return self._get_from_cache(cache_key)

    # ─── Tin tức / Thông báo ──────────────────────────────────────

    async def get_news(self, force: bool = False) -> List[dict]:
        """
        Lấy danh sách thông báo. Cache 5 phút (cấu hình: home_cache_ttl).
        Endpoint Supabase: /thongbao
        """
        async def _fetch():
            client = await get_supabase_client()
            res = await client.get("/thongbao", params={
                "select": "*",
                "order": "created_at.desc",
                "limit": "20"
            })
            res.raise_for_status()
            return res.json()

        return await self._cached_fetch_with_prefs(
            cache_key="news",
            prefs_key="cached_news",
            ttl_config_key="home_cache_ttl",
            default_ttl=_DEFAULT_TTL_NEWS,
            fetcher=_fetch,
            force=force
        ) or []

    # ─── Tuần học ─────────────────────────────────────────────────

    async def get_tuan_hoc(self, force: bool = False) -> List[dict]:
        """
        Lấy danh sách tuần học. Cache 6 giờ.
        Endpoint: /api/schedule/tuan_hoc
        """
        async def _fetch():
            client = await get_supabase_client()
            res = await client.get("/api/schedule/tuan_hoc", params={
                "select": "*",
                "order": "id.asc"
            })
            res.raise_for_status()
            return res.json()

        return await self._cached_fetch_with_prefs(
            cache_key="tuan_hoc",
            prefs_key="cached_tuan_hoc",
            ttl_config_key="schedule_cache_ttl",
            default_ttl=_DEFAULT_TTL_SCHEDULE,
            fetcher=_fetch,
            force=force
        ) or []

    # ─── Thời khóa biểu ──────────────────────────────────────────

    async def get_schedule_raw(self, force: bool = False) -> List[dict]:
        """
        Lấy thời khóa biểu (ThoiKhoaBieu) của giảng viên hiện tại.
        Cache 6 giờ theo gv_id.
        Endpoint: /api/schedule/thoikhoabieu
        """
        if self._gv_id == "N/A":
            return []

        async def _fetch():
            client = await get_supabase_client()
            res = await client.get("/api/schedule/thoikhoabieu", params={
                "select": "id,hocphan(tenhocphan),lop(tenlop)",
                "giangvien_id": f"eq.{self._gv_id}"
            })
            res.raise_for_status()
            return res.json()

        return await self._cached_fetch_with_prefs(
            cache_key=f"schedule_{self._gv_id}",
            prefs_key=f"cached_schedule_{self._gv_id}",
            ttl_config_key="schedule_cache_ttl",
            default_ttl=_DEFAULT_TTL_SCHEDULE,
            fetcher=_fetch,
            force=force
        ) or []

    # ─── TKB chi tiết (lịch dạy với tên lớp, môn, hocky) ────────

    async def get_tkb_full(self, force: bool = False) -> List[dict]:
        """
        Lấy TKB đầy đủ (có lop, hocphan, hocky) cho trang điểm danh.
        Không cache vì dùng cho CRUD selection.
        """
        if self._gv_id == "N/A":
            return []
        try:
            client = await get_supabase_client()
            res = await client.get("/api/schedule/thoikhoabieu", params={
                "select": "id,lop_id,hocphan_id,hocky_id,lop(tenlop),hocphan(tenhocphan),hocky(tenhocky,namhoc)",
                "giangvien_id": f"eq.{self._gv_id}"
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[UserService] get_tkb_full error: {e}")
            return []

    # ─── TKB Tiết ─────────────────────────────────────────────────

    async def get_tkb_tiet(self, tkb_ids: List[str], select: str = "id,tkb_id,thu,tiet_id,phong_hoc") -> List[dict]:
        """
        Lấy TKB tiết cho danh sách tkb_ids.
        Không cache — phụ thuộc vào tham số động.
        """
        if not tkb_ids:
            return []
        try:
            client = await get_supabase_client()
            res = await client.get("/api/schedule/tkb_tiet", params={
                "select": select,
                "tkb_id": f"in.({','.join(tkb_ids)})"
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[UserService] get_tkb_tiet error: {e}")
            return []

    # ─── Sinh viên theo lớp ───────────────────────────────────────

    async def get_students_by_class(self, class_id: str) -> List[dict]:
        """
        Lấy danh sách sinh viên theo lớp — không cache (cần realtime khi điểm danh).
        """
        try:
            client = await get_supabase_client()
            res = await client.get("/api/schedule/sinhvien", params={
                "select": "*",
                "class_id": f"eq.{class_id}",
                "order": "id.asc"
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[UserService] get_students_by_class error: {e}")
            return []

    # ─── Điểm danh ────────────────────────────────────────────────

    async def get_diemdanh(self, tkb_tiet_id: str, ngay: str) -> List[dict]:
        """
        Lấy trạng thái điểm danh cho một tiết cụ thể + ngày cụ thể.
        Không cache — cần realtime.
        """
        try:
            client = await get_supabase_client()
            res = await client.get("/api/schedule/diemdanh", params={
                "select": "sv_id,trang_thai",
                "tkb_tiet_id": f"eq.{tkb_tiet_id}",
                "ngay_diem_danh": f"eq.{ngay}"
            })
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"[UserService] get_diemdanh error: {e}")
            return []

    # ─── Thống kê ─────────────────────────────────────────────────

    async def get_stats(self, tkb_id: str, force: bool = False) -> Optional[dict]:
        """
        Lấy thống kê cho một TKB. Cache 24 giờ theo tkb_id.
        Dữ liệu nặng nên cache lâu, admin muốn refresh thì dùng force=True.
        """
        cache_key = f"stats_{tkb_id}"
        prefs_key = f"stats_tkb_{tkb_id}"

        async def _fetch():
            # Thống kê tính ở client-side từ raw data — chỉ fetch raw
            return None  # Placeholder: logic tính stats nằm ở page

        return await self._cached_fetch_with_prefs(
            cache_key=cache_key,
            prefs_key=prefs_key,
            ttl_config_key="stats_cache_ttl",
            default_ttl=_DEFAULT_TTL_STATS,
            fetcher=_fetch,
            force=force
        )

    # ─── Server API URL (từ config) ──────────────────────────────

    def get_server_api_url(self) -> str:
        """
        Lấy SERVER_API_URL từ system_config.
        Fallback về giá trị trong .env nếu chưa load config.
        Dùng cho các trang cần mở URL trong browser (export Excel, v.v.)
        """
        from core.config import SERVER_API_URL
        return self.get_config("server_api_url", SERVER_API_URL)
