"""Tests for core/poe2_data.py - PoE2 Game Data Module."""

import pytest
from typing import Dict

from core.poe2_data import (
    # Enums
    RuneTier,
    ModifierType,
    DamageType,
    # Dataclasses
    Rune,
    CharmMod,
    BaseItem,
    PseudoRule,
    # Data
    POE2_RUNES,
    POE2_CHARM_MODS,
    POE2_ITEM_TYPES,
    POE2_NEW_ITEM_TYPES,
    PSEUDO_STAT_RULES,
    # Functions
    calculate_goodness_score,
    get_roll_quality_label,
    calculate_filter_range,
    calculate_stat_differential,
    prioritize_mods_by_differential,
    calculate_pseudo_stat,
    calculate_all_pseudo_stats,
    get_rune_by_name,
    get_runes_for_slot,
    get_runes_by_tier,
    get_charm_mods_by_group,
    is_poe2_item_type,
    is_poe2_exclusive_type,
)


# ============================================================================
# Enum Tests
# ============================================================================

class TestRuneTier:
    """Tests for RuneTier enum."""

    def test_lesser_value(self):
        """LESSER has value 0."""
        assert RuneTier.LESSER.value == 0

    def test_normal_value(self):
        """NORMAL has value 15."""
        assert RuneTier.NORMAL.value == 15

    def test_greater_value(self):
        """GREATER has value 30."""
        assert RuneTier.GREATER.value == 30

    def test_heritage_value(self):
        """HERITAGE has value 50."""
        assert RuneTier.HERITAGE.value == 50

    def test_soul_core_value(self):
        """SOUL_CORE has value 50."""
        assert RuneTier.SOUL_CORE.value == 50


class TestModifierType:
    """Tests for ModifierType enum."""

    def test_pseudo_value(self):
        assert ModifierType.PSEUDO.value == "pseudo"

    def test_explicit_value(self):
        assert ModifierType.EXPLICIT.value == "explicit"

    def test_implicit_value(self):
        assert ModifierType.IMPLICIT.value == "implicit"

    def test_crafted_value(self):
        assert ModifierType.CRAFTED.value == "crafted"

    def test_enchant_value(self):
        assert ModifierType.ENCHANT.value == "enchant"

    def test_rune_value(self):
        assert ModifierType.RUNE.value == "rune"

    def test_fractured_value(self):
        assert ModifierType.FRACTURED.value == "fractured"

    def test_corrupted_value(self):
        assert ModifierType.CORRUPTED.value == "corrupted"

    def test_sanctum_value(self):
        assert ModifierType.SANCTUM.value == "sanctum"


class TestDamageType:
    """Tests for DamageType enum."""

    def test_all_damage_types(self):
        """All damage types have correct values."""
        assert DamageType.PHYSICAL.value == "physical"
        assert DamageType.FIRE.value == "fire"
        assert DamageType.COLD.value == "cold"
        assert DamageType.LIGHTNING.value == "lightning"
        assert DamageType.CHAOS.value == "chaos"


# ============================================================================
# Dataclass Tests
# ============================================================================

class TestRune:
    """Tests for Rune dataclass."""

    def test_create_rune(self):
        """Can create a Rune."""
        rune = Rune(
            name="Test Rune",
            tier=RuneTier.NORMAL,
            stat="Adds Fire Damage",
            value="10 to 20",
            slots=["weapon", "ring"]
        )

        assert rune.name == "Test Rune"
        assert rune.tier == RuneTier.NORMAL
        assert rune.stat == "Adds Fire Damage"
        assert rune.value == "10 to 20"
        assert rune.slots == ["weapon", "ring"]
        assert rune.stat_id is None

    def test_rune_with_stat_id(self):
        """Rune can have stat_id."""
        rune = Rune(
            name="Test",
            tier=RuneTier.LESSER,
            stat="stat",
            value="5",
            slots=["boots"],
            stat_id="custom_stat_id"
        )

        assert rune.stat_id == "custom_stat_id"


class TestCharmMod:
    """Tests for CharmMod dataclass."""

    def test_create_charm_mod(self):
        """Can create a CharmMod."""
        mod = CharmMod(
            affix="Investigator's",
            stat="increased Charm Effect Duration",
            tier=1,
            min_value=16,
            max_value=20,
            level_req=1,
            group="CharmIncreasedDuration"
        )

        assert mod.affix == "Investigator's"
        assert mod.tier == 1
        assert mod.min_value == 16
        assert mod.max_value == 20
        assert mod.trade_hash is None

    def test_charm_mod_with_trade_hash(self):
        """CharmMod can have trade_hash."""
        mod = CharmMod(
            affix="Test",
            stat="stat",
            tier=1,
            min_value=1,
            max_value=10,
            level_req=1,
            group="Test",
            trade_hash="hash123"
        )

        assert mod.trade_hash == "hash123"


