# client/core/cache.py
import json
import time
import asyncio
import flet as ft
from typing import Any, Callable, Awaitable, Optional

CacheValue = Any
Fetcher = Callable[[], Awaitable[CacheValue]]   # hàm trả về dữ liệu mới (async)

class _CacheItem:
    """Mỗi mục lưu trong SharedPreferences:
    - data: JSON‑encoded giá trị
    - ts: thời gian lưu (epoch seconds)
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
    - Dùng `ft.SharedPreferences` được chia sẻ giữa mọi page.
    - Quản lý linh hoạt TTL (giây) cho từng key riêng biệt.
    - Tự động fallback: Trả về dữ liệu cũ nếu fetcher gặp lỗi kết nối.
    - Tự động ghi nhớ keys đã cache để invalidate/clear_all dễ dàng.
    """
    def __init__(self):
        self._prefs = ft.SharedPreferences()
        self._lock = asyncio.Lock()   # tránh race condition khi nhiều task truy cập đồng thời
        self._index_key = "auedu_cache_index_keys" # Key ẩn để lưu danh sách các key đã tạo

    # -------------------- Nội bộ --------------------
    async def _read_raw(self, key: str) -> Optional[str]:
        return await self._prefs.get(key)

    async def _write_raw(self, key: str, raw: str):
        await self._prefs.set(key, raw)
        await self._register_key(key)

    async def _register_key(self, key: str):
        """Lưu lại key vào danh sách quản lý để lúc xóa không cần hardcode tên key"""
        try:
            raw_index = await self._prefs.get(self._index_key)
            keys = json.loads(raw_index) if raw_index else []
        except Exception:
            keys = []
            
        if key not in keys:
            keys.append(key)
            await self._prefs.set(self._index_key, json.dumps(keys))

    # -------------------- API Công cộng --------------------
    async def get(
        self,
        key: str,
        ttl: int,
        fetcher: Optional[Fetcher] = None,
        *,
        default: Any = None,
    ) -> Any:
        """
        - `ttl` (seconds). Nếu ttl = 0 → luôn fetch mới.
        - `fetcher` là hàm async trả về dữ liệu.
        - Tự động lấy cache, nếu hết hạn -> gọi fetcher -> lưu cache mới.
        """
        async with self._lock:
            raw = await self._read_raw(key)
            item = _CacheItem.from_json(raw) if raw else None
            
            if item and item.data is not None:
                age = time.time() - item.ts
                if ttl == 0 or age < ttl:
                    # Cache còn hiệu lực
                    return item.data

            # ----------------- Cache miss / Hết hạn -----------------
            if fetcher is None:
                return default

            try:
                # Gọi fetcher để lấy fresh data
                fresh = await fetcher()
                # Lưu lại cache mới
                await self._write_raw(key, _CacheItem(fresh, time.time()).to_json())
                return fresh
            except Exception as e:
                print(f"[CacheManager] Fetch error for key '{key}': {e}")
                # FALLBACK AN TOÀN: Nếu lỗi mạng nhưng vẫn có cache cũ, trả về cache cũ thay vì làm trống UI
                return item.data if (item and item.data is not None) else default

    async def set(self, key: str, value: Any):
        """Ghi dữ liệu vào cache bỏ qua TTL."""
        async with self._lock:
            await self._write_raw(key, _CacheItem(value, time.time()).to_json())

    async def invalidate(self, prefix: str):
        """Xóa mọi key bắt đầu bằng `prefix`. Rất hữu ích khi user logout hoặc cần xóa cache 1 page cụ thể."""
        async with self._lock:
            try:
                raw_index = await self._prefs.get(self._index_key)
                keys = json.loads(raw_index) if raw_index else []
            except Exception:
                keys = []
            
            keys_to_keep = []
            for k in keys:
                if k.startswith(prefix) or k == prefix:
                    await self._prefs.remove(k)
                else:
                    keys_to_keep.append(k)
            
            # Cập nhật lại danh sách index
            await self._prefs.set(self._index_key, json.dumps(keys_to_keep))

    async def clear_all(self):
        """Xóa toàn bộ dữ liệu cache mà hệ thống đã ghi nhận."""
        async with self._lock:
            try:
                raw_index = await self._prefs.get(self._index_key)
                keys = json.loads(raw_index) if raw_index else []
            except Exception:
                keys = []
            
            for k in keys:
                await self._prefs.remove(k)
            
            await self._prefs.remove(self._index_key)

# ==========================================
# KHỞI TẠO BIẾN TOÀN CỤC ĐỂ DÙNG CHUNG
# ==========================================
app_cache = CacheManager()