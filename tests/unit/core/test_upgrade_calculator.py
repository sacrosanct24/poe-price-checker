"""Tests for core/upgrade_calculator.py - Upgrade impact calculation."""

import pytest

from core.upgrade_calculator import (
    ItemStats,
    UpgradeImpact,
    ResistanceGaps,
    ItemStatExtractor,
    UpgradeCalculator,
)
from core.build_stat_calculator import BuildStats


# =============================================================================
# ItemStats Tests
# =============================================================================


class TestItemStats:
    """Tests for ItemStats dataclass."""

    def test_default_values(self):
        """Should have zero default values."""
        stats = ItemStats()
        assert stats.flat_life == 0.0
        assert stats.fire_res == 0.0
        assert stats.strength == 0.0

    def test_total_ele_res(self):
        """Should sum elemental resistances."""
        stats = ItemStats(fire_res=30, cold_res=25, lightning_res=20)
        assert stats.total_ele_res() == 75

    def test_total_all_res(self):
        """Should sum all resistances including chaos."""
        stats = ItemStats(fire_res=30, cold_res=25, lightning_res=20, chaos_res=10)
        assert stats.total_all_res() == 85

    def test_total_attributes(self):
        """Should sum all attributes."""
        stats = ItemStats(strength=50, dexterity=30, intelligence=20)
        assert stats.total_attributes() == 100


# =============================================================================
# UpgradeImpact Tests
# =============================================================================


class TestUpgradeImpact:
    """Tests for UpgradeImpact dataclass."""

    def test_default_values(self):
        """Should have zero default values."""
        impact = UpgradeImpact()
        assert impact.life_delta == 0.0
        assert impact.is_upgrade is False
        assert impact.improvements == []

    def test_get_summary_with_life(self):
        """Summary should include life changes."""
        impact = UpgradeImpact(effective_life_delta=50.0)
        summary = impact.get_summary()
        assert "+50" in summary
        assert "life" in summary.lower()

    def test_get_summary_with_es(self):
        """Summary should include ES changes."""
        impact = UpgradeImpact(effective_es_delta=100.0)
        summary = impact.get_summary()
        assert "+100" in summary
        assert "ES" in summary

    def test_get_summary_with_resistances(self):
        """Summary should include resistance changes."""
        impact = UpgradeImpact(
            fire_res_delta=10, cold_res_delta=15,
            lightning_res_delta=5, chaos_res_delta=0
        )
        summary = impact.get_summary()
        assert "+30" in summary
        assert "res" in summary.lower()

    def test_get_summary_with_attributes(self):
        """Summary should include attribute changes."""
        impact = UpgradeImpact(strength_delta=20, dexterity_delta=10)
        summary = impact.get_summary()
        assert "+30" in summary
        assert "attributes" in summary.lower()

    def test_get_summary_no_changes(self):
        """Summary should handle no significant changes."""
        impact = UpgradeImpact()
        summary = impact.get_summary()
        assert "No significant change" in summary

    def test_get_summary_negative_values(self):
        """Summary should handle negative values."""
        impact = UpgradeImpact(effective_life_delta=-50.0)
        summary = impact.get_summary()
        assert "-50" in summary


# =============================================================================
# ResistanceGaps Tests
# =============================================================================


class TestResistanceGaps:
    """Tests for ResistanceGaps dataclass."""

    def test_total_ele_gap(self):
        """Should sum elemental gaps."""
        gaps = ResistanceGaps(fire_gap=10, cold_gap=5, lightning_gap=15)
        assert gaps.total_ele_gap() == 30

    def test_has_gaps_true(self):
        """Should detect when gaps exist."""
        gaps = ResistanceGaps(fire_gap=10)
        assert gaps.has_gaps() is True

    def test_has_gaps_false(self):
        """Should detect when no gaps exist."""
        gaps = ResistanceGaps()
        assert gaps.has_gaps() is False

    def test_has_gaps_chaos_only(self):
        """Should detect chaos-only gaps."""
        gaps = ResistanceGaps(chaos_gap=20)
        assert gaps.has_gaps() is True


