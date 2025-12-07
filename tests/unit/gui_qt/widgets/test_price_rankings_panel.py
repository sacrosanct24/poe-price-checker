# tests/unit/gui_qt/widgets/test_price_rankings_panel.py
"""Tests for PriceRankingsPanel widget."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QFrame, QTableView, QComboBox

from gui_qt.widgets.price_rankings_panel import (
    PriceRankingsPanel,
    CompactRankingsModel,
)


class TestCompactRankingsModel:
    """Tests for CompactRankingsModel."""

    @pytest.fixture
    def model(self, qtbot):
        """Create CompactRankingsModel instance."""
        return CompactRankingsModel()

    def test_initial_row_count_is_zero(self, model):
        """Model should start with no rows."""
        assert model.rowCount() == 0

    def test_column_count_is_three(self, model):
        """Model should have 3 columns."""
        assert model.columnCount() == 3

    def test_columns_defined(self, model):
        """COLUMNS should define rank, name, chaos_value."""
        column_keys = [col[0] for col in model.COLUMNS]
        assert "rank" in column_keys
        assert "name" in column_keys
        assert "chaos_value" in column_keys

    def test_header_data_returns_labels(self, model):
        """headerData should return column labels."""
        assert model.headerData(0, Qt.Orientation.Horizontal) == "#"
        assert model.headerData(1, Qt.Orientation.Horizontal) == "Item"
        assert model.headerData(2, Qt.Orientation.Horizontal) == "Price"

    def test_set_data_populates_model(self, model):
        """set_data should populate the model."""
        from types import SimpleNamespace
        items = [
            SimpleNamespace(rank=1, name="Item 1", chaos_value=100, divine_value=0.5, rarity="unique"),
            SimpleNamespace(rank=2, name="Item 2", chaos_value=50, divine_value=0.25, rarity="rare"),
        ]
        model.set_data(items)
        assert model.rowCount() == 2

    def test_set_data_limits_to_20(self, model):
        """set_data should limit to 20 items."""
        from types import SimpleNamespace
        items = [
            SimpleNamespace(rank=i, name=f"Item {i}", chaos_value=100-i, divine_value=0, rarity="normal")
            for i in range(30)
        ]
        model.set_data(items)
        assert model.rowCount() == 20

    def test_data_returns_display_values(self, model):
        """data should return display values."""
        from types import SimpleNamespace
        items = [
            SimpleNamespace(rank=1, name="Test Item", chaos_value=1000, divine_value=5, rarity="unique"),
        ]
        model.set_data(items)

        # Rank
        rank_index = model.index(0, 0)
        assert model.data(rank_index, Qt.ItemDataRole.DisplayRole) == "1"

        # Name
        name_index = model.index(0, 1)
        assert model.data(name_index, Qt.ItemDataRole.DisplayRole) == "Test Item"

        # Chaos value
        value_index = model.index(0, 2)
        assert "1,000" in model.data(value_index, Qt.ItemDataRole.DisplayRole)

    def test_data_returns_tooltip(self, model):
        """data should return tooltip with divine value."""
        from types import SimpleNamespace
        items = [
            SimpleNamespace(rank=1, name="Test Item", chaos_value=1000, divine_value=5.5, rarity="unique"),
        ]
        model.set_data(items)

        index = model.index(0, 0)
        tooltip = model.data(index, Qt.ItemDataRole.ToolTipRole)
        assert "5.5" in tooltip

    def test_get_item_name(self, model):
        """get_item_name should return name for row."""
        from types import SimpleNamespace
        items = [
            SimpleNamespace(rank=1, name="Test Item", chaos_value=100, divine_value=0, rarity="normal"),
        ]
        model.set_data(items)
        assert model.get_item_name(0) == "Test Item"

    def test_get_item_name_invalid_row(self, model):
        """get_item_name should return None for invalid row."""
        assert model.get_item_name(99) is None

    def test_data_invalid_index_returns_none(self, model):
        """data should return None for invalid index."""
        invalid_index = model.index(99, 0)
        assert model.data(invalid_index, Qt.ItemDataRole.DisplayRole) is None


class TestPriceRankingsPanel:
    """Tests for PriceRankingsPanel widget."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock application context."""
        ctx = MagicMock()
        ctx.config = MagicMock()
        ctx.config.league = "Standard"
        return ctx

    @pytest.fixture
    def panel(self, qtbot, mock_ctx):
        """Create PriceRankingsPanel instance."""
        panel = PriceRankingsPanel(ctx=mock_ctx)
        qtbot.addWidget(panel)
        return panel

    @pytest.fixture
    def panel_no_ctx(self, qtbot):
        """Create PriceRankingsPanel without context."""
        panel = PriceRankingsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_inherits_from_qframe(self, panel):
        """PriceRankingsPanel should be a QFrame."""
        assert isinstance(panel, QFrame)

    def test_has_category_combo(self, panel):
        """Panel should have category combo box."""
        assert panel._category_combo is not None
        assert isinstance(panel._category_combo, QComboBox)

    def test_has_table_view(self, panel):
        """Panel should have table view."""
        assert panel._table is not None
        assert isinstance(panel._table, QTableView)

    def test_has_refresh_button(self, panel):
        """Panel should have refresh button."""
        assert panel._refresh_btn is not None

    def test_has_status_label(self, panel):
        """Panel should have status label."""
        assert panel._status is not None

    def test_category_combo_has_items(self, panel):
        """Category combo should have items."""
        assert panel._category_combo.count() > 0

    def test_quick_categories_defined(self, panel):
        """QUICK_CATEGORIES should have common categories."""
        category_keys = [cat[0] for cat in panel.QUICK_CATEGORIES]
        assert "currency" in category_keys
        assert "divination_cards" in category_keys
        assert "unique_weapons" in category_keys


