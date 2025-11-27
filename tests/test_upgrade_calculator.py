"""
Tests for the Upgrade Impact Calculator.

Tests:
- Item stat extraction from mods
- Resistance gap calculation
- Upgrade impact calculation
- Scaling application
"""
import pytest
from core.upgrade_calculator import (
    ItemStatExtractor,
    ItemStats,
    UpgradeCalculator,
    UpgradeImpact,
    ResistanceGaps,
)
from core.build_stat_calculator import BuildStats


class TestItemStatExtractor:
    """Tests for ItemStatExtractor."""

    def test_extract_flat_life(self):
        """Test extracting flat life mod."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["+80 to maximum Life"])
        assert stats.flat_life == 80

    def test_extract_flat_es(self):
        """Test extracting flat ES mod."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["+150 to maximum Energy Shield"])
        assert stats.flat_es == 150

    def test_extract_resistances(self):
        """Test extracting resistance mods."""
        extractor = ItemStatExtractor()
        stats = extractor.extract([
            "+40% to Fire Resistance",
            "+35% to Cold Resistance",
            "+30% to Lightning Resistance",
            "+20% to Chaos Resistance",
        ])
        assert stats.fire_res == 40
        assert stats.cold_res == 35
        assert stats.lightning_res == 30
        assert stats.chaos_res == 20

    def test_extract_all_ele_res(self):
        """Test extracting all elemental resistances mod."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["+12% to all Elemental Resistances"])
        assert stats.fire_res == 12
        assert stats.cold_res == 12
        assert stats.lightning_res == 12
        assert stats.chaos_res == 0  # Not elemental

    def test_extract_attributes(self):
        """Test extracting attribute mods."""
        extractor = ItemStatExtractor()
        stats = extractor.extract([
            "+50 to Strength",
            "+40 to Dexterity",
            "+30 to Intelligence",
        ])
        assert stats.strength == 50
        assert stats.dexterity == 40
        assert stats.intelligence == 30

    def test_extract_all_attributes(self):
        """Test extracting all attributes mod."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["+20 to all Attributes"])
        assert stats.strength == 20
        assert stats.dexterity == 20
        assert stats.intelligence == 20

    def test_extract_dual_attributes(self):
        """Test extracting dual attribute mods."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["+25 to Strength and Dexterity"])
        assert stats.strength == 25
        assert stats.dexterity == 25
        assert stats.intelligence == 0

    def test_extract_movement_speed(self):
        """Test extracting movement speed mod."""
        extractor = ItemStatExtractor()
        stats = extractor.extract(["30% increased Movement Speed"])
        assert stats.movement_speed == 30

    def test_extract_multiple_mods(self):
        """Test extracting multiple mods at once."""
        extractor = ItemStatExtractor()
        stats = extractor.extract([
            "+80 to maximum Life",
            "+40% to Fire Resistance",
            "+30% to Cold Resistance",
            "+50 to Strength",
            "25% increased Movement Speed",
        ])
        assert stats.flat_life == 80
        assert stats.fire_res == 40
        assert stats.cold_res == 30
        assert stats.strength == 50
        assert stats.movement_speed == 25

    def test_item_stats_total_ele_res(self):
        """Test total elemental resistance calculation."""
        stats = ItemStats(fire_res=40, cold_res=35, lightning_res=30)
        assert stats.total_ele_res() == 105

    def test_item_stats_total_all_res(self):
        """Test total all resistance calculation."""
        stats = ItemStats(fire_res=40, cold_res=35, lightning_res=30, chaos_res=20)
        assert stats.total_all_res() == 125


class TestResistanceGaps:
    """Tests for resistance gap calculation."""

    def test_no_gaps_when_overcapped(self):
        """Test no gaps when resistances are overcapped."""
        stats = BuildStats(
            fire_overcap=10.0,
            cold_overcap=15.0,
            lightning_overcap=20.0,
            chaos_res=75.0,
        )
        calculator = UpgradeCalculator(stats)
        gaps = calculator.calculate_resistance_gaps()

        assert gaps.fire_gap == 0
        assert gaps.cold_gap == 0
        assert gaps.lightning_gap == 0
        assert gaps.chaos_gap == 0

    def test_detects_fire_gap(self):
        """Test detecting fire resistance gap."""
        stats = BuildStats(fire_overcap=-10.0)  # 10% under cap
        calculator = UpgradeCalculator(stats)
        gaps = calculator.calculate_resistance_gaps()

        assert gaps.fire_gap == 10.0

    def test_detects_chaos_gap(self):
        """Test detecting chaos resistance gap."""
        stats = BuildStats(chaos_res=30.0)  # 45% below 75 cap
        calculator = UpgradeCalculator(stats)
        gaps = calculator.calculate_resistance_gaps()

        assert gaps.chaos_gap == 45.0

    def test_has_gaps(self):
        """Test has_gaps method."""
        gaps_with = ResistanceGaps(fire_gap=10.0)
        gaps_without = ResistanceGaps()

        assert gaps_with.has_gaps() is True
        assert gaps_without.has_gaps() is False


class TestUpgradeCalculator:
    """Tests for UpgradeCalculator."""

    @pytest.fixture
    def build_stats(self):
        """Create sample build stats."""
        return BuildStats(
            life_inc=158.0,
            total_life=5000.0,
            es_inc=50.0,
            total_es=500.0,
            fire_overcap=10.0,
            cold_overcap=-5.0,  # 5% gap
            lightning_overcap=15.0,
            chaos_res=30.0,  # 45% gap
        )

    @pytest.fixture
    def calculator(self, build_stats):
        """Create calculator with build stats."""
        return UpgradeCalculator(build_stats)

    def test_calculate_life_upgrade(self, calculator):
        """Test calculating life upgrade with scaling."""
        current = ["+60 to maximum Life"]
        new = ["+80 to maximum Life"]

        impact = calculator.calculate_upgrade(new, current)

        # +20 life with 158% inc = +20 * 2.58 = +51.6 effective
        assert impact.life_delta == 20
        assert impact.effective_life_delta > 50
        assert impact.is_upgrade is True

    def test_calculate_resistance_upgrade(self, calculator):
        """Test calculating resistance upgrade."""
        current = ["+30% to Fire Resistance"]
        new = ["+45% to Fire Resistance", "+20% to Chaos Resistance"]

        impact = calculator.calculate_upgrade(new, current)

        assert impact.fire_res_delta == 15
        assert impact.chaos_res_delta == 20
        assert impact.is_upgrade is True

    def test_gap_coverage_calculation(self, calculator):
        """Test resistance gap coverage calculation."""
        # Build has 5% cold gap
        current = []
        new = ["+10% to Cold Resistance"]  # Covers 100% of gap

        impact = calculator.calculate_upgrade(new, current)

        assert impact.cold_res_delta == 10
        assert impact.cold_res_gap_covered == 100.0  # Full gap covered

    def test_partial_gap_coverage(self, calculator):
        """Test partial gap coverage."""
        # Build has 45% chaos gap
        current = []
        new = ["+20% to Chaos Resistance"]  # Covers ~44% of gap

        impact = calculator.calculate_upgrade(new, current)

        assert impact.chaos_res_delta == 20
        assert 40 < impact.chaos_res_gap_covered < 50

    def test_downgrade_detection(self, calculator):
        """Test detecting downgrades."""
        current = ["+80 to maximum Life", "+45% to Fire Resistance"]
        new = ["+40 to maximum Life"]  # Losing life and fire res

        impact = calculator.calculate_upgrade(new, current)

        assert impact.life_delta == -40
        assert impact.fire_res_delta == -45
        assert impact.is_downgrade is True
        assert len(impact.losses) > 0

    def test_sidegrade_detection(self, calculator):
        """Test detecting sidegrades."""
        current = ["+60 to maximum Life", "+30% to Fire Resistance"]
        new = ["+50 to maximum Life", "+35% to Fire Resistance", "+10 to Strength"]

        impact = calculator.calculate_upgrade(new, current)

        # Small changes in either direction
        assert impact.is_sidegrade is True or abs(impact.upgrade_score) <= 10

    def test_empty_slot_upgrade(self, calculator):
        """Test upgrading from empty slot."""
        current = None  # Empty slot
        new = ["+80 to maximum Life", "+40% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new, current)

        assert impact.life_delta == 80
        assert impact.fire_res_delta == 40
        assert impact.is_upgrade is True

    def test_improvements_list(self, calculator):
        """Test improvements list is populated."""
        current = ["+50 to maximum Life"]
        new = ["+80 to maximum Life", "+30% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new, current)

        assert len(impact.improvements) >= 2
        assert any("life" in imp.lower() for imp in impact.improvements)
        assert any("fire" in imp.lower() for imp in impact.improvements)

    def test_losses_list(self, calculator):
        """Test losses list is populated."""
        current = ["+80 to maximum Life", "+40% to Fire Resistance"]
        new = ["+50 to maximum Life"]

        impact = calculator.calculate_upgrade(new, current)

        assert len(impact.losses) >= 1

    def test_get_summary(self, calculator):
        """Test summary string generation."""
        current = ["+50 to maximum Life"]
        new = ["+80 to maximum Life", "+30% to Fire Resistance"]

        impact = calculator.calculate_upgrade(new, current)
        summary = impact.get_summary()

        assert "life" in summary.lower()
        assert "res" in summary.lower()

    def test_compare_items_returns_dict(self, calculator):
        """Test compare_items returns proper dict structure."""
        current = ["+50 to maximum Life"]
        new = ["+80 to maximum Life"]

        result = calculator.compare_items(new, current)

        assert "impact" in result
        assert "gaps" in result
        assert "summary" in result
        assert "is_upgrade" in result
        assert "improvements" in result
        assert "losses" in result


class TestUpgradeImpact:
    """Tests for UpgradeImpact dataclass."""

    def test_get_summary_life_only(self):
        """Test summary with only life change."""
        impact = UpgradeImpact(effective_life_delta=100)
        summary = impact.get_summary()
        assert "+100" in summary
        assert "life" in summary.lower()

    def test_get_summary_multiple_changes(self):
        """Test summary with multiple changes."""
        impact = UpgradeImpact(
            effective_life_delta=50,
            fire_res_delta=20,
            cold_res_delta=15,
        )
        summary = impact.get_summary()
        assert "life" in summary.lower()
        assert "res" in summary.lower()

    def test_get_summary_no_changes(self):
        """Test summary with no significant changes."""
        impact = UpgradeImpact()
        summary = impact.get_summary()
        assert "no significant" in summary.lower()


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test full upgrade comparison workflow."""
        # Create build stats
        stats = BuildStats(
            life_inc=180.0,
            total_life=6000.0,
            fire_overcap=-10.0,  # Under fire cap
            cold_overcap=20.0,
            lightning_overcap=15.0,
            chaos_res=0.0,  # Very under chaos cap
        )

        calculator = UpgradeCalculator(stats)

        # Current helmet
        current_helmet = [
            "+70 to maximum Life",
            "+35% to Fire Resistance",
            "+30% to Cold Resistance",
        ]

        # New helmet with better stats
        new_helmet = [
            "+90 to maximum Life",
            "+45% to Fire Resistance",
            "+40% to Cold Resistance",
            "+20% to Chaos Resistance",
            "+30 to Strength",
        ]

        result = calculator.compare_items(new_helmet, current_helmet)

        # Should be a clear upgrade
        assert result["is_upgrade"] is True
        assert result["upgrade_score"] > 50

        # Should have improvements
        assert len(result["improvements"]) >= 3

        # Life should be significantly better (scaled by 180% inc)
        assert result["effective_life_change"] > 50

        # Should cover fire gap
        impact = result["impact"]
        assert impact.fire_res_gap_covered > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
