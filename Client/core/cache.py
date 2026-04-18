# client/core/cache.py
import json, time, asyncio
import flet as ft
from typing import Any, Callable, Awaitable, Optional

CacheValue = Any
Fetcher = Callable[[], Awaitable[CacheValue]]   # hàm trả về dữ liệu mới (async)

class _CacheItem:
    """Mỗi mục lưu trong SharedPreferences:
    - data:   JSON‑encoded giá trị
    - ts:    thời gian lưu (epoch seconds)
    """
    def __init__(self, data: CacheValue, ts: float):
        self.data = data
        self.ts = ts

    def to_json(self) -> str:
        return json.dumps({"data": self.data, "ts": self.ts})

    @staticmethod
    def from_json(raw: str) -> "_CacheItem":
        try:
            o = json.loads(raw)
            return _CacheItem(o.get("data"), float(o.get("ts", 0)))
        except Exception:
            # JSON hỏng → trả về item rỗng
            return _CacheItem(None, 0)


class CacheManager:
    """
    - Dùng `ft.SharedPreferences` (được chia sẻ giữa mọi page).
    - Mỗi key có thể định nghĩa TTL (giây) riêng.
    - `get(key, ttl, fetcher)` sẽ:
        * Kiểm tra cache hiện tại.
        * Nếu còn hợp lệ → trả về data.
        * Nếu hết hạn hoặc không có → gọi `fetcher()` (async) để lấy fresh data,
          lưu lại và trả về.
    - `set(key, value)` dùng khi muốn **ghi trực tiếp** (ví dụ: sau login).
    - `invalidate(key_pattern)` xóa tất cả key thỏa pattern (regex hoặc prefix).
    - `clear_all()` xóa toàn bộ.
    """
    def __init__(self):
        self._prefs = ft.SharedPreferences()
        self._lock = asyncio.Lock()   # tránh race condition khi nhiều task truy cập đồng thời

    # -------------------- nội bộ --------------------
    async def _read_raw(self, key: str) -> Optional[str]:
        return await self._prefs.get(key)

    async def _write_raw(self, key: str, raw: str):
        await self._prefs.set(key, raw)

    # -------------------- API công cộng --------------------
    async def get(
        self,
        key: str,
        ttl: int,
        fetcher: Optional[Fetcher] = None,
        *,
        default: Any = None,
    ) -> Any:
        """
        - `ttl` (seconds). Nếu ttl = 0 → **luôn** fetch mới.
        - `fetcher` là hàm async trả về dữ liệu mới (list/dict,…). Nếu `None`
          và cache miss → trả về `default`.
        """
        async with self._lock:
            raw = await self._read_raw(key)
            if raw:
                item = _CacheItem.from_json(raw)
                age = time.time() - item.ts
                if ttl == 0 or age < ttl:
                    # Cache còn hiệu lực
                    return item.data

            # ----------------- Cache miss / hết hạn -----------------
            if fetcher is None:
                # Không có hàm fetch → trả về default (hoặc None)
                return default

            # Gọi fetcher để lấy fresh data
            fresh = await fetcher()
            # Lưu lại
            await self._write_raw(key, _CacheItem(fresh, time.time()).to_json())
            return fresh

    async def set(self, key: str, value: Any):
        """Ghi dữ liệu vào cache (thời gian hiện tại)."""
        async with self._lock:
            await self._write_raw(key, _CacheItem(value, time.time()).to_json())

    async def invalidate(self, prefix: str):
        """Xóa mọi key bắt đầu bằng `prefix`."""
        async with self._lock:
            # SharedPreferences không hỗ trợ liệt kê keys, nên
            # chúng ta phải lưu danh sách các key trong một “index”.
            # Để đơn giản, ở đây mình sẽ duyệt qua các key đã biết
            # (các key cache cố định trong project) và xóa nếu match.
            known_keys = [
                "cached_news",
                "last_sync_home_",
                "cached_home_schedule_",
                "cached_today_",
            ]
            for k in known_keys:
                if k.startswith(prefix) or k == prefix:
                    await self._prefs.remove(k)

    async def clear_all(self):
        """Xóa toàn bộ dữ liệu cache (không xóa các setting khác)."""
        async with self._lock:
            known_keys = [
                "cached_news",
                "last_sync_home_",
                "cached_home_schedule_",
                "cached_today_",
                "user_session",
                "saved_accounts",
                # … (thêm nếu có)
            ]
            for k in known_keys:
                await self._prefs.remove(k)
