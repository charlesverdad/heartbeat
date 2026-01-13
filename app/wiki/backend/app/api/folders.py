"""API endpoints for Folder management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_optional
from app.db import get_db
from app.models import Folder as FolderModel
from app.models import User as UserModel
from app.schemas import Folder as FolderSchema
from app.schemas import FolderBase as FolderCreateSchema
from app.services import delete_folder

router = APIRouter(prefix="/folders", tags=["folders"])

@router.get("", response_model=List[FolderSchema])
async def list_folders(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
):
    # For MVP, just return folders user has VIEW permission for OR are public
    # This is similar logic to pages.py list_pages
    result = await db.execute(select(FolderModel))
    all_folders = result.scalars().all()
    
    from app.services import check_permission
    accessible_folders = []
    for folder in all_folders:
        if await check_permission(db, current_user, folder.id, "FOLDER", "VIEW"):
            accessible_folders.append(folder)
            
    return accessible_folders

@router.post("", response_model=FolderSchema)
async def create_folder(
    folder_in: FolderCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Basic permission check: only admins can create folders in this MVP
    if current_user.role_id not in ["superadmin", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to create folders")
        
    folder = FolderModel(
        name=folder_in.name,
        parent_id=folder_in.parent_id,
        order=0 # Default order
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder

@router.patch("/{folder_id}", response_model=FolderSchema)
async def update_folder(
    folder_id: UUID,
    folder_in: FolderCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    from app.services import check_permission
    
    # Check if user has MANAGE permission on this folder
    if not await check_permission(db, current_user, folder_id, "FOLDER", "MANAGE"):
        raise HTTPException(status_code=403, detail="Not authorized to update this folder")
    
    # Get the folder
    result = await db.execute(select(FolderModel).where(FolderModel.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Update the folder name
    if folder_in.name:
        folder.name = folder_in.name
    if folder_in.parent_id is not None:
        folder.parent_id = folder_in.parent_id
    
    await db.commit()
    await db.refresh(folder)
    return folder

@router.delete("/{folder_id}", status_code=204)
async def remove_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if not await delete_folder(db, folder_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this folder or folder not found")
    return None
