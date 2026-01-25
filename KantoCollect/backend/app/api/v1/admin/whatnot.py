"""
WhatNot sales tracking endpoints.

All endpoints require admin authentication.
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import AdminUser
from app.core.whatnot_database import get_whatnot_db
from app.models.whatnot import (
    WhatnotShow,
    SalesTransaction,
    WhatnotProduct,
    WhatnotBuyer,
    COGSMappingRule,
    ProductCatalog,
    ShowRead,
    ShowCreate,
    ShowUpdate,
    TransactionRead,
    TransactionUpdate,
    ProductRead,
    ProductUpdate,
    BuyerRead,
    BuyerUpdate,
    COGSRuleRead,
    COGSRuleCreate,
    COGSRuleUpdate,
    ProductCatalogRead,
    ProductCatalogCreate,
    ProductCatalogUpdate,
    ImportResult,
)
from app.services.whatnot.import_service import import_excel_show
from app.services.whatnot.analytics_service import (
    get_dashboard_summary,
    get_top_products,
    get_top_buyers,
    get_show_details,
    get_products_needing_cogs,
)
from app.services.whatnot.cogs_service import (
    test_rule_against_products,
    get_cogs_coverage_stats,
    get_rule_performance,
    recalculate_transaction_cogs,
)

router = APIRouter()


# === HELPER FUNCTIONS ===

def _to_show_read(show: WhatnotShow) -> ShowRead:
    """Convert show model to read schema."""
    return ShowRead.model_validate(show)


def _to_transaction_read(transaction: SalesTransaction) -> TransactionRead:
    """Convert transaction model to read schema."""
    return TransactionRead.model_validate(transaction)


def _to_product_read(product: WhatnotProduct) -> ProductRead:
    """Convert product model to read schema."""
    return ProductRead.model_validate(product)


def _to_buyer_read(buyer: WhatnotBuyer) -> BuyerRead:
    """Convert buyer model to read schema."""
    return BuyerRead.model_validate(buyer)


def _to_cogs_rule_read(rule: COGSMappingRule) -> COGSRuleRead:
    """Convert COGS rule model to read schema."""
    return COGSRuleRead.model_validate(rule)


# === SHOW ENDPOINTS ===

@router.get("/shows", response_model=List[ShowRead])
async def list_shows(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ShowRead]:
    """List all WhatNot shows with optional search."""
    query = select(WhatnotShow).order_by(WhatnotShow.show_date.desc())

    if search:
        like = f"%{search}%"
        query = query.where(WhatnotShow.show_name.ilike(like))

    shows = db.exec(query.offset(offset).limit(limit)).all()
    return [_to_show_read(show) for show in shows]


@router.post("/shows", response_model=ShowRead, status_code=status.HTTP_201_CREATED)
async def create_show(
    payload: ShowCreate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ShowRead:
    """Create a show manually (without import)."""
    show = WhatnotShow(**payload.model_dump())
    db.add(show)
    db.commit()
    db.refresh(show)
    return _to_show_read(show)


@router.get("/shows/{show_id}", response_model=dict)
async def get_show_details_endpoint(
    show_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> dict:
    """Get detailed show information with transactions."""
    details = get_show_details(db, show_id)
    if not details:
        raise HTTPException(status_code=404, detail="Show not found")
    return details


@router.put("/shows/{show_id}", response_model=ShowRead)
async def update_show(
    show_id: int,
    payload: ShowUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ShowRead:
    """Update show metadata."""
    show = db.get(WhatnotShow, show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # Update fields
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(show, field, value)

    db.add(show)
    db.commit()
    db.refresh(show)
    return _to_show_read(show)


@router.delete("/shows/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_show(
    show_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> None:
    """Delete a show and all its transactions."""
    show = db.get(WhatnotShow, show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    # Cascade delete handled by database
    db.delete(show)
    db.commit()


# === IMPORT ENDPOINTS ===

@router.post("/import/excel", response_model=ImportResult)
async def import_excel_file(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
) -> ImportResult:
    """
    Import WhatNot sales from Excel file.

    Auto-detects show name and date from the Excel file structure:
    - Row 1: Show name (e.g., "💎💎 FREE PACKS...")
    - Row 2: Column headers
    - Row 3+: Transaction data (show date extracted from first transaction)

    Args:
        file: Excel file to import
        sheet_name: Optional sheet name (for multi-sheet files)
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")

    # Save uploaded file temporarily
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())

    # Import
    try:
        result = import_excel_show(db, str(temp_path), sheet_name=sheet_name)
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()

    return result


