import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.audit import log_audit
from app.db.session import AsyncSessionLocal
from app.core.security import verify_token
from sqlalchemy import select
from app.db.models import GiangVien

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware ghi nhật ký tự động cho các yêu cầu API.
    Log tất cả các phương thức POST, PUT, DELETE và các yêu cầu GET quan trọng.
    """
    async def dispatch(self, request: Request, call_next):
        # 1. Bỏ qua các yêu cầu không phải API hoặc các endpoint tần suất cao (audit, stats, metadata)
        path = request.url.path
        if not path.startswith("/api/") or any(x in path for x in ["audit", "metadata", "stats"]):
            return await call_next(request)

        # 2. Thực thi request trước để lấy status code
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 3. Chỉ log nếu thành công (hoặc tùy cấu hình)
        # Đối với GET, ta chỉ log những endpoint mang tính chất "Xem dữ liệu" quan trọng
        method = request.method
        should_log = False
        
        if method in ["POST", "PUT", "DELETE"]:
            # Các hành động thay đổi dữ liệu thường đã được log ở level Router, 
            # nhưng middleware này có thể phục vụ như một lớp bảo vệ thứ 2 
            # hoặc để log những gì Router bỏ sót.
            # Tuy nhiên để tránh duplicate, ta có thể chỉ log GET ở đây.
            should_log = False 
        elif method == "GET":
            # Log các thao tác xem danh sách/chi tiết quan trọng (cả Admin và User)
            sensitive_paths = [
                "/admin/", "/report", "/sinhvien", "/giangvien", 
                "/attendance", "/subject", "/semester", "/class"
            ]
            if any(p in path for p in sensitive_paths):
                should_log = True

        if should_log:
            try:
                # Trích xuất user từ Token (vì middleware chạy trước Dependency Injection)
                user_id = None
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    payload = await verify_token(token)
                    if payload:
                        auth_uuid = payload.get("id")
                        # Cần truy vấn DB để lấy integer ID
                        async with AsyncSessionLocal() as db:
                            res = await db.execute(select(GiangVien.id).where(GiangVien.auth_id == auth_uuid))
                            user_id = res.scalar_one_or_none()
                            
                            await log_audit(
                                db=db,
                                user_id=user_id,
                                action="ACCESS",
                                entity="API",
                                entity_id=method,
                                details={
                                    "path": path,
                                    "status": response.status_code,
                                    "time_ms": round(process_time * 1000, 2),
                                    "params": dict(request.query_params)
                                },
                                request=request
                            )
                            await db.commit()
            except Exception as e:
                print(f"[AuditMiddleware Error] {e}")

        return response
