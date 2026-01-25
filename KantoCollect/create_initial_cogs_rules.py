#!/usr/bin/env python3
"""Create initial COGS rules based on product name patterns."""
import requests
import json

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453", "Content-Type": "application/json"}

# Initial COGS rules based on observed patterns
rules = [
    {
        "rule_name": "Free Packs - Auto-generated",
        "keywords": ["free pack", "free pokemon"],
        "cogs_amount": 1.00,
        "match_type": "contains",
        "priority": 100,
        "is_active": True,
        "category": "Giveaways",
        "notes": "Free giveaway packs - minimal COGS for tracking"
    },
    {
        "rule_name": "Random Asian Pack - Auto-generated",
        "keywords": ["random asian pack"],
        "cogs_amount": 3.00,
        "match_type": "contains",
        "priority": 95,
        "is_active": True,
        "category": "Random Packs",
        "notes": "Random Asian booster packs"
    },
    {
        "rule_name": "Booster Bundle - Auto-generated",
        "keywords": ["booster bundle"],
        "cogs_amount": 15.00,
        "match_type": "contains",
        "priority": 90,
        "is_active": True,
        "category": "Sealed Products",
        "notes": "Multiple booster packs bundled together"
    },
    {
        "rule_name": "Elite Trainer Box (ETB) - Auto-generated",
        "keywords": [" etb", "elite trainer box"],
        "cogs_amount": 40.00,
        "match_type": "contains",
        "priority": 85,
        "is_active": True,
        "category": "Sealed Products",
        "notes": "Elite Trainer Boxes"
    },
    {
        "rule_name": "Poke Ball Tin - Auto-generated",
        "keywords": ["poke ball tin", "pokeball tin"],
        "cogs_amount": 20.00,
        "match_type": "contains",
        "priority": 80,
        "is_active": True,
        "category": "Tins",
        "notes": "Pokemon Poke Ball themed tins"
    },
    {
        "rule_name": "Plush Collection - Auto-generated",
        "keywords": ["plush collection"],
        "cogs_amount": 25.00,
        "match_type": "contains",
        "priority": 75,
        "is_active": True,
        "category": "Collections",
        "notes": "Plush collections (Jigglypuff, Bulbasaur, etc.)"
    },
    {
        "rule_name": "Figure Collection - Auto-generated",
        "keywords": ["figure collection"],
        "cogs_amount": 30.00,
        "match_type": "contains",
        "priority": 70,
        "is_active": True,
        "category": "Collections",
        "notes": "Figure collections (Mega Lucario, etc.)"
    },
    {
        "rule_name": "Ex Box - Auto-generated",
        "keywords": [" ex box"],
        "cogs_amount": 22.00,
        "match_type": "contains",
        "priority": 65,
        "is_active": True,
        "category": "Pokemon Boxes",
        "notes": "Pokemon ex boxes (Mabosstiff, etc.)"
    },
    {
        "rule_name": "Ultra-Premium Collection (UPC) - Auto-generated",
        "keywords": ["ultra-premium collection", "upc", "ultra premium collection"],
        "cogs_amount": 120.00,
        "match_type": "contains",
        "priority": 60,
        "is_active": True,
        "category": "Premium Products",
        "notes": "High-value Ultra-Premium Collections"
    }
]

print("Creating initial COGS rules...\n")
created = 0
skipped = 0

for rule in rules:
    response = requests.post(f"{url_base}/cogs-rules", headers=headers, json=rule)
    if response.status_code == 200:
        created += 1
        result = response.json()
        print(f"✓ Created: {rule['rule_name']}")
        print(f"  Keywords: {', '.join(rule['keywords'])}")
        print(f"  COGS: ${rule['cogs_amount']:.2f}\n")
    else:
        skipped += 1
        print(f"✗ Failed: {rule['rule_name']} - {response.text}\n")

print(f"\nSummary: {created} rules created, {skipped} skipped")
