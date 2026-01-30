"""
Excel import service for WhatNot sales data.

Handles parsing Excel files, normalizing data, auto-assigning COGS via keyword rules,
and computing aggregates.
"""

import re
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
import pandas as pd
from sqlmodel import Session, select

from app.models.whatnot import (
    WhatnotShow,
    SalesTransaction,
    WhatnotProduct,
    WhatnotBuyer,
    ImportResult,
)
from .cogs_service import (
    normalize_product_name,
    match_cogs_rule,
    apply_cogs_to_transaction,
)


# Excel column mapping
REQUIRED_COLUMNS = [
    'Date', 'Item Name', 'Quantity', 'Buyer',
    'Gross Sale Price', 'Net Earnings'
]

OPTIONAL_COLUMNS = [
    'SKU', 'Discount', 'WhatNot Commission',
    'WhatNot Fee', 'Payment Processing Fee',
    'Shipping', 'COGS', 'Net Profit', 'ROI'
]


def validate_excel_structure(df: pd.DataFrame) -> List[str]:
    """
    Validate that Excel file has all required columns.

    Args:
        df: Pandas DataFrame from Excel

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check for required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")

    return errors


def parse_decimal(value) -> Decimal:
    """
    Safely parse a value to Decimal.

    Args:
        value: Value from Excel cell

    Returns:
        Decimal value or 0 if invalid
    """
    if pd.isna(value):
        return Decimal("0")
    try:
        return Decimal(str(value).replace('$', '').replace(',', '').strip())
    except:
        return Decimal("0")


def parse_date(value) -> datetime:
    """
    Safely parse a date value.

    Args:
        value: Date value from Excel

    Returns:
        datetime object

    Raises:
        ValueError: If date cannot be parsed
    """
    if pd.isna(value):
        raise ValueError("Date is empty")

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    # Try to parse string
    try:
        return pd.to_datetime(value)
    except:
        raise ValueError(f"Invalid date format: {value}")


def get_or_create_product(
    session: Session,
    item_name: str
) -> WhatnotProduct:
    """
    Find existing product by normalized name or create new one.

    Args:
        session: Database session
        item_name: Raw product name from Excel

    Returns:
        WhatnotProduct instance
    """
    normalized = normalize_product_name(item_name)

    # Try to find existing
    existing = session.exec(
        select(WhatnotProduct)
        .where(WhatnotProduct.normalized_name == normalized)
    ).first()

    if existing:
        return existing

    # Create new product
    product = WhatnotProduct(
        product_name=item_name.strip(),
        normalized_name=normalized
    )
    session.add(product)
    session.flush()  # Get ID without committing
    return product


def get_or_create_buyer(
    session: Session,
    username: str
) -> WhatnotBuyer:
    """
    Find existing buyer by username or create new one.

    Args:
        session: Database session
        username: Buyer username from Excel

    Returns:
        WhatnotBuyer instance
    """
    username_clean = username.strip()

    # Try to find existing
    existing = session.exec(
        select(WhatnotBuyer)
        .where(WhatnotBuyer.username == username_clean)
    ).first()

    if existing:
        return existing

    # Create new buyer
    buyer = WhatnotBuyer(username=username_clean)
    session.add(buyer)
    session.flush()  # Get ID without committing
    return buyer


def import_excel_show(
    session: Session,
    file_path: str,
    sheet_name: Optional[str] = None
) -> ImportResult:
    """
    Import an Excel file as a WhatNot show.

    Auto-detects show name and date from the Excel file:
    - Row 0: Month title (optional)
    - Row 1: Show name (e.g., "💎💎 FREE PACKS...")
    - Row 2: Column headers
    - Row 3+: Transaction data

    Show date is extracted from the first transaction.

    Workflow:
    1. Parse and auto-detect show name/date from Excel
    2. Create show record
    3. For each row:
       - Create/get product and buyer
       - Auto-assign COGS using keyword rules
       - Create transaction
    4. Compute aggregates
    5. Update product/buyer stats

    Args:
        session: Database session
        file_path: Path to Excel file
        sheet_name: Optional sheet name (for multi-sheet files)

    Returns:
        ImportResult with statistics and any errors

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file structure is invalid
    """
    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Parse Excel - read first row to get show name
    try:
        df_header = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=2)
        # Row 1 contains the show name (row 0 is month title)
        show_name = str(df_header.iloc[1, 0]) if len(df_header) > 1 else "Imported Show"

        # Read actual data with header on row 2
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=2)

        # Clean column names (remove trailing spaces)
        df.columns = df.columns.str.strip()

    except Exception as e:
        raise ValueError(f"Invalid Excel file: {str(e)}")

    # Validate structure
    validation_errors = validate_excel_structure(df)
    if validation_errors:
        return ImportResult(
            show_id=0,
            total_rows=0,
            imported=0,
            skipped=0,
            errors=validation_errors,
            warnings=[],
            cogs_assigned_count=0,
            cogs_missing_count=0
        )

    # Extract show date from first transaction
    try:
        first_date = parse_date(df['Date'].iloc[0])
        show_date = first_date.date()
    except Exception as e:
        return ImportResult(
            show_id=0,
            total_rows=len(df),
            imported=0,
            skipped=len(df),
            errors=[f"Could not extract show date from first transaction: {str(e)}"],
            warnings=[],
            cogs_assigned_count=0,
            cogs_missing_count=0
        )

    # Create show record
    show = WhatnotShow(
        show_date=show_date,
        show_name=show_name,
        platform="WhatNot",
        excel_filename=path.name
    )
    session.add(show)
    session.flush()  # Get show ID

    # Track import progress
    errors = []
    warnings = []
    imported_count = 0
    skipped_count = 0
    cogs_assigned_count = 0
    cogs_missing_count = 0
    products_created = set()
    buyers_created = set()

    # Process each row
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (header is 1)

        try:
            # Skip empty rows - check critical fields first
            if pd.isna(row.get('Item Name')) or str(row.get('Item Name')).strip() == '':
                skipped_count += 1
                continue

            if pd.isna(row.get('Date')):
                skipped_count += 1
                warnings.append(f"Row {row_num}: Skipped - no date")
                continue

            if pd.isna(row.get('Buyer')) or str(row.get('Buyer')).strip() == '':
                skipped_count += 1
                warnings.append(f"Row {row_num}: Skipped - no buyer")
                continue

            # Parse required fields with safe handling
            transaction_date = parse_date(row['Date'])
            item_name = str(row['Item Name']).strip()

            # Quantity - default to 1 if empty
            if pd.isna(row.get('Quantity')):
                quantity = 1
            else:
                try:
                    quantity = int(row['Quantity'])
                except:
                    quantity = 1

            buyer_username = str(row['Buyer']).strip()
            gross_sale_price = parse_decimal(row.get('Gross Sale Price', 0))
            net_earnings = parse_decimal(row.get('Net Earnings', 0))

            # Parse optional fields - handle all as nullable
            sku = str(row.get('SKU', '')).strip() if not pd.isna(row.get('SKU')) else None
            discount = parse_decimal(row.get('Discount', 0))
            whatnot_commission = parse_decimal(row.get('WhatNot Commission', 0))
            whatnot_fee = parse_decimal(row.get('WhatNot Fee', 0))
            payment_fee = parse_decimal(row.get('Payment Processing Fee', 0))
            shipping = parse_decimal(row.get('Shipping', 0))

            # Get or create product
            product = get_or_create_product(session, item_name)
            if product.id not in products_created:
                products_created.add(product.id)

            # Get or create buyer
            buyer = get_or_create_buyer(session, buyer_username)
            if buyer.id not in buyers_created:
                buyers_created.add(buyer.id)

            # Create transaction
            transaction = SalesTransaction(
                show_id=show.id,
                transaction_date=transaction_date,
                sku=sku,
                item_name=item_name,
                quantity=quantity,
                buyer_username=buyer_username,
                gross_sale_price=gross_sale_price,
                discount=discount,
                whatnot_commission=whatnot_commission,
                whatnot_fee=whatnot_fee,
                payment_processing_fee=payment_fee,
                shipping=shipping,
                net_earnings=net_earnings,
                product_id=product.id,
                buyer_id=buyer.id,
                row_number=row_num
            )

            # ⭐ AUTO-ASSIGN COGS using keyword rules
            normalized_name = normalize_product_name(item_name)
            rule_id, cogs_amount = match_cogs_rule(session, normalized_name)

            if cogs_amount is not None:
                # Apply COGS and calculate profit/ROI
                apply_cogs_to_transaction(transaction, cogs_amount, rule_id)
                cogs_assigned_count += 1
            else:
                # No COGS rule matched
                cogs_missing_count += 1
                warnings.append(f"Row {row_num}: No COGS rule matched for '{item_name}'")

            session.add(transaction)
            imported_count += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            continue

    # Commit all transactions
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        return ImportResult(
            show_id=show.id,
            total_rows=len(df),
            imported=0,
            skipped=len(df),
            errors=[f"Database error: {str(e)}"],
            warnings=[],
            cogs_assigned_count=0,
            cogs_missing_count=0
        )

    # Compute aggregates
    compute_show_aggregates(session, show.id)
    update_product_aggregates(session, list(products_created))
    update_buyer_aggregates(session, list(buyers_created))

    # Commit aggregates
    session.commit()

    return ImportResult(
        show_id=show.id,
        total_rows=len(df),
        imported=imported_count,
        skipped=len(df) - imported_count,
        errors=errors,
        warnings=warnings[:50],  # Limit warnings to first 50
        cogs_assigned_count=cogs_assigned_count,
        cogs_missing_count=cogs_missing_count
    )


def compute_show_aggregates(session: Session, show_id: int) -> None:
    """
    Calculate and update show-level aggregates.

    Args:
        session: Database session
        show_id: Show to update
    """
    show = session.get(WhatnotShow, show_id)
    if not show:
        return

    # Get all transactions for this show
    transactions = session.exec(
        select(SalesTransaction)
        .where(SalesTransaction.show_id == show_id)
    ).all()

    if not transactions:
        return

    # Calculate totals
    show.total_gross_sales = sum(t.gross_sale_price for t in transactions)
    show.total_discounts = sum(t.discount for t in transactions)
    show.total_whatnot_commission = sum(t.whatnot_commission for t in transactions)
    show.total_whatnot_fees = sum(t.whatnot_fee for t in transactions)
    show.total_payment_fees = sum(t.payment_processing_fee for t in transactions)
    show.total_shipping = sum(t.shipping for t in transactions)
    show.total_net_earnings = sum(t.net_earnings for t in transactions)

    # COGS and profit (only for transactions with COGS)
    show.total_cogs = sum(t.cogs for t in transactions if t.cogs is not None) or Decimal("0")
    show.total_net_profit = sum(t.net_profit for t in transactions if t.net_profit is not None) or Decimal("0")

    # Item count and averages
    show.item_count = len(transactions)
    show.avg_sale_price = show.total_gross_sales / len(transactions) if transactions else Decimal("0")

    # Unique buyers
    show.unique_buyers = len(set(t.buyer_id for t in transactions if t.buyer_id))

    show.updated_at = datetime.utcnow()
    session.add(show)


def update_product_aggregates(session: Session, product_ids: List[int]) -> None:
    """
    Update aggregate statistics for products.

    Args:
        session: Database session
        product_ids: List of product IDs to update
    """
    for product_id in product_ids:
        product = session.get(WhatnotProduct, product_id)
        if not product:
            continue

        # Get all transactions for this product
        transactions = session.exec(
            select(SalesTransaction)
            .where(SalesTransaction.product_id == product_id)
        ).all()

        if not transactions:
            continue

        # Update aggregates
        product.total_quantity_sold = sum(t.quantity for t in transactions)
        product.total_gross_sales = sum(t.gross_sale_price for t in transactions)
        product.total_net_earnings = sum(t.net_earnings for t in transactions)
        product.times_sold = len(transactions)
        product.avg_sale_price = product.total_gross_sales / len(transactions)

        # Date range
        dates = [t.transaction_date.date() for t in transactions]
        product.first_sold_date = min(dates)
        product.last_sold_date = max(dates)

        product.updated_at = datetime.utcnow()
        session.add(product)


def update_buyer_aggregates(session: Session, buyer_ids: List[int]) -> None:
    """
    Update aggregate statistics for buyers.

    Args:
        session: Database session
        buyer_ids: List of buyer IDs to update
    """
    for buyer_id in buyer_ids:
        buyer = session.get(WhatnotBuyer, buyer_id)
        if not buyer:
            continue

        # Get all transactions for this buyer
        transactions = session.exec(
            select(SalesTransaction)
            .where(SalesTransaction.buyer_id == buyer_id)
        ).all()

        if not transactions:
            continue

        # Update aggregates
        buyer.total_purchases = len(transactions)
        buyer.total_spent = sum(t.gross_sale_price for t in transactions)
        buyer.avg_purchase_price = buyer.total_spent / len(transactions)
        buyer.is_repeat_buyer = len(transactions) > 1

        # Date range
        dates = [t.transaction_date.date() for t in transactions]
        buyer.first_purchase_date = min(dates)
        buyer.last_purchase_date = max(dates)

        buyer.updated_at = datetime.utcnow()
        session.add(buyer)


def import_marketplace_excel(
    session: Session,
    file_path: str
) -> ImportResult:
    """
    Import marketplace orders from Excel file.

    Reads 'WhatNot Marketplace' sheet with structure:
    - Row 0: Column headers
    - Row 1+: Transaction data

    Args:
        session: Database session
        file_path: Path to Excel file

    Returns:
        ImportResult with statistics and any errors
    """
    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        # Read the WhatNot Marketplace sheet
        df = pd.read_excel(file_path, sheet_name='WhatNot Marketplace', header=0)

        # The first row contains the actual headers, second row starts data
        # Extract actual column names from first row
        actual_headers = df.iloc[0].tolist()
        df = pd.read_excel(file_path, sheet_name='WhatNot Marketplace', header=0, skiprows=[1])

    except Exception as e:
        return ImportResult(
            show_id=0,
            total_rows=0,
            imported=0,
            skipped=0,
            errors=[f"Failed to read Excel file: {str(e)}"],
            warnings=[],
            cogs_assigned_count=0,
            cogs_missing_count=0
        )

    # Track results
    imported_count = 0
    skipped_count = 0
    errors = []
    warnings = []
    cogs_assigned = 0
    product_ids = set()
    buyer_ids = set()

    # Process each row
    for idx, row in df.iterrows():
        try:
            # Skip empty rows
            if pd.isna(row.iloc[0]):  # Check if date is empty
                skipped_count += 1
                continue

            # Parse transaction date
            trans_date = parse_date(row.iloc[0])

            # Extract fields with robust null handling
            product_name = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else None
            if not product_name or product_name == 'nan':
                skipped_count += 1
                warnings.append(f"Row {idx + 2}: Skipped - no product name")
                continue

            # Buyer
            buyer_username = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else None
            if not buyer_username or buyer_username == 'nan':
                skipped_count += 1
                warnings.append(f"Row {idx + 2}: Skipped - no buyer")
                continue

            # Numeric fields with safe parsing
            quantity = int(row.iloc[2]) if not pd.isna(row.iloc[2]) else 1
            total_revenue = parse_decimal(row.iloc[4]) if not pd.isna(row.iloc[4]) else Decimal("0")
            payment_status = str(row.iloc[5]).strip() if not pd.isna(row.iloc[5]) else "Unknown"
            discount = parse_decimal(row.iloc[6]) if not pd.isna(row.iloc[6]) else Decimal("0")
            whatnot_commission = parse_decimal(row.iloc[7]) if not pd.isna(row.iloc[7]) else Decimal("0")
            whatnot_fee = parse_decimal(row.iloc[8]) if not pd.isna(row.iloc[8]) else Decimal("0")
            payment_processing_fee = parse_decimal(row.iloc[9]) if not pd.isna(row.iloc[9]) else Decimal("0")
            net_earnings = parse_decimal(row.iloc[10]) if not pd.isna(row.iloc[10]) else Decimal("0")

            # COGS and profit (may be empty) - use None for truly empty values
            cogs_value = parse_decimal(row.iloc[11]) if not pd.isna(row.iloc[11]) else None
            if cogs_value == Decimal("0"):
                cogs_value = None  # Treat 0 as no COGS for marketplace

            net_profit = parse_decimal(row.iloc[12]) if not pd.isna(row.iloc[12]) else None
            roi = parse_decimal(row.iloc[13]) if not pd.isna(row.iloc[13]) else None
            notes = str(row.iloc[14]).strip() if not pd.isna(row.iloc[14]) else None
            if notes == 'nan':
                notes = None

            # Get or create product
            product = get_or_create_product(session, product_name)
            product_ids.add(product.id)

            # Get or create buyer
            buyer = get_or_create_buyer(session, buyer_username)
            buyer_ids.add(buyer.id)

            # Create transaction
            transaction = SalesTransaction(
                show_id=None,  # Marketplace orders don't belong to a show
                sale_type="marketplace",
                transaction_date=trans_date,
                item_name=product_name,
                quantity=quantity,
                buyer_username=buyer_username,
                payment_status=payment_status,
                total_revenue=total_revenue,
                gross_sale_price=total_revenue,  # Use total_revenue as gross_sale_price for consistency
                discount=discount,
                whatnot_commission=whatnot_commission,
                whatnot_fee=whatnot_fee,
                payment_processing_fee=payment_processing_fee,
                shipping=Decimal("0"),
                net_earnings=net_earnings,
                cogs=cogs_value,
                net_profit=net_profit,
                roi_percent=roi,
                notes=notes,
                product_id=product.id,
                buyer_id=buyer.id,
                row_number=idx + 2,  # +2 because of header row and 0-indexing
            )

            # If COGS not provided, try to auto-assign via rules
            if transaction.cogs is None:
                normalized_name = normalize_product_name(product_name)
                rule_id, cogs_amount = match_cogs_rule(session, normalized_name)

                if rule_id and cogs_amount:
                    apply_cogs_to_transaction(transaction, cogs_amount, rule_id)
                    cogs_assigned += 1

            elif transaction.cogs is not None:
                cogs_assigned += 1

            session.add(transaction)
            imported_count += 1

        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            skipped_count += 1
            continue

    # Commit all transactions
    session.commit()

    # Update product and buyer aggregates
    update_product_aggregates(session, list(product_ids))
    update_buyer_aggregates(session, list(buyer_ids))

    session.commit()

    return ImportResult(
        show_id=0,  # No show ID for marketplace
        total_rows=len(df),
        imported=imported_count,
        skipped=skipped_count,
        errors=errors,
        warnings=warnings,
        cogs_assigned_count=cogs_assigned,
        cogs_missing_count=imported_count - cogs_assigned
    )
