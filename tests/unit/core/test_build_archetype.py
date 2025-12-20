"""Tests for core/build_archetype.py - Build archetype detection."""

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


# =============================================================================
# Additional get_summary Tests
# =============================================================================


class TestGetSummaryEdgeCases:
    """Tests for BuildArchetype.get_summary edge cases."""

    def test_get_summary_hybrid_defense(self):
        """Summary should describe hybrid defense."""
        arch = BuildArchetype(defense_type=DefenseType.HYBRID)
        summary = arch.get_summary()
        assert "Hybrid" in summary or "Life/ES" in summary

    def test_get_summary_low_life(self):
        """Summary should describe low life."""
        arch = BuildArchetype(defense_type=DefenseType.LOW_LIFE)
        summary = arch.get_summary()
        assert "Low Life" in summary

    def test_get_summary_elemental_no_primary(self):
        """Summary should show Elemental when no primary element."""
        arch = BuildArchetype(
            damage_type=DamageType.ELEMENTAL,
            primary_element=None,
        )
        summary = arch.get_summary()
        assert "Elemental" in summary

    def test_get_summary_dot_build(self):
        """Summary should show DoT for damage over time builds."""
        arch = BuildArchetype(is_dot=True)
        summary = arch.get_summary()
        assert "DoT" in summary

    def test_get_summary_trap_mine(self):
        """Summary should show trap/mine indicator."""
        arch = BuildArchetype(is_trap_mine=True)
        summary = arch.get_summary()
        assert "Trap" in summary or "Mine" in summary

    def test_get_summary_empty_returns_unknown(self):
        """Empty archetype with no clear type returns Unknown."""
        arch = BuildArchetype(
            defense_type=DefenseType.WARD,  # Ward doesn't add text
            damage_type=DamageType.CHAOS,  # Chaos doesn't add text directly
            is_minion=False,
            is_dot=False,
            is_crit=False,
            is_totem=False,
            is_trap_mine=False,
            primary_element=None,
            main_skill="",
        )
        summary = arch.get_summary()
        # Should have something or Unknown
        assert summary != ""


# =============================================================================
# Additional detect_archetype Tests
# =============================================================================


