"""
Analytics service for WhatNot sales dashboards and reports.

Provides pre-computed queries for dashboard summaries, top performers, and trends.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List
from sqlmodel import Session, select, func

from app.models.whatnot import (
    WhatnotShow,
    SalesTransaction,
    WhatnotProduct,
    WhatnotBuyer,
)


def get_dashboard_summary(session: Session, date_range: Optional[str] = None) -> dict:
    """
    Get high-level dashboard metrics.

    Args:
        session: Database session
        date_range: Filter by date range ('all', '30days', '90days', 'year', 'month')

    Returns:
        Dictionary with summary statistics
    """
    # Build date filter
    cutoff_date = _get_cutoff_date(date_range)

    # Query shows in range
    query = select(WhatnotShow)
    if cutoff_date:
        query = query.where(WhatnotShow.show_date >= cutoff_date)
    shows = session.exec(query).all()

    if not shows:
        return {
            'total_gross_sales': Decimal("0"),
            'total_net_earnings': Decimal("0"),
            'total_profit': Decimal("0"),
            'total_cogs': Decimal("0"),
            'total_items': 0,
            'show_count': 0,
            'unique_buyers': 0,
            'unique_products': 0,
            'avg_roi_percent': None,
        }

    # Aggregate from shows
    total_gross = sum(s.total_gross_sales for s in shows)
    total_net = sum(s.total_net_earnings for s in shows)
    total_profit = sum(s.total_net_profit for s in shows)
    total_cogs = sum(s.total_cogs for s in shows)
    total_items = sum(s.item_count for s in shows)

    # Get unique buyers/products from transactions
    show_ids = [s.id for s in shows]
    transactions = session.exec(
        select(SalesTransaction)
        .where(SalesTransaction.show_id.in_(show_ids))
    ).all()

    unique_buyers = len(set(t.buyer_id for t in transactions if t.buyer_id))
    unique_products = len(set(t.product_id for t in transactions if t.product_id))

    # Calculate average ROI (only for transactions with COGS)
    transactions_with_cogs = [t for t in transactions if t.cogs is not None and t.cogs > 0]
    if transactions_with_cogs:
        avg_roi = sum(t.roi_percent for t in transactions_with_cogs if t.roi_percent) / len(transactions_with_cogs)
    else:
        avg_roi = None

    return {
        'total_gross_sales': total_gross,
        'total_net_earnings': total_net,
        'total_profit': total_profit,
        'total_cogs': total_cogs,
        'total_items': total_items,
        'show_count': len(shows),
        'unique_buyers': unique_buyers,
        'unique_products': unique_products,
        'avg_roi_percent': round(float(avg_roi), 2) if avg_roi else None,
    }


def get_top_products(
    session: Session,
    limit: int = 10,
    metric: str = 'revenue',
    date_range: Optional[str] = None
) -> List[dict]:
    """
    Get top performing products.

    Args:
        session: Database session
        limit: Number of products to return
        metric: Sort by 'revenue', 'frequency', or 'profit'
        date_range: Optional date filter

    Returns:
        List of product dictionaries with stats
    """
    # Get all products with sales
    products = session.exec(
        select(WhatnotProduct)
        .where(WhatnotProduct.times_sold > 0)
    ).all()

    # Calculate metrics for each product
    product_stats = []
    for product in products:
        # Get transactions (with optional date filter)
        query = select(SalesTransaction).where(SalesTransaction.product_id == product.id)

        if date_range:
            cutoff_date = _get_cutoff_date(date_range)
            if cutoff_date:
                query = query.where(SalesTransaction.transaction_date >= datetime.combine(cutoff_date, datetime.min.time()))

        transactions = session.exec(query).all()

        if not transactions:
            continue

        # Calculate metrics
        total_revenue = sum(t.gross_sale_price for t in transactions)
        total_profit = sum(t.net_profit for t in transactions if t.net_profit is not None) or Decimal("0")
        frequency = len(transactions)

        # Calculate ROI
        transactions_with_cogs = [t for t in transactions if t.cogs and t.cogs > 0]
        if transactions_with_cogs:
            avg_roi = sum(t.roi_percent for t in transactions_with_cogs if t.roi_percent) / len(transactions_with_cogs)
        else:
            avg_roi = None

        product_stats.append({
            'id': product.id,
            'product_name': product.product_name,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'frequency': frequency,
            'avg_roi': round(float(avg_roi), 2) if avg_roi else None,
            'avg_price': total_revenue / frequency if frequency else Decimal("0")
        })

    # Sort by requested metric
    if metric == 'revenue':
        product_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
    elif metric == 'frequency':
        product_stats.sort(key=lambda x: x['frequency'], reverse=True)
    elif metric == 'profit':
        product_stats.sort(key=lambda x: x['total_profit'], reverse=True)

    return product_stats[:limit]


def get_top_buyers(
    session: Session,
    limit: int = 10,
    date_range: Optional[str] = None
) -> List[dict]:
    """
    Get top customers by total spent.

    Args:
        session: Database session
        limit: Number of buyers to return
        date_range: Optional date filter

    Returns:
        List of buyer dictionaries with stats
    """
    # Get all buyers with purchases
    buyers = session.exec(
        select(WhatnotBuyer)
        .where(WhatnotBuyer.total_purchases > 0)
    ).all()

    # Calculate metrics for each buyer
    buyer_stats = []
    for buyer in buyers:
        # Get transactions (with optional date filter)
        query = select(SalesTransaction).where(SalesTransaction.buyer_id == buyer.id)

        if date_range:
            cutoff_date = _get_cutoff_date(date_range)
            if cutoff_date:
                query = query.where(SalesTransaction.transaction_date >= datetime.combine(cutoff_date, datetime.min.time()))

        transactions = session.exec(query).all()

        if not transactions:
            continue

        total_spent = sum(t.gross_sale_price for t in transactions)
        purchase_count = len(transactions)

        buyer_stats.append({
            'id': buyer.id,
            'username': buyer.username,
            'total_spent': total_spent,
            'purchase_count': purchase_count,
            'avg_purchase': total_spent / purchase_count if purchase_count else Decimal("0"),
            'is_repeat_buyer': purchase_count > 1
        })

    # Sort by total spent descending
    buyer_stats.sort(key=lambda x: x['total_spent'], reverse=True)

    return buyer_stats[:limit]


def get_show_details(session: Session, show_id: int) -> dict:
    """
    Get detailed breakdown for a specific show.

    Args:
        session: Database session
        show_id: Show ID

    Returns:
        Dictionary with show details and transaction list
    """
    show = session.get(WhatnotShow, show_id)
    if not show:
        return None

    # Get all transactions
    transactions = session.exec(
        select(SalesTransaction)
        .where(SalesTransaction.show_id == show_id)
        .order_by(SalesTransaction.transaction_date)
    ).all()

    # Get product and buyer info
    product_ids = list(set(t.product_id for t in transactions if t.product_id))
    buyer_ids = list(set(t.buyer_id for t in transactions if t.buyer_id))

    products = session.exec(
        select(WhatnotProduct).where(WhatnotProduct.id.in_(product_ids))
    ).all() if product_ids else []

    buyers = session.exec(
        select(WhatnotBuyer).where(WhatnotBuyer.id.in_(buyer_ids))
    ).all() if buyer_ids else []

    product_map = {p.id: p for p in products}
    buyer_map = {b.id: b for b in buyers}

    # Build transaction details
    transaction_details = []
    for t in transactions:
        product = product_map.get(t.product_id)
        buyer = buyer_map.get(t.buyer_id)

        transaction_details.append({
            'id': t.id,
            'transaction_date': t.transaction_date,
            'item_name': t.item_name,
            'quantity': t.quantity,
            'buyer_username': t.buyer_username,
            'gross_sale_price': t.gross_sale_price,
            'net_earnings': t.net_earnings,
            'cogs': t.cogs,
            'net_profit': t.net_profit,
            'roi_percent': t.roi_percent,
            'product_name': product.product_name if product else None,
            'has_cogs': t.cogs is not None
        })

    # Calculate total_cogs from transactions (in case stored value is stale)
    calculated_total_cogs = sum(
        t.cogs for t in transactions if t.cogs is not None
    )
    calculated_total_profit = sum(
        t.net_profit for t in transactions if t.net_profit is not None
    )

    return {
        'show': {
            'id': show.id,
            'show_date': show.show_date,
            'show_name': show.show_name,
            'total_gross_sales': show.total_gross_sales,
            'total_net_earnings': show.total_net_earnings,
            'total_net_profit': calculated_total_profit or show.total_net_profit,
            'total_cogs': calculated_total_cogs or show.total_cogs,
            'item_count': show.item_count,
            'unique_buyers': show.unique_buyers,
        },
        'transactions': transaction_details
    }


def get_products_needing_cogs(session: Session, limit: int = 50) -> List[dict]:
    """
    Get products that don't have COGS assigned to any of their sales.

    Args:
        session: Database session
        limit: Maximum number to return

    Returns:
        List of products needing COGS configuration
    """
    # Get all products
    products = session.exec(select(WhatnotProduct)).all()

    products_needing_cogs = []
    for product in products:
        # Check if any transactions have COGS
        transactions = session.exec(
            select(SalesTransaction)
            .where(SalesTransaction.product_id == product.id)
        ).all()

        if not transactions:
            continue

        # Count transactions without COGS
        without_cogs = sum(1 for t in transactions if t.cogs is None)

        if without_cogs > 0:
            products_needing_cogs.append({
                'id': product.id,
                'product_name': product.product_name,
                'total_sales': len(transactions),
                'missing_cogs': without_cogs,
                'total_revenue': product.total_gross_sales
            })

    # Sort by revenue descending (high-value products first)
    products_needing_cogs.sort(key=lambda x: x['total_revenue'], reverse=True)

    return products_needing_cogs[:limit]


def _get_cutoff_date(date_range: Optional[str]) -> Optional[date]:
    """
    Convert date range string to cutoff date.

    Args:
        date_range: 'all', '30days', '90days', 'year', 'month'

    Returns:
        Date cutoff or None for 'all'
    """
    if not date_range or date_range == 'all':
        return None

    today = date.today()

    if date_range == '30days':
        return today - timedelta(days=30)
    elif date_range == '90days':
        return today - timedelta(days=90)
    elif date_range == 'year':
        return today - timedelta(days=365)
    elif date_range == 'month':
        # Current month
        return date(today.year, today.month, 1)

    return None
