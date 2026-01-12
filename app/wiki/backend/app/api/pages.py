from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from .db import get_db
from .auth import get_current_user
from .models import User
from .schemas import Page, PageCreate, PageUpdate
from .services import get_page, create_page, list_pages

router = APIRouter(prefix="/pages", tags=["pages"])

@router.get("/", response_model=List[Page])
async def read_pages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await list_pages(db, current_user)

@router.post("/", response_model=Page)
async def create_new_page(
    page_in: PageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has permission to create in the specified folder
    if page_in.folder_id:
        from .services import check_permission
        if not await check_permission(db, current_user, page_in.folder_id, "FOLDER", "EDIT"):
            raise HTTPException(status_code=403, detail="Not enough permissions for this folder")
            
    return await create_page(db, page_in, current_user.id)

@router.get("/{page_id}", response_model=Page)
async def read_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    page = await get_page(db, page_id, current_user)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found or access denied")
    return page
