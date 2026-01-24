#!/usr/bin/env python3
"""Add more COGS rules for top unmatched products."""
import requests

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453", "Content-Type": "application/json"}

additional_rules = [
    {
        "rule_name": "Sleeved Booster Pack - Auto-generated",
        "keywords": ["sleeved booster pack"],
        "cogs_amount": 5.00,
        "match_type": "contains",
        "priority": 88,
        "is_active": True,
        "category": "Booster Packs",
        "notes": "Individual sleeved booster packs (Destined Rivals, Phantasmal Flames, etc.)"
    },
    {
        "rule_name": "Booster Box - Auto-generated",
        "keywords": ["booster box"],
        "cogs_amount": 90.00,
        "match_type": "contains",
        "priority": 95,  # Higher priority than "booster bundle"
        "is_active": True,
        "category": "Sealed Products - Premium",
        "notes": "Full booster boxes (36 packs typically)"
    },
    {
        "rule_name": "Parallel Cards - Auto-generated",
        "keywords": ["parallel"],
        "cogs_amount": 25.00,
        "match_type": "contains",
        "priority": 82,
        "is_active": True,
        "category": "One Piece Cards - High Value",
        "notes": "Parallel rare cards (Luffy, Ace, etc.)"
    },
    {
        "rule_name": "3 Pack Blister - Auto-generated",
        "keywords": ["3 pack blister", "3-pack blister"],
        "cogs_amount": 12.00,
        "match_type": "contains",
        "priority": 87,
        "is_active": True,
        "category": "Sealed Products",
        "notes": "3-pack blister packs"
    },
    {
        "rule_name": "Single Pack Blister - Auto-generated",
        "keywords": ["single pack blister", "1 pack blister"],
        "cogs_amount": 5.00,
        "match_type": "contains",
        "priority": 86,
        "is_active": True,
        "category": "Sealed Products",
        "notes": "Single pack blister packs"
    },
    {
        "rule_name": "2 Pack Products - Auto-generated",
        "keywords": ["2 pack", "2-pack"],
        "cogs_amount": 8.00,
        "match_type": "contains",
        "priority": 84,
        "is_active": True,
        "category": "Sealed Products",
        "notes": "2-pack products (Paldean Fates, etc.)"
    },
    {
        "rule_name": "Sleeve Packs - Auto-generated",
        "keywords": ["sleeve - 1 pack", "mega evolutions sleeve"],
        "cogs_amount": 4.00,
        "match_type": "contains",
        "priority": 83,
        "is_active": True,
        "category": "Accessories",
        "notes": "Single pack sleeves"
    }
]

print("Adding additional COGS rules...\n")
created = 0

for rule in additional_rules:
    response = requests.post(f"{url_base}/cogs-rules", headers=headers, json=rule)
    if response.status_code in [200, 201]:
        result = response.json()
        created += 1
        print(f"✓ Created: {rule['rule_name']}")
        print(f"  Keywords: {', '.join(rule['keywords'])}")
        print(f"  COGS: ${rule['cogs_amount']:.2f}")
        print(f"  Priority: {rule['priority']}\n")
    else:
        print(f"✗ Failed: {rule['rule_name']}")
        print(f"  Error: {response.text}\n")

print(f"Done! Created {created} additional rules.")
print(f"Total rules now: {11 + created}")
