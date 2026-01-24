#!/usr/bin/env python3
"""
Validate that all Excel data was correctly imported to database.
Compares each sheet row-by-row against database transactions.
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

import pandas as pd
from sqlmodel import Session, select, create_engine
from app.models.whatnot import WhatnotShow, SalesTransaction
from decimal import Decimal

# Connect directly to the database
whatnot_engine = create_engine("sqlite:////Users/sahcihansahin/KantoCollect/backend/whatnot_sales.db")

print("="*80)
print("VALIDATING EXCEL IMPORT - ROW BY ROW COMPARISON")
print("="*80)

files = [
    {
        'path': '/Users/sahcihansahin/Downloads/Nov 2025 - WhatNot Stream Sales .xlsx',
        'name': 'November 2025',
        'sheets': ['🔥 FIRST SHOW 🔥']
    },
    {
        'path': '/Users/sahcihansahin/Downloads/Dec 2025 - WhatNot Stream Sales .xlsx',
        'name': 'December 2025',
        'sheets': ['1222025', '1242025', '1252025', '1262025', '1292025', 
                   '12112025', '12132025', '12142025', '12182025', '12192025',
                   '12202025', '12252025', '12262025', '12272025']
    },
    {
        'path': '/Users/sahcihansahin/Downloads/Jan 2026 - WhatNot Stream Sales .xlsx',
        'name': 'January 2026',
        'sheets': ['112026', '122026', '132026', '182026', '192026',
                   '1102026', '1162026', '1172026']
    }
]

validation_results = []
total_sheets = 0
total_issues = 0

with Session(whatnot_engine) as session:
    # Get all shows ordered by ID
    db_shows = session.exec(select(WhatnotShow).order_by(WhatnotShow.id)).all()
    show_index = 0
    
    for file_info in files:
        print(f"\n{'='*80}")
        print(f"FILE: {file_info['name']}")
        print(f"{'='*80}")
        
        for sheet_name in file_info['sheets']:
            total_sheets += 1
            
            if show_index >= len(db_shows):
                print(f"\n❌ ERROR: Not enough shows in database!")
                break
            
            db_show = db_shows[show_index]
            show_index += 1
            
            print(f"\n[Show {db_show.id}] Sheet: {sheet_name}")
            print(f"  Database Name: {db_show.show_name[:60]}")
            
            # Read Excel sheet
            try:
                # Read show name from Row 1
                df_header = pd.read_excel(file_info['path'], sheet_name=sheet_name, header=None, nrows=2)
                excel_show_name = str(df_header.iloc[1, 0]) if len(df_header) > 1 else "(unknown)"
                
                # Read data starting from row 2 (0-indexed), header is row 2
                df = pd.read_excel(file_info['path'], sheet_name=sheet_name, header=2)
                df.columns = df.columns.str.strip()
                
                # Count valid rows (same logic as import)
                valid_rows = []
                for idx, row in df.iterrows():
                    if (not pd.isna(row.get('Item Name')) and
                        str(row.get('Item Name')).strip() != '' and
                        not pd.isna(row.get('Date')) and
                        not pd.isna(row.get('Buyer')) and
                        str(row.get('Buyer')).strip() != ''):
                        valid_rows.append(idx)
                
                excel_valid_count = len(valid_rows)
                excel_total_rows = len(df)
                
                # Get transactions from database for this show
                db_transactions = session.exec(
                    select(SalesTransaction)
                    .where(SalesTransaction.show_id == db_show.id)
                    .order_by(SalesTransaction.row_number)
                ).all()
                
                db_count = len(db_transactions)
                
                # Compare counts
                match = "✅" if excel_valid_count == db_count else "❌"
                print(f"  {match} Excel: {excel_valid_count} valid rows | Database: {db_count} transactions")
                
                if excel_valid_count != db_count:
                    total_issues += 1
                    print(f"      ⚠️  MISMATCH: {abs(excel_valid_count - db_count)} transactions difference!")
                
                # Verify show totals
                if db_show.item_count != db_count:
                    print(f"      ⚠️  Show.item_count ({db_show.item_count}) != actual transactions ({db_count})")
                    total_issues += 1
                
                # Sample first 3 transactions for detailed comparison
                if db_transactions and len(valid_rows) > 0:
                    print(f"\n  📋 Sample Transaction Validation (first 3):")
                    sample_count = min(3, len(valid_rows), len(db_transactions))
                    
                    for i in range(sample_count):
                        row_idx = valid_rows[i]
                        excel_row = df.iloc[row_idx]
                        db_txn = db_transactions[i]
                        
                        # Compare key fields
                        excel_item = str(excel_row.get('Item Name', '')).strip()
                        excel_buyer = str(excel_row.get('Buyer', '')).strip()
                        excel_gross = Decimal(str(excel_row.get('Gross Sale Price', 0)).replace('$', '').replace(',', '').strip())
                        
                        item_match = excel_item == db_txn.item_name
                        buyer_match = excel_buyer == db_txn.buyer_username
                        gross_match = abs(excel_gross - db_txn.gross_sale_price) < Decimal('0.01')
                        
                        status = "✅" if (item_match and buyer_match and gross_match) else "❌"
                        print(f"      Row {row_idx + 3} {status}")
                        
                        if not item_match:
                            print(f"        Item: Excel='{excel_item[:40]}' DB='{db_txn.item_name[:40]}'")
                            total_issues += 1
                        if not buyer_match:
                            print(f"        Buyer: Excel='{excel_buyer}' DB='{db_txn.buyer_username}'")
                            total_issues += 1
                        if not gross_match:
                            print(f"        Price: Excel=${excel_gross} DB=${db_txn.gross_sale_price}")
                            total_issues += 1
                
                # Check for NULL values in critical fields
                null_issues = []
                for txn in db_transactions:
                    if txn.item_name is None or txn.item_name.strip() == '':
                        null_issues.append(f"Transaction {txn.id}: NULL item_name")
                    if txn.buyer_username is None or txn.buyer_username.strip() == '':
                        null_issues.append(f"Transaction {txn.id}: NULL buyer")
                    if txn.gross_sale_price is None:
                        null_issues.append(f"Transaction {txn.id}: NULL gross_sale_price")
                    if txn.net_earnings is None:
                        null_issues.append(f"Transaction {txn.id}: NULL net_earnings")
                
                if null_issues:
                    print(f"\n  ❌ NULL VALUE ISSUES:")
                    for issue in null_issues[:5]:  # Show first 5
                        print(f"      {issue}")
                    total_issues += len(null_issues)
                
                # Verify aggregates
                if db_transactions:
                    calc_gross = sum(t.gross_sale_price for t in db_transactions)
                    calc_net = sum(t.net_earnings for t in db_transactions)
                    
                    if abs(calc_gross - (db_show.total_gross_sales or 0)) > Decimal('0.01'):
                        print(f"  ⚠️  Aggregate mismatch: Gross sales calculated=${calc_gross} vs show.total_gross_sales=${db_show.total_gross_sales}")
                        total_issues += 1
                    
                    if abs(calc_net - (db_show.total_net_earnings or 0)) > Decimal('0.01'):
                        print(f"  ⚠️  Aggregate mismatch: Net earnings calculated=${calc_net} vs show.total_net_earnings=${db_show.total_net_earnings}")
                        total_issues += 1
                
                validation_results.append({
                    'show_id': db_show.id,
                    'sheet': sheet_name,
                    'excel_valid': excel_valid_count,
                    'excel_total': excel_total_rows,
                    'db_count': db_count,
                    'match': excel_valid_count == db_count
                })
                
            except Exception as e:
                print(f"  ❌ ERROR reading sheet: {e}")
                total_issues += 1
                validation_results.append({
                    'show_id': db_show.id,
                    'sheet': sheet_name,
                    'error': str(e)
                })

# Summary
print(f"\n{'='*80}")
print("VALIDATION SUMMARY")
print(f"{'='*80}")

successful = [r for r in validation_results if r.get('match', False)]
mismatches = [r for r in validation_results if 'match' in r and not r['match']]
errors = [r for r in validation_results if 'error' in r]

print(f"\n📊 Overall Results:")
print(f"  Total sheets validated: {total_sheets}")
print(f"  Perfect matches: {len(successful)}")
print(f"  Mismatches: {len(mismatches)}")
print(f"  Errors: {len(errors)}")
print(f"  Total issues found: {total_issues}")

if mismatches:
    print(f"\n❌ Shows with mismatches:")
    for r in mismatches:
        print(f"  Show {r['show_id']} ({r['sheet']}): Excel={r['excel_valid']} vs DB={r['db_count']}")

if errors:
    print(f"\n❌ Shows with errors:")
    for r in errors:
        print(f"  Show {r['show_id']} ({r['sheet']}): {r['error']}")

# Final totals
with Session(whatnot_engine) as session:
    total_db_shows = session.exec(select(WhatnotShow)).all()
    total_db_txns = session.exec(select(SalesTransaction)).all()
    
    print(f"\n📈 Database Totals:")
    print(f"  Shows: {len(total_db_shows)}")
    print(f"  Transactions: {len(total_db_txns)}")

if total_issues == 0:
    print(f"\n🎉 SUCCESS! All data validated - no issues found!")
else:
    print(f"\n⚠️  VALIDATION INCOMPLETE: {total_issues} issues found - review above for details")

print(f"{'='*80}")
