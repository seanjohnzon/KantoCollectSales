"""
⭐ CRITICAL: COGS (Cost of Goods Sold) mapping service.

Provides keyword-based automatic COGS assignment to products during import.
This is the core feature that enables automatic cost tracking.
"""

import re
from decimal import Decimal
from typing import Optional, Tuple, List
from sqlmodel import Session, select

from app.models.whatnot import (
    COGSMappingRule,
    SalesTransaction,
    WhatnotProduct,
    MatchType,
)


def normalize_product_name(name: str) -> str:
    """
    Normalize product names for consistent matching.

    Examples:
        "Marshall D. Teach (AA) OP09-093" → "marshall d teach aa op09-093"
        "  Booster Pack Bundle  " → "booster pack bundle"
        "Random Asian Pack!!" → "random asian pack"

    Args:
        name: Raw product name from Excel

    Returns:
        Normalized lowercase string with special chars removed
    """
    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove special characters except spaces and hyphens
    normalized = re.sub(r'[^a-z0-9\s\-]', '', normalized)

    # Collapse multiple spaces to single space
    normalized = ' '.join(normalized.split())

    return normalized


def match_cogs_rule(
    session: Session,
    normalized_product_name: str
) -> Tuple[Optional[int], Optional[Decimal]]:
    """
    Find matching COGS rule by checking keywords in priority order.

    Rules are checked from highest priority to lowest. The first matching rule wins.

    Args:
        session: Database session
        normalized_product_name: Product name after normalization

    Returns:
        Tuple of (rule_id, cogs_amount) if match found, or (None, None) if no match

    Example:
        >>> match_cogs_rule(session, "marshall d teach aa op09-093")
        (5, Decimal("30.00"))  # Matched "Marshall D. Teach" rule
    """
    # Get all active rules ordered by priority DESC (highest first)
    query = (
        select(COGSMappingRule)
        .where(COGSMappingRule.is_active == True)
        .order_by(COGSMappingRule.priority.desc())
    )
    rules = session.exec(query).all()

    # Check each rule in priority order
    for rule in rules:
        # Check each keyword in the rule
        for keyword in rule.keywords:  # JSON array of strings
            keyword_normalized = keyword.lower().strip()

            # Match based on rule's match_type
            if rule.match_type == MatchType.CONTAINS:
                if keyword_normalized in normalized_product_name:
                    return (rule.id, rule.cogs_amount)

            elif rule.match_type == MatchType.STARTS_WITH:
                if normalized_product_name.startswith(keyword_normalized):
                    return (rule.id, rule.cogs_amount)

            elif rule.match_type == MatchType.ENDS_WITH:
                if normalized_product_name.endswith(keyword_normalized):
                    return (rule.id, rule.cogs_amount)

            elif rule.match_type == MatchType.EXACT:
                if normalized_product_name == keyword_normalized:
                    return (rule.id, rule.cogs_amount)

    # No match found
    return (None, None)


def apply_cogs_to_transaction(
    transaction: SalesTransaction,
    cogs_per_unit: Decimal,
    rule_id: Optional[int] = None
) -> None:
    """
    Apply COGS to a transaction and calculate profit/ROI.

    Modifies the transaction object in-place.

    Args:
        transaction: Transaction to update
        cogs_per_unit: Cost per unit (will be multiplied by quantity)
        rule_id: Optional COGS rule ID that matched (for audit trail)

    Side Effects:
        Sets transaction.cogs, transaction.net_profit, transaction.roi_percent,
        and transaction.matched_cogs_rule_id
    """
    # Calculate total COGS
    total_cogs = cogs_per_unit * Decimal(transaction.quantity)
    transaction.cogs = total_cogs
    transaction.matched_cogs_rule_id = rule_id

    # Calculate net profit (net earnings - COGS)
    transaction.net_profit = transaction.net_earnings - total_cogs

    # Calculate ROI percentage
    if total_cogs > 0:
        transaction.roi_percent = (transaction.net_profit / total_cogs) * Decimal("100")
    else:
        transaction.roi_percent = None


