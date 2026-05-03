from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Lop
from app.core.security import get_current_user_id
from app.core.audit import log_audit

router = APIRouter()

class ClassCreate(BaseModel):
    id: str
    tenlop: str
    khoa_id: Optional[str] = None
    semester_id: Optional[int] = None
    nambd: Optional[int] = None
    namkt: Optional[int] = None
    khoahoc: Optional[int] = None

class ClassUpdate(BaseModel):
    tenlop: Optional[str] = None
    khoa_id: Optional[str] = None
    semester_id: Optional[int] = None
    nambd: Optional[int] = None
    namkt: Optional[int] = None
    khoahoc: Optional[int] = None

@router.get("/")
async def get_classes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lop).where(Lop.deleted_at.is_(None)))
    return result.scalars().all()

@router.post("/")
async def create_class(
    cls: ClassCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_cls = Lop(**cls.model_dump())
    db_cls.created_by = current_user_id
    db_cls.updated_by = current_user_id
    db.add(db_cls)
    await db.commit()
    await db.refresh(db_cls)

    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="Lop",
        entity_id=db_cls.id,
        details=cls.model_dump(),
        request=request
    )
    await db.commit()

    return {"id": db_cls.id, "message": "Created successfully"}

@router.put("/{id}")
async def update_class(
    id: str, 
    cls: ClassUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_cls = await db.get(Lop, id)
    if not db_cls:
        raise HTTPException(status_code=404, detail="Class not found")
    for k, v in cls.model_dump(exclude_unset=True).items():
        setattr(db_cls, k, v)
    
    db_cls.updated_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="Lop",
        entity_id=id,
        details=cls.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_class(
    id: str, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_cls = await db.get(Lop, id)
    if not db_cls or db_cls.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Class not found")
    
    from datetime import datetime
    db_cls.deleted_at = datetime.now()
    db_cls.deleted_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="Lop",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}
