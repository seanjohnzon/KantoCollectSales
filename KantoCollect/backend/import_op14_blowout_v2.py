#!/usr/bin/env python3
"""
Import OP14 Blowout show data (Jan 22-23, 2026) - WITH FULL PRODUCT NAMES.
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from decimal import Decimal
from sqlmodel import Session, create_engine, select
from app.models.whatnot import (
    WhatnotShow,
    SalesTransaction,
    WhatnotProduct,
    WhatnotBuyer,
)
from app.services.whatnot.cogs_service import match_cogs_rule

engine = create_engine("sqlite:///./whatnot_sales.db")

# Transaction data with FULL product names
transactions_data = [
    ("op11&op12 japanese", "23-Jan-26", "rthreat41", 3.00, 2.36),
    ("Free Pokemon Pack #11", "23-Jan-26", "hev_day", 0.00, 19.13),
    ("prb01 english", "23-Jan-26", "rthreat41", 22.00, 9.46),
    ("op 12 english", "23-Jan-26", "pokebroz", 11.00, 11.23),
    ("op 10 english", "23-Jan-26", "rthreat41", 13.00, -0.31),
    ("Free Pokemon Pack #10", "23-Jan-26", "callmethebr", 0.00, 15.64),
    ("2x Pack - OP14: Azure Sea's Seven #23", "23-Jan-26", "razzy415", 18.00, 11.22),
    ("2x Pack - OP14: Azure Sea's Seven #22", "23-Jan-26", "collectable_j", 13.00, 15.60),
    ("2x Pack - OP14: Azure Sea's Seven #20", "23-Jan-26", "razzy415", 18.00, 15.64),
    ("2x Pack - OP14: Azure Sea's Seven #19", "23-Jan-26", "rogerbear202", 18.00, -0.78),
    ("Free Pokemon Pack #9", "23-Jan-26", "callmethebr", 0.00, 15.68),
    ("2x Pack - OP14: Azure Sea's Seven #18", "23-Jan-26", "razzy415", 18.00, 12.01),
    ("2x Pack - OP14: Azure Sea's Seven #17", "23-Jan-26", "razzy415", 15.00, -0.78),
    ("Free Pokemon Pack #7", "23-Jan-26", "razzy415", 0.00, 12.98),
    ("2x Pack - OP14: Azure Sea's Seven #16", "23-Jan-26", "menderz3", 15.00, 10.32),
    ("2x Pack - OP14: Azure Sea's Seven #15", "23-Jan-26", "carlos_612", 12.00, -0.78),
    ("Free Pokemon Pack #20", "23-Jan-26", "ahd0820", 0.00, 18.32),
    ("2x Pack - OP13: Carrying On His Will", "23-Jan-26", "shdytcg", 21.00, -0.78),
    ("Free Pokemon Pack #8", "22-Jan-26", "patshu_don", 0.00, 36.07),
    ("2x Pack - OP14: Azure Sea's Seven #12", "22-Jan-26", "carlos27513", 41.00, 35.18),
    ("2x Pack - OP14: Azure Sea's Seven #11", "22-Jan-26", "carlos27513", 40.00, -0.78),
    ("Free Pokemon Pack #6", "22-Jan-26", "raz343434", 0.00, 35.20),
    ("2x Pack - OP14: Azure Sea's Seven #10", "22-Jan-26", "carlos27513", 40.00, 26.33),
    ("2x Pack - OP14: Azure Sea's Seven #9", "22-Jan-26", "carlos27513", 30.00, -0.78),
    ("Free Pokemon Pack #5", "22-Jan-26", "2peace2ay", 0.00, 29.78),
    ("2x Pack - OP14: Azure Sea's Seven #8", "22-Jan-26", "cubletcg", 34.00, 27.28),
    ("2x Pack - OP14: Azure Sea's Seven #7", "22-Jan-26", "anthonykino7", 31.00, -0.78),
    ("Free Pokemon Pack #4", "22-Jan-26", "fabiansai500", 0.00, 29.92),
    ("2x Pack - OP14: Azure Sea's Seven #6", "22-Jan-26", "blockspinnat", 24.00, 17.43),
    ("2x Pack - OP14: Azure Sea's Seven #5", "22-Jan-26", "blockspinnat", 20.00, -0.78),
    ("Free Pokemon Pack #3", "22-Jan-26", "noizecompia", 0.00, 17.43),
    ("2x Pack - OP14: Azure Sea's Seven #4", "22-Jan-26", "josevil39413", 20.00, 16.54),
    ("2x Pack - OP14: Azure Sea's Seven #3", "22-Jan-26", "teej530", 19.00, -1.35),
    ("Free Pokemon Pack #2", "22-Jan-26", "carlos27513", 0.00, 16.53),
    ("2x Pack - OP14: Azure Sea's Seven #1", "22-Jan-26", "carlos27513", 19.00, -0.78),
    ("Free Pokemon Pack #1", "22-Jan-26", "roughcollect", 0.00, 0.00),
]

def parse_date(date_str):
    """Parse '23-Jan-26' to datetime."""
    return datetime.strptime(date_str, "%d-%b-%y")

print("=" * 100)
print("IMPORTING OP14 BLOWOUT SHOW - FULL PRODUCT NAMES")
print("=" * 100)

with Session(engine) as db:
    # Delete existing show if it exists
    existing_show = db.exec(
        select(WhatnotShow).where(WhatnotShow.show_name == "OP14 Blowout")
    ).first()

    if existing_show:
        print(f"\n⚠️  Found existing 'OP14 Blowout' show (ID: {existing_show.id})")
        print("   Deleting old show and re-importing with full product names...")
        db.delete(existing_show)
        db.commit()
        print("   ✓ Deleted old show")

    # Create the show
    show_date = parse_date("22-Jan-26")  # Use earliest date
    show = WhatnotShow(
        show_date=show_date,
        show_name="OP14 Blowout",
        platform="WhatNot",
        imported_at=datetime.utcnow(),
    )
    db.add(show)
    db.flush()  # Get show_id

    print(f"\n✓ Created show: {show.show_name} (ID: {show.id})")
    print(f"  Date: {show.show_date.strftime('%Y-%m-%d')}")

    # Import transactions
    print(f"\n{'#':<4} {'Date':<12} {'Item':<50} {'Buyer':<20} {'Gross':<10} {'Net':<10} {'COGS':<10}")
    print("-" * 100)

    imported_count = 0
    cogs_matched = 0
    total_gross = Decimal("0")
    total_net = Decimal("0")
    total_cogs = Decimal("0")

    for i, (item_name, date_str, buyer_username, gross, net) in enumerate(transactions_data, 1):
        # Parse values
        transaction_date = parse_date(date_str)
        gross_decimal = Decimal(str(gross))
        net_decimal = Decimal(str(net))

        # Get or create product
        normalized_name = item_name.lower().strip()
        product = db.exec(
            select(WhatnotProduct).where(WhatnotProduct.normalized_name == normalized_name)
        ).first()

        if not product:
            product = WhatnotProduct(
                product_name=item_name,
                normalized_name=normalized_name,
                total_quantity_sold=0,
                total_gross_sales=Decimal("0"),
                total_net_earnings=Decimal("0"),
                avg_sale_price=Decimal("0"),
                times_sold=0,
            )
            db.add(product)
            db.flush()

        # Get or create buyer
        buyer = db.exec(
            select(WhatnotBuyer).where(WhatnotBuyer.username == buyer_username)
        ).first()

        if not buyer:
            buyer = WhatnotBuyer(
                username=buyer_username,
                total_purchases=0,
                total_spent=Decimal("0"),
                avg_purchase_price=Decimal("0"),
                first_purchase_date=transaction_date.date() if hasattr(transaction_date, 'date') else transaction_date,
                last_purchase_date=transaction_date.date() if hasattr(transaction_date, 'date') else transaction_date,
            )
            db.add(buyer)
            db.flush()

        # Match COGS rule
        rule_id, cogs_amount = match_cogs_rule(db, normalized_name)

        # Calculate COGS (per unit * quantity)
        quantity = 1
        transaction_cogs = None
        if cogs_amount:
            transaction_cogs = cogs_amount * quantity
            cogs_matched += 1

        # Calculate profit and ROI
        net_profit = None
        roi_percent = None
        if transaction_cogs:
            net_profit = net_decimal - transaction_cogs
            if transaction_cogs > 0:
                roi_percent = (net_profit / transaction_cogs) * 100

        # Create transaction
        transaction = SalesTransaction(
            show_id=show.id,
            transaction_date=transaction_date,
            item_name=item_name,
            quantity=quantity,
            buyer_username=buyer_username,
            gross_sale_price=gross_decimal,
            net_earnings=net_decimal,
            product_id=product.id,
            buyer_id=buyer.id,
            cogs=transaction_cogs,
            net_profit=net_profit,
            roi_percent=roi_percent,
            matched_cogs_rule_id=rule_id,
            sale_type='stream',
        )
        db.add(transaction)

        # Update product aggregates
        product.total_quantity_sold += quantity
        product.total_gross_sales += gross_decimal
        product.total_net_earnings += net_decimal
        product.times_sold += 1
        product.avg_sale_price = product.total_gross_sales / product.total_quantity_sold
        db.add(product)

        # Update buyer aggregates
        buyer.total_purchases += 1
        buyer.total_spent += gross_decimal
        buyer.avg_purchase_price = buyer.total_spent / buyer.total_purchases
        trans_date = transaction_date.date() if hasattr(transaction_date, 'date') else transaction_date
        if trans_date > buyer.last_purchase_date:
            buyer.last_purchase_date = trans_date
        if trans_date < buyer.first_purchase_date:
            buyer.first_purchase_date = trans_date
        db.add(buyer)

        # Track totals
        total_gross += gross_decimal
        total_net += net_decimal
        if transaction_cogs:
            total_cogs += transaction_cogs

        cogs_display = f"${transaction_cogs:.2f}" if transaction_cogs else "-"
        print(f"{i:<4} {date_str:<12} {item_name:<50} {buyer_username:<20} ${gross:>8.2f} ${net:>8.2f} {cogs_display:>9}")
        imported_count += 1

    # Update show totals
    show.item_count = imported_count
    show.total_gross_sales = total_gross
    show.total_net_earnings = total_net
    show.total_cogs = total_cogs
    show.total_net_profit = total_net - total_cogs
    db.add(show)

    db.commit()

    print("-" * 100)
    print(f"{'TOTALS':<87} ${total_gross:>8.2f} ${total_net:>8.2f} ${total_cogs:>8.2f}")

    print("\n" + "=" * 100)
    print("✅ IMPORT COMPLETE - FULL PRODUCT NAMES")
    print("=" * 100)
    print(f"\nShow: {show.show_name} (ID: {show.id})")
    print(f"  Transactions imported: {imported_count}")
    print(f"  COGS auto-assigned: {cogs_matched}/{imported_count} ({cogs_matched/imported_count*100:.1f}%)")
    print(f"  Gross sales: ${total_gross:.2f}")
    print(f"  Net earnings: ${total_net:.2f}")
    print(f"  Total COGS: ${total_cogs:.2f}")
    print(f"  Net profit: ${show.total_net_profit:.2f}")
    print()
