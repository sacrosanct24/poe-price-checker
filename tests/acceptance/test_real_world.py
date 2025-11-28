"""
Real-World Acceptance Tests

These tests make REAL API calls and validate against expected real-world behavior.
Results are collected for LLM review to catch issues that unit tests miss.

Run with: python -m pytest tests/acceptance/ -v --tb=short
Or standalone: python tests/acceptance/test_real_world.py
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import pytest


@dataclass
class AcceptanceResult:
    """Captures a test result for LLM review."""
    test_name: str
    category: str
    passed: bool
    actual_value: Any
    expected_range: Optional[str] = None
    notes: str = ""
    raw_data: dict = field(default_factory=dict)


class AcceptanceTestRunner:
    """Collects results for LLM analysis."""

    def __init__(self):
        self.results: list[AcceptanceResult] = []
        self.start_time = datetime.now()

    def add_result(self, result: AcceptanceResult):
        self.results.append(result)

    def get_summary(self) -> dict:
        """Generate summary for LLM review."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        return {
            "run_time": str(datetime.now() - self.start_time),
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/len(self.results)*100:.1f}%" if self.results else "N/A",
            "results": [
                {
                    "test": r.test_name,
                    "category": r.category,
                    "passed": r.passed,
                    "actual": r.actual_value,
                    "expected": r.expected_range,
                    "notes": r.notes,
                }
                for r in self.results
            ],
            "failed_tests": [
                {
                    "test": r.test_name,
                    "actual": r.actual_value,
                    "expected": r.expected_range,
                    "notes": r.notes,
                    "raw_data": r.raw_data,
                }
                for r in self.results if not r.passed
            ]
        }


# Global runner for collecting results
runner = AcceptanceTestRunner()


# =============================================================================
# API CONNECTIVITY TESTS
# =============================================================================

class TestAPIConnectivity:
    """Test that we can reach real APIs."""

    def test_poe_ninja_reachable(self):
        """Can we fetch data from poe.ninja?"""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI(league="Standard")

        try:
            # Try to get currency data
            data = ninja.get_currency_overview()

            has_data = data is not None and len(data.get("lines", [])) > 0

            runner.add_result(AcceptanceResult(
                test_name="poe_ninja_reachable",
                category="connectivity",
                passed=has_data,
                actual_value=f"{len(data.get('lines', []))} currency items" if data else "No data",
                expected_range="50+ currency items",
                notes="Basic connectivity to poe.ninja API",
                raw_data={"sample": data.get("lines", [])[:3] if data else []}
            ))

            assert has_data, "poe.ninja returned no data"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="poe_ninja_reachable",
                category="connectivity",
                passed=False,
                actual_value=str(e),
                expected_range="Successful connection",
                notes=f"Connection failed: {type(e).__name__}"
            ))
            raise

    def test_poe_watch_reachable(self):
        """Can we fetch data from poe.watch?"""
        from data_sources.pricing.poe_watch import PoeWatchAPI

        watch = PoeWatchAPI(league="Standard")

        try:
            # Try to get league info or item data
            leagues = watch.get_leagues()

            has_data = leagues is not None and len(leagues) > 0

            runner.add_result(AcceptanceResult(
                test_name="poe_watch_reachable",
                category="connectivity",
                passed=has_data,
                actual_value=f"{len(leagues)} leagues" if leagues else "No data",
                expected_range="1+ leagues",
                notes="Basic connectivity to poe.watch API",
                raw_data={"leagues": leagues[:5] if leagues else []}
            ))

            assert has_data, "poe.watch returned no data"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="poe_watch_reachable",
                category="connectivity",
                passed=False,
                actual_value=str(e),
                expected_range="Successful connection",
                notes=f"Connection failed: {type(e).__name__}"
            ))
            raise


# =============================================================================
# PRICE SANITY TESTS
# =============================================================================

