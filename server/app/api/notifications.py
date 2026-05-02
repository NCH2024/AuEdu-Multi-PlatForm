from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import ThongBao
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class NotificationCreate(BaseModel):
    tieu_de: str
    noi_dung: str
    giangvien_id: Optional[int] = None
    hinh_anh: Optional[str] = None
    link_web: Optional[str] = None

class NotificationUpdate(BaseModel):
    tieu_de: Optional[str] = None
    noi_dung: Optional[str] = None
    giangvien_id: Optional[int] = None
    hinh_anh: Optional[str] = None
    link_web: Optional[str] = None

@router.get("/")
async def get_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ThongBao).where(ThongBao.deleted_at == None))
    return result.scalars().all()

@router.post("/")
async def create_notification(noti: NotificationCreate, db: AsyncSession = Depends(get_db)):
    db_noti = ThongBao(**noti.model_dump())
    db.add(db_noti)
    await db.commit()
    await db.refresh(db_noti)
    return db_noti

@router.put("/{id}")
async def update_notification(id: int, noti: NotificationUpdate, db: AsyncSession = Depends(get_db)):
    db_noti = await db.get(ThongBao, id)
    if not db_noti:
        raise HTTPException(status_code=404, detail="Notification not found")
    for k, v in noti.model_dump(exclude_unset=True).items():
        setattr(db_noti, k, v)
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_notification(id: int, db: AsyncSession = Depends(get_db)):
    db_noti = await db.get(ThongBao, id)
    if not db_noti:
        raise HTTPException(status_code=404, detail="Notification not found")
    # Soft delete
    from datetime import datetime
    db_noti.deleted_at = datetime.now()
    await db.commit()
    return {"message": "Deleted successfully"}
