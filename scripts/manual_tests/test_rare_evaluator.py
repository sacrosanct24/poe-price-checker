"""
Test script for rare item evaluator and build matcher.
"""

from core.item_parser import ItemParser
from core.rare_evaluation import RareItemEvaluator
from core.build_matcher import BuildMatcher


def test_rare_evaluator():
    """Test the rare item evaluator."""
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    print("="*70)
    print("RARE ITEM EVALUATOR TEST")
    print("="*70)
    
    # Test 1: Excellent rare helmet
    print("\n[TEST 1] Excellent Rare - Hubris Circlet")
    print("-"*70)
    
    sample1 = """Rarity: RARE
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
23% increased Stun and Block Recovery
"""
    
    item1 = parser.parse(sample1)
    if item1:
        eval1 = evaluator.evaluate(item1)
        print(evaluator.get_summary(eval1))
    
    # Test 2: Good rare boots
    print("\n" + "="*70)
    print("[TEST 2] Good Rare - Two-Toned Boots")
    print("-"*70)
    
    sample2 = """Rarity: RARE
Speed Stride
Two-Toned Boots
--------
Item Level: 84
--------
+14% to Cold and Lightning Resistances (implicit)
--------
+72 to maximum Life
+25% increased Movement Speed
+18% to Lightning Resistance
+12% to Chaos Resistance
17% increased Stun and Block Recovery
"""
    
    item2 = parser.parse(sample2)
    if item2:
        eval2 = evaluator.evaluate(item2)
        print(evaluator.get_summary(eval2))
    
    # Test 3: Average rare ring
    print("\n" + "="*70)
    print("[TEST 3] Average Rare - Opal Ring")
    print("-"*70)
    
    sample3 = """Rarity: RARE
Doom Loop
Opal Ring
--------
Item Level: 84
--------
Grants Level 22 Venom Gyre Skill (implicit)
--------
+58 to maximum Life
Adds 8 to 14 Physical Damage to Attacks
+32% to Fire Resistance
+8 to Strength
"""
    
    item3 = parser.parse(sample3)
    if item3:
        eval3 = evaluator.evaluate(item3)
        print(evaluator.get_summary(eval3))
    
    # Test 4: Vendor trash
    print("\n" + "="*70)
    print("[TEST 4] Vendor Trash - Low ilvl, bad mods")
    print("-"*70)
    
    sample4 = """Rarity: RARE
Junk Ring
Iron Ring
--------
Item Level: 45
--------
+5 to maximum Life
+10% to Fire Resistance
+8 to Strength
+3 to maximum Mana
"""
    
    item4 = parser.parse(sample4)
    if item4:
        eval4 = evaluator.evaluate(item4)
        print(evaluator.get_summary(eval4))


def test_build_matcher():
    """Test the build matcher."""
    print("\n\n" + "="*70)
    print("BUILD MATCHER TEST")
    print("="*70)
    
    matcher = BuildMatcher()
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # Add some popular builds
    print("\n[SETUP] Adding popular builds...")
    
    build1 = matcher.add_manual_build(
        build_name="Lightning Strike Raider",
        required_life=4000,
        resistances={"fire": 75, "cold": 75, "lightning": 75},
        desired_affixes=[
            "increased Movement Speed",
            "increased Attack Speed",
            "Suppression"
        ],
        key_uniques=["Perseverance", "Thread of Hope"]
    )
    print(f"[OK] Added: {build1.build_name}")

    build2 = matcher.add_manual_build(
        build_name="Spark Inquisitor",
        required_life=3500,
        required_es=2000,
        resistances={"fire": 75, "cold": 75, "lightning": 75},
        desired_affixes=[
            "increased Critical Strike Multiplier",
            "increased Cast Speed",
            "increased Energy Shield"
        ],
        key_uniques=["Void Battery", "Anomalous Spark"]
    )
    print(f"[OK] Added: {build2.build_name}")

    # Test matching
    print("\n[TEST] Matching items to builds...")
    print("-"*70)
    
    # Item that matches Spark Inquisitor (ES + Life)
    sample = """Rarity: RARE
Power Visor
Hubris Circlet
--------
Item Level: 86
--------
+45 to maximum Energy Shield (implicit)
--------
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+85 to maximum Energy Shield
+28% to Global Critical Strike Multiplier
"""
    
    item = parser.parse(sample)
    if item:
        evaluation = evaluator.evaluate(item)
        matches = matcher.match_item_to_builds(item, evaluation.matched_affixes)
        
        print(f"\nItem: {item.get_display_name()}")
        print(f"Base: {item.base_type}")
        print("\nMatched Builds:")
        
        if matches:
            for match in matches:
                print(f"\n  [OK] {match['build_name']} (Score: {match['score']})")
                for req in match['matched_requirements']:
                    print(f"    - {req}")
        else:
            print("  No builds matched")
    
    # List all builds
    print("\n" + "="*70)
    print("SAVED BUILDS:")
    print("-"*70)
    for build_name in matcher.list_builds():
        print(f"\n{matcher.get_build_summary(build_name)}")


def main():
    """Run all tests."""
    test_rare_evaluator()
    test_build_matcher()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    
    print("\nNext Steps:")
    print("  1. Test with your own items (paste them into the test)")
    print("  2. Add more valuable affixes to data/valuable_affixes.json")
    print("  3. Add your own builds via build_matcher.add_manual_build()")
    print("  4. Import PoB codes with build_matcher.import_pob_code()")


if __name__ == "__main__":
    main()
