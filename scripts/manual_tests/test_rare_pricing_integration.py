#!/usr/bin/env python3
"""
Quick integration test for rare item pricing.

Tests that the rare_item_evaluator is properly integrated into PriceService
and produces prices for rare items.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.rare_evaluation import RareItemEvaluator
from core.pricing import PriceService


def test_rare_pricing_integration():
    """Test that rare pricing works end-to-end."""

    print("=" * 70)
    print("Testing Rare Item Pricing Integration")
    print("=" * 70)

    # Initialize components
    print("\n[1] Initializing components...")
    config = Config()
    parser = ItemParser()
    db = Database()
    rare_evaluator = RareItemEvaluator()

    # Create PriceService WITHOUT poe.ninja (to force rare evaluator usage)
    price_service = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=None,  # No market data
        poe_watch=None,
        trade_source=None,
        rare_evaluator=rare_evaluator
    )

    print("[OK] Components initialized\n")

    # Test cases
    test_items = [
        {
            "name": "Excellent Rare Helmet",
            "item_text": """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 86
--------
+45 to maximum Energy Shield (implicit)
--------
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+15% to Chaos Resistance
+85 to maximum Energy Shield
""",
            "expected": "Should be priced as 'excellent' tier"
        },
        {
            "name": "Mediocre Rare Ring",
            "item_text": """Rarity: RARE
Bad Ring
Iron Ring
--------
Item Level: 45
--------
+5 to maximum Life
+10% to Fire Resistance
+8 to Strength
""",
            "expected": "Should be priced as 'vendor' tier"
        },
        {
            "name": "Good Rare Boots",
            "item_text": """Rarity: RARE
Swift Greaves
Sorcerer Boots
--------
Item Level: 85
--------
+30% to Fire Resistance
+28% to Cold Resistance
+25% increased Movement Speed
+65 to maximum Life
""",
            "expected": "Should be priced as 'good' tier (movement + life + res)"
        }
    ]

    # Test each item
    for i, test in enumerate(test_items, 1):
        print(f"\n[TEST {i}] {test['name']}")
        print(f"Expected: {test['expected']}")
        print("-" * 70)

        try:
            result = price_service.check_item(test['item_text'])

            if not result:
                print("[FAIL] No result returned")
                continue

            row = result[0]
            chaos_value = float(row['chaos_value'])
            source = row['source']

            print(f"[OK] Price: {chaos_value:.1f} chaos")
            print(f"[OK] Source: {source}")

            # Verify rare_evaluator was used
            if 'rare_evaluator' in source:
                print("[OK] ✓ Rare evaluator was used")
            else:
                print(f"[WARN] Rare evaluator not used (source: {source})")

            # Check if price is reasonable
            if chaos_value > 0:
                print(f"[OK] ✓ Non-zero price: {chaos_value:.1f}c")
            else:
                print("[WARN] Zero price returned")

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Integration Test Complete")
    print("=" * 70)


def test_value_parsing():
    """Test the _parse_estimated_value_to_chaos helper."""

    print("\n" + "=" * 70)
    print("Testing Value Parsing")
    print("=" * 70)

    config = Config()
    parser = ItemParser()
    db = Database()
    rare_evaluator = RareItemEvaluator()

    # Mock divine rate for testing
    class MockPoeNinja:
        divine_chaos_rate = 200.0
        def ensure_divine_rate(self):
            return 200.0

    price_service = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=MockPoeNinja(),
        rare_evaluator=rare_evaluator
    )

    test_cases = [
        ("<5c", 2.5),
        ("50c+", 50.0),
        ("5-10c", 7.5),
        ("50-200c", 125.0),
        ("1div+", 200.0),
        ("200c-5div", 600.0),  # (200 + 1000) / 2
    ]

    print("\nTesting value string parsing:")
    for value_str, expected in test_cases:
        result = price_service._parse_estimated_value_to_chaos(value_str)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"{status} '{value_str}' → {result}c (expected: {expected}c)")

    print("")


if __name__ == "__main__":
    test_value_parsing()
    test_rare_pricing_integration()
