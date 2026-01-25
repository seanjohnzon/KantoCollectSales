#!/usr/bin/env python3
"""
Retroactively apply COGS rules to existing transactions.

Since most transactions were imported before COGS rules were created,
this script re-applies the matching logic to assign COGS.
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, select
from app.core.whatnot_database import whatnot_engine
from app.models.whatnot import SalesTransaction, COGSMappingRule, WhatnotProduct
from app.services.whatnot.cogs_service import match_cogs_rule
from decimal import Decimal

print("="*70)
print("RETROACTIVE COGS APPLICATION")
print("="*70)

with Session(whatnot_engine) as session:
    # Get all transactions without COGS
    transactions_query = select(SalesTransaction).where(
        (SalesTransaction.cogs == None) | (SalesTransaction.cogs == Decimal('0'))
    )
    transactions = session.exec(transactions_query).all()

    print(f"\nFound {len(transactions)} transactions without COGS")

    if len(transactions) == 0:
        print("✅ All transactions already have COGS assigned!")
        sys.exit(0)

    # Get all active COGS rules
    rules_query = select(COGSMappingRule).where(
        COGSMappingRule.is_active == True
    ).order_by(COGSMappingRule.priority.desc())

    rules = session.exec(rules_query).all()
    print(f"Found {len(rules)} active COGS rules\n")

    if len(rules) == 0:
        print("⚠️  No active COGS rules found. Please create rules first.")
        sys.exit(1)

    # Track progress
    updated_count = 0
    no_match_count = 0
    products_updated = set()

    print("Processing transactions...")
    for i, transaction in enumerate(transactions):
        if i > 0 and i % 100 == 0:
            print(f"  Processed {i}/{len(transactions)} transactions...")

        # Get product for this transaction
        product = session.get(WhatnotProduct, transaction.product_id)
        if not product:
            no_match_count += 1
            continue

        # Try to match COGS rule
        matched_rule_id, matched_cogs = match_cogs_rule(session, product.normalized_name)

        if matched_cogs:
            # Calculate COGS for this transaction
            quantity = transaction.quantity or 1
            total_cogs = matched_cogs * Decimal(str(quantity))

            # Update transaction
            transaction.cogs = total_cogs
            transaction.matched_cogs_rule_id = matched_rule_id

            # Recalculate net profit
            transaction.net_profit = transaction.net_earnings - total_cogs

            # Calculate ROI if COGS > 0
            if total_cogs > 0:
                transaction.roi_percent = (transaction.net_profit / total_cogs) * Decimal('100')
            else:
                transaction.roi_percent = None

            updated_count += 1
            products_updated.add(product.id)
        else:
            no_match_count += 1

    # Commit all updates
    session.commit()

    print(f"\n{'─'*70}")
    print(f"RESULTS:")
    print(f"  ✅ Updated: {updated_count} transactions")
    print(f"  ⚠️  No match: {no_match_count} transactions")
    print(f"  📦 Products affected: {len(products_updated)}")

    # Calculate new coverage
    total_trans_query = select(SalesTransaction)
    total_trans = session.exec(total_trans_query).all()
    total_count = len(total_trans)

    with_cogs = sum(1 for t in total_trans if t.cogs and t.cogs > 0)
    coverage = (with_cogs / total_count * 100) if total_count > 0 else 0

    print(f"\n  📊 New COGS Coverage: {with_cogs}/{total_count} ({coverage:.1f}%)")

print(f"{'='*70}")
print("✅ Retroactive COGS application complete!")
print("="*70)

# Show top unmatched products
print("\n📋 Top products still needing COGS rules:")
with Session(whatnot_engine) as session:
    # Get products without COGS
    unmatched_products_query = select(WhatnotProduct).where(
        WhatnotProduct.id.in_(
            select(SalesTransaction.product_id).where(
                (SalesTransaction.cogs == None) | (SalesTransaction.cogs == Decimal('0'))
            ).distinct()
        )
    ).order_by(WhatnotProduct.total_gross_sales.desc())

    unmatched_products = session.exec(unmatched_products_query).all()[:15]

    for i, product in enumerate(unmatched_products, 1):
        revenue = Decimal(str(product.total_gross_sales or 0))
        times = product.times_sold or 0
        print(f"{i:2}. ${revenue:7,.2f} | {times:3}x | {product.product_name[:60]}")

print("\n💡 Tip: Create COGS rules for the top unmatched products to increase coverage!")
