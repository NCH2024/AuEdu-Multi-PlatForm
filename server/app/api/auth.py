# server/app/api/auth.py
import os
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends

router = APIRouter()

from app.core.config import SUPABASE_URL, SUPABASE_KEY


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import GiangVien
from app.core.audit import log_audit
from app.core.security import get_device_metadata, get_current_user_id

@router.post("/v1/token")
async def login_proxy(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    device_info: dict = Depends(get_device_metadata)
):
    """
    Proxy tới Supabase để client không phải biết URL thực tế.
    """
    body = await request.json()
    grant_type = request.query_params.get("grant_type", "password")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type={grant_type}",
            json=body,
            headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        )
    
    if resp.status_code != 200:
        # Ghi log đăng nhập thất bại (Tùy chọn, nhưng tốt cho bảo mật)
        await log_audit(
            db=db,
            user_id=None, # System/Anonymous
            action="LOGIN_FAILED",
            entity="Auth",
            details={"email": body.get("email"), "status_code": resp.status_code, "device_info": device_info},
            request=request
        )
        await db.commit()
        raise HTTPException(status_code=resp.status_code, detail=resp.json())
    
    res_data = resp.json()
    
    # --- AUDIT LOGGING ---
    try:
        # Lấy UUID từ response của Supabase
        auth_uuid = res_data.get("user", {}).get("id")
        if auth_uuid:
            # Tìm gv_id tương ứng
            stmt = select(GiangVien.id).where(GiangVien.auth_id == auth_uuid)
            res_gv = await db.execute(stmt)
            gv_id = res_gv.scalar_one_or_none()
            
            # Ghi log thành công (luôn ghi, kể cả không tìm thấy gv_id trong bảng nội bộ)
            await log_audit(
                db=db,
                user_id=gv_id, # Có thể là None nếu chưa map gv_id
                action="LOGIN",
                entity="Auth",
                details={
                    "email": body.get("email"),
                    "auth_uuid": auth_uuid,
                    "device_info": device_info
                },
                request=request
            )
            await db.commit()
    except Exception as e:
        print(f"[Auth Proxy Log Error] {e}")

    return res_data

@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    gv_id: int = Depends(get_current_user_id)
):
    """Ghi nhật ký đăng xuất."""
    await log_audit(
        db=db,
        user_id=gv_id,
        action="LOGOUT",
        entity="Auth",
        request=request
    )
    await db.commit()
    return {"message": "Logged out successfully"}
