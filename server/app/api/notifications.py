from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import ThongBao
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user_id
from app.core.audit import log_audit

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
async def create_notification(
    noti: NotificationCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_noti = ThongBao(**noti.model_dump())
    db.add(db_noti)
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="ThongBao",
        details=noti.model_dump(),
        request=request
    )
    
    await db.commit()
    await db.refresh(db_noti)
    return db_noti

@router.put("/{id}")
async def update_notification(
    id: int, 
    noti: NotificationUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_noti = await db.get(ThongBao, id)
    if not db_noti:
        raise HTTPException(status_code=404, detail="Notification not found")
    for k, v in noti.model_dump(exclude_unset=True).items():
        setattr(db_noti, k, v)
        
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="ThongBao",
        entity_id=id,
        details=noti.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/{id}")
async def delete_notification(
    id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_noti = await db.get(ThongBao, id)
    if not db_noti:
        raise HTTPException(status_code=404, detail="Notification not found")
    # Soft delete
    from datetime import datetime
    db_noti.deleted_at = datetime.now()
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="ThongBao",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully"}
