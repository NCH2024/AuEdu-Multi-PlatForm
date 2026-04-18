# server/app/main.py
from fastapi import FastAPI

from app.api import auth, teachers, schedule, training, reports
from app.api.attendance import routes as attendance_routes
from app.api.attendance import ws as attendance_ws

def create_app() -> FastAPI:
    app = FastAPI(title="AuEdu")
    # ── auth ─────────────────────
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    # ── các router khác ────────
    app.include_router(teachers.router, tags=["giangvien"])
    app.include_router(schedule.router, tags=["schedule"])
    app.include_router(training.router, prefix="/training", tags=["training"])
    app.include_router(reports.router, prefix="/export", tags=["reports"])
    # ── attendance (REST) ───────
    app.include_router(attendance_routes.router, tags=["attendance"])
    # ── attendance (WebSocket) ─
    app.include_router(attendance_ws.router, tags=["attendance-ws"])
    return app

app = create_app()
