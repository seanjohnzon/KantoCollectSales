#!/usr/bin/env python3
"""
Add owner field to sales_transactions table.
"""
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, create_engine, text

engine = create_engine("sqlite:///./whatnot_sales.db")

print("=" * 80)
print("ADDING OWNER FIELD TO SALES_TRANSACTIONS")
print("=" * 80)

with Session(engine) as db:
    # Check if column already exists
    result = db.exec(text("PRAGMA table_info(sales_transactions)")).all()
    column_names = [row[1] for row in result]

    if "owner" in column_names:
        print("\n✓ Owner column already exists!")
    else:
        print("\n⚠️  Owner column not found - adding it now...")

        # Add owner column (nullable)
        db.exec(text("ALTER TABLE sales_transactions ADD COLUMN owner TEXT"))
        db.commit()

        print("✅ Owner column added successfully!")
        print("\nOwner can be one of: Cihan, Nima, Askar, Kanto")

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
