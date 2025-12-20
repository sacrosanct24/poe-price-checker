"""Tests for gui_qt/windows/stash_viewer_window.py - Stash viewer."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt

from core.stash_valuator import PricedItem, PriceSource, ValuationResult

from gui_qt.windows.stash_viewer_window import (
    FetchWorker,
    ItemTableModel,
    StashItemDetailsDialog,
    StashViewerWindow,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_ctx():
    """Create a mock application context."""
    ctx = MagicMock()
    ctx.config.league = "Settlers"
    ctx.config.account_name = "TestAccount"
    ctx.config.poesessid = "test_session_id"
    ctx.config.stash_last_fetch = None
    ctx.config.has_stash_credentials.return_value = True
    ctx.db = MagicMock()
    return ctx


@pytest.fixture
def mock_priced_item():
    """Create a mock PricedItem."""
    item = MagicMock(spec=PricedItem)
    item.name = "Exalted Orb"
    item.type_line = "Exalted Orb"
    item.base_type = "Exalted Orb"
    item.display_name = "Exalted Orb"
    item.stack_size = 5
    item.unit_price = 10.0
    item.total_price = 50.0
    item.display_price = "50c"
    item.rarity = "Currency"
    item.item_class = "Currency"
    item.price_source = PriceSource.POE_NINJA
    item.tab_name = "Currency Tab"
    item.ilvl = 0
    item.links = 0
    item.sockets = ""
    item.corrupted = False
    item.raw_item = {}
    return item


@pytest.fixture
def mock_valuation_result(mock_priced_item):
    """Create a mock ValuationResult."""
    tab = MagicMock()
    tab.name = "Currency"
    tab.total_value = 1000.0
    tab.display_value = "1,000c"
    tab.items = [mock_priced_item]

    result = MagicMock(spec=ValuationResult)
    result.tabs = [tab]
    result.total_items = 10
    result.priced_items = 8
    result.total_chaos_value = 1500.0
    result.display_total = "1,500c"
    return result


# =============================================================================
# FetchWorker Tests
# =============================================================================


class TestFetchWorkerInit:
    """Tests for FetchWorker initialization."""

    def test_init_stores_parameters(self):
        """Should store all parameters."""
        worker = FetchWorker(
            poesessid="test_session",
            account_name="TestAccount",
            league="Settlers",
            max_tabs=10,
        )

        assert worker.poesessid == "test_session"
        assert worker.account_name == "TestAccount"
        assert worker.league == "Settlers"
        assert worker.max_tabs == 10

    def test_init_default_max_tabs(self):
        """Should use None as default max_tabs."""
        worker = FetchWorker(
            poesessid="test",
            account_name="Test",
            league="Standard",
        )

        assert worker.max_tabs is None

    def test_has_signals(self):
        """Should have required signals."""
        worker = FetchWorker(
            poesessid="test",
            account_name="Test",
            league="Standard",
        )

        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'rate_limited')


# =============================================================================
# ItemTableModel Tests
# =============================================================================


class TestItemTableModelInit:
    """Tests for ItemTableModel initialization."""

    def test_init_empty_data(self):
        """Should initialize with empty data."""
        model = ItemTableModel()
        assert model.rowCount() == 0

    def test_init_columns_defined(self):
        """Should have defined columns."""
        model = ItemTableModel()
        assert len(model.COLUMNS) > 0
        assert model.columnCount() == len(model.COLUMNS)


class TestItemTableModelSetItems:
    """Tests for set_items method."""

    def test_set_items_updates_data(self, mock_priced_item):
        """Should update model data."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        assert model.rowCount() == 1

    def test_set_items_clears_existing(self, mock_priced_item):
        """Should clear existing items."""
        model = ItemTableModel()

        model.set_items([mock_priced_item, mock_priced_item])
        assert model.rowCount() == 2

        model.set_items([mock_priced_item])
        assert model.rowCount() == 1


