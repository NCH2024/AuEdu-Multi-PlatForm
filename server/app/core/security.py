# Server_Core/app/core/security.py
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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