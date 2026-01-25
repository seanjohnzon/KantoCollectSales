"""
Inventory models for tracking owned cards and their market data.

This is the unified system that connects:
- Cards you own (from Railway tracker)
- Price history (from PriceCharting)
- AI insights (from Claude)
- Watchlist for flip opportunities
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlmodel import Field, SQLModel, Relationship


class CardCondition(str, Enum):
    """Card condition grades."""
    NEAR_MINT = "NM"
    LIGHTLY_PLAYED = "LP"
    MODERATELY_PLAYED = "MP"
    HEAVILY_PLAYED = "HP"
    DAMAGED = "DMG"


class CardLanguage(str, Enum):
    """Card language/region."""
    ENGLISH = "English"
    JAPANESE = "Japanese"


class InventoryStatus(str, Enum):
    """Status of inventory item."""
    IN_STOCK = "in_stock"
    LISTED = "listed"
    SOLD = "sold"
    RESERVED = "reserved"


# =============================================================================
# MASTER CARD REFERENCE (normalized card data)
# =============================================================================

class MasterCard(SQLModel, table=True):
    """
    Master reference for all known One Piece cards.
    
    This is the canonical source of truth for card data.
    Populated from PriceCharting URLs and manual entries.
    
    Attributes:
        id: Primary key.
        card_number: Official card number (e.g., "OP09-093").
        name: Card name (e.g., "Marshall D. Teach").
        set_code: Set code (e.g., "OP-09").
        set_name: Full set name (e.g., "Emperors in the New World").
        variant: Card variant (Alternate Art, Event, etc.).
        rarity: Card rarity (C, UC, R, SR, SEC, etc.).
        pricecharting_url: Direct URL to PriceCharting page.
        pricecharting_id: Extracted ID for API calls.
        image_url: URL to card image.
        created_at: When first added.
        updated_at: Last modification.
    """
    
    __tablename__ = "master_cards"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Card identification
    card_number: str = Field(index=True, unique=True)  # OP09-093
    name: str = Field(index=True)
    set_code: str = Field(index=True)  # OP-09
    set_name: Optional[str] = None  # Emperors in the New World
    variant: Optional[str] = None  # Alternate Art, Event, etc.
    rarity: Optional[str] = None  # SR, SEC, etc.
    
    # PriceCharting integration
    pricecharting_url: Optional[str] = None
    pricecharting_id: Optional[str] = None
    
    # Card image
    image_url: Optional[str] = None
    
    # User-defined scores (from your tracker)
    rarity_score: Optional[int] = Field(default=None)  # 0-100
    manual_priority: Optional[int] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    price_history: List["PriceHistory"] = Relationship(back_populates="card")
    inventory_items: List["InventoryItem"] = Relationship(back_populates="master_card")
    watchlist_entries: List["WatchlistItem"] = Relationship(back_populates="card")


# =============================================================================
# PRICE HISTORY (daily snapshots from PriceCharting)
# =============================================================================

class PriceHistory(SQLModel, table=True):
    """
    Historical price data from PriceCharting.
    
    Track price trends over time for smart flip decisions.
    
    Attributes:
        id: Primary key.
        master_card_id: FK to MasterCard.
        price_usd: Price in USD at the time.
        loose_price: PriceCharting "loose" price.
        cib_price: PriceCharting "complete in box" price.
        new_price: PriceCharting "new/sealed" price.
        recorded_at: When this price was recorded.
    """
    
    __tablename__ = "price_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    master_card_id: int = Field(foreign_key="master_cards.id", index=True)
    
    # Prices
    price_usd: float  # Main/average price
    loose_price: Optional[float] = None
    cib_price: Optional[float] = None
    new_price: Optional[float] = None
    
    # Metadata
    source: str = "pricecharting"
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    card: Optional[MasterCard] = Relationship(back_populates="price_history")


# =============================================================================
# INVENTORY (cards you actually own)
# =============================================================================

class InventoryItem(SQLModel, table=True):
    """
    Cards in your physical inventory.
    
    Track what you own, where it is, and its status.
    
    Attributes:
        id: Primary key.
        master_card_id: FK to MasterCard.
        quantity: How many you own.
        condition: Card condition (NM, LP, etc.).
        language: Card language.
        cost_basis: What you paid per card.
        location: Where the card is stored.
        status: Current status (in_stock, listed, sold).
        notes: Any notes about this item.
    """
    
    __tablename__ = "inventory"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    master_card_id: int = Field(foreign_key="master_cards.id", index=True)
    
    # Inventory details
    quantity: int = Field(default=1)
    condition: CardCondition = Field(default=CardCondition.NEAR_MINT)
    language: CardLanguage = Field(default=CardLanguage.ENGLISH)
    
    # Cost tracking
    cost_basis: Optional[float] = None  # What you paid
    
    # Location/status
    location: Optional[str] = None  # e.g., "Binder 1", "Grading"
    status: InventoryStatus = Field(default=InventoryStatus.IN_STOCK)
    
    # Sales tracking (when sold)
    sold_price: Optional[float] = None
    sold_at: Optional[datetime] = None
    sold_platform: Optional[str] = None  # Whatnot, eBay, etc.
    
    # Notes
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    master_card: Optional[MasterCard] = Relationship(back_populates="inventory_items")


# =============================================================================
# WATCHLIST (cards to monitor for flip opportunities)
# =============================================================================

class WatchlistItem(SQLModel, table=True):
    """
    Cards you're watching for price movements.
    
    Set target prices and get notified when they hit.
    
    Attributes:
        id: Primary key.
        master_card_id: FK to MasterCard.
        target_buy_price: Buy if price drops to this.
        target_sell_price: Sell if price rises to this.
        notes: Why you're watching this card.
        is_active: Whether to actively monitor.
    """
    
    __tablename__ = "watchlist"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    master_card_id: int = Field(foreign_key="master_cards.id", index=True)
    
    # Targets
    target_buy_price: Optional[float] = None  # Alert when price drops
    target_sell_price: Optional[float] = None  # Alert when price rises
    
    # Monitoring
    notes: Optional[str] = None
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    card: Optional[MasterCard] = Relationship(back_populates="watchlist_entries")


# =============================================================================
# AI INSIGHTS (Claude's analysis stored for reference)
# =============================================================================

class AIInsight(SQLModel, table=True):
    """
    AI-generated insights about cards or market.
    
    Store Claude's analysis for reference and learning.
    
    Attributes:
        id: Primary key.
        master_card_id: Optional FK if about a specific card.
        insight_type: Category (flip_opportunity, market_trend, etc.).
        content: The actual insight text.
        confidence: How confident the AI is (0-100).
        created_at: When generated.
    """
    
    __tablename__ = "ai_insights"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    master_card_id: Optional[int] = Field(default=None, foreign_key="master_cards.id")
    
    # Insight details
    insight_type: str  # flip_opportunity, market_trend, buy_alert, sell_alert
    content: str
    confidence: Optional[int] = None  # 0-100
    
    # User feedback
    was_helpful: Optional[bool] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PYDANTIC SCHEMAS FOR API
# =============================================================================

class MasterCardRead(SQLModel):
    """Read schema for MasterCard."""
    id: int
    card_number: str
    name: str
    set_code: str
    set_name: Optional[str]
    variant: Optional[str]
    rarity: Optional[str]
    pricecharting_url: Optional[str]
    image_url: Optional[str]
    rarity_score: Optional[int]
    manual_priority: Optional[int]


class MasterCardCreate(SQLModel):
    """Create schema for MasterCard."""
    card_number: str
    name: str
    set_code: str
    set_name: Optional[str] = None
    variant: Optional[str] = None
    rarity: Optional[str] = None
    pricecharting_url: Optional[str] = None
    image_url: Optional[str] = None
    rarity_score: Optional[int] = None
    manual_priority: Optional[int] = None


class InventoryItemRead(SQLModel):
    """Read schema for InventoryItem with card details."""
    id: int
    quantity: int
    condition: CardCondition
    language: CardLanguage
    cost_basis: Optional[float]
    location: Optional[str]
    status: InventoryStatus
    notes: Optional[str]
    # Nested card info
    card: Optional[MasterCardRead] = None
    # Computed
    current_price: Optional[float] = None
    profit_loss: Optional[float] = None


class InventoryItemCreate(SQLModel):
    """Create schema for InventoryItem."""
    master_card_id: int
    quantity: int = 1
    condition: CardCondition = CardCondition.NEAR_MINT
    language: CardLanguage = CardLanguage.ENGLISH
    cost_basis: Optional[float] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class WatchlistItemRead(SQLModel):
    """Read schema for WatchlistItem."""
    id: int
    target_buy_price: Optional[float]
    target_sell_price: Optional[float]
    notes: Optional[str]
    is_active: bool
    card: Optional[MasterCardRead] = None
    current_price: Optional[float] = None


class PriceHistoryRead(SQLModel):
    """Read schema for PriceHistory."""
    id: int
    price_usd: float
    loose_price: Optional[float]
    recorded_at: datetime


class ImportResult(SQLModel):
    """Result of importing cards from Excel."""
    total_rows: int
    imported: int
    skipped: int
    errors: List[str]
