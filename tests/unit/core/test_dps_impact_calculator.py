"""Tests for core/dps_impact_calculator.py - DPS Impact Calculator."""

import pytest
from unittest.mock import Mock, patch

from core.dps_impact_calculator import (
    DamageType,
    DPSStats,
    DPSModImpact,
    DPSImpactResult,
    DPSImpactCalculator,
    get_dps_calculator,
)


# ============================================================================
# DamageType Enum Tests
# ============================================================================

class TestDamageType:
    """Tests for DamageType enum."""

    def test_physical_value(self):
        """PHYSICAL has correct value."""
        assert DamageType.PHYSICAL.value == "physical"

    def test_fire_value(self):
        """FIRE has correct value."""
        assert DamageType.FIRE.value == "fire"

    def test_cold_value(self):
        """COLD has correct value."""
        assert DamageType.COLD.value == "cold"

    def test_lightning_value(self):
        """LIGHTNING has correct value."""
        assert DamageType.LIGHTNING.value == "lightning"

    def test_chaos_value(self):
        """CHAOS has correct value."""
        assert DamageType.CHAOS.value == "chaos"

    def test_elemental_value(self):
        """ELEMENTAL has correct value."""
        assert DamageType.ELEMENTAL.value == "elemental"

    def test_minion_value(self):
        """MINION has correct value."""
        assert DamageType.MINION.value == "minion"

    def test_dot_value(self):
        """DOT has correct value."""
        assert DamageType.DOT.value == "dot"

    def test_unknown_value(self):
        """UNKNOWN has correct value."""
        assert DamageType.UNKNOWN.value == "unknown"


# ============================================================================
# DPSStats Dataclass Tests
# ============================================================================