class TestItemTableModelFiltering:
    """Tests for filtering functionality."""

    def test_set_min_value_filters_items(self, mock_priced_item):
        """Should filter items below minimum value."""
        model = ItemTableModel()

        # Create items with different prices
        item1 = MagicMock(spec=PricedItem)
        item1.total_price = 5.0
        item1.display_name = "Low Value"

        item2 = MagicMock(spec=PricedItem)
        item2.total_price = 100.0
        item2.display_name = "High Value"

        model.set_items([item1, item2])
        assert model.rowCount() == 2

        model.set_min_value(50.0)
        assert model.rowCount() == 1

    def test_set_search_text_filters_items(self, mock_priced_item):
        """Should filter items by search text."""
        model = ItemTableModel()

        item1 = MagicMock(spec=PricedItem)
        item1.total_price = 100.0
        item1.display_name = "Exalted Orb"

        item2 = MagicMock(spec=PricedItem)
        item2.total_price = 100.0
        item2.display_name = "Divine Orb"

        model.set_items([item1, item2])
        assert model.rowCount() == 2

        model.set_search_text("exalted")
        assert model.rowCount() == 1

    def test_search_case_insensitive(self, mock_priced_item):
        """Should perform case-insensitive search."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.total_price = 100.0
        item.display_name = "Exalted Orb"

        model.set_items([item])

        model.set_search_text("EXALTED")
        assert model.rowCount() == 1


class TestItemTableModelData:
    """Tests for data retrieval."""

    # Column indices after adding verdict column at position 0
    # 0: verdict, 1: display_name, 2: stack_size, 3: unit_price,
    # 4: total_price, 5: rarity, 6: price_source

    def test_data_display_role_verdict(self, mock_priced_item):
        """Should return verdict emoji."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        verdict_col = 0  # Verdict column
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        # Currency items with price should get KEEP verdict
        assert result in ["👍", "👎", "🤔"]

    def test_data_display_role_name(self, mock_priced_item):
        """Should return item name for display."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        name_col = 1  # display_name column (shifted by 1)
        index = model.index(0, name_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "Exalted Orb"

    def test_data_display_role_stack_size(self, mock_priced_item):
        """Should return stack size or empty string."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        stack_col = 2  # Stack size column (shifted by 1)
        index = model.index(0, stack_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "5"

    def test_data_display_role_unit_price(self, mock_priced_item):
        """Should format unit price with currency."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        unit_col = 3  # Unit price column (shifted by 1)
        index = model.index(0, unit_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "10" in result
        assert "c" in result

    def test_data_display_role_price_source(self, mock_priced_item):
        """Should show price source."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        source_col = 6  # Price source column (shifted by 1)
        index = model.index(0, source_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "poe.ninja"

    def test_data_invalid_index(self, mock_priced_item):
        """Should return None for invalid index."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        invalid_index = model.index(100, 0)
        result = model.data(invalid_index, Qt.ItemDataRole.DisplayRole)
        assert result is None

    def test_data_alignment_role(self, mock_priced_item):
        """Should return alignment for numeric columns."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        total_col = 4  # Total price column (shifted by 1)
        index = model.index(0, total_col)

        result = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert result is not None

    def test_data_verdict_alignment_center(self, mock_priced_item):
        """Should center-align verdict column."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        verdict_col = 0
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.TextAlignmentRole)
        assert result == Qt.AlignmentFlag.AlignCenter

    def test_data_verdict_tooltip(self, mock_priced_item):
        """Should show tooltip for verdict."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        verdict_col = 0
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.ToolTipRole)
        assert result is not None
        # Tooltip should contain verdict explanation
        assert "KEEP" in result or "VENDOR" in result or "MAYBE" in result

    def test_data_verdict_respects_rare_evaluated_excellent(self):
        """Should show KEEP for RARE_EVALUATED items with excellent tier."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.name = "Rare Helmet"
        item.type_line = "Hubris Circlet"
        item.base_type = "Hubris Circlet"
        item.display_name = "Rare Helmet"
        item.stack_size = 1
        item.total_price = 0.0  # No poe.ninja price
        item.rarity = "Rare"
        item.item_class = "Helmets"
        item.price_source = PriceSource.RARE_EVALUATED
        item.eval_tier = "excellent"
        item.eval_summary = "High life, tri-res"
        item.tab_name = "Dump"
        item.ilvl = 86
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        verdict_col = 0
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "👍"  # Should be KEEP for excellent tier

    def test_data_verdict_respects_rare_evaluated_good(self):
        """Should show MAYBE for RARE_EVALUATED items with good tier."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.name = "Rare Boots"
        item.type_line = "Sorcerer Boots"
        item.base_type = "Sorcerer Boots"
        item.display_name = "Rare Boots"
        item.stack_size = 1
        item.total_price = 0.0
        item.rarity = "Rare"
        item.item_class = "Boots"
        item.price_source = PriceSource.RARE_EVALUATED
        item.eval_tier = "good"
        item.eval_summary = "Movement speed, life"
        item.tab_name = "Dump"
        item.ilvl = 84
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        verdict_col = 0
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "🤔"  # Should be MAYBE for good tier

    def test_data_verdict_respects_rare_evaluated_vendor(self):
        """Should show VENDOR for RARE_EVALUATED items with vendor tier."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.name = "Rare Gloves"
        item.type_line = "Leather Gloves"
        item.base_type = "Leather Gloves"
        item.display_name = "Rare Gloves"
        item.stack_size = 1
        item.total_price = 0.0
        item.rarity = "Rare"
        item.item_class = "Gloves"
        item.price_source = PriceSource.RARE_EVALUATED
        item.eval_tier = "vendor"
        item.eval_summary = "Low-tier affixes"
        item.tab_name = "Dump"
        item.ilvl = 68
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        verdict_col = 0
        index = model.index(0, verdict_col)

        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "👎"  # Should be VENDOR for vendor tier


class TestItemTableModelHeaderData:
    """Tests for header data."""

    def test_header_data_horizontal(self):
        """Should return column headers."""
        model = ItemTableModel()

        for i, (_, label, _) in enumerate(model.COLUMNS):
            result = model.headerData(
                i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
            assert result == label

    def test_header_data_vertical_returns_none(self):
        """Should return None for vertical header."""
        model = ItemTableModel()
        result = model.headerData(
            0, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole
        )
        assert result is None


class TestItemTableModelGetItem:
    """Tests for get_item method."""

    def test_get_item_valid_row(self, mock_priced_item):
        """Should return item at valid row."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        item = model.get_item(0)
        assert item is mock_priced_item

    def test_get_item_invalid_row(self, mock_priced_item):
        """Should return None for invalid row."""
        model = ItemTableModel()
        model.set_items([mock_priced_item])

        item = model.get_item(100)
        assert item is None


# =============================================================================
# StashItemDetailsDialog Tests
# =============================================================================


class TestStashItemDetailsDialogInit:
    """Tests for StashItemDetailsDialog initialization."""

    def test_init_sets_title(self, qtbot, mock_priced_item):
        """Should set window title."""
        dialog = StashItemDetailsDialog(mock_priced_item)
        qtbot.addWidget(dialog)

        assert "Details" in dialog.windowTitle()

    def test_init_sets_minimum_size(self, qtbot, mock_priced_item):
        """Should set minimum size."""
        dialog = StashItemDetailsDialog(mock_priced_item)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 400
        assert dialog.minimumHeight() >= 300

    def test_init_stores_item(self, qtbot, mock_priced_item):
        """Should store the item reference."""
        dialog = StashItemDetailsDialog(mock_priced_item)
        qtbot.addWidget(dialog)

        assert dialog.item is mock_priced_item


class TestStashItemDetailsDialogCopyName:
    """Tests for copy name functionality."""

    def test_copy_name_copies_to_clipboard(self, qtbot, mock_priced_item):
        """Should copy item name to clipboard."""
        dialog = StashItemDetailsDialog(mock_priced_item)
        qtbot.addWidget(dialog)

        with patch('PyQt6.QtWidgets.QApplication.clipboard') as mock_clipboard:
            mock_clip = MagicMock()
            mock_clipboard.return_value = mock_clip

            with patch.object(dialog, 'accept'):  # Prevent dialog from closing
                with patch('PyQt6.QtWidgets.QMessageBox.information'):
                    dialog._copy_name()

            mock_clip.setText.assert_called_with("Exalted Orb")


# =============================================================================
# StashViewerWindow Tests
# =============================================================================


class TestStashViewerWindowInit:
    """Tests for StashViewerWindow initialization."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_init_sets_title(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should set window title."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        assert "Stash" in window.windowTitle()

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_init_sets_minimum_size(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should set minimum size."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.minimumWidth() >= 900
        assert window.minimumHeight() >= 600

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_init_creates_widgets(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should create control widgets."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.league_combo is not None
        assert window.refresh_btn is not None
        assert window.tab_list is not None
        assert window.item_table is not None

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_init_has_signals(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should have required signals."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        assert hasattr(window, 'ai_analysis_requested')
        assert hasattr(window, 'price_check_requested')


class TestStashViewerWindowSetAiCallback:
    """Tests for AI callback setting."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_set_ai_configured_callback(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should set AI callback on context menu manager."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        callback = MagicMock(return_value=True)

        with patch.object(window._context_menu_manager, 'set_ai_configured_callback') as mock_set:
            window.set_ai_configured_callback(callback)
            mock_set.assert_called_with(callback)


class TestStashViewerWindowProgress:
    """Tests for progress handling."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_progress_updates_status(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should update status label on progress."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_progress(5, 10, "Loading tabs...")

        assert "Loading" in window.status_label.text()

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_progress_updates_progress_bar(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should update progress bar."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_progress(5, 10, "Loading...")

        assert window.progress_bar.maximum() == 10
        assert window.progress_bar.value() == 5


class TestStashViewerWindowRateLimited:
    """Tests for rate limit handling."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_rate_limited_updates_status(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should update status with wait message."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_rate_limited(60, 2)

        assert "Rate limited" in window.status_label.text()
        assert "60" in window.status_label.text()


class TestStashViewerWindowFetchError:
    """Tests for fetch error handling."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_fetch_error_updates_status(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should update status with error."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        with patch('PyQt6.QtWidgets.QMessageBox.critical'):
            window._on_fetch_error("Connection failed")

        assert "Error" in window.status_label.text()


class TestStashViewerWindowTabSelection:
    """Tests for tab selection."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_tab_selected_clears_items_if_invalid(
        self, mock_leagues, mock_storage, qtbot, mock_ctx
    ):
        """Should clear items for invalid selection."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        # No result set
        window._on_tab_selected(0)

        assert window._item_model.rowCount() == 0


class TestStashViewerWindowFilters:
    """Tests for filter functionality."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_min_value_changed_updates_model(
        self, mock_leagues, mock_storage, qtbot, mock_ctx
    ):
        """Should update model minimum value."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_min_value_changed(100)

        assert window._item_model._min_value == 100.0

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_on_search_changed_updates_model(
        self, mock_leagues, mock_storage, qtbot, mock_ctx
    ):
        """Should update model search text."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        window._on_search_changed("orb")

        assert window._item_model._search_text == "orb"


