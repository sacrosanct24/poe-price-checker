"""Tests for StashGridDialog."""

from unittest.mock import patch
from dataclasses import dataclass
from typing import List


@dataclass
class MockPricedItem:
    """Mock PricedItem for testing."""
    name: str
    type_line: str
    total_price: float
    unit_price: float
    stack_size: int = 1
    rarity: str = "Normal"
    item_class: str = "Currency"
    ilvl: int = 0
    x: int = 0
    y: int = 0
    price_source: str = "poe.ninja"


@dataclass
class MockPricedTab:
    """Mock PricedTab for testing."""
    name: str
    items: List[MockPricedItem]


@dataclass
class MockValuationResult:
    """Mock ValuationResult for testing."""
    tabs: List[MockPricedTab]


class TestStashGridDialogInit:
    """Tests for StashGridDialog initialization."""

    def test_init_with_valuation_result(self, qtbot):
        """Can initialize with valuation result."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [
            MockPricedItem("Chaos Orb", "Currency", 1.0, 1.0, 10),
            MockPricedItem("Exalted Orb", "Currency", 150.0, 150.0),
        ]
        tab = MockPricedTab("Currency Tab", items)
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Stash Grid View"
        assert dialog._result is result
        assert dialog._current_tab is not None

    def test_window_size(self, qtbot):
        """Dialog has correct minimum size."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 900
        assert dialog.minimumHeight() == 700

    def test_creates_tab_combo(self, qtbot):
        """Dialog creates tab selector combo box."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.tab_combo is not None
        assert dialog.tab_combo.minimumWidth() == 250

    def test_creates_grid_widget(self, qtbot):
        """Dialog creates stash grid visualizer widget."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.grid_widget is not None

    def test_creates_details_browser(self, qtbot):
        """Dialog creates details text browser."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.details_browser is not None
        assert dialog.stats_browser is not None


class TestStashGridDialogTabLoading:
    """Tests for tab loading functionality."""

    def test_loads_tabs_into_combo(self, qtbot):
        """Tabs are loaded into combo box with item counts."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items1 = [MockPricedItem("Item1", "Type1", 10.0, 10.0)]
        items2 = [
            MockPricedItem("Item2", "Type2", 5.0, 5.0),
            MockPricedItem("Item3", "Type3", 15.0, 15.0),
        ]
        tab1 = MockPricedTab("Tab 1", items1)
        tab2 = MockPricedTab("Tab 2", items2)
        result = MockValuationResult([tab1, tab2])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.tab_combo.count() == 2
        # Check text includes tab name and item count
        assert "Tab 1" in dialog.tab_combo.itemText(0)
        assert "1 items" in dialog.tab_combo.itemText(0)
        assert "Tab 2" in dialog.tab_combo.itemText(1)
        assert "2 items" in dialog.tab_combo.itemText(1)

    def test_tab_value_formatted_in_combo(self, qtbot):
        """Tab values are formatted correctly in combo text."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        # Test with value >= 1000 (should show as "Xk")
        items_high = [MockPricedItem("Expensive", "Type", 1500.0, 1500.0)]
        tab_high = MockPricedTab("High Value", items_high)

        # Test with value < 1000 (should show as integer)
        items_low = [MockPricedItem("Cheap", "Type", 50.0, 50.0)]
        tab_low = MockPricedTab("Low Value", items_low)

        result = MockValuationResult([tab_high, tab_low])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        # High value should show as "1.5k"
        assert "1.5k" in dialog.tab_combo.itemText(0)

        # Low value should show as "50"
        assert "50c" in dialog.tab_combo.itemText(1)

    def test_total_value_label_updated(self, qtbot):
        """Total value label shows sum of all tabs."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items1 = [MockPricedItem("Item1", "Type", 100.0, 100.0)]
        items2 = [MockPricedItem("Item2", "Type", 200.0, 200.0)]
        tab1 = MockPricedTab("Tab 1", items1)
        tab2 = MockPricedTab("Tab 2", items2)
        result = MockValuationResult([tab1, tab2])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        label_text = dialog.total_value_label.text()
        assert "Total Stash Value" in label_text
        assert "300" in label_text

    def test_selects_first_tab_on_init(self, qtbot):
        """First tab is selected automatically on init."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [MockPricedItem("Item", "Type", 10.0, 10.0)]
        tab = MockPricedTab("Test Tab", items)
        result = MockValuationResult([tab])

        with patch.object(StashGridDialog, '_on_tab_changed'):
            dialog = StashGridDialog(result)
            qtbot.addWidget(dialog)

            # First tab should be current
            assert dialog.tab_combo.currentIndex() == 0

    def test_empty_tabs_list(self, qtbot):
        """Handles empty tabs list gracefully."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        assert dialog.tab_combo.count() == 0
        assert dialog.total_value_label.text() == "Total Stash Value: 0c"


