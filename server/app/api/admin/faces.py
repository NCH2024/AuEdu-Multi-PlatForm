from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from app.db.session import get_db
from app.db.models import SinhVien, FaceEmbedding, Lop

router = APIRouter()

@router.get("/stats")
async def get_face_stats(db: AsyncSession = Depends(get_db)):
    """Thống kê tổng quan dữ liệu khuôn mặt."""
    total = await db.scalar(select(func.count(SinhVien.id)))
    trained = await db.scalar(select(func.count(FaceEmbedding.sv_id)))
    return {
        "total_students": total or 0,
        "trained_students": trained or 0,
        "pending_students": (total or 0) - (trained or 0)
    }

@router.get("/list")
async def get_students_face_list(
    class_id: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None, # "trained", "pending"
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách sinh viên kèm trạng thái khuôn mặt."""
    query = select(
        SinhVien.id,
        SinhVien.hodem,
        SinhVien.ten,
        SinhVien.anhdaidien,
        Lop.tenlop,
        FaceEmbedding.updated_at.label("trained_at")
    ).outerjoin(FaceEmbedding, SinhVien.id == FaceEmbedding.sv_id)\
     .outerjoin(Lop, SinhVien.class_id == Lop.id)

    filters = []
    if class_id and class_id != "all":
        filters.append(SinhVien.class_id == class_id)
    if search:
        filters.append(and_(
            (SinhVien.ten.ilike(f"%{search}%")) | (func.cast(SinhVien.id, str).ilike(f"%{search}%"))
        ))
    
    if status == "trained":
        filters.append(FaceEmbedding.sv_id.isnot(None))
    elif status == "pending":
        filters.append(FaceEmbedding.sv_id.is_(None))

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Lop.tenlop, SinhVien.ten)
    result = await db.execute(query)
    
    data = []
    for r in result.all():
        data.append({
            "id": r.id,
            "full_name": f"{r.hodem} {r.ten}",
            "tenlop": r.tenlop or "N/A",
            "anhdaidien": r.anhdaidien,
            "has_face": r.trained_at is not None,
            "trained_at": r.trained_at.strftime("%d/%m/%Y %H:%M") if r.trained_at else None
        })
    
    return data

@router.delete("/{sv_id}")
async def delete_face_data(sv_id: int, db: AsyncSession = Depends(get_db)):
    """Xóa dữ liệu khuôn mặt của sinh viên."""
    stmt = select(FaceEmbedding).where(FaceEmbedding.sv_id == sv_id)
    result = await db.execute(stmt)
    face = result.scalar_one_or_none()
    
    if not face:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu khuôn mặt")
    
    await db.delete(face)
    await db.commit()
    return {"message": "Đã xóa dữ liệu khuôn mặt thành công"}
