# Client/core/base_service.py
"""
BaseService — Lớp cơ sở cho tầng dịch vụ (Service Layer).
Cung cấp:
  - Memory cache với TTL (Time-To-Live)
  - Truy xuất system_config từ server
  - Pattern singleton cho các lớp con
"""

import time
import flet as ft
from typing import Any, Optional, Dict
from core.config import get_supabase_client, reset_client


class CacheEntry:
    """Đối tượng lưu trữ dữ liệu cache kèm timestamp."""

    __slots__ = ("data", "timestamp")

    def __init__(self, data: Any, timestamp: float):
        self.data = data
        self.timestamp = timestamp


class BaseService:
    """
    Lớp cơ sở cung cấp memory cache + system_config access.
    Các lớp con (AdminService, UserService) kế thừa để tái sử dụng
    logic cache và config mà không phải lặp code.
    """

    # Config chia sẻ giữa mọi instance (class-level)
    _system_config: Dict[str, Any] = {}
    _config_loaded: bool = False

    def __init__(self):
        self._memory_cache: Dict[str, CacheEntry] = {}

    # ─── System Config ────────────────────────────────────────────

    async def load_system_config(self) -> Dict[str, Any]:
        """
        Fetch system_config từ server (GET /api/admin/system-config/public).
        Kết quả lưu vào class-level cache, chia sẻ giữa AdminService & UserService.
        Trả về dict {key: value}.
        """
        try:
            client = await get_supabase_client()
            res = await client.get("/api/admin/system-config/public")
            if res.status_code == 200:
                raw = res.json()
                BaseService._system_config = {
                    item["key"]: item["value"] for item in raw
                }
                BaseService._config_loaded = True

                # --- ĐỒNG BỘ URL API ---
                new_url = BaseService._system_config.get("server_api_url")
                if new_url:
                    # Reset httpx client runtime
                    reset_client(new_url)
                    # Lưu vào SharedPreferences để persist qua lần khởi động sau
                    try:
                        prefs = ft.SharedPreferences()
                        await prefs.set("server_api_url", new_url)
                    except Exception as e_pref:
                        print(f"[BaseService] SharedPreferences error: {e_pref}")
        except Exception as e:
            print(f"[BaseService] load_system_config error: {e}")
        return BaseService._system_config

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Đọc giá trị config theo key.
        Trả về default nếu key chưa được load hoặc không tồn tại.
        """
        return BaseService._system_config.get(key, default)

    @property
    def config_loaded(self) -> bool:
        """Kiểm tra config đã được fetch từ server chưa."""
        return BaseService._config_loaded

    # ─── Memory Cache ─────────────────────────────────────────────

    def _is_cache_valid(self, key: str, ttl: float) -> bool:
        """Kiểm tra entry trong cache còn hiệu lực (chưa hết TTL) hay không."""
        entry = self._memory_cache.get(key)
        if entry is None:
            return False
        return (time.time() - entry.timestamp) < ttl

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Lấy dữ liệu từ cache. Trả về None nếu chưa có."""
        entry = self._memory_cache.get(key)
        return entry.data if entry else None

    def _set_cache(self, key: str, data: Any) -> None:
        """Ghi dữ liệu vào cache với timestamp hiện tại."""
        self._memory_cache[key] = CacheEntry(data, time.time())

    def invalidate(self, key: str) -> None:
        """Xóa một entry khỏi cache (buộc fetch lại lần tiếp theo)."""
        self._memory_cache.pop(key, None)

    def invalidate_all(self) -> None:
        """Xóa toàn bộ cache (dùng khi đổi phiên hoặc logout)."""
        self._memory_cache.clear()
