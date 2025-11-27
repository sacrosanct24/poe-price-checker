"""
Tests for the PoE2 data module.

Tests:
- Rune data and lookups
- Charm modifier data
- Goodness score calculations
- Filter range calculations
- Pseudo stat aggregation
- Stat differential calculations
"""
import pytest
from core.poe2_data import (
    # Enums
    RuneTier, ModifierType, DamageType,
    # Data classes
    Rune, CharmMod, BaseItem, PseudoRule,
    # Data constants
    POE2_RUNES, POE2_CHARM_MODS, POE2_ITEM_TYPES, POE2_NEW_ITEM_TYPES,
    PSEUDO_STAT_RULES,
    # Functions
    calculate_goodness_score, get_roll_quality_label,
    calculate_filter_range,
    calculate_stat_differential, prioritize_mods_by_differential,
    calculate_pseudo_stat, calculate_all_pseudo_stats,
    get_rune_by_name, get_runes_for_slot, get_runes_by_tier,
    get_charm_mods_by_group,
    is_poe2_item_type, is_poe2_exclusive_type,
)


class TestRuneTier:
    """Tests for RuneTier enum."""

    def test_tier_values(self):
        """Test that tier values are correct."""
        assert RuneTier.LESSER.value == 0
        assert RuneTier.NORMAL.value == 15
        assert RuneTier.GREATER.value == 30
        assert RuneTier.HERITAGE.value == 50
        assert RuneTier.SOUL_CORE.value == 50


class TestModifierType:
    """Tests for ModifierType enum."""

    def test_all_types_present(self):
        """Test that all modifier types exist."""
        expected = ["pseudo", "explicit", "implicit", "crafted",
                   "enchant", "rune", "fractured", "corrupted", "sanctum"]
        for mod_type in expected:
            assert ModifierType(mod_type)


class TestDamageType:
    """Tests for DamageType enum."""

    def test_all_damage_types(self):
        """Test that all damage types exist."""
        expected = ["physical", "fire", "cold", "lightning", "chaos"]
        for dmg_type in expected:
            assert DamageType(dmg_type)


class TestRuneData:
    """Tests for POE2_RUNES data."""

    def test_rune_count(self):
        """Test that we have rune data."""
        assert len(POE2_RUNES) >= 25  # We have at least 25 runes

    def test_rune_structure(self):
        """Test that runes have required fields."""
        for name, rune in POE2_RUNES.items():
            assert rune.name == name
            assert isinstance(rune.tier, RuneTier)
            assert rune.stat
            assert rune.value
            assert len(rune.slots) > 0

    def test_elemental_rune_tiers(self):
        """Test that elemental runes have all tiers."""
        # Desert (Fire) runes
        assert "Lesser Desert Rune" in POE2_RUNES
        assert "Desert Rune" in POE2_RUNES
        assert "Greater Desert Rune" in POE2_RUNES

        # Glacial (Cold) runes
        assert "Lesser Glacial Rune" in POE2_RUNES
        assert "Glacial Rune" in POE2_RUNES
        assert "Greater Glacial Rune" in POE2_RUNES

        # Storm (Lightning) runes
        assert "Lesser Storm Rune" in POE2_RUNES
        assert "Storm Rune" in POE2_RUNES
        assert "Greater Storm Rune" in POE2_RUNES

    def test_defense_runes(self):
        """Test defense runes exist."""
        assert "Lesser Iron Rune" in POE2_RUNES
        assert "Iron Rune" in POE2_RUNES
        assert "Greater Iron Rune" in POE2_RUNES

    def test_life_mana_runes(self):
        """Test life/mana runes exist."""
        assert "Lesser Body Rune" in POE2_RUNES
        assert "Body Rune" in POE2_RUNES
        assert "Greater Body Rune" in POE2_RUNES
        assert "Lesser Mind Rune" in POE2_RUNES
        assert "Mind Rune" in POE2_RUNES
        assert "Greater Mind Rune" in POE2_RUNES

    def test_movement_runes(self):
        """Test movement speed runes exist."""
        assert "Lesser Stone Rune" in POE2_RUNES
        assert "Stone Rune" in POE2_RUNES
        assert "Greater Stone Rune" in POE2_RUNES
        # Movement runes should only work on boots
        stone = POE2_RUNES["Stone Rune"]
        assert "boots" in stone.slots
        assert len(stone.slots) == 1

    def test_heritage_runes(self):
        """Test heritage (legendary) runes exist."""
        heritage_runes = [r for r in POE2_RUNES.values() if r.tier == RuneTier.HERITAGE]
        assert len(heritage_runes) >= 3

    def test_soul_cores(self):
        """Test soul cores exist."""
        soul_cores = [r for r in POE2_RUNES.values() if r.tier == RuneTier.SOUL_CORE]
        assert len(soul_cores) >= 3


