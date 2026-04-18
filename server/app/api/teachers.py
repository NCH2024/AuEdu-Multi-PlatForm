# server/app/api/teachers.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import GiangVien, Khoa

router = APIRouter()


def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict (sử dụng trong mọi router)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/giangvien")
async def get_giangvien(
    id: Optional[str] = None,
    auth_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = (
        select(GiangVien, Khoa)
        .outerjoin(Khoa, GiangVien.khoa_id == Khoa.id)
    )

    # Lọc theo ID (eq.3)
    if id and id.startswith("eq."):
        gv_id = int(id.replace("eq.", ""))
        stmt = stmt.where(GiangVien.id == gv_id)

    # Lọc theo auth_id (eq.<uuid>)
    if auth_id and auth_id.startswith("eq."):
        a_id = auth_id.replace("eq.", "")
        stmt = stmt.where(GiangVien.auth_id == a_id)

    result = await db.execute(stmt)
    data = []
    for gv, khoa in result:
        d = model_to_dict(gv)
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        d["khoa"] = {"tenkhoa": khoa.tenkhoa} if khoa else None
        data.append(d)
    return data
