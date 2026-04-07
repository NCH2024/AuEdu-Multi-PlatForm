# Server_Core/app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import verify_token

app = FastAPI(title="AuEdu Server API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "Nhà bếp AuEdu AI Core đã sẵn sàng phục vụ!"}

# API công khai, ai cũng gọi được
@app.get("/api/ping")
async def ping_server():
    return {"status": "ok", "data": "Server đang chạy rất mượt!"}

# 🔒 API BẢO MẬT: Bắt buộc phải có Token hợp lệ từ Supabase
@app.get("/api/protected")
async def protected_route(user_info: dict = Depends(verify_token)):
    return {
        "message": "Chào mừng em đã vượt qua chốt chặn bảo mật!",
        "user_id": user_info.get("id"),
        "email": user_info.get("email")
    }