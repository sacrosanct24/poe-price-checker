#!/usr/bin/env python3
"""Simple runtime verification test for multi-source pricing."""

import logging
import sys

# Enable verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
)

from core.app_context import create_app_context

def test_divine_orb():
    """Test Divine Orb pricing."""
    print("\n" + "="*80)
    print("Testing Divine Orb pricing")
    print("="*80 + "\n")
    
    # Proper currency item format
    divine_orb_text = """Rarity: Currency
Divine Orb
--------
Stack Size: 1/10
--------
Randomises the values of the random modifiers on an item
--------"""

    # Create context
    ctx = create_app_context()
    
    print(f"poe.ninja available: {ctx.poe_ninja is not None}")
    print(f"poe.watch available: {ctx.poe_watch is not None}")
    
    if ctx.poe_watch:
        print(f"poe.watch league: {ctx.poe_watch.league}")
        print(f"poe.watch request count before: {ctx.poe_watch.request_count}")
    
    print("\n" + "-"*80)
    print("CALLING check_item('Divine Orb')...")
    print("-"*80 + "\n")
    
    # Check the item using multi-source price service
    results = ctx.price_service.check_item(divine_orb_text)

    print("\n" + "-"*80)
    print("RESULTS:")
    print("-"*80)
    
    if results:
        for r in results:
            print(f"  Item: {r['item_name']}")
            print(f"  Price: {r['chaos_value']}c")
            print(f"  Source: {r['source']}")
    else:
        print("  No results")
    
    if ctx.poe_watch:
        print(f"\npoe.watch request count after: {ctx.poe_watch.request_count}")
        print(f"poe.watch cache size after: {ctx.poe_watch.get_cache_size()}")
    
    print("\n")

if __name__ == "__main__":
    test_divine_orb()
    
    print("\n" + "="*80)
    print("VERIFICATION CHECKLIST:")
    print("="*80)
    print("Look for these log messages above:")
    print("  1. [MULTI-SOURCE] Looking up price for 'Divine Orb'")
    print("  2. [MULTI-SOURCE] Available sources: poe.ninja=True, poe.watch=True")
    print("  3. [MULTI-SOURCE] Querying poe.ninja...")
    print("  4. [MULTI-SOURCE] Querying poe.watch...")
    print("  5. [poe.watch] API Request #1: search")
    print("  6. [MULTI-SOURCE] Decision: Using...")
    print("\nIf you DON'T see steps 4-5, poe.watch is NOT being called!")
    print("="*80 + "\n")
