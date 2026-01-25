#!/usr/bin/env python3
"""
Remove all COGS rules and clear COGS data from transactions.
This will reset the database to the state before COGS rules were added.
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import COGSMappingRule, SalesTransaction

# Connect to database
whatnot_engine = create_engine("sqlite:////Users/sahcihansahin/KantoCollect/backend/whatnot_sales.db")

print("="*70)
print("REMOVE COGS RULES AND CLEAR COGS DATA")
print("="*70)

with Session(whatnot_engine) as session:
    # Step 1: Clear COGS data from all transactions
    print("\n📋 Step 1: Clearing COGS data from transactions...")

    transactions = session.exec(select(SalesTransaction)).all()
    print(f"   Found {len(transactions)} transactions")

    transactions_with_cogs = [t for t in transactions if t.cogs is not None]
    print(f"   {len(transactions_with_cogs)} have COGS data")

    for txn in transactions:
        txn.cogs = None
        txn.net_profit = None
        txn.roi_percent = None

    session.commit()
    print(f"   ✅ Cleared COGS data from all transactions")

    # Step 2: Delete all COGS rules
    print("\n📋 Step 2: Deleting all COGS rules...")

    rules = session.exec(select(COGSMappingRule)).all()
    print(f"   Found {len(rules)} COGS rules")

    for rule in rules:
        print(f"      - Deleting: {rule.rule_name}")
        session.delete(rule)

    session.commit()
    print(f"   ✅ Deleted all COGS rules")

# Step 3: Verify clean state
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

with Session(whatnot_engine) as session:
    # Check rules
    rules = session.exec(select(COGSMappingRule)).all()
    print(f"\n✅ COGS Rules: {len(rules)} (should be 0)")

    # Check transactions
    transactions = session.exec(select(SalesTransaction)).all()
    transactions_with_cogs = [t for t in transactions if t.cogs is not None]
    transactions_with_profit = [t for t in transactions if t.net_profit is not None]
    transactions_with_roi = [t for t in transactions if t.roi_percent is not None]

    print(f"\n✅ Transactions:")
    print(f"   Total: {len(transactions)}")
    print(f"   With COGS: {len(transactions_with_cogs)} (should be 0)")
    print(f"   With net_profit: {len(transactions_with_profit)} (should be 0)")
    print(f"   With ROI: {len(transactions_with_roi)} (should be 0)")

    # Check that other data is intact
    print(f"\n✅ Data Integrity Check:")
    transactions_with_earnings = [t for t in transactions if t.net_earnings is not None]
    transactions_with_items = [t for t in transactions if t.item_name]
    print(f"   Transactions with net_earnings: {len(transactions_with_earnings)}")
    print(f"   Transactions with item_name: {len(transactions_with_items)}")

print("\n" + "="*70)
print("✅ Database cleaned! Ready for fresh COGS setup.")
print("="*70)
