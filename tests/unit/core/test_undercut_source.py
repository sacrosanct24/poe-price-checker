"""
Unit tests for core.derived_sources module - Derived pricing sources.

Tests cover:
- UndercutPriceSource initialization
- Undercut factor application
- Source name handling
- Empty input handling
- Multiple row processing
- Edge cases (zero values, missing fields, invalid values)
"""

import pytest

pytestmark = pytest.mark.unit

from typing import Any, Mapping

from core.derived_sources import UndercutPriceSource
from core.price_multi import RESULT_COLUMNS


class FakePriceService:
    """Mock price service for testing."""
    def __init__(self, rows: list[Mapping[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> list[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


# -------------------------
# Initialization Tests
# -------------------------

class TestUndercutPriceSourceInitialization:
    """Test UndercutPriceSource initialization."""

    def test_creates_source_with_defaults(self):
        """Should create source with default undercut factor."""
        fake_service = FakePriceService([])

        src = UndercutPriceSource(
            name="test_undercut",
            base_service=fake_service  # type: ignore[arg-type]
        )

        assert src.name == "test_undercut"
        assert src.undercut_factor == 0.9

    def test_creates_source_with_custom_factor(self):
        """Should create source with custom undercut factor."""
        fake_service = FakePriceService([])

        src = UndercutPriceSource(
            name="aggressive_undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.8
        )

        assert src.undercut_factor == 0.8


# -------------------------
# Basic Undercut Tests
# -------------------------

class TestBasicUndercutBehavior:
    """Test basic undercut price calculation."""

    def test_undercut_price_source_scales_values_and_sets_source(self):
        """Should apply undercut factor and set source name."""
        base_rows = [
            {
                "item_name": "Hat",
                "variant": "",
                "links": "",
                "chaos_value": 100.0,
                "divine_value": 0.5,
                "listing_count": 10,
                "source": "poe_ninja",
            }
        ]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="suggested_undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9,
        )

        rows = src.check_item("some item")

        assert fake_service.calls == ["some item"]
        assert len(rows) == 1
        row = rows[0]

        # All expected columns present
        for col in RESULT_COLUMNS:
            assert col in row

        assert row["source"] == "suggested_undercut"
        assert pytest.approx(row["chaos_value"], rel=1e-6) == 90.0
        assert pytest.approx(row["divine_value"], rel=1e-6) == 0.45

    def test_applies_undercut_to_multiple_rows(self):
        """Should apply undercut to all rows from base service."""
        base_rows = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"},
            {"chaos_value": 200.0, "divine_value": 2.0, "source": "poe_ninja"},
            {"chaos_value": 50.0, "divine_value": 0.5, "source": "poe_ninja"}
        ]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.85
        )

        rows = src.check_item("item")

        assert len(rows) == 3
        assert pytest.approx(rows[0]["chaos_value"]) == 85.0  # 100 * 0.85
        assert pytest.approx(rows[1]["chaos_value"]) == 170.0  # 200 * 0.85
        assert pytest.approx(rows[2]["chaos_value"]) == 42.5  # 50 * 0.85

    def test_custom_undercut_factor(self):
        """Should apply custom undercut factors correctly."""
        base_rows = [{"chaos_value": 100.0, "divine_value": 1.0}]

        # Test various undercut factors
        test_cases = [
            (0.95, 95.0, 0.95),  # Mild undercut
            (0.9, 90.0, 0.9),    # Default
            (0.8, 80.0, 0.8),    # Aggressive
            (0.5, 50.0, 0.5),    # Very aggressive
            (1.0, 100.0, 1.0),   # No undercut
        ]

        for factor, expected_chaos, expected_divine in test_cases:
            fake_service = FakePriceService(base_rows)
            src = UndercutPriceSource(
                name="test",
                base_service=fake_service,  # type: ignore[arg-type]
                undercut_factor=factor
            )

            rows = src.check_item("item")
            assert pytest.approx(rows[0]["chaos_value"]) == expected_chaos
            assert pytest.approx(rows[0]["divine_value"]) == expected_divine


# -------------------------
# Edge Case Tests
# -------------------------

class TestUndercutEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_item_text(self):
        """Should return empty list for empty item text."""
        fake_service = FakePriceService([{"chaos_value": 100}])
        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service  # type: ignore[arg-type]
        )

        rows = src.check_item("")
        assert rows == []

        rows = src.check_item("   ")  # Whitespace only
        assert rows == []

    def test_handles_none_item_text(self):
        """Should return empty list for None item text."""
        fake_service = FakePriceService([{"chaos_value": 100}])
        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service  # type: ignore[arg-type]
        )

        rows = src.check_item(None)  # type: ignore[arg-type]
        assert rows == []

    def test_handles_empty_base_service_results(self):
        """Should return empty list when base service returns nothing."""
        fake_service = FakePriceService([])  # No rows
        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service  # type: ignore[arg-type]
        )

        rows = src.check_item("item")
        assert rows == []

    def test_handles_zero_chaos_value(self):
        """Should handle zero chaos values."""
        base_rows = [{"chaos_value": 0.0, "divine_value": 0.0}]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")
        assert rows[0]["chaos_value"] == 0.0
        assert rows[0]["divine_value"] == 0.0

    def test_handles_missing_chaos_value(self):
        """Should handle missing chaos_value field."""
        base_rows = [{"item_name": "Test"}]  # No chaos_value
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")
        assert rows[0]["chaos_value"] == 0.0
        assert rows[0]["divine_value"] == 0.0

    def test_handles_invalid_chaos_value_types(self):
        """Should handle non-numeric chaos values."""
        base_rows = [
            {"chaos_value": "invalid", "divine_value": "also_invalid"}
        ]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")
        # Should default to 0.0 for invalid values
        assert rows[0]["chaos_value"] == 0.0
        assert rows[0]["divine_value"] == 0.0

    def test_handles_none_values(self):
        """Should handle None as chaos/divine values."""
        base_rows = [{"chaos_value": None, "divine_value": None}]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")
        assert rows[0]["chaos_value"] == 0.0
        assert rows[0]["divine_value"] == 0.0


