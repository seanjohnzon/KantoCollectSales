"""
Authentication endpoints.

Handles user registration, login, and token management.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    Token,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserCreate, UserRead, UserRole
from app.api.deps import CurrentUser

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user.
    
    Args:
        user_in: User registration data.
        db: Database session.
    
    Returns:
        UserRead: Created user data.
    
    Raises:
        HTTPException: If email already registered.
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=user_in.role,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate user and return access token.
    
    Args:
        form_data: OAuth2 form with username (email) and password.
        db: Database session.
    
    Returns:
        Token: JWT access token.
    
    Raises:
        HTTPException: If credentials are invalid.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current authenticated user's information.
    
    Args:
        current_user: The authenticated user.
    
    Returns:
        UserRead: Current user data.
    """
    return current_user


@router.post("/create-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_first_admin(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create the first admin user.
    
    This endpoint only works if no admin users exist yet.
    Use this for initial setup.
    
    Args:
        user_in: Admin user data.
        db: Database session.
    
    Returns:
        UserRead: Created admin user.
    
    Raises:
        HTTPException: If an admin already exists.
    """
    # Check if any admin exists
    result = await db.execute(
        select(User).where(User.role == UserRole.ADMIN)
    )
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user already exists. Use regular registration.",
        )
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create admin user
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user
