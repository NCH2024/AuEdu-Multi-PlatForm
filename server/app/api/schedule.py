from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, cast, String, text, func, case, select
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

from app.db.session import get_db
from app.db.models import (
    TuanHoc, SinhVien, ThongBao,
    ThoiKhoaBieu, Lop, HocPhan, HocKy,
    TKBTiet, Tiet, DiemDanh, GiangVien,
)

router = APIRouter()

# --------- Tuần học (Compatibility) ----------
@router.get("/tuan_hoc")
async def get_tuan_hoc(hocky_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(TuanHoc)
    if hocky_id:
        if hocky_id.startswith("eq."):
            stmt = stmt.where(TuanHoc.hocky_id == int(hocky_id.replace("eq.", "")))
        elif hocky_id.isdigit():
            stmt = stmt.where(TuanHoc.hocky_id == int(hocky_id))
    
    result = await db.execute(stmt.order_by(TuanHoc.ngay_bat_dau))
    return result.scalars().all()

class TKBSlot(BaseModel):
    thu: int # 2=Mon, ... 8=CN (theo chuẩn Flet/Backend hiện tại)
    tiet_id: int
    phong_hoc: Optional[str] = None

class TKBItem(BaseModel):
    hocphan_id: int
    lop_id: str
    phong_hoc: str
    tuan_hoc_id: Optional[int] = None # Mới: hỗ trợ sắp theo tuần lẻ
    slots: List[TKBSlot] # List of TKBSlot objects (thu, tiet_id, etc.)

class TKBBatchSetup(BaseModel):
    hocky_id: int
    giangvien_id: int
    ai_threshold: float = 0.6
    anti_spoofing: bool = True
    fiqa_threshold: float = 0.5
    items: List[TKBItem]


def model_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# --------- Tiết học (Cấu hình hệ thống) ----------
@router.get("/tiet")
async def get_all_periods(db: AsyncSession = Depends(get_db)) -> List[dict]:
    result = await db.execute(select(Tiet).order_by(Tiet.id.asc()))
    data = []
    for t in result.scalars().all():
        d = model_to_dict(t)
        d["thoigianbd"] = str(d["thoigianbd"])
        d["thoigiankt"] = str(d["thoigiankt"])
        data.append(d)
    return data


# --------- Busy Slots (Dành cho Grid UI) ----------
@router.get("/busy_slots")
async def get_busy_slots(
    hocky_id: int,
    giangvien_id: Optional[int] = None,
    lop_id: Optional[str] = None,
    phong_hoc: Optional[str] = None,
    week_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """Lấy danh sách các tiết đã bận để hiển thị lên lưới sắp lịch."""
    stmt = (
        select(TKBTiet, ThoiKhoaBieu, HocPhan, Lop)
        .join(ThoiKhoaBieu, TKBTiet.tkb_id == ThoiKhoaBieu.id)
        .join(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)
        .join(Lop, ThoiKhoaBieu.lop_id == Lop.id)
        .where(ThoiKhoaBieu.hocky_id == hocky_id)
        .where(ThoiKhoaBieu.deleted_at.is_(None))
    )
    
    if week_id:
        # Lấy những cái áp dụng cho mọi tuần (None) HOẶC đúng tuần này
        stmt = stmt.where(or_(
            ThoiKhoaBieu.tuan_hoc_id.is_(None),
            ThoiKhoaBieu.tuan_hoc_id == week_id
        ))
    
    # Lọc theo giảng viên hoặc lớp hoặc phòng
    filters = []
    if giangvien_id: filters.append(ThoiKhoaBieu.giangvien_id == giangvien_id)
    if lop_id: filters.append(ThoiKhoaBieu.lop_id == lop_id)
    if phong_hoc: filters.append(TKBTiet.phong_hoc == phong_hoc)
    
    if filters:
        stmt = stmt.where(or_(*filters))
        
    result = await db.execute(stmt)
    data = []
    for tkbt, tkb, hp, lop in result:
        data.append({
            "id": tkbt.id,
            "tkb_id": tkb.id,
            "thu": tkbt.thu,
            "tiet_id": tkbt.tiet_id,
            "phong_hoc": tkbt.phong_hoc,
            "hocphan": hp.tenhocphan,
            "lop": lop.tenlop,
            "giangvien_id": tkb.giangvien_id
        })
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
        .where(ThoiKhoaBieu.deleted_at.is_(None))
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
    stmt = select(DiemDanh).where(DiemDanh.deleted_at.is_(None))

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


# --------- Sinh viên (dành cho Giảng viên xem danh sách lớp) ----------
@router.get("/sinhvien")
async def get_sinhvien(
    class_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Lấy danh sách sinh viên theo lớp. 
    Dùng cho Giảng viên khi vào trang Điểm danh.
    """
    stmt = select(SinhVien).where(SinhVien.deleted_at.is_(None))
    if class_id:
        if class_id.startswith("eq."):
            c_id = class_id.replace("eq.", "")
            stmt = stmt.where(SinhVien.class_id == c_id)
        else:
            stmt = stmt.where(SinhVien.class_id == class_id)
            
    stmt = stmt.order_by(SinhVien.ten.asc())
    result = await db.execute(stmt)
    
    data = []
    for sv in result.scalars().all():
        d = model_to_dict(sv)
        # Format date/datetime for JSON
        if d.get("ngaysinh"): d["ngaysinh"] = str(d["ngaysinh"])
        if d.get("created_at"): d["created_at"] = str(d["created_at"])
        data.append(d)
    return data


# --------- Thiết lập TKB hàng loạt (Grid-based) ----------
@router.post("/thoikhoabieu/setup_batch")
async def setup_batch_schedule(payload: TKBBatchSetup, db: AsyncSession = Depends(get_db)):
    """
    Thiết lập thời khóa biểu hàng loạt hỗ trợ kiểm tra xung đột.
    """
    from fastapi import HTTPException
    
    # Helper kiểm tra xung đột
    async def check_conflict(thu, tiet_id, giangvien_id, lop_id, phong_hoc, target_week_id=None):
        stmt = (
            select(TKBTiet, ThoiKhoaBieu, HocPhan, Lop, GiangVien)
            .join(ThoiKhoaBieu, TKBTiet.tkb_id == ThoiKhoaBieu.id)
            .join(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)
            .join(Lop, ThoiKhoaBieu.lop_id == Lop.id)
            .join(GiangVien, ThoiKhoaBieu.giangvien_id == GiangVien.id)
            .where(ThoiKhoaBieu.hocky_id == payload.hocky_id)
            .where(TKBTiet.thu == thu)
            .where(TKBTiet.tiet_id == tiet_id)
            .where(ThoiKhoaBieu.deleted_at.is_(None))
        )
        
        # Nếu đang sắp cho tuần lẻ, chỉ kiểm tra xung đột với tuần đó và các lịch cố định (None)
        if target_week_id:
            stmt = stmt.where(or_(
                ThoiKhoaBieu.tuan_hoc_id.is_(None),
                ThoiKhoaBieu.tuan_hoc_id == target_week_id
            ))
        
        # Kiểm tra 3 điều kiện: Trùng GV, Trùng Lớp, Trùng Phòng
        stmt = stmt.where(or_(
            ThoiKhoaBieu.giangvien_id == giangvien_id,
            ThoiKhoaBieu.lop_id == lop_id,
            TKBTiet.phong_hoc == phong_hoc
        ))
        
        res = await db.execute(stmt)
        return res.first()

    created_tkb_ids = []
    try:
        for item in payload.items:
            # 1. Kiểm tra xung đột cho từng slot trong item
            for slot in item.slots:
                conflict = await check_conflict(
                    slot.thu, slot.tiet_id, 
                    payload.giangvien_id, item.lop_id, item.phong_hoc,
                    target_week_id=item.tuan_hoc_id
                )
                if conflict:
                    # conflict là tuple (TKBTiet, ThoiKhoaBieu, HocPhan, Lop, GiangVien)
                    _, _, hp, lop, gv = conflict
                    day_names = {2: "Thứ 2", 3: "Thứ 3", 4: "Thứ 4", 5: "Thứ 5", 6: "Thứ 6", 7: "Thứ 7", 8: "Chủ Nhật"}
                    day_name = day_names.get(slot.thu, f"Thứ {slot.thu}")
                    raise Exception(
                        f"XUNG ĐỘT: {day_name}, Tiết {slot.tiet_id} đã có lịch: "
                        f"{hp.tenhocphan} - {lop.tenlop} (GV: {gv.ten}, Phòng: {item.phong_hoc})"
                    )

            # 2. Tạo ThoiKhoaBieu chính cho Item này
            new_tkb = ThoiKhoaBieu(
                hocphan_id=item.hocphan_id,
                hocky_id=payload.hocky_id,
                lop_id=item.lop_id,
                giangvien_id=payload.giangvien_id,
                tuan_hoc_id=item.tuan_hoc_id, # Lưu tuần cụ thể nếu có
                ai_threshold=payload.ai_threshold,
                anti_spoofing=payload.anti_spoofing,
                fiqa_threshold=payload.fiqa_threshold,
            )
            db.add(new_tkb)
            await db.flush()
            created_tkb_ids.append(new_tkb.id)

            # 3. Tạo các TKBTiet cho Item này
            for slot in item.slots:
                new_tkbt = TKBTiet(
                    tkb_id=new_tkb.id,
                    thu=slot.thu,
                    tiet_id=slot.tiet_id,
                    phong_hoc=item.phong_hoc
                )
                db.add(new_tkbt)
            
        await db.commit()
        return {"message": "Thành công", "ids": created_tkb_ids, "total": len(created_tkb_ids)}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/thoikhoabieu/{id}")
async def delete_schedule(id: int, db: AsyncSession = Depends(get_db)):
    """Xóa thời khóa biểu có kiểm tra dữ liệu điểm danh."""
    from fastapi import HTTPException
    
    tkb = await db.get(ThoiKhoaBieu, id)
    if not tkb:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch học")
    
    # Kiểm tra điểm danh
    # Lấy tất cả tkb_tiet_id thuộc tkb này
    res_tiet = await db.execute(select(TKBTiet.id).where(TKBTiet.tkb_id == id))
    tiet_ids = [r for r in res_tiet.scalars().all()]
    
    if tiet_ids:
        res_dd = await db.execute(select(func.count(DiemDanh.id)).where(DiemDanh.tkb_tiet_id.in_(tiet_ids)))
        count = res_dd.scalar()
        if count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Không thể xóa: Đã có {count} dữ liệu điểm danh liên quan đến lịch học này!"
            )
            
    tkb.deleted_at = datetime.now()
    await db.commit()
    return {"message": "Đã xóa lịch học thành công"}
