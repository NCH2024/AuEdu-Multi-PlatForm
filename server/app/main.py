# server/app/main.py
from fastapi import FastAPI
from app.api import (
    auth, teachers, schedule, attendance,
    training, reports
)

def create_app() -> FastAPI:
    app = FastAPI(
        title="AuEdu – Attendance System",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # ==== Đăng ký routers ====
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(teachers.router, tags=["giangvien"])
    app.include_router(schedule.router, tags=["schedule"])
    # attendance (REST)
    app.include_router(attendance.routes.router, tags=["attendance"])
    # attendance (WebSocket)
    app.include_router(attendance.ws.router, tags=["attendance-ws"])
    # training (face‑training)
    app.include_router(training.router, prefix="/training", tags=["training"])
    # reports
    app.include_router(reports.router, prefix="/export", tags=["reports"])

    return app

app = create_app()
