#!/usr/bin/env python3
"""Add rules for Premium Collections and Collection boxes."""
import requests
import json

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453", "Content-Type": "application/json"}

additional_rules = [
    {
        "rule_name": "Premium Collection - Auto-generated",
        "keywords": ["premium collection"],
        "cogs_amount": 35.00,
        "match_type": "contains",
        "priority": 68,
        "is_active": True,
        "category": "Collections",
        "notes": "Premium ex Collections (Hydreigon, Armarouge, etc.)"
    },
    {
        "rule_name": "Collection Box/Chest - Auto-generated",
        "keywords": ["collection lunch box", "collection chest", "lunch box"],
        "cogs_amount": 18.00,
        "match_type": "contains",
        "priority": 67,
        "is_active": True,
        "category": "Collections",
        "notes": "Collection lunch boxes and chests"
    }
]

print("Adding Premium Collection rules...\n")

for rule in additional_rules:
    response = requests.post(f"{url_base}/cogs-rules", headers=headers, json=rule)
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✓ Created: {rule['rule_name']}")
        print(f"  Keywords: {', '.join(rule['keywords'])}")
        print(f"  COGS: ${rule['cogs_amount']:.2f}")
        print(f"  ID: {result.get('id')}\n")
    else:
        print(f"✗ Failed: {rule['rule_name']}")
        print(f"  Error: {response.text}\n")

print("Done!")
