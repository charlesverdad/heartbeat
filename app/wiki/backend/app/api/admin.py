"""API endpoints for Admin management (Users and Roles)."""

from typing import List
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Role as RoleModel
from app.models import User as UserModel
from app.schemas import Role as RoleSchema
from app.schemas import User as UserSchema
from app.schemas import UserUpdate as UserUpdateSchema

router = APIRouter(prefix="/admin", tags=["admin"])

async def check_admin(current_user: UserModel = Depends(get_current_user)):
    if current_user.role_id != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/users", response_model=List[UserSchema])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: UserModel = Depends(check_admin)
):
    result = await db.execute(select(UserModel))
    return result.scalars().all()

@router.patch("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: UUID,
    user_update: UserUpdateSchema,
    db: AsyncSession = Depends(get_db),
    _admin: UserModel = Depends(check_admin)
):
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role_id is not None:
        user.role_id = user_update.role_id
    # We don't update email or password here for now
    
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _admin: UserModel = Depends(check_admin)
):
    result = await db.execute(select(RoleModel))
    return result.scalars().all()
