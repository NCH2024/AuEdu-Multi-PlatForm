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
    action: Optional[str] = None,
    entity: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    exclude_admins: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách nhật ký hoạt động hệ thống với bộ lọc."""
    stmt = (
        select(AuditLog, GiangVien.hodem, GiangVien.ten, GiangVien.vai_tro)
        .join(GiangVien, AuditLog.user_id == GiangVien.id, isouter=True)
    )
    
    # Áp dụng bộ lọc
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    
    if exclude_admins:
        # Loại bỏ các log của admin và super_admin, nhưng giữ lại log hệ thống (user_id IS NULL) và log của giảng viên
        from sqlalchemy import or_
        stmt = stmt.where(or_(
            AuditLog.user_id.is_(None),
            GiangVien.vai_tro == 'giangvien'
        ))
    
    if date_from:

        try:
            d_from = datetime.datetime.strptime(date_from, "%Y-%m-%d")
            stmt = stmt.where(AuditLog.created_at >= d_from)
        except ValueError:
            pass
            
    if date_to:
        try:
            d_to = datetime.datetime.strptime(date_to, "%Y-%m-%d")
            # Tăng thêm 1 ngày để bao gồm cả ngày kết thúc
            d_to = d_to + datetime.timedelta(days=1)
            stmt = stmt.where(AuditLog.created_at < d_to)
        except ValueError:
            pass

    stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    logs = []
    for row in result.all():
        log, hodem, ten, vai_tro = row
        user_name = f"{hodem} {ten}" if hodem and ten else "Hệ thống"
        logs.append({
            "id": log.id,
            "time": log.created_at.strftime("%H:%M %d/%m/%Y") if log.created_at else "N/A",
            "user": user_name,
            "action": log.action,
            "entity": log.entity,
            "entity_id": log.entity_id,
            "details": log.details,
            "ip_address": log.ip_address
        })
        
    return logs

@router.get("/audit/metadata")
async def get_audit_metadata(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách các hành động và thực thể duy nhất cho bộ lọc."""
    actions_stmt = select(AuditLog.action).distinct()
    entities_stmt = select(AuditLog.entity).distinct().where(AuditLog.entity.isnot(None))
    
    actions_res = await db.execute(actions_stmt)
    entities_res = await db.execute(entities_stmt)
    
    return {
        "actions": [a for a in actions_res.scalars().all()],
        "entities": [e for e in entities_res.scalars().all()]
    }

@router.get("/env")
async def get_system_env():
    """Lấy cấu hình môi trường cục bộ của Server (Read-only)."""
    from app.core.config import (
        SUPABASE_URL, SUPABASE_KEY, SUPABASE_STORAGE_BUCKET, 
        ANTI_SPOOF_MODEL, MAX_QUEUE_SIZE
    )
    
    # Masking key nhạy cảm để bảo mật
    masked_key = f"{SUPABASE_KEY[:6]}...{SUPABASE_KEY[-4:]}" if SUPABASE_KEY else "N/A"
    
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_key_masked": masked_key,
        "supabase_bucket": SUPABASE_STORAGE_BUCKET,
        "anti_spoof_model": ANTI_SPOOF_MODEL,
        "max_queue_size": MAX_QUEUE_SIZE,
        "server_status": "Running"
    }
