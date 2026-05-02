from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.db.models import ThongBao, SinhVien, GiangVien, Lop, DiemDanh, AuditLog
from datetime import datetime

router = APIRouter()

def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict (sử dụng trong mọi router)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/thongbao")
async def get_thongbao(limit: int = 3, db: AsyncSession = Depends(get_db)):
    stmt = select(ThongBao).order_by(ThongBao.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    res = []
    for t in result.scalars().all():
        d = model_to_dict(t)
        d["created_at"] = str(t.created_at) if t.created_at else None
        res.append(d)
    return res

@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    # 1. Tổng người dùng (Sinh viên + Giảng viên)
    sv_count = await db.scalar(select(func.count(SinhVien.id))) or 0
    gv_count = await db.scalar(select(func.count(GiangVien.id))) or 0
    
    # 2. Tổng số lớp
    lop_count = await db.scalar(select(func.count(Lop.id))) or 0
    
    # 3. Lượt điểm danh hôm nay
    today = datetime.now().date()
    att_today = await db.scalar(select(func.count(DiemDanh.sv_id)).where(DiemDanh.ngay_diem_danh == today)) or 0
    
    return {
        "total_users": sv_count + gv_count,
        "total_classes": lop_count,
        "today_att": att_today,
        "sys_load": "12%" # Mock giá trị giả định
    }

@router.get("/audit")
async def get_audit_logs(limit: int = 5, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(AuditLog, GiangVien.ten)
        .join(GiangVien, AuditLog.user_id == GiangVien.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = []
    for log, gv_ten in result.all():
        logs.append({
            "time": log.created_at.strftime("%H:%M %d/%m"),
            "user": gv_ten,
            "action": log.action,
            "details": f"{log.entity}: {log.entity_id}" if log.entity else "N/A"
        })
    return logs