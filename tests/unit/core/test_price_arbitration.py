import pytest

from core.price_arbitration import arbitrate_rows, _to_dict
from core.price_row import PriceRow

pytestmark = pytest.mark.unit


class TestToDictFunction:
    """Tests for _to_dict helper function."""

    def test_dict_input_returns_copy(self):
        """Dictionary input should return a copy."""
        input_dict = {"source": "test", "chaos_value": 100}
        result = _to_dict(input_dict)
        assert result == input_dict
        assert result is not input_dict  # Should be a copy

    def test_price_row_via_vars(self):
        """Normal objects should use vars()."""
        row = PriceRow(
            source="ninja",
            item_name="Exalted Orb",
            chaos_value=150.0,
            confidence="high"
        )
        result = _to_dict(row)
        assert result["source"] == "ninja"
        assert result["item_name"] == "Exalted Orb"
        assert result["chaos_value"] == 150.0

    def test_object_without_vars_uses_getattr_fallback(self):
        """Objects that fail vars() should use getattr fallback."""
        # Create an object where vars() fails (using __slots__)
        class CustomRow:
            __slots__ = ['source', 'item_name', 'chaos_value', 'variant',
                        'links', 'divine_value', 'listing_count', 'confidence', 'explanation']

            def __init__(self):
                self.source = "custom"
                self.item_name = "Test Item"
                self.chaos_value = 50.0
                self.variant = "default"
                self.links = 6
                self.divine_value = 0.5
                self.listing_count = 10
                self.confidence = "high"
                self.explanation = "test"

        row = CustomRow()
        result = _to_dict(row)
        assert result["source"] == "custom"
        assert result["item_name"] == "Test Item"
        assert result["chaos_value"] == 50.0
        assert result["links"] == 6

    def test_fallback_handles_missing_attributes(self):
        """Fallback should handle missing attributes gracefully."""
        class MinimalRow:
            __slots__ = ['source']

            def __init__(self):
                self.source = "minimal"

        row = MinimalRow()
        result = _to_dict(row)
        assert result["source"] == "minimal"
        assert result["item_name"] == ""
        assert result["chaos_value"] is None
        assert result["confidence"] == ""


class TestArbitrateRowsEdgeCases:
    """Additional tests for arbitrate_rows edge cases."""

    def test_handles_invalid_listing_count_type_error(self):
        """TypeError during listing_count conversion should be handled."""
        rows = [
            {"source": "bad", "chaos_value": 100, "confidence": "high", "listing_count": object()},
            {"source": "good", "chaos_value": 100, "confidence": "high", "listing_count": 10},
        ]
        result = arbitrate_rows(rows)
        assert result["source"] == "good"

    def test_handles_invalid_listing_count_value_error(self):
        """ValueError during listing_count conversion should be handled."""
        rows = [
            {"source": "bad", "chaos_value": 100, "confidence": "high", "listing_count": "not_a_number"},
            {"source": "good", "chaos_value": 100, "confidence": "high", "listing_count": 5},
        ]
        result = arbitrate_rows(rows)
        assert result["source"] == "good"

    def test_handles_type_error_during_chaos_value_conversion(self):
        """TypeError during chaos_value conversion should filter the row."""
        rows = [
            {"source": "bad", "chaos_value": object()},  # Will raise TypeError
            {"source": "good", "chaos_value": 100, "confidence": "high"},
        ]
        result = arbitrate_rows(rows)
        assert result["source"] == "good"

    def test_handles_value_error_during_chaos_value_conversion(self):
        """ValueError during chaos_value conversion should filter the row."""
        rows = [
            {"source": "bad", "chaos_value": "not_convertible"},
            {"source": "good", "chaos_value": 50.0, "confidence": "low"},
        ]
        result = arbitrate_rows(rows)
        assert result["source"] == "good"


def test_arbitrate_rows_picks_high_confidence_over_medium():
    rows = [
        {"source": "A", "chaos_value": 100.0, "listing_count": 5, "confidence": "medium"},
        {"source": "B", "chaos_value": 98.0, "listing_count": 3, "confidence": "high"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_uses_listing_count_as_tiebreaker():
    rows = [
        {"source": "A", "chaos_value": 10.0, "listing_count": 2, "confidence": "medium"},
        {"source": "B", "chaos_value": 10.5, "listing_count": 10, "confidence": "medium"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_prefers_value_closer_to_median_when_counts_equal():
    # Median is 10.0; pick row closer to 10.0
    rows = [
        {"source": "A", "chaos_value": 8.0, "listing_count": 5, "confidence": "low"},
        {"source": "B", "chaos_value": 12.0, "listing_count": 5, "confidence": "low"},
        {"source": "C", "chaos_value": 10.1, "listing_count": 5, "confidence": "low"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "C"


def test_arbitrate_rows_uses_source_priority_last():
    rows = [
        {"source": "A", "chaos_value": 10.0, "listing_count": 5, "confidence": "medium"},
        {"source": "B", "chaos_value": 10.0, "listing_count": 5, "confidence": "medium"},
    ]
    chosen = arbitrate_rows(rows, source_priority=["B", "A"])  # prefer B
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_ignores_rows_without_numeric_value():
    rows = [
        {"source": "A", "chaos_value": None, "listing_count": 0, "confidence": "none"},
        {"source": "B", "chaos_value": 5.0, "listing_count": 1, "confidence": "low"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_returns_none_for_empty_or_unusable():
    assert arbitrate_rows([]) is None
    assert arbitrate_rows([{"source": "A", "chaos_value": None}]) is None
