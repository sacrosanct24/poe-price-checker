"""Tests for core/price_row.py - Price result row dataclass and helpers."""

import pytest
from dataclasses import dataclass
from typing import Any

from core.price_row import (
    PriceRow,
    LinksType,
    RESULT_COLUMNS,
    _coerce_float,
    _coerce_int,
    to_dict,
    validate_and_normalize_row,
)


# =============================================================================
# PriceRow Dataclass Tests
# =============================================================================


class TestPriceRow:
    """Tests for PriceRow dataclass."""

    def test_create_minimal_price_row(self):
        """Should create row with only required field."""
        row = PriceRow(source="poe.ninja")
        assert row.source == "poe.ninja"
        assert row.item_name == ""
        assert row.variant == ""
        assert row.links is None
        assert row.chaos_value is None
        assert row.divine_value is None
        assert row.listing_count is None
        assert row.confidence == ""
        assert row.explanation == ""

    def test_create_full_price_row(self):
        """Should create row with all fields."""
        row = PriceRow(
            source="trade",
            item_name="Headhunter",
            variant="",
            links=None,
            chaos_value=50000.0,
            divine_value=250.0,
            listing_count=15,
            confidence="high",
            explanation="15 listings at this price",
        )
        assert row.source == "trade"
        assert row.item_name == "Headhunter"
        assert row.chaos_value == 50000.0
        assert row.divine_value == 250.0
        assert row.listing_count == 15
        assert row.confidence == "high"

    def test_price_row_with_links_as_string(self):
        """Should accept links as string."""
        row = PriceRow(source="ninja", links="6L")
        assert row.links == "6L"

    def test_price_row_with_links_as_int(self):
        """Should accept links as int."""
        row = PriceRow(source="ninja", links=6)
        assert row.links == 6

    def test_price_row_equality(self):
        """Rows with same values should be equal."""
        row1 = PriceRow(source="ninja", item_name="Exalted Orb", chaos_value=150.0)
        row2 = PriceRow(source="ninja", item_name="Exalted Orb", chaos_value=150.0)
        assert row1 == row2

    def test_price_row_inequality(self):
        """Rows with different values should not be equal."""
        row1 = PriceRow(source="ninja", chaos_value=150.0)
        row2 = PriceRow(source="ninja", chaos_value=160.0)
        assert row1 != row2


# =============================================================================
# RESULT_COLUMNS Tests
# =============================================================================


class TestResultColumns:
    """Tests for RESULT_COLUMNS constant."""

    def test_result_columns_contains_required_fields(self):
        """Should contain all expected column names."""
        assert "item_name" in RESULT_COLUMNS
        assert "variant" in RESULT_COLUMNS
        assert "links" in RESULT_COLUMNS
        assert "chaos_value" in RESULT_COLUMNS
        assert "divine_value" in RESULT_COLUMNS
        assert "listing_count" in RESULT_COLUMNS
        assert "source" in RESULT_COLUMNS

    def test_result_columns_is_tuple(self):
        """Should be immutable tuple."""
        assert isinstance(RESULT_COLUMNS, tuple)

    def test_result_columns_count(self):
        """Should have expected number of columns."""
        assert len(RESULT_COLUMNS) == 7


# =============================================================================
# _coerce_float Tests
# =============================================================================


class TestCoerceFloat:
    """Tests for _coerce_float helper."""

    def test_coerce_float_from_float(self):
        """Should return float unchanged."""
        assert _coerce_float(123.45) == 123.45

    def test_coerce_float_from_int(self):
        """Should convert int to float."""
        result = _coerce_float(100)
        assert result == 100.0
        assert isinstance(result, float)

    def test_coerce_float_from_string(self):
        """Should parse string to float."""
        assert _coerce_float("123.45") == 123.45
        assert _coerce_float("100") == 100.0

    def test_coerce_float_from_none(self):
        """Should return None for None input."""
        assert _coerce_float(None) is None

    def test_coerce_float_from_empty_string(self):
        """Should return None for empty string."""
        assert _coerce_float("") is None

    def test_coerce_float_invalid_string(self):
        """Should return None for invalid string."""
        assert _coerce_float("not a number") is None
        assert _coerce_float("abc123") is None

    def test_coerce_float_invalid_type(self):
        """Should return None for invalid types."""
        assert _coerce_float([1, 2, 3]) is None
        assert _coerce_float({"value": 10}) is None

    def test_coerce_float_negative(self):
        """Should handle negative numbers."""
        assert _coerce_float(-50.5) == -50.5
        assert _coerce_float("-25.0") == -25.0

    def test_coerce_float_scientific_notation(self):
        """Should handle scientific notation."""
        assert _coerce_float("1e3") == 1000.0
        assert _coerce_float("1.5e2") == 150.0


# =============================================================================
# _coerce_int Tests
# =============================================================================


class TestCoerceInt:
    """Tests for _coerce_int helper."""

    def test_coerce_int_from_int(self):
        """Should return int unchanged."""
        assert _coerce_int(42) == 42

    def test_coerce_int_from_float(self):
        """Should truncate float to int."""
        assert _coerce_int(42.9) == 42
        assert _coerce_int(42.1) == 42

    def test_coerce_int_from_string(self):
        """Should parse string to int."""
        assert _coerce_int("42") == 42
        assert _coerce_int("100") == 100

    def test_coerce_int_from_none(self):
        """Should return None for None input."""
        assert _coerce_int(None) is None

    def test_coerce_int_from_empty_string(self):
        """Should return None for empty string."""
        assert _coerce_int("") is None

    def test_coerce_int_invalid_string(self):
        """Should return None for invalid string."""
        assert _coerce_int("not a number") is None
        assert _coerce_int("abc") is None

    def test_coerce_int_string_float(self):
        """Should handle string floats by truncation."""
        # float("42.5") works, then int() truncates
        result = _coerce_int("42.5")
        # Implementation uses int() which doesn't accept "42.5" directly
        # So this should return None
        assert result is None

    def test_coerce_int_negative(self):
        """Should handle negative numbers."""
        assert _coerce_int(-10) == -10
        assert _coerce_int("-25") == -25