class TestStashGridDialogTabChange:
    """Tests for tab change handling."""

    def test_on_tab_changed_loads_grid(self, qtbot):
        """Changing tab loads grid widget."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [MockPricedItem("Item", "Type", 10.0, 10.0)]
        tab = MockPricedTab("Test Tab", items)
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        # Grid widget should be loaded with tab
        assert dialog.grid_widget is not None
        # Just verify it doesn't crash when changing tabs

    def test_updates_current_tab_reference(self, qtbot):
        """Changing tab updates _current_tab reference."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items1 = [MockPricedItem("Item1", "Type", 10.0, 10.0)]
        items2 = [MockPricedItem("Item2", "Type", 20.0, 20.0)]
        tab1 = MockPricedTab("Tab 1", items1)
        tab2 = MockPricedTab("Tab 2", items2)
        result = MockValuationResult([tab1, tab2])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        # Initially first tab
        assert dialog._current_tab.name == "Tab 1"

        # Change to second tab
        dialog.tab_combo.setCurrentIndex(1)
        assert dialog._current_tab.name == "Tab 2"


class TestStashGridDialogItemSelection:
    """Tests for item selection and details display."""

    def test_shows_no_selection_placeholder(self, qtbot):
        """Shows placeholder text when no item selected."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        html = dialog.details_browser.toHtml()
        assert "Click an item in the grid" in html

    def test_on_item_selected_shows_details(self, qtbot):
        """Selecting item displays details."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        # Simulate item selection
        item = MockPricedItem(
            name="Chaos Orb",
            type_line="Currency",
            total_price=10.0,
            unit_price=1.0,
            stack_size=10,
        )

        dialog._on_item_selected(item)

        # Details should be shown
        html = dialog.details_browser.toHtml()
        assert "Chaos Orb" in html
        assert "10.0c" in html

    def test_shows_item_details_with_name(self, qtbot):
        """Item details show name and type line."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        item = MockPricedItem(
            name="Tabula Rasa",
            type_line="Simple Robe",
            total_price=10.0,
            unit_price=10.0,
            rarity="Unique",
        )

        dialog._show_item_details(item)

        html = dialog.details_browser.toHtml()
        assert "Tabula Rasa" in html
        assert "Simple Robe" in html

    def test_shows_item_details_stacked(self, qtbot):
        """Item details show stack size for stacked items."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        item = MockPricedItem(
            name="Chaos Orb",
            type_line="Currency",
            total_price=50.0,
            unit_price=1.0,
            stack_size=50,
        )

        dialog._show_item_details(item)

        html = dialog.details_browser.toHtml()
        assert "Stack Size" in html
        assert "50" in html
        assert "Total Value" in html

    def test_shows_item_properties(self, qtbot):
        """Item details show properties like rarity and ilvl."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        item = MockPricedItem(
            name="Test Item",
            type_line="Test Type",
            total_price=10.0,
            unit_price=10.0,
            rarity="Rare",
            item_class="Helmet",
            ilvl=85,
            x=5,
            y=3,
        )

        dialog._show_item_details(item)

        html = dialog.details_browser.toHtml()
        assert "Rare" in html
        assert "Helmet" in html
        assert "85" in html  # ilvl
        assert "(5, 3)" in html  # position


class TestStashGridDialogTabStats:
    """Tests for tab statistics display."""

    def test_updates_tab_stats(self, qtbot):
        """Tab statistics are updated when tab changes."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [
            MockPricedItem("Item1", "Type", 1000.0, 1000.0),  # exceptional
            MockPricedItem("Item2", "Type", 100.0, 100.0),    # high
            MockPricedItem("Item3", "Type", 10.0, 10.0),      # medium
        ]
        tab = MockPricedTab("Test Tab", items)
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        dialog._update_tab_stats()

        html = dialog.stats_browser.toHtml()
        assert "Value Distribution" in html

    def test_value_tier_counts(self, qtbot):
        """Stats show correct value tier counts."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [
            MockPricedItem("Exceptional", "Type", 1500.0, 1500.0),  # >= 1000
            MockPricedItem("Very High", "Type", 500.0, 500.0),      # >= 200
            MockPricedItem("High", "Type", 75.0, 75.0),             # >= 50
            MockPricedItem("Medium", "Type", 20.0, 20.0),           # >= 5
            MockPricedItem("Low", "Type", 2.0, 2.0),                # >= 1
            MockPricedItem("Vendor", "Type", 0.5, 0.5),             # < 1
        ]
        tab = MockPricedTab("Test Tab", items)
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        dialog._current_tab = tab
        dialog._update_tab_stats()

        text = dialog.stats_browser.toPlainText()
        # Should show counts for different tiers
        assert ">1000c" in text
        assert "200-1000c" in text
        assert "50-200c" in text

    def test_rarity_breakdown(self, qtbot):
        """Stats show rarity breakdown."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        items = [
            MockPricedItem("Unique1", "Type", 10.0, 10.0, rarity="Unique"),
            MockPricedItem("Unique2", "Type", 20.0, 20.0, rarity="Unique"),
            MockPricedItem("Rare1", "Type", 5.0, 5.0, rarity="Rare"),
        ]
        tab = MockPricedTab("Test Tab", items)
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        dialog._current_tab = tab
        dialog._update_tab_stats()

        html = dialog.stats_browser.toHtml()
        assert "Rarity Breakdown" in html
        assert "Unique: 2" in html
        assert "Rare: 1" in html

    def test_empty_tab_stats(self, qtbot):
        """Empty tab shows no stats."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        tab = MockPricedTab("Empty Tab", [])
        result = MockValuationResult([tab])

        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        dialog._current_tab = tab
        dialog._update_tab_stats()

        # Should handle empty gracefully
        html = dialog.stats_browser.toHtml()
        assert "Value Distribution" in html


class TestStashGridDialogCloseButton:
    """Tests for close button."""

    def test_close_button_accepts_dialog(self, qtbot):
        """Close button accepts dialog."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            # Find close button
            from PyQt6.QtWidgets import QPushButton
            close_btn = None
            for btn in dialog.findChildren(QPushButton):
                if btn.text() == "Close":
                    close_btn = btn
                    break
            assert close_btn is not None
            close_btn.click()


class TestStashGridDialogSplitter:
    """Tests for splitter layout."""

    def test_splitter_proportions(self, qtbot):
        """Splitter has correct initial proportions (70/30)."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog
        from PyQt6.QtWidgets import QSplitter

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        # Find splitter
        splitter = dialog.findChild(QSplitter)
        assert splitter is not None

        # Check initial sizes (should be [700, 300])
        sizes = splitter.sizes()
        assert len(sizes) == 2
        # Proportions should be roughly 70/30
        total = sum(sizes)
        if total > 0:
            left_percent = sizes[0] / total
            assert 0.6 < left_percent < 0.8  # Allow some variance


class TestStashGridDialogWindowIcon:
    """Tests for window icon application."""

    @patch('gui_qt.dialogs.stash_grid_dialog.apply_window_icon')
    def test_applies_window_icon(self, mock_apply_icon, qtbot):
        """Window icon is applied on initialization."""
        from gui_qt.dialogs.stash_grid_dialog import StashGridDialog

        result = MockValuationResult([])
        dialog = StashGridDialog(result)
        qtbot.addWidget(dialog)

        mock_apply_icon.assert_called_once_with(dialog)
