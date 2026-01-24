#!/usr/bin/env python3
"""
Import all 23 WhatNot shows from the 3 Excel files via API.
November 2025: 1 show
December 2025: 14 shows
January 2026: 8 shows
Total: 23 shows
"""
import requests
import pandas as pd
from datetime import datetime
import time

API_BASE = "http://localhost:8000/api/v1/admin/whatnot"
HEADERS = {"Authorization": "Bearer 1453"}

print("=" * 70)
print("IMPORT ALL SHOWS VIA API")
print("=" * 70)

files = [
    {
        'path': '/Users/sahcihansahin/Downloads/Nov 2025 - WhatNot Stream Sales .xlsx',
        'name': 'November 2025',
        'expected_sheets': 1
    },
    {
        'path': '/Users/sahcihansahin/Downloads/Dec 2025 - WhatNot Stream Sales .xlsx',
        'name': 'December 2025',
        'expected_sheets': 14
    },
    {
        'path': '/Users/sahcihansahin/Downloads/Jan 2026 - WhatNot Stream Sales .xlsx',
        'name': 'January 2026',
        'expected_sheets': 8
    }
]

all_imports = []
total_imported = 0
total_skipped = 0
total_errors = 0

for file_info in files:
    print(f"\n{'=' * 70}")
    print(f"Processing: {file_info['name']}")
    print(f"{'=' * 70}")

    try:
        xl_file = pd.ExcelFile(file_info['path'])
        sheet_names = xl_file.sheet_names

        print(f"Found {len(sheet_names)} sheets (expected {file_info['expected_sheets']})")

        for i, sheet_name in enumerate(sheet_names, 1):
            print(f"\n[{i}/{len(sheet_names)}] Importing sheet: {sheet_name}")

            # Parse show date from sheet name
            # Sheet name format: MDDYYYY (e.g., 112025 = 11/1/2025)
            try:
                if len(sheet_name) == 6:  # MDDYY
                    month = int(sheet_name[0])
                    day = int(sheet_name[1:3])
                    year = 2000 + int(sheet_name[3:5])
                elif len(sheet_name) == 7:  # MMDDYYY or MDDYYYY
                    if sheet_name[1].isdigit() and sheet_name[2].isdigit() and not sheet_name[3].isdigit():
                        # MMDDYYY
                        month = int(sheet_name[0:2])
                        day = int(sheet_name[2:4])
                        year = int(sheet_name[4:7])
                    else:
                        # MDDYYYY
                        month = int(sheet_name[0])
                        day = int(sheet_name[1:3])
                        year = int(sheet_name[3:7])
                elif len(sheet_name) == 8:  # MMDDYYYY
                    month = int(sheet_name[0:2])
                    day = int(sheet_name[2:4])
                    year = int(sheet_name[4:8])
                else:
                    print(f"   ⚠️  Unexpected sheet name format: {sheet_name}")
                    month, day, year = 1, 1, 2025

                show_date = f"{year}-{month:02d}-{day:02d}"
            except Exception as e:
                print(f"   ⚠️  Error parsing date from '{sheet_name}': {e}")
                show_date = "2025-01-01"

            # Get show name from first row
            first_row = pd.read_excel(file_info['path'], sheet_name=sheet_name, header=None, nrows=1)
            show_name = str(first_row.iloc[0, 0]) if not pd.isna(first_row.iloc[0, 0]) else f"Show {sheet_name}"

            print(f"   Date: {show_date}")
            print(f"   Name: {show_name[:50]}")

            # Upload via API
            try:
                with open(file_info['path'], 'rb') as f:
                    files_payload = {
                        'file': (file_info['path'].split('/')[-1], f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    }
                    data = {
                        'show_date': show_date,
                        'show_name': show_name,
                        'sheet_name': sheet_name
                    }

                    response = requests.post(
                        f"{API_BASE}/import/excel",
                        headers=HEADERS,
                        files=files_payload,
                        data=data
                    )

                    if response.status_code == 200:
                        result = response.json()
                        print(f"   ✅ Success!")
                        print(f"      Show ID: {result.get('show_id')}")
                        print(f"      Imported: {result.get('imported', 0)} transactions")
                        print(f"      Skipped: {result.get('skipped', 0)} rows")

                        total_imported += result.get('imported', 0)
                        total_skipped += result.get('skipped', 0)

                        all_imports.append({
                            'sheet': sheet_name,
                            'file': file_info['name'],
                            'show_date': show_date,
                            'show_name': show_name,
                            'show_id': result.get('show_id'),
                            'imported': result.get('imported', 0),
                            'skipped': result.get('skipped', 0),
                            'success': True
                        })
                    else:
                        print(f"   ❌ API Error: {response.status_code}")
                        print(f"      {response.text[:200]}")
                        total_errors += 1

                        all_imports.append({
                            'sheet': sheet_name,
                            'file': file_info['name'],
                            'error': f"HTTP {response.status_code}: {response.text[:100]}",
                            'success': False
                        })

            except Exception as e:
                print(f"   ❌ Error uploading: {e}")
                total_errors += 1
                all_imports.append({
                    'sheet': sheet_name,
                    'file': file_info['name'],
                    'error': str(e),
                    'success': False
                })

            # Small delay to avoid overwhelming the server
            time.sleep(0.5)

    except Exception as e:
        print(f"\n❌ Error reading {file_info['name']}: {e}")
        total_errors += 1

# Summary
print("\n" + "=" * 70)
print("IMPORT SUMMARY")
print("=" * 70)

successful_imports = [r for r in all_imports if r.get('success', False)]
failed_imports = [r for r in all_imports if not r.get('success', False)]

print(f"\n📊 Overall Statistics:")
print(f"   Total sheets processed: {len(all_imports)}")
print(f"   Successful imports: {len(successful_imports)}")
print(f"   Failed imports: {len(failed_imports)}")
print(f"   Total transactions imported: {total_imported}")
print(f"   Total rows skipped: {total_skipped}")

print(f"\n📋 By File:")
for file_info in files:
    file_sheets = [r for r in successful_imports if r.get('file') == file_info['name']]
    file_transactions = sum(r.get('imported', 0) for r in file_sheets)
    print(f"\n   {file_info['name']}: {len(file_sheets)} shows imported")
    print(f"      Transactions: {file_transactions}")

if failed_imports:
    print(f"\n❌ Failed Imports ({len(failed_imports)}):")
    for imp in failed_imports:
        print(f"   - {imp['sheet']}: {imp.get('error', 'Unknown error')}")

# Verify final show count
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

try:
    response = requests.get(f"{API_BASE}/shows", headers=HEADERS)
    if response.status_code == 200:
        shows = response.json()
        print(f"\n✅ Database now has {len(shows)} shows")
        print(f"   Expected: 23 shows")

        if len(shows) == 23:
            print(f"\n🎉 SUCCESS! All 23 shows imported correctly!")
        else:
            print(f"\n⚠️  WARNING: Show count mismatch!")
            print(f"   Got {len(shows)}, expected 23")
    else:
        print(f"\n❌ Could not verify - API error: {response.status_code}")
except Exception as e:
    print(f"\n❌ Could not verify: {e}")

print("\n" + "=" * 70)