class TestBaseItem:
    """Tests for BaseItem dataclass."""

    def test_create_base_item_minimal(self):
        """Can create BaseItem with minimal fields."""
        item = BaseItem(
            name="Simple Robe",
            item_type="body_armour",
            sub_type="cloth",
            level_req=1
        )

        assert item.name == "Simple Robe"
        assert item.item_type == "body_armour"
        assert item.str_req == 0
        assert item.dex_req == 0
        assert item.int_req == 0
        assert item.armour == 0
        assert item.socket_limit == 4
        assert item.implicit is None

    def test_create_base_item_full(self):
        """Can create BaseItem with all fields."""
        item = BaseItem(
            name="Astral Plate",
            item_type="body_armour",
            sub_type="str_armour",
            level_req=62,
            str_req=180,
            dex_req=0,
            int_req=0,
            armour=711,
            evasion=0,
            energy_shield=0,
            movement_penalty=0.05,
            socket_limit=6,
            implicit="+12% to all Elemental Resistances"
        )

        assert item.str_req == 180
        assert item.armour == 711
        assert item.movement_penalty == 0.05
        assert item.socket_limit == 6
        assert item.implicit == "+12% to all Elemental Resistances"


class TestPseudoRule:
    """Tests for PseudoRule dataclass."""

    def test_create_pseudo_rule(self):
        """Can create PseudoRule."""
        rule = PseudoRule(
            pseudo_stat="pseudo_total_life",
            sources=[
                ("to maximum Life", 1.0),
                ("to Strength", 0.5),
            ],
            requires="to maximum Life"
        )

        assert rule.pseudo_stat == "pseudo_total_life"
        assert len(rule.sources) == 2
        assert rule.requires == "to maximum Life"

    def test_pseudo_rule_without_requires(self):
        """PseudoRule can have no requirements."""
        rule = PseudoRule(
            pseudo_stat="pseudo_total_resistance",
            sources=[("to Fire Resistance", 1.0)]
        )

        assert rule.requires is None


# ============================================================================
# POE2_RUNES Data Tests
# ============================================================================

class TestPoe2Runes:
    """Tests for POE2_RUNES data."""

    def test_runes_not_empty(self):
        """Runes data is not empty."""
        assert len(POE2_RUNES) > 0

    def test_desert_rune_exists(self):
        """Desert Rune exists in data."""
        assert "Desert Rune" in POE2_RUNES

    def test_rune_data_valid(self):
        """Rune data is valid."""
        rune = POE2_RUNES["Desert Rune"]

        assert isinstance(rune, Rune)
        assert rune.tier == RuneTier.NORMAL
        assert "weapon" in rune.slots

    def test_all_runes_have_slots(self):
        """All runes have at least one slot."""
        for name, rune in POE2_RUNES.items():
            assert len(rune.slots) > 0, f"{name} has no slots"

    def test_heritage_runes_exist(self):
        """Heritage runes exist."""
        heritage = [r for r in POE2_RUNES.values() if r.tier == RuneTier.HERITAGE]
        assert len(heritage) > 0

    def test_soul_cores_exist(self):
        """Soul cores exist."""
        souls = [r for r in POE2_RUNES.values() if r.tier == RuneTier.SOUL_CORE]
        assert len(souls) > 0


# ============================================================================
# POE2_CHARM_MODS Data Tests
# ============================================================================

class TestPoe2CharmMods:
    """Tests for POE2_CHARM_MODS data."""

    def test_charm_mods_not_empty(self):
        """Charm mods data is not empty."""
        assert len(POE2_CHARM_MODS) > 0

    def test_charm_mods_have_tiers(self):
        """Charm mods have tiers from 1-3."""
        tiers = {mod.tier for mod in POE2_CHARM_MODS}
        assert 1 in tiers
        assert 2 in tiers
        assert 3 in tiers

    def test_charm_mods_have_groups(self):
        """Charm mods are grouped."""
        groups = {mod.group for mod in POE2_CHARM_MODS}
        assert len(groups) > 0


# ============================================================================
# Item Type Data Tests
# ============================================================================

