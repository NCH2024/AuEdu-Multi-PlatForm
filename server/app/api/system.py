from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import ThongBao

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