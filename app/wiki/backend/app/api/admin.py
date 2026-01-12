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

@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _admin: UserModel = Depends(check_admin)
):
    result = await db.execute(select(RoleModel))
    return result.scalars().all()
