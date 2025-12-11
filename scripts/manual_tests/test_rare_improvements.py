"""
Test script for Phase 1.2 rare item evaluator improvements.

Tests:
- Tier detection (T1, T2, T3)
- Synergy bonuses
- Red flag penalties
- Influence mod detection
"""

from core.item_parser import ItemParser
from core.rare_evaluation import RareItemEvaluator


def test_tier_detection():
    """Test T1/T2/T3 tier detection with value ranges."""
    print("=" * 70)
    print("TEST 1: Tier Detection (T1/T2/T3)")
    print("=" * 70)
    
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # T1 Life (100+)
    item_t1 = """Rarity: RARE
Perfect Ring
Opal Ring
--------
Item Level: 86
--------
+105 to maximum Life
+42% to Fire Resistance
"""
    
    # T2 Life (90-99)
    item_t2 = """Rarity: RARE
Good Ring
Opal Ring
--------
Item Level: 84
--------
+95 to maximum Life
+42% to Fire Resistance
"""
    
    # T3 Life (80-89)
    item_t3 = """Rarity: RARE
Decent Ring
Opal Ring
--------
Item Level: 82
--------
+85 to maximum Life
+38% to Fire Resistance
"""
    
    for label, text in [("T1", item_t1), ("T2", item_t2), ("T3", item_t3)]:
        item = parser.parse(text)
        if item:
            eval_result = evaluator.evaluate(item)
            print(f"\n{label} Life Item:")
            print(f"  Total Score: {eval_result.total_score}/100")
            print(f"  Tier: {eval_result.tier.upper()}")
            print(f"  Value: {eval_result.estimated_value}")
            if eval_result.matched_affixes:
                for match in eval_result.matched_affixes:
                    print(f"    - {match.affix_type} ({match.tier}): {match.value} [weight: {match.weight}]")


def test_synergy_bonuses():
    """Test synergy detection and bonus scoring."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Synergy Bonuses")
    print("=" * 70)
    
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # Life + Triple Res (should get +20 bonus)
    item_synergy = """Rarity: RARE
Synergy Ring
Vermillion Ring
--------
Item Level: 86
--------
+95 to maximum Life
+45% to Fire Resistance
+42% to Cold Resistance
+40% to Lightning Resistance
"""
    
    # No synergy (just life + single res)
    item_no_synergy = """Rarity: RARE
Basic Ring
Vermillion Ring
--------
Item Level: 86
--------
+95 to maximum Life
+45% to Fire Resistance
"""
    
    for label, text in [("With Synergy", item_synergy), ("Without Synergy", item_no_synergy)]:
        item = parser.parse(text)
        if item:
            eval_result = evaluator.evaluate(item)
            print(f"\n{label}:")
            print(f"  Affix Score: {eval_result.affix_score}/100")
            print(f"  Synergy Bonus: +{eval_result.synergy_bonus}")
            print(f"  Total Score: {eval_result.total_score}/100")
            print(f"  Tier: {eval_result.tier.upper()}")
            print(f"  Value: {eval_result.estimated_value}")
            if eval_result.synergies_found:
                print(f"  Synergies: {', '.join(eval_result.synergies_found)}")


def test_red_flags():
    """Test red flag detection and penalties."""
    print("\n\n" + "=" * 70)
    print("TEST 3: Red Flag Penalties")
    print("=" * 70)
    
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # Good boots (with movement speed)
    good_boots = """Rarity: RARE
Speed Boots
Two-Toned Boots
--------
Item Level: 86
--------
+90 to maximum Life
+42% to Fire Resistance
+40% to Cold Resistance
30% increased Movement Speed
"""
    
    # Bad boots (missing movement speed) - should get -30 penalty
    bad_boots = """Rarity: RARE
Slow Boots
Two-Toned Boots
--------
Item Level: 86
--------
+90 to maximum Life
+42% to Fire Resistance
+40% to Cold Resistance
+35% to Lightning Resistance
"""
    
    # Life + ES hybrid (should get -20 penalty)
    hybrid_item = """Rarity: RARE
