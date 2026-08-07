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
from app.models import Role, User, UserRole
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
        # Create default system roles
        system_roles = [
            ("superadmin", "Super Admin", "Full system access"),
            ("admin", "Admin", "Administrative access"),
            ("member", "Member", "Standard member access"),
            ("public", "Public", "Public access only")
        ]
        
        for role_id, role_name, description in system_roles:
            session.add(Role(
                id=role_id,
                name=role_name,
                is_system=True,
                description=description
            ))
        
        await session.flush()
        
        # Create default admin user
        admin_user = User(
            email="admin@admin.com",
            full_name="System Admin",
            password_hash=pwd_context.hash("password")
        )
        session.add(admin_user)
        await session.flush()
        
        # Assign superadmin role to admin user
        user_role = UserRole(user_id=admin_user.id, role_id="superadmin")
        session.add(user_role)
        
        await session.commit()
    
    yield

@pytest.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def async_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
async def admin_token(async_client):
    response = await async_client.post("/token", data={
        "username": "admin@admin.com",
        "password": "password"
    })
    return response.json()["access_token"]

@pytest.fixture
async def admin_user(db_session):
    """Get the admin user with roles loaded."""
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(User)
        .where(User.email == "admin@admin.com")
        .options(selectinload(User.user_roles))
    )
    return result.scalar_one()

@pytest.fixture
async def test_user(db_session):
    """Create a test user with no roles."""
    import uuid
    user = User(
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",  # Unique email per test
        full_name="Test User",
        password_hash=pwd_context.hash("testpass")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user, ["user_roles"])
    return user

