from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Khoa

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
    result = await db.execute(select(Khoa))
    return [{"id": d.id, "tenkhoa": d.tenkhoa, "email": d.email, "description": d.description} for d in result.scalars().all()]

@router.post("/")
async def create_department(dept: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    db_dept = Khoa(**dept.model_dump())
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return {"id": db_dept.id, "message": "Created successfully"}

@router.put("/{id}")
async def update_department(id: str, dept: DepartmentUpdate, db: AsyncSession = Depends(get_db)):
    db_dept = await db.get(Khoa, id)
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in dept.model_dump(exclude_unset=True).items():
        setattr(db_dept, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_department(id: str, db: AsyncSession = Depends(get_db)):
    db_dept = await db.get(Khoa, id)
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(db_dept)
    await db.commit()
    return {"message": "Deleted successfully"}
