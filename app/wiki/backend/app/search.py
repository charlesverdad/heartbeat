"""Full-text search services for the Wiki."""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Page
from app.schemas import Page as PageSchema

async def search_pages(db: AsyncSession, query: str, user_id: UUID) -> List[Page]:
    # This query uses PostgreSQL Full-Text Search and filters by user permissions
    # Note: In a real app, the permission check would be integrated into the SQL query
    # for performance. Here we'll do a basic search and assume filtering happens after.
    # But let's try to do it slightly better.
    
    # Simple search query using plainto_tsquery for safety
    stmt = select(Page).where(
        Page.search_vector.op("@@")(text(f"plainto_tsquery('english', :query)")).params(query=query)
    )
    
    result = await db.execute(stmt)
    pages = result.scalars().all()
    
    # TODO: Refined permission filtering in SQL
    # For MVP, we'll filter in Python for now (not ideal for large datasets)
    from app.services import check_permission
    from app.models import User
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    
    accessible_pages = []
    for page in pages:
        if await check_permission(db, user, page.id, "PAGE", "VIEW"):
            accessible_pages.append(page)
            
    return accessible_pages

async def update_page_search_vector(db: AsyncSession, page_id: UUID):
    # This would typically be a trigger in Postgres, but we can do it manually for MVP
    await db.execute(
        text(
            """
            UPDATE pages 
            SET search_vector = to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
            WHERE id = :page_id
            """
        ).params(page_id=page_id)
    )
    await db.commit()
