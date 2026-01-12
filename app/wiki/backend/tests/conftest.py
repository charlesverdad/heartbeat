import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.context import CryptContext
from sqlalchemy import select

import sys
import os
# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, get_db
from app.models import Role, User
from main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        # Create default roles
        for role_id, role_name in [("superadmin", "Super Admin"), ("admin", "Admin"), ("member", "Member"), ("public", "Public")]:
            session.add(Role(id=role_id, name=role_name))
        
        # Create default admin user
        admin_user = User(
            email="admin@admin.com",
            full_name="System Admin",
            role_id="superadmin",
            password_hash=pwd_context.hash("password")
        )
        session.add(admin_user)
        await session.commit()
    
    yield

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
async def admin_token(client):
    response = await client.post("/token", data={
        "username": "admin@admin.com",
        "password": "password"
    })
    return response.json()["access_token"]
