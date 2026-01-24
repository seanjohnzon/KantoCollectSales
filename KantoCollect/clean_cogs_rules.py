#!/usr/bin/env python3
"""Clean up all auto-generated COGS rules directly from database."""
import sys
sys.path.insert(0, '/Users/sahcihansahin/KantoCollect/backend')

from sqlmodel import Session, select
from app.core.whatnot_database import whatnot_engine
from app.models.whatnot import COGSMappingRule

print("="*70)
print("CLEAN UP AUTO-GENERATED COGS RULES")
print("="*70)

with Session(whatnot_engine) as session:
    # Get all rules
    all_rules = session.exec(select(COGSMappingRule)).all()
    print(f"\nFound {len(all_rules)} total COGS rules\n")

    # Delete all auto-generated rules
    deleted_count = 0
    for rule in all_rules:
        if "Auto-generated" in rule.rule_name:
            print(f"Deleting: {rule.rule_name} (ID: {rule.id})")
            session.delete(rule)
            deleted_count += 1

    # Commit the deletions
    session.commit()

    print(f"\n✅ Deleted {deleted_count} auto-generated rules")

    # Show remaining rules
    remaining_rules = session.exec(select(COGSMappingRule)).all()
    if remaining_rules:
        print(f"\nRemaining rules: {len(remaining_rules)}")
        for rule in remaining_rules:
            print(f"  - {rule.rule_name}")
    else:
        print("\n✅ All rules cleared! You can now add your own custom rules.")

print("="*70)
