from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import Setting, User
from app.schemas import Setting as SettingSchema, SettingUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/", response_model=List[SettingSchema])
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    return result.scalars().all()

@router.put("/{key}", response_model=SettingSchema)
async def update_setting(
    key: str,
    setting_in: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role_id != "superadmin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        setting = Setting(key=key, value=setting_in.value)
        db.add(setting)
    else:
        setting.value = setting_in.value
        
    await db.commit()
    await db.refresh(setting)
    return setting
