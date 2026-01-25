#!/usr/bin/env python3
"""Test import with COGS rules to see auto-assignment."""
import requests

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453"}

# Get existing shows
print("=== Existing Shows ===")
response = requests.get(f"{url_base}/shows?limit=20", headers=headers)
shows = response.json()
for show in shows:
    print(f"ID: {show['id']} | Date: {show['show_date']} | Name: {show['show_name'][:50]}... | Items: {show['item_count']} | COGS: ${show['total_cogs']}")

# Delete test shows (shows 10 and 11 from our tests)
print("\n=== Deleting Test Shows ===")
for show_id in [10, 11]:
    response = requests.delete(f"{url_base}/shows/{show_id}", headers=headers)
    if response.status_code == 200:
        print(f"✓ Deleted show {show_id}")
    else:
        print(f"✗ Failed to delete show {show_id}: {response.text}")

# Re-import with COGS rules active
print("\n=== Re-importing with COGS Rules ===")
excel_file = "/Users/sahcihansahin/Downloads/Jan 2026 - WhatNot Stream Sales .xlsx"
with open(excel_file, 'rb') as f:
    files = {'file': ('test.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    response = requests.post(f"{url_base}/import/excel", headers=headers, files=files)

result = response.json()
print(f"\nStatus Code: {response.status_code}")
print(f"Total Rows: {result['total_rows']}")
print(f"Imported: {result['imported']}")
print(f"Skipped: {result['skipped']}")
print(f"Errors: {len(result['errors'])}")
print(f"✅ COGS Assigned: {result['cogs_assigned_count']}")
print(f"⚠️  COGS Missing: {result['cogs_missing_count']}")
print(f"\n📊 COGS Coverage: {(result['cogs_assigned_count'] / result['imported'] * 100):.1f}%")

# Show warnings for missing COGS
if result['cogs_missing_count'] > 0:
    print(f"\n=== Products Needing COGS Rules ===")
    missing_products = set()
    for warning in result['warnings']:
        if "No COGS rule matched" in warning:
            # Extract product name from warning
            parts = warning.split("'")
            if len(parts) >= 2:
                product = parts[1]
                missing_products.add(product)

    for product in sorted(missing_products)[:10]:
        print(f"  • {product}")

    if len(missing_products) > 10:
        print(f"  ... and {len(missing_products) - 10} more")
