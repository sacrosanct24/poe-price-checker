#!/usr/bin/env python3
"""
Runtime Verification Test for Multi-Source Pricing

This script tests whether poe.watch is actually being called during price lookups.
"""

import logging
import sys
from core.app_context import create_app_context

# Enable verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_item_price_lookup(item_text: str, description: str):
    """Test price lookup for a specific item."""
    print("\n" + "="*80)
    print(f"TEST: {description}")
    print("="*80)
    print(f"Item text:\n{item_text}\n")
    
    # Create app context
    ctx = create_app_context()
    
    # Check what's available
    print("[OK] App context created")
    print(f"  - poe.ninja: {'[OK] Available' if ctx.poe_ninja else '[FAIL] Not available'}")
    print(f"  - poe.watch: {'[OK] Available' if ctx.poe_watch else '[FAIL] Not available'}")

    if ctx.poe_watch:
        print(f"  - poe.watch league: {ctx.poe_watch.league}")
        print(f"  - poe.watch cache size: {ctx.poe_watch.get_cache_size()}")
    
    print("\n" + "-"*80)
    print("PRICE LOOKUP (watch for [MULTI-SOURCE] logs):")
    print("-"*80 + "\n")
    
    # Get the price service
    if ctx.price_sources:
        price_service = ctx.price_sources[0].service
        
        # Check the item
        results = price_service.check_item(item_text)
        
        print("\n" + "-"*80)
        print("RESULTS:")
        print("-"*80)
        
        if results:
            for result in results:
                print(f"  Item: {result['item_name']}")
                print(f"  Price: {result['chaos_value']}c ({result['divine_value']}d)")
                print(f"  Listings: {result['listing_count']}")
                print(f"  Source: {result['source']}")
        else:
            print("  No results returned")
        
        if ctx.poe_watch:
            print(f"\n  poe.watch cache size after: {ctx.poe_watch.get_cache_size()}")
    else:
        print("[FAIL] No price sources available!")

    print("\n")


def main():
    """Run verification tests."""
    print("\n" + "="*80)
    print(" "*15 + "MULTI-SOURCE PRICING RUNTIME VERIFICATION")
    print("="*80 + "\n")

    # Test 1: Currency item (Divine Orb)
    test_item_price_lookup(
        "Divine Orb",
        "Currency Item - Divine Orb"
    )
    
    # Test 2: Unique item
    test_item_price_lookup(
        """Rarity: Unique
Headhunter
Leather Belt
--------
Requirements:
Level: 40
--------
Has 1 Socket
--------
+40 to maximum Life
+32% to Lightning Resistance
+24% to Cold Resistance
--------
When you Kill a Rare monster, you gain its Modifiers for 20 seconds
--------
""",
        "Unique Item - Headhunter"
    )
    
    # Test 3: Simple gem
    test_item_price_lookup(
        """Rarity: Gem
Awakened Spell Echo Support
--------
Level: 5
Quality: +20%
--------
""",
        "Gem - Awakened Spell Echo Support"
    )
    
    print("\n" + "="*80)
    print(" "*34 + "TEST COMPLETE")
    print("="*80 + "\n")

    print("WHAT TO LOOK FOR IN THE LOGS ABOVE:")
    print("-" * 80)
    print("[OK] [MULTI-SOURCE] Looking up price for '...'")
    print("[OK] [MULTI-SOURCE] Available sources: poe.ninja=True, poe.watch=True")
    print("[OK] [MULTI-SOURCE] Querying poe.ninja...")
    print("[OK] [MULTI-SOURCE]   poe.ninja result: <price>c")
    print("[OK] [MULTI-SOURCE] Querying poe.watch...")
    print("[OK] [MULTI-SOURCE]   poe.watch result: <price>c")
    print("[OK] [MULTI-SOURCE] Decision: Using <source> <price>c")
    print("-" * 80)
    print("\nIf you DON'T see poe.watch being queried, that's the bug!")
    print("The logs will tell us exactly where the issue is.\n")


if __name__ == "__main__":
    main()
