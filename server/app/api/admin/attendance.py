from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.db.models import DiemDanh, SinhVien, Lop, ThoiKhoaBieu, HocPhan, TKBTiet

router = APIRouter()

@router.get("/report")
async def get_attendance_report(
    class_id: Optional[str] = None,
    subject_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Báo cáo điểm danh chi tiết cho Admin."""
    query = select(
        DiemDanh.id,
        DiemDanh.ngay_diem_danh,
        DiemDanh.trang_thai,
        DiemDanh.confidence_score,
        DiemDanh.note,
        SinhVien.id.label("sv_id"),
        SinhVien.hodem,
        SinhVien.ten,
        Lop.tenlop,
        HocPhan.tenhocphan
    ).join(SinhVien, DiemDanh.sv_id == SinhVien.id)\
     .join(TKBTiet, DiemDanh.tkb_tiet_id == TKBTiet.id)\
     .join(ThoiKhoaBieu, TKBTiet.tkb_id == ThoiKhoaBieu.id)\
     .join(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)\
     .join(Lop, SinhVien.class_id == Lop.id)

    filters = []
    if class_id and class_id != "all":
        filters.append(SinhVien.class_id == class_id)
    if subject_id:
        filters.append(ThoiKhoaBieu.hocphan_id == subject_id)
    if start_date:
        filters.append(DiemDanh.ngay_diem_danh >= start_date)
    if end_date:
        filters.append(DiemDanh.ngay_diem_danh <= end_date)
    if status:
        filters.append(DiemDanh.trang_thai == status)
    if search:
        filters.append(and_(
            (SinhVien.ten.ilike(f"%{search}%")) | (func.cast(SinhVien.id, str).ilike(f"%{search}%"))
        ))

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(desc(DiemDanh.ngay_diem_danh), Lop.tenlop, SinhVien.ten)
    result = await db.execute(query)
    
    data = []
    for r in result.all():
        data.append({
            "id": r.id,
            "ngay": r.ngay_diem_danh.strftime("%d/%m/%Y"),
            "trang_thai": r.trang_thai,
            "confidence": f"{r.confidence_score*100:.1f}%" if r.confidence_score else "N/A",
            "mssv": r.sv_id,
            "full_name": f"{r.hodem} {r.ten}",
            "tenlop": r.tenlop,
            "mon_hoc": r.tenhocphan,
            "note": r.note
        })
    
    return data

@router.get("/summary")
async def get_attendance_summary(db: AsyncSession = Depends(get_db)):
    """Thống kê tổng quan tỷ lệ điểm danh."""
    # Thống kê số lượng theo trạng thái
    stats = await db.execute(
        select(DiemDanh.trang_thai, func.count(DiemDanh.id))
        .group_by(DiemDanh.trang_thai)
    )
    
    summary = {r[0]: r[1] for r in stats.all()}
    return {
        "present": summary.get("Có mặt", 0),
        "absent": summary.get("Vắng", 0),
        "late": summary.get("Đi trễ", 0),
        "total": sum(summary.values())
    }

@router.get("/logs")
async def get_attendance_logs(limit: int = 30, db: AsyncSession = Depends(get_db)):
    """Lấy N bản ghi điểm danh mới nhất để hiển thị card giám sát."""
    query = select(
        DiemDanh.id,
        DiemDanh.ngay_diem_danh,
        DiemDanh.trang_thai,
        DiemDanh.confidence_score,
        DiemDanh.note,
        DiemDanh.created_at,
        SinhVien.id.label("sv_id"),
        SinhVien.hodem,
        SinhVien.ten,
        Lop.tenlop,
        HocPhan.tenhocphan
    ).join(SinhVien, DiemDanh.sv_id == SinhVien.id)\
     .join(TKBTiet, DiemDanh.tkb_tiet_id == TKBTiet.id)\
     .join(ThoiKhoaBieu, TKBTiet.tkb_id == ThoiKhoaBieu.id)\
     .join(HocPhan, ThoiKhoaBieu.hocphan_id == HocPhan.id)\
     .join(Lop, SinhVien.class_id == Lop.id)\
     .order_by(desc(DiemDanh.created_at))\
     .limit(limit)

    result = await db.execute(query)
    
    data = []
    for r in result.all():
        data.append({
            "id": r.id,
            "mssv": r.sv_id,
            "name": f"{r.hodem} {r.ten}".strip(),
            "tenlop": r.tenlop,
            "mon_hoc": r.tenhocphan,
            "trang_thai": r.trang_thai,
            "time": r.created_at.strftime("%H:%M:%S"),
            "ngay": r.ngay_diem_danh.strftime("%d/%m/%Y"),
            "score": round(float(r.confidence_score), 4) if r.confidence_score else 0,
            "note": r.note
        })
    return data

@router.post("/manual")
async def create_manual_attendance(payload: dict, db: AsyncSession = Depends(get_db)):
    """Admin điểm danh thủ công cho sinh viên."""
    sv_id = payload.get("sv_id")
    tkb_tiet_id = payload.get("tkb_tiet_id")
    ngay = payload.get("ngay") # ISO format
    trang_thai = payload.get("trang_thai", "Có mặt")
    note = payload.get("note", "Admin điểm danh thủ công")

    if not sv_id or not tkb_tiet_id:
        raise HTTPException(status_code=400, detail="Thiếu MSSV hoặc ID Tiết học")

    try:
        # Kiểm tra xem đã có bản ghi chưa
        stmt = select(DiemDanh).where(
            DiemDanh.sv_id == sv_id,
            DiemDanh.tkb_tiet_id == tkb_tiet_id,
            DiemDanh.ngay_diem_danh == (date.fromisoformat(ngay) if ngay else date.today())
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            record.trang_thai = trang_thai
            record.note = note
            record.updated_at = func.now()
        else:
            record = DiemDanh(
                sv_id=sv_id,
                tkb_tiet_id=tkb_tiet_id,
                ngay_diem_danh=(date.fromisoformat(ngay) if ngay else date.today()),
                trang_thai=trang_thai,
                note=note,
                confidence_score=1.0 # Thủ công thì độ tin cậy là 100%
            )
            db.add(record)
        
        await db.commit()
        return {"status": "success", "id": record.id}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_attendance(id: int, db: AsyncSession = Depends(get_db)):
    """Admin xóa bản ghi điểm danh."""
    stmt = select(DiemDanh).where(DiemDanh.id == id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")

    try:
        await db.delete(record)
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