class TestItemTypes:
    """Tests for item type data."""

    def test_item_types_not_empty(self):
        """Item types set is not empty."""
        assert len(POE2_ITEM_TYPES) > 0

    def test_common_types_exist(self):
        """Common item types exist."""
        assert "helmet" in POE2_ITEM_TYPES
        assert "body_armour" in POE2_ITEM_TYPES
        assert "gloves" in POE2_ITEM_TYPES
        assert "boots" in POE2_ITEM_TYPES
        assert "ring" in POE2_ITEM_TYPES
        assert "amulet" in POE2_ITEM_TYPES

    def test_new_types_not_empty(self):
        """New PoE2 types set is not empty."""
        assert len(POE2_NEW_ITEM_TYPES) > 0

    def test_new_types_subset(self):
        """New types are subset of all types."""
        assert POE2_NEW_ITEM_TYPES.issubset(POE2_ITEM_TYPES)

    def test_focus_is_new(self):
        """Focus is a new PoE2 item type."""
        assert "focus" in POE2_NEW_ITEM_TYPES

    def test_crossbow_is_new(self):
        """Crossbow is a new PoE2 item type."""
        assert "crossbow" in POE2_NEW_ITEM_TYPES


# ============================================================================
# Goodness Score Tests
# ============================================================================

class TestCalculateGoodnessScore:
    """Tests for calculate_goodness_score function."""

    def test_perfect_roll(self):
        """Perfect roll returns 1.0."""
        assert calculate_goodness_score(100, 80, 100) == 1.0

    def test_worst_roll(self):
        """Worst roll returns 0.0."""
        assert calculate_goodness_score(80, 80, 100) == 0.0

    def test_mid_roll(self):
        """Mid roll returns 0.5."""
        assert calculate_goodness_score(90, 80, 100) == 0.5

    def test_fixed_value_returns_1(self):
        """Fixed value (min == max) returns 1.0."""
        assert calculate_goodness_score(50, 50, 50) == 1.0

    def test_below_min_returns_0(self):
        """Value below min returns 0.0."""
        assert calculate_goodness_score(70, 80, 100) == 0.0

    def test_above_max_returns_1(self):
        """Value above max returns 1.0."""
        assert calculate_goodness_score(110, 80, 100) == 1.0

    def test_decimal_values(self):
        """Handles decimal values."""
        score = calculate_goodness_score(95.0, 80.0, 100.0)
        assert score == pytest.approx(0.75)


class TestGetRollQualityLabel:
    """Tests for get_roll_quality_label function."""

    def test_perfect_label(self):
        """0.95+ returns Perfect."""
        assert get_roll_quality_label(0.95) == "Perfect"
        assert get_roll_quality_label(1.0) == "Perfect"

    def test_excellent_label(self):
        """0.80-0.94 returns Excellent."""
        assert get_roll_quality_label(0.80) == "Excellent"
        assert get_roll_quality_label(0.94) == "Excellent"

    def test_good_label(self):
        """0.60-0.79 returns Good."""
        assert get_roll_quality_label(0.60) == "Good"
        assert get_roll_quality_label(0.79) == "Good"

    def test_average_label(self):
        """0.40-0.59 returns Average."""
        assert get_roll_quality_label(0.40) == "Average"
        assert get_roll_quality_label(0.59) == "Average"

    def test_below_average_label(self):
        """0.20-0.39 returns Below Average."""
        assert get_roll_quality_label(0.20) == "Below Average"
        assert get_roll_quality_label(0.39) == "Below Average"

    def test_low_label(self):
        """Below 0.20 returns Low."""
        assert get_roll_quality_label(0.0) == "Low"
        assert get_roll_quality_label(0.19) == "Low"


class TestCalculateFilterRange:
    """Tests for calculate_filter_range function."""

    def test_basic_range(self):
        """Calculates range correctly."""
        fmin, fmax = calculate_filter_range(90, 80, 100, 0.2)

        # Range is 20, 20% = 4, so 90 +/- 4 = 86-94
        assert fmin == pytest.approx(86.0)
        assert fmax == pytest.approx(94.0)

    def test_clamped_to_min(self):
        """Range is clamped to tier min."""
        fmin, fmax = calculate_filter_range(82, 80, 100, 0.2)

        # 82 - 4 = 78, but clamped to min 80
        assert fmin == 80.0

    def test_clamped_to_max(self):
        """Range is clamped to tier max."""
        fmin, fmax = calculate_filter_range(98, 80, 100, 0.2)

        # 98 + 4 = 102, but clamped to max 100
        assert fmax == 100.0

    def test_custom_range_percent(self):
        """Supports custom range percent."""
        fmin, fmax = calculate_filter_range(90, 80, 100, 0.5)

        # Range is 20, 50% = 10
        assert fmin == pytest.approx(80.0)
        assert fmax == pytest.approx(100.0)


