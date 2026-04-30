from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date, time
from app.db.session import get_db
from app.db.models import AttendanceSchedule

router = APIRouter()

class ScheduleCreate(BaseModel):
    title: str
    date: date
    start_time: time
    end_time: time
    class_ids: List[str]
    semester_id: int
    recurrence: Optional[str] = 'none'
    ai_threshold: Optional[float] = 0.6
    anti_spoofing: Optional[bool] = True
    fiqa_threshold: Optional[float] = 0.5

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    class_ids: Optional[List[str]] = None
    semester_id: Optional[int] = None
    recurrence: Optional[str] = None
    ai_threshold: Optional[float] = None
    anti_spoofing: Optional[bool] = None
    fiqa_threshold: Optional[float] = None

@router.get("/")
async def get_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AttendanceSchedule))
    return result.scalars().all()

@router.post("/")
async def create_schedule(sched: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    db_sched = AttendanceSchedule(**sched.model_dump())
    db.add(db_sched)
    await db.commit()
    await db.refresh(db_sched)
    return db_sched

@router.put("/{id}")
async def update_schedule(id: int, sched: ScheduleUpdate, db: AsyncSession = Depends(get_db)):
    db_sched = await db.get(AttendanceSchedule, id)
    if not db_sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for k, v in sched.model_dump(exclude_unset=True).items():
        setattr(db_sched, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_schedule(id: int, db: AsyncSession = Depends(get_db)):
    db_sched = await db.get(AttendanceSchedule, id)
    if not db_sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(db_sched)
    await db.commit()
    return {"message": "Deleted successfully"}
