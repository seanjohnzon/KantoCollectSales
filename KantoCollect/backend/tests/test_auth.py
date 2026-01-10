"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_first_admin(client: AsyncClient):
    """Test creating first admin user."""
    response = await client.post(
        "/api/v1/auth/create-admin",
        json={
            "email": "newadmin@test.com",
            "password": "securepassword",
            "full_name": "New Admin",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newadmin@test.com"
    assert data["role"] == "admin"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user: User):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user: User):
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "wrongpassword"},
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password"},
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, admin_token: str):
    """Test getting current user info."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_access_without_token(client: AsyncClient):
    """Test accessing protected route without token."""
    response = await client.get("/api/v1/auth/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_with_invalid_token(client: AsyncClient):
    """Test accessing protected route with invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    
    assert response.status_code == 401
