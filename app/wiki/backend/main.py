"""Main entry point for the Wiki API application."""

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import pages
from app.db import Base
from app.db import engine
from app.db import get_db

app = FastAPI(title="Wiki API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: Create tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(pages.router)

@app.get("/")
async def root():
    return {"message": "Wiki API is running"}

@app.get("/export")
async def export_data(db: AsyncSession = Depends(get_db)):
    from .export import export_all_to_zip
    from fastapi.responses import StreamingResponse
    
    zip_buffer = await export_all_to_zip(db)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=wiki_export.zip"}
    )
