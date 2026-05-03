from typing import Any, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog
import json

async def log_audit(
    db: AsyncSession,
    user_id: int,
    action: str,
    entity: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Any] = None,
    request: Optional[Request] = None
):
    """
    Ghi nhật ký hệ thống (Audit Log).
    Đảm bảo tính ổn định: Nếu lỗi ghi log xảy ra, hệ thống vẫn tiếp tục hoạt động.
    """
    try:
        ip_address = None
        user_agent = None
        
        if request:
            # Lấy IP từ header nếu có proxy (Nginx/Cloudflare)
            ip_address = request.headers.get("x-forwarded-for") or request.client.host
            user_agent = request.headers.get("user-agent")

        # Chuẩn hóa details về JSON string nếu nó là dict/list
        if details and not isinstance(details, (str, int, float, bool)):
            try:
                # Nếu là model Pydantic hoặc object có method model_dump
                if hasattr(details, "model_dump"):
                    details = details.model_dump()
            except Exception:
                pass

        new_log = AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(new_log)
        # Lưu ý: Không gọi db.commit() ở đây để tránh side-effect. 
        # Việc commit nên được thực hiện cùng với transaction của API gọi nó.
        # Tuy nhiên, nếu API đã commit trước đó, ta cần flush hoặc commit riêng.
        # Để an toàn và tách biệt, ta dùng flush().
        await db.flush()
        
    except Exception as e:
        # Fail-safe: Chỉ log lỗi ra console, không làm sập API chính
        print(f"[AUDIT LOG ERROR] Failed to record log: {e}")
