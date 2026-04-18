# server/app/api/schedule.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from sqlalchemy import or_, cast, String, text, func, case, select

from app.db.session import get_db
from app.db.models import (
    TuanHoc, SinhVien, ThongBao,
    ThoiKhoaBieu, Lop, HocPhan, HocKy,
    TKBTiet, Tiet, DiemDanh, DiemDanh, GiangVien,
)

router = APIRouter()


def model_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# --------- Tuần học ----------
@router.get("/tuan_hoc")
async def get_tuan_hoc(db: AsyncSession = Depends(get_db)) -> List[dict]:
    stmt = select(TuanHoc).order_by(TuanHoc.id.asc())
    result = await db.execute(stmt)
    data = []
    for t in result.scalars().all():
        d = model_to_dict(t)
        d["ngay_bat_dau"] = str(d["ngay_bat_dau"]) if d.get("ngay_bat_dau") else None
        d["ngay_ket_thuc"] = str(d["ngay_ket_thuc"]) if d.get("ngay_ket_thuc") else None
        data.append(d)
    return data


# --------- Thời khoá biểu ----------
@router.get("/thoikhoabieu")
async def get_thoi_khoa_bieu(
    giangvien_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = (
        select(ThoiKhoaBieu, Lop, HocPhan, HocKy)
        .outerjoin(Lop, ThoiKhoaBieu.lop_id == Lop.id)
        .outerjoin(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)
        .outerjoin(HocKy, ThoiKhoaBieu.hocky_id == HocKy.id)
    )
    if giangvien_id and giangvien_id.startswith("eq."):
        gv_id = int(giangvien_id.replace("eq.", ""))
        stmt = stmt.where(ThoiKhoaBieu.giangvien_id == gv_id)

    result = await db.execute(stmt)
    data = []
    for tkb, lop, hp, hk in result:
        d = model_to_dict(tkb)
        d["lop"] = {"tenlop": lop.tenlop} if lop else None
        d["hocphan"] = (
            {"tenhocphan": hp.tenhocphan, "sobuoi": hp.sobuoi} if hp else None
        )
        d["hocky"] = (
            {"namhoc": hk.namhoc, "tenhocky": hk.tenhocky} if hk else None
        )
        data.append(d)
    return data


# --------- Tiết ----------
@router.get("/tkb_tiet")
async def get_tkb_tiet(
    tkb_id: Optional[str] = None,
    thu: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = (
        select(TKBTiet, Tiet)
        .outerjoin(Tiet, TKBTiet.tiet_id == Tiet.id)
    )
    if tkb_id:
        if tkb_id.startswith("in."):
            ids = [int(i) for i in tkb_id.replace("in.", "").strip("()").split(",")]
            stmt = stmt.where(TKBTiet.tkb_id.in_(ids))
        elif tkb_id.startswith("eq."):
            stmt = stmt.where(TKBTiet.tkb_id == int(tkb_id.replace("eq.", "")))
    if thu and thu.startswith("eq."):
        stmt = stmt.where(TKBTiet.thu == int(thu.replace("eq.", "")))

    stmt = stmt.order_by(Tiet.thoigianbd.asc())
    result = await db.execute(stmt)
    data = []
    for tkbt, tiet in result:
        d = model_to_dict(tkbt)
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        d["tiet"] = (
            {
                "thoigianbd": str(tiet.thoigianbd) if tiet.thoigianbd else None,
                "thoigiankt": str(tiet.thoigiankt) if tiet.thoigiankt else None,
            }
            if tiet
            else None
        )
        data.append(d)
    return data


# --------- Điểm danh (REST) ----------
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
