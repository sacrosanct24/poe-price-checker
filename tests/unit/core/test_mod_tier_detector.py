"""Tests for core/mod_tier_detector.py - Mod Tier Detection."""

import pytest
from unittest.mock import patch

from core.mod_tier_detector import (
    ModTierResult,
    MOD_PATTERNS,
    detect_mod_tier,
    detect_mod_tiers,
    get_mod_display_info,
    _get_tier_for_value,
)


# ============================================================================
# ModTierResult Dataclass Tests
# ============================================================================

class TestModTierResult:
    """Tests for ModTierResult dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        result = ModTierResult(mod_text="+50 to Maximum Life")

        assert result.mod_text == "+50 to Maximum Life"
        assert result.stat_type is None
        assert result.tier is None
        assert result.value is None
        assert result.is_crafted is False
        assert result.is_implicit is False

    def test_tier_label_with_tier(self):
        """tier_label returns T# format when tier is set."""
        result = ModTierResult(mod_text="test", tier=1)
        assert result.tier_label == "T1"

        result = ModTierResult(mod_text="test", tier=3)
        assert result.tier_label == "T3"

        result = ModTierResult(mod_text="test", tier=7)
        assert result.tier_label == "T7"

    def test_tier_label_without_tier(self):
        """tier_label returns empty string when tier is None."""
        result = ModTierResult(mod_text="test", tier=None)
        assert result.tier_label == ""

    def test_all_fields_set(self):
        """All fields can be set."""
        result = ModTierResult(
            mod_text="+92 to Maximum Life",
            stat_type="life",
            tier=2,
            value=92,
            is_crafted=False,
            is_implicit=True,
        )

        assert result.mod_text == "+92 to Maximum Life"
        assert result.stat_type == "life"
        assert result.tier == 2
        assert result.value == 92
        assert result.is_crafted is False
        assert result.is_implicit is True


# ============================================================================
# MOD_PATTERNS Tests
# ============================================================================

