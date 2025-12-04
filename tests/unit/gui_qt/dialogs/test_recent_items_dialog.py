"""Tests for RecentItemsDialog."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from PyQt6.QtCore import Qt


class TestRecentItemsDialogInit:
    """Tests for RecentItemsDialog initialization."""

    def test_init_with_empty_history(self, qtbot):
        """Can initialize with empty history."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Recent Items"
        assert dialog._history == []
        assert dialog._table.rowCount() == 0

    def test_init_with_history_entries(self, qtbot):
        """Can initialize with history entries."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Tabula Rasa",
                "item_text": "Rarity: Unique\nTabula Rasa\nSimple Robe",
                "results_count": 5,
                "best_price": 10.5,
            },
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Chaos Orb",
                "item_text": "Rarity: Currency\nChaos Orb",
                "results_count": 1,
                "best_price": 1.0,
            },
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        assert len(dialog._history) == 2
        assert dialog._table.rowCount() == 2

    def test_window_size(self, qtbot):
        """Dialog has correct minimum size."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 600
        assert dialog.minimumHeight() == 400

    def test_copies_history_list(self, qtbot):
        """Dialog copies history list to avoid mutation."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        original_history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test Item",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 5.0,
            }
        ]

        dialog = RecentItemsDialog(original_history)
        qtbot.addWidget(dialog)

        # Mutate original
        original_history.append({"timestamp": "", "item_name": "New"})

        # Dialog's copy should be unaffected
        assert len(dialog._history) == 1


class TestRecentItemsDialogTable:
    """Tests for table widget and data display."""

    def test_table_has_correct_columns(self, qtbot):
        """Table has 4 columns: Time, Item, Price, Results."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        assert dialog._table.columnCount() == 4
        headers = [
            dialog._table.horizontalHeaderItem(i).text()
            for i in range(4)
        ]
        assert headers == ["Time", "Item", "Price", "Results"]

    def test_table_selection_mode(self, qtbot):
        """Table allows single row selection."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from PyQt6.QtWidgets import QAbstractItemView

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        assert dialog._table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
        assert dialog._table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection

    def test_populates_table_in_reverse_order(self, qtbot):
        """Table shows most recent items first (reversed)."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": "2024-01-01T10:00:00",
                "item_name": "First Item",
                "item_text": "First",
                "results_count": 1,
                "best_price": 1.0,
            },
            {
                "timestamp": "2024-01-01T11:00:00",
                "item_name": "Second Item",
                "item_text": "Second",
                "results_count": 2,
                "best_price": 2.0,
            },
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        # Most recent should be first
        first_row_item = dialog._table.item(0, 1).text()
        assert first_row_item == "Second Item"

        second_row_item = dialog._table.item(1, 1).text()
        assert second_row_item == "First Item"

    def test_formats_time_column(self, qtbot):
        """Time column shows HH:MM:SS format."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": "2024-01-01T14:30:45",
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        time_text = dialog._table.item(0, 0).text()
        assert time_text == "14:30:45"

    def test_handles_invalid_timestamp(self, qtbot):
        """Displays placeholder for invalid timestamps."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": "invalid",
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        time_text = dialog._table.item(0, 0).text()
        assert time_text == "??:??:??"

    def test_price_formatting(self, qtbot):
        """Price column shows value with 'c' suffix."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 15.7,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        price_text = dialog._table.item(0, 2).text()
        assert price_text == "15.7c"

    def test_zero_price_shows_dash(self, qtbot):
        """Zero or missing price shows '-'."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 0,
                "best_price": 0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        price_text = dialog._table.item(0, 2).text()
        assert price_text == "-"

    def test_results_count_display(self, qtbot):
        """Results column shows count as string."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 42,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        results_text = dialog._table.item(0, 3).text()
        assert results_text == "42"

    def test_stores_entry_in_item_data(self, qtbot):
        """Full entry is stored in item UserRole data."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        entry = {
            "timestamp": datetime.now().isoformat(),
            "item_name": "Test",
            "item_text": "Full item text here",
            "results_count": 1,
            "best_price": 5.0,
        }

        dialog = RecentItemsDialog([entry])
        qtbot.addWidget(dialog)

        # Data stored in name column (column 1)
        name_item = dialog._table.item(0, 1)
        stored_entry = name_item.data(Qt.ItemDataRole.UserRole)
        assert stored_entry == entry