class TestRuneLookups:
    """Tests for rune lookup functions."""

    def test_get_rune_by_name(self):
        """Test getting rune by name."""
        rune = get_rune_by_name("Desert Rune")
        assert rune is not None
        assert rune.name == "Desert Rune"
        assert rune.tier == RuneTier.NORMAL

    def test_get_rune_by_name_not_found(self):
        """Test getting non-existent rune."""
        rune = get_rune_by_name("Nonexistent Rune")
        assert rune is None

    def test_get_runes_for_slot(self):
        """Test getting runes for a slot."""
        boot_runes = get_runes_for_slot("boots")
        assert len(boot_runes) >= 3  # At least stone runes
        for rune in boot_runes:
            assert "boots" in rune.slots

    def test_get_runes_by_tier(self):
        """Test getting runes by tier."""
        lesser_runes = get_runes_by_tier(RuneTier.LESSER)
        assert len(lesser_runes) >= 5
        for rune in lesser_runes:
            assert rune.tier == RuneTier.LESSER


class TestCharmModData:
    """Tests for POE2_CHARM_MODS data."""

    def test_charm_mod_count(self):
        """Test that we have charm mod data."""
        assert len(POE2_CHARM_MODS) >= 9

    def test_charm_mod_structure(self):
        """Test that charm mods have required fields."""
        for mod in POE2_CHARM_MODS:
            assert mod.affix
            assert mod.stat
            assert mod.tier >= 1
            assert mod.min_value <= mod.max_value
            assert mod.level_req >= 1
            assert mod.group

    def test_charm_mod_tiers(self):
        """Test that charm mods have proper tier progression."""
        duration_mods = get_charm_mods_by_group("CharmIncreasedDuration")
        assert len(duration_mods) == 3

        # Check tier progression
        tier_values = [(m.tier, m.min_value) for m in duration_mods]
        tier_values.sort(key=lambda x: x[0])
        # Higher tiers should have higher values
        assert tier_values[0][1] < tier_values[1][1] < tier_values[2][1]

    def test_get_charm_mods_by_group(self):
        """Test getting charm mods by group."""
        life_mods = get_charm_mods_by_group("CharmLifeRecovery")
        assert len(life_mods) == 3
        for mod in life_mods:
            assert mod.group == "CharmLifeRecovery"


class TestItemTypes:
    """Tests for item type data."""

    def test_item_types_complete(self):
        """Test that all expected item types exist."""
        expected = [
            "helmet", "body_armour", "gloves", "boots", "shield",
            "amulet", "ring", "belt", "quiver",
            "sword", "axe", "mace", "dagger", "wand", "sceptre",
            "bow", "staff",
        ]
        for item_type in expected:
            assert item_type in POE2_ITEM_TYPES

    def test_poe2_new_types(self):
        """Test PoE2-exclusive item types."""
        new_types = ["focus", "crossbow", "flail", "spear", "warstaff", "charm"]
        for item_type in new_types:
            assert item_type in POE2_NEW_ITEM_TYPES
            assert item_type in POE2_ITEM_TYPES

    def test_is_poe2_item_type(self):
        """Test item type checking."""
        assert is_poe2_item_type("helmet") is True
        assert is_poe2_item_type("focus") is True
        assert is_poe2_item_type("invalid_type") is False

    def test_is_poe2_exclusive_type(self):
        """Test PoE2-exclusive type checking."""
        assert is_poe2_exclusive_type("focus") is True
        assert is_poe2_exclusive_type("helmet") is False


class TestGoodnessScore:
    """Tests for goodness score calculations."""

    def test_perfect_roll(self):
        """Test max value returns 1.0."""
        score = calculate_goodness_score(100, 80, 100)
        assert score == 1.0

    def test_minimum_roll(self):
        """Test min value returns 0.0."""
        score = calculate_goodness_score(80, 80, 100)
        assert score == 0.0

    def test_middle_roll(self):
        """Test middle value returns 0.5."""
        score = calculate_goodness_score(90, 80, 100)
        assert score == 0.5

    def test_fixed_value(self):
        """Test fixed value (min == max) returns 1.0."""
        score = calculate_goodness_score(35, 35, 35)
        assert score == 1.0

    def test_above_max(self):
        """Test value above max returns 1.0."""
        score = calculate_goodness_score(110, 80, 100)
        assert score == 1.0

    def test_below_min(self):
        """Test value below min returns 0.0."""
        score = calculate_goodness_score(70, 80, 100)
        assert score == 0.0


