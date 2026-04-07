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

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Hàm này tự động đọc Header 'Authorization: Bearer <token>' từ Client gửi lên.
    """
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
        
    # Nếu thành công, trả về thông tin user đã giải mã từ Supabase
    return response.json()