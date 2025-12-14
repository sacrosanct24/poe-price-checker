"""
Tests for ChartDataService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from core.services.chart_data_service import (
    ChartDataService,
    ChartSeries,
    PriceDataPoint,
)


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock()
    db.conn = Mock()
    return db


@pytest.fixture
def service(mock_db):
    """Create a ChartDataService instance."""
    return ChartDataService(mock_db)


class TestPriceDataPoint:
    """Tests for PriceDataPoint dataclass."""

    def test_create_with_all_fields(self):
        """Test creating a data point with all fields."""
        now = datetime.now()
        point = PriceDataPoint(
            date=now,
            chaos_value=100.5,
            divine_value=0.5
        )
        assert point.date == now
        assert point.chaos_value == 100.5
        assert point.divine_value == 0.5

    def test_create_without_divine(self):
        """Test creating a data point without divine value."""
        now = datetime.now()
        point = PriceDataPoint(date=now, chaos_value=50.0)
        assert point.divine_value is None


class TestChartSeries:
    """Tests for ChartSeries dataclass."""

    def test_empty_series(self):
        """Test empty series properties."""
        series = ChartSeries(name="Test", data_points=[])
        assert series.dates == []
        assert series.chaos_values == []
        assert series.divine_values == []

    def test_series_with_data(self):
        """Test series with data points."""
        now = datetime.now()
        points = [
            PriceDataPoint(date=now, chaos_value=100.0, divine_value=0.5),
            PriceDataPoint(date=now + timedelta(days=1), chaos_value=110.0),
        ]
        series = ChartSeries(name="Test Item", data_points=points)

        assert len(series.dates) == 2
        assert len(series.chaos_values) == 2
        assert series.chaos_values[0] == 100.0
        assert series.chaos_values[1] == 110.0
        assert series.divine_values[0] == 0.5
        assert series.divine_values[1] is None


class TestChartDataService:
    """Tests for ChartDataService."""

    def test_init(self, service, mock_db):
        """Test service initialization."""
        assert service.db is mock_db

    def test_get_item_price_series_with_data(self, service, mock_db):
        """Test getting item price series when data exists."""
        # Mock database response
        now = datetime.now()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            (now.isoformat(), 100.0, 0.5),
            ((now + timedelta(days=1)).isoformat(), 110.0, 0.55),
        ]

        series = service.get_item_price_series("Test Item", "Settlers", days=30)

        assert series is not None
        assert series.name == "Test Item"
        assert len(series.data_points) == 2
        assert series.chaos_values[0] == 100.0
        assert series.chaos_values[1] == 110.0

    def test_get_item_price_series_no_data(self, service, mock_db):
        """Test getting item price series when no data exists."""
        mock_db.conn.execute.return_value.fetchall.return_value = []

        series = service.get_item_price_series("Unknown Item", "Settlers")

        assert series is None

    def test_get_item_price_series_error(self, service, mock_db):
        """Test handling errors in get_item_price_series."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        series = service.get_item_price_series("Test Item", "Settlers")

        assert series is None

    def test_get_currency_rate_series_divine(self, service, mock_db):
        """Test getting Divine Orb rate series."""
        now = datetime.now()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            (now.isoformat(), 200.0),
            ((now + timedelta(days=1)).isoformat(), 210.0),
        ]

        series = service.get_currency_rate_series("Divine Orb", "Settlers", days=30)

        assert series is not None
        assert series.name == "Divine Orb"
        assert len(series.data_points) == 2

    def test_get_currency_rate_series_exalt(self, service, mock_db):
        """Test getting Exalted Orb rate series."""
        now = datetime.now()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            (now.isoformat(), 15.0),
        ]

        series = service.get_currency_rate_series("Exalted Orb", "Settlers", days=7)

        assert series is not None
        assert series.name == "Exalted Orb"

    def test_get_currency_rate_series_unknown_currency(self, service, mock_db):
        """Test getting rate series for unknown currency falls back to economy rates."""
        now = datetime.now()
        mock_db.conn.execute.return_value.fetchall.return_value = [
            ("2024-01-01", 5.0),
        ]

        series = service.get_currency_rate_series("Orb of Fusing", "Settlers", days=30)

        # Should attempt to get from economy rates table
        assert mock_db.conn.execute.called

    def test_get_available_currencies(self, service, mock_db):
        """Test getting available currencies for a league."""
        mock_db.conn.execute.return_value.fetchall.return_value = [
            ("Divine Orb",),
            ("Exalted Orb",),
            ("Chaos Orb",),
        ]

        currencies = service.get_available_currencies("Settlers")

        assert len(currencies) == 3
        assert "Divine Orb" in currencies

    def test_get_available_currencies_error(self, service, mock_db):
        """Test handling errors in get_available_currencies."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        currencies = service.get_available_currencies("Settlers")

        assert currencies == []

    def test_get_available_items(self, service, mock_db):
        """Test getting available items for a league."""
        mock_db.conn.execute.return_value.fetchall.return_value = [
            ("Mageblood",),
            ("Headhunter",),
        ]

        items = service.get_available_items("Settlers", limit=100)

        assert len(items) == 2
        assert "Mageblood" in items

    def test_get_available_items_error(self, service, mock_db):
        """Test handling errors in get_available_items."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        items = service.get_available_items("Settlers")

        assert items == []

    def test_get_item_from_economy_items(self, service, mock_db):
        """Test getting item data from economy items table."""
        mock_db.conn.execute.return_value.fetchall.return_value = [
            ("2024-01-01", 50000.0, 250.0),
            ("2024-01-02", 51000.0, 255.0),
        ]

        series = service.get_item_from_economy_items("Mageblood", "Settlers", days=30)

        assert series is not None
        assert series.name == "Mageblood"
        assert len(series.data_points) == 2

    def test_get_item_from_economy_items_fallback(self, service, mock_db):
        """Test fallback to price_history when economy_items has no data."""
        # First call (economy_items) returns empty
        # Second call (price_history) returns data
        mock_db.conn.execute.return_value.fetchall.side_effect = [
            [],  # economy_items empty
            [("2024-01-01T00:00:00", 100.0, 0.5)],  # price_history has data
        ]

        series = service.get_item_from_economy_items("Some Item", "Settlers")

        # Should have called execute twice
        assert mock_db.conn.execute.call_count == 2

    def test_time_range_all_time(self, service, mock_db):
        """Test querying with days=0 (all time)."""
        mock_db.conn.execute.return_value.fetchall.return_value = []

        service.get_item_price_series("Test", "League", days=0)

        # Should not include date filter in query
        call_args = mock_db.conn.execute.call_args
        query = call_args[0][0]
        assert "recorded_at >=" not in query

    def test_get_currency_rate_series_empty_returns_none(self, service, mock_db):
        """Test get_currency_rate_series returns None for empty data."""
        mock_db.conn.execute.return_value.fetchall.return_value = []

        series = service.get_currency_rate_series("Divine Orb", "Settlers", days=30)

        assert series is None

    def test_get_currency_rate_series_with_string_date(self, service, mock_db):
        """Test handling string dates from database."""
        mock_db.conn.execute.return_value.fetchall.return_value = [
            ("2024-01-15T12:00:00", 200.0),
        ]

        series = service.get_currency_rate_series("Divine Orb", "Settlers", days=30)

        assert series is not None
        assert len(series.data_points) == 1

    def test_get_currency_rate_series_error(self, service, mock_db):
        """Test error handling in get_currency_rate_series."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        series = service.get_currency_rate_series("Divine Orb", "Settlers")

        assert series is None

    def test_get_item_from_economy_items_error(self, service, mock_db):
        """Test error handling in get_item_from_economy_items."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        series = service.get_item_from_economy_items("Test Item", "Settlers")

        assert series is None

    def test_get_item_from_economy_items_empty_returns_none(self, service, mock_db):
        """Test get_item_from_economy_items returns None for empty data."""
        # Both queries return empty
        mock_db.conn.execute.return_value.fetchall.side_effect = [
            [],  # economy_items empty
            [],  # price_history also empty
        ]

        series = service.get_item_from_economy_items("Unknown Item", "Settlers")

        assert series is None
