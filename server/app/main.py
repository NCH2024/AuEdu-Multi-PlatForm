# server/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    auth, teachers, schedule, training, students, system,
    departments, semesters, classes, system_config, system_status, subjects, notifications
)
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
    app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
    app.include_router(system.router, tags=["system"])
    app.include_router(training.router, prefix="/training", tags=["training"])
    
    # ── admin CRUD ────────
    app.include_router(departments.router, prefix="/api/admin/departments", tags=["admin-departments"])
    app.include_router(semesters.router, prefix="/api/admin/semesters", tags=["admin-semesters"])
    app.include_router(classes.router, prefix="/api/admin/classes", tags=["admin-classes"])
    app.include_router(system_config.router, prefix="/api/admin/system-config", tags=["admin-system-config"])
    app.include_router(system_status.router, prefix="/api/admin/system", tags=["admin-system-status"])
    app.include_router(students.router, prefix="/api/admin/system", tags=["admin-students"])
    app.include_router(subjects.router, prefix="/api/admin/subjects", tags=["admin-subjects"])
    app.include_router(notifications.router, prefix="/api/admin/notifications", tags=["admin-notifications"])
    app.include_router(teachers.router, prefix="/api/admin/teachers", tags=["admin-teachers"])
    
    # ── reports ───────
    app.include_router(excel.router, prefix="/export", tags=["reports"])

    # ── attendance (REST) ───────
    app.include_router(attendance_routes.router, prefix="/api/attendance", tags=["attendance"])
    # ── attendance (WebSocket) ─
    app.include_router(attendance_ws.router, prefix="/api/ws/attendance", tags=["attendance-ws"])
    
    return app

app = create_app()
