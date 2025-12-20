"""Tests for PoE2 trade stat IDs and affix data."""

from unittest.mock import MagicMock

from data_sources.pricing.trade_stat_ids_poe2 import (
    POE2_AFFIX_TO_STAT_ID,
    POE2_AFFIX_TIERS,
    POE2_ITEM_TYPES,
    POE2_SLOT_TO_TYPE,
    POE2_AFFIX_MIN_VALUES,
    POE2_PSEUDO_COMPONENTS,
    get_poe2_stat_id,
    get_poe2_min_value,
    get_max_tier_for_slot,
    build_poe2_stat_filters,
)


class TestPoe2AffixToStatIdMapping:
    """Tests for POE2_AFFIX_TO_STAT_ID mapping."""

    def test_life_stat_id(self):
        """Life maps to pseudo total life."""
        stat_id, is_pseudo = POE2_AFFIX_TO_STAT_ID["life"]
        assert stat_id == "pseudo.pseudo_total_life"
        assert is_pseudo is True

    def test_energy_shield_stat_id(self):
        """Energy shield maps to pseudo."""
        stat_id, is_pseudo = POE2_AFFIX_TO_STAT_ID["energy_shield"]
        assert stat_id == "pseudo.pseudo_total_energy_shield"
        assert is_pseudo is True

    def test_resistance_stat_ids(self):
        """Resistance affixes map correctly."""
        assert "resistances" in POE2_AFFIX_TO_STAT_ID
        assert "fire_resistance" in POE2_AFFIX_TO_STAT_ID
        assert "cold_resistance" in POE2_AFFIX_TO_STAT_ID
        assert "lightning_resistance" in POE2_AFFIX_TO_STAT_ID
        assert "chaos_resistance" in POE2_AFFIX_TO_STAT_ID

    def test_attribute_stat_ids(self):
        """Attribute affixes map to pseudo stats."""
        for attr in ["strength", "dexterity", "intelligence", "all_attributes"]:
            stat_id, is_pseudo = POE2_AFFIX_TO_STAT_ID[attr]
            assert is_pseudo is True
            assert "pseudo" in stat_id

    def test_movement_speed_is_explicit(self):
        """Movement speed is explicit stat, not pseudo."""
        stat_id, is_pseudo = POE2_AFFIX_TO_STAT_ID["movement_speed"]
        assert is_pseudo is False
        assert "explicit" in stat_id

    def test_spirit_is_poe2_specific(self):
        """Spirit stat is PoE2-specific."""
        assert "spirit" in POE2_AFFIX_TO_STAT_ID
        stat_id, is_pseudo = POE2_AFFIX_TO_STAT_ID["spirit"]
        assert "explicit" in stat_id


class TestPoe2AffixTiers:
    """Tests for POE2_AFFIX_TIERS data."""

    def test_life_tier_on_body_armour(self):
        """Body armour has 13 tiers for life."""
        tier_data = POE2_AFFIX_TIERS["+# to maximum Life"]
        assert tier_data["body_armour"] == 13

    def test_life_tier_on_ring(self):
        """Ring has 8 tiers for life."""
        tier_data = POE2_AFFIX_TIERS["+# to maximum Life"]
        assert tier_data["ring"] == 8

    def test_strength_tiers_exist(self):
        """Strength mod has tier data."""
        assert "+# to Strength" in POE2_AFFIX_TIERS
        tier_data = POE2_AFFIX_TIERS["+# to Strength"]
        assert "amulet" in tier_data
        assert "ring" in tier_data

    def test_movement_speed_on_boots(self):
        """Movement speed has tiers on boots."""
        tier_data = POE2_AFFIX_TIERS["#% increased Movement Speed"]
        assert tier_data["boots"] == 6

    def test_resistance_tiers(self):
        """Resistances have tier data."""
        fire_res = POE2_AFFIX_TIERS["+#% to Fire Resistance"]
        assert "ring" in fire_res
        assert fire_res["ring"] == 8


