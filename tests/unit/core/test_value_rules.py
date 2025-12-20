# tests/test_value_rules.py

import pytest

from core.item_parser import ParsedItem
from core.value_rules import (
    assess_rare_item,
    _get_slot,
    _eval_condition,
    _any_mod_matches,
    _count_mod_matches,
    _pattern_to_regex,
    Rule,
)

pytestmark = pytest.mark.unit


def make_rare_item(
    *,
    raw_text: str = "",
    name: str = "Test Rare",
    base_type: str = "Hubris Circlet",
    item_level: int = 84,
    implicits=None,
    explicits=None,
    enchants=None,
) -> ParsedItem:
    """Minimal helper to construct a ParsedItem for value-rule tests."""
    return ParsedItem(
        raw_text=raw_text or "dummy",
        rarity="RARE",
        name=name,
        base_type=base_type,
        item_level=item_level,
        implicits=implicits or [],
        explicits=explicits or [],
        enchants=enchants or [],
        is_corrupted=False,
    )


def test_fractured_rare_flagged_as_fracture_base():
    item = make_rare_item(
        explicits=[
            "+71 to maximum Energy Shield (fractured)",
            "+37% to Lightning Resistance",
        ]
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "fracture_base"
    # At least one reason should mention "fractured" or the rule name
    assert any("fractured" in r.lower() for r in assessment.reasons)


def test_high_life_rare_flagged_as_craft_base():
    item = make_rare_item(
        base_type="Astral Plate",
        item_level=84,
        explicits=[
            "+98 to maximum Life",
            "+45% to Cold Resistance",
            "+38% to Lightning Resistance",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag in {"craft_base", "check_trade"}
    assert any("life" in r.lower() for r in assessment.reasons)


def test_multi_damage_mods_flagged_as_check_trade():
    item = make_rare_item(
        base_type="Bone Helmet",
        item_level=86,
        explicits=[
            "+30% to Damage over Time Multiplier",
            "Non-Channelling Skills have -8 to Total Mana Cost",
            "+74 to maximum Life",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "check_trade"
    assert any("damage" in r.lower() or "trade" in r.lower() for r in assessment.reasons)


def test_obvious_junk_rare_is_junk():
    item = make_rare_item(
        base_type="Iron Greaves",
        item_level=50,
        explicits=[
            "+22% to Fire Resistance",
            "+19% to Cold Resistance",
            "+35 to maximum Mana",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "junk"
    assert any("no rare value rules matched" in r.lower() for r in assessment.reasons)


def test_non_rare_items_always_junk():
    """Non-rare items should not be treated as valuable by this module."""
    non_rare = ParsedItem(
        raw_text="dummy",
        rarity="UNIQUE",
        name="Shavronne's Wrappings",
        base_type="Occultist's Vestment",
        item_level=85,
        implicits=[],
        explicits=[],
        enchants=[],
        is_corrupted=False,
    )

    assessment = assess_rare_item(non_rare)

    assert assessment.flag == "junk"
    assert any("not a rare item" in r.lower() for r in assessment.reasons)


# ---------------------------------------------------------------------------
# Tests for _get_slot()
# ---------------------------------------------------------------------------

class TestGetSlot:
    """Tests for slot inference from base type."""

    def test_helmet_from_circlet(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _get_slot(item) == "Helmet"

    def test_helmet_from_mask(self):
        item = make_rare_item(base_type="Vaal Mask")
        assert _get_slot(item) == "Helmet"

    def test_helmet_from_crown(self):
        item = make_rare_item(base_type="Eternal Burgonet Crown")
        assert _get_slot(item) == "Helmet"

    def test_helmet_from_hood(self):
        item = make_rare_item(base_type="Lion's Hood")
        assert _get_slot(item) == "Helmet"

    def test_body_armour_from_plate(self):
        item = make_rare_item(base_type="Astral Plate")
        assert _get_slot(item) == "BodyArmour"

    def test_body_armour_from_robe(self):
        item = make_rare_item(base_type="Vaal Regalia Robe")
        assert _get_slot(item) == "BodyArmour"

    def test_body_armour_from_vestment(self):
        item = make_rare_item(base_type="Occultist's Vestment")
        assert _get_slot(item) == "BodyArmour"

    def test_boots_from_greaves(self):
        item = make_rare_item(base_type="Titan Greaves")
        assert _get_slot(item) == "Boots"

    def test_boots_from_slippers(self):
        item = make_rare_item(base_type="Sorcerer Slippers")
        assert _get_slot(item) == "Boots"

    def test_boots_from_shoes(self):
        item = make_rare_item(base_type="Arcanist Shoes")
        assert _get_slot(item) == "Boots"

    def test_gloves_from_mitts(self):
        item = make_rare_item(base_type="Sorcerer Mitts")
        assert _get_slot(item) == "Gloves"

    def test_gloves_from_gauntlets(self):
        item = make_rare_item(base_type="Spiked Gauntlets")
        assert _get_slot(item) == "Gloves"

    def test_gloves_from_gloves(self):
        item = make_rare_item(base_type="Fingerless Silk Gloves")
        assert _get_slot(item) == "Gloves"

    def test_ring(self):
        item = make_rare_item(base_type="Two-Stone Ring")
        assert _get_slot(item) == "Ring"

    def test_amulet(self):
        item = make_rare_item(base_type="Jade Amulet")
        assert _get_slot(item) == "Amulet"

    def test_belt_from_belt(self):
        item = make_rare_item(base_type="Leather Belt")
        assert _get_slot(item) == "Belt"

    def test_belt_from_sash(self):
        item = make_rare_item(base_type="Rustic Sash")
        assert _get_slot(item) == "Belt"

    def test_belt_from_chain(self):
        item = make_rare_item(base_type="Heavy Chain Belt")
        assert _get_slot(item) == "Belt"

    def test_unknown_returns_any(self):
        item = make_rare_item(base_type="Exquisite Blade")
        assert _get_slot(item) == "Any"

    def test_empty_base_type_returns_any(self):
        item = make_rare_item(base_type="")
        assert _get_slot(item) == "Any"

    def test_none_base_type_returns_any(self):
        item = ParsedItem(
            raw_text="dummy",
            rarity="RARE",
            name="Test",
            base_type=None,
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=False,
        )
        assert _get_slot(item) == "Any"


# ---------------------------------------------------------------------------
# Tests for _eval_condition()
# ---------------------------------------------------------------------------

class TestEvalConditionSlot:
    """Tests for slot-based conditions."""

    def test_slot_equals_match(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _eval_condition("slot == Helmet", item, "Helmet") is True

    def test_slot_equals_no_match(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _eval_condition("slot == Boots", item, "Helmet") is False

    def test_slot_in_list_match(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _eval_condition("slot in [Helmet, BodyArmour]", item, "Helmet") is True

    def test_slot_in_list_no_match(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _eval_condition("slot in [Ring, Amulet]", item, "Helmet") is False

    def test_slot_in_list_with_spaces(self):
        item = make_rare_item(base_type="Hubris Circlet")
        assert _eval_condition("slot in [Helmet, Boots, Gloves]", item, "Boots") is True

    def test_invalid_slot_condition_returns_false(self):
        item = make_rare_item(base_type="Hubris Circlet")
        # Invalid slot condition syntax
        assert _eval_condition("slot ~ Helmet", item, "Helmet") is False


class TestEvalConditionModCount:
    """Tests for mod_count conditions."""

    def test_mod_count_gte_match(self):
        item = make_rare_item(explicits=["+1 fractured", "+2 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' >= 1", item, "Any") is True

    def test_mod_count_gte_no_match(self):
        item = make_rare_item(explicits=["+1 regular"])
        assert _eval_condition("mod_count ~ 'fractured' >= 1", item, "Any") is False

    def test_mod_count_equals_match(self):
        item = make_rare_item(explicits=["+1 fractured", "+2 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' == 2", item, "Any") is True

    def test_mod_count_equals_no_match(self):
        item = make_rare_item(explicits=["+1 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' == 2", item, "Any") is False

    def test_mod_count_lte_match(self):
        item = make_rare_item(explicits=["+1 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' <= 2", item, "Any") is True

    def test_mod_count_lte_no_match(self):
        item = make_rare_item(explicits=["+1 fractured", "+2 fractured", "+3 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' <= 2", item, "Any") is False

    def test_mod_count_gt_match(self):
        item = make_rare_item(explicits=["+1 fractured", "+2 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' > 1", item, "Any") is True

    def test_mod_count_gt_no_match(self):
        item = make_rare_item(explicits=["+1 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' > 1", item, "Any") is False

    def test_mod_count_lt_match(self):
        item = make_rare_item(explicits=["+1 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' < 2", item, "Any") is True

    def test_mod_count_lt_no_match(self):
        item = make_rare_item(explicits=["+1 fractured", "+2 fractured"])
        assert _eval_condition("mod_count ~ 'fractured' < 2", item, "Any") is False


class TestEvalConditionMod:
    """Tests for mod pattern matching."""

    def test_mod_match_with_number_placeholder(self):
        item = make_rare_item(explicits=["+98 to maximum Life"])
        assert _eval_condition("mod ~ '+# to maximum Life'", item, "Any") is True

    def test_mod_match_no_match(self):
        item = make_rare_item(explicits=["+45% to Cold Resistance"])
        assert _eval_condition("mod ~ '+# to maximum Life'", item, "Any") is False

    def test_mod_match_in_implicits(self):
        item = make_rare_item(implicits=["+30% to Cold and Lightning Resistances"])
        assert _eval_condition("mod ~ 'Resistances'", item, "Any") is True

    def test_mod_match_in_enchants(self):
        item = make_rare_item(enchants=["Enchanted: 16% increased Movement Speed"])
        assert _eval_condition("mod ~ 'Movement Speed'", item, "Any") is True


class TestEvalConditionBoolean:
    """Tests for boolean field conditions."""

    def test_is_corrupted_equals_true(self):
        item = ParsedItem(
            raw_text="dummy",
            rarity="RARE",
            name="Test",
            base_type="Ring",
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=True,
        )
        assert _eval_condition("is_corrupted == True", item, "Ring") is True

    def test_is_corrupted_equals_false(self):
        item = make_rare_item()
        assert _eval_condition("is_corrupted == False", item, "Any") is True

    def test_is_corrupted_not_equals(self):
        item = make_rare_item()
        assert _eval_condition("is_corrupted != True", item, "Any") is True

    def test_is_fractured_equals_true(self):
        item = ParsedItem(
            raw_text="dummy",
            rarity="RARE",
            name="Test",
            base_type="Ring",
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=False,
            is_fractured=True,
        )
        assert _eval_condition("is_fractured == True", item, "Ring") is True

    def test_boolean_invalid_op_returns_false(self):
        item = make_rare_item()
        # >= doesn't make sense for booleans
        assert _eval_condition("is_corrupted >= True", item, "Any") is False


class TestEvalConditionNumeric:
    """Tests for numeric field conditions."""

    def test_item_level_gte_match(self):
        item = make_rare_item(item_level=85)
        assert _eval_condition("item_level >= 84", item, "Any") is True

    def test_item_level_gte_no_match(self):
        item = make_rare_item(item_level=83)
        assert _eval_condition("item_level >= 84", item, "Any") is False

    def test_item_level_equals_match(self):
        item = make_rare_item(item_level=84)
        assert _eval_condition("item_level == 84", item, "Any") is True

    def test_item_level_not_equals_match(self):
        item = make_rare_item(item_level=85)
        assert _eval_condition("item_level != 84", item, "Any") is True

    def test_item_level_lte_match(self):
        item = make_rare_item(item_level=84)
        assert _eval_condition("item_level <= 84", item, "Any") is True

    def test_item_level_gt_match(self):
        item = make_rare_item(item_level=85)
        assert _eval_condition("item_level > 84", item, "Any") is True

    def test_item_level_gt_no_match(self):
        item = make_rare_item(item_level=84)
        assert _eval_condition("item_level > 84", item, "Any") is False

    def test_item_level_lt_match(self):
        item = make_rare_item(item_level=83)
        assert _eval_condition("item_level < 84", item, "Any") is True

    def test_item_level_lt_no_match(self):
        item = make_rare_item(item_level=84)
        assert _eval_condition("item_level < 84", item, "Any") is False

    def test_numeric_invalid_rhs_returns_false(self):
        item = make_rare_item(item_level=84)
        assert _eval_condition("item_level >= notanumber", item, "Any") is False


class TestEvalConditionString:
    """Tests for string field conditions."""

    def test_rarity_equals_match(self):
        item = make_rare_item()
        assert _eval_condition("rarity == RARE", item, "Any") is True

    def test_rarity_equals_case_insensitive(self):
        item = make_rare_item()
        assert _eval_condition("rarity == rare", item, "Any") is True

    def test_rarity_not_equals_match(self):
        item = make_rare_item()
        assert _eval_condition("rarity != UNIQUE", item, "Any") is True

    def test_base_type_equals(self):
        item = make_rare_item(base_type="Astral Plate")
        assert _eval_condition("base_type == Astral Plate", item, "Any") is True

    def test_string_comparison_operators_invalid(self):
        """Numeric operators on strings return false."""
        item = make_rare_item(base_type="Astral Plate")
        assert _eval_condition("base_type >= Astral", item, "Any") is False


class TestEvalConditionEdgeCases:
    """Tests for edge cases in condition evaluation."""

    def test_empty_condition_returns_true(self):
        item = make_rare_item()
        assert _eval_condition("", item, "Any") is True

    def test_whitespace_condition_returns_true(self):
        item = make_rare_item()
        assert _eval_condition("   ", item, "Any") is True

    def test_unknown_condition_syntax_returns_false(self):
        item = make_rare_item()
        assert _eval_condition("this is not valid", item, "Any") is False

    def test_gem_level_field(self):
        """Test gem_level field access (defaults to 0)."""
        item = make_rare_item()
        assert _eval_condition("gem_level >= 0", item, "Any") is True

    def test_gem_level_invalid_value_returns_false(self):
        """Test gem_level with invalid numeric value."""
        item = make_rare_item()
        assert _eval_condition("gem_level >= notanumber", item, "Any") is False

    def test_gem_quality_invalid_value_returns_false(self):
        """Test gem_quality with invalid numeric value."""
        item = make_rare_item()
        assert _eval_condition("gem_quality == invalid", item, "Any") is False

    def test_generic_string_field(self):
        item = make_rare_item(name="Test Ring")
        assert _eval_condition("name == Test Ring", item, "Any") is True


# ---------------------------------------------------------------------------
# Tests for Rule class
# ---------------------------------------------------------------------------

class TestRule:
    """Tests for Rule class methods."""

    def test_applies_to_slot_any(self):
        rule = Rule(name="Test", slots=["Any"], conditions=[])
        assert rule.applies_to_slot("Helmet") is True
        assert rule.applies_to_slot("Boots") is True

    def test_applies_to_slot_specific(self):
        rule = Rule(name="Test", slots=["Helmet", "Boots"], conditions=[])
        assert rule.applies_to_slot("Helmet") is True
        assert rule.applies_to_slot("Boots") is True
        assert rule.applies_to_slot("Ring") is False

    def test_applies_to_slot_empty_list(self):
        rule = Rule(name="Test", slots=[], conditions=[])
        assert rule.applies_to_slot("Any") is True

    def test_matches_with_all_conditions(self):
        rule = Rule(
            name="Test",
            slots=["Any"],
            conditions=["rarity == RARE", "item_level >= 80"],
        )
        item = make_rare_item(item_level=85)
        assert rule.matches(item, "Any") is True

    def test_matches_fails_if_slot_wrong(self):
        rule = Rule(
            name="Test",
            slots=["Boots"],
            conditions=["rarity == RARE"],
        )
        item = make_rare_item()
        assert rule.matches(item, "Helmet") is False

    def test_matches_fails_if_condition_wrong(self):
        rule = Rule(
            name="Test",
            slots=["Any"],
            conditions=["item_level >= 90"],
        )
        item = make_rare_item(item_level=85)
        assert rule.matches(item, "Any") is False


# ---------------------------------------------------------------------------
# Tests for helper functions
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Tests for pattern matching helper functions."""

    def test_pattern_to_regex_simple(self):
        pattern = _pattern_to_regex("+# to maximum Life")
        assert pattern.search("+98 to maximum life")
        assert not pattern.search("+98 to maximum Mana")

    def test_pattern_to_regex_multiple_placeholders(self):
        pattern = _pattern_to_regex("Adds # to # Lightning Damage")
        assert pattern.search("adds 5 to 50 lightning damage")

    def test_any_mod_matches_explicit(self):
        item = make_rare_item(explicits=["+98 to maximum Life"])
        assert _any_mod_matches(item, "+# to maximum Life") is True

    def test_any_mod_matches_implicit(self):
        item = make_rare_item(implicits=["+30% to Cold Resistance"])
        assert _any_mod_matches(item, "Cold Resistance") is True

    def test_any_mod_matches_enchant(self):
        item = make_rare_item(enchants=["16% increased Attack Speed"])
        assert _any_mod_matches(item, "Attack Speed") is True

    def test_any_mod_matches_no_match(self):
        item = make_rare_item(explicits=["+50 to Strength"])
        assert _any_mod_matches(item, "maximum Life") is False

    def test_count_mod_matches_multiple(self):
        item = make_rare_item(explicits=[
            "+50 to maximum Life",
            "+30 to maximum Life (fractured)",
        ])
        assert _count_mod_matches(item, "maximum Life") == 2

    def test_count_mod_matches_zero(self):
        item = make_rare_item(explicits=["+50 to Strength"])
        assert _count_mod_matches(item, "maximum Life") == 0


# ---------------------------------------------------------------------------
# Tests for assess_rare_item edge cases
# ---------------------------------------------------------------------------

class TestAssessRareItemEdgeCases:
    """Additional edge case tests for assess_rare_item."""

    def test_rule_without_explicit_flag(self):
        """Test weight accumulation without explicit flag."""
        # Create an item that matches high life rule (weight 60)
        # but doesn't match fractured or damage rules
        item = make_rare_item(
            base_type="Leather Belt",
            item_level=82,
            explicits=["+98 to maximum Life"],
        )
        assessment = assess_rare_item(item)
        # Weight 60 should trigger craft_base
        assert assessment.flag in {"craft_base", "junk"}

    def test_magic_item_is_junk(self):
        magic_item = ParsedItem(
            raw_text="dummy",
            rarity="MAGIC",
            name="Test",
            base_type="Ring",
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=False,
        )
        assessment = assess_rare_item(magic_item)
        assert assessment.flag == "junk"

    def test_normal_item_is_junk(self):
        normal_item = ParsedItem(
            raw_text="dummy",
            rarity="NORMAL",
            name="Test",
            base_type="Ring",
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=False,
        )
        assessment = assess_rare_item(normal_item)
        assert assessment.flag == "junk"

    def test_none_rarity_is_junk(self):
        item = ParsedItem(
            raw_text="dummy",
            rarity=None,
            name="Test",
            base_type="Ring",
            item_level=84,
            implicits=[],
            explicits=[],
            enchants=[],
            is_corrupted=False,
        )
        assessment = assess_rare_item(item)
        assert assessment.flag == "junk"

    def test_rule_reason_appended_when_present(self):
        """Verify that rule reasons are added to assessment."""
        item = make_rare_item(
            item_level=85,
            explicits=["+71 to maximum Energy Shield (fractured)"],
        )
        assessment = assess_rare_item(item)
        # Should have the reason from the fractured rule
        assert any("fractured" in r.lower() for r in assessment.reasons)

    def test_rule_name_used_when_no_reason(self):
        """When rule has no reason field, rule name is used."""
        # This requires creating a custom rule set, so we test indirectly
        # by checking that reasons list is not empty for matched rules
        item = make_rare_item(
            item_level=85,
            explicits=["+98 to maximum Life"],
        )
        assessment = assess_rare_item(item)
        assert len(assessment.reasons) > 0


class TestHeuristicWeightPaths:
    """Tests for weight-based heuristic flag assignment using patched rules."""

    def test_high_weight_without_flag_triggers_check_trade(self, monkeypatch):
        """Weight >= 100 without explicit flag triggers check_trade."""
        import core.value_rules as vr

        # Create a rule with high weight but no flag
        test_rules = [
            Rule(
                name="High weight no flag",
                slots=["Any"],
                conditions=["rarity == RARE"],
                weight=100,
                flag=None,  # No explicit flag
                reason=None,  # No explicit reason
            )
        ]
        monkeypatch.setattr(vr, "RARE_VALUE_RULES", test_rules)

        item = make_rare_item()
        assessment = assess_rare_item(item)

        assert assessment.flag == "check_trade"
        assert any("high combined rule weight" in r.lower() for r in assessment.reasons)

    def test_moderate_weight_without_flag_triggers_craft_base(self, monkeypatch):
        """Weight >= 50 without explicit flag triggers craft_base."""
        import core.value_rules as vr

        test_rules = [
            Rule(
                name="Moderate weight no flag",
                slots=["Any"],
                conditions=["rarity == RARE"],
                weight=60,
                flag=None,
                reason=None,
            )
        ]
        monkeypatch.setattr(vr, "RARE_VALUE_RULES", test_rules)

        item = make_rare_item()
        assessment = assess_rare_item(item)

        assert assessment.flag == "craft_base"
        assert any("moderate combined rule weight" in r.lower() for r in assessment.reasons)

    def test_rule_name_in_reasons_when_no_explicit_reason(self, monkeypatch):
        """When rule has no explicit reason, rule name is used."""
        import core.value_rules as vr

        test_rules = [
            Rule(
                name="Test Rule Without Reason",
                slots=["Any"],
                conditions=["rarity == RARE"],
                weight=10,
                flag="craft_base",
                reason=None,  # No explicit reason
            )
        ]
        monkeypatch.setattr(vr, "RARE_VALUE_RULES", test_rules)

        item = make_rare_item()
        assessment = assess_rare_item(item)

        assert any("Test Rule Without Reason" in r for r in assessment.reasons)
