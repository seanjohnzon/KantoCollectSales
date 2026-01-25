#!/usr/bin/env python3
"""
Import marketplace orders (Destined Rivals Sleeved Booster Pack).
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from decimal import Decimal
from sqlmodel import Session, create_engine, select
from app.models.whatnot import (
    SalesTransaction,
    WhatnotProduct,
    WhatnotBuyer,
)
from app.services.whatnot.cogs_service import match_cogs_rule

engine = create_engine("sqlite:///./whatnot_sales.db")

# Marketplace orders data
marketplace_orders = [
    ("Destined Rivals Sleeved Booster Pack", "jimmyang", 10.00, 8.57),
    ("Destined Rivals Sleeved Booster Pack", "jimmyang", 10.00, 8.46),
    ("Destined Rivals Sleeved Booster Pack", "worharle", 10.00, 8.58),
    ("Destined Rivals Sleeved Booster Pack", "worharle", 10.00, 8.47),
    ("Destined Rivals Sleeved Booster Pack", "tammygil", 10.00, 8.58),
    ("Destined Rivals Sleeved Booster Pack", "tammygil", 10.00, 8.45),
]

print("=" * 80)
print("IMPORTING MARKETPLACE ORDERS")
print("=" * 80)

with Session(engine) as db:
    # Use today's date for marketplace orders
    transaction_date = datetime.utcnow()

    print(f"\n{'#':<4} {'Item':<45} {'Buyer':<20} {'Gross':<10} {'Net':<10} {'COGS':<10}")
    print("-" * 80)

    imported_count = 0
    cogs_matched = 0
    total_gross = Decimal("0")
    total_net = Decimal("0")
    total_cogs = Decimal("0")

    for i, (item_name, buyer_username, gross, net) in enumerate(marketplace_orders, 1):
        # Parse values
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
                first_purchase_date=transaction_date.date(),
                last_purchase_date=transaction_date.date(),
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

        # Create transaction (NO show_id - this is marketplace)
        transaction = SalesTransaction(
            show_id=None,  # Marketplace orders have no show
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
            sale_type='marketplace',  # Mark as marketplace
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
        trans_date = transaction_date.date()
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
        print(f"{i:<4} {item_name:<45} {buyer_username:<20} ${gross:>8.2f} ${net:>8.2f} {cogs_display:>9}")
        imported_count += 1

    db.commit()

    print("-" * 80)
    print(f"{'TOTALS':<70} ${total_gross:>8.2f} ${total_net:>8.2f} ${total_cogs:>8.2f}")

    print("\n" + "=" * 80)
    print("✅ MARKETPLACE ORDERS IMPORT COMPLETE")
    print("=" * 80)
    print(f"\nMarketplace orders imported: {imported_count}")
    print(f"COGS auto-assigned: {cogs_matched}/{imported_count} ({cogs_matched/imported_count*100:.1f}%)" if imported_count > 0 else "")
    print(f"Gross sales: ${total_gross:.2f}")
    print(f"Net earnings: ${total_net:.2f}")
    print(f"Total COGS: ${total_cogs:.2f}")
    print(f"Net profit: ${total_net - total_cogs:.2f}")
    print()
