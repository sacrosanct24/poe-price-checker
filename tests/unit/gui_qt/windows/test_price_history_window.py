"""Tests for PriceHistoryWindow."""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt

from gui_qt.windows.price_history_window import (
    PriceHistoryWindow,
    CurrencySummaryModel,
    TopItemsModel,
    TRACKED_CURRENCIES,
    CURRENCY_SHORT_NAMES,
)


# =============================================================================
# CurrencySummaryModel Tests
# =============================================================================


class TestCurrencySummaryModelBasics:
    """Basic tests for CurrencySummaryModel."""

    def test_init_empty(self, qtbot):
        """Model initializes with empty data."""
        model = CurrencySummaryModel()
        assert model.rowCount() == 0
        assert model.columnCount() == len(CurrencySummaryModel.COLUMNS)

    def test_set_data(self, qtbot):
        """Can set data and row count updates."""
        model = CurrencySummaryModel()
        data = [
            {"currency_name": "Divine Orb", "avg_value": 150.5},
            {"currency_name": "Exalted Orb", "avg_value": 40.2},
        ]
        model.set_data(data)
        assert model.rowCount() == 2

    def test_column_headers(self, qtbot):
        """Column headers are correct."""
        model = CurrencySummaryModel()
        for i, (_, header, _) in enumerate(CurrencySummaryModel.COLUMNS):
            assert model.headerData(i, Qt.Orientation.Horizontal) == header


class TestCurrencySummaryModelDisplayRole:
    """Tests for CurrencySummaryModel display formatting."""

    @pytest.fixture
    def model_with_data(self):
        """Create model with test data."""
        model = CurrencySummaryModel()
        model.set_data([
            {
                "currency_name": "Divine Orb",
                "currency": "Divine Orb",
                "avg_value": 150.5,
                "min_value": 120.0,
                "max_value": 180.0,
                "start_value": 130.0,
                "end_value": 160.0,
                "data_points": 90,
            },
        ])
        return model

    def test_currency_shows_short_name(self, model_with_data):
        """Currency column shows short name."""
        index = model_with_data.index(0, 0)  # currency column
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "Divine"

    def test_numeric_large_value_formatting(self, model_with_data):
        """Large values use comma formatting."""
        # Add a row with large value
        model_with_data.set_data([
            {"currency_name": "Test", "avg_value": 1500.0},
        ])
        index = model_with_data.index(0, 1)  # avg_value column
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "1,500"

    def test_numeric_medium_value_formatting(self, model_with_data):
        """Medium values show 1 decimal place."""
        index = model_with_data.index(0, 1)  # avg_value column
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "150.5"

    def test_numeric_small_value_formatting(self):
        """Small values show 2 decimal places."""
        model = CurrencySummaryModel()
        model.set_data([{"currency_name": "Test", "avg_value": 5.55}])
        index = model.index(0, 1)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "5.55"

    def test_data_points_column(self, model_with_data):
        """Data points column shows integer."""
        index = model_with_data.index(0, 6)  # data_points column
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "90"

    def test_invalid_value_shows_dash(self):
        """Invalid numeric values show dash."""
        model = CurrencySummaryModel()
        model.set_data([{"currency_name": "Test", "avg_value": "invalid"}])
        index = model.index(0, 1)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "-"


class TestCurrencySummaryModelAlignment:
    """Tests for CurrencySummaryModel alignment."""

    def test_currency_column_left_aligned(self):
        """Currency column has no special alignment (left)."""
        model = CurrencySummaryModel()
        model.set_data([{"currency_name": "Test"}])
        index = model.index(0, 0)
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert alignment is None  # Default left alignment

    def test_numeric_columns_right_aligned(self):
        """Numeric columns are right aligned."""
        model = CurrencySummaryModel()
        model.set_data([{"currency_name": "Test", "avg_value": 100}])
        index = model.index(0, 1)  # avg_value column
        alignment = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert alignment == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


# =============================================================================
# TopItemsModel Tests
# =============================================================================


