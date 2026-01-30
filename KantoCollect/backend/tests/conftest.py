"""
Pytest configuration and fixtures.

Root-level fixtures shared across all test modules.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.main import app
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole


# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# === Project Paths ===

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """Return the test data directory."""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


# === Marker Configuration ===

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "admin: Tests requiring admin authentication")
    config.addinivalue_line("markers", "non_admin: Tests that don't require admin authentication")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "ui: UI browser tests")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")


def pytest_collection_modifyitems(config, items):
    """Automatically add markers based on test location."""
    for item in items:
        # Add api/ui markers based on path
        if "tests/api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        elif "tests/ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)

        # Add admin/non_admin markers based on path
        if "/admin/" in str(item.fspath):
            item.add_marker(pytest.mark.admin)
        elif "/non_admin/" in str(item.fspath):
            item.add_marker(pytest.mark.non_admin)


# === Core Database Fixtures ===


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """Create admin user for tests."""
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(test_db: AsyncSession) -> User:
    """Create regular user for tests."""
    user = User(
        email="user@test.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.USER,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Get admin auth token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, regular_user: User) -> str:
    """Get regular user auth token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "user@test.com", "password": "testpassword"},
    )
    return response.json()["access_token"]
