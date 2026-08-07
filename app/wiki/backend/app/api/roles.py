"""API endpoints for role management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Role, User, UserRole
from pydantic import BaseModel

router = APIRouter(prefix="/roles", tags=["roles"])


# Schemas
class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    is_system: bool
    description: Optional[str]
    user_count: int
    created_at: str

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    role_ids: List[str]


# Endpoints
@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all roles (system + custom)."""
    # Only superadmin/admin can view roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized to view roles")
    
    # Get all roles with user counts
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    
    role_responses = []
    for role in roles:
        # Count users with this role
        count_result = await db.execute(
            select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
        )
        user_count = count_result.scalar()
        
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            is_system=role.is_system,
            description=role.description,
            user_count=user_count,
            created_at=role.created_at.isoformat()
        ))
    
    return role_responses


@router.post("/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new custom role."""
    # Only superadmin/admin can create roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized to create roles")
    
    # Generate role ID from name (e.g., "Media Team" -> "media-team")
    role_id = role_in.name.lower().replace(" ", "-")
    
    # Check if role already exists
    result = await db.execute(select(Role).where(Role.id == role_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    
    # Create role
    new_role = Role(
        id=role_id,
        name=role_in.name,
        is_system=False,
        description=role_in.description,
        created_by=current_user.id
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)
    
    return RoleResponse(
        id=new_role.id,
        name=new_role.name,
        is_system=new_role.is_system,
        description=new_role.description,
        user_count=0,
        created_at=new_role.created_at.isoformat()
    )


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a custom role."""
    # Only superadmin/admin can update roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized to update roles")
    
    # Get role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Cannot modify system roles
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system roles")
    
    # Update fields
    if role_in.name:
        role.name = role_in.name
    if role_in.description is not None:
        role.description = role_in.description
    
    await db.commit()
    await db.refresh(role)
    
    # Get user count
    count_result = await db.execute(
        select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
    )
    user_count = count_result.scalar()
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        is_system=role.is_system,
        description=role.description,
        user_count=user_count,
        created_at=role.created_at.isoformat()
    )


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a custom role."""
    # Only superadmin/admin can delete roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized to delete roles")
    
    # Get role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Cannot delete system roles
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    # Check if role has users
    count_result = await db.execute(
        select(func.count(UserRole.id)).where(UserRole.role_id == role.id)
    )
    user_count = count_result.scalar()
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete role with {user_count} assigned users. Please reassign users first."
        )
    
    # Delete role
    await db.delete(role)
    await db.commit()
    return None


# User-Role Assignment Endpoints
@router.get("/users/{user_id}/roles", response_model=List[str])
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all roles assigned to a user."""
    # Only superadmin/admin can view user roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(
        select(UserRole.role_id).where(UserRole.user_id == user_id)
    )
    role_ids = result.scalars().all()
    return list(role_ids)


@router.post("/users/{user_id}/roles", status_code=204)
async def assign_user_roles(
    user_id: UUID,
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign roles to a user (replaces existing roles)."""
    # Only superadmin/admin can assign roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify all roles exist
    for role_id in assignment.role_ids:
        result = await db.execute(select(Role).where(Role.id == role_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Role '{role_id}' not found")
    
    # Remove existing roles
    await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    existing_roles = (await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )).scalars().all()
    for ur in existing_roles:
        await db.delete(ur)
    
    # Add new roles
    for role_id in assignment.role_ids:
        user_role = UserRole(user_id=user_id, role_id=role_id)
        db.add(user_role)
    
    await db.commit()
    return None


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def remove_user_role(
    user_id: UUID,
    role_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a role from a user."""
    # Only superadmin/admin can remove roles
    user_role_ids = [ur.role_id for ur in current_user.user_roles]
    if "superadmin" not in user_role_ids and "admin" not in user_role_ids:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find and delete the user-role assignment
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise HTTPException(status_code=404, detail="User role assignment not found")
    
    # Check if this is the user's last role
    count_result = await db.execute(
        select(func.count(UserRole.id)).where(UserRole.user_id == user_id)
    )
    role_count = count_result.scalar()
    if role_count <= 1:
        # Check allow_zero_role_users setting
        from app.models import Setting
        setting_result = await db.execute(
            select(Setting).where(Setting.key == "allow_zero_role_users")
        )
        setting = setting_result.scalar_one_or_none()
        allow_zero = setting and setting.value == "true" if setting else True
        
        if not allow_zero:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove last role. User must have at least one role."
            )
    
    await db.delete(user_role)
    await db.commit()
    return None

