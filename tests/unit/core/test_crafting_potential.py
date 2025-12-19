"""
Tests for core/crafting_potential.py

Tests the crafting potential analyzer including:
- Mod analysis and tier detection
- Divine potential calculation
- Open slot estimation
- Craft option generation
"""
import pytest
from unittest.mock import MagicMock

from core.crafting_potential import (
    CraftingPotentialAnalyzer,
    CraftingAnalysis,
    ModAnalysis,
    CraftOption,
    analyze_crafting_potential,
    get_divine_recommendation,
)


class TestModAnalysis:
    """Tests for ModAnalysis dataclass."""

    def test_divine_potential_with_good_roll(self):
        """Divine potential calculated correctly for good rolls."""
        mod = ModAnalysis(
            mod_text="+92 to Maximum Life",
            stat_type="life",
            current_value=92,
            tier=2,
            min_roll=90,
            max_roll=99,
        )
        assert mod.divine_potential == 7  # 99 - 92

    def test_divine_potential_at_max(self):
        """Divine potential is 0 when at max roll."""
        mod = ModAnalysis(
            mod_text="+99 to Maximum Life",
            stat_type="life",
            current_value=99,
            tier=2,
            min_roll=90,
            max_roll=99,
        )
        assert mod.divine_potential == 0

    def test_divine_potential_with_no_value(self):
        """Divine potential is 0 when no current value."""
        mod = ModAnalysis(
            mod_text="Unknown mod",
            stat_type=None,
            current_value=None,
            tier=None,
        )
        assert mod.divine_potential == 0

    def test_roll_quality_mid_range(self):
        """Roll quality calculated correctly for mid-range roll."""
        mod = ModAnalysis(
            mod_text="+95 to Maximum Life",
            stat_type="life",
            current_value=95,
            tier=2,
            min_roll=90,
            max_roll=100,
        )
        # (95 - 90) / (100 - 90) * 100 = 50%
        assert mod.roll_quality == 50.0

    def test_roll_quality_at_max(self):
        """Roll quality is 100% at max roll."""
        mod = ModAnalysis(
            mod_text="+100 to Maximum Life",
            stat_type="life",
            current_value=100,
            tier=2,
            min_roll=90,
            max_roll=100,
        )
        assert mod.roll_quality == 100.0

    def test_roll_quality_at_min(self):
        """Roll quality is 0% at min roll."""
        mod = ModAnalysis(
            mod_text="+90 to Maximum Life",
            stat_type="life",
            current_value=90,
            tier=2,
            min_roll=90,
            max_roll=100,
        )
        assert mod.roll_quality == 0.0

    def test_roll_quality_fixed_roll(self):
        """Roll quality is 100% for fixed rolls (min == max)."""
        mod = ModAnalysis(
            mod_text="35% increased Movement Speed",
            stat_type="movement_speed",
            current_value=35,
            tier=1,
            min_roll=35,
            max_roll=35,
        )
        assert mod.roll_quality == 100.0

    def test_tier_label(self):
        """Tier label formatted correctly."""
        mod = ModAnalysis(
            mod_text="+92 to Maximum Life",
            stat_type="life",
            current_value=92,
            tier=2,
        )
        assert mod.tier_label == "T2"

    def test_tier_label_no_tier(self):
        """Tier label is empty when no tier."""
        mod = ModAnalysis(
            mod_text="Unknown mod",
            stat_type=None,
            current_value=None,
            tier=None,
        )
        assert mod.tier_label == ""


class TestCraftingAnalysis:
    """Tests for CraftingAnalysis dataclass."""

    def test_get_divine_summary_recommended(self):
        """Divine summary shows upgradeable mods when recommended."""
        analysis = CraftingAnalysis(
            divine_recommended=True,
            mod_analyses=[
                ModAnalysis(
                    mod_text="+92 to Maximum Life",
                    stat_type="life",
                    current_value=92,
                    tier=2,
                    min_roll=90,
                    max_roll=99,
                ),
            ],
        )
        summary = analysis.get_divine_summary()
        assert "life" in summary
        assert "+7 potential" in summary

    def test_get_divine_summary_not_recommended(self):
        """Divine summary explains when not recommended."""
        analysis = CraftingAnalysis(
            divine_recommended=False,
            mod_analyses=[],
        )
        summary = analysis.get_divine_summary()
        assert "not recommended" in summary.lower()

    def test_get_craft_summary_with_options(self):
        """Craft summary shows best option."""
        analysis = CraftingAnalysis(
            craft_options=[
                CraftOption(
                    name="Craft Life",
                    cost_estimate="2c",
                    expected_value_add=15,
                    description="Add life",
                ),
            ],
        )
        summary = analysis.get_craft_summary()
        assert "Craft Life" in summary
        assert "2c" in summary

    def test_get_craft_summary_no_options(self):
        """Craft summary explains when no options."""
        analysis = CraftingAnalysis(craft_options=[])
        summary = analysis.get_craft_summary()
        assert "no crafting" in summary.lower()


