"""Tests for gui_qt/windows/price_rankings_window.py - Price rankings display."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from PyQt6.QtCore import Qt, QModelIndex

from gui_qt.windows.price_rankings_window import (
    IconCache,
    RankingsTableModel,
    FetchWorker,
    PriceRankingsWindow,
    get_icon_cache,
    TREND_COLORS,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_ctx():
    """Create a mock application context."""
    ctx = MagicMock()
    ctx.config.league = "Settlers"
    return ctx


@pytest.fixture
def mock_ranked_item():
    """Create a mock RankedItem."""
    item = MagicMock()
    item.rank = 1
    item.name = "Mirror of Kalandra"
    item.base_type = "Currency"
    item.chaos_value = 75000.0
    item.divine_value = 500.0
    item.icon = "https://example.com/icon.png"
    item.rarity = "currency"
    return item


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    return tmp_path / "icon_cache"


# =============================================================================
# IconCache Tests
# =============================================================================


class TestIconCacheInit:
    """Tests for IconCache initialization."""

    def test_init_creates_directory(self, temp_cache_dir):
        """Should create cache directory."""
        cache = IconCache(cache_dir=temp_cache_dir)
        assert temp_cache_dir.exists()

    def test_init_default_directory(self):
        """Should use default directory if none specified."""
        with patch('gui_qt.windows.price_rankings_window.ICON_CACHE_DIR', Path("/tmp/test_cache")):
            cache = IconCache()
            # Just verify it doesn't crash - don't actually create the directory


class TestIconCacheUrlToFilename:
    """Tests for URL to filename conversion."""

    def test_url_to_filename_consistent(self, temp_cache_dir):
        """Should produce consistent filenames for same URL."""
        cache = IconCache(cache_dir=temp_cache_dir)
        url = "https://example.com/icon.png"

        filename1 = cache._url_to_filename(url)
        filename2 = cache._url_to_filename(url)

        assert filename1 == filename2
        assert filename1.endswith(".png")

    def test_url_to_filename_unique(self, temp_cache_dir):
        """Should produce different filenames for different URLs."""
        cache = IconCache(cache_dir=temp_cache_dir)

        filename1 = cache._url_to_filename("https://example.com/icon1.png")
        filename2 = cache._url_to_filename("https://example.com/icon2.png")

        assert filename1 != filename2


class TestIconCacheGetIcon:
    """Tests for icon retrieval."""

    def test_get_icon_empty_url(self, temp_cache_dir):
        """Should return None for empty URL."""
        cache = IconCache(cache_dir=temp_cache_dir)
        result = cache.get_icon("")
        assert result is None

    def test_get_icon_from_memory_cache(self, temp_cache_dir):
        """Should return icon from memory cache."""
        cache = IconCache(cache_dir=temp_cache_dir)
        url = "https://example.com/icon.png"

        # Pre-populate memory cache
        mock_pixmap = MagicMock()
        cache._pixmaps[url] = mock_pixmap

        result = cache.get_icon(url)
        assert result is mock_pixmap

    def test_get_icon_not_cached_no_callback(self, temp_cache_dir):
        """Should return None if not cached and no callback."""
        cache = IconCache(cache_dir=temp_cache_dir)
        result = cache.get_icon("https://example.com/icon.png")
        assert result is None

    def test_get_icon_starts_download_with_callback(self, temp_cache_dir):
        """Should start download when callback provided."""
        cache = IconCache(cache_dir=temp_cache_dir)
        callback = MagicMock()

        with patch.object(cache, '_download_icon') as mock_download:
            cache.get_icon("https://example.com/icon.png", callback=callback)
            mock_download.assert_called_once()


class TestGetIconCache:
    """Tests for get_icon_cache singleton."""

    def test_get_icon_cache_returns_instance(self):
        """Should return IconCache instance."""
        # Reset global
        import gui_qt.windows.price_rankings_window as module
        module._icon_cache = None

        cache = get_icon_cache()
        assert isinstance(cache, IconCache)

    def test_get_icon_cache_returns_same_instance(self):
        """Should return same instance on subsequent calls."""
        cache1 = get_icon_cache()
        cache2 = get_icon_cache()
        assert cache1 is cache2


# =============================================================================
# RankingsTableModel Tests
# =============================================================================


class TestRankingsTableModelInit:
    """Tests for RankingsTableModel initialization."""

    def test_init_empty_data(self):
        """Should initialize with empty data."""
        model = RankingsTableModel()
        assert model.rowCount() == 0

    def test_init_columns_defined(self):
        """Should have defined columns."""
        model = RankingsTableModel()
        assert model.columnCount() > 0
        assert len(model.COLUMNS) > 0


class TestRankingsTableModelRowColumn:
    """Tests for row/column counts."""

    def test_row_count_empty(self):
        """Should return 0 for empty model."""
        model = RankingsTableModel()
        assert model.rowCount() == 0

    def test_column_count(self):
        """Should return correct column count."""
        model = RankingsTableModel()
        assert model.columnCount() == len(model.COLUMNS)


class TestRankingsTableModelSetData:
    """Tests for setting model data."""

    def test_set_data_from_items(self, mock_ranked_item):
        """Should populate data from RankedItem list."""
        model = RankingsTableModel()

        # Disable trend calculation for this test
        model.set_data([mock_ranked_item], calculate_trends=False)

        assert model.rowCount() == 1

    def test_set_data_multiple_items(self, mock_ranked_item):
        """Should handle multiple items."""
        model = RankingsTableModel()

        item2 = MagicMock()
        item2.rank = 2
        item2.name = "Divine Orb"
        item2.base_type = "Currency"
        item2.chaos_value = 150.0
        item2.divine_value = 1.0
        item2.icon = ""
        item2.rarity = "currency"

        model.set_data([mock_ranked_item, item2], calculate_trends=False)

        assert model.rowCount() == 2

    def test_set_data_clears_existing(self, mock_ranked_item):
        """Should clear existing data when setting new."""
        model = RankingsTableModel()

        model.set_data([mock_ranked_item], calculate_trends=False)
        assert model.rowCount() == 1

        model.set_data([], calculate_trends=False)
        assert model.rowCount() == 0


class TestRankingsTableModelData:
    """Tests for data retrieval."""

    def test_data_display_role_name(self, mock_ranked_item):
        """Should return item name for display."""
        model = RankingsTableModel()
        model.set_data([mock_ranked_item], calculate_trends=False)

        # Find name column index
        name_col = next(i for i, (key, _, _) in enumerate(model.COLUMNS) if key == "name")
        index = model.index(0, name_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "Mirror of Kalandra"

    def test_data_display_role_chaos_formatted(self, mock_ranked_item):
        """Should format chaos value."""
        model = RankingsTableModel()
        model.set_data([mock_ranked_item], calculate_trends=False)

        chaos_col = next(i for i, (key, _, _) in enumerate(model.COLUMNS) if key == "chaos_value")
        index = model.index(0, chaos_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "75,000c" in result

    def test_data_display_role_divine_formatted(self, mock_ranked_item):
        """Should format divine value."""
        model = RankingsTableModel()
        model.set_data([mock_ranked_item], calculate_trends=False)

        divine_col = next(i for i, (key, _, _) in enumerate(model.COLUMNS) if key == "divine_value")
        index = model.index(0, divine_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "500.00" in result

    def test_data_invalid_index(self, mock_ranked_item):
        """Should return None for invalid index."""
        model = RankingsTableModel()
        model.set_data([mock_ranked_item], calculate_trends=False)

        invalid_index = model.index(100, 0)  # Invalid row
        result = model.data(invalid_index, Qt.ItemDataRole.DisplayRole)
        assert result is None

    def test_data_alignment_role(self, mock_ranked_item):
        """Should return alignment for numeric columns."""
        model = RankingsTableModel()
        model.set_data([mock_ranked_item], calculate_trends=False)

        chaos_col = next(i for i, (key, _, _) in enumerate(model.COLUMNS) if key == "chaos_value")
        index = model.index(0, chaos_col)

        result = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert result is not None


class TestRankingsTableModelHeaderData:
    """Tests for header data."""

    def test_header_data_horizontal(self):
        """Should return column headers."""
        model = RankingsTableModel()

        for i, (_, label, _) in enumerate(model.COLUMNS):
            result = model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            assert result == label

    def test_header_data_vertical_returns_none(self):
        """Should return None for vertical header."""
        model = RankingsTableModel()
        result = model.headerData(0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole)
        assert result is None


class TestRankingsTableModelSetContext:
    """Tests for context setting."""

    def test_set_context_stores_values(self):
        """Should store league and category."""
        model = RankingsTableModel()
        model.set_context("Settlers", "currency")

        assert model._league == "Settlers"
        assert model._category == "currency"


# =============================================================================
# FetchWorker Tests
# =============================================================================


class TestFetchWorkerInit:
    """Tests for FetchWorker initialization."""

    def test_init_stores_parameters(self):
        """Should store all parameters."""
        worker = FetchWorker(
            league="Settlers",
            category="currency",
            slot="helmet",
            all_slots=True,
            force_refresh=True,
        )

        assert worker.league == "Settlers"
        assert worker.category == "currency"
        assert worker.slot == "helmet"
        assert worker.all_slots is True
        assert worker.force_refresh is True

    def test_init_default_values(self):
        """Should use default values."""
        worker = FetchWorker(league="Standard")

        assert worker.league == "Standard"
        assert worker.category is None
        assert worker.slot is None
        assert worker.all_slots is False
        assert worker.force_refresh is False

    def test_has_signals(self):
        """Should have required signals."""
        worker = FetchWorker(league="Standard")

        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'progress')


# =============================================================================
# PriceRankingsWindow Tests
# =============================================================================


class TestPriceRankingsWindowInit:
    """Tests for PriceRankingsWindow initialization."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_init_sets_title(self, mock_load, qtbot, mock_ctx):
        """Should set window title."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)
        assert "Rankings" in window.windowTitle()

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_init_sets_minimum_size(self, mock_load, qtbot, mock_ctx):
        """Should set minimum size."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)
        assert window.minimumWidth() >= 700
        assert window.minimumHeight() >= 500

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_init_creates_controls(self, mock_load, qtbot, mock_ctx):
        """Should create control widgets."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.league_combo is not None
        assert window.category_combo is not None
        assert window.refresh_btn is not None
        assert window.force_refresh_cb is not None

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_init_creates_tab_widget(self, mock_load, qtbot, mock_ctx):
        """Should create tab widget."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)
        assert window.tab_widget is not None

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_init_has_signals(self, mock_load, qtbot, mock_ctx):
        """Should have required signals."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        assert hasattr(window, 'priceCheckRequested')
        assert hasattr(window, 'ai_analysis_requested')


class TestPriceRankingsWindowUI:
    """Tests for UI setup."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_category_combo_populated(self, mock_load, qtbot, mock_ctx):
        """Should populate category combo box."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        # Should have items (All Categories plus others)
        assert window.category_combo.count() > 1

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_progress_bar_hidden_initially(self, mock_load, qtbot, mock_ctx):
        """Should hide progress bar initially."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)
        assert window.progress_bar.isHidden()


