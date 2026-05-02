from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.db.session import get_db
from app.db.models import SinhVien, Lop, DiemDanh, AuditLog, GiangVien
from typing import List, Optional
import datetime

router = APIRouter()

@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """Lấy số liệu thống kê tổng quan cho Dashboard Admin."""
    # Tổng số sinh viên
    total_students = await db.scalar(select(func.count(SinhVien.id)))
    
    # Tổng số lớp
    total_classes = await db.scalar(select(func.count(Lop.id)))
    
    # Lượt điểm danh hôm nay
    today = datetime.date.today()
    today_attendance = await db.scalar(
        select(func.count(DiemDanh.id)).where(DiemDanh.ngay_diem_danh == today)
    )
    
    # Tải hệ thống (Mock - thực tế có thể dùng psutil nếu server cho phép)
    import random
    sys_load = f"{random.randint(10, 40)}%"

    return {
        "total_users": total_students or 0,
        "total_classes": total_classes or 0,
        "today_att": today_attendance or 0,
        "sys_load": sys_load
    }

@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách nhật ký hoạt động hệ thống."""
    stmt = (
        select(AuditLog, GiangVien.hodem, GiangVien.ten)
        .join(GiangVien, AuditLog.user_id == GiangVien.id, isouter=True)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(stmt)
    logs = []
    for row in result.all():
        log, hodem, ten = row
        user_name = f"{hodem} {ten}" if hodem and ten else "Hệ thống"
        logs.append({
            "id": log.id,
            "time": log.created_at.strftime("%H:%M %d/%m/%Y") if log.created_at else "N/A",
            "user": user_name,
            "action": log.action,
            "entity": log.entity,
            "details": log.details,
            "ip_address": log.ip_address
        })
        
    return logs
