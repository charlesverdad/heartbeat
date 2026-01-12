from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from .db import engine, Base, get_db
from .api import pages

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