class TestStashViewerWindowCloseEvent:
    """Tests for window close."""

    @patch('gui_qt.stash_viewer.get_stash_storage')
    @patch('gui_qt.stash_viewer.get_available_leagues')
    def test_close_stops_worker(self, mock_leagues, mock_storage, qtbot, mock_ctx):
        """Should stop worker on close."""
        mock_leagues.return_value = ["Standard"]
        mock_storage.return_value = MagicMock()
        mock_storage.return_value.load_latest_snapshot.return_value = None

        window = StashViewerWindow(mock_ctx)
        qtbot.addWidget(window)

        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        window._worker = mock_worker

        window.close()

        mock_worker.terminate.assert_called_once()


# =============================================================================
# Edge Cases
# =============================================================================


class TestStashViewerWindowEdgeCases:
    """Edge case tests."""

    def test_item_model_stack_size_one(self):
        """Should show empty string for stack size 1."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.stack_size = 1
        item.total_price = 100.0
        item.display_name = "Test"
        # Add required attributes for verdict calculation
        item.name = "Test"
        item.type_line = "Test"
        item.base_type = "Test"
        item.tab_name = "Test Tab"
        item.rarity = "Normal"
        item.item_class = "Armour"
        item.ilvl = 0
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        stack_col = 2  # Shifted by 1 due to verdict column
        index = model.index(0, stack_col)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == ""

    def test_item_model_low_unit_price(self):
        """Should format low unit price with decimals."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.unit_price = 0.5
        item.total_price = 100.0
        item.display_name = "Test"
        # Add required attributes for verdict calculation
        item.name = "Test"
        item.type_line = "Test"
        item.base_type = "Test"
        item.tab_name = "Test Tab"
        item.rarity = "Normal"
        item.item_class = "Armour"
        item.stack_size = 1
        item.ilvl = 0
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        unit_col = 3  # Shifted by 1 due to verdict column
        index = model.index(0, unit_col)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert "0.50c" in result

    def test_item_model_poeprices_source(self):
        """Should display poeprices source."""
        model = ItemTableModel()

        item = MagicMock(spec=PricedItem)
        item.price_source = PriceSource.POE_PRICES
        item.total_price = 100.0
        item.display_name = "Test"
        # Add required attributes for verdict calculation
        item.name = "Test"
        item.type_line = "Test"
        item.base_type = "Test"
        item.tab_name = "Test Tab"
        item.rarity = "Normal"
        item.item_class = "Armour"
        item.stack_size = 1
        item.ilvl = 0
        item.links = 0
        item.sockets = ""
        item.corrupted = False
        item.raw_item = {}

        model.set_items([item])

        source_col = 6  # Shifted by 1 due to verdict column
        index = model.index(0, source_col)
        result = model.data(index, Qt.ItemDataRole.DisplayRole)
        assert result == "poeprices"
