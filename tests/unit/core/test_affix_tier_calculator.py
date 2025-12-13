"""Tests for core/affix_tier_calculator.py - Affix tier calculations."""

import pytest
from unittest.mock import patch, MagicMock

from core.affix_tier_calculator import (
    AffixTier,
    IdealRareSpec,
    AffixTierCalculator,
    AFFIX_TIER_DATA,
    SLOT_AVAILABLE_AFFIXES,
)
from core.build_priorities import BuildPriorities, PriorityTier


# =============================================================================
# AffixTier Tests
# =============================================================================


class TestAffixTier:
    """Tests for AffixTier dataclass."""

    def test_create_affix_tier(self):
        """Should create tier with all fields."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
            mod_name="Prime",
        )
        assert tier.stat_type == "life"
        assert tier.tier == 1
        assert tier.ilvl_required == 86
        assert tier.min_value == 100
        assert tier.max_value == 109
        assert tier.mod_name == "Prime"

    def test_stat_name_property(self):
        """Should return human-readable stat name."""
        tier = AffixTier(
            stat_type="fire_resistance",
            tier=1,
            ilvl_required=84,
            min_value=46,
            max_value=48,
        )
        # stat_name looks up from AVAILABLE_STATS
        assert tier.stat_name is not None

    def test_display_range_same_values(self):
        """Should show single value when min equals max."""
        tier = AffixTier(
            stat_type="movement_speed",
            tier=1,
            ilvl_required=86,
            min_value=35,
            max_value=35,
        )
        assert tier.display_range == "35"

    def test_display_range_different_values(self):
        """Should show range when min differs from max."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        assert tier.display_range == "100-109"

    def test_full_display_with_mod_name(self):
        """Should include mod name in display."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
            mod_name="Prime",
        )
        full = tier.full_display
        assert "Prime" in full
        assert "100-109" in full

    def test_full_display_without_mod_name(self):
        """Should show just range without mod name."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109,
        )
        assert tier.full_display == "100-109"


# =============================================================================
# IdealRareSpec Tests
# =============================================================================


