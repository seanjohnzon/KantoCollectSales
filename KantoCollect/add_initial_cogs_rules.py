#!/usr/bin/env python3
"""
Add initial COGS mapping rules to the database.

These rules will auto-assign costs to products based on keywords.
Higher priority rules are checked first.
"""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, create_engine, select
from app.models.whatnot import COGSMappingRule
from decimal import Decimal

# Connect to database
whatnot_engine = create_engine("sqlite:////Users/sahcihansahin/KantoCollect/backend/whatnot_sales.db")

print("="*70)
print("ADD INITIAL COGS MAPPING RULES")
print("="*70)

# Define initial rules based on the plan
initial_rules = [
    {
        'rule_name': 'One Piece Alternate Art',
        'keywords': ['alternate art', 'aa', '(aa)', 'alt art'],
        'cogs_amount': Decimal('25.00'),
        'match_type': 'contains',
        'priority': 100,
        'category': 'One Piece Cards',
        'notes': 'Standard AA cards - typical cost around $25',
        'is_active': True
    },
    {
        'rule_name': 'Marshall D. Teach OP09-093',
        'keywords': ['marshall d teach', 'op09-093', 'marshall d. teach'],
        'cogs_amount': Decimal('30.00'),
        'match_type': 'contains',
        'priority': 95,
        'category': 'One Piece Cards - High Value',
        'notes': 'Specific high-value card',
        'is_active': True
    },
    {
        'rule_name': 'Booster Bundle',
        'keywords': ['booster bundle', 'booster pack bundle'],
        'cogs_amount': Decimal('15.00'),
        'match_type': 'contains',
        'priority': 90,
        'category': 'Sealed Products',
        'notes': 'Bundle of booster packs',
        'is_active': True
    },
    {
        'rule_name': 'Random Asian Pack',
        'keywords': ['random asian pack', 'asian pack'],
        'cogs_amount': Decimal('3.00'),
        'match_type': 'contains',
        'priority': 85,
        'category': 'Random Packs',
        'notes': 'Random pack products',
        'is_active': True
    },
    {
        'rule_name': 'UPC Box',
        'keywords': ['upc', 'ultra premium collection'],
        'cogs_amount': Decimal('120.00'),
        'match_type': 'contains',
        'priority': 80,
        'category': 'Sealed Products - Premium',
        'notes': 'Ultra Premium Collection boxes',
        'is_active': True
    },
    {
        'rule_name': 'ETB',
        'keywords': ['etb', 'elite trainer box'],
        'cogs_amount': Decimal('40.00'),
        'match_type': 'contains',
        'priority': 75,
        'category': 'Sealed Products',
        'notes': 'Elite Trainer Boxes',
        'is_active': True
    },
    {
        'rule_name': 'Free Pack',
        'keywords': ['free', 'free pack', 'free pokemon'],
        'cogs_amount': Decimal('0.00'),
        'match_type': 'contains',
        'priority': 50,
        'category': 'Giveaways',
        'notes': 'Free giveaway items',
        'is_active': True
    }
]

with Session(whatnot_engine) as session:
    # Check if rules already exist
    existing_rules = session.exec(select(COGSMappingRule)).all()

    if existing_rules:
        print(f"\n⚠️  Found {len(existing_rules)} existing rules")
        print("   Clearing existing rules first...")
        for rule in existing_rules:
            session.delete(rule)
        session.commit()
        print("   ✅ Cleared!")

    print(f"\n📋 Adding {len(initial_rules)} COGS mapping rules...\n")

    # Add each rule
    for rule_data in initial_rules:
        rule = COGSMappingRule(**rule_data)
        session.add(rule)

        print(f"   [{rule_data['priority']}] {rule_data['rule_name']}")
        print(f"      Keywords: {', '.join(rule_data['keywords'][:3])}{'...' if len(rule_data['keywords']) > 3 else ''}")
        print(f"      COGS: ${rule_data['cogs_amount']}")
        print(f"      Category: {rule_data['category']}")
        print()

    session.commit()
    print("✅ All rules added successfully!")

# Verify
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)

with Session(whatnot_engine) as session:
    rules = session.exec(
        select(COGSMappingRule).order_by(COGSMappingRule.priority.desc())
    ).all()

    print(f"\n✅ Database now has {len(rules)} COGS rules:\n")

    for rule in rules:
        status = "✓ Active" if rule.is_active else "✗ Inactive"
        print(f"   Priority {rule.priority:3d} | {status} | {rule.rule_name}")
        print(f"      COGS: ${rule.cogs_amount} | Keywords: {len(rule.keywords)}")

print("\n" + "="*70)
print("✅ Ready to apply COGS rules to transactions!")
print("="*70)
