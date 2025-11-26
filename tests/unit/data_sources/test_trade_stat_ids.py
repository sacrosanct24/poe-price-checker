"""
Tests for data_sources.pricing.trade_stat_ids module.

Tests the mapping of affix types to PoE Trade API stat IDs.
"""

import pytest
from data_sources.pricing.trade_stat_ids import (
    AFFIX_TO_STAT_ID,
    AFFIX_MIN_VALUES,
    get_stat_id,
    get_min_value,
    build_stat_filters,
)


class TestAffixToStatIdMapping:
    """Tests for AFFIX_TO_STAT_ID constant."""

    def test_all_mappings_have_tuple_format(self):
        """All mappings should be (stat_id, is_pseudo) tuples."""
        for affix_type, mapping in AFFIX_TO_STAT_ID.items():
            assert isinstance(mapping, tuple), f"{affix_type} should map to a tuple"
            assert len(mapping) == 2, f"{affix_type} tuple should have 2 elements"
            stat_id, is_pseudo = mapping
            assert isinstance(stat_id, str), f"{affix_type} stat_id should be string"
            assert isinstance(is_pseudo, bool), f"{affix_type} is_pseudo should be bool"

    def test_pseudo_stats_have_pseudo_prefix(self):
        """Pseudo stats should have 'pseudo.' prefix in stat_id."""
        for affix_type, (stat_id, is_pseudo) in AFFIX_TO_STAT_ID.items():
            if is_pseudo:
                assert stat_id.startswith("pseudo."), \
                    f"{affix_type} is marked as pseudo but stat_id doesn't start with 'pseudo.'"

    def test_explicit_stats_have_explicit_prefix(self):
        """Explicit stats should have 'explicit.' prefix in stat_id."""
        for affix_type, (stat_id, is_pseudo) in AFFIX_TO_STAT_ID.items():
            if not is_pseudo:
                assert stat_id.startswith("explicit."), \
                    f"{affix_type} is marked as explicit but stat_id doesn't start with 'explicit.'"

    def test_core_defensive_stats_exist(self):
        """Core defensive stats should be mapped."""
        assert "life" in AFFIX_TO_STAT_ID
        assert "energy_shield" in AFFIX_TO_STAT_ID
        assert "resistances" in AFFIX_TO_STAT_ID

    def test_core_offensive_stats_exist(self):
        """Core offensive stats should be mapped."""
        assert "critical_strike_multiplier" in AFFIX_TO_STAT_ID
        assert "critical_strike_chance" in AFFIX_TO_STAT_ID
        assert "attack_speed" in AFFIX_TO_STAT_ID

    def test_attribute_stats_exist(self):
        """Attribute stats should be mapped."""
        assert "strength" in AFFIX_TO_STAT_ID
        assert "dexterity" in AFFIX_TO_STAT_ID
        assert "intelligence" in AFFIX_TO_STAT_ID

    def test_resistance_stats_exist(self):
        """Individual resistance stats should be mapped."""
        assert "fire_resistance" in AFFIX_TO_STAT_ID
        assert "cold_resistance" in AFFIX_TO_STAT_ID
        assert "lightning_resistance" in AFFIX_TO_STAT_ID
        assert "chaos_resistance" in AFFIX_TO_STAT_ID


class TestAffixMinValues:
    """Tests for AFFIX_MIN_VALUES constant."""

    def test_all_min_values_are_positive_integers(self):
        """All minimum values should be positive integers."""
        for affix_type, min_value in AFFIX_MIN_VALUES.items():
            assert isinstance(min_value, int), f"{affix_type} min_value should be int"
            assert min_value > 0, f"{affix_type} min_value should be positive"

    def test_min_values_exist_for_common_affixes(self):
        """Min values should exist for commonly priced affixes."""
        common_affixes = ["life", "resistances", "movement_speed", "critical_strike_multiplier"]
        for affix in common_affixes:
            assert affix in AFFIX_MIN_VALUES, f"{affix} should have a min value"

    def test_life_min_value_is_reasonable(self):
        """Life min value should be T2+ threshold (around 70-80)."""
        assert 60 <= AFFIX_MIN_VALUES["life"] <= 90

    def test_resistance_min_value_is_reasonable(self):
        """Resistance min value should be T3+ threshold (around 30-40)."""
        assert 25 <= AFFIX_MIN_VALUES["resistances"] <= 50


