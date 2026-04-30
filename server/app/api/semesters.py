from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.db.session import get_db
from app.db.models import HocKy

router = APIRouter()

class SemesterCreate(BaseModel):
    tenhocky: str
    namhoc: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class SemesterUpdate(BaseModel):
    tenhocky: Optional[str] = None
    namhoc: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

@router.get("/")
async def get_semesters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HocKy))
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
