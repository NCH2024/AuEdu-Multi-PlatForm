from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import HocPhan
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class SubjectCreate(BaseModel):
    tenhocphan: str
    sotinchi: int
    loaihp_id: Optional[int] = None
    sobuoi: int

class SubjectUpdate(BaseModel):
    tenhocphan: Optional[str] = None
    sotinchi: Optional[int] = None
    loaihp_id: Optional[int] = None
    sobuoi: Optional[int] = None

@router.get("/")
async def get_subjects(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách học phần — chỉ những bản ghi chưa bị xóa mềm."""
    stmt = select(HocPhan).where(HocPhan.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/")
async def create_subject(subj: SubjectCreate, db: AsyncSession = Depends(get_db)):
    """Tạo mới học phần."""
    db_subj = HocPhan(**subj.model_dump())
    db.add(db_subj)
    await db.commit()
    await db.refresh(db_subj)
    return db_subj

@router.put("/{id}")
async def update_subject(id: int, subj: SubjectUpdate, db: AsyncSession = Depends(get_db)):
    """Cập nhật thông tin học phần theo ID."""
    db_subj = await db.get(HocPhan, id)
    if not db_subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for k, v in subj.model_dump(exclude_unset=True).items():
        setattr(db_subj, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_subject(id: int, db: AsyncSession = Depends(get_db)):
    """Xóa mềm học phần theo ID."""
    db_subj = await db.get(HocPhan, id)
    if not db_subj or db_subj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Subject not found")

    db_subj.deleted_at = datetime.now()
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}

