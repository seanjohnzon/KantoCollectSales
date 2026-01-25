#!/usr/bin/env python3
"""
Migrate product catalog to rule-based matching system.

This script:
1. Adds new columns to product_catalog table
2. Converts existing keywords to include_keywords
3. Sets appropriate rule_type for each catalog item
4. Sets "Unmapped Items" to CATCH_ALL (catches anything not matched elsewhere)
"""
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, create_engine, select, text
from app.models.whatnot import ProductCatalog, CatalogRuleType

engine = create_engine("sqlite:///./whatnot_sales.db")

print("=" * 80)
print("MIGRATING TO RULE-BASED MATCHING SYSTEM")
print("=" * 80)

with Session(engine) as db:
    # Step 1: Check if columns exist, add if not
    print("\n[1] Checking database schema...")

    # Check if rule_type column exists
    result = db.exec(text("PRAGMA table_info(product_catalog)")).all()
    column_names = [row[1] for row in result]

    needs_migration = "rule_type" not in column_names

    if needs_migration:
        print("   ⚠️  New columns not found - adding them now...")

        # Add new columns (use NULL default, we'll populate in next step)
        db.exec(text("ALTER TABLE product_catalog ADD COLUMN rule_type TEXT"))
        db.exec(text("ALTER TABLE product_catalog ADD COLUMN include_keywords TEXT"))
        db.exec(text("ALTER TABLE product_catalog ADD COLUMN exclude_keywords TEXT"))
        db.exec(text("ALTER TABLE product_catalog ADD COLUMN priority INTEGER"))
        db.commit()

        print("   ✅ New columns added successfully!")
    else:
        print("   ✅ Columns already exist")

    # Step 2: Migrate existing keywords to include_keywords
    print("\n[2] Migrating existing keywords to rule-based system...")

    catalog_items = db.exec(select(ProductCatalog)).all()

    migrated_count = 0
    for item in catalog_items:
        # If already migrated (has rule_type set), skip
        if item.rule_type is not None:
            continue

        # Special handling for "Unmapped Items" - make it CATCH_ALL
        if item.name == "Unmapped Items":
            item.rule_type = CatalogRuleType.CATCH_ALL
            item.include_keywords = []  # No keywords needed - catches everything else
            item.exclude_keywords = []
            item.priority = 0  # Lowest priority (checked last)
            print(f"   [{item.id}] {item.name} → CATCH_ALL (priority: 0)")

        # Items that need ALL keywords to match (both conditions must be true)
        elif item.name in [
            "Prismatic Evolutions Mini Tin",  # Needs BOTH "prismatic" AND "mini tin"
            "Mega Heroes Mini Tin",  # Needs BOTH "mega heroes" AND "mini tin"
            "Surging Sparks 2-Pack Trainer Box and Booster Bundle",  # Needs BOTH "surging sparks" AND "etb" AND "booster bundle"
        ]:
            item.rule_type = CatalogRuleType.INCLUDE_ALL
            item.include_keywords = item.keywords.copy()
            item.exclude_keywords = []
            item.priority = 200  # Higher priority to match before generic items
            print(f"   [{item.id}] {item.name} → INCLUDE_ALL (priority: 200)")

        # All other items: INCLUDE_ANY (contains at least one keyword)
        else:
            item.rule_type = CatalogRuleType.INCLUDE_ANY
            item.include_keywords = item.keywords.copy()
            item.exclude_keywords = []
            item.priority = 100  # Default priority
            print(f"   [{item.id}] {item.name} → INCLUDE_ANY (priority: 100)")

        db.add(item)
        migrated_count += 1

    db.commit()
    print(f"\n   ✅ Migrated {migrated_count} catalog items")

    # Step 3: Summary
    print("\n[3] Migration summary:")

    items_by_type = {}
    for item in catalog_items:
        rule_type = item.rule_type
        if rule_type not in items_by_type:
            items_by_type[rule_type] = []
        items_by_type[rule_type].append(item.name)

    for rule_type, names in sorted(items_by_type.items()):
        print(f"\n   {rule_type.upper()}:")
        for name in names:
            print(f"      - {name}")

print("\n" + "=" * 80)
print("✅ MIGRATION COMPLETE!")
print("=" * 80)
print("\n📝 Summary:")
print("   - Added new columns: rule_type, include_keywords, exclude_keywords, priority")
print("   - Converted existing keywords to rule-based system")
print("   - 'Unmapped Items' now catches ALL unmatched transactions")
print("   - No transactions will disappear anymore!")
print("\n💡 Next steps:")
print("   1. Restart the backend server")
print("   2. Test the Master Catalog - all 289 disappeared transactions should now appear in 'Unmapped Items'")
print("   3. Use the UI to edit rules if needed (Edit button shows both include/exclude keywords)")
print()
