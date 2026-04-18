from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import SinhVien

router = APIRouter()

def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict (sử dụng trong mọi router)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/sinhvien")
async def get_danh_sach_sinh_vien(class_id: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SinhVien)
    if class_id and class_id.startswith("eq."):
        c_id = class_id.replace("eq.", "")
        stmt = stmt.where(SinhVien.class_id == c_id)
    result = await db.execute(stmt)
    res = []
    for sv in result.scalars().all():
        d = model_to_dict(sv)
        d["ngaysinh"] = str(d["ngaysinh"]) if d.get("ngaysinh") else None
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        res.append(d)
    return res