"""Core business logic and permission services."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Folder
from app.models import Page
from app.models import Permission
from app.models import User
from app.schemas import PageCreate
from app.schemas import PageUpdate

async def check_permission(
    db: AsyncSession,
    user: Optional[User],
    object_id: UUID,
    object_type: str,  # FOLDER or PAGE
    required_level: str # MANAGE, EDIT, VIEW
) -> bool:
    # Public objects are viewable by everyone
    if required_level == "VIEW":
        if object_type == "PAGE":
            page_result = await db.execute(select(Page).where(Page.id == object_id))
            page = page_result.scalar_one_or_none()
            if page and page.is_public:
                return True
        elif object_type == "FOLDER":
            folder_result = await db.execute(select(Folder).where(Folder.id == object_id))
            folder = folder_result.scalar_one_or_none()
            if folder and folder.is_public:
                return True

    if not user:
        return False

    # SuperAdmin has all permissions
    if user and user.role_id == "superadmin":
        return True
        
    # Check for direct permission
    stmt = select(Permission).where(
        and_(
            Permission.object_id == object_id,
            Permission.object_type == object_type,
            or_(
                and_(Permission.subject_type == "USER", Permission.subject_id == str(user.id)),
                and_(Permission.subject_type == "ROLE", Permission.subject_id == user.role_id)
            )
        )
    )
    result = await db.execute(stmt)
    perm = result.scalar_one_or_none()
    
    levels = ["VIEW", "EDIT", "MANAGE"]
    if perm:
        if levels.index(perm.level) >= levels.index(required_level):
            return True
            
    # If not found and it's a page, check folder permissions (inheritance)
    if object_type == "PAGE":
        page_result = await db.execute(select(Page).where(Page.id == object_id))
        page = page_result.scalar_one_or_none()
        if page and page.folder_id:
            return await check_permission(db, user, page.folder_id, "FOLDER", required_level)
            
    # If not found and it's a folder, check parent folder permissions (inheritance)
    if object_type == "FOLDER":
        folder_result = await db.execute(select(Folder).where(Folder.id == object_id))
        folder = folder_result.scalar_one_or_none()
        if folder and folder.parent_id:
            return await check_permission(db, user, folder.parent_id, "FOLDER", required_level)
            
    return False

async def get_page(db: AsyncSession, page_id: UUID, user: Optional[User]) -> Optional[Page]:
    if not await check_permission(db, user, page_id, "PAGE", "VIEW"):
        return None
    result = await db.execute(select(Page).where(Page.id == page_id))
    return result.scalar_one_or_none()

async def create_page(db: AsyncSession, page_data: PageCreate, author_id: UUID) -> Page:
    db_page = Page(
        **page_data.model_dump(),
        author_id=author_id
    )
    db.add(db_page)
    await db.commit()
    await db.refresh(db_page)
    return db_page

async def update_page(db: AsyncSession, page_id: UUID, page_data: PageUpdate, user: User) -> Optional[Page]:
    if not await check_permission(db, user, page_id, "PAGE", "EDIT"):
        return None
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        return None
    
    update_data = page_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(page, key, value)
    
    await db.commit()
    await db.refresh(page)
    return page

async def list_pages(db: AsyncSession, user: Optional[User]) -> List[Page]:
    # This is a naive implementation; in a real app, you'd filter in the query
    # However, for MVP, we'll fetch and filter if necessary, OR better:
    # Use a CTE or join to filter efficiently.
    # For now, let's fetch all and filter which is NOT efficient but demonstrates the logic.
    # Actually, let's just fetch those with permissions for better scalability.
    
    # Simple version for MVP: fetch all pages and check perms
    # Note: In production, we'd use a more complex SQL query to do this in one go.
    # Exclude deleted pages
    result = await db.execute(select(Page).where(Page.deleted_at.is_(None)))
    all_pages = result.scalars().all()
    
    accessible_pages = []
    for page in all_pages:
        if await check_permission(db, user, page.id, "PAGE", "VIEW"):
            accessible_pages.append(page)
    return accessible_pages

async def delete_folder(db: AsyncSession, folder_id: UUID, user: User) -> bool:
    """Soft delete a folder and all pages within it."""
    if not await check_permission(db, user, folder_id, "FOLDER", "MANAGE"):
        return False
        
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        return False
    
    from datetime import datetime
    from sqlalchemy import update
    
    # Soft delete the folder
    folder.deleted_at = datetime.utcnow()
    
    # Cascade soft delete to all pages in this folder
    await db.execute(
        update(Page)
        .where(Page.folder_id == folder_id)
        .values(deleted_at=datetime.utcnow())
    )
    
    await db.commit()
    return True

async def delete_page(db: AsyncSession, page_id: UUID, user: User) -> bool:
    """Soft delete a page."""
    if not await check_permission(db, user, page_id, "PAGE", "MANAGE"):
        return False
        
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        return False
    
    from datetime import datetime
    
    # Soft delete the page
    page.deleted_at = datetime.utcnow()
    
    await db.commit()
    return True

