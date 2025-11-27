"""
Tests for Build Stat Calculator.

Tests:
- BuildStats from PoB data
- Effective value calculations with scaling
- Different mod types (life, ES, resistances, attributes)
"""
import pytest
from core.build_stat_calculator import (
    BuildStats,
    BuildStatCalculator,
    EffectiveModValue,
)


class TestBuildStats:
    """Tests for BuildStats dataclass."""

    def test_from_pob_stats_life_scaling(self):
        """Test extracting life scaling from PoB stats."""
        stats = BuildStats.from_pob_stats({
            "Spec:LifeInc": 158.0,
            "Life": 5637.0,
        })
        assert stats.life_inc == 158.0
        assert stats.total_life == 5637.0

    def test_from_pob_stats_es_scaling(self):
        """Test extracting ES scaling from PoB stats."""
        stats = BuildStats.from_pob_stats({
            "Spec:EnergyShieldInc": 200.0,
            "EnergyShield": 8000.0,
        })
        assert stats.es_inc == 200.0
        assert stats.total_es == 8000.0

    def test_from_pob_stats_armour_scaling(self):
        """Test extracting armour scaling from PoB stats."""
        stats = BuildStats.from_pob_stats({
            "Spec:ArmourInc": 92.0,
            "Armour": 13878.0,
        })
        assert stats.armour_inc == 92.0
        assert stats.total_armour == 13878.0

    def test_from_pob_stats_resistances(self):
        """Test extracting resistance values and overcaps."""
        stats = BuildStats.from_pob_stats({
            "FireResist": 90.0,
            "FireResistOverCap": 377.0,
            "ColdResist": 85.0,
            "ColdResistOverCap": 10.0,
            "LightningResist": 90.0,
            "LightningResistOverCap": -5.0,  # Under cap
            "ChaosResist": 45.0,
        })
        assert stats.fire_res == 90.0
        assert stats.fire_overcap == 377.0
        assert stats.cold_res == 85.0
        assert stats.cold_overcap == 10.0
        assert stats.lightning_overcap == -5.0  # Can be negative
        assert stats.chaos_res == 45.0

    def test_from_pob_stats_attributes(self):
        """Test extracting attribute values."""
        stats = BuildStats.from_pob_stats({
            "Str": 332.0,
            "Dex": 128.0,
            "Int": 144.0,
        })
        assert stats.strength == 332.0
        assert stats.dexterity == 128.0
        assert stats.intelligence == 144.0

    def test_from_pob_stats_missing_values(self):
        """Test handling missing PoB stat values."""
        stats = BuildStats.from_pob_stats({})
        assert stats.life_inc == 0.0
        assert stats.total_life == 0.0
        assert stats.strength == 0.0

    def test_get_summary(self):
        """Test getting summary dict."""
        stats = BuildStats(
            total_life=5000,
            life_inc=150,
            fire_res=75,
            fire_overcap=10,
            cold_res=75,
            cold_overcap=5,
            lightning_res=75,
            lightning_overcap=0,
            chaos_res=30,
        )
        summary = stats.get_summary()
        assert "Life" in summary
        assert "5000" in summary["Life"]
        assert "+150%" in summary["Life"]