class TestRollQualityLabel:
    """Tests for roll quality label function."""

    def test_perfect_label(self):
        """Test perfect roll label."""
        assert get_roll_quality_label(0.95) == "Perfect"
        assert get_roll_quality_label(1.0) == "Perfect"

    def test_excellent_label(self):
        """Test excellent roll label."""
        assert get_roll_quality_label(0.80) == "Excellent"
        assert get_roll_quality_label(0.90) == "Excellent"

    def test_good_label(self):
        """Test good roll label."""
        assert get_roll_quality_label(0.60) == "Good"
        assert get_roll_quality_label(0.75) == "Good"

    def test_average_label(self):
        """Test average roll label."""
        assert get_roll_quality_label(0.40) == "Average"
        assert get_roll_quality_label(0.55) == "Average"

    def test_below_average_label(self):
        """Test below average label."""
        assert get_roll_quality_label(0.20) == "Below Average"
        assert get_roll_quality_label(0.35) == "Below Average"

    def test_low_label(self):
        """Test low roll label."""
        assert get_roll_quality_label(0.0) == "Low"
        assert get_roll_quality_label(0.15) == "Low"


class TestFilterRange:
    """Tests for filter range calculations."""

    def test_basic_range(self):
        """Test basic filter range calculation."""
        fmin, fmax = calculate_filter_range(90, 80, 100, 0.2)
        assert fmin == 86.0  # 90 - (20 * 0.2)
        assert fmax == 94.0  # 90 + (20 * 0.2)

    def test_clamped_to_min(self):
        """Test filter range clamped to tier minimum."""
        fmin, fmax = calculate_filter_range(82, 80, 100, 0.2)
        assert fmin == 80.0  # Clamped to tier min
        assert fmax == 86.0

    def test_clamped_to_max(self):
        """Test filter range clamped to tier maximum."""
        fmin, fmax = calculate_filter_range(98, 80, 100, 0.2)
        assert fmin == 94.0
        assert fmax == 100.0  # Clamped to tier max

    def test_narrow_variance(self):
        """Test with narrow variance."""
        fmin, fmax = calculate_filter_range(90, 80, 100, 0.1)
        assert fmin == 88.0
        assert fmax == 92.0


class TestStatDifferential:
    """Tests for stat differential calculations."""

    def test_basic_differential(self):
        """Test basic stat differential."""
        diff = calculate_stat_differential(100, 150, 1.0)
        assert diff == 50.0

    def test_weighted_differential(self):
        """Test weighted stat differential."""
        diff = calculate_stat_differential(100, 150, 2.0)
        assert diff == 100.0

    def test_negative_differential(self):
        """Test negative differential (stat decrease)."""
        diff = calculate_stat_differential(150, 100, 1.0)
        assert diff == -50.0

    def test_zero_differential(self):
        """Test zero differential."""
        diff = calculate_stat_differential(100, 100, 1.0)
        assert diff == 0.0


class TestPrioritizeMods:
    """Tests for mod prioritization."""

    def test_prioritize_by_differential(self):
        """Test mods are sorted by differential magnitude."""
        diffs = {
            "mod_a": 10.0,
            "mod_b": 50.0,
            "mod_c": -30.0,
            "mod_d": 5.0,
        }
        result = prioritize_mods_by_differential(diffs)
        assert result[0] == "mod_b"  # Highest absolute
        assert result[1] == "mod_c"  # Second highest absolute
        assert result[2] == "mod_a"
        assert result[3] == "mod_d"

    def test_max_filters_limit(self):
        """Test max filter limit is applied."""
        diffs = {f"mod_{i}": float(i) for i in range(50)}
        result = prioritize_mods_by_differential(diffs, max_filters=10)
        assert len(result) == 10

    def test_empty_input(self):
        """Test empty input returns empty list."""
        result = prioritize_mods_by_differential({})
        assert result == []


class TestPseudoStatRules:
    """Tests for pseudo stat aggregation rules."""

    def test_rules_exist(self):
        """Test that pseudo stat rules exist."""
        assert len(PSEUDO_STAT_RULES) >= 10

    def test_resistance_rule(self):
        """Test elemental resistance rule."""
        rule = next(r for r in PSEUDO_STAT_RULES
                   if r.pseudo_stat == "pseudo_total_elemental_resistance")
        assert len(rule.sources) >= 4

    def test_life_rule_has_strength(self):
        """Test life rule includes strength contribution."""
        rule = next(r for r in PSEUDO_STAT_RULES
                   if r.pseudo_stat == "pseudo_total_life")
        sources = dict(rule.sources)
        assert "to Strength" in sources
        assert sources["to Strength"] == 0.5  # 2 Str = 1 Life


