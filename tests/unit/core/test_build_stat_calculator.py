"""Tests for core/build_stat_calculator.py - Effective mod value calculation."""

import pytest

from core.build_stat_calculator import (
    EffectiveModValue,
    BuildStats,
    BuildStatCalculator,
)


# =============================================================================
# EffectiveModValue Tests
# =============================================================================


class TestEffectiveModValue:
    """Tests for EffectiveModValue dataclass."""

    def test_create_effective_mod_value(self):
        """Should create effective mod value with all fields."""
        emv = EffectiveModValue(
            mod_text="+80 to maximum Life",
            mod_type="life",
            raw_value=80.0,
            effective_value=200.0,
            multiplier=2.5,
            explanation="Scaled by 150% increased life",
        )
        assert emv.mod_text == "+80 to maximum Life"
        assert emv.mod_type == "life"
        assert emv.raw_value == 80.0
        assert emv.effective_value == 200.0
        assert emv.multiplier == 2.5


# =============================================================================
# BuildStats Tests
# =============================================================================


class TestBuildStats:
    """Tests for BuildStats dataclass."""

    def test_default_values(self):
        """Should have zero defaults."""
        stats = BuildStats()
        assert stats.life_inc == 0.0
        assert stats.total_life == 0.0
        assert stats.fire_res == 0.0
        assert stats.strength == 0.0

    def test_from_pob_stats(self):
        """Should create from PoB stats dictionary."""
        pob_data = {
            "Spec:LifeInc": 158.0,
            "Life": 5637.0,
            "Spec:EnergyShieldInc": 22.0,
            "EnergyShield": 113.0,
            "FireResist": 75.0,
            "FireResistOverCap": 30.0,
            "ColdResist": 75.0,
            "ColdResistOverCap": 20.0,
            "LightningResist": 75.0,
            "LightningResistOverCap": 15.0,
            "ChaosResist": 30.0,
            "Str": 200.0,
            "Dex": 100.0,
            "Int": 150.0,
            "CombinedDPS": 1000000.0,
        }
        stats = BuildStats.from_pob_stats(pob_data)

        assert stats.life_inc == 158.0
        assert stats.total_life == 5637.0
        assert stats.es_inc == 22.0
        assert stats.total_es == 113.0
        assert stats.fire_res == 75.0
        assert stats.fire_overcap == 30.0
        assert stats.strength == 200.0
        assert stats.combined_dps == 1000000.0

    def test_from_pob_stats_missing_keys(self):
        """Should use defaults for missing keys."""
        stats = BuildStats.from_pob_stats({})
        assert stats.life_inc == 0.0
        assert stats.total_life == 0.0

    def test_get_summary(self):
        """Should return formatted summary dict."""
        stats = BuildStats(
            total_life=5000,
            life_inc=150.0,
            total_es=500,
            es_inc=50.0,
            fire_res=75.0,
            fire_overcap=20.0,
            cold_res=75.0,
            cold_overcap=10.0,
            lightning_res=75.0,
            lightning_overcap=5.0,
            chaos_res=30.0,
            strength=200,
            dexterity=100,
            intelligence=150,
        )
        summary = stats.get_summary()

        assert "Life" in summary
        assert "5000" in summary["Life"]
        assert "150" in summary["Life"]
        assert "ES" in summary
        assert "Fire Res" in summary
        assert "Str/Dex/Int" in summary

    def test_get_summary_hides_zero_es(self):
        """Should hide ES if zero."""
        stats = BuildStats(total_life=5000, total_es=0)
        summary = stats.get_summary()
        assert summary.get("ES") is None


# =============================================================================
# BuildStatCalculator Tests
# =============================================================================


