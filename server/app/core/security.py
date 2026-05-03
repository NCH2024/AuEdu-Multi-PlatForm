# Server_Core/app/core/security.py
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import os
from app.core.config import SUPABASE_URL, SUPABASE_KEY

from app.db.session import get_db
from app.db.models import GiangVien

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials | str = Depends(security)):
    """
    Tự động đọc Header từ API hoặc nhận chuỗi token trực tiếp từ WebSocket.
    """
    # Xử lý thông minh: Nếu là chuỗi (từ WS) thì dùng luôn, nếu là Object (từ API) thì trích xuất
    if isinstance(credentials, str):
        token = credentials
    else:
        token = credentials.credentials
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_KEY
            }
        )
        
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")
        
    return response.json()

async def get_current_user_id(
    user_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Dependency để lấy ID (Integer) của giảng viên đang đăng nhập.
    """
    auth_uuid = user_payload.get("id")
    if not auth_uuid:
        raise HTTPException(status_code=401, detail="Không tìm thấy ID người dùng trong token")
        
    stmt = select(GiangVien.id).where(GiangVien.auth_id == auth_uuid)
    result = await db.execute(stmt)
    gv_id = result.scalar_one_or_none()
    
    if gv_id is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin giảng viên trong hệ thống")
        
    return gv_id

async def get_device_metadata(
    x_device_id: str = Header(default="Unknown"),
    x_client_version: str = Header(default="Unknown"),
    x_platform: str = Header(default="Unknown")
) -> dict:
    return {
        "device_id": x_device_id,
        "client_version": x_client_version,
        "platform": x_platform
    }