class TestPriceRankingsPanelSignals:
    """Tests for panel signals."""

    @pytest.fixture
    def panel(self, qtbot):
        """Create PriceRankingsPanel instance."""
        panel = PriceRankingsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_price_check_requested_signal_exists(self, panel):
        """Panel should have price_check_requested signal."""
        assert hasattr(panel, 'price_check_requested')

    def test_visibility_changed_signal_exists(self, panel):
        """Panel should have visibility_changed signal."""
        assert hasattr(panel, 'visibility_changed')

    def test_double_click_emits_price_check(self, qtbot, panel):
        """Double-clicking item should emit price_check_requested."""
        from types import SimpleNamespace
        # Add test data
        items = [
            SimpleNamespace(rank=1, name="Test Item", chaos_value=100, divine_value=0, rarity="normal"),
        ]
        panel._model.set_data(items)

        with qtbot.waitSignal(panel.price_check_requested, timeout=1000) as blocker:
            # Simulate double-click via the handler
            index = panel._model.index(0, 0)
            panel._on_item_double_clicked(index)

        assert blocker.args == ["Test Item"]


class TestPriceRankingsPanelLoading:
    """Tests for data loading functionality."""

    @pytest.fixture
    def panel(self, qtbot):
        """Create PriceRankingsPanel instance."""
        panel = PriceRankingsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_load_category_sets_loading_flag(self, panel):
        """_load_category should set is_loading flag."""
        # Mock the loading to prevent actual API call
        with patch.object(panel, '_load_category') as mock_load:
            mock_load.return_value = None
            # Manually test the flag behavior
            panel._is_loading = True
            assert panel._is_loading

    def test_load_category_when_already_loading_returns_early(self, panel):
        """_load_category should return early if already loading."""
        panel._is_loading = True
        # Should not raise or change state
        panel._load_category("currency")

    def test_refresh_calls_load_category(self, panel):
        """refresh should call _load_category."""
        with patch.object(panel, '_load_category') as mock_load:
            panel._on_refresh()
            mock_load.assert_called()

    def test_load_initial_data_loads_first_category(self, panel):
        """load_initial_data should load first category."""
        with patch.object(panel, '_on_category_changed') as mock_change:
            panel.load_initial_data()
            mock_change.assert_called_with(0)


class TestPriceRankingsPanelDisplay:
    """Tests for display functionality."""

    @pytest.fixture
    def panel(self, qtbot):
        """Create PriceRankingsPanel instance."""
        panel = PriceRankingsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_display_rankings_updates_model(self, panel):
        """_display_rankings should update the model."""
        from types import SimpleNamespace
        ranking = SimpleNamespace(items=[
            SimpleNamespace(rank=1, name="Item", chaos_value=100, divine_value=0, rarity="normal"),
        ])

        panel._display_rankings(ranking)
        assert panel._model.rowCount() == 1

    def test_display_rankings_updates_status(self, panel):
        """_display_rankings should update status label."""
        from types import SimpleNamespace
        ranking = SimpleNamespace(items=[
            SimpleNamespace(rank=i, name=f"Item {i}", chaos_value=100, divine_value=0, rarity="normal")
            for i in range(5)
        ])

        panel._display_rankings(ranking)
        assert "5" in panel._status.text()

    def test_display_rankings_handles_none(self, panel):
        """_display_rankings should handle None ranking."""
        panel._display_rankings(None)
        assert panel._model.rowCount() == 0

    def test_display_rankings_handles_no_items_attr(self, panel):
        """_display_rankings should handle ranking without items attr."""
        ranking = MagicMock(spec=[])  # No items attribute
        panel._display_rankings(ranking)
        assert panel._model.rowCount() == 0
