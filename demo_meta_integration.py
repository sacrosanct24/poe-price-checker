#!/usr/bin/env python3
"""
Demo: Meta-Based Dynamic Affix Weighting

Shows how to integrate build scraping and meta analysis
with the rare item evaluation system.

Workflow:
1. Scrape builds from poe.ninja/pobb.in
2. Analyze meta affixes
3. Generate dynamic weights
4. Update rare item evaluator configuration
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from core.build_matcher import BuildMatcher
from core.meta_analyzer import MetaAnalyzer
from data_sources.build_scrapers import PoeNinjaBuildScraper, extract_pob_link

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_manual_builds():
    """Demo 1: Manually add builds and analyze."""
    print("=" * 80)
    print("DEMO 1: Manual Build Analysis")
    print("=" * 80)

    # Create builds (simulating meta builds)
    matcher = BuildMatcher()

    builds = [
        matcher.add_manual_build(
            "Lightning Strike Raider",
            required_life=4000,
            resistances={"fire": 75, "cold": 75, "lightning": 75},
            desired_affixes=["Movement Speed", "Attack Speed", "Suppression"]
        ),
        matcher.add_manual_build(
            "Righteous Fire Juggernaut",
            required_life=8000,
            resistances={"fire": 90, "chaos": 75},
            desired_affixes=["Life Regeneration", "Maximum Life", "Fire Resistance"]
        ),
        matcher.add_manual_build(
            "Poison Blade Vortex Pathfinder",
            required_life=5000,
            resistances={"chaos": 75},
            desired_affixes=["Cast Speed", "Attack Speed", "Chaos Resistance"]
        ),
        matcher.add_manual_build(
            "Cold DoT Occultist",
            required_es=6000,
            resistances={"chaos": 75},
            desired_affixes=["Energy Shield", "Cast Speed", "Chaos Resistance"]
        ),
        matcher.add_manual_build(
            "Spark Inquisitor",
            required_life=4500,
            resistances={"fire": 75, "cold": 75, "lightning": 75},
            desired_affixes=["Cast Speed", "Critical Strike Multiplier", "Maximum Life"]
        ),
    ]

    # Analyze meta
    analyzer = MetaAnalyzer()
    analyzer.analyze_builds(matcher.builds, league="Settlers")

    # Show results
    print("\nTop Meta Affixes:")
    for i, (affix_type, pop) in enumerate(analyzer.get_top_affixes(8), 1):
        print(f"{i:2d}. {affix_type:25s} - {pop.popularity_percent:5.1f}% "
              f"({pop.appearance_count}/{pop.total_builds} builds)")

    # Generate dynamic weights
    print("\nDynamic Weights (for RareItemEvaluator):")
    weights = analyzer.generate_dynamic_weights(
        base_weight=5.0,
        popularity_multiplier=0.1
    )

    for affix_type, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  {affix_type:25s}: {weight:5.1f}")

    return analyzer


def demo_weight_mapping():
    """Demo 2: Map meta weights to valuable_affixes.json format."""
    print("\n" + "=" * 80)
    print("DEMO 2: Weight Mapping for valuable_affixes.json")
    print("=" * 80)

    # Load current config
    config_path = Path("data/valuable_affixes.json")
    with open(config_path) as f:
        config = json.load(f)

    # Get meta weights
    analyzer = MetaAnalyzer()
    if analyzer.load_cache():
        print("\nLoaded cached meta analysis")
        weights = analyzer.generate_dynamic_weights()

        # Mapping from meta analyzer affix types to valuable_affixes.json keys
        affix_mapping = {
            'life': ['life', 'life_percent', 'life_regen'],
            'energy_shield': ['energy_shield', 'energy_shield_percent'],
            'resistances': ['fire_resistance', 'cold_resistance', 'lightning_resistance'],
            'chaos_resistance': ['chaos_resistance'],
            'movement_speed': ['movement_speed'],
            'attack_speed': ['attack_speed'],
            'cast_speed': ['cast_speed'],
            'spell_suppression': ['spell_suppression'],
            'critical_strike_multiplier': ['critical_strike_multiplier'],
            'attributes': ['strength', 'dexterity', 'intelligence'],
        }

        print("\nWeight Updates (showing how meta affects evaluation):")
        print("-" * 80)

        for meta_type, meta_weight in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:8]:
            config_keys = affix_mapping.get(meta_type, [])

            print(f"\n{meta_type.upper()} (meta weight: {meta_weight:.1f}):")
            for key in config_keys:
                if key in config:
                    old_weight = config[key].get('weight', 5)
                    # Suggest new weight based on meta
                    suggested_weight = min(10, int(meta_weight))
                    if suggested_weight != old_weight:
                        print(f"  {key:30s}: {old_weight} → {suggested_weight} "
                              f"({'↑' if suggested_weight > old_weight else '↓'})")
                    else:
                        print(f"  {key:30s}: {old_weight} (no change)")
    else:
        print("No cached meta analysis found. Run demo_manual_builds() first.")


def demo_build_scrapers():
    """Demo 3: Scrape builds from poe.ninja (if available)."""
    print("\n" + "=" * 80)
    print("DEMO 3: Build Scraping (poe.ninja)")
    print("=" * 80)

    print("\nNote: This requires poe.ninja API to be accessible.")
    print("The scraper will try to fetch top builds by DPS.\n")

    scraper = PoeNinjaBuildScraper(league="Settlers")

    try:
        builds = scraper.scrape_top_builds(limit=5, sort_by="dps")

        if builds:
            print(f"Successfully scraped {len(builds)} builds:")
            for i, build in enumerate(builds, 1):
                print(f"\n{i}. {build.build_name}")
                print(f"   Class: {build.char_class}/{build.ascendancy}")
                print(f"   Skill: {build.main_skill}")
                print(f"   DPS: {build.dps:,.0f}" if build.dps else "   DPS: N/A")
                print(f"   Life: {build.life:,}" if build.life else "   Life: N/A")
                print(f"   ES: {build.es:,}" if build.es else "   ES: N/A")
        else:
            print("No builds returned. The API structure may have changed,")
            print("or poe.ninja may be temporarily unavailable.")

    except Exception as e:
        print(f"Error scraping builds: {e}")
        print("This is expected if poe.ninja API is unavailable or has changed.")


def demo_pob_link_extraction():
    """Demo 4: Extract PoB links from text."""
    print("\n" + "=" * 80)
    print("DEMO 4: PoB Link Extraction")
    print("=" * 80)

    # Sample texts with PoB links
    test_cases = [
        "Check out my build: https://pobb.in/ABC123",
        "PoB here: pastebin.com/XYZ789",
        "My setup https://pobb.in/Test_Link-123 is pretty good",
        "No PoB link in this text",
    ]

    print("\nExtracting PoB links from sample texts:")
    for text in test_cases:
        link = extract_pob_link(text)
        status = "✓" if link else "✗"
        print(f"{status} '{text[:50]}...'")
        if link:
            print(f"  → {link}")


def demo_integration_workflow():
    """Demo 5: Complete integration workflow."""
    print("\n" + "=" * 80)
    print("DEMO 5: Complete Integration Workflow")
    print("=" * 80)

    print("\n1. SCRAPE BUILDS (manual entry for demo)")
    matcher = BuildMatcher()

    # Simulate meta builds
    popular_builds = [
        ("Lightning Strike Raider", 4000, 0, ["fire", "cold", "lightning"],
         ["Movement Speed", "Attack Speed", "Suppression"]),
        ("Righteous Fire Jugg", 8000, 0, ["fire", "chaos"],
         ["Life", "Fire Resistance", "Life Regen"]),
        ("CI Spark Inquis", 0, 6000, ["chaos"],
         ["Energy Shield", "Cast Speed"]),
        ("Poison BV PF", 5000, 0, ["chaos"],
         ["Attack Speed", "Chaos Resistance"]),
        ("Cold DoT Occultist", 0, 5500, ["chaos"],
         ["Energy Shield", "Cast Speed"]),
    ]

    for name, life, es, res_types, affixes in popular_builds:
        resistances = {res: 75 for res in res_types}
        matcher.add_manual_build(
            name,
            required_life=life,
            required_es=es,
            resistances=resistances,
            desired_affixes=affixes
        )

    print(f"Added {len(popular_builds)} meta builds")

    print("\n2. ANALYZE META")
    analyzer = MetaAnalyzer()
    analyzer.analyze_builds(matcher.builds, league="Settlers")

    top_affixes = analyzer.get_top_affixes(5)
    print(f"\nTop 5 Meta Affixes:")
    for affix_type, pop in top_affixes:
        print(f"  • {affix_type:20s} - {pop.popularity_percent:5.1f}%")

    print("\n3. GENERATE DYNAMIC WEIGHTS")
    weights = analyzer.generate_dynamic_weights()

    print("\nTop 5 Weights:")
    for affix_type, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {affix_type:20s} - {weight:5.1f}")

    print("\n4. INTEGRATION POINTS")
    print("  ✓ Weights cached to: data/meta_affixes.json")
    print("  ✓ Can be loaded by RareItemEvaluator")
    print("  ✓ Auto-updates when league changes")
    print("  ✓ Falls back to static config if stale")

    print("\n5. NEXT STEPS")
    print("  → Update RareItemEvaluator to read meta_affixes.json")
    print("  → Merge dynamic weights with static config")
    print("  → Boost weights for meta affixes (e.g., +2 bonus)")
    print("  → Re-evaluate items with updated weights")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("META-BASED DYNAMIC AFFIX WEIGHTING DEMO")
    print("=" * 80)

    # Run demos
    demo_manual_builds()
    demo_weight_mapping()
    demo_build_scrapers()
    demo_pob_link_extraction()
    demo_integration_workflow()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The meta analysis system enables:

1. BUILD SCRAPING
   - Fetch popular builds from poe.ninja, pobb.in, pastebin
   - Extract PoB codes from links
   - Parse build requirements

2. META ANALYSIS
   - Aggregate affix popularity across builds
   - Calculate appearance percentages
   - Track value ranges

3. DYNAMIC WEIGHTS
   - Generate weights based on meta popularity
   - Base weight + (popularity % × multiplier)
   - Higher weights for meta affixes

4. INTEGRATION
   - Cache results per league (data/meta_affixes.json)
   - Auto-update on league changes
   - Merge with static valuable_affixes.json config

5. BENEFITS
   - League-specific item evaluation
   - Automatically adapts to meta shifts
   - Identifies undervalued items for current meta
   - More accurate rare item pricing
    """)

    print("=" * 80)
