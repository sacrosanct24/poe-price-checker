"""Tests for core/build_archetype.py - Build archetype detection."""

import pytest
from unittest.mock import patch, MagicMock

from core.build_archetype import (
    DefenseType,
    DamageType,
    AttackType,
    BuildArchetype,
    detect_archetype,
    detect_archetype_from_build,
    get_default_archetype,
    load_archetype_weights,
    get_weight_multiplier,
    apply_archetype_weights,
    _get_stat,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestDefenseType:
    """Tests for DefenseType enum."""

    def test_all_defense_types(self):
        """Should have all expected defense types."""
        types = list(DefenseType)
        assert len(types) == 5
        assert DefenseType.LIFE in types
        assert DefenseType.ENERGY_SHIELD in types
        assert DefenseType.HYBRID in types
        assert DefenseType.LOW_LIFE in types
        assert DefenseType.WARD in types

    def test_enum_values(self):
        """Enum values should be strings."""
        assert DefenseType.LIFE.value == "life"
        assert DefenseType.ENERGY_SHIELD.value == "es"


class TestDamageType:
    """Tests for DamageType enum."""

    def test_all_damage_types(self):
        """Should have all expected damage types."""
        types = list(DamageType)
        assert len(types) == 8
        assert DamageType.PHYSICAL in types
        assert DamageType.FIRE in types
        assert DamageType.MINION in types
        assert DamageType.DOT in types


class TestAttackType:
    """Tests for AttackType enum."""

    def test_all_attack_types(self):
        """Should have all expected attack types."""
        types = list(AttackType)
        assert len(types) == 4
        assert AttackType.ATTACK in types
        assert AttackType.SPELL in types


# =============================================================================
# BuildArchetype Tests
# =============================================================================


class TestBuildArchetype:
    """Tests for BuildArchetype dataclass."""

    def test_default_archetype(self):
        """Should have sensible defaults."""
        arch = BuildArchetype()
        assert arch.defense_type == DefenseType.LIFE
        assert arch.damage_type == DamageType.PHYSICAL
        assert arch.attack_type == AttackType.ATTACK
        assert arch.is_crit is False
        assert arch.confidence == 0.5

    def test_to_dict(self):
        """Should serialize to dictionary."""
        arch = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            damage_type=DamageType.COLD,
            is_crit=True,
            primary_element="cold",
            confidence=0.9,
        )
        data = arch.to_dict()

        assert data["defense_type"] == "es"
        assert data["damage_type"] == "cold"
        assert data["is_crit"] is True
        assert data["primary_element"] == "cold"
        assert data["confidence"] == 0.9

    def test_from_dict(self):
        """Should deserialize from dictionary."""
        data = {
            "defense_type": "es",
            "damage_type": "fire",
            "attack_type": "spell",
            "is_crit": True,
            "is_dot": False,
            "is_minion": False,
            "primary_element": "fire",
            "main_skill": "Fireball",
            "confidence": 0.85,
        }
        arch = BuildArchetype.from_dict(data)

        assert arch.defense_type == DefenseType.ENERGY_SHIELD
        assert arch.damage_type == DamageType.FIRE
        assert arch.attack_type == AttackType.SPELL
        assert arch.is_crit is True
        assert arch.primary_element == "fire"
        assert arch.main_skill == "Fireball"

    def test_from_dict_defaults(self):
        """Should use defaults for missing keys."""
        arch = BuildArchetype.from_dict({})
        assert arch.defense_type == DefenseType.LIFE
        assert arch.is_crit is False

    def test_get_summary_life_crit_attack(self):
        """Summary should describe life crit attack build."""
        arch = BuildArchetype(
            defense_type=DefenseType.LIFE,
            damage_type=DamageType.PHYSICAL,
            attack_type=AttackType.ATTACK,
            is_crit=True,
        )
        summary = arch.get_summary()
        assert "Life" in summary
        assert "Physical" in summary
        assert "Attack" in summary
        assert "Crit" in summary

    def test_get_summary_es_spell(self):
        """Summary should describe ES spell build."""
        arch = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            attack_type=AttackType.SPELL,
            primary_element="cold",
        )
        summary = arch.get_summary()
        assert "ES" in summary
        assert "Spell" in summary
        assert "Cold" in summary

    def test_get_summary_minion(self):
        """Summary should describe minion build."""
        arch = BuildArchetype(
            is_minion=True,
            damage_type=DamageType.MINION,
        )
        summary = arch.get_summary()
        assert "Minion" in summary

    def test_get_summary_with_main_skill(self):
        """Summary should include main skill."""
        arch = BuildArchetype(main_skill="Cyclone")
        summary = arch.get_summary()
        assert "Cyclone" in summary

    def test_get_summary_totem(self):
        """Summary should indicate totem build."""
        arch = BuildArchetype(is_totem=True)
        summary = arch.get_summary()
        assert "Totem" in summary


