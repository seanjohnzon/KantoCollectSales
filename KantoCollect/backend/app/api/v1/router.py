"""
Main API v1 router.

Aggregates all v1 endpoint routers.
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .admin.router import router as admin_router

api_router = APIRouter()

# Public routes
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# Admin-only routes
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"],
)
