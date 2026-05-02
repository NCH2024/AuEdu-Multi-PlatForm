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
    so_tuan_hoc: Optional[int] = 15
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class SemesterUpdate(BaseModel):
    tenhocky: Optional[str] = None
    namhoc: Optional[str] = None
    so_tuan_hoc: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

@router.get("/")
async def get_semesters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HocKy))
    return result.scalars().all()

@router.get("/{id}/weeks")
async def get_semester_weeks(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TuanHoc).where(TuanHoc.hocky_id == id).order_by(TuanHoc.ngay_bat_dau))
    return result.scalars().all()

@router.post("/")
async def create_semester(sem: SemesterCreate, db: AsyncSession = Depends(get_db)):
    db_sem = HocKy(**sem.model_dump())
    db.add(db_sem)
    await db.commit()
    await db.refresh(db_sem)
    return db_sem

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
    if not db_sem:
        raise HTTPException(status_code=404, detail="Semester not found")
    await db.delete(db_sem)
    await db.commit()
    return {"message": "Deleted successfully"}

@router.post("/{id}/generate_weeks")
async def generate_semester_weeks(id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    # 1. Lấy thông tin học kỳ
    db_sem = await db.get(HocKy, id)
    if not db_sem:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    start_date_str = payload.get("start_date")
    if not start_date_str:
        raise HTTPException(status_code=400, detail="start_date is required")
        
    import datetime
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    so_tuan = db_sem.so_tuan_hoc or 15
    
    # 2. Xóa các tuần cũ (nếu có)
    from sqlalchemy import text
    delete_stmt = text("DELETE FROM tuan_hoc WHERE hocky_id = :hk_id")
    await db.execute(delete_stmt, {"hk_id": id})
    
    # 3. Tạo tuần mới
    new_weeks = []
    current_start = start_date
    for i in range(1, so_tuan + 1):
        current_end = current_start + datetime.timedelta(days=6)
        new_weeks.append(TuanHoc(
            hocky_id=id,
            ten_tuan=f"Tuần {i:02d}",
            ngay_bat_dau=current_start,
            ngay_ket_thuc=current_end
        ))
        current_start = current_start + datetime.timedelta(days=7)
    
    db.add_all(new_weeks)
    
    # 4. Cập nhật ngày bắt đầu/kết thúc của học kỳ dựa trên tuần
    db_sem.start_date = start_date
    db_sem.end_date = new_weeks[-1].ngay_ket_thuc
    
    await db.commit()
    return {"message": f"Đã tạo thành công {so_tuan} tuần học", "start_date": str(db_sem.start_date), "end_date": str(db_sem.end_date)}