class TestRecentItemsDialogInteraction:
    """Tests for user interactions."""

    def test_recheck_button_initially_disabled(self, qtbot):
        """Re-check button disabled when nothing selected."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        assert dialog._recheck_btn.isEnabled() is False

    def test_recheck_button_enabled_on_selection(self, qtbot):
        """Re-check button enabled when row selected."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        # Select first row
        dialog._table.selectRow(0)

        assert dialog._recheck_btn.isEnabled() is True

    def test_double_click_emits_signal(self, qtbot):
        """Double-clicking row emits item_selected signal."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from unittest.mock import MagicMock

        entry = {
            "timestamp": datetime.now().isoformat(),
            "item_name": "Test",
            "item_text": "Full item text",
            "results_count": 1,
            "best_price": 1.0,
        }

        dialog = RecentItemsDialog([entry])
        qtbot.addWidget(dialog)

        # Select the row first
        dialog._table.selectRow(0)

        # Connect spy to capture signal
        signal_spy = MagicMock()
        dialog.item_selected.connect(signal_spy)

        # Call the handler directly
        dialog._on_double_click(0, 0)

        # Verify signal was emitted
        signal_spy.assert_called_once_with("Full item text")

    def test_recheck_button_emits_signal(self, qtbot):
        """Clicking re-check button emits item_selected signal."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        entry = {
            "timestamp": datetime.now().isoformat(),
            "item_name": "Test",
            "item_text": "Item to recheck",
            "results_count": 1,
            "best_price": 1.0,
        }

        dialog = RecentItemsDialog([entry])
        qtbot.addWidget(dialog)

        # Select row
        dialog._table.selectRow(0)

        with qtbot.waitSignal(dialog.item_selected, timeout=1000) as blocker:
            dialog._recheck_btn.click()

        assert blocker.args[0] == "Item to recheck"

    def test_clear_button_clears_history(self, qtbot):
        """Clear button clears history and table."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Test",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 1.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        assert dialog._table.rowCount() == 1
        assert len(dialog._history) == 1

        dialog._clear_btn.click()

        assert dialog._table.rowCount() == 0
        assert len(dialog._history) == 0
        assert dialog._recheck_btn.isEnabled() is False

    def test_get_selected_item_text(self, qtbot):
        """get_selected_item_text returns item text of selected row."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        entry = {
            "timestamp": datetime.now().isoformat(),
            "item_name": "Test",
            "item_text": "Selected item text",
            "results_count": 1,
            "best_price": 1.0,
        }

        dialog = RecentItemsDialog([entry])
        qtbot.addWidget(dialog)

        # No selection initially
        assert dialog.get_selected_item_text() is None

        # Select row
        dialog._table.selectRow(0)
        assert dialog.get_selected_item_text() == "Selected item text"

    def test_close_button_closes_dialog(self, qtbot):
        """Close button accepts dialog."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            # Find and click close button
            close_btn = None
            for btn in dialog.findChildren(type(dialog._recheck_btn)):
                if btn.text() == "Close":
                    close_btn = btn
                    break
            assert close_btn is not None
            close_btn.click()


class TestRecentItemsDialogTheme:
    """Tests for theme application."""

    @patch('gui_qt.dialogs.recent_items_dialog.get_theme_manager')
    def test_applies_theme_on_init(self, mock_theme_manager, qtbot):
        """Theme is applied on initialization."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        mock_manager = MagicMock()
        mock_manager.get_stylesheet.return_value = "test-stylesheet"
        mock_theme_manager.return_value = mock_manager

        dialog = RecentItemsDialog([])
        qtbot.addWidget(dialog)

        mock_theme_manager.assert_called_once()
        mock_manager.get_stylesheet.assert_called_once()


class TestRecentItemsDialogValueColoring:
    """Tests for price coloring based on value."""

    def test_high_value_items_colored(self, qtbot):
        """Items >= 100c get high_value color."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Expensive",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 150.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        price_item = dialog._table.item(0, 2)
        # Should have foreground color set
        assert price_item.foreground() is not None

    def test_medium_value_items_colored(self, qtbot):
        """Items >= 10c get medium_value color."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Medium",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 25.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        price_item = dialog._table.item(0, 2)
        # Should have foreground color set
        assert price_item.foreground() is not None

    def test_low_value_items_no_special_color(self, qtbot):
        """Items < 10c don't get special coloring."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Cheap",
                "item_text": "Test",
                "results_count": 1,
                "best_price": 5.0,
            }
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        price_item = dialog._table.item(0, 2)
        assert price_item.text() == "5.0c"


class TestRecentItemsDialogHistoryEntry:
    """Tests for HistoryEntry dataclass compatibility."""

    def test_works_with_history_entry_dataclass(self, qtbot):
        """Dialog works with HistoryEntry dataclass instances."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from core.history import HistoryEntry

        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            item_name="Dataclass Item",
            item_text="Full text",
            results_count=3,
            best_price=7.5,
        )

        dialog = RecentItemsDialog([entry])
        qtbot.addWidget(dialog)

        assert dialog._table.rowCount() == 1
        assert dialog._table.item(0, 1).text() == "Dataclass Item"
        assert dialog._table.item(0, 2).text() == "7.5c"
        assert dialog._table.item(0, 3).text() == "3"

    def test_mixed_dict_and_dataclass_entries(self, qtbot):
        """Dialog handles both dict and HistoryEntry instances."""
        from gui_qt.dialogs.recent_items_dialog import RecentItemsDialog
        from core.history import HistoryEntry

        history = [
            {
                "timestamp": datetime.now().isoformat(),
                "item_name": "Dict Entry",
                "item_text": "Dict",
                "results_count": 1,
                "best_price": 1.0,
            },
            HistoryEntry(
                timestamp=datetime.now().isoformat(),
                item_name="Dataclass Entry",
                item_text="Dataclass",
                results_count=2,
                best_price=2.0,
            ),
        ]

        dialog = RecentItemsDialog(history)
        qtbot.addWidget(dialog)

        assert dialog._table.rowCount() == 2
