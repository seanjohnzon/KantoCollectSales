#!/usr/bin/env python3
"""
Clean database and import all WhatNot sales from scratch.

November 2025: 1 show
December 2025: 14 shows
January 2026: 8 shows
Total: 23 shows
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, select
from app.core.whatnot_database import whatnot_engine
from app.models.whatnot import (
    WhatnotShow, SalesTransaction, WhatnotProduct,
    WhatnotBuyer, COGSMappingRule
)
import pandas as pd
from datetime import datetime

print("="*70)
print("CLEAN DATABASE AND IMPORT ALL SHOWS")
print("="*70)

# Step 1: Clean existing data
print("\n📋 Step 1: Cleaning existing data...")
with Session(whatnot_engine) as session:
    # Count existing data
    existing_shows = session.exec(select(WhatnotShow)).all()
    existing_transactions = session.exec(select(SalesTransaction)).all()
    existing_products = session.exec(select(WhatnotProduct)).all()
    existing_buyers = session.exec(select(WhatnotBuyer)).all()

    print(f"   Found {len(existing_shows)} existing shows")
    print(f"   Found {len(existing_transactions)} existing transactions")
    print(f"   Found {len(existing_products)} existing products")
    print(f"   Found {len(existing_buyers)} existing buyers")

    # Delete all (cascade will handle transactions)
    for show in existing_shows:
        session.delete(show)
    for transaction in existing_transactions:
        session.delete(transaction)
    for product in existing_products:
        session.delete(product)
    for buyer in existing_buyers:
        session.delete(buyer)

    session.commit()
    print("   ✅ Database cleaned!")

# Step 2: Analyze Excel files
print("\n📋 Step 2: Analyzing Excel files...")

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

all_sheets = []
for file_info in files:
    try:
        xl_file = pd.ExcelFile(file_info['path'])
        sheet_names = xl_file.sheet_names
        print(f"\n   {file_info['name']}:")
        print(f"      Path: {file_info['path']}")
        print(f"      Expected sheets: {file_info['expected_sheets']}")
        print(f"      Found sheets: {len(sheet_names)}")
        print(f"      Sheet names: {sheet_names}")

        if len(sheet_names) != file_info['expected_sheets']:
            print(f"      ⚠️  WARNING: Sheet count mismatch!")

        for sheet_name in sheet_names:
            all_sheets.append({
                'file': file_info['path'],
                'file_name': file_info['name'],
                'sheet_name': sheet_name
            })
    except Exception as e:
        print(f"   ❌ Error reading {file_info['name']}: {e}")

print(f"\n   📊 Total sheets to import: {len(all_sheets)}")
print(f"   Expected: 23 sheets (1 + 14 + 8)")

if len(all_sheets) != 23:
    print(f"   ⚠️  WARNING: Total sheet count ({len(all_sheets)}) doesn't match expected (23)!")
    response = input("   Continue anyway? (y/n): ")
    if response.lower() != 'y':
        print("   Aborted.")
        sys.exit(1)

# Step 3: Import all sheets
print("\n📋 Step 3: Importing all sheets...")

import_results = []

for i, sheet_info in enumerate(all_sheets, 1):
    print(f"\n   [{i}/{len(all_sheets)}] Importing: {sheet_info['sheet_name']}")
    print(f"      File: {sheet_info['file_name']}")

    try:
        # Read the sheet
        df = pd.read_excel(sheet_info['file'], sheet_name=sheet_info['sheet_name'], header=1)

        # Get show name from first row, first cell
        first_row = pd.read_excel(sheet_info['file'], sheet_name=sheet_info['sheet_name'], header=None, nrows=1)
        show_name = str(first_row.iloc[0, 0]) if not pd.isna(first_row.iloc[0, 0]) else f"Show {sheet_info['sheet_name']}"

        # Parse show date from sheet name
        # Sheet name format: MDDYYYY (e.g., 112025 = 11/1/2025)
        sheet_name = sheet_info['sheet_name']
        if len(sheet_name) >= 6:  # At least MDDYY
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
                    raise ValueError(f"Unexpected sheet name format: {sheet_name}")

                show_date = datetime(year, month, day).date()
            except Exception as e:
                print(f"      ⚠️  Error parsing date from '{sheet_name}': {e}")
                print(f"      Using default date: 2025-01-01")
                show_date = datetime(2025, 1, 1).date()
        else:
            print(f"      ⚠️  Sheet name too short: '{sheet_name}'")
            show_date = datetime(2025, 1, 1).date()

        total_rows = len(df)
        valid_rows = 0
        skipped_rows = 0

        # Count valid rows (rows with Item Name, Date, and Buyer)
        for idx, row in df.iterrows():
            if (not pd.isna(row.get('Item Name')) and
                str(row.get('Item Name')).strip() != '' and
                not pd.isna(row.get('Date')) and
                not pd.isna(row.get('Buyer')) and
                str(row.get('Buyer')).strip() != ''):
                valid_rows += 1
            else:
                skipped_rows += 1

        result = {
            'sheet': sheet_info['sheet_name'],
            'file': sheet_info['file_name'],
            'show_name': show_name[:50] + '...' if len(show_name) > 50 else show_name,
            'show_date': show_date,
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'skipped_rows': skipped_rows
        }
        import_results.append(result)

        print(f"      Show: {result['show_name']}")
        print(f"      Date: {show_date}")
        print(f"      Total rows: {total_rows}")
        print(f"      Valid rows: {valid_rows}")
        print(f"      Skipped rows: {skipped_rows}")

    except Exception as e:
        print(f"      ❌ Error: {e}")
        import_results.append({
            'sheet': sheet_info['sheet_name'],
            'file': sheet_info['file_name'],
            'error': str(e)
        })

# Step 4: Summary
print("\n" + "="*70)
print("IMPORT SUMMARY")
print("="*70)

print("\n📊 By File:")
for file_info in files:
    file_sheets = [r for r in import_results if r.get('file') == file_info['name']]
    total_valid = sum(r.get('valid_rows', 0) for r in file_sheets)
    total_skipped = sum(r.get('skipped_rows', 0) for r in file_sheets)
    print(f"\n   {file_info['name']}: {len(file_sheets)} sheets")
    print(f"      Valid transactions: {total_valid}")
    print(f"      Skipped rows: {total_skipped}")

total_sheets = len([r for r in import_results if 'error' not in r])
total_errors = len([r for r in import_results if 'error' in r])
total_valid_transactions = sum(r.get('valid_rows', 0) for r in import_results)
total_skipped = sum(r.get('skipped_rows', 0) for r in import_results)

print(f"\n📈 Overall:")
print(f"   Total sheets analyzed: {len(import_results)}")
print(f"   Successful: {total_sheets}")
print(f"   Errors: {total_errors}")
print(f"   Total valid transactions: {total_valid_transactions}")
print(f"   Total skipped rows: {total_skipped}")

if total_errors > 0:
    print(f"\n❌ Errors encountered:")
    for result in import_results:
        if 'error' in result:
            print(f"   - {result['sheet']}: {result['error']}")

print("\n" + "="*70)
print("Ready to import via API? This was just a dry run to verify the data.")
print("="*70)