class TestPseudoStatCalculation:
    """Tests for pseudo stat calculation."""

    def test_calculate_elemental_resistance(self):
        """Test elemental resistance pseudo calculation."""
        mods = {
            "+45% to Fire Resistance": 45,
            "+40% to Cold Resistance": 40,
            "+35% to Lightning Resistance": 35,
        }
        result = calculate_all_pseudo_stats(mods)
        assert "pseudo_total_elemental_resistance" in result
        assert result["pseudo_total_elemental_resistance"] == 120  # 45 + 40 + 35

    def test_calculate_all_ele_res_multiplier(self):
        """Test all elemental resistance counts 3x."""
        mods = {
            "+10% to all Elemental Resistances": 10,
        }
        result = calculate_all_pseudo_stats(mods)
        assert result["pseudo_total_elemental_resistance"] == 30  # 10 * 3

    def test_calculate_life_with_strength(self):
        """Test life includes strength contribution."""
        mods = {
            "+80 to maximum Life": 80,
            "+40 to Strength": 40,
        }
        result = calculate_all_pseudo_stats(mods)
        assert "pseudo_total_life" in result
        assert result["pseudo_total_life"] == 100  # 80 + (40 * 0.5)

    def test_calculate_life_requires_base(self):
        """Test life calculation requires base life mod."""
        mods = {
            "+40 to Strength": 40,  # Only strength, no life
        }
        rule = next(r for r in PSEUDO_STAT_RULES
                   if r.pseudo_stat == "pseudo_total_life")
        result = calculate_pseudo_stat(rule, mods)
        assert result is None  # Requires "to maximum Life"

    def test_calculate_attributes(self):
        """Test attribute pseudo calculations."""
        mods = {
            "+30 to Strength": 30,
            "+20 to Dexterity": 20,
            "+10 to Intelligence": 10,
            "+5 to all Attributes": 5,
        }
        result = calculate_all_pseudo_stats(mods)

        assert result["pseudo_total_strength"] == 35  # 30 + 5
        assert result["pseudo_total_dexterity"] == 25  # 20 + 5
        assert result["pseudo_total_intelligence"] == 15  # 10 + 5
        # Total: (30+20+10) + (5*3)
        assert result["pseudo_total_all_attributes"] == 75

    def test_calculate_empty_mods(self):
        """Test with no mods returns empty dict."""
        result = calculate_all_pseudo_stats({})
        assert result == {}


class TestPseudoStatRule:
    """Tests for PseudoRule dataclass."""

    def test_rule_structure(self):
        """Test PseudoRule has correct structure."""
        rule = PseudoRule(
            pseudo_stat="test_stat",
            sources=[("test mod", 1.0), ("other mod", 2.0)],
            requires="test mod"
        )
        assert rule.pseudo_stat == "test_stat"
        assert len(rule.sources) == 2
        assert rule.requires == "test mod"

    def test_rule_without_requires(self):
        """Test PseudoRule without requirements."""
        rule = PseudoRule(
            pseudo_stat="test_stat",
            sources=[("test mod", 1.0)],
        )
        assert rule.requires is None


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_item_analysis(self):
        """Test analyzing a complete item."""
        # Simulate an item with multiple mods
        item_mods = {
            "+95 to maximum Life": 95,
            "+42% to Fire Resistance": 42,
            "+38% to Cold Resistance": 38,
            "+35% to Lightning Resistance": 35,
            "+25 to Strength": 25,
        }

        # Calculate pseudo stats
        pseudo = calculate_all_pseudo_stats(item_mods)

        # Verify life includes strength bonus
        assert pseudo["pseudo_total_life"] == 107.5  # 95 + (25 * 0.5)

        # Verify resistance total
        assert pseudo["pseudo_total_elemental_resistance"] == 115  # 42+38+35

        # Calculate goodness for life roll (assume T2: 90-99)
        life_goodness = calculate_goodness_score(95, 90, 99)
        assert 0.5 < life_goodness < 0.6  # Should be around 0.55

        # Get quality label
        label = get_roll_quality_label(life_goodness)
        assert label == "Average"

    def test_trade_filter_workflow(self):
        """Test creating trade filters from item analysis."""
        # Item has a life roll
        life_value = 95
        tier_min, tier_max = 90, 99

        # Calculate goodness
        goodness = calculate_goodness_score(life_value, tier_min, tier_max)

        # Calculate filter range (20% variance)
        filter_min, filter_max = calculate_filter_range(
            life_value, tier_min, tier_max, 0.2
        )

        # Verify reasonable filter values
        assert filter_min >= tier_min
        assert filter_max <= tier_max
        assert filter_min < life_value < filter_max

    def test_rune_selection_for_build(self):
        """Test selecting runes for a build slot."""
        # Get all runes for boots
        boot_runes = get_runes_for_slot("boots")

        # Find movement speed runes
        ms_runes = [r for r in boot_runes if "Movement Speed" in r.stat]
        assert len(ms_runes) >= 3

        # Verify tier progression
        tiers = {r.tier: r for r in ms_runes}
        assert RuneTier.LESSER in tiers
        assert RuneTier.NORMAL in tiers
        assert RuneTier.GREATER in tiers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
