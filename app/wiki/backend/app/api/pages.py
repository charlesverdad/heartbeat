"""API endpoints for Page management."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_optional
from app.db import get_db
from app.models import User
from app.schemas import Page
from app.schemas import PageCreate
from app.schemas import PageUpdate
from app.services import create_page
from app.services import get_page
from app.services import list_pages
from app.services import update_page
from app.search import search_pages

router = APIRouter(prefix="/pages", tags=["pages"])

@router.get("/", response_model=List[Page])
async def read_pages(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    return await list_pages(db, current_user)

@router.get("/search", response_model=List[Page])
async def search_wiki_pages(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    return await search_pages(db, q, current_user.id if current_user else None)

@router.post("/", response_model=Page)
async def create_new_page(
    page_in: PageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has permission to create in the specified folder
    if page_in.folder_id:
        from app.services import check_permission
        if not await check_permission(db, current_user, page_in.folder_id, "FOLDER", "EDIT"):
            raise HTTPException(status_code=403, detail="Not enough permissions for this folder")
            
    return await create_page(db, page_in, current_user.id)

@router.get("/{page_id}", response_model=Page)
async def read_page(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    page = await get_page(db, page_id, current_user)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found or access denied")
    return page

@router.put("/{page_id}", response_model=Page)
async def update_page_endpoint(
    page_id: UUID,
    page_in: PageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    page = await update_page(db, page_id, page_in, current_user)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found or access denied")
    return page

@router.get("/{page_id}/subpage-count")
async def get_page_subpage_count(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the count of non-deleted subpages for a page."""
    from sqlalchemy import func
    from app.models import Page as PageModel
    
    result = await db.execute(
        select(func.count(PageModel.id))
        .where(PageModel.parent_id == page_id)
        .where(PageModel.deleted_at.is_(None))
    )
    count = result.scalar()
    return {"count": count}

@router.patch("/{page_id}", response_model=Page)
async def patch_page_endpoint(
    page_id: UUID,
    page_in: PageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Partial update for pages (e.g., just renaming)."""
    page = await update_page(db, page_id, page_in, current_user)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found or access denied")
    return page

@router.delete("/{page_id}", status_code=204)
async def delete_page_endpoint(
    page_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a page (move to trash)."""
    from app.services import delete_page
    
    if not await delete_page(db, page_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this page or page not found")
    return None