# -------------------------
# Column Handling Tests
# -------------------------

class TestColumnHandling:
    """Test handling of expected columns."""

    def test_ensures_all_result_columns_present(self):
        """Should ensure all RESULT_COLUMNS are present in output."""
        base_rows = [{"chaos_value": 100}]  # Minimal row
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")

        # All expected columns should be present
        for col in RESULT_COLUMNS:
            assert col in rows[0], f"Missing column: {col}"

    def test_preserves_non_price_columns(self):
        """Should preserve non-price data from base service."""
        base_rows = [{
            "item_name": "Cool Ring",
            "variant": "Fire",
            "links": "6L",
            "chaos_value": 100.0,
            "divine_value": 1.0,
            "listing_count": 42,
            "source": "poe_ninja"
        }]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.9
        )

        rows = src.check_item("item")
        row = rows[0]

        # Non-price columns should be preserved
        assert row["item_name"] == "Cool Ring"
        assert row["variant"] == "Fire"
        assert row["links"] == "6L"
        assert row["listing_count"] == 42

        # Source should be overwritten
        assert row["source"] == "undercut"


# -------------------------
# Integration Tests
# -------------------------

class TestUndercutIntegration:
    """Test undercut source in realistic scenarios."""

    def test_realistic_pricing_scenario(self):
        """Should handle realistic pricing data."""
        base_rows = [
            {
                "item_name": "Shavronne's Wrappings",
                "variant": "",
                "links": "6L",
                "chaos_value": 8500.0,
                "divine_value": 27.4,
                "listing_count": 15,
                "source": "poe_ninja"
            }
        ]
        fake_service = FakePriceService(base_rows)

        src = UndercutPriceSource(
            name="suggested_undercut",
            base_service=fake_service,  # type: ignore[arg-type]
            undercut_factor=0.95  # Mild undercut
        )

        rows = src.check_item("Shavronne's Wrappings")
        row = rows[0]

        # Check undercut applied correctly
        assert pytest.approx(row["chaos_value"], rel=1e-6) == 8075.0  # 8500 * 0.95
        assert pytest.approx(row["divine_value"], rel=1e-6) == 26.03  # 27.4 * 0.95
        assert row["source"] == "suggested_undercut"
        assert row["item_name"] == "Shavronne's Wrappings"

    def test_calls_base_service_with_item_text(self):
        """Should pass item text to base service."""
        fake_service = FakePriceService([{"chaos_value": 100}])
        src = UndercutPriceSource(
            name="undercut",
            base_service=fake_service  # type: ignore[arg-type]
        )

        src.check_item("Tabula Rasa")
        assert fake_service.calls == ["Tabula Rasa"]

        src.check_item("Headhunter")
        assert fake_service.calls == ["Tabula Rasa", "Headhunter"]