class TestPriceSanity:
    """Test that prices are in reasonable real-world ranges."""

    def test_divine_orb_price_range(self):
        """Divine Orb should be worth significant chaos (typically 100-300c)."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI(league="Standard")

        try:
            price, source = ninja.get_currency_price("Divine Orb")

            # Divine typically 100-300c in Standard, but can vary
            reasonable = 50 <= price <= 500

            runner.add_result(AcceptanceResult(
                test_name="divine_orb_price",
                category="price_sanity",
                passed=reasonable,
                actual_value=f"{price:.1f}c",
                expected_range="50-500c (Standard league)",
                notes=f"Source: {source}. Price outside range may indicate market shift or API issue.",
                raw_data={"price": price, "source": source}
            ))

            assert reasonable, f"Divine Orb price {price}c outside expected range"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="divine_orb_price",
                category="price_sanity",
                passed=False,
                actual_value=str(e),
                expected_range="50-500c",
                notes=f"Failed to get price: {type(e).__name__}"
            ))
            raise

    def test_exalted_orb_cheaper_than_divine(self):
        """Exalted Orbs should be cheaper than Divine Orbs."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI(league="Standard")

        try:
            divine_price, _ = ninja.get_currency_price("Divine Orb")
            exalt_price, _ = ninja.get_currency_price("Exalted Orb")

            exalt_cheaper = exalt_price < divine_price
            ratio = divine_price / exalt_price if exalt_price > 0 else 0

            runner.add_result(AcceptanceResult(
                test_name="exalt_vs_divine",
                category="price_sanity",
                passed=exalt_cheaper,
                actual_value=f"Divine: {divine_price:.1f}c, Exalt: {exalt_price:.1f}c, Ratio: {ratio:.1f}x",
                expected_range="Divine > Exalt (typically 10-20x ratio)",
                notes="Exalts have been cheaper than Divines since 3.19",
                raw_data={"divine": divine_price, "exalt": exalt_price, "ratio": ratio}
            ))

            assert exalt_cheaper, f"Exalt ({exalt_price}c) not cheaper than Divine ({divine_price}c)"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="exalt_vs_divine",
                category="price_sanity",
                passed=False,
                actual_value=str(e),
                expected_range="Divine > Exalt",
                notes=f"Failed: {type(e).__name__}"
            ))
            raise

    def test_chaos_orb_is_one_chaos(self):
        """Chaos Orb should be worth exactly 1 chaos (it's the base currency)."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        ninja = PoeNinjaAPI(league="Standard")

        try:
            price, source = ninja.get_currency_price("Chaos Orb")

            is_one = 0.9 <= price <= 1.1  # Allow tiny floating point variance

            runner.add_result(AcceptanceResult(
                test_name="chaos_orb_base",
                category="price_sanity",
                passed=is_one,
                actual_value=f"{price:.2f}c",
                expected_range="1.0c (base currency)",
                notes="Chaos is the reference currency, should always be 1.0",
                raw_data={"price": price}
            ))

            assert is_one, f"Chaos Orb price {price}c should be 1.0"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="chaos_orb_base",
                category="price_sanity",
                passed=False,
                actual_value=str(e),
                expected_range="1.0c",
                notes=f"Failed: {type(e).__name__}"
            ))
            raise


# =============================================================================
# ITEM PARSER TESTS
# =============================================================================

class TestItemParser:
    """Test parsing of real item clipboard text."""

    SAMPLE_UNIQUE_ITEM = """Rarity: Unique
Headhunter
Leather Belt
--------
Requirements:
Level: 40
--------
Item Level: 75
--------
+25 to maximum Life (implicit)
--------
+55 to Strength
+77 to maximum Life
+48% to Cold Resistance
13% increased Damage with Hits against Rare monsters
When you Kill a Rare monster, you gain its Modifiers for 60 seconds
--------
Corrupted
"""

    SAMPLE_RARE_ITEM = """Rarity: Rare