# ============================================================================
# Stat Differential Tests
# ============================================================================

class TestCalculateStatDifferential:
    """Tests for calculate_stat_differential function."""

    def test_positive_differential(self):
        """Calculates positive differential."""
        result = calculate_stat_differential(100, 150, 1.0)
        assert result == 50.0

    def test_negative_differential(self):
        """Calculates negative differential."""
        result = calculate_stat_differential(150, 100, 1.0)
        assert result == -50.0

    def test_with_weight(self):
        """Applies weight multiplier."""
        result = calculate_stat_differential(100, 150, 2.0)
        assert result == 100.0

    def test_zero_differential(self):
        """Handles zero differential."""
        result = calculate_stat_differential(100, 100, 1.0)
        assert result == 0.0


class TestPrioritizeModsByDifferential:
    """Tests for prioritize_mods_by_differential function."""

    def test_sorts_by_absolute_value(self):
        """Sorts by absolute differential (highest first)."""
        diffs = {
            "mod_a": 10,
            "mod_b": -50,
            "mod_c": 30,
        }

        result = prioritize_mods_by_differential(diffs)

        assert result[0] == "mod_b"  # |-50| = 50, highest
        assert result[1] == "mod_c"  # |30| = 30
        assert result[2] == "mod_a"  # |10| = 10

    def test_respects_max_limit(self):
        """Respects max_filters limit."""
        diffs = {f"mod_{i}": i for i in range(50)}

        result = prioritize_mods_by_differential(diffs, max_filters=10)

        assert len(result) == 10

    def test_default_limit_is_35(self):
        """Default max_filters is 35."""
        diffs = {f"mod_{i}": i for i in range(50)}

        result = prioritize_mods_by_differential(diffs)

        assert len(result) == 35


# ============================================================================
# Pseudo Stat Tests
# ============================================================================

class TestCalculatePseudoStat:
    """Tests for calculate_pseudo_stat function."""

    def test_calculates_total_resistance(self):
        """Calculates total elemental resistance."""
        rule = next(r for r in PSEUDO_STAT_RULES if r.pseudo_stat == "pseudo_total_elemental_resistance")

        mods = {
            "+45% to Fire Resistance": 45,
            "+40% to Cold Resistance": 40,
            "+35% to Lightning Resistance": 35,
        }

        result = calculate_pseudo_stat(rule, mods)

        assert result == 120.0  # 45 + 40 + 35

    def test_all_ele_res_counts_triple(self):
        """All elemental resistance counts 3x."""
        rule = next(r for r in PSEUDO_STAT_RULES if r.pseudo_stat == "pseudo_total_elemental_resistance")

        mods = {
            "+10% to all Elemental Resistances": 10,
        }

        result = calculate_pseudo_stat(rule, mods)

        assert result == 30.0  # 10 * 3

    def test_respects_requirements(self):
        """Returns None when requirements not met."""
        rule = next(r for r in PSEUDO_STAT_RULES if r.pseudo_stat == "pseudo_total_life")

        # Only Strength, no Life - requirement not met
        mods = {
            "+25 to Strength": 25,
        }

        result = calculate_pseudo_stat(rule, mods)

        assert result is None

    def test_meets_requirements(self):
        """Returns value when requirements met."""
        rule = next(r for r in PSEUDO_STAT_RULES if r.pseudo_stat == "pseudo_total_life")

        mods = {
            "+80 to maximum Life": 80,
            "+25 to Strength": 25,
        }

        result = calculate_pseudo_stat(rule, mods)

        # 80 * 1.0 + 25 * 0.5 = 92.5
        assert result == pytest.approx(92.5)

    def test_returns_none_if_no_matches(self):
        """Returns None if no mods match sources."""
        rule = next(r for r in PSEUDO_STAT_RULES if r.pseudo_stat == "pseudo_total_elemental_resistance")

        mods = {
            "+50 to Maximum Life": 50,
        }

        result = calculate_pseudo_stat(rule, mods)

        assert result is None


