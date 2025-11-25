#!/usr/bin/env python3
"""
Demonstration of rare item pricing with Trade API smart filtering.

Shows how a real rare item is processed through the full pipeline:
1. Item parsing
2. Rare evaluation
3. Trade API query generation with affix filters
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.item_parser import ItemParser
from core.rare_item_evaluator import RareItemEvaluator
from data_sources.pricing.trade_stat_ids import build_stat_filters
import json


def demo_rare_pricing():
    """Demonstrate the rare pricing pipeline."""

    # Real rare item from user
    item_text = """Item Class: Boots
Rarity: Rare
Carrion Spark
Precursor Greaves
--------
Quality: +20% (augmented)
Armour: 582 (augmented)
--------
Requirements:
Level: 78
Str: 155
--------
Sockets: R-R-R-R
--------
Item Level: 81
--------
7% increased Life Regeneration rate (implicit)
+15% to Fire Resistance (implicit)
--------
+36 to Strength
+90 to maximum Life
Regenerate 49 Life per second
+34% to Chaos Resistance
30% increased Movement Speed
44% increased Armour (crafted)
Searing Exarch Item
Eater of Worlds Item"""

    print("=" * 80)
    print("RARE ITEM PRICING DEMONSTRATION")
    print("=" * 80)

    # Step 1: Parse the item
    print("\n[STEP 1] Parsing Item")
    print("-" * 80)

    parser = ItemParser()
    parsed = parser.parse(item_text)

    print(f"Name: {parsed.name}")
    print(f"Base Type: {parsed.base_type}")
    print(f"Rarity: {parsed.rarity}")
    print(f"Item Level: {parsed.item_level}")
    print(f"Is Fractured: {parsed.is_fractured}")
    print(f"Influences: {parsed.influences}")
    print(f"\nExplicit Mods ({len(parsed.explicits)}):")
    for mod in parsed.explicits:
        print(f"  - {mod}")

    # Step 2: Evaluate the rare item
    print("\n[STEP 2] Rare Item Evaluation")
    print("-" * 80)

    evaluator = RareItemEvaluator()
    evaluation = evaluator.evaluate(parsed)

    print(f"Tier: {evaluation.tier.upper()}")
    print(f"Total Score: {evaluation.total_score}/100")
    print(f"  - Base Score: {evaluation.base_score}/50")
    print(f"  - Affix Score: {evaluation.affix_score}/100")
    print(f"Estimated Value: {evaluation.estimated_value}")
    print(f"Is Valuable Base: {evaluation.is_valuable_base}")
    print(f"Has High iLvl: {evaluation.has_high_ilvl}")

    print(f"\nMatched Affixes ({len(evaluation.matched_affixes)}):")
    for match in evaluation.matched_affixes:
        tier_str = f" [{match.tier.upper()}]" if match.tier else ""
        value_str = f" = {int(match.value)}" if match.value else ""
        print(f"  - {match.affix_type}{tier_str}: {match.mod_text}{value_str} (weight: {match.weight})")

    synergies = getattr(evaluation, 'synergies_found', [])
    if synergies:
        print(f"\nSynergies Detected ({len(synergies)}):")
        for synergy in synergies:
            print(f"  - {synergy}")

    red_flags = getattr(evaluation, 'red_flags', [])
    if red_flags:
        print(f"\nRed Flags ({len(red_flags)}):")
        for flag in red_flags:
            print(f"  - {flag}")

    # Step 3: Build Trade API query using the actual TradeApiSource
    print("\n[STEP 3] Trade API Query Generation")
    print("-" * 80)

    # Attach evaluation to parsed item (like PriceService does)
    parsed._rare_evaluation = evaluation

    # Import TradeApiSource to use the real _build_query method
    from data_sources.pricing.trade_api import TradeApiSource

    # Create a minimal TradeApiSource instance (just for query building)
    trade_source = TradeApiSource(league="Standard")

    # Use the actual _build_query method
    query = trade_source._build_query(parsed)

    # Extract stat filters for display
    stat_filters = query.get("query", {}).get("stats", [{}])[0].get("filters", [])

    print(f"Generated {len(stat_filters)} affix filters:")
    for i, filter_dict in enumerate(stat_filters, 1):
        stat_id = filter_dict["id"]
        min_val = filter_dict["value"]["min"]

        # Get human-readable name
        stat_names = {
            "pseudo.pseudo_total_life": "Total Life",
            "pseudo.pseudo_total_fire_resistance": "Fire Resistance",
            "pseudo.pseudo_total_elemental_resistance": "Elemental Resistance",
            "pseudo.pseudo_total_chaos_resistance": "Chaos Resistance",
        }
        name = stat_names.get(stat_id, stat_id)

        print(f"  {i}. {name} >= {min_val}")
        print(f"     (stat_id: {stat_id})")

    # Display influence filters if present
    influence_filters = query.get("query", {}).get("filters", {}).get("type_filters", {}).get("filters", {})
    if influence_filters:
        print(f"\nInfluence Filters ({len(influence_filters)}):")
        influence_names = {
            "searing_exarch_item": "Searing Exarch",
            "eater_of_worlds_item": "Eater of Worlds",
            "shaper_item": "Shaper",
            "elder_item": "Elder",
            "crusader_item": "Crusader",
            "hunter_item": "Hunter",
            "redeemer_item": "Redeemer",
            "warlord_item": "Warlord",
        }
        for filter_key in influence_filters:
            name = influence_names.get(filter_key, filter_key)
            print(f"  - {name}")

    print("\nComplete Trade API Query:")
    print(json.dumps(query, indent=2))

    # Step 4: What this query finds
    print("\n[STEP 4] What This Query Finds")
    print("-" * 80)

    print("This query will search for:")
    print(f"  Base Type: {parsed.base_type}")

    if influence_filters:
        print("  With influences:")
        for filter_key in influence_filters:
            name = influence_names.get(filter_key, filter_key)
            print(f"    - {name}")

    print("  With affixes:")
    for filter_dict in stat_filters:
        stat_id = filter_dict["id"]
        min_val = filter_dict["value"]["min"]
        stat_names = {
            "pseudo.pseudo_total_life": "Life",
            "pseudo.pseudo_total_fire_resistance": "Fire Res",
            "pseudo.pseudo_total_elemental_resistance": "Ele Res",
            "pseudo.pseudo_total_chaos_resistance": "Chaos Res",
        }
        name = stat_names.get(stat_id, stat_id.split(".")[-1])
        print(f"    - {name} >= {min_val}")

    print("\nExpected Results:")
    print(f"  - Only {parsed.base_type}")
    if influence_filters:
        influence_list = [influence_names.get(k, k) for k in influence_filters]
        print(f"  - With {' + '.join(influence_list)} influence")
    print("  - With similar affix rolls")
    print("  - Sorted by price (cheapest first)")
    print("  - Real market data from actual listings")

    # Step 5: Pricing decision
    print("\n[STEP 5] Final Pricing Decision")
    print("-" * 80)

    print(f"Evaluator Estimate: {evaluation.estimated_value}")
    print("Trade API: Would fetch 20 similar listings")
    print("Final Price: Median of trade results (if available)")
    print("             or evaluator estimate (if trade has no results)")
    print("Confidence: HIGH (if 10+ trade results with low spread)")
    print("            MEDIUM (if 5-10 results or moderate spread)")
    print("            LOW (if <5 results or evaluator-only)")

    # Special notes
    print("\n[NOTES]")
    print("-" * 80)

    # Dynamically generate notes based on item properties
    if parsed.influences:
        print(f"✓ Dual influence detected: {' + '.join(parsed.influences)}")
        print("✓ Influence filters applied to Trade API query")

    # Check for T1 affixes
    t1_affixes = [m for m in evaluation.matched_affixes if getattr(m, 'tier', '') == 'tier1']
    if t1_affixes:
        t1_names = [m.affix_type for m in t1_affixes]
        print(f"✓ {len(t1_affixes)} T1 affix(es): {', '.join(t1_names)}")

    # Check for life regen
    if any(m.affix_type == 'life_regeneration' for m in evaluation.matched_affixes):
        print("✓ Life regeneration detected and included in filters")

    # Check for movement speed on boots
    if parsed.base_type and 'boots' in parsed.base_type.lower():
        ms_affixes = [m for m in evaluation.matched_affixes if m.affix_type == 'movement_speed']
        if ms_affixes:
            print(f"✓ Movement speed: {int(ms_affixes[0].value)}% (essential for boots)")

    print("\nCompleted enhancements:")
    print("  ✓ Life regen and 8 new affix types added to detection")
    print("  ✓ Tier ranges fixed for movement speed and 4 other affixes")
    print("  ✓ Influence filtering added to Trade API queries")

    print("\nPotential future enhancements:")
    print("  - Add fractured mod prioritization")
    print("  - Improve synergy detection (e.g., boots_perfect)")
    print("  - Add influence mod detection (Exarch/Eater specific mods)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    demo_rare_pricing()
