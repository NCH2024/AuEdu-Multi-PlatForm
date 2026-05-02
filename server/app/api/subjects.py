from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import HocPhan
from pydantic import BaseModel
from typing import Optional

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
    result = await db.execute(select(HocPhan))
    return result.scalars().all()

@router.post("/")
async def create_subject(subj: SubjectCreate, db: AsyncSession = Depends(get_db)):
    db_subj = HocPhan(**subj.model_dump())
    db.add(db_subj)
    await db.commit()
    await db.refresh(db_subj)
    return db_subj

@router.put("/{id}")
async def update_subject(id: int, subj: SubjectUpdate, db: AsyncSession = Depends(get_db)):
    db_subj = await db.get(HocPhan, id)
    if not db_subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    for k, v in subj.model_dump(exclude_unset=True).items():
        setattr(db_subj, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_subject(id: int, db: AsyncSession = Depends(get_db)):
    db_subj = await db.get(HocPhan, id)
    if not db_subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    await db.delete(db_subj)
    await db.commit()
    return {"message": "Deleted successfully"}