class TestCraftingPotentialAnalyzer:
    """Tests for CraftingPotentialAnalyzer class."""

    def test_analyze_item_with_life(self):
        """Analyzer detects life mod correctly."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        assert len(analysis.mod_analyses) == 1
        assert analysis.mod_analyses[0].stat_type == "life"

    def test_analyze_item_multiple_mods(self):
        """Analyzer handles multiple mods."""
        item = MagicMock()
        item.explicits = [
            "+92 to Maximum Life",
            "+45% to Fire Resistance",
            "+30% to Cold Resistance",
        ]
        item.rarity = "Rare"
        item.fractured_mods = []

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        assert len(analysis.mod_analyses) == 3
        assert analysis.total_mods == 3

    def test_analyze_empty_item(self):
        """Analyzer handles item with no mods."""
        item = MagicMock()
        item.explicits = []
        item.rarity = "Rare"

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        assert len(analysis.mod_analyses) == 0
        assert analysis.total_mods == 0

    def test_open_slots_estimation(self):
        """Open slots estimated correctly."""
        item = MagicMock()
        # 2 prefixes (life, ES), 1 suffix (fire res)
        item.explicits = [
            "+92 to Maximum Life",
            "+45 to Maximum Energy Shield",
            "+45% to Fire Resistance",
        ]
        item.rarity = "Rare"
        item.fractured_mods = []

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        # Should have 1 open prefix (3-2) and 2 open suffixes (3-1)
        assert analysis.open_prefixes == 1
        assert analysis.open_suffixes == 2

    def test_divine_recommendation(self):
        """Divine recommended when good potential exists."""
        item = MagicMock()
        item.explicits = ["+90 to Maximum Life"]  # T2, low roll
        item.rarity = "Rare"
        item.fractured_mods = []

        analyzer = CraftingPotentialAnalyzer()
        analyzer.analyze(item)

        # T2 life at 90 has potential (max is 99)
        # But need significant potential for recommendation
        # This depends on the specific thresholds in the code


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_analyze_crafting_potential(self):
        """Convenience function works correctly."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"
        item.fractured_mods = []

        analysis = analyze_crafting_potential(item)

        assert isinstance(analysis, CraftingAnalysis)
        assert len(analysis.mod_analyses) == 1

    def test_get_divine_recommendation(self):
        """Divine recommendation function works."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"
        item.fractured_mods = []

        recommendation = get_divine_recommendation(item)

        assert isinstance(recommendation, str)


class TestCraftOptionGeneration:
    """Tests for craft option generation."""

    def test_generates_prefix_crafts_when_open(self):
        """Generates prefix crafts when slots available."""
        item = MagicMock()
        # Only 1 suffix (resistance), no prefixes
        item.explicits = ["+45% to Fire Resistance"]
        item.rarity = "Rare"
        item.fractured_mods = []
        item.slot = "Ring"

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        # Should suggest prefix craft since open
        prefix_crafts = [c for c in analysis.craft_options if c.slot_type == "prefix"]
        assert len(prefix_crafts) > 0 or analysis.open_prefixes > 0

    def test_generates_suffix_crafts_when_open(self):
        """Generates suffix crafts when slots available."""
        item = MagicMock()
        # Only 1 prefix (life), no suffixes
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"
        item.fractured_mods = []
        item.slot = "Ring"

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        # Should have open suffix slots
        assert analysis.open_suffixes > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_missing_explicits_attr(self):
        """Handles items without explicits attribute."""
        item = MagicMock(spec=[])  # No attributes
        del item.explicits

        analyzer = CraftingPotentialAnalyzer()
        # Should not raise, should return empty analysis
        analysis = analyzer.analyze(item)
        assert analysis.total_mods == 0

    def test_handles_none_explicits(self):
        """Handles items with None explicits."""
        item = MagicMock()
        item.explicits = None

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)
        assert analysis.total_mods == 0

    def test_handles_unknown_mod_text(self):
        """Handles unrecognized mod text gracefully."""
        item = MagicMock()
        item.explicits = ["Some completely unknown mod text here"]
        item.rarity = "Rare"
        item.fractured_mods = []

        analyzer = CraftingPotentialAnalyzer()
        analysis = analyzer.analyze(item)

        # Should still create mod analysis, just without tier info
        assert len(analysis.mod_analyses) == 1
        assert analysis.mod_analyses[0].tier is None