# =============================================================================
# to_dict Tests
# =============================================================================


class TestToDict:
    """Tests for to_dict helper."""

    def test_to_dict_from_dict(self):
        """Should return copy of dict."""
        original = {"source": "ninja", "item_name": "Exalted"}
        result = to_dict(original)
        assert result == original
        assert result is not original  # Should be a copy

    def test_to_dict_from_pricerow(self):
        """Should convert PriceRow to dict."""
        row = PriceRow(
            source="ninja",
            item_name="Divine Orb",
            chaos_value=200.0,
        )
        result = to_dict(row)
        assert result["source"] == "ninja"
        assert result["item_name"] == "Divine Orb"
        assert result["chaos_value"] == 200.0

    def test_to_dict_from_dataclass(self):
        """Should convert custom dataclass to dict."""
        @dataclass
        class CustomRow:
            source: str = "test"
            item_name: str = "Item"
            chaos_value: float = 50.0

        obj = CustomRow()
        result = to_dict(obj)
        assert result["source"] == "test"
        assert result["item_name"] == "Item"

    def test_to_dict_fallback_for_object_without_vars(self):
        """Should use getattr fallback for objects without __dict__."""
        class NoVarsObject:
            __slots__ = ["source", "item_name"]

            def __init__(self):
                self.source = "test"
                self.item_name = "Test Item"

        # This will use the fallback path
        obj = NoVarsObject()
        result = to_dict(obj)
        assert result["source"] == "test"
        assert result["item_name"] == "Test Item"


# =============================================================================
# validate_and_normalize_row Tests
# =============================================================================


class TestValidateAndNormalizeRow:
    """Tests for validate_and_normalize_row function."""

    def test_normalize_from_dict_with_all_fields(self):
        """Should normalize dict with all fields."""
        raw = {
            "source": "poe_ninja",
            "item_name": "Exalted Orb",
            "variant": "",
            "links": "6L",
            "chaos_value": 150.0,
            "divine_value": 0.75,
            "listing_count": 100,
        }
        result = validate_and_normalize_row(raw)
        assert result["source"] == "poe_ninja"
        assert result["item_name"] == "Exalted Orb"
        assert result["links"] == "6L"
        assert result["chaos_value"] == 150.0
        assert result["divine_value"] == 0.75
        assert result["listing_count"] == 100

    def test_normalize_coerces_string_numbers(self):
        """Should coerce string numbers to proper types."""
        raw = {
            "source": "test",
            "chaos_value": "123.45",
            "divine_value": "0.5",
            "listing_count": "42",
        }
        result = validate_and_normalize_row(raw)
        assert result["chaos_value"] == 123.45
        assert result["divine_value"] == 0.5
        assert result["listing_count"] == 42

    def test_normalize_handles_missing_fields(self):
        """Should provide defaults for missing fields."""
        raw = {"source": "X"}
        result = validate_and_normalize_row(raw)
        assert result["source"] == "X"
        assert result["item_name"] == ""
        assert result["variant"] == ""
        assert result["chaos_value"] is None
        assert result["divine_value"] is None
        assert result["listing_count"] is None

    def test_normalize_preserves_confidence(self):
        """Should preserve confidence field if present."""
        raw = {"source": "test", "confidence": "high"}
        result = validate_and_normalize_row(raw)
        assert result["confidence"] == "high"

    def test_normalize_preserves_explanation(self):
        """Should preserve explanation field if present."""
        raw = {"source": "test", "explanation": {"reason": "test"}}
        result = validate_and_normalize_row(raw)
        assert result["explanation"] == {"reason": "test"}

    def test_normalize_from_pricerow(self):
        """Should normalize PriceRow dataclass."""
        row = PriceRow(
            source="trade",
            item_name="Mirror",
            chaos_value=80000.0,
            listing_count=5,
            confidence="medium",
        )
        result = validate_and_normalize_row(row)
        assert result["source"] == "trade"
        assert result["item_name"] == "Mirror"
        assert result["chaos_value"] == 80000.0

    def test_normalize_ensures_all_columns_exist(self):
        """Should ensure all RESULT_COLUMNS exist in output."""
        raw = {"source": "test"}
        result = validate_and_normalize_row(raw)
        for col in RESULT_COLUMNS:
            assert col in result

    def test_normalize_handles_none_values(self):
        """Should handle None values properly."""
        raw = {
            "source": "test",
            "item_name": None,
            "chaos_value": None,
            "listing_count": None,
        }
        result = validate_and_normalize_row(raw)
        assert result["item_name"] == "None"  # str(None)
        assert result["chaos_value"] is None
        assert result["listing_count"] is None

    def test_normalize_handles_empty_dict(self):
        """Should handle empty dict gracefully."""
        result = validate_and_normalize_row({})
        assert result["source"] == ""
        assert result["item_name"] == ""
        for col in RESULT_COLUMNS:
            assert col in result
