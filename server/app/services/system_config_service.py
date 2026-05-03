# Server/app/services/system_config_service.py
import json
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SystemConfig
from app.db.session import AsyncSessionLocal

class SystemConfigService:
    _instance = None
    _config_cache: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemConfigService, cls).__new__(cls)
        return cls._instance

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = SystemConfigService()
        return cls._instance

    async def refresh_cache(self):
        """Tải toàn bộ cấu hình từ Database vào Cache."""
        print("\n[SystemConfig] 🔄 Đang tải cấu hình hệ thống từ Database...")
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(SystemConfig))
                configs = result.scalars().all()
                
                new_cache = {}
                for cfg in configs:
                    new_cache[cfg.key] = cfg.value
                
                self._config_cache = new_cache
                self._log_current_config()
        except Exception as e:
            print(f"[SystemConfig] ❌ Lỗi khi tải cấu hình: {e}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị cấu hình từ cache."""
        return self._config_cache.get(key, default)

    def get_ai_threshold(self) -> float:
        val = self.get_config("ai_threshold", 0.45)
        try: return float(val)
        except: return 0.45

    def get_fiqa_threshold(self) -> float:
        val = self.get_config("fiqa_threshold", 0.05)
        try: return float(val)
        except: return 0.05

    def get_anti_spoof_threshold(self) -> float:
        val = self.get_config("anti_spoof_threshold", 0.15)
        try: return float(val)
        except: return 0.15

    def get_min_face_area(self) -> int:
        val = self.get_config("min_face_area", 900)
        try: return int(val)
        except: return 900

    def _log_current_config(self):
        """In các tham số quan trọng ra Terminal."""
        print(" [AI Thresholds] ──────────────────────────────────────────")
        print(f"  • Recognition (Cosine): {self.get_ai_threshold()}")
        print(f"  • Anti-Spoofing:       {self.get_anti_spoof_threshold()}")
        print(f"  • Quality (FIQA):      {self.get_fiqa_threshold()}")
        print(f"  • Min Face Area:       {self.get_min_face_area()} px")
        print(" ──────────────────────────────────────────────────────────\n")

# Singleton Instance
config_service = SystemConfigService.instance()