class TestPriceRankingsWindowRefresh:
    """Tests for refresh functionality."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    @patch('gui_qt.windows.price_rankings_window.FetchWorker')
    def test_refresh_creates_worker(self, mock_worker_cls, mock_load, qtbot, mock_ctx):
        """Should create worker on refresh."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        # Set up league combo
        window.league_combo.addItem("Standard", "Standard")

        # Configure mock worker
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        mock_worker_cls.return_value = mock_worker

        # Reset call count and call refresh
        mock_worker_cls.reset_mock()
        window._worker = None
        window._on_refresh()

        # Should have called FetchWorker once
        assert mock_worker_cls.call_count == 1
        mock_worker.start.assert_called()

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    @patch('gui_qt.windows.price_rankings_window.FetchWorker')
    def test_refresh_shows_progress(self, mock_worker_cls, mock_load, qtbot, mock_ctx):
        """Should show progress bar during refresh."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        window.league_combo.addItem("Standard", "Standard")

        # Configure mock worker
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        mock_worker_cls.return_value = mock_worker

        # Ensure progress bar is hidden initially, then call refresh
        window.progress_bar.hide()
        window._worker = None
        window._on_refresh()

        # Use isHidden() since isVisible() requires the window itself to be shown
        assert not window.progress_bar.isHidden()  # Progress bar is shown
        assert not window.refresh_btn.isEnabled()  # Button is disabled

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_refresh_blocked_if_running(self, mock_load, qtbot, mock_ctx):
        """Should not start new refresh if worker running."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        # Simulate running worker
        window._worker = MagicMock()
        window._worker.isRunning.return_value = True

        with patch('gui_qt.windows.price_rankings_window.FetchWorker') as mock_worker_cls:
            window._on_refresh()
            mock_worker_cls.assert_not_called()


