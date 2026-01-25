#!/usr/bin/env python3
"""
Preview import data before adding to database.
"""

# Parse the data from the image
transactions = [
    ("op11&op1", "23-Jan-26", "rthreat41", 3.00, 2.36),
    ("Free Poke", "23-Jan-26", "hev_day", 0.00, 19.13),  # Free item, no price but has net?
    ("prb01 eng", "23-Jan-26", "rthreat41", 22.00, 9.46),
    ("op 12 eng", "23-Jan-26", "pokebroz", 11.00, 11.23),
    ("op 10 eng", "23-Jan-26", "rthreat41", 13.00, -0.31),  # Negative net
    ("Free Poke", "23-Jan-26", "callmethebr", 0.00, 15.64),
    ("2x Pack", "23-Jan-26", "razzy415", 18.00, 11.22),
    ("2x Pack", "23-Jan-26", "collectable_j", 13.00, 15.60),
    ("2x Pack", "23-Jan-26", "razzy415", 18.00, 15.64),
    ("2x Pack", "23-Jan-26", "rogerbear202", 18.00, -0.78),
    ("Free Poke", "23-Jan-26", "callmethebr", 0.00, 15.68),
    ("2x Pack", "23-Jan-26", "razzy415", 18.00, 12.01),
    ("2x Pack", "23-Jan-26", "razzy415", 15.00, -0.78),
    ("Free Poke", "23-Jan-26", "razzy415", 0.00, 12.98),
    ("2x Pack", "23-Jan-26", "menderz3", 15.00, 10.32),
    ("2x Pack", "23-Jan-26", "carlos_612", 12.00, -0.78),
    ("Free Poke", "23-Jan-26", "ahd0820", 0.00, 18.32),
    ("2x Pack", "23-Jan-26", "shdytcg", 21.00, -0.78),
    ("Free Poke", "22-Jan-26", "patshu_don", 0.00, 36.07),
    ("2x Pack", "22-Jan-26", "carlos27513", 41.00, 35.18),
    ("2x Pack", "22-Jan-26", "carlos27513", 40.00, -0.78),
    ("Free Poke", "22-Jan-26", "raz343434", 0.00, 35.20),
    ("2x Pack", "22-Jan-26", "carlos27513", 40.00, 26.33),
    ("2x Pack", "22-Jan-26", "carlos27513", 30.00, -0.78),
    ("Free Poke", "22-Jan-26", "2peace2ay", 0.00, 29.78),
    ("2x Pack", "22-Jan-26", "cubletcg", 34.00, 27.28),
    ("2x Pack", "22-Jan-26", "anthonykino7", 31.00, -0.78),
    ("Free Poke", "22-Jan-26", "fabiansai500", 0.00, 29.92),
    ("2x Pack", "22-Jan-26", "blockspinnat", 24.00, 17.43),
    ("2x Pack", "22-Jan-26", "blockspinnat", 20.00, -0.78),
    ("Free Poke", "22-Jan-26", "noizecompia", 0.00, 17.43),
    ("2x Pack", "22-Jan-26", "josevil39413", 20.00, 16.54),
    ("2x Pack", "22-Jan-26", "teej530", 19.00, -1.35),
    ("Free Poke", "22-Jan-26", "carlos27513", 0.00, 16.53),
    ("2x Pack", "22-Jan-26", "carlos27513", 19.00, -0.78),
    ("Free Poke", "22-Jan-26", "roughcollect", 0.00, 0.00),  # No net amount shown
]

print("=" * 100)
print("IMPORT PREVIEW - Jan 22-23, 2026 Show")
print("=" * 100)
print(f"\n{'#':<4} {'Date':<12} {'Item Name':<25} {'Buyer':<20} {'Gross $':<10} {'Net $':<10}")
print("-" * 100)

total_gross = 0
total_net = 0

for i, (item, date, buyer, gross, net) in enumerate(transactions, 1):
    print(f"{i:<4} {date:<12} {item:<25} {buyer:<20} ${gross:>8.2f} ${net:>8.2f}")
    total_gross += gross
    total_net += net

print("-" * 100)
print(f"{'TOTALS':<63} ${total_gross:>8.2f} ${total_net:>8.2f}")
print()

print("\nISSUES TO CONFIRM:")
print("-" * 100)

# Find issues
free_poke_with_net = [(i+1, item, buyer, gross, net) for i, (item, date, buyer, gross, net) in enumerate(transactions) if item == "Free Poke" and net > 0]
negative_nets = [(i+1, item, buyer, gross, net) for i, (item, date, buyer, gross, net) in enumerate(transactions) if net < 0]
zero_gross_positive_net = [(i+1, item, buyer, gross, net) for i, (item, date, buyer, gross, net) in enumerate(transactions) if gross == 0 and net > 0]

print(f"\n1. 'Free Poke' items with $0.00 gross but positive net earnings:")
print(f"   Found {len(free_poke_with_net)} items")
for row_num, item, buyer, gross, net in free_poke_with_net[:5]:
    print(f"   Row {row_num}: {buyer} - Gross: ${gross:.2f}, Net: ${net:.2f}")
if len(free_poke_with_net) > 5:
    print(f"   ... and {len(free_poke_with_net) - 5} more")

print(f"\n2. Transactions with NEGATIVE net earnings:")
print(f"   Found {len(negative_nets)} items")
for row_num, item, buyer, gross, net in negative_nets[:5]:
    print(f"   Row {row_num}: {item} - {buyer} - Gross: ${gross:.2f}, Net: ${net:.2f}")
if len(negative_nets) > 5:
    print(f"   ... and {len(negative_nets) - 5} more")

print(f"\n3. Items with $0 gross but positive net:")
print(f"   Found {len(zero_gross_positive_net)} items")
for row_num, item, buyer, gross, net in zero_gross_positive_net[:5]:
    print(f"   Row {row_num}: {item} - {buyer} - Gross: ${gross:.2f}, Net: ${net:.2f}")
if len(zero_gross_positive_net) > 5:
    print(f"   ... and {len(zero_gross_positive_net) - 5} more")

print("\n" + "=" * 100)
print("QUESTIONS BEFORE IMPORT:")
print("=" * 100)
print("\n1. What should the show name be? (e.g., 'Jan 22-23, 2026 Stream')")
print("\n2. Free Poke items: Are these giveaways that WhatNot pays you for? Should gross = net?")
print("\n3. Negative net earnings: Are these refunds/chargebacks? Should we import them?")
print("\n4. All transactions are quantity = 1, correct?")
print()
