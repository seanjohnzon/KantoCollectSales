#!/usr/bin/env python3
"""
Delete test transactions (NULL show_id AND not marketplace).
"""
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import SalesTransaction

engine = create_engine("sqlite:///./whatnot_sales.db")

print("=" * 80)
print("DELETING TEST TRANSACTIONS")
print("=" * 80)

with Session(engine) as db:
    # Find test transactions: NULL show_id AND not marketplace
    test_transactions = db.exec(
        select(SalesTransaction).where(
            SalesTransaction.show_id == None,
            SalesTransaction.sale_type != 'marketplace'
        )
    ).all()

    print(f"\nFound {len(test_transactions)} test transactions:")
    print(f"{'ID':<8} {'Date':<20} {'Item Name':<50} {'Sale Type':<15}")
    print("-" * 80)

    for t in test_transactions:
        print(f"{t.id:<8} {str(t.transaction_date):<20} {t.item_name[:47]:<50} {t.sale_type or 'NULL':<15}")

    if len(test_transactions) > 0:
        print(f"\n🗑️  Deleting {len(test_transactions)} test transactions...")
        for t in test_transactions:
            db.delete(t)
        db.commit()
        print(f"✅ Deleted {len(test_transactions)} test transactions")
    else:
        print("\n✓ No test transactions found!")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