class TestCalculateAllPseudoStats:
    """Tests for calculate_all_pseudo_stats function."""

    def test_calculates_multiple_pseudos(self):
        """Calculates multiple pseudo stats."""
        mods = {
            "+45% to Fire Resistance": 45,
            "+40% to Cold Resistance": 40,
            "+80 to maximum Life": 80,
            "+25 to Strength": 25,
        }

        result = calculate_all_pseudo_stats(mods)

        assert "pseudo_total_elemental_resistance" in result
        assert "pseudo_total_life" in result

    def test_empty_mods_returns_empty(self):
        """Empty mods returns empty dict."""
        result = calculate_all_pseudo_stats({})
        assert result == {}

    def test_excludes_zero_values(self):
        """Excludes pseudo stats with zero total."""
        mods = {
            "+45% to Fire Resistance": 45,
        }

        result = calculate_all_pseudo_stats(mods)

        # Life pseudo shouldn't be included (no life mods)
        assert "pseudo_total_life" not in result


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestGetRuneByName:
    """Tests for get_rune_by_name function."""

    def test_finds_existing_rune(self):
        """Finds rune that exists."""
        rune = get_rune_by_name("Desert Rune")

        assert rune is not None
        assert rune.name == "Desert Rune"

    def test_returns_none_for_unknown(self):
        """Returns None for unknown rune."""
        rune = get_rune_by_name("Nonexistent Rune")
        assert rune is None


class TestGetRunesForSlot:
    """Tests for get_runes_for_slot function."""

    def test_finds_boot_runes(self):
        """Finds runes for boots slot."""
        runes = get_runes_for_slot("boots")

        assert len(runes) > 0
        # Stone runes should be included
        names = [r.name for r in runes]
        assert any("Stone" in n for n in names)

    def test_finds_weapon_runes(self):
        """Finds runes for weapon slot."""
        runes = get_runes_for_slot("weapon")

        assert len(runes) > 0
        # Desert/Glacial/Storm runes should be included
        names = [r.name for r in runes]
        assert any("Desert" in n or "Glacial" in n or "Storm" in n for n in names)

    def test_empty_for_unknown_slot(self):
        """Returns empty for unknown slot."""
        runes = get_runes_for_slot("unknown_slot")
        assert runes == []


class TestGetRunesByTier:
    """Tests for get_runes_by_tier function."""

    def test_finds_lesser_runes(self):
        """Finds all lesser runes."""
        runes = get_runes_by_tier(RuneTier.LESSER)

        assert len(runes) > 0
        assert all(r.tier == RuneTier.LESSER for r in runes)

    def test_finds_greater_runes(self):
        """Finds all greater runes."""
        runes = get_runes_by_tier(RuneTier.GREATER)

        assert len(runes) > 0
        assert all(r.tier == RuneTier.GREATER for r in runes)


class TestGetCharmModsByGroup:
    """Tests for get_charm_mods_by_group function."""

    def test_finds_duration_mods(self):
        """Finds duration charm mods."""
        mods = get_charm_mods_by_group("CharmIncreasedDuration")

        assert len(mods) > 0
        assert all(m.group == "CharmIncreasedDuration" for m in mods)

    def test_empty_for_unknown_group(self):
        """Returns empty for unknown group."""
        mods = get_charm_mods_by_group("UnknownGroup")
        assert mods == []


class TestIsPoe2ItemType:
    """Tests for is_poe2_item_type function."""

    def test_helmet_is_poe2(self):
        """Helmet is a PoE2 item type."""
        assert is_poe2_item_type("helmet") is True

    def test_focus_is_poe2(self):
        """Focus is a PoE2 item type."""
        assert is_poe2_item_type("focus") is True

    def test_case_insensitive(self):
        """Check is case insensitive."""
        assert is_poe2_item_type("HELMET") is True
        assert is_poe2_item_type("Helmet") is True

    def test_unknown_type(self):
        """Unknown type returns False."""
        assert is_poe2_item_type("unknown_type") is False


class TestIsPoe2ExclusiveType:
    """Tests for is_poe2_exclusive_type function."""

    def test_focus_is_exclusive(self):
        """Focus is PoE2 exclusive."""
        assert is_poe2_exclusive_type("focus") is True

    def test_crossbow_is_exclusive(self):
        """Crossbow is PoE2 exclusive."""
        assert is_poe2_exclusive_type("crossbow") is True

    def test_helmet_is_not_exclusive(self):
        """Helmet is not PoE2 exclusive."""
        assert is_poe2_exclusive_type("helmet") is False

    def test_case_insensitive(self):
        """Check is case insensitive."""
        assert is_poe2_exclusive_type("FOCUS") is True
