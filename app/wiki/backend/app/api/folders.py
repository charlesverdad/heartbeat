"""API endpoints for Folder management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Folder as FolderModel
from app.models import User as UserModel
from app.schemas import Folder as FolderSchema
from app.schemas import FolderBase as FolderCreateSchema

router = APIRouter(prefix="/folders", tags=["folders"])

@router.get("", response_model=List[FolderSchema])
async def list_folders(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(select(FolderModel))
    return result.scalars().all()

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
