"""
Database models using SQLModel.
"""

from .user import User, UserRole
from .card import (
    CardCache,
    CardGame,
    CardSource,
    UserCardIdentification,
    CardCacheRead,
    CardSearchResult,
)
from .inventory import (
    MasterCard,
    PriceHistory,
    InventoryItem,
    WatchlistItem,
    AIInsight,
    CardCondition,
    CardLanguage,
    InventoryStatus,
    MasterCardRead,
    MasterCardCreate,
    InventoryItemRead,
    InventoryItemCreate,
    WatchlistItemRead,
    PriceHistoryRead,
    ImportResult,
)

__all__ = [
    # User
    "User",
    "UserRole",
    # Legacy card cache
    "CardCache",
    "CardGame",
    "CardSource",
    "UserCardIdentification",
    "CardCacheRead",
    "CardSearchResult",
    # New inventory system
    "MasterCard",
    "PriceHistory",
    "InventoryItem",
    "WatchlistItem",
    "AIInsight",
    "CardCondition",
    "CardLanguage",
    "InventoryStatus",
    "MasterCardRead",
    "MasterCardCreate",
    "InventoryItemRead",
    "InventoryItemCreate",
    "WatchlistItemRead",
    "PriceHistoryRead",
    "ImportResult",
]
