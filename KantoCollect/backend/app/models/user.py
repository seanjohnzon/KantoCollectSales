"""
User model for authentication and authorization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"


class UserBase(SQLModel):
    """Base user fields shared across schemas."""
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.USER


class User(UserBase, table=True):
    """
    User database model.
    
    Attributes:
        id: Primary key.
        email: Unique email address.
        full_name: Optional display name.
        hashed_password: Bcrypt hashed password.
        is_active: Whether user can log in.
        role: User role (admin or user).
        created_at: Account creation timestamp.
        updated_at: Last update timestamp.
    """
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(SQLModel):
    """Schema for creating a new user."""
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserRead(UserBase):
    """Schema for reading user data (no password)."""
    id: int
    created_at: datetime


class UserUpdate(SQLModel):
    """Schema for updating user data."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