Havoc Knuckle
Titan Gauntlets
--------
Quality: +20% (augmented)
Armour: 270 (augmented)
--------
Requirements:
Level: 69
Str: 98
--------
Sockets: R-R-R-R
--------
Item Level: 84
--------
+49 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+15% to Lightning Resistance
14% increased Armour
+52 to maximum Mana
"""

    def test_parse_unique_item(self):
        """Parse a real Headhunter item text."""
        from core.item_parser import ItemParser

        parser = ItemParser()

        try:
            parsed = parser.parse(self.SAMPLE_UNIQUE_ITEM)

            checks = {
                "name_correct": parsed.name == "Headhunter" if parsed else False,
                "rarity_unique": parsed.rarity.upper() == "UNIQUE" if parsed and parsed.rarity else False,
                "base_type": parsed.base_type == "Leather Belt" if parsed else False,
                "corrupted_detected": parsed.is_corrupted if parsed else False,
            }

            all_passed = all(checks.values())

            runner.add_result(AcceptanceResult(
                test_name="parse_unique_headhunter",
                category="parser",
                passed=all_passed,
                actual_value=str(checks),
                expected_range="All checks True",
                notes="Parsing a corrupted Headhunter",
                raw_data={
                    "parsed_name": parsed.name if parsed else None,
                    "parsed_rarity": parsed.rarity if parsed else None,
                    "parsed_base": parsed.base_type if parsed else None,
                    "parsed_corrupted": parsed.is_corrupted if parsed else None,
                }
            ))

            assert all_passed, f"Parser checks failed: {checks}"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="parse_unique_headhunter",
                category="parser",
                passed=False,
                actual_value=str(e),
                expected_range="Successful parse",
                notes=f"Parse failed: {type(e).__name__}"
            ))
            raise

    def test_parse_rare_item(self):
        """Parse a real rare item with multiple mods."""
        from core.item_parser import ItemParser

        parser = ItemParser()

        try:
            parsed = parser.parse(self.SAMPLE_RARE_ITEM)

            # ParsedItem uses 'explicits' not 'mods'
            mods = parsed.explicits or [] if parsed else []
            checks = {
                "has_name": bool(parsed.name) if parsed else False,
                "rarity_rare": parsed.rarity.upper() == "RARE" if parsed and parsed.rarity else False,
                "has_life_mod": any("Life" in mod for mod in mods),
                "has_resistance": any("Resistance" in mod for mod in mods),
                "sockets_detected": parsed.sockets is not None if parsed else False,
            }

            all_passed = all(checks.values())

            runner.add_result(AcceptanceResult(
                test_name="parse_rare_gloves",
                category="parser",
                passed=all_passed,
                actual_value=str(checks),
                expected_range="All checks True",
                notes="Parsing rare gloves with life and resistances",
                raw_data={
                    "parsed_name": parsed.name if parsed else None,
                    "mods_count": len(parsed.explicits) if parsed and parsed.explicits else 0,
                    "sockets": parsed.sockets if parsed else None,
                }
            ))

            assert all_passed, f"Parser checks failed: {checks}"

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="parse_rare_gloves",
                category="parser",
                passed=False,
                actual_value=str(e),
                expected_range="Successful parse",
                notes=f"Parse failed: {type(e).__name__}"
            ))
            raise


# =============================================================================
# MULTI-SOURCE CONSISTENCY TESTS
# =============================================================================

class TestMultiSourceConsistency:
    """Test that different pricing sources agree reasonably."""

    def test_divine_price_consistency(self):
        """poe.ninja and poe.watch should agree on Divine Orb within 20%."""
        from data_sources.pricing.poe_ninja import PoeNinjaAPI
        from data_sources.pricing.poe_watch import PoeWatchAPI

        ninja = PoeNinjaAPI(league="Standard")
        watch = PoeWatchAPI(league="Standard")

        try:
            ninja_price, _ = ninja.get_currency_price("Divine Orb")

            # Get from watch - use get_items_by_category for currency
            watch_data = watch.get_items_by_category("currency")
            watch_price = None
            if watch_data:
                for item in watch_data:
                    if item.get("name", "").lower() == "divine orb":
                        watch_price = item.get("mean")
                        break

            if ninja_price and watch_price:
                diff_pct = abs(ninja_price - watch_price) / max(ninja_price, watch_price) * 100
                within_tolerance = diff_pct <= 20

                runner.add_result(AcceptanceResult(
                    test_name="divine_price_consistency",
                    category="consistency",
                    passed=within_tolerance,
                    actual_value=f"Ninja: {ninja_price:.1f}c, Watch: {watch_price:.1f}c, Diff: {diff_pct:.1f}%",
                    expected_range="Within 20% of each other",
                    notes="Large divergence may indicate stale data or market volatility",
                    raw_data={"ninja": ninja_price, "watch": watch_price, "diff_pct": diff_pct}
                ))

                assert within_tolerance, f"Price difference {diff_pct:.1f}% exceeds 20% tolerance"
            else:
                runner.add_result(AcceptanceResult(
                    test_name="divine_price_consistency",
                    category="consistency",
                    passed=False,
                    actual_value=f"Ninja: {ninja_price}, Watch: {watch_price}",
                    expected_range="Both sources return prices",
                    notes="One or both sources returned no data"
                ))
                pytest.skip("Could not get prices from both sources")

        except Exception as e:
            runner.add_result(AcceptanceResult(
                test_name="divine_price_consistency",
                category="consistency",
                passed=False,
                actual_value=str(e),
                expected_range="Both sources agree",
                notes=f"Failed: {type(e).__name__}"
            ))
            raise


# =============================================================================
# MAIN - Generate Report for LLM Review
# =============================================================================

def generate_llm_report():
    """Generate a report formatted for LLM review."""
    summary = runner.get_summary()

    report = f"""
