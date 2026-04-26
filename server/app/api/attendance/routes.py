# server/app/api/attendance/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union
from app.db.session import get_db
from app.db.models import DiemDanh, TKBTiet, SinhVien, ThoiKhoaBieu
from datetime import datetime, date
from sqlalchemy import or_, cast, String, text, func, case, select, update
from pydantic import BaseModel
import traceback

router = APIRouter()

def model_to_dict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# --- KHUÔN MẪU DỮ LIỆU (PYDANTIC) ---
# Giúp FastAPI tự động hiểu và xác thực JSON gửi từ Flet
class UpdateManualReq(BaseModel):
    sv_id: Union[int, str] 
    tkb_tiet_id: int
    date: str # Nhận chuỗi thô từ Flet để tự xử lý an toàn
    new_status: str

@router.get("/diemdanh")
async def get_diemdanh(
    tkb_tiet_id: Optional[str] = None,
    ngay_diem_danh: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = select(DiemDanh)

    if tkb_tiet_id:
        if tkb_tiet_id.startswith("in."):
            ids = [int(i) for i in tkb_tiet_id.replace("in.", "").strip("()").split(",")]
            stmt = stmt.where(DiemDanh.tkb_tiet_id.in_(ids))
        elif tkb_tiet_id.startswith("eq."):
            stmt = stmt.where(DiemDanh.tkb_tiet_id == int(tkb_tiet_id.replace("eq.", "")))

    if ngay_diem_danh and ngay_diem_danh.startswith("eq."):
        date_str = ngay_diem_danh.replace("eq.", "")
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        stmt = stmt.where(DiemDanh.ngay_diem_danh == target)

    result = await db.execute(stmt)
    data = []
    for d in result.scalars().all():
        d_dict = model_to_dict(d)
        d_dict["ngay_diem_danh"] = str(d.ngay_diem_danh) if d.ngay_diem_danh else None
        d_dict["created_at"] = str(d.created_at) if d.created_at else None
        data.append(d_dict)
    return data

@router.get("/history/{tkb_id}")
async def get_attendance_history(tkb_id: int, db: AsyncSession = Depends(get_db)):
    tkb_stmt = select(ThoiKhoaBieu).where(ThoiKhoaBieu.id == tkb_id)
    tkb_res = await db.execute(tkb_stmt)
    tkb_obj = tkb_res.scalar()
    if not tkb_obj: return []

    sv_count_stmt = select(func.count(SinhVien.id)).where(SinhVien.class_id == tkb_obj.lop_id)
    sv_count_res = await db.execute(sv_count_stmt)
    total_class_students = sv_count_res.scalar() or 0

    stmt = (
        select(
            DiemDanh.ngay_diem_danh,
            DiemDanh.tkb_tiet_id,
            func.count(case((DiemDanh.trang_thai == 'Có mặt', 1))).label("present_count")
        )
        .join(TKBTiet, DiemDanh.tkb_tiet_id == TKBTiet.id)
        .where(TKBTiet.tkb_id == tkb_id)
        .group_by(DiemDanh.ngay_diem_danh, DiemDanh.tkb_tiet_id)
        .order_by(DiemDanh.ngay_diem_danh.desc())
    )
    
    result = await db.execute(stmt)
    history = []
    for row in result.all():
        history.append({
            "date": row.ngay_diem_danh.isoformat(),
            "tkb_tiet_id": row.tkb_tiet_id,
            "total": total_class_students,
            "present": row.present_count,
            "percent": int((row.present_count / total_class_students * 100)) if total_class_students > 0 else 0
        })
    return history

@router.get("/details/{tkb_tiet_id}/{date_str}")
async def get_attendance_detail(tkb_tiet_id: int, date_str: str, db: AsyncSession = Depends(get_db)):
    try:
        # Cập nhật logic ép kiểu ngày an toàn cho Python 3.10
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        print("Lỗi parse ngày:", e)
        return []

    tkb_stmt = select(ThoiKhoaBieu.lop_id).join(TKBTiet).where(TKBTiet.id == tkb_tiet_id)
    tkb_res = await db.execute(tkb_stmt)
    lop_id = tkb_res.scalar()

    stmt = (
        select(
            SinhVien.id, SinhVien.hodem, SinhVien.ten, SinhVien.gioitinh, SinhVien.ngaysinh,
            DiemDanh.trang_thai, DiemDanh.created_at, DiemDanh.vitri
        )
        .outerjoin(DiemDanh, (SinhVien.id == DiemDanh.sv_id) & 
                           (DiemDanh.tkb_tiet_id == tkb_tiet_id) & 
                           (DiemDanh.ngay_diem_danh == target_date))
        .where(SinhVien.class_id == lop_id)
        .order_by(SinhVien.ten.asc()) 
    )
    
    res = await db.execute(stmt)
    data = []
    for row in res.all():
        d = dict(row._mapping)
        d["time"] = d["created_at"].strftime("%H:%M:%S") if d["created_at"] else "--:--:--"
        d["trang_thai"] = d["trang_thai"] if d["trang_thai"] else "Vắng"
        d["ngaysinh"] = d["ngaysinh"].strftime("%d/%m/%Y") if d["ngaysinh"] else "N/A"
        d["vitri"] = d["vitri"] if d["vitri"] else "Không ghi nhận"
        data.append(d)
    return data

@router.patch("/update-manual")
async def update_attendance_manual(payload: UpdateManualReq, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    try:
        # 1. Tự ép kiểu ngày tháng cực kỳ an toàn
        target_date = datetime.strptime(payload.date, "%Y-%m-%d").date()
        sv_id_val = payload.sv_id

        # 2. Tìm bản ghi cũ
        stmt = select(DiemDanh).where(
            (DiemDanh.sv_id == sv_id_val) &
            (DiemDanh.tkb_tiet_id == payload.tkb_tiet_id) &
            (DiemDanh.ngay_diem_danh == target_date)
        )
        res = await db.execute(stmt)
        # Sử dụng scalars().first() thay vì scalar_first() để lấy đúng Object
        record = res.scalars().first() 

        if record:
            record.trang_thai = payload.new_status
        else:
            new_record = DiemDanh(
                sv_id=sv_id_val,
                tkb_tiet_id=payload.tkb_tiet_id,
                ngay_diem_danh=target_date,
                trang_thai=payload.new_status,
                vitri="Cập nhật thủ công bởi GV",           
            )
            db.add(new_record)

        await db.commit()
        return {"status": "success", "message": "Đã lưu trạng thái"}

    except Exception as e:
        error_str = traceback.format_exc()
        print(f"--- LỖI API UPDATE MANUAL ---\n{error_str}")
        # Bắt buộc trả dòng lỗi chi tiết về cho Client
        raise HTTPException(status_code=500, detail=str(e))