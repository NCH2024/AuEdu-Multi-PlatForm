from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Khoa
from app.core.security import get_current_user_id
from app.core.audit import log_audit

router = APIRouter()

class DepartmentCreate(BaseModel):
    id: str
    tenkhoa: str
    email: Optional[str] = None
    description: Optional[str] = None

class DepartmentUpdate(BaseModel):
    tenkhoa: Optional[str] = None
    email: Optional[str] = None
    description: Optional[str] = None

@router.get("/")
async def get_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Khoa).where(Khoa.deleted_at.is_(None)))
    return [{"id": d.id, "tenkhoa": d.tenkhoa, "email": d.email, "description": d.description} for d in result.scalars().all()]

@router.post("/")
async def create_department(
    dept: DepartmentCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_dept = Khoa(**dept.model_dump())
    db_dept.created_by = current_user_id
    db_dept.updated_by = current_user_id
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="Khoa",
        entity_id=db_dept.id,
        details=dept.model_dump(),
        request=request
    )
    await db.commit()

    return {"id": db_dept.id, "message": "Created successfully"}

@router.put("/{id}")
async def update_department(
    id: str, 
    dept: DepartmentUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_dept = await db.get(Khoa, id)
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in dept.model_dump(exclude_unset=True).items():
        setattr(db_dept, k, v)
    
    db_dept.updated_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="Khoa",
        entity_id=id,
        details=dept.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_department(
    id: str, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_dept = await db.get(Khoa, id)
    if not db_dept or db_dept.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Department not found")
    
    from datetime import datetime
    db_dept.deleted_at = datetime.now()
    db_dept.deleted_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="Khoa",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}
