"""
Tests for core.dps_impact_calculator module.

Tests the DPS impact estimation for item mods based on build stats.
"""

import pytest
from core.dps_impact_calculator import (
    DamageType,
    DPSStats,
    DPSModImpact,
    DPSImpactResult,
    DPSImpactCalculator,
    get_dps_calculator,
)


class TestDamageType:
    """Tests for DamageType enum."""

    def test_all_damage_types_exist(self):
        """Verify all expected damage types are defined."""
        assert DamageType.PHYSICAL.value == "physical"
        assert DamageType.FIRE.value == "fire"
        assert DamageType.COLD.value == "cold"
        assert DamageType.LIGHTNING.value == "lightning"
        assert DamageType.CHAOS.value == "chaos"
        assert DamageType.ELEMENTAL.value == "elemental"
        assert DamageType.MINION.value == "minion"
        assert DamageType.DOT.value == "dot"
        assert DamageType.UNKNOWN.value == "unknown"


class TestDPSStats:
    """Tests for DPSStats dataclass."""

    def test_default_values(self):
        """Test default DPSStats initialization."""
        stats = DPSStats()
        assert stats.combined_dps == 0.0
        assert stats.physical_dps == 0.0
        assert stats.fire_dps == 0.0
        assert stats.crit_chance == 0.0
        assert stats.primary_damage_type == DamageType.UNKNOWN
        assert stats.is_crit_build is False
        assert stats.is_spell_build is False

    def test_from_pob_stats_fire_build(self):
        """Test creating DPSStats from fire spell build."""
        pob_stats = {
            "CombinedDPS": 2_500_000,
            "FireDPS": 2_200_000,
            "ColdDPS": 100_000,
            "LightningDPS": 100_000,
            "PhysicalDPS": 100_000,
            "CritChance": 65.0,
            "CritMultiplier": 450.0,
            "SpellDPS": 2_500_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.combined_dps == 2_500_000
        assert stats.fire_dps == 2_200_000
        assert stats.primary_damage_type == DamageType.FIRE
        assert stats.is_crit_build is True
        assert stats.is_spell_build is True

    def test_from_pob_stats_physical_attack_build(self):
        """Test creating DPSStats from physical attack build."""
        pob_stats = {
            "CombinedDPS": 1_000_000,
            "PhysicalDPS": 800_000,
            "FireDPS": 100_000,
            "ColdDPS": 50_000,
            "LightningDPS": 50_000,
            "CritChance": 30.0,
            "CritMultiplier": 200.0,
            "AttackDPS": 1_000_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.PHYSICAL
        assert stats.is_crit_build is False  # 30% crit is not high enough
        assert stats.is_attack_build is True

    def test_from_pob_stats_minion_build(self):
        """Test creating DPSStats from minion build."""
        pob_stats = {
            "CombinedDPS": 500_000,
            "MinionDPS": 400_000,
            "PhysicalDPS": 50_000,
            "FireDPS": 25_000,
            "ColdDPS": 25_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.MINION
        assert stats.is_minion_build is True

    def test_from_pob_stats_dot_build(self):
        """Test creating DPSStats from DoT build."""
        pob_stats = {
            "CombinedDPS": 100_000,
            "TotalDPS": 100_000,
            "TotalDotDPS": 800_000,
            "BleedDPS": 500_000,
            "PoisonDPS": 300_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.DOT
        assert stats.is_dot_build is True

    def test_from_pob_stats_crit_threshold(self):
        """Test crit build detection thresholds."""
        # High crit chance alone
        stats1 = DPSStats.from_pob_stats({"CritChance": 45.0, "CritMultiplier": 200.0})
        assert stats1.is_crit_build is True

        # Medium crit with high multi
        stats2 = DPSStats.from_pob_stats({"CritChance": 30.0, "CritMultiplier": 350.0})
        assert stats2.is_crit_build is True

        # Low crit
        stats3 = DPSStats.from_pob_stats({"CritChance": 15.0, "CritMultiplier": 200.0})
        assert stats3.is_crit_build is False


class TestDPSImpactCalculator:
    """Tests for DPSImpactCalculator class."""

    @pytest.fixture
    def fire_spell_build(self):
        """Create a fire spell crit build for testing."""
        pob_stats = {
            "CombinedDPS": 2_500_000,
            "FireDPS": 2_200_000,
            "ColdDPS": 100_000,
            "LightningDPS": 100_000,
            "PhysicalDPS": 100_000,
            "CritChance": 65.0,
            "CritMultiplier": 450.0,
            "SpellDPS": 2_500_000,
        }
        return DPSStats.from_pob_stats(pob_stats)

    @pytest.fixture
    def physical_attack_build(self):
        """Create a physical attack build for testing."""
        pob_stats = {
            "CombinedDPS": 1_000_000,
            "PhysicalDPS": 800_000,
            "FireDPS": 100_000,
            "ColdDPS": 50_000,
            "LightningDPS": 50_000,
            "CritChance": 50.0,
            "CritMultiplier": 350.0,
            "AttackDPS": 1_000_000,
        }
        return DPSStats.from_pob_stats(pob_stats)

    def test_calculator_initialization(self):
        """Test calculator can be initialized."""
        calc = DPSImpactCalculator()
        assert calc.dps_stats is not None

    def test_calculator_with_stats(self, fire_spell_build):
        """Test calculator with provided stats."""
        calc = DPSImpactCalculator(fire_spell_build)
        assert calc.dps_stats.combined_dps == 2_500_000

    def test_set_stats(self, fire_spell_build):
        """Test updating stats after initialization."""
        calc = DPSImpactCalculator()
        calc.set_stats(fire_spell_build)
        assert calc.dps_stats.combined_dps == 2_500_000

    def test_calculate_impact_fire_damage(self, fire_spell_build):
        """Test fire damage mod impact on fire build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+35% increased Fire Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "high"
        assert result.total_dps_percent > 0

    def test_calculate_impact_spell_damage(self, fire_spell_build):
        """Test spell damage mod impact on spell build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+25% increased Spell Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "high"
        assert result.mod_impacts[0].mod_category == "spell_damage"

    def test_calculate_impact_crit_multi(self, fire_spell_build):
        """Test crit multi mod impact on crit build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+40% to Global Critical Strike Multiplier"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "high"
        assert result.mod_impacts[0].mod_category == "crit_multi"

    def test_calculate_impact_cast_speed(self, fire_spell_build):
        """Test cast speed mod impact on spell build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+15% increased Cast Speed"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "high"
        assert result.mod_impacts[0].mod_category == "cast_speed"

    def test_calculate_impact_attack_speed_on_spell_build(self, fire_spell_build):
        """Test attack speed mod has no impact on spell build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+15% increased Attack Speed"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "none"

    def test_calculate_impact_physical_on_fire_build(self, fire_spell_build):
        """Test physical damage mod has low impact on fire build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+30% increased Physical Damage"])

        assert len(result.mod_impacts) == 1
        # Physical is only 4% of DPS (100k/2.5M), so should be low
        assert result.mod_impacts[0].relevance in ("low", "medium")

    def test_calculate_impact_physical_on_physical_build(self, physical_attack_build):
        """Test physical damage mod has high impact on physical build."""
        calc = DPSImpactCalculator(physical_attack_build)
        result = calc.calculate_impact(["+30% increased Physical Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "high"

    def test_calculate_impact_multiple_mods(self, fire_spell_build):
        """Test calculating impact for multiple mods."""
        calc = DPSImpactCalculator(fire_spell_build)
        mods = [
            "+35% increased Fire Damage",
            "+25% increased Spell Damage",
            "+40% to Global Critical Strike Multiplier",
        ]
        result = calc.calculate_impact(mods)

        assert len(result.mod_impacts) == 3
        assert result.total_dps_percent > 0
        assert result.total_dps_change > 0

    def test_calculate_impact_no_offensive_mods(self, fire_spell_build):
        """Test with mods that don't affect DPS."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact([
            "+80 to maximum Life",
            "+45% to Fire Resistance",
        ])

        assert len(result.mod_impacts) == 0
        assert result.total_dps_percent == 0

    def test_calculate_impact_no_dps(self):
        """Test calculator with no DPS data."""
        calc = DPSImpactCalculator(DPSStats())
        result = calc.calculate_impact(["+35% increased Fire Damage"])

        assert "No DPS data" in result.summary

    def test_calculate_impact_minion_mod_on_non_minion(self, fire_spell_build):
        """Test minion damage mod has no impact on non-minion build."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+30% increased Minion Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].relevance == "none"

    def test_summary_generation(self, fire_spell_build):
        """Test summary generation for various impact levels."""
        calc = DPSImpactCalculator(fire_spell_build)

        # Significant upgrade
        result1 = calc.calculate_impact([
            "+35% increased Fire Damage",
            "+40% to Global Critical Strike Multiplier",
            "+25% increased Spell Damage",
        ])
        assert "Significant" in result1.summary or "Moderate" in result1.summary

        # Minor upgrade
        result2 = calc.calculate_impact(["+5% increased Fire Damage"])
        assert "Minor" in result2.summary or "Negligible" in result2.summary

    def test_build_info_generation(self, fire_spell_build):
        """Test build info string generation."""
        calc = DPSImpactCalculator(fire_spell_build)
        result = calc.calculate_impact(["+35% increased Fire Damage"])

        assert "2.50M" in result.build_info
        assert "Fire" in result.build_info
        assert "Crit" in result.build_info
        assert "Spell" in result.build_info


class TestDPSModPatterns:
    """Tests for mod pattern recognition."""

    @pytest.fixture
    def calculator(self):
        """Create a calculator with sample build stats."""
        pob_stats = {
            "CombinedDPS": 1_000_000,
            "PhysicalDPS": 500_000,
            "FireDPS": 250_000,
            "ColdDPS": 125_000,
            "LightningDPS": 125_000,
            "CritChance": 50.0,
            "CritMultiplier": 300.0,
            "AttackDPS": 1_000_000,
        }
        return DPSImpactCalculator(DPSStats.from_pob_stats(pob_stats))

    def test_pattern_physical_damage(self, calculator):
        """Test physical damage pattern recognition."""
        result = calculator.calculate_impact(["40% increased Physical Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "physical_damage"

    def test_pattern_elemental_damage(self, calculator):
        """Test elemental damage pattern recognition."""
        result = calculator.calculate_impact(["30% increased Elemental Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "elemental_damage"

    def test_pattern_fire_damage(self, calculator):
        """Test fire damage pattern recognition."""
        result = calculator.calculate_impact(["25% increased Fire Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "fire_damage"

    def test_pattern_cold_damage(self, calculator):
        """Test cold damage pattern recognition."""
        result = calculator.calculate_impact(["25% increased Cold Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "cold_damage"

    def test_pattern_lightning_damage(self, calculator):
        """Test lightning damage pattern recognition."""
        result = calculator.calculate_impact(["25% increased Lightning Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "lightning_damage"

    def test_pattern_chaos_damage(self, calculator):
        """Test chaos damage pattern recognition."""
        result = calculator.calculate_impact(["25% increased Chaos Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "chaos_damage"

    def test_pattern_crit_chance(self, calculator):
        """Test crit chance pattern recognition."""
        result = calculator.calculate_impact(["30% increased Critical Strike Chance"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "crit_chance"

    def test_pattern_global_crit_chance(self, calculator):
        """Test global crit chance pattern recognition."""
        result = calculator.calculate_impact(["30% increased Global Critical Strike Chance"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "crit_chance"

    def test_pattern_crit_multi(self, calculator):
        """Test crit multiplier pattern recognition."""
        result = calculator.calculate_impact(["+50% to Critical Strike Multiplier"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "crit_multi"

    def test_pattern_attack_speed(self, calculator):
        """Test attack speed pattern recognition."""
        result = calculator.calculate_impact(["10% increased Attack Speed"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "attack_speed"

    def test_pattern_cast_speed(self, calculator):
        """Test cast speed pattern recognition."""
        result = calculator.calculate_impact(["10% increased Cast Speed"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "cast_speed"

    def test_pattern_added_physical(self, calculator):
        """Test added physical damage pattern recognition."""
        result = calculator.calculate_impact(["Adds 10 to 20 Physical Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "added_physical"

    def test_pattern_added_fire(self, calculator):
        """Test added fire damage pattern recognition."""
        result = calculator.calculate_impact(["Adds 15 to 30 Fire Damage"])
        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "added_fire"


class TestGetDPSCalculator:
    """Tests for get_dps_calculator factory function."""

    def test_returns_calculator(self):
        """Test factory returns a calculator instance."""
        calc = get_dps_calculator()
        assert isinstance(calc, DPSImpactCalculator)

    def test_returns_new_instance(self):
        """Test factory returns new instances."""
        calc1 = get_dps_calculator()
        calc2 = get_dps_calculator()
        # Different instances (not singleton)
        assert calc1 is not calc2
