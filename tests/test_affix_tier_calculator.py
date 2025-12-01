"""
Tests for Affix Tier Calculator Module.

Tests the affix tier calculation functionality including:
- AffixTier dataclass
- IdealRareSpec dataclass
- AffixTierCalculator class methods
- Slot-specific affix availability
- Ideal rare item generation
"""
import pytest
from unittest.mock import Mock, patch

from core.affix_tier_calculator import (
    AffixTier,
    IdealRareSpec,
    AffixTierCalculator,
    AFFIX_TIER_DATA,
    SLOT_AVAILABLE_AFFIXES,
)
from core.build_priorities import BuildPriorities, PriorityTier


class TestAffixTier:
    """Tests for AffixTier dataclass."""

    def test_basic_creation(self):
        """Test creating a basic AffixTier."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        assert tier.stat_type == "life"
        assert tier.tier == 1
        assert tier.ilvl_required == 86
        assert tier.min_value == 100
        assert tier.max_value == 109
        assert tier.mod_name == ""

    def test_with_mod_name(self):
        """Test AffixTier with mod name."""
        tier = AffixTier(
            stat_type="fire_resistance",
            tier=1,
            ilvl_required=84,
            min_value=46,
            max_value=48,
            mod_name="of Tzteosh",
        )
        assert tier.mod_name == "of Tzteosh"

    def test_stat_name_property(self):
        """Test stat_name property returns display name."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        # Should return display name from AVAILABLE_STATS
        assert tier.stat_name is not None
        assert len(tier.stat_name) > 0

    def test_display_range_single_value(self):
        """Test display_range when min equals max."""
        tier = AffixTier(
            stat_type="movement_speed",
            tier=1,
            ilvl_required=86,
            min_value=35,
            max_value=35,
        )
        assert tier.display_range == "35"

    def test_display_range_range(self):
        """Test display_range with different min/max."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        assert tier.display_range == "100-109"

    def test_full_display_with_mod_name(self):
        """Test full_display with mod name."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
            mod_name="Prime",
        )
        assert "Prime" in tier.full_display
        assert "100-109" in tier.full_display

    def test_full_display_without_mod_name(self):
        """Test full_display without mod name."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        assert tier.full_display == "100-109"


class TestIdealRareSpec:
    """Tests for IdealRareSpec dataclass."""

    def test_basic_creation(self):
        """Test creating a basic IdealRareSpec."""
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
        )
        assert spec.slot == "Helmet"
        assert spec.target_ilvl == 86
        assert spec.affixes == []
        assert spec.notes == ""

    def test_with_affixes(self):
        """Test IdealRareSpec with affixes."""
        affixes = [
            AffixTier("life", 1, 86, 100, 109),
            AffixTier("fire_resistance", 1, 84, 46, 48),
        ]
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=affixes,
            notes="Test spec",
        )
        assert len(spec.affixes) == 2
        assert spec.notes == "Test spec"

    def test_get_total_value_for_stat(self):
        """Test get_total_value_for_stat calculation."""
        affixes = [
            AffixTier("life", 1, 86, 100, 109),
            AffixTier("life", 2, 82, 90, 99),  # Second life affix (unusual but possible)
        ]
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=affixes,
        )
        min_val, max_val = spec.get_total_value_for_stat("life")
        assert min_val == 190  # 100 + 90
        assert max_val == 208  # 109 + 99

    def test_get_total_value_for_stat_not_present(self):
        """Test get_total_value_for_stat when stat not present."""
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=[AffixTier("life", 1, 86, 100, 109)],
        )
        min_val, max_val = spec.get_total_value_for_stat("fire_resistance")
        assert min_val == 0
        assert max_val == 0


class TestAffixTierData:
    """Tests for hardcoded tier data constants."""

    def test_common_stats_have_data(self):
        """Test that common stats have tier data."""
        common_stats = [
            "life", "energy_shield", "fire_resistance", "cold_resistance",
            "lightning_resistance", "chaos_resistance", "strength", "dexterity",
            "intelligence", "movement_speed", "attack_speed",
        ]
        for stat in common_stats:
            assert stat in AFFIX_TIER_DATA, f"{stat} should have tier data"
            assert len(AFFIX_TIER_DATA[stat]) > 0, f"{stat} should have at least one tier"

    def test_tier_data_format(self):
        """Test tier data has correct format."""
        for stat_type, tiers in AFFIX_TIER_DATA.items():
            for tier_data in tiers:
                assert len(tier_data) == 4, f"{stat_type} tier should have 4 elements"
                tier, ilvl_req, min_val, max_val = tier_data
                assert isinstance(tier, int)
                assert isinstance(ilvl_req, int)
                assert isinstance(min_val, int)
                assert isinstance(max_val, int)
                assert min_val <= max_val

    def test_tiers_sorted_by_ilvl_descending(self):
        """Test tiers are sorted by ilvl (highest first)."""
        for stat_type, tiers in AFFIX_TIER_DATA.items():
            ilvl_reqs = [t[1] for t in tiers]
            assert ilvl_reqs == sorted(ilvl_reqs, reverse=True), \
                f"{stat_type} tiers should be sorted by ilvl descending"


class TestSlotAvailableAffixes:
    """Tests for slot affix availability constants."""

    def test_common_slots_defined(self):
        """Test common equipment slots are defined."""
        expected_slots = [
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Belt", "Ring", "Amulet", "Shield",
        ]
        for slot in expected_slots:
            assert slot in SLOT_AVAILABLE_AFFIXES, f"{slot} should be defined"

    def test_life_available_on_armor(self):
        """Test life is available on armor pieces."""
        armor_slots = ["Helmet", "Body Armour", "Gloves", "Boots"]
        for slot in armor_slots:
            assert "life" in SLOT_AVAILABLE_AFFIXES[slot], \
                f"life should be available on {slot}"

    def test_movement_speed_only_on_boots(self):
        """Test movement speed is only available on boots."""
        assert "movement_speed" in SLOT_AVAILABLE_AFFIXES["Boots"]
        for slot in ["Helmet", "Body Armour", "Gloves", "Belt", "Ring", "Amulet"]:
            assert "movement_speed" not in SLOT_AVAILABLE_AFFIXES.get(slot, []), \
                f"movement_speed should not be on {slot}"

    def test_attack_speed_only_on_gloves(self):
        """Test attack speed is only available on gloves among armor."""
        assert "attack_speed" in SLOT_AVAILABLE_AFFIXES["Gloves"]
        for slot in ["Helmet", "Body Armour", "Boots", "Belt"]:
            assert "attack_speed" not in SLOT_AVAILABLE_AFFIXES.get(slot, []), \
                f"attack_speed should not be on {slot}"


class TestAffixTierCalculator:
    """Tests for AffixTierCalculator class."""

    def test_initialization_without_repoe(self):
        """Test initialization with RePoE disabled."""
        calc = AffixTierCalculator(use_repoe=False)
        assert calc._repoe_provider is None
        assert calc.using_repoe is False

    def test_initialization_with_repoe_fallback(self):
        """Test initialization falls back when RePoE unavailable."""
        # Patch the import inside the __init__ to simulate failure
        with patch.dict('sys.modules', {'core.repoe_tier_provider': None}):
            calc = AffixTierCalculator(use_repoe=True)
            # Should fall back gracefully (may or may not load depending on import cache)
            # Just verify it doesn't crash
            assert calc._tier_data is not None

    def test_get_best_tier_for_ilvl_life(self):
        """Test getting best life tier for different ilvls."""
        calc = AffixTierCalculator(use_repoe=False)

        # ilvl 86+ should get T1
        tier = calc.get_best_tier_for_ilvl("life", 86)
        assert tier is not None
        assert tier.tier == 1
        assert tier.min_value == 100

        # ilvl 82 should get T2
        tier = calc.get_best_tier_for_ilvl("life", 82)
        assert tier is not None
        assert tier.tier == 2

        # ilvl 73 should get T3
        tier = calc.get_best_tier_for_ilvl("life", 73)
        assert tier is not None
        assert tier.tier == 3

    def test_get_best_tier_for_ilvl_unknown_stat(self):
        """Test getting tier for unknown stat returns None."""
        calc = AffixTierCalculator(use_repoe=False)
        tier = calc.get_best_tier_for_ilvl("unknown_stat", 86)
        assert tier is None

    def test_get_best_tier_for_ilvl_low_level(self):
        """Test getting tier at very low level."""
        calc = AffixTierCalculator(use_repoe=False)
        # Even at ilvl 1, should return lowest tier
        tier = calc.get_best_tier_for_ilvl("life", 1)
        assert tier is not None
        assert tier.tier == 7  # Lowest tier for life

    def test_get_all_tiers(self):
        """Test getting all tiers for a stat."""
        calc = AffixTierCalculator(use_repoe=False)
        tiers = calc.get_all_tiers("life")
        assert len(tiers) == 7  # Life has 7 tiers
        # Should be sorted by tier number
        for i, tier in enumerate(tiers):
            assert tier.tier == i + 1

    def test_get_all_tiers_unknown_stat(self):
        """Test getting tiers for unknown stat returns empty list."""
        calc = AffixTierCalculator(use_repoe=False)
        tiers = calc.get_all_tiers("unknown_stat")
        assert tiers == []

    def test_can_slot_have_stat(self):
        """Test checking slot stat availability."""
        calc = AffixTierCalculator(use_repoe=False)

        assert calc.can_slot_have_stat("Boots", "movement_speed") is True
        assert calc.can_slot_have_stat("Helmet", "movement_speed") is False
        assert calc.can_slot_have_stat("Gloves", "attack_speed") is True
        assert calc.can_slot_have_stat("Boots", "attack_speed") is False

    def test_can_slot_have_stat_unknown_slot(self):
        """Test checking stat for unknown slot."""
        calc = AffixTierCalculator(use_repoe=False)
        assert calc.can_slot_have_stat("UnknownSlot", "life") is False

    def test_get_available_stats_for_slot(self):
        """Test getting available stats for a slot."""
        calc = AffixTierCalculator(use_repoe=False)

        boot_stats = calc.get_available_stats_for_slot("Boots")
        assert "life" in boot_stats
        assert "movement_speed" in boot_stats
        assert "attack_speed" not in boot_stats

    def test_get_available_stats_for_unknown_slot(self):
        """Test getting stats for unknown slot returns empty list."""
        calc = AffixTierCalculator(use_repoe=False)
        stats = calc.get_available_stats_for_slot("UnknownSlot")
        assert stats == []


class TestCalculateIdealRare:
    """Tests for calculate_ideal_rare method."""

    def test_basic_ideal_rare(self):
        """Test generating basic ideal rare."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        assert spec.slot == "Helmet"
        assert spec.target_ilvl == 86
        assert len(spec.affixes) >= 2
        # Life should be first (critical)
        assert spec.affixes[0].stat_type == "life"

    def test_ideal_rare_respects_max_affixes(self):
        """Test ideal rare respects max_affixes limit."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.CRITICAL)
        priorities.add_priority("cold_resistance", PriorityTier.CRITICAL)
        priorities.add_priority("lightning_resistance", PriorityTier.CRITICAL)

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86, max_affixes=3)

        assert len(spec.affixes) == 3

    def test_ideal_rare_boots_get_movement_speed(self):
        """Test boots automatically get movement speed."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)

        spec = calc.calculate_ideal_rare("Boots", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" in stat_types

    def test_ideal_rare_unknown_slot(self):
        """Test ideal rare for unknown slot."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()

        spec = calc.calculate_ideal_rare("UnknownSlot", priorities, target_ilvl=86)

        assert "Unknown slot" in spec.notes
        assert len(spec.affixes) == 0

    def test_ideal_rare_life_build_adds_life(self):
        """Test life build automatically adds life if room."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities(is_life_build=True)
        # Don't add life as priority - should be auto-added

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types

    def test_ideal_rare_es_build_adds_es(self):
        """Test ES build automatically adds ES if room."""
        calc = AffixTierCalculator(use_repoe=False)
        # Must explicitly set is_life_build=False since it takes precedence in elif
        priorities = BuildPriorities(is_es_build=True, is_life_build=False)
        # Don't add ES as priority - should be auto-added

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "energy_shield" in stat_types

    def test_ideal_rare_priority_order(self):
        """Test affixes added in priority order."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()
        priorities.add_priority("fire_resistance", PriorityTier.CRITICAL)
        priorities.add_priority("life", PriorityTier.IMPORTANT)
        priorities.add_priority("cold_resistance", PriorityTier.NICE_TO_HAVE)

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        # First should be fire_resistance (critical)
        assert spec.affixes[0].stat_type == "fire_resistance"
        # Second should be life (important)
        assert spec.affixes[1].stat_type == "life"

    def test_ideal_rare_skips_unavailable_stats(self):
        """Test ideal rare skips stats not available on slot."""
        calc = AffixTierCalculator(use_repoe=False)
        priorities = BuildPriorities()
        priorities.add_priority("movement_speed", PriorityTier.CRITICAL)  # Not on helmet
        priorities.add_priority("life", PriorityTier.IMPORTANT)

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" not in stat_types
        assert "life" in stat_types


class TestFormatIdealRareSummary:
    """Tests for format_ideal_rare_summary method."""

    def test_basic_format(self):
        """Test basic formatting."""
        calc = AffixTierCalculator(use_repoe=False)
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=[
                AffixTier("life", 1, 86, 100, 109),
                AffixTier("fire_resistance", 1, 84, 46, 48),
            ],
        )

        summary = calc.format_ideal_rare_summary(spec)

        assert "Ideal Helmet" in summary
        assert "ilvl 86" in summary
        assert "T1" in summary
        assert "100-109" in summary

    def test_format_with_mod_names(self):
        """Test formatting includes mod names when present."""
        calc = AffixTierCalculator(use_repoe=False)
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=[
                AffixTier("life", 1, 86, 100, 109, mod_name="Prime"),
            ],
        )

        summary = calc.format_ideal_rare_summary(spec, show_mod_names=True)

        assert "Prime" in summary

    def test_format_without_mod_names(self):
        """Test formatting excludes mod names when disabled."""
        calc = AffixTierCalculator(use_repoe=False)
        spec = IdealRareSpec(
            slot="Helmet",
            target_ilvl=86,
            affixes=[
                AffixTier("life", 1, 86, 100, 109, mod_name="Prime"),
            ],
        )

        summary = calc.format_ideal_rare_summary(spec, show_mod_names=False)

        assert "Prime" not in summary


class TestAffixTierCalculatorWithRePoE:
    """Tests for AffixTierCalculator with mocked RePoE data."""

    def test_uses_repoe_when_available(self):
        """Test calculator uses RePoE data when available."""
        mock_provider = Mock()
        mock_repoe_tier = Mock()
        mock_repoe_tier.tier_number = 1
        mock_repoe_tier.ilvl_required = 86
        mock_repoe_tier.min_value = 100
        mock_repoe_tier.max_value = 109
        mock_repoe_tier.mod_name = "Prime"
        mock_provider.get_best_tier_for_ilvl.return_value = mock_repoe_tier

        calc = AffixTierCalculator(use_repoe=False)
        calc._repoe_provider = mock_provider

        tier = calc.get_best_tier_for_ilvl("life", 86)

        assert tier is not None
        assert tier.mod_name == "Prime"
        mock_provider.get_best_tier_for_ilvl.assert_called_once_with("life", 86)

    def test_falls_back_to_hardcoded_when_repoe_returns_none(self):
        """Test falls back to hardcoded data when RePoE returns None."""
        mock_provider = Mock()
        mock_provider.get_best_tier_for_ilvl.return_value = None

        calc = AffixTierCalculator(use_repoe=False)
        calc._repoe_provider = mock_provider

        tier = calc.get_best_tier_for_ilvl("life", 86)

        # Should fall back to hardcoded data
        assert tier is not None
        assert tier.tier == 1

    def test_get_all_tiers_with_repoe(self):
        """Test get_all_tiers uses RePoE data when available."""
        mock_provider = Mock()
        mock_repoe_tiers = [
            Mock(tier_number=1, ilvl_required=86, min_value=100, max_value=109, mod_name="T1"),
            Mock(tier_number=2, ilvl_required=82, min_value=90, max_value=99, mod_name="T2"),
        ]
        mock_provider.get_tiers_for_stat.return_value = mock_repoe_tiers

        calc = AffixTierCalculator(use_repoe=False)
        calc._repoe_provider = mock_provider

        tiers = calc.get_all_tiers("life")

        assert len(tiers) == 2
        assert tiers[0].mod_name == "T1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
