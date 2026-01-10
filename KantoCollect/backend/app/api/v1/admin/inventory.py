"""
Inventory management endpoints.

Admin-only endpoints for managing product inventory.
"""

from fastapi import APIRouter

from app.api.deps import AdminUser

router = APIRouter()


@router.get("/")
async def list_inventory(current_user: AdminUser):
    """
    List all inventory items.
    
    TODO: Implement after Deal Analyzer is complete.
    """
    return {
        "message": "Inventory endpoint - Coming soon",
        "user": current_user.email,
    }


@router.get("/stats")
async def inventory_stats(current_user: AdminUser):
    """
    Get inventory statistics.
    
    TODO: Implement after Deal Analyzer is complete.
    """
    return {
        "total_items": 0,
        "total_value": 0,
        "low_stock_alerts": 0,
    }
