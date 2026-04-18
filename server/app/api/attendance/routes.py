# server/app/api/attendance/routes.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db
from app.db.models import DiemDanh, TKBTiet, SinhVien
from datetime import datetime
from sqlalchemy import select

router = APIRouter()


def model_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("/diemdanh")
async def get_diemdanh(
    tkb_tiet_id: Optional[str] = None,
    ngay_diem_danh: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = select(DiemDanh)

    if tkb_tiet_id:
        if tkb_tiet_id.startswith("in."):
            ids = [
                int(i) for i in tkb_tiet_id.replace("in.", "").strip("()").split(",")
            ]
            stmt = stmt.where(DiemDanh.tkb_tiet_id.in_(ids))
        elif tkb_tiet_id.startswith("eq."):
            stmt = stmt.where(DiemDanh.tkb_tiet_id == int(tkb_tiet_id.replace("eq.", "")))

    if ngay_diem_danh and ngay_diem_danh.startswith("eq."):
        date_str = ngay_diem_danh.replace("eq.", "")
        target = datetime.fromisoformat(date_str).date()
        stmt = stmt.where(DiemDanh.ngay_diem_danh == target)

    result = await db.execute(stmt)
    data = []
    for d in result.scalars().all():
        d_dict = model_to_dict(d)
        d_dict["ngay_diem_danh"] = str(d.ngay_diem_danh) if d.ngay_diem_danh else None
        d_dict["created_at"] = str(d.created_at) if d.created_at else None
        data.append(d_dict)
    return data