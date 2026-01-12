"""Search services for the Wiki using generic SQL."""

from typing import List
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Page
from app.schemas import Page as PageSchema


async def search_pages(db: AsyncSession, query: str, user_id: UUID) -> List[Page]:
    """Search pages using generic SQL LIKE.
    
    Note: Full-text search with SQLite FTS5 could be implemented later.
    """
    search_pattern = f"%{query}%"
    stmt = select(Page).where(
        or_(
            Page.title.ilike(search_pattern),
            Page.content.ilike(search_pattern)
        )
    )
    
    result = await db.execute(stmt)
    pages = result.scalars().all()
    
    # Filtering by user permissions
    from app.services import check_permission
    from app.models import User
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        return []
    
    accessible_pages = []
    for page in pages:
        if await check_permission(db, user, page.id, "PAGE", "VIEW"):
            accessible_pages.append(page)
            
    return accessible_pages


async def update_page_search_vector(db: AsyncSession, page_id: UUID):
    """No-op for SQLite implementation."""
    pass
