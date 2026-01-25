#!/usr/bin/env python3
"""
Add missing items to the Master Catalog.

This script helps you add the 22 missing products to reach the total of 48.

INSTRUCTIONS:
1. Go to the ImageKit folder and copy all 48 image filenames
2. Paste them in the IMAGEKIT_FILES list below
3. Run this script to generate the updated catalog code

Current catalog has 26 items. We need to add 22 more to reach 48 total.
"""

# ============================================================================
# PASTE ALL 48 IMAGE FILENAMES FROM IMAGEKIT HERE (one per line)
# ============================================================================
IMAGEKIT_FILES = """
Mega Charizard X ex Ultra Premium Collection.jpg
Team Rocket_s Moltres ex Ultra-Premium Collection.jpg
The Azure Sea's Seven Booster Box(OP14).jpg
Pokemon Scarlet & Violet Black Bolt Elite Trainer Box .jpeg
Phantasmal Flames Elite Trainer Box.jpg
Surging Sparks Elite Trainer Box.jpg
Twilight Masquerade Elite Trainer Box.jpg
White Flare Elite Trainer Box.jpg
Black Bolt Booster Bundle.jpg
Mega Evolution Booster Bundle .webp
Phantasmal Flames Booster Bundle.jpg
Prismatic Evolutions Booster Bundle.jpg
Shrouded Fable Booster Bundle.jpg
Surging Sparks Booster Bundle.jpg
Armarouge ex Premium Collection.jpg
Hydreigon ex & Dragapult ex Premium Collection.jpg
Mega Lucario ex Premium Figure Collection.jpg
Mega Venusaur ex Premium Collection.jpg
Prismatic Evolutions Premium Figure Collection.jpg
Unova Heavy Hitters Premium Collection.jpg
Phantasmal Flames 3 Pack Blister _Sneasel_.jpg
Pokeball Tin.webp
Mega Heroes Mini Tin.jpg
Prismatic Evolutions Mini Tin.jpg
Monkey.D.Luffy (118) (Parallel) - Carrying On His Will (OP13).jpg
Portgas.D.Ace (119) (Parallel) - Carrying On His Will (OP13).jpg

ADD THE REMAINING 22 IMAGE FILENAMES HERE...

""".strip()

# ============================================================================
# EXISTING CATALOG (26 items) - DO NOT MODIFY
# ============================================================================
EXISTING_ITEMS = {
    "Mega Charizard X ex Ultra Premium Collection.jpg",
    "Team Rocket_s Moltres ex Ultra-Premium Collection.jpg",
    "The Azure Sea's Seven Booster Box(OP14).jpg",
    "Pokemon Scarlet & Violet Black Bolt Elite Trainer Box .jpeg",
    "Phantasmal Flames Elite Trainer Box.jpg",
    "Surging Sparks Elite Trainer Box.jpg",
    "Twilight Masquerade Elite Trainer Box.jpg",
    "White Flare Elite Trainer Box.jpg",
    "Black Bolt Booster Bundle.jpg",
    "Mega Evolution Booster Bundle .webp",
    "Phantasmal Flames Booster Bundle.jpg",
    "Prismatic Evolutions Booster Bundle.jpg",
    "Shrouded Fable Booster Bundle.jpg",
    "Surging Sparks Booster Bundle.jpg",
    "Armarouge ex Premium Collection.jpg",
    "Hydreigon ex & Dragapult ex Premium Collection.jpg",
    "Mega Lucario ex Premium Figure Collection.jpg",
    "Mega Venusaur ex Premium Collection.jpg",
    "Prismatic Evolutions Premium Figure Collection.jpg",
    "Unova Heavy Hitters Premium Collection.jpg",
    "Phantasmal Flames 3 Pack Blister _Sneasel_.jpg",
    "Pokeball Tin.webp",
    "Mega Heroes Mini Tin.jpg",
    "Prismatic Evolutions Mini Tin.jpg",
    "Monkey.D.Luffy (118) (Parallel) - Carrying On His Will (OP13).jpg",
    "Portgas.D.Ace (119) (Parallel) - Carrying On His Will (OP13).jpg",
}

def clean_filename(filename):
    """Remove file extension and clean up filename."""
    name = filename.rsplit('.', 1)[0]  # Remove extension
    name = name.replace('_s', "'s")  # Fix apostrophes
    name = name.replace('_', ' ')  # Replace underscores with spaces
    return name.strip()

