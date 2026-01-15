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
from app.models import UserRole
from app.schemas import Role as RoleSchema
from app.schemas import User as UserSchema
from app.schemas import UserUpdate as UserUpdateSchema

router = APIRouter(prefix="/admin", tags=["admin"])

async def check_admin(current_user: UserModel = Depends(get_current_user)):
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids:
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
    users = result.scalars().all()
    
    # Convert to schema with roles
    user_list = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "last_login": user.last_login,
            "roles": [ur.role_id for ur in user.user_roles]
        }
        user_list.append(UserSchema(**user_dict))
    
    return user_list

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
    
    if user_update.role_ids is not None:
        # Remove existing roles
        existing_roles = (await db.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )).scalars().all()
        for ur in existing_roles:
            await db.delete(ur)
        
        # Add new roles
        for role_id in user_update.role_ids:
            # Verify role exists
            role_result = await db.execute(select(RoleModel).where(RoleModel.id == role_id))
            if not role_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"Role '{role_id}' not found")
            
            user_role = UserRole(user_id=user_id, role_id=role_id)
            db.add(user_role)
    
    await db.commit()
    await db.refresh(user)
    
    # Return user with roles
    user_dict = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "last_login": user.last_login,
        "roles": [ur.role_id for ur in user.user_roles]
    }
    return UserSchema(**user_dict)

@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _admin: UserModel = Depends(check_admin)
):
    result = await db.execute(select(RoleModel))
    return result.scalars().all()