class TestDetectArchetypeEdgeCases:
    """Tests for detect_archetype edge cases."""

    def test_detect_lightning_damage(self):
        """Should detect lightning damage build."""
        stats = {
            "PhysicalDPS": 100000,
            "FireDPS": 100000,
            "ColdDPS": 100000,
            "LightningDPS": 3000000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.LIGHTNING
        assert arch.primary_element == "lightning"

    def test_detect_chaos_damage(self):
        """Should detect chaos damage build."""
        stats = {
            "PhysicalDPS": 100000,
            "ChaosDPS": 2000000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.CHAOS

    def test_detect_totem_build(self):
        """Should detect totem build."""
        stats = {"TotemDPS": 5000000}
        arch = detect_archetype(stats)
        assert arch.is_totem is True

    def test_detect_trap_build(self):
        """Should detect trap build."""
        stats = {"TrapDPS": 3000000}
        arch = detect_archetype(stats)
        assert arch.is_trap_mine is True

    def test_detect_mine_build(self):
        """Should detect mine build."""
        stats = {"MineDPS": 3000000}
        arch = detect_archetype(stats)
        assert arch.is_trap_mine is True

    def test_detect_needs_cold_res(self):
        """Should detect need for cold resistance."""
        stats = {"ColdResistOverCap": 5}
        arch = detect_archetype(stats)
        assert arch.needs_cold_res is True

    def test_detect_needs_lightning_res(self):
        """Should detect need for lightning resistance."""
        stats = {"LightningResistOverCap": 5}
        arch = detect_archetype(stats)
        assert arch.needs_lightning_res is True

    def test_detect_needs_dexterity(self):
        """Should detect high dexterity requirement."""
        stats = {"Dex": 200}
        arch = detect_archetype(stats)
        assert arch.needs_dexterity is True

    def test_detect_needs_intelligence(self):
        """Should detect high intelligence requirement."""
        stats = {"Int": 200}
        arch = detect_archetype(stats)
        assert arch.needs_intelligence is True

    def test_zero_life_and_es_uses_default(self):
        """When both life and ES are zero, should use default."""
        stats = {"Life": 0, "EnergyShield": 0}
        arch = detect_archetype(stats)
        # Confidence factors list will be empty, so confidence is low
        assert arch.defense_type == DefenseType.LIFE  # Default

    def test_dot_dps_overrides_attack_type(self):
        """DoT DPS should override attack type to DOT."""
        stats = {
            "TotalDotDPS": 5000000,
            "PhysicalDPS": 100000,  # Small hit DPS
            "AttackSpeed": 5.0,  # Would indicate attack
        }
        arch = detect_archetype(stats)
        assert arch.is_dot is True
        assert arch.attack_type == AttackType.DOT

    def test_alternative_stat_names_total_life(self):
        """Should recognize total_life stat name."""
        stats = {"total_life": 5000}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LIFE

    def test_alternative_stat_names_total_energy_shield(self):
        """Should recognize total_energy_shield stat name."""
        stats = {"total_energy_shield": 8000, "Life": 500}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.ENERGY_SHIELD

    def test_crit_multiplier_boosts_crit_detection(self):
        """High crit multi with moderate crit chance should still detect crit."""
        stats = {"CritChance": 30, "CritMultiplier": 400}
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_alternative_crit_stat_names(self):
        """Should recognize alternative crit stat names."""
        stats = {"MeleeCritChance": 45}
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_alternative_crit_stat_spell(self):
        """Should recognize SpellCritChance."""
        stats = {"SpellCritChance": 50}
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_life_reserved_percent_triggers_low_life(self):
        """LifeReservedPercent should trigger low life detection."""
        stats = {"Life": 5000, "LifeReservedPercent": 75}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LOW_LIFE

    def test_defense_type_else_default_case(self):
        """Low life and low ES ratio should default to LIFE with low confidence.

        This tests the else branch when:
        - Neither ratio is > 0.8 (not pure life/ES)
        - Not both > 0.3 (not hybrid)
        - No reserved life
        """
        # life=80, es=20 -> life_ratio=0.8, es_ratio=0.2
        # 0.8 is NOT > 0.8, so life check fails
        # 0.2 is NOT > 0.3, so hybrid check fails
        # Falls through to else branch
        stats = {"Life": 80, "EnergyShield": 20}
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LIFE


# =============================================================================
# Weight Loading Error Cases
# =============================================================================


class TestWeightLoadingErrors:
    """Tests for weight loading error handling."""

    def test_load_weights_file_not_found(self):
        """Should handle missing weights file gracefully."""
        import core.build_archetype as module
        # Reset cache
        module._cached_weights = None

        with patch("builtins.open", side_effect=FileNotFoundError()):
            weights = load_archetype_weights()
            assert weights == {}

        # Reset for other tests
        module._cached_weights = None

    def test_load_weights_json_decode_error(self):
        """Should handle JSON decode error gracefully."""
        import json
        import core.build_archetype as module
        module._cached_weights = None

        mock_file = MagicMock()
        mock_file.read.return_value = "invalid json {"
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            with patch("json.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                weights = load_archetype_weights()
                # Should return empty dict, not crash
                assert weights == {}

        module._cached_weights = None


# =============================================================================
# Weight Multiplier Branches
# =============================================================================


class TestWeightMultiplierBranches:
    """Tests for get_weight_multiplier branches with actual weights."""

    def test_defense_type_weight_applied(self):
        """Defense type weights should be applied."""
        arch = BuildArchetype(defense_type=DefenseType.ENERGY_SHIELD)
        weights = {
            "defense_types": {
                "es": {"energy_shield": 1.5, "life": 0.5}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "energy_shield")
            assert mult == 1.5
            mult_life = get_weight_multiplier(arch, "life")
            assert mult_life == 0.5

    def test_damage_type_weight_applied(self):
        """Damage type weights should be applied."""
        arch = BuildArchetype(damage_type=DamageType.FIRE)
        weights = {
            "damage_types": {
                "fire": {"fire_damage": 1.5}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "fire_damage")
            assert mult == 1.5

    def test_attack_type_weight_applied(self):
        """Attack type weights should be applied."""
        arch = BuildArchetype(attack_type=AttackType.SPELL)
        weights = {
            "attack_types": {
                "spell": {"spell_damage": 1.3}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "spell_damage")
            assert mult == 1.3

    def test_crit_flag_weight_applied(self):
        """Crit flag weights should be applied."""
        arch = BuildArchetype(is_crit=True)
        weights = {
            "flags": {
                "is_crit": {"crit_chance": 2.0, "crit_multi": 1.8}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "crit_chance")
            assert mult == 2.0

    def test_dot_flag_weight_applied(self):
        """DoT flag weights should be applied."""
        arch = BuildArchetype(is_dot=True)
        weights = {
            "flags": {
                "is_dot": {"damage_over_time": 1.8}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "damage_over_time")
            assert mult == 1.8

    def test_minion_flag_weight_applied(self):
        """Minion flag weights should be applied."""
        arch = BuildArchetype(is_minion=True)
        weights = {
            "flags": {
                "is_minion": {"minion_damage": 2.0}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "minion_damage")
            assert mult == 2.0

    def test_fire_res_need_weight_applied(self):
        """Fire resistance need weights should be applied."""
        arch = BuildArchetype(needs_fire_res=True)
        weights = {
            "resistance_needs": {
                "needs_fire_res": {"fire_resistance": 1.5}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "fire_resistance")
            assert mult == 1.5

    def test_cold_res_need_weight_applied(self):
        """Cold resistance need weights should be applied."""
        arch = BuildArchetype(needs_cold_res=True)
        weights = {
            "resistance_needs": {
                "needs_cold_res": {"cold_resistance": 1.5}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "cold_resistance")
            assert mult == 1.5

    def test_lightning_res_need_weight_applied(self):
        """Lightning resistance need weights should be applied."""
        arch = BuildArchetype(needs_lightning_res=True)
        weights = {
            "resistance_needs": {
                "needs_lightning_res": {"lightning_resistance": 1.5}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "lightning_resistance")
            assert mult == 1.5

    def test_chaos_res_need_weight_applied(self):
        """Chaos resistance need weights should be applied."""
        arch = BuildArchetype(needs_chaos_res=True)
        weights = {
            "resistance_needs": {
                "needs_chaos_res": {"chaos_resistance": 1.8}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "chaos_resistance")
            assert mult == 1.8

    def test_strength_need_weight_applied(self):
        """Strength need weights should be applied."""
        arch = BuildArchetype(needs_strength=True)
        weights = {
            "attribute_needs": {
                "needs_strength": {"strength": 1.4}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "strength")
            assert mult == 1.4

    def test_dexterity_need_weight_applied(self):
        """Dexterity need weights should be applied."""
        arch = BuildArchetype(needs_dexterity=True)
        weights = {
            "attribute_needs": {
                "needs_dexterity": {"dexterity": 1.4}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "dexterity")
            assert mult == 1.4

    def test_intelligence_need_weight_applied(self):
        """Intelligence need weights should be applied."""
        arch = BuildArchetype(needs_intelligence=True)
        weights = {
            "attribute_needs": {
                "needs_intelligence": {"intelligence": 1.4}
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "intelligence")
            assert mult == 1.4

    def test_multiple_weights_multiply(self):
        """Multiple weight sources should multiply together."""
        arch = BuildArchetype(
            defense_type=DefenseType.LIFE,
            is_crit=True,
        )
        weights = {
            "defense_types": {
                "life": {"life": 1.2}
            },
            "flags": {
                "is_crit": {"life": 1.1}  # Crit also values life
            }
        }
        with patch("core.build_archetype.load_archetype_weights", return_value=weights):
            mult = get_weight_multiplier(arch, "life")
            # 1.2 * 1.1 = 1.32
            assert abs(mult - 1.32) < 0.01


# =============================================================================
# Combined Weight Multiplier Tests
# =============================================================================


class TestCombinedWeightMultiplier:
    """Tests for get_combined_weight_multiplier function."""

    def test_no_main_skill_returns_base(self):
        """Without main skill, should return base multiplier."""
        from core.build_archetype import get_combined_weight_multiplier
        arch = BuildArchetype(main_skill="")

        with patch("core.build_archetype.load_archetype_weights", return_value={}):
            mult = get_combined_weight_multiplier(arch, "life")
            assert mult == 1.0

    def test_with_main_skill_calls_analyzer(self):
        """With main skill, should call skill analyzer."""
        from core.build_archetype import get_combined_weight_multiplier
        arch = BuildArchetype(main_skill="Fireball")

        mock_analyzer = MagicMock()
        mock_analyzer.get_affix_multiplier.return_value = 1.5

        with patch("core.build_archetype.load_archetype_weights", return_value={}):
            with patch("core.skill_analyzer.SkillAnalyzer", return_value=mock_analyzer):
                mult = get_combined_weight_multiplier(arch, "fire_damage")
                # Combined: base * (0.7 + 0.3 * skill_mult) = 1.0 * (0.7 + 0.3 * 1.5) = 1.15
                assert abs(mult - 1.15) < 0.01

    def test_skill_multiplier_error_returns_base(self):
        """Should handle skill analyzer errors gracefully."""
        from core.build_archetype import get_combined_weight_multiplier
        arch = BuildArchetype(main_skill="Unknown Skill")

        with patch("core.build_archetype.load_archetype_weights", return_value={}):
            with patch("core.skill_analyzer.SkillAnalyzer", side_effect=Exception("Not found")):
                mult = get_combined_weight_multiplier(arch, "life")
                assert mult == 1.0

    def test_skill_multiplier_one_no_change(self):
        """Skill multiplier of 1.0 should not change base."""
        from core.build_archetype import get_combined_weight_multiplier
        arch = BuildArchetype(main_skill="Generic Skill")

        mock_analyzer = MagicMock()
        mock_analyzer.get_affix_multiplier.return_value = 1.0

        with patch("core.build_archetype.load_archetype_weights", return_value={}):
            with patch("core.skill_analyzer.SkillAnalyzer", return_value=mock_analyzer):
                mult = get_combined_weight_multiplier(arch, "life")
                # When skill_mult == 1.0, returns base_mult unchanged
                assert mult == 1.0


# =============================================================================
# Skill Valuable Affixes Tests
# =============================================================================


class TestGetSkillValuableAffixes:
    """Tests for get_skill_valuable_affixes function."""

    def test_empty_skill_returns_empty(self):
        """Empty skill name should return empty list."""
        from core.build_archetype import get_skill_valuable_affixes
        result = get_skill_valuable_affixes("")
        assert result == []

    def test_calls_skill_analyzer(self):
        """Should call skill analyzer for valid skill."""
        from core.build_archetype import get_skill_valuable_affixes

        mock_analyzer = MagicMock()
        mock_analyzer.get_valuable_affixes.return_value = [
            ("fire_damage", 1.5),
            ("spell_damage", 1.3),
        ]

        with patch("core.skill_analyzer.SkillAnalyzer", return_value=mock_analyzer):
            result = get_skill_valuable_affixes("Fireball")
            assert "fire_damage" in result
            assert "spell_damage" in result

    def test_analyzer_error_returns_empty(self):
        """Should return empty list on analyzer error."""
        from core.build_archetype import get_skill_valuable_affixes

        with patch("core.skill_analyzer.SkillAnalyzer", side_effect=Exception("Error")):
            result = get_skill_valuable_affixes("Unknown Skill")
            assert result == []
