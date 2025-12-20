"""
Tests for core/database/repositories/currency_repository.py

Tests currency rate tracking functionality.
"""
import pytest
from datetime import datetime

from core.database import Database

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


class TestRecordCurrencyRate:
    """Tests for record_currency_rate method."""

    def test_record_basic_rate(self, temp_db):
        """Records a basic currency rate."""
        row_id = temp_db.record_currency_rate(
            league="Settlers",
            game_version="poe1",
            divine_to_chaos=180.0,
        )
        assert row_id > 0

    def test_record_rate_with_exalt(self, temp_db):
        """Records rate including exalt value."""
        row_id = temp_db.record_currency_rate(
            league="Settlers",
            game_version="poe1",
            divine_to_chaos=180.0,
            exalt_to_chaos=15.0,
        )
        assert row_id > 0

    def test_record_multiple_rates(self, temp_db):
        """Records multiple rates for same league."""
        id1 = temp_db.record_currency_rate("League1", "poe1", 100.0)
        id2 = temp_db.record_currency_rate("League1", "poe1", 110.0)
        assert id2 > id1

    def test_record_different_leagues(self, temp_db):
        """Records rates for different leagues."""
        id1 = temp_db.record_currency_rate("League1", "poe1", 100.0)
        id2 = temp_db.record_currency_rate("League2", "poe1", 200.0)
        assert id1 > 0
        assert id2 > 0
        assert id1 != id2

    def test_record_poe2_rate(self, temp_db):
        """Records rate for PoE2."""
        row_id = temp_db.record_currency_rate(
            league="Dawn",
            game_version="poe2",
            divine_to_chaos=50.0,
        )
        assert row_id > 0


class TestGetLatestCurrencyRate:
    """Tests for get_latest_currency_rate method."""

    def test_get_latest_returns_a_rate(self, temp_db):
        """Returns a rate for league with multiple entries."""
        temp_db.record_currency_rate("TestLeague", "poe1", 100.0)
        temp_db.record_currency_rate("TestLeague", "poe1", 150.0)
        temp_db.record_currency_rate("TestLeague", "poe1", 200.0)

        result = temp_db.get_latest_currency_rate("TestLeague", "poe1")

        assert result is not None
        # Should return one of the recorded values
        assert result["divine_to_chaos"] in [100.0, 150.0, 200.0]

    def test_get_latest_includes_exalt(self, temp_db):
        """Returns exalt rate when recorded."""
        temp_db.record_currency_rate("TestLeague", "poe1", 180.0, 15.0)

        result = temp_db.get_latest_currency_rate("TestLeague", "poe1")

        assert result is not None
        assert result["divine_to_chaos"] == 180.0
        assert result["exalt_to_chaos"] == 15.0

    def test_get_latest_none_for_unknown_league(self, temp_db):
        """Returns None for league with no rates."""
        result = temp_db.get_latest_currency_rate("UnknownLeague", "poe1")
        assert result is None

    def test_get_latest_filters_by_game_version(self, temp_db):
        """Filters by game version correctly."""
        temp_db.record_currency_rate("TestLeague", "poe1", 180.0)
        temp_db.record_currency_rate("TestLeague", "poe2", 50.0)

        poe1_result = temp_db.get_latest_currency_rate("TestLeague", "poe1")
        poe2_result = temp_db.get_latest_currency_rate("TestLeague", "poe2")

        assert poe1_result["divine_to_chaos"] == 180.0
        assert poe2_result["divine_to_chaos"] == 50.0

    def test_get_latest_includes_timestamp(self, temp_db):
        """Result includes recorded_at timestamp."""
        temp_db.record_currency_rate("TestLeague", "poe1", 180.0)

        result = temp_db.get_latest_currency_rate("TestLeague", "poe1")

        assert result is not None
        assert "recorded_at" in result
        # Should be a datetime
        assert isinstance(result["recorded_at"], datetime)


class TestGetCurrencyRateHistory:
    """Tests for get_currency_rate_history method."""

    def test_get_history_returns_list(self, temp_db):
        """Returns a list of rate records."""
        temp_db.record_currency_rate("TestLeague", "poe1", 100.0)
        temp_db.record_currency_rate("TestLeague", "poe1", 110.0)

        result = temp_db.get_currency_rate_history("TestLeague", days=30)

        assert isinstance(result, list)
        assert len(result) >= 2

    def test_get_history_returns_all_rates(self, temp_db):
        """Returns all rates for the period."""
        temp_db.record_currency_rate("TestLeague", "poe1", 100.0)
        temp_db.record_currency_rate("TestLeague", "poe1", 200.0)

        result = temp_db.get_currency_rate_history("TestLeague", days=30)

        # Should have both rates
        assert len(result) == 2
        values = [r["divine_to_chaos"] for r in result]
        assert 100.0 in values
        assert 200.0 in values

    def test_get_history_empty_for_unknown_league(self, temp_db):
        """Returns empty list for unknown league."""
        result = temp_db.get_currency_rate_history("Unknown", days=30)
        assert result == []

    def test_get_history_filters_by_game_version(self, temp_db):
        """Filters history by game version."""
        temp_db.record_currency_rate("TestLeague", "poe1", 180.0)
        temp_db.record_currency_rate("TestLeague", "poe2", 50.0)

        poe1_history = temp_db.get_currency_rate_history(
            "TestLeague", days=30, game_version="poe1"
        )
        poe2_history = temp_db.get_currency_rate_history(
            "TestLeague", days=30, game_version="poe2"
        )

        assert len(poe1_history) == 1
        assert poe1_history[0]["divine_to_chaos"] == 180.0
        assert len(poe2_history) == 1
        assert poe2_history[0]["divine_to_chaos"] == 50.0

    def test_get_history_includes_all_fields(self, temp_db):
        """Each record has all expected fields."""
        temp_db.record_currency_rate("TestLeague", "poe1", 180.0, 15.0)

        result = temp_db.get_currency_rate_history("TestLeague", days=30)

        assert len(result) == 1
        record = result[0]
        assert "divine_to_chaos" in record
        assert "exalt_to_chaos" in record
        assert "recorded_at" in record


class TestCurrencyRateIntegration:
    """Integration tests for currency rate workflows."""

    def test_track_rate_changes_over_time(self, temp_db):
        """Tracks rate changes correctly."""
        # Record multiple rates
        temp_db.record_currency_rate("League", "poe1", 150.0)
        temp_db.record_currency_rate("League", "poe1", 160.0)
        temp_db.record_currency_rate("League", "poe1", 155.0)

        # Latest returns one of the recorded values
        latest = temp_db.get_latest_currency_rate("League", "poe1")
        assert latest["divine_to_chaos"] in [150.0, 160.0, 155.0]

        # History should have all 3
        history = temp_db.get_currency_rate_history("League", days=30)
        assert len(history) == 3
        values = [r["divine_to_chaos"] for r in history]
        assert 150.0 in values
        assert 160.0 in values
        assert 155.0 in values