class TestPoe2ItemTypes:
    """Tests for POE2_ITEM_TYPES set."""

    def test_contains_armour_slots(self):
        """Contains all armour slots."""
        for slot in ["helmet", "body_armour", "gloves", "boots", "shield"]:
            assert slot in POE2_ITEM_TYPES

    def test_contains_poe2_specific_types(self):
        """Contains PoE2-specific item types."""
        # Focus is new in PoE2
        assert "focus" in POE2_ITEM_TYPES
        # Flail is new weapon type
        assert "flail" in POE2_ITEM_TYPES
        # Crossbow is new
        assert "crossbow" in POE2_ITEM_TYPES
        # Spear is new
        assert "spear" in POE2_ITEM_TYPES
        # Warstaff is new
        assert "warstaff" in POE2_ITEM_TYPES
        # Trap is new
        assert "trap" in POE2_ITEM_TYPES

    def test_contains_accessories(self):
        """Contains accessory types."""
        for acc in ["amulet", "ring", "belt", "quiver"]:
            assert acc in POE2_ITEM_TYPES


class TestPoe2SlotToType:
    """Tests for POE2_SLOT_TO_TYPE mapping."""

    def test_armour_slot_mappings(self):
        """Armour slots map correctly."""
        assert POE2_SLOT_TO_TYPE["Helmet"] == "helmet"
        assert POE2_SLOT_TO_TYPE["Body Armour"] == "body_armour"
        assert POE2_SLOT_TO_TYPE["Gloves"] == "gloves"
        assert POE2_SLOT_TO_TYPE["Boots"] == "boots"

    def test_ring_slots_map_to_ring(self):
        """Both ring slots map to ring type."""
        assert POE2_SLOT_TO_TYPE["Ring 1"] == "ring"
        assert POE2_SLOT_TO_TYPE["Ring 2"] == "ring"

    def test_focus_slot_mapping(self):
        """Focus slot maps correctly."""
        assert POE2_SLOT_TO_TYPE["Focus"] == "focus"

    def test_weapon_slots_map_to_generic(self):
        """Weapon slots map to one_hand_weapon."""
        assert POE2_SLOT_TO_TYPE["Weapon 1"] == "one_hand_weapon"
        assert POE2_SLOT_TO_TYPE["Weapon 2"] == "one_hand_weapon"


class TestPoe2AffixMinValues:
    """Tests for POE2_AFFIX_MIN_VALUES thresholds."""

    def test_life_minimum(self):
        """Life has appropriate minimum value."""
        assert POE2_AFFIX_MIN_VALUES["life"] == 80

    def test_resistance_minimums(self):
        """Resistances have appropriate minimums."""
        assert POE2_AFFIX_MIN_VALUES["fire_resistance"] == 30
        assert POE2_AFFIX_MIN_VALUES["cold_resistance"] == 30
        assert POE2_AFFIX_MIN_VALUES["lightning_resistance"] == 30
        assert POE2_AFFIX_MIN_VALUES["chaos_resistance"] == 15

    def test_movement_speed_minimum(self):
        """Movement speed has minimum."""
        assert POE2_AFFIX_MIN_VALUES["movement_speed"] == 20

    def test_spirit_minimum_is_poe2_specific(self):
        """Spirit has minimum value."""
        assert POE2_AFFIX_MIN_VALUES["spirit"] == 20


class TestGetPoe2StatId:
    """Tests for get_poe2_stat_id function."""

    def test_valid_affix_type(self):
        """Returns stat ID for valid affix type."""
        result = get_poe2_stat_id("life")
        assert result is not None
        stat_id, is_pseudo = result
        assert stat_id == "pseudo.pseudo_total_life"
        assert is_pseudo is True

    def test_invalid_affix_type(self):
        """Returns None for invalid affix type."""
        result = get_poe2_stat_id("nonexistent_affix")
        assert result is None

    def test_all_mapped_affixes_return_valid(self):
        """All mapped affixes return valid tuples."""
        for affix_type in POE2_AFFIX_TO_STAT_ID.keys():
            result = get_poe2_stat_id(affix_type)
            assert result is not None
            assert len(result) == 2
            stat_id, is_pseudo = result
            assert isinstance(stat_id, str)
            assert isinstance(is_pseudo, bool)