def test_rule_against_products(
    session: Session,
    rule: COGSMappingRule,
    limit: int = 20
) -> List[str]:
    """
    Test a COGS rule against existing products to see what it would match.

    Useful for validating rules before saving them.

    Args:
        session: Database session
        rule: COGS rule to test (can be unsaved)
        limit: Maximum number of matches to return

    Returns:
        List of product names that would match this rule

    Example:
        >>> rule = COGSMappingRule(keywords=["aa", "alternate art"], match_type="contains")
        >>> test_rule_against_products(session, rule)
        ["Marshall D. Teach (AA)", "Monkey D. Luffy (Alt Art)", ...]
    """
    # Get all products
    products = session.exec(select(WhatnotProduct).limit(1000)).all()

    matched_names = []
    for product in products:
        # Normalize product name
        normalized = normalize_product_name(product.product_name)

        # Check if any keyword matches
        for keyword in rule.keywords:
            keyword_normalized = keyword.lower().strip()

            matched = False
            if rule.match_type == MatchType.CONTAINS:
                matched = keyword_normalized in normalized
            elif rule.match_type == MatchType.STARTS_WITH:
                matched = normalized.startswith(keyword_normalized)
            elif rule.match_type == MatchType.ENDS_WITH:
                matched = normalized.endswith(keyword_normalized)
            elif rule.match_type == MatchType.EXACT:
                matched = normalized == keyword_normalized

            if matched:
                matched_names.append(product.product_name)
                break  # Move to next product

        if len(matched_names) >= limit:
            break

    return matched_names


def get_cogs_coverage_stats(session: Session) -> dict:
    """
    Get statistics on COGS coverage across all transactions.

    Args:
        session: Database session

    Returns:
        Dictionary with coverage statistics:
        {
            'total_transactions': 150,
            'with_cogs': 127,
            'without_cogs': 23,
            'coverage_percent': 84.67
        }
    """
    # Get all transactions
    all_transactions = session.exec(select(SalesTransaction)).all()
    total = len(all_transactions)

    if total == 0:
        return {
            'total_transactions': 0,
            'with_cogs': 0,
            'without_cogs': 0,
            'coverage_percent': 0.0
        }

    # Count transactions with COGS
    with_cogs = sum(1 for t in all_transactions if t.cogs is not None)
    without_cogs = total - with_cogs
    coverage_percent = (with_cogs / total) * 100

    return {
        'total_transactions': total,
        'with_cogs': with_cogs,
        'without_cogs': without_cogs,
        'coverage_percent': round(coverage_percent, 2)
    }


def get_rule_performance(session: Session) -> List[dict]:
    """
    Get performance statistics for each COGS rule.

    Shows how many transactions each rule has matched.

    Args:
        session: Database session

    Returns:
        List of dictionaries with rule performance:
        [
            {
                'rule_id': 1,
                'rule_name': 'One Piece AA Cards',
                'matches': 35,
                'total_cogs_assigned': Decimal('875.00')
            },
            ...
        ]
    """
    rules = session.exec(select(COGSMappingRule)).all()

    performance = []
    for rule in rules:
        # Get transactions matched by this rule
        matched_transactions = session.exec(
            select(SalesTransaction)
            .where(SalesTransaction.matched_cogs_rule_id == rule.id)
        ).all()

        match_count = len(matched_transactions)
        total_cogs = sum(
            t.cogs for t in matched_transactions if t.cogs is not None
        ) or Decimal("0")

        performance.append({
            'rule_id': rule.id,
            'rule_name': rule.rule_name,
            'matches': match_count,
            'total_cogs_assigned': total_cogs
        })

    # Sort by match count descending
    performance.sort(key=lambda x: x['matches'], reverse=True)

    return performance


def recalculate_transaction_cogs(
    session: Session,
    transaction: SalesTransaction
) -> bool:
    """
    Re-run COGS matching for a specific transaction.

    Useful when rules are updated and you want to re-apply them.

    Args:
        session: Database session
        transaction: Transaction to recalculate

    Returns:
        True if COGS was assigned, False if no matching rule found
    """
    # Normalize product name
    normalized = normalize_product_name(transaction.item_name)

    # Try to match a rule
    rule_id, cogs_amount = match_cogs_rule(session, normalized)

    if cogs_amount is not None:
        # Apply COGS
        apply_cogs_to_transaction(transaction, cogs_amount, rule_id)
        session.add(transaction)
        return True
    else:
        # No match - clear existing COGS
        transaction.cogs = None
        transaction.net_profit = None
        transaction.roi_percent = None
        transaction.matched_cogs_rule_id = None
        session.add(transaction)
        return False
