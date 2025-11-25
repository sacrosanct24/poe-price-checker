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
    item_text = """Item Class: Gloves
Rarity: Rare
Vengeance Grasp
Precursor Gauntlets
--------
Quality: +20% (augmented)
Armour: 540 (augmented)
--------
Requirements:
Level: 78
Str: 155
Int: 68
--------
Sockets: G-R-R-R
--------
Item Level: 86
--------
Ignites you inflict spread to other Enemies within 1.2 metres (implicit)
--------
+48% to Fire Resistance (fractured)
+43 to Armour
14% increased Armour
+157 to maximum Life
Regenerate 47.4 Life per second
9% increased Stun and Block Recovery
+13% to Fire and Chaos Resistances (crafted)
Searing Exarch Item
--------
Fractured Item"""

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

    # Step 3: Build Trade API query
    print("\n[STEP 3] Trade API Query Generation")
    print("-" * 80)

    # Attach evaluation to parsed item (like PriceService does)
    parsed._rare_evaluation = evaluation

    # Build stat filters from matched affixes
    stat_filters = build_stat_filters(evaluation.matched_affixes, max_filters=4)

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

    # Build the complete query
    query = {
        "query": {
            "status": {"option": "online"},
            "type": parsed.base_type,  # Precursor Gauntlets
            "stats": [{"type": "and", "filters": stat_filters}]
        },
        "sort": {"price": "asc"}
    }

    print("\nComplete Trade API Query:")
    print(json.dumps(query, indent=2))

    # Step 4: What this query finds
    print("\n[STEP 4] What This Query Finds")
    print("-" * 80)

    print("This query will search for:")
    print(f"  Base Type: {parsed.base_type}")
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
    print("  - Only Precursor Gauntlets (not random gloves)")
    print("  - With similar high life roll (125+ life)")
    print("  - With decent fire resistance (38+ fire res)")
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
    print("✓ Fractured mod detected: +48% fire res")
    print("✓ High life roll (+157) is T1 affix")
    print("✓ Life regen adds value but not in trade filters (niche mod)")
    print("✓ Searing Exarch influence adds value (not yet in filters)")
    print("✓ Item level 86 allows all T1 mods")
    print("\nPotential enhancements:")
    print("  - Add life regen to stat mappings")
    print("  - Add influence filtering for Exarch/Eater items")
    print("  - Add fractured mod prioritization")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    demo_rare_pricing()
