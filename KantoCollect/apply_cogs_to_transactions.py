#!/usr/bin/env python3
"""
Apply COGS rules to all existing transactions.

This script will:
1. Load all COGS mapping rules (by priority)
2. For each transaction without COGS:
   - Match product name against rules
   - Assign COGS if match found
   - Calculate net profit and ROI
3. Update transaction records
4. Report coverage statistics
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import COGSMappingRule, SalesTransaction, WhatnotProduct
from decimal import Decimal
import re

# Connect to database
whatnot_engine = create_engine("sqlite:////Users/sahcihansahin/KantoCollect/backend/whatnot_sales.db")

print("="*70)
print("APPLY COGS RULES TO TRANSACTIONS")
print("="*70)

def normalize_product_name(name: str) -> str:
    """Normalize product name for matching."""
    if not name:
        return ""
    # Remove special characters, convert to lowercase
    normalized = re.sub(r'[^a-z0-9\s\-]', '', name.lower()).strip()
    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def match_cogs_rule(session: Session, product_name: str, rules: list) -> tuple:
    """
    Find matching COGS rule by checking keywords.
    Returns: (rule_id, cogs_amount) or (None, None)
    """
    normalized_name = normalize_product_name(product_name)

    for rule in rules:
        if not rule.is_active:
            continue

        for keyword in rule.keywords:
            keyword_normalized = normalize_product_name(keyword)

            matched = False
            if rule.match_type == 'contains':
                matched = keyword_normalized in normalized_name
            elif rule.match_type == 'starts_with':
                matched = normalized_name.startswith(keyword_normalized)
            elif rule.match_type == 'ends_with':
                matched = normalized_name.endswith(keyword_normalized)
            elif rule.match_type == 'exact':
                matched = normalized_name == keyword_normalized

            if matched:
                return (rule.id, rule.cogs_amount)

    return (None, None)

with Session(whatnot_engine) as session:
    # Load all rules ordered by priority
    rules = session.exec(
        select(COGSMappingRule)
        .where(COGSMappingRule.is_active == True)
        .order_by(COGSMappingRule.priority.desc())
    ).all()

    print(f"\n📋 Loaded {len(rules)} active COGS rules")

    # Get all transactions
    transactions = session.exec(select(SalesTransaction)).all()
    print(f"📦 Found {len(transactions)} total transactions")

    # Statistics
    already_has_cogs = sum(1 for t in transactions if t.cogs is not None and t.cogs > 0)
    needs_cogs = len(transactions) - already_has_cogs

    print(f"\n   Already has COGS: {already_has_cogs}")
    print(f"   Needs COGS: {needs_cogs}")

    if needs_cogs == 0:
        print("\n✅ All transactions already have COGS assigned!")
        sys.exit(0)

    print(f"\n🔄 Processing {needs_cogs} transactions...\n")

    # Track results
    matched_count = 0
    unmatched_count = 0
    rule_matches = {}  # rule_id -> count

    for i, txn in enumerate(transactions, 1):
        # Skip if already has COGS
        if txn.cogs and txn.cogs > 0:
            continue

        # Try to match rule
        rule_id, cogs_amount = match_cogs_rule(session, txn.item_name, rules)

        if rule_id:
            # Calculate COGS for quantity
            total_cogs = cogs_amount * txn.quantity

            # Calculate profit and ROI
            if txn.net_earnings:
                net_profit = txn.net_earnings - total_cogs
                roi_percent = (net_profit / total_cogs * 100) if total_cogs > 0 else None
            else:
                net_profit = None
                roi_percent = None

            # Update transaction
            txn.cogs = total_cogs
            txn.net_profit = net_profit
            txn.roi_percent = roi_percent

            matched_count += 1
            rule_matches[rule_id] = rule_matches.get(rule_id, 0) + 1

            if matched_count % 50 == 0:
                print(f"   Processed {matched_count} matches...")
        else:
            unmatched_count += 1

    # Commit all changes
    session.commit()
    print(f"\n✅ Applied COGS to {matched_count} transactions")

# Report results
print("\n" + "="*70)
print("RESULTS")
print("="*70)

with Session(whatnot_engine) as session:
    # Overall stats
    all_transactions = session.exec(select(SalesTransaction)).all()
    total = len(all_transactions)
    with_cogs = sum(1 for t in all_transactions if t.cogs is not None and t.cogs > 0)
    without_cogs = total - with_cogs

    coverage_percent = (with_cogs / total * 100) if total > 0 else 0

    print(f"\n📊 COGS Coverage:")
    print(f"   Total transactions: {total}")
    print(f"   With COGS: {with_cogs} ({coverage_percent:.1f}%)")
    print(f"   Without COGS: {without_cogs} ({100 - coverage_percent:.1f}%)")

    # Rule performance
    if rule_matches:
        print(f"\n🎯 Rule Performance:")
        rules_by_id = {rule.id: rule for rule in session.exec(select(COGSMappingRule)).all()}

        for rule_id, count in sorted(rule_matches.items(), key=lambda x: x[1], reverse=True):
            rule = rules_by_id.get(rule_id)
            if rule:
                print(f"   {rule.rule_name}: {count} matches (${rule.cogs_amount} each)")

    # Show sample unmatched products
    if without_cogs > 0:
        print(f"\n⚠️  Sample Unmatched Products (need manual COGS or new rules):")
        unmatched_txns = [t for t in all_transactions if not t.cogs or t.cogs == 0]
        # Get unique product names
        unique_products = {}
        for txn in unmatched_txns:
            if txn.item_name not in unique_products:
                unique_products[txn.item_name] = txn

        # Show first 10
        for i, (product_name, txn) in enumerate(list(unique_products.items())[:10], 1):
            print(f"   {i}. {product_name[:60]}")
            if txn.net_earnings:
                print(f"      Net earnings: ${txn.net_earnings:.2f}")

        if len(unique_products) > 10:
            print(f"   ... and {len(unique_products) - 10} more unique products")

print("\n" + "="*70)
print("✅ COGS application complete!")
print("="*70)