class TestGetPoe2MinValue:
    """Tests for get_poe2_min_value function."""

    def test_with_actual_value(self):
        """Returns 80% of actual value when provided."""
        # 100 * 0.8 = 80
        result = get_poe2_min_value("life", actual_value=100)
        assert result == 80

    def test_with_actual_value_rounds_down(self):
        """Returns integer (truncated) value."""
        # 55 * 0.8 = 44
        result = get_poe2_min_value("life", actual_value=55)
        assert result == 44

    def test_without_actual_value_uses_default(self):
        """Returns default minimum when no actual value."""
        result = get_poe2_min_value("life")
        assert result == POE2_AFFIX_MIN_VALUES["life"]
        assert result == 80

    def test_unknown_affix_without_value_returns_none(self):
        """Returns None for unknown affix without value."""
        result = get_poe2_min_value("unknown_affix")
        assert result is None

    def test_unknown_affix_with_value_uses_value(self):
        """Returns 80% of actual value even for unknown affix."""
        result = get_poe2_min_value("unknown_affix", actual_value=100)
        assert result == 80

    def test_zero_actual_value_uses_default(self):
        """Zero actual value falls back to default."""
        result = get_poe2_min_value("life", actual_value=0)
        assert result == 80

    def test_negative_actual_value_uses_default(self):
        """Negative actual value falls back to default."""
        result = get_poe2_min_value("life", actual_value=-10)
        assert result == 80


class TestGetMaxTierForSlot:
    """Tests for get_max_tier_for_slot function."""

    def test_valid_mod_and_slot(self):
        """Returns max tier for valid mod/slot combination."""
        result = get_max_tier_for_slot("+# to maximum Life", "body_armour")
        assert result == 13

    def test_valid_mod_invalid_slot(self):
        """Returns None for valid mod but invalid slot."""
        result = get_max_tier_for_slot("+# to maximum Life", "weapon")
        assert result is None

    def test_invalid_mod(self):
        """Returns None for invalid mod."""
        result = get_max_tier_for_slot("Nonexistent Mod", "body_armour")
        assert result is None

    def test_ring_life_tier(self):
        """Ring has 8 tiers for life."""
        result = get_max_tier_for_slot("+# to maximum Life", "ring")
        assert result == 8

    def test_boots_movement_speed_tier(self):
        """Boots have 6 tiers for movement speed."""
        result = get_max_tier_for_slot("#% increased Movement Speed", "boots")
        assert result == 6