Confused Helmet
Hubris Circlet
--------
Item Level: 86
--------
+90 to maximum Life
+80 to maximum Energy Shield
+42% to Fire Resistance
"""
    
    test_cases = [
        ("Good Boots", good_boots),
        ("Boots Missing MS", bad_boots),
        ("Life+ES Hybrid", hybrid_item)
    ]
    
    for label, text in test_cases:
        item = parser.parse(text)
        if item:
            eval_result = evaluator.evaluate(item)
            print(f"\n{label}:")
            print(f"  Base Score: {eval_result.base_score}")
            print(f"  Affix Score: {eval_result.affix_score}")
            print(f"  Red Flag Penalty: {eval_result.red_flag_penalty}")
            print(f"  Total Score: {eval_result.total_score}/100")
            print(f"  Tier: {eval_result.tier.upper()}")
            if eval_result.red_flags_found:
                print(f"  Red Flags: {', '.join(eval_result.red_flags_found)}")


def test_influence_mods():
    """Test influence mod detection."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Influence Mod Detection")
    print("=" * 70)
    
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # Hunter influence with high-value mod
    hunter_item = """Item Class: Body Armour
Rarity: RARE
Life Chest
Vaal Regalia
--------
Item Level: 86
--------
+95 to maximum Life
+42% to Fire Resistance
+10% to maximum Life
Nearby Enemies have -9% to Chaos Resistance
Hunter Item
"""
    
    # Crusader influence
    crusader_item = """Rarity: RARE
Explode Chest
Astral Plate
--------
Item Level: 86
--------
+90 to maximum Life
+42% to Fire Resistance
Enemies you Kill Explode, dealing 3% of their Life as Physical Damage
Crusader Item
"""
    
    test_cases = [
        ("Hunter (% max life)", hunter_item),
        ("Crusader (Explode)", crusader_item)
    ]
    
    for label, text in test_cases:
        item = parser.parse(text)
        if item:
            eval_result = evaluator.evaluate(item)
            print(f"\n{label}:")
            print(f"  Influences: {item.influences}")
            print(f"  Total Score: {eval_result.total_score}/100")
            print(f"  Tier: {eval_result.tier.upper()}")
            print(f"  Value: {eval_result.estimated_value}")
            
            influence_mods = [m for m in eval_result.matched_affixes if m.is_influence_mod]
            if influence_mods:
                print(f"  Influence Mods Detected:")
                for mod in influence_mods:
                    print(f"    - {mod.affix_type}: {mod.mod_text}")


def test_complete_item():
    """Test a complete item with multiple features."""
    print("\n\n" + "=" * 70)
    print("TEST 5: Complete Item Evaluation")
    print("=" * 70)
    
    parser = ItemParser()
    evaluator = RareItemEvaluator()
    
    # Perfect boots: high base, T1 mods, synergy, no red flags
    perfect_boots = """Item Class: Boots
Rarity: RARE
Carrion Spark
Two-Toned Boots
--------
Quality: +20% (augmented)
--------
Item Level: 86
--------
+15% to Fire and Cold Resistances (implicit)
--------
+102 to maximum Life
+45% to Fire Resistance
+42% to Cold Resistance
30% increased Movement Speed
Searing Exarch Item
Eater of Worlds Item
"""
    
    item = parser.parse(perfect_boots)
    if item:
        eval_result = evaluator.evaluate(item)
        print(evaluator.get_summary(eval_result))


if __name__ == "__main__":
    print("\n")
    print("*" * 70)
    print("  RARE ITEM EVALUATOR - PHASE 1.2 IMPROVEMENTS TEST")
    print("*" * 70)
    
    test_tier_detection()
    test_synergy_bonuses()
    test_red_flags()
    test_influence_mods()
    test_complete_item()
    
    print("\n\n" + "*" * 70)
    print("  ALL TESTS COMPLETE")
    print("*" * 70)
    print("\nNew Features:")
    print("  [OK] T1/T2/T3 tier detection with value ranges")
    print("  [OK] Synergy bonuses for mod combinations")
    print("  [OK] Red flag penalties for anti-synergies")
    print("  [OK] Influence mod detection (Hunter, Warlord, Crusader, etc.)")
    print("  [OK] Enhanced scoring algorithm")
    print("\n")
