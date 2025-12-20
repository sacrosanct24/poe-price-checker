"""Tests for core/history.py - History entry management."""
from datetime import datetime
from unittest.mock import MagicMock


from core.history import HistoryEntry


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_create_basic_entry(self):
        """Should create basic history entry."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Headhunter",
            item_text="Headhunter\nLeather Belt",
        )

        assert entry.timestamp == "2025-01-01T12:00:00"
        assert entry.item_name == "Headhunter"
        assert entry.item_text == "Headhunter\nLeather Belt"
        assert entry.results_count == 0
        assert entry.best_price == 0.0
        assert entry.parsed_item is None

    def test_create_with_all_fields(self):
        """Should create entry with all fields."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Headhunter",
            item_text="Headhunter\nLeather Belt",
            results_count=5,
            best_price=150.0,
            parsed_item=MagicMock(),
        )

        assert entry.results_count == 5
        assert entry.best_price == 150.0
        assert entry.parsed_item is not None

    def test_from_price_check_basic(self):
        """Should create entry from price check results."""
        parsed = MagicMock()
        parsed.name = "Shavronne's Wrappings"

        results = [
            {"chaos_value": 100.0},
            {"chaos_value": 120.0},
            {"chaos_value": 90.0},
        ]

        entry = HistoryEntry.from_price_check(
            item_text="Test item text",
            parsed=parsed,
            results=results,
        )

        assert entry.item_name == "Shavronne's Wrappings"
        assert entry.item_text == "Test item text"
        assert entry.results_count == 3
        assert entry.best_price == 120.0  # Max chaos value
        assert entry.parsed_item is parsed

    def test_from_price_check_no_results(self):
        """Should handle empty results."""
        parsed = MagicMock()
        parsed.name = "Test Item"

        entry = HistoryEntry.from_price_check(
            item_text="Test text",
            parsed=parsed,
            results=[],
        )

        assert entry.results_count == 0
        assert entry.best_price == 0.0

    def test_from_price_check_none_chaos_values(self):
        """Should handle None chaos values safely."""
        parsed = MagicMock()
        parsed.name = "Test Item"

        results = [
            {"chaos_value": None},
            {"chaos_value": 50.0},
            {"chaos_value": None},
        ]

        entry = HistoryEntry.from_price_check(
            item_text="Test text",
            parsed=parsed,
            results=results,
        )

        assert entry.best_price == 50.0

    def test_from_price_check_invalid_chaos_values(self):
        """Should handle invalid chaos values safely."""
        parsed = MagicMock()
        parsed.name = "Test Item"

        results = [
            {"chaos_value": "invalid"},
            {"chaos_value": 75.0},
            {"chaos_value": "also invalid"},
        ]

        entry = HistoryEntry.from_price_check(
            item_text="Test text",
            parsed=parsed,
            results=results,
        )

        assert entry.best_price == 75.0

    def test_from_price_check_missing_chaos_value_key(self):
        """Should handle missing chaos_value key."""
        parsed = MagicMock()
        parsed.name = "Test Item"

        results = [
            {"price": 100.0},  # Wrong key
            {"chaos_value": 80.0},
            {},  # Missing key
        ]

        entry = HistoryEntry.from_price_check(
            item_text="Test text",
            parsed=parsed,
            results=results,
        )

        assert entry.best_price == 80.0

    def test_from_price_check_uses_item_text_when_no_name(self):
        """Should use item_text when parsed.name is empty."""
        parsed = MagicMock()
        parsed.name = None

        entry = HistoryEntry.from_price_check(
            item_text="Very long item text that should be truncated" * 5,
            parsed=parsed,
            results=[],
        )

        assert len(entry.item_name) == 50
        assert entry.item_name.startswith("Very long")

    def test_from_price_check_timestamp_is_recent(self):
        """Timestamp should be recent (within last second)."""
        parsed = MagicMock()
        parsed.name = "Test"

        entry = HistoryEntry.from_price_check(
            item_text="Test",
            parsed=parsed,
            results=[],
        )

        # Parse timestamp and check it's recent
        timestamp = datetime.fromisoformat(entry.timestamp)
        now = datetime.now()
        diff = (now - timestamp).total_seconds()
        assert diff < 1.0  # Should be less than 1 second old

    def test_to_dict(self):
        """Should convert to dict format."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Headhunter",
            item_text="Test text",
            results_count=3,
            best_price=150.0,
            parsed_item=MagicMock(),
        )

        result = entry.to_dict()

        assert result["timestamp"] == "2025-01-01T12:00:00"
        assert result["item_name"] == "Headhunter"
        assert result["item_text"] == "Test text"
        assert result["results_count"] == 3
        assert result["best_price"] == 150.0
        assert "_parsed" in result

    def test_to_dict_preserves_parsed_item_reference(self):
        """to_dict should preserve parsed_item reference."""
        parsed = MagicMock()
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
            parsed_item=parsed,
        )

        result = entry.to_dict()

        assert result["_parsed"] is parsed

    def test_get_method_basic_keys(self):
        """get() should access dataclass attributes."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Headhunter",
            item_text="Test text",
            results_count=5,
            best_price=100.0,
        )

        assert entry.get("timestamp") == "2025-01-01T12:00:00"
        assert entry.get("item_name") == "Headhunter"
        assert entry.get("results_count") == 5
        assert entry.get("best_price") == 100.0

    def test_get_method_mapped_key(self):
        """get() should map _parsed to parsed_item."""
        parsed = MagicMock()
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
            parsed_item=parsed,
        )

        assert entry.get("_parsed") is parsed

    def test_get_method_missing_key_returns_none(self):
        """get() should return None for missing key."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
        )

        assert entry.get("nonexistent") is None

    def test_get_method_missing_key_with_default(self):
        """get() should return default for missing key."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
        )

        assert entry.get("nonexistent", "default") == "default"

    def test_get_method_existing_key_ignores_default(self):
        """get() should return value even if default provided."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
            results_count=5,
        )

        assert entry.get("results_count", 999) == 5

    def test_safe_float_handles_none(self):
        """_safe_float should convert None to 0.0."""
        parsed = MagicMock()
        parsed.name = "Test"

        results = [{"chaos_value": None}]
        entry = HistoryEntry.from_price_check("test", parsed, results)

        assert entry.best_price == 0.0

    def test_safe_float_handles_string(self):
        """_safe_float should handle non-numeric strings."""
        parsed = MagicMock()
        parsed.name = "Test"

        results = [{"chaos_value": "not a number"}]
        entry = HistoryEntry.from_price_check("test", parsed, results)

        assert entry.best_price == 0.0

    def test_safe_float_handles_mixed_valid_invalid(self):
        """Should find max among mixed valid/invalid values."""
        parsed = MagicMock()
        parsed.name = "Test"

        results = [
            {"chaos_value": None},
            {"chaos_value": "invalid"},
            {"chaos_value": 42.5},
            {"chaos_value": 30.0},
            {"chaos_value": []},  # Invalid type
        ]

        entry = HistoryEntry.from_price_check("test", parsed, results)

        assert entry.best_price == 42.5

    def test_safe_float_handles_zero(self):
        """Zero should be valid chaos value."""
        parsed = MagicMock()
        parsed.name = "Test"

        results = [{"chaos_value": 0.0}]
        entry = HistoryEntry.from_price_check("test", parsed, results)

        assert entry.best_price == 0.0

    def test_safe_float_handles_negative(self):
        """Negative values should be handled (even if unusual)."""
        parsed = MagicMock()
        parsed.name = "Test"

        results = [{"chaos_value": -10.0}]
        entry = HistoryEntry.from_price_check("test", parsed, results)

        assert entry.best_price == -10.0

    def test_repr_excludes_parsed_item(self):
        """repr should exclude parsed_item (repr=False)."""
        parsed = MagicMock()
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Test",
            item_text="Test",
            parsed_item=parsed,
        )

        repr_str = repr(entry)

        # Should not contain the parsed_item
        assert "parsed_item" not in repr_str
        # Should contain other fields
        assert "Test" in repr_str
        assert "2025-01-01T12:00:00" in repr_str

    def test_item_name_truncation(self):
        """Item name should be truncated to 50 chars when using item_text."""
        parsed = MagicMock()
        parsed.name = None

        long_text = "x" * 100

        entry = HistoryEntry.from_price_check(long_text, parsed, [])

        assert len(entry.item_name) == 50
        assert entry.item_name == "x" * 50

    def test_backwards_compatibility_with_dict_access(self):
        """Should work like a dict for backwards compatibility."""
        entry = HistoryEntry(
            timestamp="2025-01-01T12:00:00",
            item_name="Headhunter",
            item_text="Test",
            results_count=3,
            best_price=150.0,
        )

        # Can use get() like dict
        assert entry.get("timestamp") == "2025-01-01T12:00:00"
        assert entry.get("nonexistent", "default") == "default"

        # Can convert to dict
        as_dict = entry.to_dict()
        assert isinstance(as_dict, dict)
        assert as_dict["item_name"] == "Headhunter"
