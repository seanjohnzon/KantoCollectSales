#!/usr/bin/env python3
"""Check overall system statistics."""
import requests
from decimal import Decimal

url_base = "http://localhost:8000/api/v1/admin/whatnot"
headers = {"Authorization": "Bearer 1453"}

print("="*70)
print("WHATNOT SALES TRACKING SYSTEM - OVERALL STATISTICS")
print("="*70)

# Get all shows
shows_response = requests.get(f"{url_base}/shows?limit=100", headers=headers)
shows = shows_response.json()

print(f"\n📊 SHOWS SUMMARY")
print(f"   Total Shows: {len(shows)}")

total_revenue = Decimal('0')
total_earnings = Decimal('0')
total_cogs = Decimal('0')
total_profit = Decimal('0')
total_items = 0
total_buyers_set = set()

print(f"\n   Show Details:")
for show in sorted(shows, key=lambda x: x['show_date']):
    revenue = Decimal(str(show['total_gross_sales']))
    earnings = Decimal(str(show['total_net_earnings']))
    cogs = Decimal(str(show['total_cogs']))
    profit = Decimal(str(show['total_net_profit']))

    total_revenue += revenue
    total_earnings += earnings
    total_cogs += cogs
    total_profit += profit
    total_items += show['item_count']

    roi = (profit / cogs * 100) if cogs > 0 else 0
    print(f"   {show['show_date']} | Items: {show['item_count']:3} | Revenue: ${revenue:8,.2f} | COGS: ${cogs:6,.2f} | Profit: ${profit:7,.2f} | ROI: {roi:5.1f}%")

print(f"\n   {'─'*66}")
print(f"   TOTALS          | Items: {total_items:3} | Revenue: ${total_revenue:8,.2f} | COGS: ${total_cogs:6,.2f} | Profit: ${total_profit:7,.2f}")

if total_cogs > 0:
    overall_roi = (total_profit / total_cogs * 100)
    print(f"   Overall ROI: {overall_roi:.1f}%")

# Get all transactions to check COGS coverage
trans_response = requests.get(f"{url_base}/transactions?sale_type=stream&limit=1000", headers=headers)
transactions = trans_response.json()

total_transactions = len(transactions)
with_cogs = sum(1 for t in transactions if t.get('cogs') and Decimal(str(t['cogs'])) > 0)
without_cogs = total_transactions - with_cogs

print(f"\n💰 COGS COVERAGE")
print(f"   Total Transactions: {total_transactions}")
print(f"   With COGS: {with_cogs} ({with_cogs/total_transactions*100:.1f}%)")
print(f"   Without COGS: {without_cogs} ({without_cogs/total_transactions*100:.1f}%)")

# Get COGS rules
rules_response = requests.get(f"{url_base}/cogs-rules", headers=headers)
rules = rules_response.json()

print(f"\n📋 COGS RULES")
print(f"   Total Rules: {len(rules)}")
print(f"   Active Rules: {sum(1 for r in rules if r.get('is_active', True))}")

print(f"\n   Top Rules by Priority:")
for rule in sorted(rules, key=lambda x: x['priority'], reverse=True)[:10]:
    status = "✓" if rule.get('is_active', True) else "✗"
    keywords_str = ", ".join(rule['keywords'][:3])
    if len(rule['keywords']) > 3:
        keywords_str += f", +{len(rule['keywords'])-3} more"
    print(f"   {status} Priority {rule['priority']:3} | ${float(rule['cogs_amount']):6.2f} | {rule['rule_name'][:30]}")
    print(f"      Keywords: {keywords_str}")

# Get products
products_response = requests.get(f"{url_base}/products?limit=1000", headers=headers)
products = products_response.json()

print(f"\n🎁 PRODUCTS")
print(f"   Total Unique Products: {len(products)}")

# Count products with/without COGS
products_with_cogs = 0
products_without_cogs = 0

for product in products:
    # Check if any transaction for this product has COGS
    product_trans = [t for t in transactions if t.get('product_id') == product['id']]
    if any(t.get('cogs') and Decimal(str(t['cogs'])) > 0 for t in product_trans):
        products_with_cogs += 1
    else:
        products_without_cogs += 1

print(f"   Products with COGS assigned: {products_with_cogs}")
print(f"   Products needing COGS: {products_without_cogs}")

# Top products by revenue
top_products = sorted(products, key=lambda x: Decimal(str(x.get('total_gross_sales', '0'))), reverse=True)[:10]
print(f"\n   Top 10 Products by Revenue:")
for i, product in enumerate(top_products, 1):
    revenue = Decimal(str(product.get('total_gross_sales', '0')))
    times_sold = product.get('times_sold', 0)
    avg_price = revenue / times_sold if times_sold > 0 else 0
    print(f"   {i:2}. ${revenue:7,.2f} | {times_sold:2}x @ ${avg_price:5,.2f} | {product['product_name'][:40]}")

# Get buyers
buyers_response = requests.get(f"{url_base}/buyers?limit=1000", headers=headers)
buyers = buyers_response.json()

print(f"\n👥 BUYERS")
print(f"   Total Unique Buyers: {len(buyers)}")

total_spent = sum(Decimal(str(b.get('total_spent', '0'))) for b in buyers)
total_purchases = sum(b.get('total_purchases', 0) for b in buyers)
avg_purchase_value = total_spent / total_purchases if total_purchases > 0 else 0

print(f"   Total Spent: ${total_spent:,.2f}")
print(f"   Total Purchases: {total_purchases}")
print(f"   Average Purchase: ${avg_purchase_value:.2f}")

# Top buyers
top_buyers = sorted(buyers, key=lambda x: Decimal(str(x.get('total_spent', '0'))), reverse=True)[:10]
print(f"\n   Top 10 Buyers by Spending:")
for i, buyer in enumerate(top_buyers, 1):
    spent = Decimal(str(buyer.get('total_spent', '0')))
    purchases = buyer.get('total_purchases', 0)
    avg = spent / purchases if purchases > 0 else 0
    print(f"   {i:2}. ${spent:7,.2f} | {purchases:2} purchases @ ${avg:5,.2f} | @{buyer['username']}")

print(f"\n{'='*70}")
print("✅ System is operational and tracking sales successfully!")
print("="*70)
