"""ZIP export services for the Wiki."""

import io
import os
import zipfile
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Folder
from app.models import Page
from app.schemas import Page as PageSchema

async def export_all_to_zip(db: AsyncSession) -> io.BytesIO:
    # Fetch all pages and folders
    # (Note: In a real app, this should probably be limited to what the user can see,
    # but the requirement said "backup all data").
    
    pages_result = await db.execute(select(Page))
    pages = pages_result.scalars().all()
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for page in pages:
            # Create a path based on folder hierarchy
            # Simple version: root/title.md
            filename = f"{page.title.replace('/', '_')}.md"
            content = f"--- \ntitle: {page.title}\ncreated_at: {page.created_at}\n---\n\n{page.content}"
            zip_file.writestr(filename, content)
            
    zip_buffer.seek(0)
    return zip_buffer