class TestTopItemsModelBasics:
    """Basic tests for TopItemsModel."""

    def test_init_empty(self, qtbot):
        """Model initializes with empty data."""
        model = TopItemsModel()
        assert model.rowCount() == 0
        assert model.columnCount() == len(TopItemsModel.COLUMNS)

    def test_set_data(self):
        """Can set data and row count updates."""
        model = TopItemsModel()
        data = [
            {"rank": 1, "item_name": "Mageblood", "avg_value": 50000},
            {"rank": 2, "item_name": "Headhunter", "avg_value": 30000},
        ]
        model.set_data(data)
        assert model.rowCount() == 2

    def test_column_headers(self):
        """Column headers are correct."""
        model = TopItemsModel()
        for i, (_, header, _) in enumerate(TopItemsModel.COLUMNS):
            assert model.headerData(i, Qt.Orientation.Horizontal) == header


class TestTopItemsModelDisplayRole:
    """Tests for TopItemsModel display formatting."""

    @pytest.fixture
    def model_with_data(self):
        """Create model with test data."""
        model = TopItemsModel()
        model.set_data([
            {
                "rank": 1,
                "item_name": "Mageblood",
                "avg_value": 50000.0,
                "min_value": 45000.0,
                "max_value": 55000.0,
                "data_points": 60,
            },
        ])
        return model

    def test_rank_displays_correctly(self, model_with_data):
        """Rank column shows stored rank."""
        index = model_with_data.index(0, 0)
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "1"

    def test_rank_uses_row_index_if_missing(self):
        """Rank uses row index if not in data."""
        model = TopItemsModel()
        model.set_data([{"item_name": "Test"}])
        index = model.index(0, 0)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "1"

    def test_item_name_displays(self, model_with_data):
        """Item name displays correctly."""
        index = model_with_data.index(0, 1)
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "Mageblood"

    def test_large_value_formatting(self, model_with_data):
        """Large values use comma formatting."""
        index = model_with_data.index(0, 2)  # avg_value
        value = model_with_data.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "50,000"

    def test_small_value_formatting(self):
        """Small values show 1 decimal place."""
        model = TopItemsModel()
        model.set_data([{"item_name": "Test", "avg_value": 99.5}])
        index = model.index(0, 2)
        value = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert value == "99.5"


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_tracked_currencies_not_empty(self):
        """TRACKED_CURRENCIES has entries."""
        assert len(TRACKED_CURRENCIES) > 0

    def test_divine_orb_in_tracked(self):
        """Divine Orb is tracked."""
        assert "Divine Orb" in TRACKED_CURRENCIES

    def test_all_tracked_have_short_names(self):
        """All tracked currencies have short names."""
        for currency in TRACKED_CURRENCIES:
            assert currency in CURRENCY_SHORT_NAMES

    def test_short_names_are_short(self):
        """Short names are actually shorter."""
        for full, short in CURRENCY_SHORT_NAMES.items():
            assert len(short) <= len(full)


# =============================================================================
# PriceHistoryWindow Tests
# =============================================================================


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()
    ctx.db = MagicMock()
    ctx.config = MagicMock()
    ctx.config.league = "Settlers"

    # Mock database cursor
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("Settlers",), ("Affliction",)]
    ctx.db.conn.execute.return_value = mock_cursor

    return ctx


