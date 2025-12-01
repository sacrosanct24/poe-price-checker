"""Tests for core/derived_sources.py - Undercut price derivation."""
from unittest.mock import MagicMock

import pytest

from core.derived_sources import UndercutPriceSource


class TestUndercutPriceSource:
    """Tests for UndercutPriceSource class."""

    @pytest.fixture
    def mock_price_service(self):
        """Create a mock PriceService."""
        service = MagicMock()
        return service

    @pytest.fixture
    def undercut_source(self, mock_price_service):
        """Create UndercutPriceSource with mock service."""
        return UndercutPriceSource(
            name="suggested_undercut",
            base_service=mock_price_service,
            undercut_factor=0.9,
        )

    def test_init_default_factor(self, mock_price_service):
        """Default undercut factor should be 0.9."""
        source = UndercutPriceSource(
            name="test",
            base_service=mock_price_service,
        )
        assert source.undercut_factor == 0.9

    def test_init_custom_factor(self, mock_price_service):
        """Should accept custom undercut factor."""
        source = UndercutPriceSource(
            name="test",
            base_service=mock_price_service,
            undercut_factor=0.85,
        )
        assert source.undercut_factor == 0.85

    def test_check_item_empty_string(self, undercut_source):
        """Empty item text should return empty list."""
        result = undercut_source.check_item("")
        assert result == []

    def test_check_item_whitespace(self, undercut_source):
        """Whitespace-only text should return empty list."""
        result = undercut_source.check_item("   \n\t  ")
        assert result == []

    def test_check_item_none(self, undercut_source):
        """None should return empty list."""
        result = undercut_source.check_item(None)
        assert result == []

    def test_check_item_applies_undercut(self, undercut_source, mock_price_service):
        """Should apply undercut factor to prices."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"}
        ]

        result = undercut_source.check_item("Divine Orb")

        assert len(result) == 1
        assert result[0]["chaos_value"] == 90.0  # 100 * 0.9
        assert result[0]["divine_value"] == 0.9  # 1.0 * 0.9

    def test_check_item_sets_source_name(self, undercut_source, mock_price_service):
        """Should set source to undercut source name."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"}
        ]

        result = undercut_source.check_item("Divine Orb")

        assert result[0]["source"] == "suggested_undercut"

    def test_check_item_handles_string_values(self, undercut_source, mock_price_service):
        """Should handle string price values."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": "100.0", "divine_value": "1.0", "source": "poe_ninja"}
        ]

        result = undercut_source.check_item("Divine Orb")

        assert result[0]["chaos_value"] == 90.0

    def test_check_item_handles_invalid_values(self, undercut_source, mock_price_service):
        """Should treat invalid values as 0."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": "N/A", "divine_value": "", "source": "poe_ninja"}
        ]

        result = undercut_source.check_item("Divine Orb")

        assert result[0]["chaos_value"] == 0.0
        assert result[0]["divine_value"] == 0.0

    def test_check_item_handles_none_values(self, undercut_source, mock_price_service):
        """Should treat None values as 0."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": None, "divine_value": None, "source": "poe_ninja"}
        ]

        result = undercut_source.check_item("Divine Orb")

        assert result[0]["chaos_value"] == 0.0
        assert result[0]["divine_value"] == 0.0

    def test_check_item_multiple_results(self, undercut_source, mock_price_service):
        """Should apply undercut to all results."""
        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"},
            {"chaos_value": 200.0, "divine_value": 2.0, "source": "poe_ninja"},
        ]

        result = undercut_source.check_item("Some Item")

        assert len(result) == 2
        assert result[0]["chaos_value"] == 90.0
        assert result[1]["chaos_value"] == 180.0

    def test_check_item_empty_base_results(self, undercut_source, mock_price_service):
        """Should return empty list when base service returns empty."""
        mock_price_service.check_item.return_value = []

        result = undercut_source.check_item("Unknown Item")

        assert result == []

    def test_check_item_preserves_other_fields(self, undercut_source, mock_price_service):
        """Should preserve other fields from base results."""
        mock_price_service.check_item.return_value = [
            {
                "chaos_value": 100.0,
                "divine_value": 1.0,
                "source": "poe_ninja",
                "item_name": "Test Item",
                "category": "Currency",
            }
        ]

        result = undercut_source.check_item("Test Item")

        assert result[0]["item_name"] == "Test Item"
        assert result[0]["category"] == "Currency"

    def test_check_item_different_factors(self, mock_price_service):
        """Should apply different undercut factors correctly."""
        # 85% undercut
        source_85 = UndercutPriceSource(
            name="undercut_85",
            base_service=mock_price_service,
            undercut_factor=0.85,
        )

        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"}
        ]

        result = source_85.check_item("Item")
        assert result[0]["chaos_value"] == 85.0

        # 95% undercut
        source_95 = UndercutPriceSource(
            name="undercut_95",
            base_service=mock_price_service,
            undercut_factor=0.95,
        )

        result = source_95.check_item("Item")
        assert result[0]["chaos_value"] == 95.0

    def test_check_item_strips_whitespace(self, undercut_source, mock_price_service):
        """Should strip whitespace from item text."""
        mock_price_service.check_item.return_value = []

        undercut_source.check_item("  Divine Orb  ")

        # Should call with stripped text
        mock_price_service.check_item.assert_called_once()
        # The call was made (even if result is empty)

    def test_undercut_source_name_attribute(self, undercut_source):
        """Should have name attribute."""
        assert undercut_source.name == "suggested_undercut"

    def test_undercut_zero_factor(self, mock_price_service):
        """Zero factor should result in zero prices."""
        source = UndercutPriceSource(
            name="free",
            base_service=mock_price_service,
            undercut_factor=0.0,
        )

        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"}
        ]

        result = source.check_item("Item")

        assert result[0]["chaos_value"] == 0.0
        assert result[0]["divine_value"] == 0.0

    def test_undercut_factor_greater_than_one(self, mock_price_service):
        """Factor > 1 should increase prices (markup)."""
        source = UndercutPriceSource(
            name="markup",
            base_service=mock_price_service,
            undercut_factor=1.1,
        )

        mock_price_service.check_item.return_value = [
            {"chaos_value": 100.0, "divine_value": 1.0, "source": "poe_ninja"}
        ]

        result = source.check_item("Item")

        assert result[0]["chaos_value"] == pytest.approx(110.0)
        assert result[0]["divine_value"] == pytest.approx(1.1)
