"""
API Dependencies.

Shared dependencies for authentication, database sessions, etc.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.security import decode_access_token, TokenData
from app.models.user import User, UserRole

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to get the current authenticated user.

    Args:
        token: JWT access token from Authorization header or simple admin key.
        db: Database session.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    from app.core.config import settings

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # If no token provided, raise exception
    if not token:
        raise credentials_exception

    # Check if token is the simple admin key
    if token == settings.admin_key:
        # Return first admin user for simple key auth
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN).limit(1)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        raise credentials_exception

    # Otherwise, try JWT validation
    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_optional_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, otherwise None.
    Used for read-only endpoints that don't require authentication.

    Args:
        token: JWT access token from Authorization header or simple admin key.
        db: Database session.

    Returns:
        User | None: The authenticated user or None if not authenticated.
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to ensure current user is an admin.
    
    Args:
        current_user: The authenticated user.
    
    Returns:
        User: The authenticated admin user.
    
    Raises:
        HTTPException: If user is not an admin.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
