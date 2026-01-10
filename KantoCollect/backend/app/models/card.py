"""
Card cache model for storing card data from external APIs.

This avoids repeated API calls by caching card information locally.
Images are NOT stored - only URLs are cached.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class CardGame(str, Enum):
    """Supported card games."""
    ONE_PIECE = "one_piece"
    POKEMON = "pokemon"


class CardSource(str, Enum):
    """Source API for card data."""
    ONEPIECE_CARDGAME_DEV = "onepiece-cardgame.dev"
    POKEMON_TCG_IO = "pokemontcg.io"
    PRICECHARTING = "pricecharting"
    USER_ADDED = "user_added"


class CardCache(SQLModel, table=True):
    """
    Cached card data from external APIs.
    
    Stores card metadata and image URLs (not actual images).
    Used to quickly identify cards without repeated API calls.
    
    Attributes:
        id: Primary key (local).
        external_id: Card ID from source API.
        game: Which game (One Piece, Pokemon).
        source: Which API provided this data.
        name: Card name.
        set_name: Set/expansion name.
        card_number: Card number in set (e.g., "OP01-001").
        cost: Card cost/energy (for One Piece).
        power: Card power (for One Piece).
        color: Card color(s).
        rarity: Card rarity.
        card_type: Type (Leader, Character, Event, etc.).
        image_url: URL to card image (NOT stored locally).
        pricecharting_id: ID for PriceCharting lookup.
        last_price_usd: Cached price from last lookup.
        price_updated_at: When price was last fetched.
        created_at: When cached.
        updated_at: When cache was refreshed.
    """
    
    __tablename__ = "card_cache"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)
    game: CardGame
    source: CardSource
    
    # Card identification
    name: str = Field(index=True)
    set_name: Optional[str] = None
    card_number: Optional[str] = Field(default=None, index=True)
    
    # Card attributes (for matching)
    cost: Optional[int] = None
    power: Optional[int] = None
    color: Optional[str] = None
    rarity: Optional[str] = None
    card_type: Optional[str] = None
    
    # Image (URL only, not stored)
    image_url: Optional[str] = None
    
    # Price tracking
    pricecharting_id: Optional[str] = None
    last_price_usd: Optional[float] = None
    price_updated_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCardIdentification(SQLModel, table=True):
    """
    Stores user-confirmed card identifications.
    
    When a user confirms which card matches their image,
    we store this to improve future suggestions.
    
    Attributes:
        id: Primary key.
        card_cache_id: Foreign key to CardCache.
        ai_detected_name: What the AI initially thought.
        ai_detected_cost: Cost AI extracted.
        ai_detected_power: Power AI extracted.
        ai_detected_color: Color AI extracted.
        confirmed: Whether user confirmed this match.
        created_at: When identification happened.
    """
    
    __tablename__ = "user_card_identifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    card_cache_id: int = Field(foreign_key="card_cache.id", index=True)
    
    # What AI detected
    ai_detected_name: Optional[str] = None
    ai_detected_cost: Optional[int] = None
    ai_detected_power: Optional[int] = None
    ai_detected_color: Optional[str] = None
    
    # User feedback
    confirmed: bool = False
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Pydantic schemas for API responses
class CardCacheRead(SQLModel):
    """Schema for reading cached card data."""
    id: int
    external_id: str
    game: CardGame
    name: str
    set_name: Optional[str]
    card_number: Optional[str]
    cost: Optional[int]
    power: Optional[int]
    color: Optional[str]
    rarity: Optional[str]
    card_type: Optional[str]
    image_url: Optional[str]
    last_price_usd: Optional[float]


class CardSearchResult(SQLModel):
    """Schema for card search results with match score."""
    card: CardCacheRead
    match_score: float  # 0.0 to 1.0
    match_reason: str  # Why this card matched