@router.post("/import/marketplace", response_model=ImportResult)
async def import_marketplace_file(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    file: UploadFile = File(...),
) -> ImportResult:
    """
    Import WhatNot Marketplace orders from Excel file.

    Expects a file with 'WhatNot Marketplace' sheet containing:
    - Date, Name of Product, Quantity, Buyer
    - Total Revenue, Payment Status, Discount
    - WhatNot Commission, WhatNot Fee, Payment Processing Fee
    - Net Earnings, COGS, Net Profit, ROI, Notes
    """
    from app.services.whatnot.import_service import import_marketplace_excel

    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")

    # Save uploaded file temporarily
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())

    # Import
    try:
        result = import_marketplace_excel(db, str(temp_path))
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()

    return result


# === TRANSACTION ENDPOINTS ===

@router.get("/transactions", response_model=List[TransactionRead])
async def list_transactions(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    show_id: Optional[int] = None,
    product_id: Optional[int] = None,
    buyer_id: Optional[int] = None,
    sale_type: Optional[str] = None,  # 'stream' or 'marketplace'
    has_cogs: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[TransactionRead]:
    """List transactions with optional filters. Filter by sale_type to get stream or marketplace orders."""
    query = select(SalesTransaction).order_by(SalesTransaction.transaction_date.desc())

    if show_id:
        query = query.where(SalesTransaction.show_id == show_id)
    if sale_type:
        query = query.where(SalesTransaction.sale_type == sale_type)
    if product_id:
        query = query.where(SalesTransaction.product_id == product_id)
    if buyer_id:
        query = query.where(SalesTransaction.buyer_id == buyer_id)
    if has_cogs is not None:
        if has_cogs:
            query = query.where(SalesTransaction.cogs.isnot(None))
        else:
            query = query.where(SalesTransaction.cogs.is_(None))

    transactions = db.exec(query.offset(offset).limit(limit)).all()
    return [_to_transaction_read(t) for t in transactions]


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> TransactionRead:
    """Get a single transaction."""
    transaction = db.get(SalesTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _to_transaction_read(transaction)


@router.put("/transactions/{transaction_id}", response_model=TransactionRead)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> TransactionRead:
    """Update transaction COGS manually (admin override)."""
    transaction = db.get(SalesTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update COGS if provided (total COGS, not per-unit)
    if payload.cogs is not None:
        transaction.cogs = payload.cogs
        transaction.matched_cogs_rule_id = None  # Clear rule since this is manual

        # Recalculate net profit and ROI
        transaction.net_profit = transaction.net_earnings - payload.cogs

        # Calculate ROI percentage
        if payload.cogs > 0:
            transaction.roi_percent = (transaction.net_profit / payload.cogs) * Decimal("100")
        else:
            transaction.roi_percent = None

    # Update notes if provided
    if payload.notes is not None:
        transaction.notes = payload.notes

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return _to_transaction_read(transaction)


@router.post("/transactions/{transaction_id}/recalculate-cogs", response_model=TransactionRead)
async def recalculate_cogs(
    transaction_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> TransactionRead:
    """Re-run COGS matching for a transaction."""
    transaction = db.get(SalesTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Recalculate
    recalculate_transaction_cogs(db, transaction)
    db.commit()
    db.refresh(transaction)
    return _to_transaction_read(transaction)


# === PRODUCT ENDPOINTS ===

@router.get("/products", response_model=List[ProductRead])
async def list_products(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    search: Optional[str] = None,
    has_cogs: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ProductRead]:
    """List products with optional filters."""
    query = select(WhatnotProduct).order_by(WhatnotProduct.total_gross_sales.desc())

    if search:
        like = f"%{search}%"
        query = query.where(WhatnotProduct.product_name.ilike(like))

    products = db.exec(query.offset(offset).limit(limit)).all()

    # Filter by COGS if requested
    if has_cogs is not None:
        filtered = []
        for product in products:
            # Check if product has any transactions with COGS
            transactions = db.exec(
                select(SalesTransaction)
                .where(SalesTransaction.product_id == product.id)
                .limit(1)
            ).all()

            has_any_cogs = any(t.cogs is not None for t in transactions)

            if has_cogs and has_any_cogs:
                filtered.append(product)
            elif not has_cogs and not has_any_cogs:
                filtered.append(product)

        products = filtered

    return [_to_product_read(p) for p in products]


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ProductRead:
    """Get product details."""
    product = db.get(WhatnotProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_product_read(product)


@router.put("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ProductRead:
    """Update product metadata."""
    product = db.get(WhatnotProduct, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_product_read(product)


# === BUYER ENDPOINTS ===

@router.get("/buyers", response_model=List[BuyerRead])
async def list_buyers(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    search: Optional[str] = None,
    repeat_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> List[BuyerRead]:
    """List buyers with optional filters."""
    query = select(WhatnotBuyer).order_by(WhatnotBuyer.total_spent.desc())

    if search:
        like = f"%{search}%"
        query = query.where(WhatnotBuyer.username.ilike(like))

    if repeat_only:
        query = query.where(WhatnotBuyer.is_repeat_buyer == True)

    buyers = db.exec(query.offset(offset).limit(limit)).all()
    return [_to_buyer_read(b) for b in buyers]


@router.get("/buyers/{buyer_id}", response_model=BuyerRead)
async def get_buyer(
    buyer_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> BuyerRead:
    """Get buyer details."""
    buyer = db.get(WhatnotBuyer, buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return _to_buyer_read(buyer)


@router.put("/buyers/{buyer_id}", response_model=BuyerRead)
async def update_buyer(
    buyer_id: int,
    payload: BuyerUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> BuyerRead:
    """Update buyer notes."""
    buyer = db.get(WhatnotBuyer, buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(buyer, field, value)

    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return _to_buyer_read(buyer)


# === COGS RULE ENDPOINTS ⭐ CRITICAL ===

@router.get("/cogs-rules", response_model=List[COGSRuleRead])
async def list_cogs_rules(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    active_only: bool = False,
) -> List[COGSRuleRead]:
    """List all COGS mapping rules ordered by priority."""
    query = select(COGSMappingRule).order_by(COGSMappingRule.priority.desc())

    if active_only:
        query = query.where(COGSMappingRule.is_active == True)

    rules = db.exec(query).all()
    return [_to_cogs_rule_read(r) for r in rules]


@router.post("/cogs-rules", response_model=COGSRuleRead, status_code=status.HTTP_201_CREATED)
async def create_cogs_rule(
    payload: COGSRuleCreate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> COGSRuleRead:
    """Create a new COGS mapping rule."""
    rule = COGSMappingRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _to_cogs_rule_read(rule)


@router.get("/cogs-rules/{rule_id}", response_model=COGSRuleRead)
async def get_cogs_rule(
    rule_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> COGSRuleRead:
    """Get COGS rule details."""
    rule = db.get(COGSMappingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="COGS rule not found")
    return _to_cogs_rule_read(rule)


@router.put("/cogs-rules/{rule_id}", response_model=COGSRuleRead)
async def update_cogs_rule(
    rule_id: int,
    payload: COGSRuleUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> COGSRuleRead:
    """Update COGS rule."""
    rule = db.get(COGSMappingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="COGS rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _to_cogs_rule_read(rule)


@router.delete("/cogs-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cogs_rule(
    rule_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> None:
    """Delete COGS rule."""
    rule = db.get(COGSMappingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="COGS rule not found")

    db.delete(rule)
    db.commit()


@router.post("/cogs-rules/{rule_id}/toggle", response_model=COGSRuleRead)
async def toggle_cogs_rule(
    rule_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> COGSRuleRead:
    """Enable/disable COGS rule without deleting."""
    rule = db.get(COGSMappingRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="COGS rule not found")

    rule.is_active = not rule.is_active
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _to_cogs_rule_read(rule)


@router.post("/cogs-rules/test")
async def test_cogs_rule(
    payload: COGSRuleCreate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> dict:
    """Test a COGS rule against existing products without saving."""
    # Create temporary rule (not saved)
    temp_rule = COGSMappingRule(**payload.model_dump())

    # Test against products
    matched_names = test_rule_against_products(db, temp_rule, limit=20)

    return {
        'matches': matched_names,
        'match_count': len(matched_names)
    }


# === ANALYTICS ENDPOINTS ===

@router.get("/analytics/overview")
async def get_analytics_overview(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    date_range: Optional[str] = None,
) -> dict:
    """Get dashboard summary statistics."""
    summary = get_dashboard_summary(db, date_range)
    cogs_stats = get_cogs_coverage_stats(db)

    return {
        **summary,
        'cogs_coverage': cogs_stats
    }


@router.get("/analytics/top-products")
async def get_analytics_top_products(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    limit: int = 10,
    metric: str = 'revenue',
    date_range: Optional[str] = None,
) -> List[dict]:
    """Get top performing products."""
    return get_top_products(db, limit, metric, date_range)


@router.get("/analytics/top-buyers")
async def get_analytics_top_buyers(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    limit: int = 10,
    date_range: Optional[str] = None,
) -> List[dict]:
    """Get top customers."""
    return get_top_buyers(db, limit, date_range)


@router.get("/analytics/products-needing-cogs")
async def get_analytics_products_needing_cogs(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    limit: int = 50,
) -> List[dict]:
    """Get products without COGS assigned."""
    return get_products_needing_cogs(db, limit)


@router.get("/product-catalog")
async def get_product_catalog(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> dict:
    """Get product catalog from database."""
    # Get all catalog items from database
    catalog_items = db.exec(select(ProductCatalog)).all()

    # Get all transactions for matching
    transactions = db.exec(select(SalesTransaction)).all()

    # Build response
    products = []
    for item in catalog_items:
        # Count sales that match keywords
        sales = 0
        revenue = 0.0

        for t in transactions:
            item_name_lower = t.item_name.lower()
            for keyword in item.keywords:
                if keyword.lower() in item_name_lower:
                    sales += 1
                    revenue += float(t.gross_sale_price)
                    break

        products.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "imageUrl": item.image_url,
            "keywords": item.keywords,
            "sales": sales,
            "revenue": round(revenue, 2),
            "cogs": None  # For backward compatibility
        })

    return {
        "products": products,
        "totalProducts": len(products)
    }


@router.post("/product-catalog/save-cogs")
async def save_product_cogs(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    product_id: int = Body(...),
    cogs: float = Body(...),
    keywords: List[str] = Body(...),
    product_name: str = Body(...),
) -> dict:
    """Save product COGS and create keyword rule."""
    from decimal import Decimal
    from app.models.whatnot import COGSMappingRule, MatchType

    # Create or update COGS mapping rule
    rule_name = f"{product_name} - Auto-generated"

    existing_rule = db.exec(
        select(COGSMappingRule).where(COGSMappingRule.rule_name == rule_name)
    ).first()

    if existing_rule:
        # Update existing rule
        existing_rule.keywords = keywords
        existing_rule.cogs_amount = Decimal(str(cogs))
        existing_rule.is_active = True
        db.add(existing_rule)
    else:
        # Create new rule
        rule = COGSMappingRule(
            rule_name=rule_name,
            keywords=keywords,
            cogs_amount=Decimal(str(cogs)),
            match_type=MatchType.CONTAINS,
            priority=50,
            is_active=True,
            category=product_name,
            notes=f"Auto-generated from product catalog"
        )
        db.add(rule)

    db.commit()

    return {
        "success": True,
        "message": f"COGS rule created for {product_name}"
    }


@router.post("/product-catalog/add")
async def add_catalog_item(
    payload: ProductCatalogCreate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ProductCatalogRead:
    """Add new item to product catalog from image URL."""
    import re
    from urllib.parse import unquote

    # Extract filename from URL
    # Example: https://ik.imagekit.io/homecraft/Item%20Pics/Mega%20Battle%20Deck%20(Mega%20Diancie%20ex).jpg?updatedAt=1768894216143
    url = payload.image_url

    # Remove query params
    url_clean = url.split('?')[0]

    # Check if this URL already exists (ignoring query params)
    existing_by_url = db.exec(
        select(ProductCatalog).where(ProductCatalog.image_url.like(f"{url_clean}%"))
    ).first()

    if existing_by_url:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate item: This image URL is already in the Master Catalog as '{existing_by_url.name}' (ID: {existing_by_url.id})"
        )

    # Get filename (last part after /)
    filename_encoded = url_clean.split('/')[-1]
    filename = unquote(filename_encoded)

    # Extract product name (remove extension)
    product_name = filename.rsplit('.', 1)[0]
    product_name = product_name.replace('_s', "'s")  # Fix apostrophes
    product_name = product_name.replace('_', ' ')    # Replace underscores

    # Check if this product name already exists
    existing_by_name = db.exec(
        select(ProductCatalog).where(ProductCatalog.name == product_name)
    ).first()

    if existing_by_name:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate item: A product named '{product_name}' already exists in the Master Catalog (ID: {existing_by_name.id})"
        )

    # Auto-categorize
    name_lower = product_name.lower()
    if 'ultra premium' in name_lower or 'upc' in name_lower:
        category = 'UPC'
    elif 'elite trainer box' in name_lower or 'etb' in name_lower:
        category = 'ETB'
    elif 'booster bundle' in name_lower:
        category = 'Booster Bundle'
    elif 'booster box' in name_lower:
        category = 'Booster Box'
    elif 'battle deck' in name_lower:
        category = 'Battle Deck'
    elif 'premium collection' in name_lower or 'premium figure' in name_lower:
        category = 'Premium Collection'
    elif 'blister' in name_lower:
        category = '3 Pack Blister'
    elif 'tin' in name_lower:
        category = 'Tin'
    elif 'sleeved' in name_lower or ('sleeve' in name_lower and 'pack' in name_lower):
        category = 'Sleeved Packs'
    elif '(' in product_name and ')' in product_name:
        category = 'Singles'
    elif 'box' in name_lower:
        category = 'Box'
    else:
        category = 'Other'

    # Auto-generate keywords
    keywords = [name_lower]

    # Extract card numbers
    card_numbers = re.findall(r'op[-\s]?\d{1,2}[-\s]?\d{3}', name_lower)
    for num in card_numbers:
        keywords.append(num)
        keywords.append(num.replace('-', ''))
        keywords.append(num.replace('-', ' '))

    # Add important words
    important_words = ['mega', 'ex', 'premium', 'elite', 'booster', 'parallel', 'battle deck']
    for word in important_words:
        if word in name_lower:
            keywords.append(word)

    # Add product type keywords
    if category == 'ETB':
        keywords.extend(['elite trainer box', 'etb'])
    elif category == 'Booster Bundle':
        keywords.append('booster bundle')
    elif category == 'UPC':
        keywords.extend(['ultra premium', 'upc'])
    elif category == 'Battle Deck':
        keywords.append('battle deck')

    # Remove duplicates
    keywords = list(set([k.strip() for k in keywords if k.strip()]))

    # Create catalog item
    catalog_item = ProductCatalog(
        name=product_name,
        category=category,
        image_url=url,
        image_filename=filename,
        keywords=keywords,
        sales_count=0,
        total_revenue=Decimal("0"),
        created_by=current_user.id
    )

    db.add(catalog_item)
    db.commit()
    db.refresh(catalog_item)

    return ProductCatalogRead.model_validate(catalog_item)


@router.delete("/product-catalog/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_item(
    item_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> None:
    """Delete item from product catalog."""
    item = db.get(ProductCatalog, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    db.delete(item)
    db.commit()


@router.get("/analytics/cogs-rule-performance")
async def get_analytics_rule_performance(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> List[dict]:
    """Get COGS rule performance statistics."""
    return get_rule_performance(db)