class TestPriceRankingsWindowFetchCallbacks:
    """Tests for fetch callbacks."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_on_fetch_progress_updates_status(self, mock_load, qtbot, mock_ctx):
        """Should update status on progress."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_fetch_progress("Fetching currency...")

        assert "currency" in window.status_label.text().lower()

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._update_tabs')
    def test_on_fetch_finished_stores_rankings(self, mock_update, mock_load, qtbot, mock_ctx):
        """Should store rankings on finish."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        mock_ranking = MagicMock()
        mock_ranking.items = [MagicMock()]
        rankings = {"currency": mock_ranking}

        window._on_fetch_finished(rankings)

        assert window._rankings == rankings
        assert window.progress_bar.isHidden()
        assert window.refresh_btn.isEnabled()

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_on_fetch_error_shows_message(self, mock_load, qtbot, mock_ctx):
        """Should show error message on failure."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        with patch('PyQt6.QtWidgets.QMessageBox.warning'):
            window._on_fetch_error("Connection failed")

        assert "error" in window.status_label.text().lower()


class TestPriceRankingsWindowSetAiCallback:
    """Tests for AI callback setting."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_set_ai_configured_callback(self, mock_load, qtbot, mock_ctx):
        """Should set AI callback on context menu manager."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        callback = MagicMock(return_value=True)

        # Mock the context menu manager's method
        with patch.object(window._context_menu_manager, 'set_ai_configured_callback') as mock_set:
            window.set_ai_configured_callback(callback)
            mock_set.assert_called_with(callback)