class TestPriceHistoryWindowInit:
    """Tests for PriceHistoryWindow initialization."""

    def test_init_creates_window(self, qtbot, mock_ctx):
        """Window initializes without error."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window is not None

    def test_init_sets_title(self, qtbot, mock_ctx):
        """Window has correct title."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert "Price History" in window.windowTitle()

    def test_init_sets_minimum_size(self, qtbot, mock_ctx):
        """Window has minimum size set."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window.minimumWidth() >= 900
            assert window.minimumHeight() >= 600

    def test_init_creates_league_combo(self, qtbot, mock_ctx):
        """League combo box is created."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window._league_combo is not None

    def test_init_creates_currency_table(self, qtbot, mock_ctx):
        """Currency table is created."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window._currency_table is not None
            assert window._currency_model is not None

    def test_init_creates_uniques_table(self, qtbot, mock_ctx):
        """Uniques table is created."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window._uniques_table is not None
            assert window._uniques_model is not None

    def test_init_creates_aggregate_button(self, qtbot, mock_ctx):
        """Aggregate button is created."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            assert window._aggregate_btn is not None


class TestPriceHistoryWindowLeagues:
    """Tests for league loading and selection."""

    def test_load_leagues_populates_combo(self, qtbot, mock_ctx):
        """Leagues are loaded into combo box."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)
            # Combo should have leagues from mock
            assert window._league_combo.count() >= 1

    def test_load_leagues_selects_current_league(self, qtbot, mock_ctx):
        """Current league is selected if available."""
        mock_ctx.config.league = "Settlers"

        # Mock returns Settlers as first league
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("Settlers",), ("Affliction",)]
        mock_ctx.db.conn.execute.return_value = mock_cursor

        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            # Should select current league
            if window._league_combo.count() > 0:
                assert window._league_combo.currentText() == "Settlers"


class TestPriceHistoryWindowAggregation:
    """Tests for aggregation functionality."""

    def test_aggregate_button_click(self, qtbot, mock_ctx):
        """Aggregate button triggers aggregation."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            # Mock the economy service
            mock_service = MagicMock()
            mock_service.aggregate_league.return_value = True
            mock_service.is_league_aggregated.return_value = True
            mock_service.get_currency_summary.return_value = []
            mock_service.get_top_items_summary.return_value = []
            mock_service.get_league_summary.return_value = {}

            with patch.object(window, '_get_economy_service', return_value=mock_service):
                window._league_combo.setCurrentText("Settlers")
                window._on_aggregate_clicked()

                mock_service.aggregate_league.assert_called_once()

    def test_aggregate_button_disabled_during_aggregation(self, qtbot, mock_ctx):
        """Button is disabled during aggregation."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            # Create slow mock service
            mock_service = MagicMock()

            def slow_aggregate(*args, **kwargs):
                # Check button is disabled
                assert not window._aggregate_btn.isEnabled()
                return True

            mock_service.aggregate_league.side_effect = slow_aggregate
            mock_service.is_league_aggregated.return_value = True
            mock_service.get_currency_summary.return_value = []
            mock_service.get_top_items_summary.return_value = []
            mock_service.get_league_summary.return_value = {}

            with patch.object(window, '_get_economy_service', return_value=mock_service):
                window._league_combo.setCurrentText("Settlers")
                window._on_aggregate_clicked()


class TestPriceHistoryWindowDataLoading:
    """Tests for data loading."""

    def test_on_league_changed_loads_data(self, qtbot, mock_ctx):
        """Changing league loads new data."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            mock_service = MagicMock()
            mock_service.is_league_aggregated.return_value = False

            with patch.object(window, '_get_economy_service', return_value=mock_service):
                with patch.object(window, '_load_currency_data_raw') as mock_load_currency:
                    with patch.object(window, '_load_uniques_data_raw') as mock_load_uniques:
                        window._on_league_changed("Affliction")

                        mock_load_currency.assert_called_once()
                        mock_load_uniques.assert_called_once()

    def test_empty_league_does_nothing(self, qtbot, mock_ctx):
        """Empty league string does nothing."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            # Should not raise
            window._on_league_changed("")


class TestPriceHistoryWindowEconomyService:
    """Tests for economy service integration."""

    def test_get_economy_service_creates_once(self, qtbot, mock_ctx):
        """Economy service is created on first access."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            # First access creates the service
            service = window._get_economy_service()
            assert service is not None

    def test_get_economy_service_caches(self, qtbot, mock_ctx):
        """Economy service is cached after first access."""
        with patch('gui_qt.windows.price_history_window.apply_window_icon'):
            window = PriceHistoryWindow(mock_ctx)
            qtbot.addWidget(window)

            service1 = window._get_economy_service()
            service2 = window._get_economy_service()

            assert service1 is service2  # Same instance returned