def categorize_product(filename, product_name):
    """Auto-detect product category based on name."""
    name_lower = product_name.lower()

    if 'ultra premium' in name_lower or 'upc' in name_lower:
        return 'UPC'
    elif 'elite trainer box' in name_lower or 'etb' in name_lower:
        return 'ETB'
    elif 'booster bundle' in name_lower:
        return 'Booster Bundle'
    elif 'booster box' in name_lower:
        return 'Booster Box'
    elif 'premium collection' in name_lower or 'premium figure' in name_lower:
        return 'Premium Collection'
    elif 'blister' in name_lower:
        return '3 Pack Blister'
    elif 'tin' in name_lower:
        return 'Tin'
    elif '(' in product_name and ')' in product_name:  # Card numbers like (118)
        return 'Singles'
    elif 'sleeved' in name_lower or 'pack' in name_lower:
        return 'Sleeved Packs'
    elif 'box' in name_lower:
        return 'Box'
    else:
        return 'Other'

def generate_keywords(product_name):
    """Auto-generate search keywords for matching."""
    name_lower = product_name.lower()
    keywords = []

    # Add full name
    keywords.append(name_lower)

    # Extract card numbers (e.g., OP-13-118, OP13-118)
    import re
    card_numbers = re.findall(r'op[-\s]?\d{1,2}[-\s]?\d{3}', name_lower)
    keywords.extend(card_numbers)

    # Add variations of card numbers
    for num in card_numbers:
        # Add with and without hyphens
        keywords.append(num.replace('-', ''))
        keywords.append(num.replace('-', ' '))

    # Add key product words
    important_words = ['mega', 'ex', 'premium', 'elite', 'booster', 'parallel',
                       'charizard', 'pikachu', 'luffy', 'ace', 'zoro']
    for word in important_words:
        if word in name_lower:
            keywords.append(word)

    # Add product type keywords
    if 'etb' in name_lower or 'elite trainer box' in name_lower:
        keywords.append('elite trainer box')
        keywords.append('etb')
    if 'booster bundle' in name_lower:
        keywords.append('booster bundle')
    if 'ultra premium' in name_lower:
        keywords.append('ultra premium')
        keywords.append('upc')

    # Remove duplicates and empty strings
    keywords = list(set([k.strip() for k in keywords if k.strip()]))

    return keywords[:5]  # Limit to 5 most relevant keywords

def main():
    print("=" * 80)
    print("MASTER CATALOG - ADD MISSING ITEMS")
    print("=" * 80)

    # Parse ImageKit files
    files = [line.strip() for line in IMAGEKIT_FILES.split('\n') if line.strip()]
    files = [f for f in files if not f.startswith('ADD THE REMAINING')]

    print(f"\n📋 ImageKit files provided: {len(files)}")
    print(f"📋 Existing catalog items: {len(EXISTING_ITEMS)}")

    # Find missing items
    missing_files = [f for f in files if f not in EXISTING_ITEMS]

    print(f"📋 Missing items to add: {len(missing_files)}")

    if len(files) < 48:
        print(f"\n⚠️  WARNING: You provided {len(files)} files but need 48 total.")
        print("   Please add all 48 image filenames from ImageKit to IMAGEKIT_FILES")
        return

    if len(missing_files) == 0:
        print("\n✅ No missing items! All 48 products are already in the catalog.")
        return

    print(f"\n" + "=" * 80)
    print(f"MISSING ITEMS ({len(missing_files)} products):")
    print("=" * 80)

    # Generate catalog entries for missing items
    next_id = 27  # Current catalog ends at id 26

    print("\n# Add these to the catalog_products list in whatnot.py:\n")

    for filename in missing_files:
        product_name = clean_filename(filename)
        category = categorize_product(filename, product_name)
        keywords = generate_keywords(product_name)

        print(f'    {{"id": {next_id}, "name": "{product_name}", "category": "{category}", "image": "{filename}", "keywords": {keywords}}},')

        next_id += 1

    print(f"\n" + "=" * 80)
    print(f"✅ Generated {len(missing_files)} new catalog entries")
    print(f"✅ Total catalog will have {len(EXISTING_ITEMS) + len(missing_files)} items")
    print("=" * 80)

    print("\nINSTRUCTIONS:")
    print("1. Copy the generated entries above")
    print("2. Open backend/app/api/v1/admin/whatnot.py")
    print("3. Find the catalog_products list (around line 662)")
    print("4. Add the new entries after the existing 26 items")
    print("5. Save and restart the server")

if __name__ == "__main__":
    main()