class TestModPatterns:
    """Tests for MOD_PATTERNS regex patterns."""

    def test_life_pattern(self):
        """Life pattern matches correctly."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "life")

        match = re.search(pattern, "+92 to Maximum Life")
        assert match is not None
        assert match.group(1) == "92"

    def test_fire_resistance_pattern(self):
        """Fire resistance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "fire_resistance")

        match = re.search(pattern, "+45% to Fire Resistance")
        assert match is not None
        assert match.group(1) == "45"

    def test_cold_resistance_pattern(self):
        """Cold resistance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "cold_resistance")

        match = re.search(pattern, "+30% to Cold Resistance")
        assert match is not None
        assert match.group(1) == "30"

    def test_lightning_resistance_pattern(self):
        """Lightning resistance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "lightning_resistance")

        match = re.search(pattern, "+42% to Lightning Resistance")
        assert match is not None
        assert match.group(1) == "42"

    def test_chaos_resistance_pattern(self):
        """Chaos resistance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "chaos_resistance")

        match = re.search(pattern, "+20% to Chaos Resistance")
        assert match is not None
        assert match.group(1) == "20"

    def test_all_ele_res_pattern(self):
        """All elemental resistance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "all_ele_res")

        match = re.search(pattern, "+12% to all Elemental Resistances")
        assert match is not None
        assert match.group(1) == "12"

    def test_strength_pattern(self):
        """Strength pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "strength")

        match = re.search(pattern, "+55 to Strength")
        assert match is not None
        assert match.group(1) == "55"

    def test_dexterity_pattern(self):
        """Dexterity pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "dexterity")

        match = re.search(pattern, "+40 to Dexterity")
        assert match is not None
        assert match.group(1) == "40"

    def test_intelligence_pattern(self):
        """Intelligence pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "intelligence")

        match = re.search(pattern, "+48 to Intelligence")
        assert match is not None
        assert match.group(1) == "48"

    def test_all_attributes_pattern(self):
        """All attributes pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "all_attributes")

        match = re.search(pattern, "+16 to all Attributes")
        assert match is not None
        assert match.group(1) == "16"

    def test_movement_speed_pattern(self):
        """Movement speed pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "movement_speed")

        match = re.search(pattern, "35% increased Movement Speed")
        assert match is not None
        assert match.group(1) == "35"

    def test_attack_speed_pattern(self):
        """Attack speed pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "attack_speed")

        match = re.search(pattern, "14% increased Attack Speed")
        assert match is not None
        assert match.group(1) == "14"

    def test_cast_speed_pattern(self):
        """Cast speed pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "cast_speed")

        match = re.search(pattern, "20% increased Cast Speed")
        assert match is not None
        assert match.group(1) == "20"

    def test_crit_chance_pattern(self):
        """Critical strike chance pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "critical_strike_chance")

        match = re.search(pattern, "30% increased Global Critical Strike Chance")
        assert match is not None
        assert match.group(1) == "30"

    def test_crit_multi_pattern(self):
        """Critical strike multiplier pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "critical_strike_multiplier")

        match = re.search(pattern, "+25% to Global Critical Strike Multiplier")
        assert match is not None
        assert match.group(1) == "25"

    def test_mana_pattern(self):
        """Mana pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "mana")

        match = re.search(pattern, "+70 to Maximum Mana")
        assert match is not None
        assert match.group(1) == "70"

    def test_energy_shield_pattern(self):
        """Energy shield pattern matches."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "energy_shield")

        match = re.search(pattern, "+50 to Maximum Energy Shield")
        assert match is not None
        assert match.group(1) == "50"

    def test_life_regen_pattern(self):
        """Life regeneration pattern matches decimal values."""
        import re
        pattern = next(p for p, s, i in MOD_PATTERNS if s == "life_regeneration")

        match = re.search(pattern, "Regenerate 7.5 Life per second")
        assert match is not None
        assert match.group(1) == "7.5"


# ============================================================================
# detect_mod_tier Tests
# ============================================================================

class TestDetectModTier:
    """Tests for detect_mod_tier function."""

    def test_detects_life_mod(self):
        """Detects life mod tier."""
        result = detect_mod_tier("+92 to Maximum Life")

        assert result.stat_type == "life"
        assert result.value == 92

    def test_detects_resistance_mod(self):
        """Detects resistance mod."""
        result = detect_mod_tier("+45% to Fire Resistance")

        assert result.stat_type == "fire_resistance"
        assert result.value == 45

    def test_detects_attribute_mod(self):
        """Detects attribute mod."""
        result = detect_mod_tier("+55 to Strength")

        assert result.stat_type == "strength"
        assert result.value == 55

    def test_detects_movement_speed(self):
        """Detects movement speed mod."""
        result = detect_mod_tier("35% increased Movement Speed")

        assert result.stat_type == "movement_speed"
        assert result.value == 35

    def test_detects_crafted_mod(self):
        """Detects crafted mod marker."""
        result = detect_mod_tier("+50 to Dexterity (crafted)")

        assert result.is_crafted is True
        assert result.stat_type == "dexterity"

    def test_implicit_flag_passed_through(self):
        """Implicit flag is passed through."""
        result = detect_mod_tier("+30 to Intelligence", is_implicit=True)

        assert result.is_implicit is True

    def test_unrecognized_mod(self):
        """Unrecognized mod returns empty result."""
        result = detect_mod_tier("Some unknown modifier text")

        assert result.stat_type is None
        assert result.tier is None
        assert result.value is None

    def test_handles_decimal_values(self):
        """Handles decimal values (like life regen)."""
        result = detect_mod_tier("Regenerate 7.5 Life per second")

        assert result.stat_type == "life_regeneration"
        assert result.value == 7  # Converted to int

    def test_case_sensitive_patterns(self):
        """Pattern matching uses character classes for partial case sensitivity."""
        # Patterns use [Mm]aximum style - matches standard title case and lowercase
        result1 = detect_mod_tier("+50 to maximum life")
        result2 = detect_mod_tier("+50 to Maximum Life")

        assert result1.stat_type == "life"
        assert result2.stat_type == "life"

        # All caps doesn't match because [Mm] doesn't include 'A' for MAXIMUM
        result3 = detect_mod_tier("+50 to MAXIMUM LIFE")
        assert result3.stat_type is None  # No match for all caps

    @patch('core.mod_tier_detector._get_tier_for_value')
    def test_calls_tier_lookup(self, mock_get_tier):
        """Calls tier lookup with correct arguments."""
        mock_get_tier.return_value = 2

        result = detect_mod_tier("+92 to Maximum Life")

        mock_get_tier.assert_called_once_with("life", 92)
        assert result.tier == 2


# ============================================================================
# _get_tier_for_value Tests
# ============================================================================

class TestGetTierForValue:
    """Tests for _get_tier_for_value function."""

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {})
    def test_returns_none_for_unknown_stat(self):
        """Returns None for unknown stat type."""
        result = _get_tier_for_value("unknown_stat", 50)
        assert result is None

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {
        "life": [
            (1, 82, 90, 99),  # T1: 90-99
            (2, 74, 80, 89),  # T2: 80-89
            (3, 64, 70, 79),  # T3: 70-79
        ]
    })
    def test_returns_correct_tier_for_value_in_range(self):
        """Returns correct tier when value is in range."""
        assert _get_tier_for_value("life", 95) == 1
        assert _get_tier_for_value("life", 85) == 2
        assert _get_tier_for_value("life", 75) == 3

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {
        "life": [
            (1, 82, 90, 99),
            (2, 74, 80, 89),
        ]
    })
    def test_returns_t1_for_value_above_max(self):
        """Returns T1 for value above T1 max (elevated/exceptional roll)."""
        assert _get_tier_for_value("life", 105) == 1

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {
        "life": [
            (1, 82, 90, 99),
            (2, 74, 80, 89),
        ]
    })
    def test_returns_worst_tier_for_value_below_min(self):
        """Returns worst tier for value below all tiers."""
        assert _get_tier_for_value("life", 50) == 2

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {
        "life": [
            (1, 82, 90, 99),
        ]
    })
    def test_matches_exact_boundaries(self):
        """Matches values exactly on tier boundaries."""
        assert _get_tier_for_value("life", 90) == 1  # Min value
        assert _get_tier_for_value("life", 99) == 1  # Max value


# ============================================================================
# detect_mod_tiers Tests
# ============================================================================

class TestDetectModTiers:
    """Tests for detect_mod_tiers function."""

    def test_detects_multiple_mods(self):
        """Detects tiers for multiple mods."""
        mods = [
            "+92 to Maximum Life",
            "+45% to Fire Resistance",
            "35% increased Movement Speed",
        ]

        results = detect_mod_tiers(mods)

        assert len(results) == 3
        assert results[0].stat_type == "life"
        assert results[1].stat_type == "fire_resistance"
        assert results[2].stat_type == "movement_speed"

    def test_empty_list_returns_empty(self):
        """Empty mod list returns empty results."""
        results = detect_mod_tiers([])
        assert results == []

    def test_passes_implicit_flag(self):
        """Passes implicit flag to all results."""
        mods = ["+50 to Life", "+30% to Fire Resistance"]

        results = detect_mod_tiers(mods, are_implicit=True)

        assert all(r.is_implicit for r in results)


# ============================================================================
# get_mod_display_info Tests
# ============================================================================

class TestGetModDisplayInfo:
    """Tests for get_mod_display_info function."""

    def test_returns_tuple(self):
        """Returns tuple of (tier_label, tier, stat_type)."""
        result = get_mod_display_info("+92 to Maximum Life")

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_returns_tier_label(self):
        """Returns tier label in first position."""
        tier_label, tier, stat_type = get_mod_display_info("+92 to Maximum Life")

        # tier_label format depends on tier data
        assert isinstance(tier_label, str)

    def test_returns_stat_type(self):
        """Returns stat type in third position."""
        tier_label, tier, stat_type = get_mod_display_info("+92 to Maximum Life")

        assert stat_type == "life"

    def test_handles_unrecognized_mod(self):
        """Handles unrecognized mod gracefully."""
        tier_label, tier, stat_type = get_mod_display_info("Unknown mod text")

        assert tier_label == ""
        assert tier is None
        assert stat_type == ""

    def test_passes_implicit_flag(self):
        """Passes implicit flag through."""
        # Just verifies it doesn't error - implicit handling is internal
        result = get_mod_display_info("+50 to Life", is_implicit=True)
        assert result is not None


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_empty_string(self):
        """Handles empty string mod text."""
        result = detect_mod_tier("")

        assert result.mod_text == ""
        assert result.stat_type is None

    def test_handles_whitespace_only(self):
        """Handles whitespace-only mod text."""
        result = detect_mod_tier("   ")

        assert result.stat_type is None

    def test_handles_partial_match(self):
        """Handles text that partially matches pattern."""
        # Missing the number
        result = detect_mod_tier("+to Maximum Life")

        assert result.stat_type is None

    def test_handles_malformed_numbers(self):
        """Handles malformed numeric values gracefully."""
        # This shouldn't match since pattern expects digits
        result = detect_mod_tier("+abc to Maximum Life")

        assert result.value is None

    def test_first_pattern_match_wins(self):
        """First matching pattern is used (order matters)."""
        # Both +X to Maximum Life and +X to Life match for "life"
        result = detect_mod_tier("+50 to Maximum Life")

        assert result.stat_type == "life"
        assert result.value == 50

    def test_crafted_marker_variations(self):
        """Detects crafted marker with different casings."""
        assert detect_mod_tier("+50 to Dex (Crafted)").is_crafted is True
        assert detect_mod_tier("+50 to Dex (CRAFTED)").is_crafted is True
        assert detect_mod_tier("+50 to Dex (crafted)").is_crafted is True

    @patch('core.mod_tier_detector.AFFIX_TIER_DATA', {
        "life": [
            (1, 82, 90, 99),  # T1: 90-99
            (2, 64, 70, 79),  # T2: 70-79 (gap at 80-89)
        ]
    })
    def test_value_in_gap_returns_none(self):
        """Returns None for value in gap between tiers."""
        # Value 85 is between T1 min (90) and T2 max (79) - in the gap
        result = _get_tier_for_value("life", 85)
        assert result is None

    def test_parse_error_during_mod_detection(self):
        """Parse errors during mod detection are handled gracefully."""
        # Create a pattern that might cause a parsing issue
        # This tests the exception handler at lines 127-129
        result = detect_mod_tier("+to Maximum Life")
        # Should not raise, should return result with None values
        assert result.value is None
        assert result.stat_type is None

    @patch('core.mod_tier_detector.MOD_PATTERNS', [
        (r'\+(\d+) to [Mm]aximum [Ll]ife', "life", int),
        # Add a pattern that will match but cause ValueError during conversion
        (r'Adds (\S+) to (\S+) Physical Damage', "phys_damage", int),
    ])
    def test_value_conversion_error_continues(self):
        """ValueError during value conversion is caught and continues."""
        # "NaN" will match the second pattern but fail int() conversion
        result = detect_mod_tier("Adds NaN to stuff Physical Damage")
        # Should not raise, should return result with None (no patterns matched successfully)
        assert result.stat_type is None
        assert result.value is None