# =============================================================================
# detect_archetype Tests
# =============================================================================


class TestDetectArchetype:
    """Tests for detect_archetype function."""

    def test_detect_life_build(self):
        """Should detect life-based build."""
        stats = {"Life": 5000, "EnergyShield": 200}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LIFE

    def test_detect_es_build(self):
        """Should detect ES-based build."""
        stats = {"Life": 500, "EnergyShield": 8000}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.ENERGY_SHIELD

    def test_detect_hybrid_build(self):
        """Should detect hybrid build."""
        stats = {"Life": 3000, "EnergyShield": 3000}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.HYBRID

    def test_detect_low_life(self):
        """Should detect low life build."""
        stats = {"Life": 5000, "EnergyShield": 3000, "LifeReserved": 70}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LOW_LIFE

    def test_detect_crit_build_high_chance(self):
        """Should detect crit build from high crit chance."""
        stats = {"CritChance": 65, "CritMultiplier": 400}
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_detect_crit_build_moderate(self):
        """Should detect moderate crit build."""
        stats = {"CritChance": 25}
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_detect_non_crit_build(self):
        """Should detect non-crit build."""
        stats = {"CritChance": 5}
        arch = detect_archetype(stats)
        assert arch.is_crit is False

    def test_detect_physical_damage(self):
        """Should detect physical damage build."""
        stats = {
            "PhysicalDPS": 1500000,
            "FireDPS": 100000,
            "ColdDPS": 100000,
            "LightningDPS": 100000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.PHYSICAL

    def test_detect_fire_damage(self):
        """Should detect fire damage build."""
        stats = {
            "PhysicalDPS": 100000,
            "FireDPS": 2000000,
            "ColdDPS": 100000,
            "LightningDPS": 100000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.FIRE
        assert arch.primary_element == "fire"

    def test_detect_cold_damage(self):
        """Should detect cold damage build."""
        stats = {"ColdDPS": 2000000}
        arch = detect_archetype(stats)
        assert arch.primary_element == "cold"

    def test_detect_minion_build(self):
        """Should detect minion build."""
        stats = {"MinionDPS": 5000000, "PhysicalDPS": 10000}
        arch = detect_archetype(stats)
        assert arch.is_minion is True
        assert arch.damage_type == DamageType.MINION

    def test_detect_dot_build(self):
        """Should detect DoT build."""
        stats = {"TotalDotDPS": 5000000, "PhysicalDPS": 0}
        arch = detect_archetype(stats)
        assert arch.is_dot is True
        assert arch.attack_type == AttackType.DOT

    def test_detect_spell_from_skill_name(self):
        """Should detect spell from skill name."""
        stats = {}
        arch = detect_archetype(stats, main_skill="Fireball")
        assert arch.attack_type == AttackType.SPELL

    def test_detect_attack_from_skill_name(self):
        """Should detect attack from skill name."""
        stats = {}
        arch = detect_archetype(stats, main_skill="Cyclone")
        assert arch.attack_type == AttackType.ATTACK

    def test_detect_spell_from_cast_speed(self):
        """Should detect spell from cast speed."""
        stats = {"CastSpeed": 3.0, "AttackSpeed": 1.0}
        arch = detect_archetype(stats)
        assert arch.attack_type == AttackType.SPELL

    def test_detect_attack_from_attack_speed(self):
        """Should detect attack from attack speed."""
        stats = {"AttackSpeed": 5.0, "CastSpeed": 1.0}
        arch = detect_archetype(stats)
        assert arch.attack_type == AttackType.ATTACK

    def test_detect_needs_fire_res(self):
        """Should detect need for fire resistance."""
        stats = {"FireResistOverCap": 10}  # Low overcap
        arch = detect_archetype(stats)
        assert arch.needs_fire_res is True

    def test_detect_capped_fire_res(self):
        """Should detect capped fire resistance."""
        stats = {"FireResistOverCap": 30}
        arch = detect_archetype(stats)
        assert arch.needs_fire_res is False

    def test_detect_needs_chaos_res(self):
        """Should detect need for chaos resistance."""
        stats = {"ChaosResist": -20}
        arch = detect_archetype(stats)
        assert arch.needs_chaos_res is True

    def test_detect_needs_strength(self):
        """Should detect high strength requirement."""
        stats = {"Str": 200}
        arch = detect_archetype(stats)
        assert arch.needs_strength is True

    def test_detect_no_strength_need(self):
        """Should detect no strength need."""
        stats = {"Str": 50}
        arch = detect_archetype(stats)
        assert arch.needs_strength is False

    def test_stores_source_stats(self):
        """Should store source stats for debugging."""
        stats = {"Life": 5000, "CritChance": 50}
        arch = detect_archetype(stats)
        assert arch.source_stats == stats

    def test_stores_main_skill(self):
        """Should store main skill."""
        arch = detect_archetype({}, main_skill="Lightning Arrow")
        assert arch.main_skill == "Lightning Arrow"

    def test_confidence_high_for_clear_build(self):
        """Should have high confidence for clear builds."""
        stats = {
            "Life": 5000,
            "EnergyShield": 200,
            "CritChance": 70,
            "PhysicalDPS": 2000000,
        }
        arch = detect_archetype(stats)
        assert arch.confidence > 0.7

    def test_confidence_low_for_unclear_build(self):
        """Should have lower confidence for unclear builds."""
        stats = {}
        arch = detect_archetype(stats)
        assert arch.confidence < 0.5


# =============================================================================
# detect_archetype_from_build Tests
# =============================================================================


class TestDetectArchetypeFromBuild:
    """Tests for detect_archetype_from_build function."""

    def test_with_build_object(self):
        """Should extract stats from build object."""
        mock_build = MagicMock()
        mock_build.stats = {"Life": 5000, "CritChance": 50}
        mock_build.main_skill = "Cyclone"

        arch = detect_archetype_from_build(mock_build)

        assert arch.main_skill == "Cyclone"

    def test_with_empty_build(self):
        """Should handle build without stats."""
        mock_build = MagicMock(spec=[])

        arch = detect_archetype_from_build(mock_build)

        assert arch is not None


# =============================================================================
# get_default_archetype Tests
# =============================================================================


class TestGetDefaultArchetype:
    """Tests for get_default_archetype function."""

    def test_returns_safe_defaults(self):
        """Should return safe defaults."""
        arch = get_default_archetype()
        assert arch.defense_type == DefenseType.LIFE
        assert arch.damage_type == DamageType.PHYSICAL
        assert arch.attack_type == AttackType.ATTACK

    def test_zero_confidence(self):
        """Should have zero confidence."""
        arch = get_default_archetype()
        assert arch.confidence == 0.0


# =============================================================================
# _get_stat Helper Tests
# =============================================================================


class TestGetStat:
    """Tests for _get_stat helper function."""

    def test_finds_first_matching_name(self):
        """Should return value for first matching name."""
        stats = {"Life": 5000}
        result = _get_stat(stats, ["Life", "TotalLife"])
        assert result == 5000

    def test_tries_multiple_names(self):
        """Should try multiple names."""
        stats = {"TotalLife": 6000}
        result = _get_stat(stats, ["Life", "TotalLife"])
        assert result == 6000

    def test_returns_default_when_not_found(self):
        """Should return default when not found."""
        stats = {}
        result = _get_stat(stats, ["Life"], default=0.0)
        assert result == 0.0


# =============================================================================
# Weight Loading and Application Tests
# =============================================================================


class TestWeightFunctions:
    """Tests for weight-related functions."""

    def test_load_archetype_weights_caches(self):
        """Should cache weights after loading."""
        # First call loads
        weights1 = load_archetype_weights()
        # Second call returns cached
        weights2 = load_archetype_weights()
        assert weights1 is weights2

    def test_get_weight_multiplier_default(self):
        """Should return 1.0 by default."""
        arch = BuildArchetype()
        multiplier = get_weight_multiplier(arch, "unknown_affix")
        assert multiplier == 1.0

    def test_apply_archetype_weights(self):
        """Should apply weights to affix scores."""
        arch = BuildArchetype()
        scores = {"life": 100, "es": 50, "fire_res": 30}

        with patch("core.build_archetype.load_archetype_weights", return_value={}):
            weighted = apply_archetype_weights(arch, scores)

        # With empty weights, scores should be unchanged
        assert weighted["life"] == 100
        assert weighted["es"] == 50
        assert weighted["fire_res"] == 30
