# server/app/api/teachers.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select, update
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import GiangVien, Khoa
from app.core.security import get_current_user_id
from app.core.audit import log_audit
import os
import httpx

router = APIRouter()

from app.core.config import SUPABASE_URL, SUPABASE_KEY

class TeacherCreate(BaseModel):
    hodem: str
    ten: str
    gioitinh: str
    diachi: Optional[str] = None
    sodienthoai: Optional[str] = None
    khoa_id: str
    vai_tro: str = "giangvien"

class TeacherUpdate(BaseModel):
    hodem: Optional[str] = None
    ten: Optional[str] = None
    gioitinh: Optional[str] = None
    diachi: Optional[str] = None
    sodienthoai: Optional[str] = None
    khoa_id: Optional[str] = None
    vai_tro: Optional[str] = None

def model_to_dict(obj):
    """Chuyển SQLAlchemy model → dict."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

@router.get("/giangvien")
async def get_giangvien(
    id: Optional[str] = None,
    auth_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    stmt = (
        select(GiangVien, Khoa)
        .outerjoin(Khoa, GiangVien.khoa_id == Khoa.id)
        .where(GiangVien.deleted_at.is_(None))
    )

    if id and id.startswith("eq."):
        gv_id = int(id.replace("eq.", ""))
        stmt = stmt.where(GiangVien.id == gv_id)

    if auth_id and auth_id.startswith("eq."):
        a_id = auth_id.replace("eq.", "")
        stmt = stmt.where(GiangVien.auth_id == a_id)

    result = await db.execute(stmt)
    data = []
    for gv, khoa in result:
        d = model_to_dict(gv)
        d["created_at"] = str(d["created_at"]) if d.get("created_at") else None
        d["khoa"] = {"tenkhoa": khoa.tenkhoa} if khoa else None
        data.append(d)
    return data

@router.post("/giangvien")
async def create_teacher(
    gv: TeacherCreate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_gv = GiangVien(**gv.model_dump())
    db_gv.created_by = current_user_id
    db_gv.updated_by = current_user_id
    db.add(db_gv)
    await db.commit()
    await db.refresh(db_gv)

    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="CREATE",
        entity="GiangVien",
        entity_id=db_gv.id,
        details=gv.model_dump(),
        request=request
    )
    await db.commit()

    return {"id": db_gv.id, "message": "Giảng viên created successfully"}

@router.put("/giangvien/{id}")
async def update_teacher(
    id: int, 
    gv: TeacherUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_gv = await db.get(GiangVien, id)
    if not db_gv:
        raise HTTPException(status_code=404, detail="Giảng viên not found")
    for k, v in gv.model_dump(exclude_unset=True).items():
        setattr(db_gv, k, v)
    
    db_gv.updated_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="GiangVien",
        entity_id=id,
        details=gv.model_dump(exclude_unset=True),
        request=request
    )
    
    await db.commit()
    return {"message": "Updated successfully"}

@router.delete("/giangvien/{id}")
async def delete_teacher(
    id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_gv = await db.get(GiangVien, id)
    if not db_gv or db_gv.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Giảng viên not found")
    
    from datetime import datetime
    db_gv.deleted_at = datetime.now()
    db_gv.deleted_by = current_user_id
    
    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="DELETE",
        entity="GiangVien",
        entity_id=id,
        request=request
    )
    
    await db.commit()
    return {"message": "Deleted successfully (Soft Delete)"}

@router.post("/giangvien/{id}/create-auth")
async def create_supabase_auth(id: int, payload: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Tạo tài khoản Auth trên Supabase và gán auth_id cho Giảng viên.
    Payload: { "email": "...", "password": "..." }
    """
    db_gv = await db.get(GiangVien, id)
    if not db_gv:
        raise HTTPException(status_code=404, detail="Giảng viên not found")
    
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    async with httpx.AsyncClient() as client:
        # Sử dụng Admin API của GoTrue (Supabase Auth)
        # Cần SUPABASE_SERVICE_ROLE_KEY để thực hiện việc này mà không cần confirm email
        # Ở đây ta tạm dùng SUPABASE_KEY (nếu là service role)
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"role": db_gv.vai_tro, "display_name": f"{db_gv.hodem} {db_gv.ten}"}
            },
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        if resp.status_code not in (200, 201):
            # Nếu lỗi, có thể do key không có quyền admin hoặc user đã tồn tại
            detail = resp.json()
            raise HTTPException(status_code=resp.status_code, detail=f"Supabase Auth Error: {detail}")

        auth_data = resp.json()
        auth_id = auth_data.get("id")
        
        # Cập nhật auth_id vào DB
        db_gv.auth_id = auth_id
        
        # Audit Log (Sử dụng ID người thực hiện nếu có, ở đây endpoint này chưa có get_current_user_id dependency nhưng nên có)
        # Tạm thời log với user_id của chính GV được tạo auth nếu không có admin id
        await log_audit(
            db=db,
            user_id=id, 
            action="CREATE_AUTH",
            entity="GiangVien",
            entity_id=id,
            details={"email": email},
            request=request
        )
        
        await db.commit()
        
        return {"message": "Auth account created and linked", "auth_id": auth_id}
