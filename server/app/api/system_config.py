from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Any, Dict
from app.db.session import get_db
from app.db.models import SystemConfig

router = APIRouter()

class ConfigUpdate(BaseModel):
    value: Dict[str, Any]
    description: Optional[str] = None

@router.get("/")
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemConfig))
    return result.scalars().all()

@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    db_cfg = await db.get(SystemConfig, key)
    if not db_cfg:
        raise HTTPException(status_code=404, detail="Config not found")
    return db_cfg

@router.put("/{key}")
async def update_config(key: str, cfg: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    db_cfg = await db.get(SystemConfig, key)
    if not db_cfg:
        # Create if not exists
        db_cfg = SystemConfig(key=key, value=cfg.value, description=cfg.description)
        db.add(db_cfg)
    else:
        db_cfg.value = cfg.value
        if cfg.description is not None:
            db_cfg.description = cfg.description
            
    await db.commit()
    await db.refresh(db_cfg)
    return {"message": "Config updated successfully", "key": db_cfg.key}