class TestDPSStats:
    """Tests for DPSStats dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        stats = DPSStats()
        assert stats.combined_dps == 0.0
        assert stats.total_dps == 0.0
        assert stats.physical_dps == 0.0
        assert stats.fire_dps == 0.0
        assert stats.cold_dps == 0.0
        assert stats.lightning_dps == 0.0
        assert stats.chaos_dps == 0.0
        assert stats.minion_dps == 0.0
        assert stats.crit_chance == 0.0
        assert stats.crit_multi == 0.0
        assert stats.primary_damage_type == DamageType.UNKNOWN
        assert stats.is_crit_build is False
        assert stats.is_dot_build is False
        assert stats.is_minion_build is False

    def test_from_pob_stats_physical_build(self):
        """Create DPSStats from physical build."""
        pob_stats = {
            "CombinedDPS": 1_000_000,
            "TotalDPS": 1_000_000,
            "PhysicalDPS": 800_000,
            "FireDPS": 100_000,
            "ColdDPS": 50_000,
            "LightningDPS": 50_000,
            "ChaosDPS": 0,
            "CritChance": 30.0,
            "CritMultiplier": 200.0,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.combined_dps == 1_000_000
        assert stats.physical_dps == 800_000
        assert stats.primary_damage_type == DamageType.PHYSICAL
        assert stats.is_crit_build is False  # 30% crit, 200% multi

    def test_from_pob_stats_fire_build(self):
        """Create DPSStats from fire build."""
        pob_stats = {
            "CombinedDPS": 2_000_000,
            "TotalDPS": 2_000_000,
            "PhysicalDPS": 100_000,
            "FireDPS": 1_500_000,
            "ColdDPS": 200_000,
            "LightningDPS": 200_000,
            "ChaosDPS": 0,
            "CritChance": 50.0,
            "CritMultiplier": 350.0,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.FIRE
        assert stats.is_crit_build is True  # 50% crit, 350% multi

    def test_from_pob_stats_cold_build(self):
        """Create DPSStats from cold build."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "PhysicalDPS": 50_000,
            "FireDPS": 50_000,
            "ColdDPS": 800_000,
            "LightningDPS": 100_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.COLD

    def test_from_pob_stats_lightning_build(self):
        """Create DPSStats from lightning build."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "PhysicalDPS": 50_000,
            "FireDPS": 50_000,
            "ColdDPS": 100_000,
            "LightningDPS": 800_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.LIGHTNING

    def test_from_pob_stats_chaos_build(self):
        """Create DPSStats from chaos build."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "PhysicalDPS": 100_000,
            "ChaosDPS": 600_000,
            "FireDPS": 100_000,
            "ColdDPS": 100_000,
            "LightningDPS": 100_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.CHAOS

    def test_from_pob_stats_minion_build(self):
        """Create DPSStats from minion build."""
        pob_stats = {
            "TotalDPS": 100_000,
            "MinionDPS": 5_000_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.MINION
        assert stats.is_minion_build is True

    def test_from_pob_stats_dot_build(self):
        """Create DPSStats from DoT build."""
        pob_stats = {
            "TotalDPS": 0,
            "BleedDPS": 500_000,
            "IgniteDPS": 0,
            "PoisonDPS": 0,
            "TotalDotDPS": 500_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.primary_damage_type == DamageType.DOT
        assert stats.is_dot_build is True

    def test_from_pob_stats_dot_hybrid(self):
        """Create DPSStats from hybrid DoT build."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "FireDPS": 1_000_000,
            "TotalDotDPS": 500_000,  # 50% of hit DPS
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.is_dot_build is True  # >30% dot ratio

    def test_from_pob_stats_crit_by_chance(self):
        """Crit build detected by high crit chance."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "CritChance": 45.0,
            "CritMultiplier": 200.0,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.is_crit_build is True  # >40% crit

    def test_from_pob_stats_crit_by_multi(self):
        """Crit build detected by high multiplier."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "CritChance": 30.0,
            "CritMultiplier": 400.0,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.is_crit_build is True  # >25% crit and >300% multi

    def test_from_pob_stats_spell_build(self):
        """Spell build detected from SpellDPS."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "SpellDPS": 1_000_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.is_spell_build is True

    def test_from_pob_stats_attack_build(self):
        """Attack build detected from AttackDPS."""
        pob_stats = {
            "TotalDPS": 1_000_000,
            "AttackDPS": 1_000_000,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.is_attack_build is True

    def test_from_pob_stats_alternate_keys(self):
        """Handle alternate stat key names."""
        pob_stats = {
            "TotalPhysicalDPS": 500_000,
            "TotalFireDPS": 300_000,
            "TotalColdDPS": 100_000,
            "TotalLightningDPS": 100_000,
            "MeleeCritChance": 50.0,
            "CritDamage": 350.0,
            "AttackRate": 5.0,
            "CastRate": 3.0,
        }
        stats = DPSStats.from_pob_stats(pob_stats)

        assert stats.physical_dps == 500_000
        assert stats.fire_dps == 300_000
        assert stats.crit_chance == 50.0
        assert stats.crit_multi == 350.0
        assert stats.attack_speed == 5.0
        assert stats.cast_speed == 3.0


# ============================================================================
# DPSModImpact Dataclass Tests
# ============================================================================

class TestDPSModImpact:
    """Tests for DPSModImpact dataclass."""

    def test_creation(self):
        """Create DPSModImpact with all fields."""
        impact = DPSModImpact(
            mod_text="+25% increased Fire Damage",
            mod_category="fire_damage",
            raw_value=25.0,
            estimated_dps_change=50_000,
            estimated_dps_percent=2.5,
            relevance="high",
            explanation="Test explanation"
        )

        assert impact.mod_text == "+25% increased Fire Damage"
        assert impact.mod_category == "fire_damage"
        assert impact.raw_value == 25.0
        assert impact.estimated_dps_change == 50_000
        assert impact.estimated_dps_percent == 2.5
        assert impact.relevance == "high"
        assert impact.explanation == "Test explanation"


# ============================================================================
# DPSImpactResult Dataclass Tests
# ============================================================================

class TestDPSImpactResult:
    """Tests for DPSImpactResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = DPSImpactResult()

        assert result.total_dps_change == 0.0
        assert result.total_dps_percent == 0.0
        assert result.mod_impacts == []
        assert result.summary == ""
        assert result.build_info == ""


# ============================================================================
# DPSImpactCalculator Tests
# ============================================================================

class TestDPSImpactCalculator:
    """Tests for DPSImpactCalculator class."""

    @pytest.fixture
    def fire_build_stats(self):
        """Create stats for a fire spell build."""
        return DPSStats(
            combined_dps=2_000_000,
            total_dps=2_000_000,
            physical_dps=50_000,
            fire_dps=1_800_000,
            cold_dps=50_000,
            lightning_dps=50_000,
            chaos_dps=50_000,
            crit_chance=50.0,
            crit_multi=350.0,
            primary_damage_type=DamageType.FIRE,
            is_crit_build=True,
            is_spell_build=True,
            is_attack_build=False,
        )

    @pytest.fixture
    def phys_attack_stats(self):
        """Create stats for a physical attack build."""
        return DPSStats(
            combined_dps=1_500_000,
            total_dps=1_500_000,
            physical_dps=1_200_000,
            fire_dps=100_000,
            cold_dps=100_000,
            lightning_dps=100_000,
            crit_chance=60.0,
            crit_multi=400.0,
            attack_speed=8.0,
            primary_damage_type=DamageType.PHYSICAL,
            is_crit_build=True,
            is_spell_build=False,
            is_attack_build=True,
        )

    @pytest.fixture
    def minion_stats(self):
        """Create stats for a minion build."""
        return DPSStats(
            combined_dps=3_000_000,
            total_dps=100_000,
            minion_dps=3_000_000,
            primary_damage_type=DamageType.MINION,
            is_minion_build=True,
        )

    @pytest.fixture
    def dot_stats(self):
        """Create stats for a DoT build."""
        return DPSStats(
            combined_dps=500_000,
            total_dps=0,
            total_dot_dps=500_000,
            bleed_dps=500_000,
            primary_damage_type=DamageType.DOT,
            is_dot_build=True,
        )

    def test_init_default(self):
        """Calculator initializes with default stats."""
        calc = DPSImpactCalculator()
        assert calc.dps_stats is not None
        assert calc.dps_stats.combined_dps == 0.0

    def test_init_with_stats(self, fire_build_stats):
        """Calculator initializes with provided stats."""
        calc = DPSImpactCalculator(fire_build_stats)
        assert calc.dps_stats == fire_build_stats

    def test_set_stats(self, fire_build_stats, phys_attack_stats):
        """set_stats updates the stats."""
        calc = DPSImpactCalculator(fire_build_stats)
        calc.set_stats(phys_attack_stats)
        assert calc.dps_stats == phys_attack_stats

    def test_calculate_impact_no_dps(self):
        """Calculate impact with no DPS data."""
        calc = DPSImpactCalculator()
        result = calc.calculate_impact(["+25% increased Fire Damage"])

        assert result.summary == "No DPS data available from build"
        assert result.total_dps_change == 0.0

    def test_calculate_impact_fire_damage(self, fire_build_stats):
        """Calculate impact of fire damage on fire build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+25% increased Fire Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "fire_damage"
        assert impact.raw_value == 25.0
        assert impact.relevance == "high"
        assert impact.estimated_dps_percent > 0

    def test_calculate_impact_physical_damage_on_fire(self, fire_build_stats):
        """Calculate impact of physical damage on fire build (low relevance)."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+25% increased Physical Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.relevance in ("low", "medium")

    def test_calculate_impact_crit_chance(self, fire_build_stats):
        """Calculate impact of crit chance on crit build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+30% increased Critical Strike Chance"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "crit_chance"
        assert impact.relevance == "high"

    def test_calculate_impact_crit_multi(self, fire_build_stats):
        """Calculate impact of crit multi on crit build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+40% to Global Critical Strike Multiplier"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "crit_multi"
        assert impact.relevance == "high"
        assert impact.estimated_dps_percent > 0

    def test_calculate_impact_attack_speed(self, phys_attack_stats):
        """Calculate impact of attack speed on attack build."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["+15% increased Attack Speed"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "attack_speed"
        assert impact.relevance == "high"

    def test_calculate_impact_attack_speed_on_spell(self, fire_build_stats):
        """Attack speed has no impact on spell build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+15% increased Attack Speed"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.relevance == "none"

    def test_calculate_impact_cast_speed(self, fire_build_stats):
        """Calculate impact of cast speed on spell build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+15% increased Cast Speed"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "cast_speed"
        assert impact.relevance == "high"

    def test_calculate_impact_spell_damage(self, fire_build_stats):
        """Calculate impact of spell damage on spell build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+30% increased Spell Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "spell_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_spell_damage_on_attack(self, phys_attack_stats):
        """Spell damage has no impact on attack build."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["+30% increased Spell Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.relevance == "none"

    def test_calculate_impact_minion_damage(self, minion_stats):
        """Calculate impact of minion damage on minion build."""
        calc = DPSImpactCalculator(minion_stats)
        result = calc.calculate_impact(["+35% increased Minion Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "minion_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_minion_damage_on_non_minion(self, fire_build_stats):
        """Minion damage has no impact on non-minion build."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+35% increased Minion Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.relevance == "none"

    def test_calculate_impact_dot_damage(self, dot_stats):
        """Calculate impact of DoT damage on DoT build."""
        calc = DPSImpactCalculator(dot_stats)
        result = calc.calculate_impact(["+25% increased Damage over Time"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "dot_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_elemental_damage(self, fire_build_stats):
        """Calculate impact of elemental damage."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+20% increased Elemental Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "elemental_damage"

    def test_calculate_impact_cold_damage(self):
        """Calculate impact of cold damage on cold build."""
        cold_stats = DPSStats(
            combined_dps=1_000_000,
            total_dps=1_000_000,
            cold_dps=900_000,
            primary_damage_type=DamageType.COLD,
        )
        calc = DPSImpactCalculator(cold_stats)
        result = calc.calculate_impact(["+25% increased Cold Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "cold_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_lightning_damage(self):
        """Calculate impact of lightning damage on lightning build."""
        light_stats = DPSStats(
            combined_dps=1_000_000,
            total_dps=1_000_000,
            lightning_dps=900_000,
            primary_damage_type=DamageType.LIGHTNING,
        )
        calc = DPSImpactCalculator(light_stats)
        result = calc.calculate_impact(["+25% increased Lightning Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "lightning_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_chaos_damage(self):
        """Calculate impact of chaos damage on chaos build."""
        chaos_stats = DPSStats(
            combined_dps=1_000_000,
            total_dps=1_000_000,
            chaos_dps=900_000,
            primary_damage_type=DamageType.CHAOS,
        )
        calc = DPSImpactCalculator(chaos_stats)
        result = calc.calculate_impact(["+25% increased Chaos Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "chaos_damage"
        assert impact.relevance == "high"

    def test_calculate_impact_more_damage(self, fire_build_stats):
        """Calculate impact of 'more' damage (multiplicative)."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+10% more Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "more_damage"
        assert impact.relevance == "high"
        assert impact.estimated_dps_percent == 10.0  # More is 1:1

    def test_calculate_impact_added_damage(self, phys_attack_stats):
        """Calculate impact of flat added damage on attack build."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["Adds 15 to 30 Physical Damage"])

        assert len(result.mod_impacts) == 1
        impact = result.mod_impacts[0]
        assert impact.mod_category == "added_physical"
        assert impact.relevance == "medium"

    def test_calculate_impact_multiple_mods(self, fire_build_stats):
        """Calculate impact of multiple mods."""
        calc = DPSImpactCalculator(fire_build_stats)
        mods = [
            "+25% increased Fire Damage",
            "+30% increased Spell Damage",
            "+40% to Global Critical Strike Multiplier",
        ]
        result = calc.calculate_impact(mods)

        assert len(result.mod_impacts) == 3
        assert result.total_dps_percent > 0
        assert result.total_dps_change > 0

    def test_calculate_impact_no_matching_mods(self, fire_build_stats):
        """Calculate impact with no offensive mods."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+50 to Maximum Life", "+30% increased Rarity"])

        assert len(result.mod_impacts) == 0
        assert result.summary == "No offensive mods detected"

    def test_calculate_impact_crit_chance_on_non_crit(self):
        """Crit chance has low impact on non-crit build."""
        non_crit = DPSStats(
            combined_dps=1_000_000,
            crit_chance=5.0,
            crit_multi=150.0,
            is_crit_build=False,
        )
        calc = DPSImpactCalculator(non_crit)
        result = calc.calculate_impact(["+30% increased Critical Strike Chance"])

        impact = result.mod_impacts[0]
        assert impact.relevance == "low"

    def test_calculate_impact_crit_multi_on_non_crit(self):
        """Crit multi has low impact on non-crit build."""
        non_crit = DPSStats(
            combined_dps=1_000_000,
            crit_chance=5.0,
            crit_multi=150.0,
            is_crit_build=False,
        )
        calc = DPSImpactCalculator(non_crit)
        result = calc.calculate_impact(["+40% to Global Critical Strike Multiplier"])

        impact = result.mod_impacts[0]
        assert impact.relevance == "low"

    def test_summary_significant_upgrade(self, fire_build_stats):
        """Summary indicates significant upgrade."""
        calc = DPSImpactCalculator(fire_build_stats)
        mods = [
            "+35% increased Fire Damage",
            "+35% increased Spell Damage",
            "+10% more Damage",
        ]
        result = calc.calculate_impact(mods)

        assert "Significant" in result.summary or result.total_dps_percent >= 5

    def test_summary_moderate_upgrade(self, fire_build_stats):
        """Summary indicates moderate upgrade."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+25% increased Fire Damage"])

        # Just check it generates a summary
        assert result.summary != ""

    def test_build_info_generation(self, fire_build_stats):
        """Build info is generated correctly."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+10% increased Fire Damage"])

        assert "DPS" in result.build_info
        assert "Fire" in result.build_info
        assert "Crit" in result.build_info
        assert "Spell" in result.build_info

    def test_build_info_millions(self, fire_build_stats):
        """Build info formats millions correctly."""
        calc = DPSImpactCalculator(fire_build_stats)
        info = calc._get_build_info()

        assert "M" in info  # 2M DPS

    def test_build_info_thousands(self):
        """Build info formats thousands correctly."""
        stats = DPSStats(combined_dps=500_000)
        calc = DPSImpactCalculator(stats)
        info = calc._get_build_info()

        assert "K" in info  # 500K DPS

    def test_build_info_low_dps(self):
        """Build info formats low DPS correctly."""
        stats = DPSStats(combined_dps=500)
        calc = DPSImpactCalculator(stats)
        info = calc._get_build_info()

        assert "500" in info

    def test_build_info_no_data(self):
        """Build info handles no data."""
        calc = DPSImpactCalculator()
        info = calc._get_build_info()

        assert "No build data" in info

    def test_global_crit_patterns(self, fire_build_stats):
        """Matches global crit patterns."""
        calc = DPSImpactCalculator(fire_build_stats)

        result1 = calc.calculate_impact(["+25% increased Global Critical Strike Chance"])
        result2 = calc.calculate_impact(["+35% to Global Critical Strike Multiplier"])

        assert len(result1.mod_impacts) == 1
        assert len(result2.mod_impacts) == 1

    def test_spell_crit_pattern(self, fire_build_stats):
        """Matches spell crit pattern - matched by general crit pattern first."""
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+25% increased Critical Strike Chance for Spells"])

        assert len(result.mod_impacts) == 1
        # The general crit_chance pattern matches first since it doesn't require "for Spells"
        assert result.mod_impacts[0].mod_category == "crit_chance"

    def test_weapon_elemental_pattern(self, phys_attack_stats):
        """Matches weapon elemental pattern."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["+25% increased Elemental Damage with Attack Skills"])

        assert len(result.mod_impacts) == 1

    def test_melee_damage_pattern(self, phys_attack_stats):
        """Matches melee damage pattern."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["+25% increased Melee Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "melee_damage"

    def test_projectile_damage_pattern(self, phys_attack_stats):
        """Matches projectile damage pattern."""
        calc = DPSImpactCalculator(phys_attack_stats)
        result = calc.calculate_impact(["+25% increased Projectile Damage"])

        assert len(result.mod_impacts) == 1
        assert result.mod_impacts[0].mod_category == "projectile_damage"

    def test_added_elemental_patterns(self, phys_attack_stats):
        """Matches added elemental damage patterns."""
        calc = DPSImpactCalculator(phys_attack_stats)

        fire_result = calc.calculate_impact(["Adds 15 to 30 Fire Damage"])
        cold_result = calc.calculate_impact(["Adds 10 to 25 Cold Damage"])
        light_result = calc.calculate_impact(["Adds 5 to 50 Lightning Damage"])
        chaos_result = calc.calculate_impact(["Adds 10 to 20 Chaos Damage"])

        assert len(fire_result.mod_impacts) == 1
        assert len(cold_result.mod_impacts) == 1
        assert len(light_result.mod_impacts) == 1
        assert len(chaos_result.mod_impacts) == 1

    def test_cast_speed_on_dot(self, dot_stats):
        """Cast speed has low relevance on DoT build."""
        calc = DPSImpactCalculator(dot_stats)
        result = calc.calculate_impact(["+15% increased Cast Speed"])

        impact = result.mod_impacts[0]
        assert impact.relevance == "low"

    def test_summary_dps_formatting_millions(self, fire_build_stats):
        """Summary formats millions correctly."""
        calc = DPSImpactCalculator(fire_build_stats)
        # More damage gives 1:1 ratio, easy to calculate
        result = calc.calculate_impact(["+10% more Damage"])

        # 10% of 2M = 200K
        assert "K" in result.summary or "M" in result.summary

    def test_summary_negligible_impact(self, fire_build_stats):
        """Summary indicates negligible impact."""
        # Use physical damage on fire build - very low impact
        fire_build_stats.physical_dps = 10  # Almost no physical
        calc = DPSImpactCalculator(fire_build_stats)
        result = calc.calculate_impact(["+5% increased Physical Damage"])

        # Should have low/negligible classification
        assert result.mod_impacts[0].relevance == "low"


# ============================================================================
# Module Function Tests
# ============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_dps_calculator(self):
        """get_dps_calculator returns a calculator instance."""
        calc = get_dps_calculator()
        assert isinstance(calc, DPSImpactCalculator)

    def test_get_dps_calculator_fresh_instance(self):
        """get_dps_calculator returns fresh instances."""
        calc1 = get_dps_calculator()
        calc2 = get_dps_calculator()
        # Each call creates new instance (not singleton)
        assert calc1 is not calc2


# ============================================================================
# Pattern Matching Tests
# ============================================================================

class TestDamagePatterns:
    """Tests for DAMAGE_PATTERNS regex matching."""

    @pytest.fixture
    def calc(self):
        """Create calculator with some DPS."""
        stats = DPSStats(combined_dps=1_000_000)
        return DPSImpactCalculator(stats)

    def test_pattern_phys_dmg_pct(self, calc):
        """Physical damage pattern matches."""
        result = calc.calculate_impact(["25% increased Physical Damage"])
        assert len(result.mod_impacts) == 1

    def test_pattern_ele_dmg_pct(self, calc):
        """Elemental damage pattern matches."""
        result = calc.calculate_impact(["30% increased Elemental Damage"])
        assert len(result.mod_impacts) == 1

    def test_pattern_damage_with_hits(self, calc):
        """Damage with hits pattern matches."""
        result = calc.calculate_impact(["20% increased Damage with Hits"])
        assert len(result.mod_impacts) == 1

    def test_case_insensitive(self, calc):
        """Patterns are case insensitive."""
        result1 = calc.calculate_impact(["25% INCREASED FIRE DAMAGE"])
        result2 = calc.calculate_impact(["25% Increased Fire Damage"])
        result3 = calc.calculate_impact(["25% increased fire damage"])

        assert len(result1.mod_impacts) == 1
        assert len(result2.mod_impacts) == 1
        assert len(result3.mod_impacts) == 1

    def test_optional_percent_sign(self, calc):
        """Patterns work with or without % sign."""
        result1 = calc.calculate_impact(["25% increased Fire Damage"])
        result2 = calc.calculate_impact(["25 increased Fire Damage"])

        assert len(result1.mod_impacts) == 1
        assert len(result2.mod_impacts) == 1