class TestBuildPoe2StatFilters:
    """Tests for build_poe2_stat_filters function."""

    def test_empty_affixes(self):
        """Returns empty list for no affixes."""
        result = build_poe2_stat_filters([])
        assert result == []

    def test_single_affix(self):
        """Builds filter for single affix."""
        affix = MagicMock()
        affix.affix_type = "life"
        affix.tier = "tier1"
        affix.weight = 100
        affix.value = 90

        result = build_poe2_stat_filters([affix])

        assert len(result) == 1
        assert result[0]["id"] == "pseudo.pseudo_total_life"
        assert "min" in result[0]["value"]

    def test_multiple_affixes(self):
        """Builds filters for multiple affixes."""
        affixes = []
        for affix_type in ["life", "fire_resistance", "strength"]:
            affix = MagicMock()
            affix.affix_type = affix_type
            affix.tier = "tier2"
            affix.weight = 50
            affix.value = 50
            affixes.append(affix)

        result = build_poe2_stat_filters(affixes)

        assert len(result) == 3

    def test_respects_max_filters(self):
        """Respects max_filters limit."""
        affixes = []
        for i, affix_type in enumerate(["life", "fire_resistance", "strength", "dexterity", "intelligence"]):
            affix = MagicMock()
            affix.affix_type = affix_type
            affix.tier = "tier2"
            affix.weight = 50
            affix.value = 50
            affixes.append(affix)

        result = build_poe2_stat_filters(affixes, max_filters=2)

        assert len(result) == 2

    def test_sorts_by_tier(self):
        """Sorts affixes by tier (tier1 first)."""
        affix1 = MagicMock()
        affix1.affix_type = "life"
        affix1.tier = "tier3"
        affix1.weight = 100
        affix1.value = 50

        affix2 = MagicMock()
        affix2.affix_type = "strength"
        affix2.tier = "tier1"
        affix2.weight = 50
        affix2.value = 50

        result = build_poe2_stat_filters([affix1, affix2], max_filters=1)

        # tier1 should be selected first
        assert len(result) == 1
        assert "strength" in result[0]["id"]

    def test_skips_unknown_affix_type(self):
        """Skips affixes with unknown types."""
        affix = MagicMock()
        affix.affix_type = "unknown_type"
        affix.tier = "tier1"
        affix.weight = 100
        affix.value = 50

        result = build_poe2_stat_filters([affix])

        assert result == []

    def test_skips_affix_without_type(self):
        """Skips affixes without affix_type attribute."""
        affix = MagicMock(spec=[])  # No attributes
        affix.affix_type = None

        result = build_poe2_stat_filters([affix])

        assert result == []

    def test_uses_actual_value_for_min(self):
        """Uses 80% of actual value for min filter."""
        affix = MagicMock()
        affix.affix_type = "life"
        affix.tier = "tier1"
        affix.weight = 100
        affix.value = 100  # 80% = 80

        result = build_poe2_stat_filters([affix])

        assert result[0]["value"]["min"] == 80


class TestPoe2PseudoComponents:
    """Tests for POE2_PSEUDO_COMPONENTS mapping."""

    def test_elemental_resistance_components(self):
        """Elemental resistance pseudo has correct components."""
        components = POE2_PSEUDO_COMPONENTS["pseudo_total_elemental_resistance"]
        assert len(components) == 4  # fire, cold, lightning, all ele

    def test_total_resistance_includes_chaos(self):
        """Total resistance includes chaos resistance."""
        components = POE2_PSEUDO_COMPONENTS["pseudo_total_resistance"]
        assert len(components) == 5  # fire, cold, lightning, all ele, chaos

    def test_all_attributes_components(self):
        """All attributes pseudo has str/dex/int."""
        components = POE2_PSEUDO_COMPONENTS["pseudo_total_all_attributes"]
        assert len(components) == 3

    def test_life_component(self):
        """Life pseudo has single component."""
        components = POE2_PSEUDO_COMPONENTS["pseudo_total_life"]
        assert len(components) == 1

    def test_energy_shield_components(self):
        """Energy shield pseudo has flat and percentage."""
        components = POE2_PSEUDO_COMPONENTS["pseudo_total_energy_shield"]
        assert len(components) == 2


class TestDataIntegrity:
    """Tests for data structure integrity."""

    def test_all_affix_min_values_are_positive(self):
        """All minimum values are positive integers."""
        for affix_type, min_val in POE2_AFFIX_MIN_VALUES.items():
            assert min_val > 0, f"{affix_type} has non-positive min value"
            assert isinstance(min_val, int), f"{affix_type} min value not int"

    def test_all_tiers_are_positive(self):
        """All tier counts are positive integers."""
        for mod_name, slot_data in POE2_AFFIX_TIERS.items():
            for slot, tier_count in slot_data.items():
                assert tier_count > 0, f"{mod_name} on {slot} has non-positive tier"
                assert isinstance(tier_count, int)

    def test_stat_ids_have_correct_format(self):
        """All stat IDs have expected format."""
        for affix_type, (stat_id, is_pseudo) in POE2_AFFIX_TO_STAT_ID.items():
            if is_pseudo:
                assert "pseudo" in stat_id, f"{affix_type} marked pseudo but ID doesn't match"
            else:
                assert "explicit" in stat_id, f"{affix_type} marked explicit but ID doesn't match"
