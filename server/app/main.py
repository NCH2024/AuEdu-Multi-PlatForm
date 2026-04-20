# server/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, teachers, schedule, training, students, system
from app.api.attendance import routes as attendance_routes
from app.api.attendance import ws as attendance_ws
from app.api.export import excel

def create_app() -> FastAPI:
    app = FastAPI(title="AuEdu")
    
    # CORS Middleware 
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Cho phép mọi nguồn kết nối (rất cần thiết cho Flet đa nền tảng)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
    
    # ── auth ─────────────────────
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    
    # ── các router khác ────────
    app.include_router(teachers.router, tags=["giangvien"])
    app.include_router(students.router, tags=["sinhvien"])
    app.include_router(schedule.router, tags=["schedule"])
    app.include_router(system.router, tags=["system"])
    app.include_router(training.router, prefix="/training", tags=["training"])
    
    # ── reports ───────
    app.include_router(excel.router, prefix="/export", tags=["reports"])

    # ── attendance (REST) ───────
    app.include_router(attendance_routes.router, prefix="/api/attendance", tags=["attendance"])
    # ── attendance (WebSocket) ─
    app.include_router(attendance_ws.router, prefix="/api/ws/attendance", tags=["attendance-ws"])
    
    return app

app = create_app()
