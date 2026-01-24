#!/usr/bin/env python3
"""Delete all auto-generated COGS rules."""
import requests

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453"}

# Get all rules
response = requests.get(f"{url_base}/cogs-rules", headers=headers)
rules = response.json()

print(f"Found {len(rules)} total COGS rules\n")

# Delete all auto-generated rules (those ending with "- Auto-generated")
deleted = 0
for rule in rules:
    if "Auto-generated" in rule['rule_name']:
        rule_id = rule['id']
        del_response = requests.delete(f"{url_base}/cogs-rules/{rule_id}", headers=headers)
        if del_response.status_code == 200:
            print(f"✓ Deleted: {rule['rule_name']}")
            deleted += 1
        else:
            print(f"✗ Failed to delete: {rule['rule_name']}")

print(f"\n✅ Deleted {deleted} auto-generated rules")
print(f"You can now add your own custom rules based on your default values!")
