"""Main entry point for the Wiki API application."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import admin
from app.api import auth
from app.api import folders
from app.api import pages
from app.api import settings # Added this line to import settings
from app.db import Base
from app.db import engine
from app.db import get_db
from app.models import Role
from app.models import User

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and default data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        from app.models import UserRole
        
        # Create default system roles if they don't exist
        system_roles = [
            ("superadmin", "Super Admin", "Full system access"),
            ("admin", "Admin", "Administrative access"),
            ("member", "Member", "Standard member access"),
            ("public", "Public", "Public access only")
        ]
        
        for role_id, role_name, description in system_roles:
            result = await session.execute(select(Role).where(Role.id == role_id))
            if not result.scalar_one_or_none():
                session.add(Role(
                    id=role_id,
                    name=role_name,
                    is_system=True,
                    description=description
                ))
        
        await session.commit()
        
        # Create default admin user if not exists
        admin_email = "admin@admin.com"
        result = await session.execute(select(User).where(User.email == admin_email))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            logger.info(f"Creating default admin user: {admin_email}")
            admin_user = User(
                email=admin_email,
                full_name="System Admin",
                password_hash=pwd_context.hash("password")
            )
            session.add(admin_user)
            await session.flush()  # Get the admin_user.id
            
            # Assign superadmin role to admin user
            user_role = UserRole(user_id=admin_user.id, role_id="superadmin")
            session.add(user_role)
        
        await session.commit()
    
    yield
    # Shutdown logic (if any)

app = FastAPI(title="Wiki API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(folders.router)
app.include_router(settings.router)
app.include_router(pages.router)

@app.get("/")
async def root():
    return {"message": "Wiki API is running"}

@app.get("/export")
async def export_data(db: AsyncSession = Depends(get_db)):
    from app.export import export_all_to_zip
    from fastapi.responses import StreamingResponse
    
    zip_buffer = await export_all_to_zip(db)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=wiki_export.zip"}
    )
