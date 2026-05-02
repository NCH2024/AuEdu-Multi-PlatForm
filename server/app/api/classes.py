from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from app.db.session import get_db
from app.db.models import Lop

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
    result = await db.execute(select(Lop))
    return result.scalars().all()

@router.post("/")
async def create_class(cls: ClassCreate, db: AsyncSession = Depends(get_db)):
    db_cls = Lop(**cls.model_dump())
    db.add(db_cls)
    await db.commit()
    await db.refresh(db_cls)
    return {"id": db_cls.id, "message": "Created successfully"}

@router.put("/{id}")
async def update_class(id: str, cls: ClassUpdate, db: AsyncSession = Depends(get_db)):
    db_cls = await db.get(Lop, id)
    if not db_cls:
        raise HTTPException(status_code=404, detail="Class not found")
    for k, v in cls.model_dump(exclude_unset=True).items():
        setattr(db_cls, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_class(id: str, db: AsyncSession = Depends(get_db)):
    db_cls = await db.get(Lop, id)
    if not db_cls:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.delete(db_cls)
    await db.commit()
    return {"message": "Deleted successfully"}