class TestIdealRareSpec:
    """Tests for IdealRareSpec dataclass."""

    def test_create_spec(self):
        """Should create spec with fields."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        assert spec.slot == "Helmet"
        assert spec.target_ilvl == 86
        assert spec.affixes == []

    def test_get_total_value_for_stat(self):
        """Should sum stat values from affixes."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        spec.affixes = [
            AffixTier("life", 1, 86, 100, 109),
            AffixTier("fire_resistance", 1, 84, 46, 48),
        ]

        life_min, life_max = spec.get_total_value_for_stat("life")
        assert life_min == 100
        assert life_max == 109

        fire_min, fire_max = spec.get_total_value_for_stat("fire_resistance")
        assert fire_min == 46
        assert fire_max == 48

    def test_get_total_value_missing_stat(self):
        """Should return zero for missing stat."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        spec.affixes = [
            AffixTier("life", 1, 86, 100, 109),
        ]

        chaos_min, chaos_max = spec.get_total_value_for_stat("chaos_resistance")
        assert chaos_min == 0
        assert chaos_max == 0


# =============================================================================
# AffixTierCalculator Tests
# =============================================================================


class TestAffixTierCalculator:
    """Tests for AffixTierCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator without RePoE."""
        return AffixTierCalculator(use_repoe=False)

    def test_get_best_tier_for_ilvl_86(self, calculator):
        """Should get T1 life at ilvl 86."""
        tier = calculator.get_best_tier_for_ilvl("life", 86)
        assert tier is not None
        assert tier.tier == 1
        assert tier.min_value == 100
        assert tier.max_value == 109

    def test_get_best_tier_for_ilvl_75(self, calculator):
        """Should get T3 life at ilvl 75."""
        tier = calculator.get_best_tier_for_ilvl("life", 75)
        assert tier is not None
        assert tier.tier == 3
        assert tier.min_value == 80

    def test_get_best_tier_for_ilvl_low(self, calculator):
        """Should get lower tier at low ilvl."""
        tier = calculator.get_best_tier_for_ilvl("life", 50)
        assert tier is not None
        assert tier.tier >= 5

    def test_get_best_tier_unknown_stat(self, calculator):
        """Should return None for unknown stat."""
        tier = calculator.get_best_tier_for_ilvl("unknown_stat", 86)
        assert tier is None

    def test_get_all_tiers(self, calculator):
        """Should return all tiers for stat."""
        tiers = calculator.get_all_tiers("life")
        assert len(tiers) == 7
        # Should be sorted T1 first
        assert tiers[0].tier == 1
        assert tiers[-1].tier == 7

    def test_can_slot_have_stat(self, calculator):
        """Should check slot stat availability."""
        assert calculator.can_slot_have_stat("Boots", "movement_speed") is True
        assert calculator.can_slot_have_stat("Helmet", "movement_speed") is False
        assert calculator.can_slot_have_stat("Helmet", "life") is True

    def test_get_available_stats_for_slot(self, calculator):
        """Should return available stats for slot."""
        stats = calculator.get_available_stats_for_slot("Boots")
        assert "movement_speed" in stats
        assert "life" in stats

    def test_get_available_stats_unknown_slot(self, calculator):
        """Should return empty list for unknown slot."""
        stats = calculator.get_available_stats_for_slot("Unknown")
        assert stats == []


class TestAffixTierCalculatorIdealRare:
    """Tests for ideal rare calculation."""

    @pytest.fixture
    def calculator(self):
        """Create calculator without RePoE."""
        return AffixTierCalculator(use_repoe=False)

    @pytest.fixture
    def priorities(self):
        """Create sample priorities."""
        p = BuildPriorities()
        p.add_priority("life", PriorityTier.CRITICAL)
        p.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        p.add_priority("cold_resistance", PriorityTier.IMPORTANT)
        return p

    def test_calculate_ideal_rare_helmet(self, calculator, priorities):
        """Should calculate ideal helmet."""
        spec = calculator.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)

        assert spec.slot == "Helmet"
        assert spec.target_ilvl == 86
        assert len(spec.affixes) > 0

        # Should include life (critical)
        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types

    def test_calculate_ideal_rare_boots_adds_movespeed(self, calculator, priorities):
        """Should add movement speed to boots."""
        spec = calculator.calculate_ideal_rare("Boots", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" in stat_types

    def test_calculate_ideal_rare_respects_slot_restrictions(self, calculator, priorities):
        """Should not add unavailable stats to slot."""
        spec = calculator.calculate_ideal_rare("Belt", priorities, target_ilvl=86)

        # Belt can't have movement_speed
        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" not in stat_types

    def test_calculate_ideal_rare_max_affixes(self, calculator, priorities):
        """Should respect max affixes limit."""
        spec = calculator.calculate_ideal_rare(
            "Helmet", priorities, target_ilvl=86, max_affixes=3
        )
        assert len(spec.affixes) <= 3

    def test_calculate_ideal_rare_unknown_slot(self, calculator, priorities):
        """Should handle unknown slot."""
        spec = calculator.calculate_ideal_rare("Unknown", priorities, target_ilvl=86)
        assert "Unknown slot" in spec.notes
        assert len(spec.affixes) == 0

    def test_format_ideal_rare_summary(self, calculator, priorities):
        """Should format summary correctly."""
        spec = calculator.calculate_ideal_rare("Helmet", priorities, target_ilvl=86)
        summary = calculator.format_ideal_rare_summary(spec)

        assert "Ideal Helmet" in summary
        assert "ilvl 86" in summary
        assert "T1" in summary or "T2" in summary


class TestAffixTierData:
    """Tests for AFFIX_TIER_DATA constant."""

    def test_life_tiers_exist(self):
        """Should have life tiers."""
        assert "life" in AFFIX_TIER_DATA
        assert len(AFFIX_TIER_DATA["life"]) > 0

    def test_tiers_ordered_by_ilvl(self):
        """Tiers should be ordered highest ilvl first."""
        for stat_type, tiers in AFFIX_TIER_DATA.items():
            ilvls = [t[1] for t in tiers]
            assert ilvls == sorted(ilvls, reverse=True), f"{stat_type} not sorted"

    def test_all_resistances_have_tiers(self):
        """Should have resistance tiers."""
        for res in ["fire_resistance", "cold_resistance", "lightning_resistance", "chaos_resistance"]:
            assert res in AFFIX_TIER_DATA


class TestSlotAvailableAffixes:
    """Tests for SLOT_AVAILABLE_AFFIXES constant."""

    def test_all_slots_exist(self):
        """Should have all equipment slots."""
        expected_slots = [
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Belt", "Ring", "Amulet", "Shield"
        ]
        for slot in expected_slots:
            assert slot in SLOT_AVAILABLE_AFFIXES

    def test_boots_have_movement_speed(self):
        """Boots should have movement speed."""
        assert "movement_speed" in SLOT_AVAILABLE_AFFIXES["Boots"]

    def test_gloves_have_attack_speed(self):
        """Gloves should have attack speed."""
        assert "attack_speed" in SLOT_AVAILABLE_AFFIXES["Gloves"]

    def test_all_slots_have_life(self):
        """All armor slots should have life."""
        for slot in ["Helmet", "Body Armour", "Gloves", "Boots", "Belt", "Ring", "Amulet", "Shield"]:
            assert "life" in SLOT_AVAILABLE_AFFIXES[slot]


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestAffixTierCalculatorRePoE:
    """Tests for RePoE integration in AffixTierCalculator."""

    def test_use_repoe_loading_fails(self):
        """Should fall back to hardcoded when RePoE fails to load."""
        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            side_effect=Exception("RePoE not available")
        ):
            calc = AffixTierCalculator(use_repoe=True)
            assert calc.using_repoe is False

    def test_use_repoe_not_requested(self):
        """Should not use RePoE when use_repoe=False."""
        calc = AffixTierCalculator(use_repoe=False)
        assert calc.using_repoe is False

    def test_use_repoe_success(self):
        """Should use RePoE when it loads successfully."""
        mock_provider = MagicMock()

        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            return_value=mock_provider
        ):
            calc = AffixTierCalculator(use_repoe=True)
            assert calc.using_repoe is True

    def test_get_best_tier_uses_repoe(self):
        """Should use RePoE data when available."""
        mock_provider = MagicMock()
        mock_tier = MagicMock()
        mock_tier.tier_number = 1
        mock_tier.ilvl_required = 86
        mock_tier.min_value = 100
        mock_tier.max_value = 109
        mock_tier.mod_name = "Superb"
        mock_provider.get_best_tier_for_ilvl.return_value = mock_tier

        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            return_value=mock_provider
        ):
            calc = AffixTierCalculator(use_repoe=True)
            tier = calc.get_best_tier_for_ilvl("life", 86)

            assert tier is not None
            assert tier.tier == 1
            assert tier.mod_name == "Superb"
            mock_provider.get_best_tier_for_ilvl.assert_called_with("life", 86)

    def test_get_best_tier_repoe_returns_none(self):
        """Should fall back to hardcoded if RePoE returns None."""
        mock_provider = MagicMock()
        mock_provider.get_best_tier_for_ilvl.return_value = None

        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            return_value=mock_provider
        ):
            calc = AffixTierCalculator(use_repoe=True)
            tier = calc.get_best_tier_for_ilvl("life", 86)

            # Should fall back to hardcoded data
            assert tier is not None
            assert tier.tier == 1  # T1 life from hardcoded

    def test_get_all_tiers_uses_repoe(self):
        """Should use RePoE data for get_all_tiers."""
        mock_provider = MagicMock()
        mock_tier1 = MagicMock(tier_number=1, ilvl_required=86, min_value=100, max_value=109, mod_name="T1")
        mock_tier2 = MagicMock(tier_number=2, ilvl_required=82, min_value=90, max_value=99, mod_name="T2")
        mock_provider.get_tiers_for_stat.return_value = [mock_tier1, mock_tier2]

        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            return_value=mock_provider
        ):
            calc = AffixTierCalculator(use_repoe=True)
            tiers = calc.get_all_tiers("life")

            assert len(tiers) == 2
            assert tiers[0].tier == 1
            assert tiers[1].tier == 2

    def test_get_all_tiers_repoe_returns_none(self):
        """Should fall back to hardcoded if RePoE returns None."""
        mock_provider = MagicMock()
        mock_provider.get_tiers_for_stat.return_value = None

        with patch(
            "core.repoe_tier_provider.get_repoe_tier_provider",
            return_value=mock_provider
        ):
            calc = AffixTierCalculator(use_repoe=True)
            tiers = calc.get_all_tiers("life")

            # Should fall back to hardcoded
            assert len(tiers) == 7  # Hardcoded has 7 life tiers


class TestIdealRarePriorityBranches:
    """Tests for priority iteration branches in calculate_ideal_rare."""

    @pytest.fixture
    def calculator(self):
        """Create calculator without RePoE."""
        return AffixTierCalculator(use_repoe=False)

    def test_critical_priorities_fill_affixes(self, calculator):
        """Critical priorities should fill affixes first."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.CRITICAL)
        priorities.add_priority("cold_resistance", PriorityTier.CRITICAL)
        priorities.add_priority("lightning_resistance", PriorityTier.IMPORTANT)

        spec = calculator.calculate_ideal_rare("Helmet", priorities, max_affixes=3)

        stat_types = [a.stat_type for a in spec.affixes]
        # Should have all 3 critical, not important
        assert "life" in stat_types
        assert "fire_resistance" in stat_types
        assert "cold_resistance" in stat_types
        assert "lightning_resistance" not in stat_types  # Limit reached

    def test_nice_to_have_fills_remaining(self, calculator):
        """Nice-to-have priorities should fill remaining slots."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("attack_speed", PriorityTier.NICE_TO_HAVE)

        spec = calculator.calculate_ideal_rare("Gloves", priorities, max_affixes=6)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types
        assert "attack_speed" in stat_types

    def test_is_life_build_adds_life(self, calculator):
        """Life build should add life if room and not already added."""
        priorities = BuildPriorities()
        priorities.is_life_build = True
        # Don't add life as priority

        spec = calculator.calculate_ideal_rare("Helmet", priorities, max_affixes=6)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types

    def test_is_es_build_adds_es(self, calculator):
        """ES build should add energy_shield if room and not already added."""
        priorities = BuildPriorities()
        priorities.is_es_build = True
        priorities.is_life_build = False

        spec = calculator.calculate_ideal_rare("Helmet", priorities, max_affixes=6)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "energy_shield" in stat_types

    def test_max_affixes_stops_iteration(self, calculator):
        """Should stop adding affixes when max reached."""
        priorities = BuildPriorities()
        for stat in ["life", "fire_resistance", "cold_resistance", "lightning_resistance", "chaos_resistance"]:
            priorities.add_priority(stat, PriorityTier.CRITICAL)

        spec = calculator.calculate_ideal_rare("Helmet", priorities, max_affixes=2)

        # Should only have 2 affixes
        assert len(spec.affixes) == 2

    def test_stat_not_available_skipped(self, calculator):
        """Should skip stats not available on slot."""
        priorities = BuildPriorities()
        priorities.add_priority("movement_speed", PriorityTier.CRITICAL)  # Not on Helmet
        priorities.add_priority("life", PriorityTier.IMPORTANT)

        spec = calculator.calculate_ideal_rare("Helmet", priorities, max_affixes=6)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" not in stat_types
        assert "life" in stat_types


class TestIdealRareLowIlvlFallback:
    """Tests for low ilvl fallback in get_best_tier_for_ilvl."""

    @pytest.fixture
    def calculator(self):
        """Create calculator without RePoE."""
        return AffixTierCalculator(use_repoe=False)

    def test_very_low_ilvl_returns_lowest_tier(self, calculator):
        """Should return lowest tier when ilvl is below all requirements."""
        # ilvl 1 is below all tier requirements
        tier = calculator.get_best_tier_for_ilvl("life", 1)

        # Should return the lowest tier (T7)
        assert tier is not None
        assert tier.tier == 7  # Lowest tier


class TestFormatIdealRareSummary:
    """Tests for format_ideal_rare_summary."""

    @pytest.fixture
    def calculator(self):
        """Create calculator without RePoE."""
        return AffixTierCalculator(use_repoe=False)

    def test_format_with_mod_names(self, calculator):
        """Should include mod names when show_mod_names=True and mod_name present."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        spec.affixes = [
            AffixTier("life", 1, 86, 100, 109, mod_name="Prime"),
        ]

        summary = calculator.format_ideal_rare_summary(spec, show_mod_names=True)

        assert "Prime" in summary
        assert "100-109" in summary

    def test_format_without_mod_names(self, calculator):
        """Should not include mod names when show_mod_names=False."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        spec.affixes = [
            AffixTier("life", 1, 86, 100, 109, mod_name="Prime"),
        ]

        summary = calculator.format_ideal_rare_summary(spec, show_mod_names=False)

        assert "Prime" not in summary
        assert "100-109" in summary

    def test_format_affix_without_mod_name(self, calculator):
        """Should handle affixes without mod_name."""
        spec = IdealRareSpec(slot="Helmet", target_ilvl=86)
        spec.affixes = [
            AffixTier("life", 1, 86, 100, 109),  # No mod_name
        ]

        summary = calculator.format_ideal_rare_summary(spec, show_mod_names=True)

        # Should still work
        assert "100-109" in summary
        assert "T1" in summary
