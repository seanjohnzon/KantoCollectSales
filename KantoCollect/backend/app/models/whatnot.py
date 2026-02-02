"""
WhatNot sales tracking models.

Tracks sales from WhatNot streams with Excel import support and keyword-based COGS mapping.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from sqlmodel import Field, SQLModel, Relationship, Column, JSON


# === ENUMS ===

class MatchType(str, Enum):
    """Match type for COGS keyword rules."""
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EXACT = "exact"


class CatalogRuleType(str, Enum):
    """Rule type for product catalog keyword matching."""
    INCLUDE_ANY = "include_any"  # Must contain AT LEAST ONE include keyword
    INCLUDE_ALL = "include_all"  # Must contain ALL include keywords
    INCLUDE_AND_EXCLUDE = "include_and_exclude"  # Must have include keywords but NOT exclude keywords
    CATCH_ALL = "catch_all"  # Catches anything that doesn't match other items (for "Unmapped Items")


class Owner(str, Enum):
    """Transaction owner assignment."""
    CIHAN = "Cihan"
    NIMA = "Nima"
    ASKAR = "Askar"
    KANTO = "Kanto"


# === DATABASE MODELS ===

class WhatnotShow(SQLModel, table=True):
    """A WhatNot show/stream with aggregated sales data."""
    __tablename__ = "whatnot_shows"

    id: Optional[int] = Field(default=None, primary_key=True)
    show_date: date = Field(index=True)
    show_name: Optional[str] = None
    platform: str = Field(default="WhatNot")

    # Pre-computed aggregates
    total_gross_sales: Decimal = Field(default=Decimal("0"))
    total_discounts: Decimal = Field(default=Decimal("0"))
    total_whatnot_commission: Decimal = Field(default=Decimal("0"))
    total_whatnot_fees: Decimal = Field(default=Decimal("0"))
    total_payment_fees: Decimal = Field(default=Decimal("0"))
    total_shipping: Decimal = Field(default=Decimal("0"))
    total_net_earnings: Decimal = Field(default=Decimal("0"))
    total_cogs: Decimal = Field(default=Decimal("0"))
    total_net_profit: Decimal = Field(default=Decimal("0"))

    item_count: int = Field(default=0)
    unique_buyers: int = Field(default=0)
    avg_sale_price: Decimal = Field(default=Decimal("0"))

    # Import metadata
    excel_filename: Optional[str] = None
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    imported_by: Optional[int] = None
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transactions: List["SalesTransaction"] = Relationship(back_populates="show")


class SalesTransaction(SQLModel, table=True):
    """Individual sale transaction from WhatNot (stream or marketplace)."""
    __tablename__ = "sales_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    show_id: Optional[int] = Field(default=None, foreign_key="whatnot_shows.id", index=True)

    # Sale type: 'stream' or 'marketplace'
    sale_type: str = Field(default="stream", index=True)

    # Raw Excel data
    transaction_date: datetime = Field(index=True)
    sku: Optional[str] = None
    item_name: str
    quantity: int = Field(default=1)
    buyer_username: str

    # Marketplace-specific fields
    payment_status: Optional[str] = None  # For marketplace: Completed, Pending, etc.
    total_revenue: Optional[Decimal] = Field(default=None)  # Marketplace uses this instead of gross_sale_price

    # Financial data
    gross_sale_price: Decimal = Field(default=Decimal("0"))
    discount: Decimal = Field(default=Decimal("0"))
    whatnot_commission: Decimal = Field(default=Decimal("0"))
    whatnot_fee: Decimal = Field(default=Decimal("0"))
    payment_processing_fee: Decimal = Field(default=Decimal("0"))
    shipping: Decimal = Field(default=Decimal("0"))
    net_earnings: Decimal = Field(default=Decimal("0"))

    # Notes field for marketplace
    notes: Optional[str] = None

    # COGS and profit
    cogs: Optional[Decimal] = Field(default=None)
    net_profit: Optional[Decimal] = Field(default=None)
    roi_percent: Optional[Decimal] = Field(default=None)

    # Normalized references
    product_id: Optional[int] = Field(default=None, foreign_key="whatnot_products.id", index=True)
    buyer_id: Optional[int] = Field(default=None, foreign_key="whatnot_buyers.id", index=True)
    inventory_item_id: Optional[int] = None
    master_card_id: Optional[int] = Field(default=None, index=True)

    # COGS rule tracking
    matched_cogs_rule_id: Optional[int] = Field(default=None, foreign_key="cogs_mapping_rules.id")

    # Master Catalog mapping tracking
    catalog_item_id: Optional[int] = Field(default=None, foreign_key="product_catalog.id", index=True)
    is_mapped: bool = Field(default=False, index=True)  # Quick filter for mapped vs unmapped
    matched_keyword: Optional[str] = None  # Which keyword caused the match
    mapped_at: Optional[datetime] = None  # When it was mapped

    # Owner assignment
    owner: Optional[str] = Field(default=None, index=True)  # One of: Cihan, Nima, Askar, Kanto

    # Metadata
    row_number: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    show: Optional[WhatnotShow] = Relationship(back_populates="transactions")
    product: Optional["WhatnotProduct"] = Relationship(back_populates="transactions")
    buyer: Optional["WhatnotBuyer"] = Relationship(back_populates="transactions")
    matched_cogs_rule: Optional["COGSMappingRule"] = Relationship(back_populates="matched_transactions")


class WhatnotProduct(SQLModel, table=True):
    """Normalized product catalog from WhatNot sales."""
    __tablename__ = "whatnot_products"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str
    normalized_name: str = Field(index=True, unique=True)
    sku: Optional[str] = None

    # Aggregated metrics (updated on import)
    total_quantity_sold: int = Field(default=0)
    total_gross_sales: Decimal = Field(default=Decimal("0"))
    total_net_earnings: Decimal = Field(default=Decimal("0"))
    avg_sale_price: Decimal = Field(default=Decimal("0"))

    # Inventory linking
    master_card_id: Optional[int] = Field(default=None, index=True)
    default_cogs: Optional[Decimal] = Field(default=None)
    category: Optional[str] = None

    # Metadata
    first_sold_date: Optional[date] = None
    last_sold_date: Optional[date] = None
    times_sold: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transactions: List[SalesTransaction] = Relationship(back_populates="product")


class WhatnotBuyer(SQLModel, table=True):
    """Normalized buyer/customer data."""
    __tablename__ = "whatnot_buyers"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    display_name: Optional[str] = None

    # Aggregated metrics
    total_purchases: int = Field(default=0)
    total_spent: Decimal = Field(default=Decimal("0"))
    avg_purchase_price: Decimal = Field(default=Decimal("0"))

    # Engagement
    first_purchase_date: Optional[date] = None
    last_purchase_date: Optional[date] = None
    is_repeat_buyer: bool = Field(default=False)
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    transactions: List[SalesTransaction] = Relationship(back_populates="buyer")


class COGSMappingRule(SQLModel, table=True):
    """
    ⭐ CRITICAL: Keyword-based COGS assignment rules.

    Rules are checked in priority order (highest first) to automatically assign
    COGS to products based on name matching.
    """
    __tablename__ = "cogs_mapping_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    rule_name: str
    keywords: List[str] = Field(sa_column=Column(JSON))  # JSON array of strings
    cogs_amount: Decimal = Field()
    match_type: MatchType = Field(default=MatchType.CONTAINS)
    priority: int = Field(default=50, index=True)  # Higher = checked first
    is_active: bool = Field(default=True)
    category: Optional[str] = None
    notes: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    matched_transactions: List[SalesTransaction] = Relationship(back_populates="matched_cogs_rule")


class MonthlySummary(SQLModel, table=True):
    """Pre-computed monthly aggregates for performance."""
    __tablename__ = "monthly_summaries"

    id: Optional[int] = Field(default=None, primary_key=True)
    year: int
    month: int  # 1-12

    show_count: int = Field(default=0)
    total_items_sold: int = Field(default=0)
    total_gross_sales: Decimal = Field(default=Decimal("0"))
    total_net_earnings: Decimal = Field(default=Decimal("0"))
    total_cogs: Decimal = Field(default=Decimal("0"))
    total_net_profit: Decimal = Field(default=Decimal("0"))
    avg_roi_percent: Optional[Decimal] = Field(default=None)

    unique_buyers: int = Field(default=0)
    unique_products: int = Field(default=0)

    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ProductInventoryLink(SQLModel, table=True):
    """Many-to-many linking table for WhatNot products to inventory master cards."""
    __tablename__ = "product_inventory_links"

    id: Optional[int] = Field(default=None, primary_key=True)
    whatnot_product_id: int = Field(foreign_key="whatnot_products.id")
    master_card_id: int
    match_confidence: str = Field(default="manual")  # 'exact', 'fuzzy', 'manual'
    matched_at: datetime = Field(default_factory=datetime.utcnow)
    matched_by: Optional[int] = None  # FK to users.id if manual
    notes: Optional[str] = None


class ProductCatalog(SQLModel, table=True):
    """Master product catalog - curated list of main product types for COGS assignment."""
    __tablename__ = "product_catalog"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Product name (clean, without extension)
    category: str  # UPC, ETB, Booster Bundle, Singles, etc.
    image_url: str  # Full ImageKit URL
    image_filename: str  # Just the filename for reference

    # NEW: Rule-based matching system
    rule_type: CatalogRuleType = Field(default=CatalogRuleType.INCLUDE_ANY)  # Type of matching rule
    include_keywords: List[str] = Field(default=[], sa_column=Column(JSON))  # Must contain these keywords
    exclude_keywords: List[str] = Field(default=[], sa_column=Column(JSON))  # Must NOT contain these keywords
    priority: int = Field(default=100)  # Higher priority = checked first (for breaking ties)

    # OLD: Keep for backward compatibility during migration
    keywords: List[str] = Field(default=[], sa_column=Column(JSON))  # DEPRECATED: Use include_keywords instead

    # These will be computed from transactions
    sales_count: int = Field(default=0)  # Number of sales matched
    total_revenue: Decimal = Field(default=Decimal("0"))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = None  # Admin user ID

    # Relationships
    mapped_transactions: List["SalesTransaction"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[SalesTransaction.catalog_item_id]"}
    )
    inventory_items: List["WhatnotInventory"] = Relationship(back_populates="catalog_item")


class InventoryItemStatus(str, Enum):
    """Status of inventory item."""
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    RESERVED = "reserved"


class WhatnotInventory(SQLModel, table=True):
    """
    Inventory tracking for items the business has on hand.
    Links to ProductCatalog for product info and images.
    """
    __tablename__ = "whatnot_inventory"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Link to catalog item (optional - can have inventory without catalog entry)
    catalog_item_id: Optional[int] = Field(default=None, foreign_key="product_catalog.id", index=True)

    # Item details (if not linked to catalog)
    item_name: str = Field(index=True)
    sku: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = None
    image_url: Optional[str] = None  # Custom image if not using catalog

    # Inventory tracking
    quantity: int = Field(default=0)
    low_stock_threshold: int = Field(default=5)  # Alert when below this
    status: InventoryItemStatus = Field(default=InventoryItemStatus.IN_STOCK)

    # Cost tracking
    cost_per_unit: Optional[Decimal] = Field(default=None)  # What we paid per unit
    total_cost: Optional[Decimal] = Field(default=None)  # Total investment

    # Location/organization
    location: Optional[str] = None  # e.g., "Shelf A", "Storage Box 1"
    bin_number: Optional[str] = None

    # Supplier info
    supplier: Optional[str] = None
    last_restock_date: Optional[date] = None

    # Notes
    notes: Optional[str] = None

    # Owner assignment
    owner: Optional[str] = Field(default=None, index=True)  # Cihan, Nima, Askar, Kanto

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    catalog_item: Optional[ProductCatalog] = Relationship(back_populates="inventory_items")


# === PYDANTIC SCHEMAS (for API responses) ===

class ShowRead(SQLModel):
    """Read schema for WhatNot show."""
    id: int
    show_date: date
    show_name: Optional[str]
    platform: str
    total_gross_sales: Decimal
    total_discounts: Decimal
    total_whatnot_commission: Decimal
    total_whatnot_fees: Decimal
    total_payment_fees: Decimal
    total_shipping: Decimal
    total_net_earnings: Decimal
    total_net_profit: Decimal
    total_cogs: Decimal
    item_count: int
    unique_buyers: int
    avg_sale_price: Decimal
    excel_filename: Optional[str]
    imported_at: datetime


class ShowCreate(SQLModel):
    """Create schema for manual show entry."""
    show_date: date
    show_name: Optional[str] = None
    platform: str = "WhatNot"
    notes: Optional[str] = None


class ShowUpdate(SQLModel):
    """Update schema for show metadata."""
    show_name: Optional[str] = None
    notes: Optional[str] = None


class TransactionRead(SQLModel):
    """Read schema for transaction."""
    id: int
    show_id: Optional[int]  # Nullable for marketplace orders
    show_name: Optional[str] = None  # Show name (populated from related show)
    sale_type: str  # 'stream' or 'marketplace'
    transaction_date: datetime
    item_name: str
    quantity: int
    buyer_username: str
    payment_status: Optional[str]  # For marketplace orders
    total_revenue: Optional[Decimal]  # For marketplace orders
    gross_sale_price: Decimal
    net_earnings: Decimal
    notes: Optional[str]  # For marketplace orders
    cogs: Optional[Decimal]
    net_profit: Optional[Decimal]
    roi_percent: Optional[Decimal]
    matched_cogs_rule_id: Optional[int]
    owner: Optional[str]  # Owner assignment (Cihan, Nima, Askar, Kanto)


class TransactionUpdate(SQLModel):
    """Update schema for transaction."""
    cogs: Optional[Decimal] = None
    notes: Optional[str] = None


class ProductRead(SQLModel):
    """Read schema for product."""
    id: int
    product_name: str
    normalized_name: str
    total_quantity_sold: int
    total_gross_sales: Decimal
    total_net_earnings: Decimal
    avg_sale_price: Decimal
    times_sold: int
    default_cogs: Optional[Decimal]
    category: Optional[str]
    master_card_id: Optional[int]
    has_cogs: Optional[bool] = None


class ProductUpdate(SQLModel):
    """Update schema for product."""
    default_cogs: Optional[Decimal] = None
    category: Optional[str] = None


class BuyerRead(SQLModel):
    """Read schema for buyer."""
    id: int
    username: str
    display_name: Optional[str]
    total_purchases: int
    total_spent: Decimal
    avg_purchase_price: Decimal
    is_repeat_buyer: bool
    first_purchase_date: Optional[date]
    last_purchase_date: Optional[date]


class BuyerUpdate(SQLModel):
    """Update schema for buyer."""
    display_name: Optional[str] = None
    notes: Optional[str] = None


class COGSRuleRead(SQLModel):
    """Read schema for COGS mapping rule."""
    id: int
    rule_name: str
    keywords: List[str]
    cogs_amount: Decimal
    match_type: MatchType
    priority: int
    is_active: bool
    category: Optional[str]
    notes: Optional[str]
    created_at: datetime


class COGSRuleCreate(SQLModel):
    """Create schema for COGS mapping rule."""
    rule_name: str
    keywords: List[str]
    cogs_amount: Decimal
    match_type: MatchType = MatchType.CONTAINS
    priority: int = 50
    is_active: bool = True
    category: Optional[str] = None
    notes: Optional[str] = None


class COGSRuleUpdate(SQLModel):
    """Update schema for COGS mapping rule."""
    rule_name: Optional[str] = None
    keywords: Optional[List[str]] = None
    cogs_amount: Optional[Decimal] = None
    match_type: Optional[MatchType] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class ImportResult(SQLModel):
    """Result of Excel import operation."""
    show_id: int
    total_rows: int
    imported: int
    skipped: int
    errors: List[str]
    warnings: List[str]
    cogs_assigned_count: int
    cogs_missing_count: int


class ProductCatalogRead(SQLModel):
    """Read schema for product catalog item."""
    id: int
    name: str
    category: str
    image_url: str
    image_filename: str
    rule_type: CatalogRuleType
    include_keywords: List[str]
    exclude_keywords: List[str]
    priority: int
    keywords: List[str]  # DEPRECATED: Keep for backward compatibility
    sales_count: int
    total_revenue: Decimal
    created_at: datetime


class ProductCatalogCreate(SQLModel):
    """Create schema for adding product to catalog."""
    image_url: str  # User pastes full URL
    name: Optional[str] = None  # Optional: override auto-extracted name
    category: Optional[str] = None  # Optional: override auto-categorization (e.g., "Singles")


class ProductCatalogUpdate(SQLModel):
    """Update schema for product catalog item."""
    name: Optional[str] = None
    category: Optional[str] = None
    rule_type: Optional[CatalogRuleType] = None
    include_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    keywords: Optional[List[str]] = None  # DEPRECATED: Keep for backward compatibility


# === INVENTORY SCHEMAS ===

class InventoryRead(SQLModel):
    """Read schema for inventory item."""
    id: int
    catalog_item_id: Optional[int]
    item_name: str
    sku: Optional[str]
    category: Optional[str]
    image_url: Optional[str]
    quantity: int
    low_stock_threshold: int
    status: InventoryItemStatus
    cost_per_unit: Optional[Decimal]
    total_cost: Optional[Decimal]
    location: Optional[str]
    bin_number: Optional[str]
    supplier: Optional[str]
    last_restock_date: Optional[date]
    notes: Optional[str]
    owner: Optional[str]
    created_at: datetime
    updated_at: datetime
    # From catalog if linked
    catalog_name: Optional[str] = None
    catalog_image_url: Optional[str] = None
    catalog_category: Optional[str] = None


class InventoryCreate(SQLModel):
    """Create schema for inventory item."""
    catalog_item_id: Optional[int] = None
    item_name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    quantity: int = 0
    low_stock_threshold: int = 5
    cost_per_unit: Optional[Decimal] = None
    location: Optional[str] = None
    bin_number: Optional[str] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None
    owner: Optional[str] = None


class InventoryUpdate(SQLModel):
    """Update schema for inventory item."""
    catalog_item_id: Optional[int] = None
    item_name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    cost_per_unit: Optional[Decimal] = None
    location: Optional[str] = None
    bin_number: Optional[str] = None
    supplier: Optional[str] = None
    last_restock_date: Optional[date] = None
    notes: Optional[str] = None
    owner: Optional[str] = None


class InventoryAdjustment(SQLModel):
    """Schema for adjusting inventory quantity."""
    adjustment: int  # Positive to add, negative to remove
    reason: Optional[str] = None  # e.g., "Sold on stream", "Damaged", "Restock"
