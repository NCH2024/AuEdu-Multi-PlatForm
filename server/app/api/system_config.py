# Server/app/api/system_config.py
"""
API quản lý cấu hình hệ thống (system_config).
Cung cấp CRUD cho bảng key-value config, bao gồm:
- GET  /           : Lấy toàn bộ config (admin only)
- GET  /public     : Lấy config an toàn cho client bootstrap
- GET  /{key}      : Lấy config theo key
- PUT  /{key}      : Cập nhật config theo key
- POST /batch      : Cập nhật hàng loạt config
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Any, Dict, List, Union
from app.db.session import get_db
from app.db.models import SystemConfig, GiangVien
from app.core.security import get_current_user_id
from app.core.audit import log_audit
from fastapi import Request

router = APIRouter()

# Danh sách các key nhạy cảm — KHÔNG trả về qua /public
_SENSITIVE_KEYS = {"supabase_key"}


class ConfigUpdate(BaseModel):
    """Schema cập nhật config đơn lẻ."""
    value: Any
    description: Optional[str] = None


class ConfigBatchItem(BaseModel):
    """Schema cho từng item trong batch update dạng list."""
    key: str
    value: Any


@router.get("/")
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    """Trả về toàn bộ config — dành cho admin dashboard."""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return [{"key": c.key, "value": c.value, "description": c.description} for c in configs]


@router.get("/public")
async def get_public_configs(db: AsyncSession = Depends(get_db)):
    """
    Trả về config an toàn cho client bootstrap.
    Loại bỏ các key nhạy cảm (VD: supabase_key).
    Client gọi endpoint này khi khởi động để đồng bộ config từ server.
    """
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return [
        {"key": c.key, "value": c.value}
        for c in configs
        if c.key not in _SENSITIVE_KEYS
    ]


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    """Lấy config theo key cụ thể."""
    db_cfg = await db.get(SystemConfig, key)
    if not db_cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"key": db_cfg.key, "value": db_cfg.value, "description": db_cfg.description}


@router.put("/{key}")
async def update_config(
    key: str, 
    cfg: ConfigUpdate, 
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Cập nhật hoặc tạo mới config theo key (upsert)."""
    db_cfg = await db.get(SystemConfig, key)
    if not db_cfg:
        db_cfg = SystemConfig(key=key, value=cfg.value, description=cfg.description)
        db.add(db_cfg)
    else:
        db_cfg.value = cfg.value
        if cfg.description is not None:
            db_cfg.description = cfg.description

    await db.commit()
    await db.refresh(db_cfg)

    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="UPDATE",
        entity="SystemConfig",
        entity_id=key,
        details=cfg.model_dump(),
        request=request
    )
    await db.commit()

    return {"message": "Config updated successfully", "key": db_cfg.key}


@router.post("/batch")
async def update_configs_batch(
    configs: Union[List[ConfigBatchItem], Dict[str, Any]],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Cập nhật hàng loạt cấu hình hệ thống (upsert).
    Hỗ trợ 2 format đầu vào:
      - List[{key, value}]  — format chuẩn từ system_settings_page
      - Dict[str, Any]      — format nhanh {key: value}
    """
    # Chuẩn hóa về list of tuples (key, value)
    items: list[tuple[str, Any]] = []
    if isinstance(configs, list):
        items = [(item.key, item.value) for item in configs]
    elif isinstance(configs, dict):
        items = list(configs.items())

    for key, value in items:
        db_cfg = await db.get(SystemConfig, key)
        if not db_cfg:
            db_cfg = SystemConfig(key=key, value=value)
            db.add(db_cfg)
        else:
            db_cfg.value = value

    await db.commit()

    # Audit Log
    await log_audit(
        db=db,
        user_id=current_user_id,
        action="BATCH_UPDATE",
        entity="SystemConfig",
        details={"count": len(items), "keys": [i[0] for i in items]},
        request=request
    )
    await db.commit()

    return {"message": f"Batch updated {len(items)} configs successfully"}