class TestGetStatId:
    """Tests for get_stat_id function."""

    def test_returns_tuple_for_known_affix(self):
        """Should return (stat_id, is_pseudo) tuple for known affix."""
        result = get_stat_id("life")
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_none_for_unknown_affix(self):
        """Should return None for unknown affix type."""
        result = get_stat_id("nonexistent_affix_type")
        assert result is None

    def test_life_is_pseudo_stat(self):
        """Life should be a pseudo stat."""
        stat_id, is_pseudo = get_stat_id("life")
        assert is_pseudo is True
        assert "pseudo" in stat_id

    def test_movement_speed_is_explicit_stat(self):
        """Movement speed should be an explicit stat."""
        stat_id, is_pseudo = get_stat_id("movement_speed")
        assert is_pseudo is False
        assert "explicit" in stat_id


class TestGetMinValue:
    """Tests for get_min_value function."""

    def test_returns_threshold_when_no_actual_value(self):
        """Should return threshold from AFFIX_MIN_VALUES when no actual value."""
        result = get_min_value("life")
        assert result == AFFIX_MIN_VALUES["life"]

    def test_returns_none_for_unknown_affix_without_value(self):
        """Should return None for unknown affix without actual value."""
        result = get_min_value("unknown_affix")
        assert result is None

    def test_uses_80_percent_of_actual_value(self):
        """Should return 80% of actual value when provided."""
        result = get_min_value("life", actual_value=100)
        assert result == 80  # 100 * 0.8

    def test_actual_value_overrides_threshold(self):
        """Actual value should override threshold."""
        threshold = AFFIX_MIN_VALUES["life"]
        high_value = threshold * 2
        result = get_min_value("life", actual_value=high_value)
        assert result == int(high_value * 0.8)

    def test_zero_actual_value_uses_threshold(self):
        """Zero actual value should fall back to threshold."""
        result = get_min_value("life", actual_value=0)
        assert result == AFFIX_MIN_VALUES["life"]

    def test_negative_actual_value_uses_threshold(self):
        """Negative actual value should fall back to threshold."""
        result = get_min_value("life", actual_value=-10)
        assert result == AFFIX_MIN_VALUES["life"]


class TestBuildStatFilters:
    """Tests for build_stat_filters function."""

    def test_empty_list_returns_empty_filters(self):
        """Empty affix list should return empty filters."""
        result = build_stat_filters([])
        assert result == []

    def test_respects_max_filters_limit(self):
        """Should not exceed max_filters limit."""
        # Create mock affix matches
        class MockMatch:
            def __init__(self, affix_type, tier="tier1", weight=1.0, value=100):
                self.affix_type = affix_type
                self.tier = tier
                self.weight = weight
                self.value = value

        matches = [
            MockMatch("life"),
            MockMatch("resistances"),
            MockMatch("movement_speed"),
            MockMatch("critical_strike_multiplier"),
            MockMatch("attack_speed"),
            MockMatch("strength"),
        ]

        result = build_stat_filters(matches, max_filters=3)
        assert len(result) <= 3

    def test_filter_has_correct_structure(self):
        """Filter dict should have id and value keys."""
        class MockMatch:
            affix_type = "life"
            tier = "tier1"
            weight = 1.0
            value = 100

        result = build_stat_filters([MockMatch()])
        assert len(result) == 1
        assert "id" in result[0]
        assert "value" in result[0]
        assert "min" in result[0]["value"]

    def test_prioritizes_tier1_over_tier2(self):
        """T1 affixes should come before T2."""
        class MockMatch:
            def __init__(self, affix_type, tier, weight=1.0):
                self.affix_type = affix_type
                self.tier = tier
                self.weight = weight
                self.value = 100

        matches = [
            MockMatch("resistances", "tier2"),
            MockMatch("life", "tier1"),
        ]

        result = build_stat_filters(matches, max_filters=1)
        # Should only include life (tier1)
        assert len(result) == 1
        stat_id, _ = get_stat_id("life")
        assert result[0]["id"] == stat_id

    def test_skips_unknown_affix_types(self):
        """Unknown affix types should be skipped."""
        class MockMatch:
            affix_type = "unknown_affix"
            tier = "tier1"
            weight = 1.0
            value = 100

        result = build_stat_filters([MockMatch()])
        assert result == []

    def test_skips_affixes_without_type(self):
        """Affixes without affix_type attribute should be skipped."""
        class MockMatch:
            tier = "tier1"
            weight = 1.0
            value = 100
            # No affix_type attribute

        result = build_stat_filters([MockMatch()])
        assert result == []

    def test_uses_actual_value_for_min_filter(self):
        """Filter min should be based on actual rolled value."""
        class MockMatch:
            affix_type = "life"
            tier = "tier1"
            weight = 1.0
            value = 150  # High life roll

        result = build_stat_filters([MockMatch()])
        assert len(result) == 1
        # Should be 80% of 150 = 120
        assert result[0]["value"]["min"] == 120