class TestBuildStatCalculator:
    """Tests for BuildStatCalculator."""

    @pytest.fixture
    def build_stats(self):
        """Create sample build stats."""
        return BuildStats(
            life_inc=150.0,
            total_life=5000.0,
            es_inc=50.0,
            total_es=500.0,
            armour_inc=100.0,
            total_armour=10000.0,
            evasion_inc=50.0,
            fire_overcap=20.0,
            cold_overcap=10.0,
            lightning_overcap=5.0,
            chaos_res=30.0,
            strength=200.0,
        )

    @pytest.fixture
    def calculator(self, build_stats):
        """Create calculator with build stats."""
        return BuildStatCalculator(build_stats)

    def test_calculate_effective_life(self, calculator):
        """Should scale flat life by life%."""
        mods = ["+80 to maximum Life"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "life"
        assert result.raw_value == 80.0
        # 80 * (1 + 150/100) = 80 * 2.5 = 200
        assert result.effective_value == 200.0
        assert result.multiplier == 2.5

    def test_calculate_effective_es(self, calculator):
        """Should scale flat ES by ES%."""
        mods = ["+100 to maximum Energy Shield"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "es"
        # 100 * (1 + 50/100) = 100 * 1.5 = 150
        assert result.effective_value == 150.0

    def test_calculate_effective_armour(self, calculator):
        """Should scale flat armour by armour%."""
        mods = ["+500 to Armour"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        # 500 * (1 + 100/100) = 500 * 2 = 1000
        assert result.effective_value == 1000.0

    def test_fire_resistance_shows_overcap(self, calculator):
        """Should show resistance overcap change."""
        mods = ["+30% to Fire Resistance"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert "overcap" in result.explanation
        # 20 + 30 = 50
        assert "50" in result.explanation

    def test_all_ele_resistance(self, calculator):
        """Should calculate triple value for all ele res."""
        mods = ["+12% to all Elemental Resistances"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert result.effective_value == 36.0  # 12 * 3
        assert result.multiplier == 3.0

    def test_strength_adds_life(self, calculator):
        """Should explain life from strength."""
        mods = ["+50 to Strength"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert "life" in result.explanation.lower()
        # 50 str = 25 base life, scaled by 2.5 = 62.5
        assert "62" in result.explanation

    def test_all_attributes(self, calculator):
        """Should calculate all attributes bonus."""
        mods = ["+10 to all Attributes"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert result.effective_value == 30.0  # 10 * 3
        assert result.multiplier == 3.0

    def test_dual_attributes(self, calculator):
        """Should handle dual attribute mods."""
        mods = ["+20 to Strength and Dexterity"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        result = results[0]
        assert result.effective_value == 40.0  # 20 * 2

    def test_multiple_mods(self, calculator):
        """Should calculate multiple mods."""
        mods = [
            "+80 to maximum Life",
            "+35% to Fire Resistance",
            "+25 to Strength",
        ]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 3
        mod_types = [r.mod_type for r in results]
        assert "life" in mod_types
        assert "fire_res" in mod_types
        assert "strength" in mod_types

    def test_unknown_mod_ignored(self, calculator):
        """Should ignore unrecognized mods."""
        mods = ["Some unknown mod text"]
        results = calculator.calculate_effective_values(mods)
        assert results == []

    def test_empty_mods(self, calculator):
        """Should handle empty mod list."""
        results = calculator.calculate_effective_values([])
        assert results == []


class TestBuildStatCalculatorWithoutStats:
    """Tests for BuildStatCalculator without build stats."""

    def test_works_without_build_stats(self):
        """Should work with default stats (no scaling)."""
        calculator = BuildStatCalculator()
        mods = ["+80 to maximum Life"]
        results = calculator.calculate_effective_values(mods)

        assert len(results) == 1
        # No scaling: 80 * 1.0 = 80
        assert results[0].effective_value == 80.0
        assert results[0].multiplier == 1.0

    def test_get_build_summary(self):
        """Should return formatted build summary."""
        stats = BuildStats(
            total_life=5000,
            life_inc=150.0,
            total_armour=10000,
            armour_inc=100.0,
            fire_res=75.0,
            fire_overcap=20.0,
            cold_res=75.0,
            cold_overcap=10.0,
            lightning_res=75.0,
            lightning_overcap=5.0,
            chaos_res=30.0,
            strength=200,
            dexterity=100,
            intelligence=150,
            combined_dps=1500000.0,
        )
        calculator = BuildStatCalculator(stats)
        summary = calculator.get_build_summary()

        assert "5000" in summary
        assert "150%" in summary or "150" in summary
        assert "1.5" in summary or "1.50" in summary  # DPS in millions

    def test_get_build_summary_with_low_dps(self):
        """Should format low DPS correctly."""
        stats = BuildStats(combined_dps=50000.0, total_life=3000, life_inc=100.0)
        calculator = BuildStatCalculator(stats)
        summary = calculator.get_build_summary()

        assert "50.0K" in summary or "50K" in summary
