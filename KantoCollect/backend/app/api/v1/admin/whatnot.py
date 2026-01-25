"""
WhatNot sales tracking endpoints.

All endpoints require admin authentication.
"""

from decimal import Decimal
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select, or_

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
    query = select(SalesTransaction).where(
        or_(
            SalesTransaction.show_id != None,
            SalesTransaction.sale_type == 'marketplace'
        )
    ).order_by(SalesTransaction.transaction_date.desc())

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

@router.get("/products")
async def list_products(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
    search: Optional[str] = None,
    has_cogs: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List products with optional filters and pagination metadata."""

    # When filtering by COGS, we need to check ALL products first, then paginate
    # Otherwise low-revenue items with missing COGS won't show up in top 50
    if has_cogs is not None:
        # Get ALL products (or with search filter)
        query = select(WhatnotProduct).order_by(WhatnotProduct.total_gross_sales.desc())

        if search:
            like = f"%{search}%"
            query = query.where(WhatnotProduct.product_name.ilike(like))

        all_products = db.exec(query).all()

        # Filter by COGS status
        filtered = []
        for product in all_products:
            # Get ALL transactions for this product
            transactions = db.exec(
                select(SalesTransaction)
                .where(SalesTransaction.product_id == product.id)
                .where(
                    or_(
                        SalesTransaction.show_id != None,
                        SalesTransaction.sale_type == 'marketplace'
                    )
                )
            ).all()

            if not transactions:
                continue  # Skip products with no transactions

            # Check COGS status
            # has_cogs=True: ALL transactions must have COGS > 0 (positive values only)
            # has_cogs=False: ANY transaction missing COGS (NULL or $0.00)
            all_have_cogs = all(t.cogs is not None and t.cogs > 0 for t in transactions)
            any_missing_cogs = any(t.cogs is None or t.cogs == 0 for t in transactions)

            if has_cogs and all_have_cogs:
                filtered.append(product)
            elif not has_cogs and any_missing_cogs:
                filtered.append(product)

        # Store total count before pagination
        total_count = len(filtered)

        # Now apply pagination to filtered results
        products = filtered[offset:offset + limit]
    else:
        # No COGS filter - use normal pagination
        from sqlmodel import func

        query = select(WhatnotProduct).order_by(WhatnotProduct.total_gross_sales.desc())

        if search:
            like = f"%{search}%"
            query = query.where(WhatnotProduct.product_name.ilike(like))

        # Get total count
        count_query = select(func.count(WhatnotProduct.id))
        if search:
            like = f"%{search}%"
            count_query = count_query.where(WhatnotProduct.product_name.ilike(like))
        total_count = db.exec(count_query).one()

        products = db.exec(query.offset(offset).limit(limit)).all()

    # Add has_cogs field to each product by checking transactions
    result = []
    for p in products:
        product_dict = _to_product_read(p).model_dump()

        # Check if this product's transactions have COGS
        transactions = db.exec(
            select(SalesTransaction)
            .where(SalesTransaction.product_id == p.id)
            .where(
                or_(
                    SalesTransaction.show_id != None,
                    SalesTransaction.sale_type == 'marketplace'
                )
            )
        ).all()

        # Add has_cogs field - True if ALL transactions have COGS > 0 (positive values only, not NULL or $0.00)
        product_dict['has_cogs'] = all(t.cogs is not None and t.cogs > 0 for t in transactions) if transactions else False
        result.append(product_dict)

    return {
        "products": result,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


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
    """Get product catalog from database with rule-based matching."""
    from app.models.whatnot import CatalogRuleType

    # Get all catalog items from database (ordered by priority DESC)
    catalog_items = db.exec(
        select(ProductCatalog).order_by(ProductCatalog.priority.desc())
    ).all()

    # Get all transactions for matching (exclude test transactions: NULL show_id AND not marketplace)
    transactions = db.exec(
        select(SalesTransaction).where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
    ).all()

    # NEW RULE-BASED MATCHING LOGIC
    # Simple, universal matching that doesn't require constant patching
    transaction_matches = {}  # transaction_id -> catalog_item_id
    catch_all_item = None

    # Find the CATCH_ALL item (for "Unmapped Items")
    for catalog_item in catalog_items:
        if catalog_item.rule_type == CatalogRuleType.CATCH_ALL:
            catch_all_item = catalog_item
            break

    # Match each transaction
    for t in transactions:
        item_name_lower = t.item_name.lower()
        matched = False

        # Try to match against catalog items (ordered by priority)
        for catalog_item in catalog_items:
            # Skip CATCH_ALL items in this pass
            if catalog_item.rule_type == CatalogRuleType.CATCH_ALL:
                continue

            match = False

            if catalog_item.rule_type == CatalogRuleType.INCLUDE_ALL:
                # Must contain ALL include keywords
                match = all(
                    kw.lower() in item_name_lower
                    for kw in catalog_item.include_keywords
                )

            elif catalog_item.rule_type == CatalogRuleType.INCLUDE_ANY:
                # Must contain AT LEAST ONE include keyword
                match = any(
                    kw.lower() in item_name_lower
                    for kw in catalog_item.include_keywords
                )

            elif catalog_item.rule_type == CatalogRuleType.INCLUDE_AND_EXCLUDE:
                # Must have include keywords but NOT exclude keywords
                has_include = any(
                    kw.lower() in item_name_lower
                    for kw in catalog_item.include_keywords
                )
                has_exclude = any(
                    kw.lower() in item_name_lower
                    for kw in catalog_item.exclude_keywords
                )
                match = has_include and not has_exclude

            # If matched, assign to this catalog item and stop checking
            if match:
                transaction_matches[t.id] = catalog_item.id
                matched = True
                break

        # If no match found and we have a CATCH_ALL item, assign to it
        if not matched and catch_all_item:
            transaction_matches[t.id] = catch_all_item.id

    # Count matches for each catalog item
    products = []
    for item in catalog_items:
        sales = 0
        revenue = 0.0

        for t in transactions:
            # Check if this transaction matched this catalog item
            if transaction_matches.get(t.id) == item.id:
                sales += 1
                revenue += float(t.gross_sale_price)

        products.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "imageUrl": item.image_url,
            "ruleType": item.rule_type,
            "includeKeywords": item.include_keywords,
            "excludeKeywords": item.exclude_keywords,
            "priority": item.priority,
            "keywords": item.keywords,  # DEPRECATED: Keep for backward compatibility
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
    """Save product COGS and create keyword rule, then apply to all matching transactions."""
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
        rule_id = existing_rule.id
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
        db.flush()  # Get the rule ID
        rule_id = rule.id

    # Apply COGS to all matching transactions (exclude test transactions: NULL show_id AND not marketplace)
    all_transactions = db.exec(
        select(SalesTransaction).where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
    ).all()
    cogs_decimal = Decimal(str(cogs))
    matched_count = 0
    affected_show_ids = set()

    for t in all_transactions:
        item_name_lower = t.item_name.lower()
        for keyword in keywords:
            if keyword.lower() in item_name_lower:
                # Calculate COGS (cogs per item * quantity)
                t.cogs = cogs_decimal * t.quantity
                t.matched_cogs_rule_id = rule_id

                # Calculate profit and ROI
                if t.net_earnings:
                    t.net_profit = t.net_earnings - t.cogs
                    if t.cogs > 0:
                        t.roi_percent = (t.net_profit / t.cogs) * 100

                db.add(t)
                matched_count += 1

                # Track which shows need totals recalculated
                if t.show_id:
                    affected_show_ids.add(t.show_id)
                break

    # Recalculate show totals for affected shows
    for show_id in affected_show_ids:
        show = db.get(WhatnotShow, show_id)
        if show:
            # Get all transactions for this show
            show_transactions = db.exec(
                select(SalesTransaction).where(SalesTransaction.show_id == show_id)
            ).all()

            # Recalculate totals
            show.total_cogs = sum(t.cogs or Decimal("0") for t in show_transactions)
            show.total_net_profit = sum(t.net_profit or Decimal("0") for t in show_transactions)
            db.add(show)

    db.commit()

    return {
        "success": True,
        "message": f"COGS rule created for {product_name}. Applied to {matched_count} transactions."
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
    # Get all items and check URLs in Python to avoid LIKE wildcard issues with %20 in URLs
    all_items = db.exec(select(ProductCatalog)).all()
    existing_by_url = None
    for item in all_items:
        item_url_clean = item.image_url.split('?')[0]
        if item_url_clean == url_clean:
            existing_by_url = item
            break

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


@router.patch("/product-catalog/{item_id}")
async def update_catalog_item(
    item_id: int,
    payload: ProductCatalogUpdate,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> ProductCatalogRead:
    """Update catalog item (keywords, name, category, etc.)."""
    item = db.get(ProductCatalog, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    # Update fields that are provided
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.add(item)
    db.commit()
    db.refresh(item)

    return ProductCatalogRead.model_validate(item)


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


@router.post("/product-catalog/{catalog_id}/mark-mapped")
async def mark_catalog_item_mapped(
    catalog_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> dict:
    """
    Mark all transactions matching this catalog item as 'mapped'.
    Call this after user reviews and confirms the keyword matches are correct.
    """
    from datetime import datetime

    # Get catalog item
    catalog_item = db.get(ProductCatalog, catalog_id)
    if not catalog_item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    # Find all transactions that match this catalog item's keywords (exclude test transactions: NULL show_id AND not marketplace)
    all_transactions = db.exec(
        select(SalesTransaction).where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
    ).all()

    mapped_count = 0
    for t in all_transactions:
        # Skip if already mapped to another catalog item
        if t.is_mapped and t.catalog_item_id != catalog_id:
            continue

        item_name_lower = t.item_name.lower()
        matched = False
        matched_kw = None

        for keyword in catalog_item.keywords:
            if keyword.lower() in item_name_lower:
                # Mark as mapped
                t.catalog_item_id = catalog_id
                t.is_mapped = True
                t.matched_keyword = keyword
                t.mapped_at = datetime.utcnow()
                db.add(t)
                matched_count += 1
                matched = True
                break

    db.commit()

    return {
        "success": True,
        "catalog_item": catalog_item.name,
        "transactions_mapped": mapped_count
    }


@router.get("/analytics/mapping-status")
async def get_mapping_status(
    current_user: AdminUser,
    db: Session = Depends(get_whatnot_db),
) -> dict:
    """Get overview of mapped vs unmapped transactions."""
    from sqlmodel import func

    # Total transactions (exclude test transactions: NULL show_id AND not marketplace)
    total = db.exec(
        select(func.count(SalesTransaction.id))
        .where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
    ).one()

    # Mapped transactions
    mapped = db.exec(
        select(func.count(SalesTransaction.id))
        .where(SalesTransaction.is_mapped == True)
        .where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
    ).one()

    # Unmapped transactions
    unmapped = total - mapped

    # Get unmapped transaction samples (first 10)
    unmapped_samples = db.exec(
        select(SalesTransaction)
        .where(SalesTransaction.is_mapped == False)
        .where(
            or_(
                SalesTransaction.show_id != None,
                SalesTransaction.sale_type == 'marketplace'
            )
        )
        .limit(10)
    ).all()

    return {
        "total_transactions": total,
        "mapped": mapped,
        "unmapped": unmapped,
        "mapping_percentage": round((mapped / total * 100), 2) if total > 0 else 0,
        "unmapped_samples": [
            {
                "id": t.id,
                "item_name": t.item_name,
                "show_id": t.show_id,
                "price": float(t.gross_sale_price)
            }
            for t in unmapped_samples
        ]
    }