class TestBuildStatCalculator:
    """Tests for effective value calculations."""

    @pytest.fixture
    def calculator_with_life_scaling(self):
        """Calculator with 158% increased life."""
        stats = BuildStats(life_inc=158.0, total_life=5637.0)
        return BuildStatCalculator(stats)

    @pytest.fixture
    def calculator_with_es_scaling(self):
        """Calculator with 200% increased ES."""
        stats = BuildStats(es_inc=200.0, total_es=8000.0)
        return BuildStatCalculator(stats)

    @pytest.fixture
    def calculator_with_full_stats(self):
        """Calculator with full build stats."""
        stats = BuildStats(
            life_inc=158.0,
            total_life=5637.0,
            es_inc=22.0,
            total_es=113.0,
            armour_inc=92.0,
            total_armour=13878.0,
            fire_res=90.0,
            fire_overcap=20.0,
            cold_res=85.0,
            cold_overcap=-5.0,  # Under cap
            lightning_res=90.0,
            lightning_overcap=10.0,
            chaos_res=45.0,
            strength=332.0,
            dexterity=128.0,
            intelligence=144.0,
        )
        return BuildStatCalculator(stats)

    def test_flat_life_scaling(self, calculator_with_life_scaling):
        """Test flat life scales with % increased life."""
        results = calculator_with_life_scaling.calculate_effective_values([
            "+80 to maximum Life"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "life"
        assert result.raw_value == 80
        # 80 * (1 + 1.58) = 80 * 2.58 = 206.4
        assert abs(result.effective_value - 206.4) < 0.1
        assert abs(result.multiplier - 2.58) < 0.01

    def test_flat_es_scaling(self, calculator_with_es_scaling):
        """Test flat ES scales with % increased ES."""
        results = calculator_with_es_scaling.calculate_effective_values([
            "+150 to maximum Energy Shield"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "es"
        assert result.raw_value == 150
        # 150 * (1 + 2.0) = 150 * 3.0 = 450
        assert abs(result.effective_value - 450) < 0.1
        assert abs(result.multiplier - 3.0) < 0.01

    def test_flat_armour_scaling(self, calculator_with_full_stats):
        """Test flat armour scales with % increased armour."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+500 to Armour"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "armour"
        # 500 * (1 + 0.92) = 500 * 1.92 = 960
        assert abs(result.effective_value - 960) < 0.1

    def test_fire_resistance_shows_overcap(self, calculator_with_full_stats):
        """Test fire resistance shows overcap change."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+45% to Fire Resistance"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "fire_res"
        assert result.raw_value == 45
        # Effective value is same as raw for resistances
        assert result.effective_value == 45
        # Should mention overcap in explanation
        assert "overcap" in result.explanation.lower()

    def test_cold_resistance_under_cap(self, calculator_with_full_stats):
        """Test cold resistance when under cap shows fill."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+30% to Cold Resistance"
        ])
        assert len(results) == 1
        result = results[0]
        # With -5% overcap, +30% would bring it to +25% overcap
        assert "overcap" in result.explanation.lower()

    def test_strength_shows_effective_life(self, calculator_with_full_stats):
        """Test strength shows effective life contribution."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+50 to Strength"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "strength"
        # 50 str = 25 base life, * 2.58 = 64.5 effective life
        assert "life" in result.explanation.lower()

    def test_intelligence_shows_es_contribution(self, calculator_with_full_stats):
        """Test intelligence shows ES contribution."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+40 to Intelligence"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "intelligence"
        assert "es" in result.explanation.lower()

    def test_all_elemental_resistances(self, calculator_with_full_stats):
        """Test all elemental resistances mod."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+12% to all Elemental Resistances"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "all_ele_res"
        # Effective value is 3x for the combined effect
        assert result.effective_value == 36

    def test_dual_attribute_mod(self, calculator_with_full_stats):
        """Test dual attribute mods."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+25 to Strength and Dexterity"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "str_dex"

    def test_all_attributes_mod(self, calculator_with_full_stats):
        """Test all attributes mod."""
        results = calculator_with_full_stats.calculate_effective_values([
            "+16 to all Attributes"
        ])
        assert len(results) == 1
        result = results[0]
        assert result.mod_type == "all_attributes"
        # 3x effective value
        assert result.effective_value == 48

    def test_multiple_mods(self, calculator_with_full_stats):
        """Test calculating multiple mods at once."""
        mods = [
            "+80 to maximum Life",
            "+45% to Fire Resistance",
            "+30% to Cold Resistance",
            "+50 to Strength",
        ]
        results = calculator_with_full_stats.calculate_effective_values(mods)
        assert len(results) == 4

    def test_unrecognized_mod_returns_none(self, calculator_with_full_stats):
        """Test that unrecognized mods are skipped."""
        results = calculator_with_full_stats.calculate_effective_values([
            "Something completely unrelated"
        ])
        assert len(results) == 0

    def test_no_scaling_without_stats(self):
        """Test calculator without build stats uses 1.0 multiplier."""
        calculator = BuildStatCalculator()  # No stats
        results = calculator.calculate_effective_values([
            "+80 to maximum Life"
        ])
        assert len(results) == 1
        result = results[0]
        # Without scaling, effective = raw
        assert result.effective_value == 80
        assert result.multiplier == 1.0


class TestEffectiveModValue:
    """Tests for EffectiveModValue dataclass."""

    def test_dataclass_creation(self):
        """Test creating EffectiveModValue."""
        result = EffectiveModValue(
            mod_text="+80 to maximum Life",
            mod_type="life",
            raw_value=80,
            effective_value=206.4,
            multiplier=2.58,
            explanation="+80 life x 2.58 = 206 effective",
        )
        assert result.mod_text == "+80 to maximum Life"
        assert result.mod_type == "life"
        assert result.raw_value == 80
        assert abs(result.effective_value - 206.4) < 0.01


class TestBuildStatCalculatorBuildSummary:
    """Tests for build summary generation."""

    def test_get_build_summary_full(self):
        """Test full build summary."""
        stats = BuildStats(
            total_life=5637,
            life_inc=158,
            total_es=113,
            es_inc=22,
            total_armour=13878,
            armour_inc=92,
            fire_res=90,
            fire_overcap=20,
            cold_res=85,
            cold_overcap=10,
            lightning_res=90,
            lightning_overcap=15,
            chaos_res=45,
            strength=332,
            dexterity=128,
            intelligence=144,
            combined_dps=294808,
        )
        calculator = BuildStatCalculator(stats)
        summary = calculator.get_build_summary()

        assert "Life:" in summary
        assert "5637" in summary
        assert "158%" in summary
        assert "ES:" in summary
        assert "Armour:" in summary
        assert "Res:" in summary
        assert "DPS:" in summary

    def test_get_build_summary_minimal(self):
        """Test build summary with minimal stats."""
        stats = BuildStats(
            total_life=4000,
            life_inc=100,
            fire_res=75,
            cold_res=75,
            lightning_res=75,
            chaos_res=0,
        )
        calculator = BuildStatCalculator(stats)
        summary = calculator.get_build_summary()

        assert "Life:" in summary
        # ES and Armour sections should be skipped when low
        assert "ES:" not in summary  # Only shows if > 50
        assert "Armour:" not in summary  # Only shows if > 100


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_pob_to_effective_values(self):
        """Test full workflow from PoB stats to effective values."""
        # Simulate PoB stats
        pob_stats = {
            "Spec:LifeInc": 158.0,
            "Life": 5637.0,
            "Spec:EnergyShieldInc": 22.0,
            "EnergyShield": 113.0,
            "Spec:ArmourInc": 92.0,
            "Armour": 13878.0,
            "FireResist": 90.0,
            "FireResistOverCap": 377.0,
            "ColdResist": 90.0,
            "ColdResistOverCap": 136.0,
            "LightningResist": 90.0,
            "LightningResistOverCap": 132.0,
            "ChaosResist": 75.0,
            "Str": 332.0,
            "Dex": 128.0,
            "Int": 144.0,
            "CombinedDPS": 294808.0,
        }

        # Create build stats from PoB
        build_stats = BuildStats.from_pob_stats(pob_stats)
        calculator = BuildStatCalculator(build_stats)

        # Calculate effective values for item mods
        test_mods = [
            "+80 to maximum Life",
            "+45% to Fire Resistance",
            "+50 to Strength",
            "+500 to Armour",
        ]

        results = calculator.calculate_effective_values(test_mods)

        # Verify we got results for all recognized mods
        assert len(results) == 4

        # Life should be scaled by 2.58x
        life_result = next(r for r in results if r.mod_type == "life")
        assert life_result.multiplier > 2.5

        # Armour should be scaled by 1.92x
        armour_result = next(r for r in results if r.mod_type == "armour")
        assert armour_result.multiplier > 1.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
