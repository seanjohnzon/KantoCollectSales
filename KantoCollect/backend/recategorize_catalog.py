#!/usr/bin/env python3
"""
Recategorize product catalog items.
"""
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import ProductCatalog

engine = create_engine("sqlite:///./whatnot_sales.db")

print("=" * 80)
print("RECATEGORIZING PRODUCT CATALOG")
print("=" * 80)

# Define recategorization mapping
recategorizations = {
    # Blister (change from "3 Pack Blister" to "Blister")
    21: "Blister",  # Phantasmal Flames 3 Pack Blister
    53: "Blister",  # Phantasmal Flames Single Blister Pack
    35: "Blister",  # Phantasmal Flames Single Pack Blister Cottonee
    33: "Blister",  # Phantasmal Flames Single Pack Blister Whimsicott

    # Sleeved Pack
    34: "Sleeved Pack",  # Destined Rivals Sleeved Booster Pack
    61: "Sleeved Pack",  # 2 Pack Destined Rivals Sleeves
    28: "Sleeved Pack",  # Mega Evolution Sleeved Booster Pack
    29: "Sleeved Pack",  # Phantasmal Flames Sleeved Booster Pack

    # Booster Pack (all single/2-pack loose boosters)
    32: "Booster Pack",  # 2 x Black Bolt Booster Pack
    68: "Booster Pack",  # 2 x Crown Zenith Booster Pack
    55: "Booster Pack",  # 2 x Destined Rivals Booster Pack
    42: "Booster Pack",  # 2 x Journey Together Booster Pack
    57: "Booster Pack",  # 2 x Mega Evolutions Booster Pack
    30: "Booster Pack",  # 2 x Paldean Fates Booster Pack
    56: "Booster Pack",  # 2 x Phantasmal Flames Booster Pack
    37: "Booster Pack",  # 2 x Prismatic Evolutions Booster Pack
    38: "Booster Pack",  # 2 x Stellar Crown Booster Pack
    31: "Booster Pack",  # 2 x Surging Sparks Booster Pack
    70: "Booster Pack",  # 2 x The Azure Sea's Seven Booster Pack (OP14)
    43: "Booster Pack",  # 2 x Twilight Masquerade Booster Pack
    69: "Booster Pack",  # Black Bolt Booster Pack
    36: "Booster Pack",  # Crown Zenith Booster Pack
    67: "Booster Pack",  # Journey Together Booster Pack
    62: "Booster Pack",  # Mega Evolutions Booster Pack
    66: "Booster Pack",  # Paldean Fates Booster Pack
    63: "Booster Pack",  # Phantasmal Flames Booster Pack
    65: "Booster Pack",  # Stellar Crown Booster Pack
    64: "Booster Pack",  # Surging Sparks Booster Pack
    41: "Booster Pack",  # The Azure Sea's Seven Booster Pack (OP14)

    # Singles
    51: "Singles",  # Single Cards (rename)

    # Collection Box
    45: "Collection Box",  # Fall 2025 Collector Chest

    # Toy
    52: "Toy",  # Plushy Toy

    # Multi Packs
    58: "Multi Packs",  # RYTH
    60: "Multi Packs",  # 5 pack mix
    59: "Multi Packs",  # 2 Packer

    # Pack Giveaway
    27: "Pack Giveaway",  # random pack

    # Illustration Box
    46: "Illustration Box",  # One Piece Card Game Illustration Box Vol. 3
}

with Session(engine) as db:
    updated_count = 0

    for item_id, new_category in recategorizations.items():
        item = db.get(ProductCatalog, item_id)
        if not item:
            print(f"⚠️  Item {item_id} not found - skipping")
            continue

        old_category = item.category
        if old_category == new_category:
            print(f"✓ [{item_id:3d}] {item.name:50s} | Already '{new_category}'")
        else:
            item.category = new_category
            db.add(item)
            updated_count += 1
            print(f"✓ [{item_id:3d}] {item.name:50s} | '{old_category}' → '{new_category}'")

    db.commit()

    print("\n" + "=" * 80)
    print(f"✅ RECATEGORIZATION COMPLETE - {updated_count} items updated")
    print("=" * 80)

    # Show summary by category
    print("\nCatalog by Category:")
    print("-" * 80)

    all_items = db.exec(select(ProductCatalog).order_by(ProductCatalog.category, ProductCatalog.name)).all()
    current_category = None

    for item in all_items:
        if item.category != current_category:
            current_category = item.category
            print(f"\n{current_category}:")
        print(f"  - {item.name}")

    print("\n" + "=" * 80)
