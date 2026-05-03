from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.db.session import get_db
from app.db.models import HocKy, TuanHoc

router = APIRouter()

class SemesterCreate(BaseModel):
    tenhocky: str
    namhoc: str
    so_tuan_hoc: int = 15
    loai_hocky: Optional[str] = "Chính"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class SemesterUpdate(BaseModel):
    tenhocky: Optional[str] = None
    namhoc: Optional[str] = None
    so_tuan_hoc: Optional[int] = None
    loai_hocky: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

@router.get("/")
async def get_semesters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HocKy).where(HocKy.deleted_at.is_(None)))
    return result.scalars().all()

@router.get("/{id}/weeks")
async def get_semester_weeks(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TuanHoc).where(TuanHoc.hocky_id == id).order_by(TuanHoc.ngay_bat_dau))
    return result.scalars().all()

@router.post("/")
async def create_semester(sem: SemesterCreate, db: AsyncSession = Depends(get_db)):
    """Tạo mới học kỳ."""
    try:
        db_sem = HocKy(**sem.model_dump())
        db.add(db_sem)
        await db.commit()
        await db.refresh(db_sem)
        return db_sem
    except Exception as e:
        await db.rollback()
        print(f"Error creating semester: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{id}")
async def update_semester(id: int, sem: SemesterUpdate, db: AsyncSession = Depends(get_db)):
    db_sem = await db.get(HocKy, id)
    if not db_sem:
        raise HTTPException(status_code=404, detail="Semester not found")
    for k, v in sem.model_dump(exclude_unset=True).items():
        setattr(db_sem, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_semester(id: int, db: AsyncSession = Depends(get_db)):
    db_sem = await db.get(HocKy, id)
    if not db_sem or db_sem.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    from datetime import datetime
    db_sem.deleted_at = datetime.now()
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}

@router.post("/{id}/generate_weeks")
async def generate_semester_weeks(id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Tạo hoặc cập nhật danh sách tuần học cho một học kỳ.
    Cơ chế: Tìm kiếm các tuần có sẵn trong CSDL theo ngày để reuse (link), 
    nếu không có thì mới tạo mới. Đảm bảo tính nhất quán dữ liệu.
    """
    # 1. Lấy thông tin học kỳ
    db_sem = await db.get(HocKy, id)
    if not db_sem:
        raise HTTPException(status_code=404, detail="Không tìm thấy học kỳ")
    
    start_date_str = payload.get("start_date")
    if not start_date_str:
        # Nếu không gửi start_date trong payload, dùng start_date của học kỳ
        if db_sem.start_date:
            start_date = db_sem.start_date
        else:
            raise HTTPException(status_code=400, detail="Ngày bắt đầu (start_date) là bắt buộc")
    else:
        import datetime
        try:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="Định dạng ngày bắt đầu không hợp lệ (YYYY-MM-DD)")

    so_tuan = db_sem.so_tuan_hoc or 15
    if so_tuan <= 0:
        raise HTTPException(status_code=400, detail="Số tuần học phải lớn hơn 0")
    
    # 2. Lấy danh sách tuần hiện có của học kỳ này
    result = await db.execute(select(TuanHoc).where(TuanHoc.hocky_id == id).order_by(TuanHoc.id))
    existing_weeks = result.scalars().all()
    
    # 3. Tính toán dữ liệu tuần mới dựa trên ngày bắt đầu
    import datetime
    new_weeks_data = []
    current_start = start_date
    start_idx = payload.get("start_week_index", 1)
    
    for i in range(so_tuan):
        current_end = current_start + datetime.timedelta(days=6)
        week_num = start_idx + i
        new_weeks_data.append({
            "ten_tuan": f"{week_num:02d}",
            "ngay_bat_dau": current_start,
            "ngay_ket_thuc": current_end
        })
        current_start = current_start + datetime.timedelta(days=7)
    
    # 4. Thực hiện Cập nhật / Thêm mới / Link
    for i in range(len(new_weeks_data)):
        w_data = new_weeks_data[i]
        
        # Tìm tuần khớp ngày trong toàn bộ hệ thống
        stmt_check = select(TuanHoc).where(
            TuanHoc.ngay_bat_dau == w_data["ngay_bat_dau"],
            TuanHoc.ngay_ket_thuc == w_data["ngay_ket_thuc"]
        )
        res_check = await db.execute(stmt_check)
        found_week = res_check.scalar_one_or_none()
        
        if found_week:
            # Reuse tuần cũ: cập nhật link tới học kỳ này
            found_week.hocky_id = id
            found_week.ten_tuan = w_data["ten_tuan"]
        elif i < len(existing_weeks):
            # Cập nhật tuần đang có của học kỳ này
            existing_weeks[i].ten_tuan = w_data["ten_tuan"]
            existing_weeks[i].ngay_bat_dau = w_data["ngay_bat_dau"]
            existing_weeks[i].ngay_ket_thuc = w_data["ngay_ket_thuc"]
        else:
            # Tạo mới hoàn toàn
            db.add(TuanHoc(
                hocky_id=id,
                ten_tuan=w_data["ten_tuan"],
                ngay_bat_dau=w_data["ngay_bat_dau"],
                ngay_ket_thuc=w_data["ngay_ket_thuc"]
            ))
            
    # Xóa các tuần dư thừa (nếu số tuần của học kỳ bị giảm đi)
    if len(existing_weeks) > len(new_weeks_data):
        for ew in existing_weeks[len(new_weeks_data):]:
            # Chỉ xóa nếu tuần này không trùng với bất kỳ ngày nào trong dải tuần mới
            # (Thực tế existing_weeks[len(new_weeks_data):] chắc chắn là dư thừa)
            await db.delete(ew)
    
    # 5. Đồng bộ lại ngày của học kỳ
    db_sem.start_date = start_date
    db_sem.end_date = new_weeks_data[-1]["ngay_ket_thuc"]
    
    await db.commit()
    return {
        "status": "success",
        "message": f"Đã đồng bộ {so_tuan} tuần học",
        "details": {
            "start_date": str(db_sem.start_date),
            "end_date": str(db_sem.end_date),
            "so_tuan": so_tuan
        }
    }
