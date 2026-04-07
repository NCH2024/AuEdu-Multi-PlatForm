# Server_Core/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router # Dòng thêm mới

app = FastAPI(title="AuEdu Server API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gắn toàn bộ API trong file routes.py vào tiền tố /api
app.include_router(api_router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": "AUEDU đã sẵng sàng!"}