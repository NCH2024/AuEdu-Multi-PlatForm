# Server_Core/app/core/security.py
from fastapi import HTTPException, Depends
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