# =============================================================================
# ItemStatExtractor Tests
# =============================================================================


class TestItemStatExtractor:
    """Tests for ItemStatExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ItemStatExtractor()

    def test_extract_flat_life(self, extractor):
        """Should extract flat life."""
        mods = ["+65 to maximum Life"]
        stats = extractor.extract(mods)
        assert stats.flat_life == 65.0

    def test_extract_percent_life(self, extractor):
        """Should extract percent life."""
        mods = ["10% increased maximum Life"]
        stats = extractor.extract(mods)
        assert stats.percent_life == 10.0

    def test_extract_fire_resistance(self, extractor):
        """Should extract fire resistance."""
        mods = ["+35% to Fire Resistance"]
        stats = extractor.extract(mods)
        assert stats.fire_res == 35.0

    def test_extract_all_ele_resistance(self, extractor):
        """Should apply all ele res to each element."""
        mods = ["+12% to all Elemental Resistances"]
        stats = extractor.extract(mods)
        assert stats.fire_res == 12.0
        assert stats.cold_res == 12.0
        assert stats.lightning_res == 12.0

    def test_extract_all_attributes(self, extractor):
        """Should apply all attributes to each stat."""
        mods = ["+10 to all Attributes"]
        stats = extractor.extract(mods)
        assert stats.strength == 10.0
        assert stats.dexterity == 10.0
        assert stats.intelligence == 10.0

    def test_extract_strength_dexterity(self, extractor):
        """Should extract dual attributes."""
        mods = ["+20 to Strength and Dexterity"]
        stats = extractor.extract(mods)
        assert stats.strength == 20.0
        assert stats.dexterity == 20.0
        assert stats.intelligence == 0.0

    def test_extract_single_strength(self, extractor):
        """Should extract single attribute."""
        mods = ["+30 to Strength"]
        stats = extractor.extract(mods)
        assert stats.strength == 30.0

    def test_extract_attack_speed(self, extractor):
        """Should extract attack speed."""
        mods = ["15% increased Attack Speed"]
        stats = extractor.extract(mods)
        assert stats.attack_speed == 15.0

    def test_extract_crit_multi(self, extractor):
        """Should extract crit multi."""
        mods = ["+25% to Critical Strike Multiplier"]
        stats = extractor.extract(mods)
        assert stats.crit_multi == 25.0

    def test_extract_movement_speed(self, extractor):
        """Should extract movement speed."""
        mods = ["30% increased Movement Speed"]
        stats = extractor.extract(mods)
        assert stats.movement_speed == 30.0

    def test_extract_multiple_mods(self, extractor):
        """Should extract multiple mods."""
        mods = [
            "+70 to maximum Life",
            "+40% to Fire Resistance",
            "+35% to Cold Resistance",
            "+25 to Strength",
        ]
        stats = extractor.extract(mods)
        assert stats.flat_life == 70.0
        assert stats.fire_res == 40.0
        assert stats.cold_res == 35.0
        assert stats.strength == 25.0

    def test_extract_empty_mods(self, extractor):
        """Should handle empty mod list."""
        stats = extractor.extract([])
        assert stats.flat_life == 0.0
        assert stats.total_all_res() == 0.0


# =============================================================================
# UpgradeCalculator Tests
# =============================================================================


class TestUpgradeCalculator:
    """Tests for UpgradeCalculator."""

    @pytest.fixture
    def basic_build_stats(self):
        """Create basic build stats."""
        return BuildStats(
            total_life=5000,
            total_es=200,
            life_inc=150.0,
            es_inc=20.0,
            armour_inc=100.0,
            fire_overcap=20.0,
            cold_overcap=-10.0,  # 10% under cap
            lightning_overcap=15.0,
            chaos_res=30.0,
        )

    @pytest.fixture
    def calculator(self, basic_build_stats):
        """Create calculator with build stats."""
        return UpgradeCalculator(basic_build_stats)

    def test_calculate_resistance_gaps(self, calculator):
        """Should calculate resistance gaps from build stats."""
        gaps = calculator.calculate_resistance_gaps()
        assert gaps.fire_gap == 0  # Has 20% overcap
        assert gaps.cold_gap == 10  # 10% under cap
        assert gaps.lightning_gap == 0  # Has 15% overcap
        assert gaps.chaos_gap == 45  # 75 - 30 = 45

    def test_calculate_upgrade_life_increase(self, calculator):
        """Should calculate life upgrade correctly."""
        new_mods = ["+80 to maximum Life"]
        current_mods = ["+60 to maximum Life"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.life_delta == 20.0
        assert impact.effective_life_delta > 20.0  # Scaled by life%

    def test_calculate_upgrade_resistance_improvement(self, calculator):
        """Should calculate resistance upgrade."""
        new_mods = ["+40% to Cold Resistance"]
        current_mods = ["+20% to Cold Resistance"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.cold_res_delta == 20.0
        assert impact.cold_res_gap_covered > 0  # Covers part of gap

    def test_calculate_upgrade_empty_slot(self, calculator):
        """Should handle upgrade to empty slot."""
        new_mods = ["+70 to maximum Life", "+30% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new_mods, current_item_mods=None)

        assert impact.life_delta == 70.0
        assert impact.fire_res_delta == 30.0

    def test_calculate_upgrade_is_upgrade(self, calculator):
        """Should identify clear upgrades."""
        new_mods = [
            "+90 to maximum Life",
            "+40% to Cold Resistance",  # Covers gap
            "+30% to Chaos Resistance",  # Also covers gap
        ]
        current_mods = ["+50 to maximum Life"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.is_upgrade is True

    def test_calculate_upgrade_is_downgrade(self, calculator):
        """Should identify clear downgrades."""
        new_mods = ["+30 to maximum Life"]
        current_mods = [
            "+90 to maximum Life",
            "+40% to Fire Resistance",
            "+40% to Cold Resistance",
        ]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.is_downgrade is True

    def test_calculate_upgrade_is_sidegrade(self, calculator):
        """Should identify sidegrades."""
        new_mods = ["+70 to maximum Life", "+20% to Fire Resistance"]
        current_mods = ["+65 to maximum Life", "+25% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.is_sidegrade is True

    def test_compare_items(self, calculator):
        """compare_items should return detailed comparison."""
        new_mods = ["+80 to maximum Life", "+35% to Cold Resistance"]
        current_mods = ["+60 to maximum Life", "+20% to Cold Resistance"]

        result = calculator.compare_items(new_mods, current_mods)

        assert "impact" in result
        assert "gaps" in result
        assert "summary" in result
        assert "is_upgrade" in result
        assert "improvements" in result
        assert "losses" in result

    def test_strength_adds_life(self, calculator):
        """Strength should contribute to effective life."""
        new_mods = ["+50 to Strength"]
        current_mods = []

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        # 50 str = 25 base life, scaled by life%
        assert impact.strength_delta == 50.0
        assert impact.effective_life_delta > 0  # Life from str


class TestUpgradeCalculatorWithoutBuildStats:
    """Tests for UpgradeCalculator without build stats."""

    def test_works_without_build_stats(self):
        """Should work with default build stats."""
        calculator = UpgradeCalculator()

        new_mods = ["+70 to maximum Life"]
        current_mods = ["+50 to maximum Life"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert impact.life_delta == 20.0

    def test_improvements_list_populated(self):
        """Should populate improvements list."""
        calculator = UpgradeCalculator()

        new_mods = ["+100 to maximum Life", "+40% to Fire Resistance"]
        current_mods = []

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert len(impact.improvements) >= 1
        assert any("life" in imp.lower() for imp in impact.improvements)

    def test_losses_list_populated(self):
        """Should populate losses list."""
        calculator = UpgradeCalculator()

        new_mods = []
        current_mods = ["+100 to maximum Life", "+40% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new_mods, current_mods)

        assert len(impact.losses) >= 1