# Real-World Acceptance Test Results
Generated: {datetime.now().isoformat()}
Duration: {summary['run_time']}

## Summary
- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['passed']}
- **Failed**: {summary['failed']}
- **Pass Rate**: {summary['pass_rate']}

## Results by Category

"""

    # Group by category
    by_category = {}
    for result in summary['results']:
        cat = result['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(result)

    for category, results in by_category.items():
        report += f"### {category.upper()}\n\n"
        for r in results:
            status = "[PASS]" if r['passed'] else "[FAIL]"
            report += f"- {status} **{r['test']}**\n"
            report += f"  - Actual: {r['actual']}\n"
            report += f"  - Expected: {r['expected']}\n"
            if r['notes']:
                report += f"  - Notes: {r['notes']}\n"
            report += "\n"

    if summary['failed_tests']:
        report += "## Failed Tests - Details\n\n"
        for f in summary['failed_tests']:
            report += f"### {f['test']}\n"
            report += f"- **Actual**: {f['actual']}\n"
            report += f"- **Expected**: {f['expected']}\n"
            report += f"- **Notes**: {f['notes']}\n"
            if f['raw_data']:
                report += f"- **Raw Data**: ```{json.dumps(f['raw_data'], indent=2)}```\n"
            report += "\n"

    report += """
## Questions for LLM Review

1. Do the Divine Orb prices seem reasonable for the current market?
2. Are there any unexpected failures that might indicate bugs?
3. Do the parser results look correct for the sample items?
4. Are there any red flags in the raw data?

Please analyze these results and flag any concerns.
"""

    return report, summary


def run_tests_directly():
    """Run tests directly without pytest to capture results in global runner."""
    import sys
    from pathlib import Path
    # Add project root to path for imports
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    test_classes = [
        TestAPIConnectivity(),
        TestPriceSanity(),
        TestItemParser(),
        TestMultiSourceConsistency(),
    ]

    for test_instance in test_classes:
        # Get all test methods
        test_methods = [m for m in dir(test_instance) if m.startswith("test_")]

        for method_name in test_methods:
            method = getattr(test_instance, method_name)
            try:
                print(f"  Running {test_instance.__class__.__name__}::{method_name}...", end=" ")
                method()
                print("PASSED")
            except Exception as e:
                print(f"FAILED: {e}")


if __name__ == "__main__":
    import sys

    print("Running Real-World Acceptance Tests...")
    print("=" * 60)

    # Run tests directly to capture results in global runner
    run_tests_directly()

    # Generate report
    report, summary = generate_llm_report()

    print("\n" + "=" * 60)
    print(report)

    # Save report
    report_path = "tests/acceptance/latest_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")

    # Also save JSON for programmatic access
    json_path = "tests/acceptance/latest_report.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"JSON saved to: {json_path}")
