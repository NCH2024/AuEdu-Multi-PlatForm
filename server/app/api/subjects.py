from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.session import get_db
from app.db.models import HocPhan
from app.core.security import get_current_user_id
from app.core.audit import log_audit
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
async def create_subject(
    subj: SubjectCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Tạo mới học phần."""
    db_subj = HocPhan(**subj.model_dump())
    db_subj.created_by = current_user_id
    db_subj.updated_by = current_user_id
    db.add(db_subj)
    await db.commit()
    await db.refresh(db_subj)

    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="HocPhan",
        entity_id=db_subj.id,
        details=subj.model_dump(),
        request=request
    )
    await db.commit()

    return db_subj

@router.put("/{id}")
async def update_subject(
    id: int, 
    subj: SubjectUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Cập nhật thông tin học phần theo ID."""
    db_subj = await db.get(HocPhan, id)
    if not db_subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for k, v in subj.model_dump(exclude_unset=True).items():
        setattr(db_subj, k, v)
    
    db_subj.updated_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="HocPhan",
        entity_id=id,
        details=subj.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_subject(
    id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Xóa mềm học phần theo ID."""
    db_subj = await db.get(HocPhan, id)
    if not db_subj or db_subj.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Subject not found")

    db_subj.deleted_at = datetime.now()
    db_subj.deleted_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="HocPhan",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}