class TestPriceRankingsWindowCloseEvent:
    """Tests for window close."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_close_stops_worker(self, mock_load, qtbot, mock_ctx):
        """Should stop worker on close."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        window._worker = mock_worker

        window.close()

        mock_worker.quit.assert_called_once()


# =============================================================================
# TREND_COLORS Tests
# =============================================================================


class TestTrendColors:
    """Tests for trend color constants."""

    def test_has_up_color(self):
        """Should have 'up' trend color."""
        assert "up" in TREND_COLORS
        assert TREND_COLORS["up"].startswith("#")

    def test_has_down_color(self):
        """Should have 'down' trend color."""
        assert "down" in TREND_COLORS
        assert TREND_COLORS["down"].startswith("#")

    def test_has_stable_color(self):
        """Should have 'stable' trend color."""
        assert "stable" in TREND_COLORS
        assert TREND_COLORS["stable"].startswith("#")

    def test_colors_are_different(self):
        """Should have distinct colors for each trend."""
        assert TREND_COLORS["up"] != TREND_COLORS["down"]
        assert TREND_COLORS["up"] != TREND_COLORS["stable"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestPriceRankingsWindowEdgeCases:
    """Edge case tests."""

    @patch('gui_qt.windows.price_rankings_window.PriceRankingsWindow._load_initial_data')
    def test_copy_to_clipboard(self, mock_load, qtbot, mock_ctx):
        """Should copy text to clipboard."""
        window = PriceRankingsWindow(mock_ctx)
        qtbot.addWidget(window)

        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard:
            mock_clip = MagicMock()
            mock_clipboard.return_value = mock_clip

            window._copy_to_clipboard("Test text")

            mock_clip.setText.assert_called_with("Test text")

    def test_rankings_model_trend_calculator_lazy(self):
        """Should lazy-load trend calculator."""
        model = RankingsTableModel()

        # Initially None
        assert model._trend_calculator is None

        # Accessing property should try to load - patch at source module
        with patch('core.price_trend_calculator.get_trend_calculator') as mock_get:
            mock_calc = MagicMock()
            mock_get.return_value = mock_calc
            result = model.trend_calculator
            mock_get.assert_called_once()
            assert result is mock_calc

    def test_rankings_model_handles_none_values(self, mock_ranked_item):
        """Should handle None values in data."""
        model = RankingsTableModel()

        # Set some values to None
        mock_ranked_item.base_type = None
        mock_ranked_item.icon = None

        model.set_data([mock_ranked_item], calculate_trends=False)

        # Should not crash
        base_col = next(i for i, (key, _, _) in enumerate(model.COLUMNS) if key == "base_type")
        index = model.index(0, base_col)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == ""  # Empty string for None
