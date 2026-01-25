#!/usr/bin/env python3
"""
Migrate hardcoded product catalog to database.

This script populates the product_catalog table with the existing 26 items
that were previously hardcoded in the API.
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import ProductCatalog
from decimal import Decimal

# Connect to database
whatnot_engine = create_engine("sqlite:////Users/sahcihansahin/KantoCollect/backend/whatnot_sales.db")

print("=" * 80)
print("MIGRATE PRODUCT CATALOG TO DATABASE")
print("=" * 80)

# Existing 26 items from hardcoded list
base_url = "https://ik.imagekit.io/homecraft/Item%20Pics/"

existing_items = [
    {"id": 1, "name": "Mega Charizard X ex Ultra Premium Collection", "category": "UPC", "image": "Mega Charizard X ex Ultra Premium Collection.jpg", "keywords": ["mega charizard x", "ultra premium", "upc"]},
    {"id": 2, "name": "Team Rocket's Moltres ex Ultra-Premium Collection", "category": "UPC", "image": "Team Rocket_s Moltres ex Ultra-Premium Collection.jpg", "keywords": ["team rocket moltres", "ultra premium", "moltres upc"]},
    {"id": 3, "name": "The Azure Sea's Seven Booster Box (OP14)", "category": "Booster Box", "image": "The Azure Sea's Seven Booster Box(OP14).jpg", "keywords": ["op14 booster box", "op 14 booster box", "azure sea"]},
    {"id": 4, "name": "Black Bolt Elite Trainer Box", "category": "ETB", "image": "Pokemon Scarlet & Violet Black Bolt Elite Trainer Box .jpeg", "keywords": ["black bolt etb", "elite trainer box"]},
    {"id": 5, "name": "Phantasmal Flames Elite Trainer Box", "category": "ETB", "image": "Phantasmal Flames Elite Trainer Box.jpg", "keywords": ["phantasmal flames etb", "fantasmal flames", "elite trainer box"]},
    {"id": 6, "name": "Surging Sparks Elite Trainer Box", "category": "ETB", "image": "Surging Sparks Elite Trainer Box.jpg", "keywords": ["surging sparks etb", "elite trainer box"]},
    {"id": 7, "name": "Twilight Masquerade Elite Trainer Box", "category": "ETB", "image": "Twilight Masquerade Elite Trainer Box.jpg", "keywords": ["twilight masquerade etb", "twilight", "elite trainer box"]},
    {"id": 8, "name": "White Flare Elite Trainer Box", "category": "ETB", "image": "White Flare Elite Trainer Box.jpg", "keywords": ["white flare etb", "elite trainer box"]},
    {"id": 9, "name": "Black Bolt Booster Bundle", "category": "Booster Bundle", "image": "Black Bolt Booster Bundle.jpg", "keywords": ["black bolt booster bundle", "booster bundle"]},
    {"id": 10, "name": "Mega Evolution Booster Bundle", "category": "Booster Bundle", "image": "Mega Evolution Booster Bundle .webp", "keywords": ["mega evolution booster bundle", "booster bundle"]},
    {"id": 11, "name": "Phantasmal Flames Booster Bundle", "category": "Booster Bundle", "image": "Phantasmal Flames Booster Bundle.jpg", "keywords": ["phantasmal flames booster bundle", "booster bundle"]},
    {"id": 12, "name": "Prismatic Evolutions Booster Bundle", "category": "Booster Bundle", "image": "Prismatic Evolutions Booster Bundle.jpg", "keywords": ["prismatic evolutions booster bundle", "booster bundle"]},
    {"id": 13, "name": "Shrouded Fable Booster Bundle", "category": "Booster Bundle", "image": "Shrouded Fable Booster Bundle.jpg", "keywords": ["shrouded fable booster bundle", "booster bundle"]},
    {"id": 14, "name": "Surging Sparks Booster Bundle", "category": "Booster Bundle", "image": "Surging Sparks Booster Bundle.jpg", "keywords": ["surging sparks booster bundle", "booster bundle"]},
    {"id": 15, "name": "Armarouge ex Premium Collection", "category": "Premium Collection", "image": "Armarouge ex Premium Collection.jpg", "keywords": ["armarouge", "premium collection"]},
    {"id": 16, "name": "Hydreigon ex & Dragapult ex Premium Collection", "category": "Premium Collection", "image": "Hydreigon ex & Dragapult ex Premium Collection.jpg", "keywords": ["hydreigon", "dragapult", "premium collection"]},
    {"id": 17, "name": "Mega Lucario ex Premium Figure Collection", "category": "Premium Collection", "image": "Mega Lucario ex Premium Figure Collection.jpg", "keywords": ["mega lucario", "figure collection"]},
    {"id": 18, "name": "Mega Venusaur ex Premium Collection", "category": "Premium Collection", "image": "Mega Venusaur ex Premium Collection.jpg", "keywords": ["mega venusaur", "premium collection"]},
    {"id": 19, "name": "Prismatic Evolutions Premium Figure Collection", "category": "Premium Collection", "image": "Prismatic Evolutions Premium Figure Collection.jpg", "keywords": ["prismatic evolutions", "premium figure collection"]},
    {"id": 20, "name": "Unova Heavy Hitters Premium Collection", "category": "Premium Collection", "image": "Unova Heavy Hitters Premium Collection.jpg", "keywords": ["unova heavy hitters", "premium collection"]},
    {"id": 21, "name": "Phantasmal Flames 3 Pack Blister", "category": "3 Pack Blister", "image": "Phantasmal Flames 3 Pack Blister _Sneasel_.jpg", "keywords": ["3 pack blister", "phantasmal flames", "blister"]},
    {"id": 22, "name": "Pokeball Tin", "category": "Tin", "image": "Pokeball Tin.webp", "keywords": ["poke ball tin", "pokeball tin"]},
    {"id": 23, "name": "Mega Heroes Mini Tin", "category": "Tin", "image": "Mega Heroes Mini Tin.jpg", "keywords": ["mega heroes mini tin", "mini tin"]},
    {"id": 24, "name": "Prismatic Evolutions Mini Tin", "category": "Tin", "image": "Prismatic Evolutions Mini Tin.jpg", "keywords": ["prismatic evolutions mini tin", "mini tin"]},
    {"id": 25, "name": "Luffy Parallel OP-13-118", "category": "Singles", "image": "Monkey.D.Luffy (118) (Parallel) - Carrying On His Will (OP13).jpg", "keywords": ["luffy parallel", "op-13-118", "op13-118", "luffy 118"]},
    {"id": 26, "name": "Ace Parallel OP-13-119", "category": "Singles", "image": "Portgas.D.Ace (119) (Parallel) - Carrying On His Will (OP13).jpg", "keywords": ["ace parallel", "op13-119", "op-13-119", "ace 119"]},
]

with Session(whatnot_engine) as session:
    # Check if catalog already has items
    existing_count = len(session.exec(select(ProductCatalog)).all())

    if existing_count > 0:
        print(f"\n⚠️  WARNING: Catalog already has {existing_count} items!")
        response = input("   Clear existing items and re-import? (yes/no): ")
        if response.lower() != 'yes':
            print("\n❌ Migration cancelled")
            sys.exit(0)

        # Clear existing
        for item in session.exec(select(ProductCatalog)).all():
            session.delete(item)
        session.commit()
        print(f"   ✅ Cleared {existing_count} existing items")

    print(f"\n📋 Importing {len(existing_items)} catalog items...\n")

    # Add each item
    for item_data in existing_items:
        # Build full URL
        encoded_filename = item_data['image'].replace(' ', '%20')
        full_url = base_url + encoded_filename

        catalog_item = ProductCatalog(
            name=item_data['name'],
            category=item_data['category'],
            image_url=full_url,
            image_filename=item_data['image'],
            keywords=item_data['keywords'],
            sales_count=0,
            total_revenue=Decimal("0")
        )

        session.add(catalog_item)

        print(f"   [{item_data['category']:20s}] {item_data['name']}")

    session.commit()
    print(f"\n✅ Successfully imported {len(existing_items)} items!")

# Verify
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

with Session(whatnot_engine) as session:
    items = session.exec(select(ProductCatalog)).all()

    print(f"\n✅ Database now has {len(items)} catalog items\n")

    # Group by category
    by_category = {}
    for item in items:
        if item.category not in by_category:
            by_category[item.category] = []
        by_category[item.category].append(item.name)

    for category, names in sorted(by_category.items()):
        print(f"   {category}: {len(names)} items")

print("\n" + "=" * 80)
print("✅ Migration complete! Restart the server to see changes.")
print("=" * 80)
