"""Tests for CommandPaletteDialog."""

from unittest.mock import MagicMock
from PyQt6.QtCore import Qt


class TestCommandPaletteDialogInit:
    """Tests for CommandPaletteDialog initialization."""

    def test_init_with_actions(self, qtbot):
        """Can initialize with action list."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Test Action",
                "description": "Does something",
                "shortcut": "Ctrl+T",
                "category": "Testing",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Command Palette"
        assert dialog._actions == actions
        assert dialog._filtered_actions == actions

    def test_init_with_empty_actions(self, qtbot):
        """Can initialize with empty action list."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        assert dialog._actions == []
        assert dialog._filtered_actions == []

    def test_window_size(self, qtbot):
        """Dialog has correct size constraints."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 500
        assert dialog.minimumHeight() == 400
        assert dialog.maximumWidth() == 700
        assert dialog.maximumHeight() == 600

    def test_frameless_window(self, qtbot):
        """Dialog is frameless popup."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        flags = dialog.windowFlags()
        assert Qt.WindowType.Popup in flags or Qt.WindowType.FramelessWindowHint in flags


class TestCommandPaletteDialogWidgets:
    """Tests for widget creation."""

    def test_has_search_input(self, qtbot):
        """Dialog has search input field."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        assert dialog._search_input is not None
        assert dialog._search_input.placeholderText() == "Type to search commands..."

    def test_has_list_widget(self, qtbot):
        """Dialog has list widget for results."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        assert dialog._list is not None

    def test_search_input_focused_on_show(self, qtbot):
        """Search input is focused when dialog shown."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        dialog.show()
        qtbot.waitExposed(dialog)

        assert dialog._search_input.hasFocus()


class TestCommandPaletteDialogPopulateList:
    """Tests for list population."""

    def test_populates_list_on_init(self, qtbot):
        """List is populated with actions on init."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Action 1",
                "description": "First action",
                "shortcut": "Ctrl+1",
                "category": "Test",
            },
            {
                "id": "action2",
                "name": "Action 2",
                "description": "Second action",
                "shortcut": "Ctrl+2",
                "category": "Test",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        assert dialog._list.count() == 2

    def test_stores_action_id_in_item_data(self, qtbot):
        """List items store action ID in UserRole."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "test_action",
                "name": "Test",
                "description": "Test action",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        item = dialog._list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == "test_action"

    def test_first_item_selected_by_default(self, qtbot):
        """First item is selected by default."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Action 1",
                "description": "First",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        assert dialog._list.currentRow() == 0


class TestCommandPaletteDialogSearch:
    """Tests for search functionality."""

    def test_search_filters_by_name(self, qtbot):
        """Search filters actions by name."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "copy",
                "name": "Copy Item",
                "description": "Copy to clipboard",
                "shortcut": "Ctrl+C",
                "category": "Edit",
            },
            {
                "id": "paste",
                "name": "Paste Item",
                "description": "Paste from clipboard",
                "shortcut": "Ctrl+V",
                "category": "Edit",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Search for "copy"
        dialog._search_input.setText("copy")

        assert dialog._list.count() == 1
        assert dialog._list.item(0).data(Qt.ItemDataRole.UserRole) == "copy"

    def test_search_is_case_insensitive(self, qtbot):
        """Search is case insensitive."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "test",
                "name": "Test Action",
                "description": "Test",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Search with different cases
        dialog._search_input.setText("TEST")
        assert dialog._list.count() == 1

        dialog._search_input.setText("test")
        assert dialog._list.count() == 1

        dialog._search_input.setText("TeSt")
        assert dialog._list.count() == 1

    def test_search_filters_by_description(self, qtbot):
        """Search filters by description."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Action 1",
                "description": "Does something unique",
                "shortcut": "",
                "category": "Test",
            },
            {
                "id": "action2",
                "name": "Action 2",
                "description": "Does something else",
                "shortcut": "",
                "category": "Test",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("unique")
        assert dialog._list.count() == 1
        assert dialog._list.item(0).data(Qt.ItemDataRole.UserRole) == "action1"

    def test_search_filters_by_category(self, qtbot):
        """Search filters by category."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "file_open",
                "name": "Open File",
                "description": "Open a file",
                "shortcut": "",
                "category": "File",
            },
            {
                "id": "edit_copy",
                "name": "Copy",
                "description": "Copy text",
                "shortcut": "",
                "category": "Edit",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("file")
        # Should match both category "File" and name "Open File"
        assert dialog._list.count() >= 1

    def test_empty_search_shows_all_actions(self, qtbot):
        """Empty search shows all actions."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Action 1",
                "description": "First",
                "shortcut": "",
                "category": "Test",
            },
            {
                "id": "action2",
                "name": "Action 2",
                "description": "Second",
                "shortcut": "",
                "category": "Test",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Enter search then clear it
        dialog._search_input.setText("action1")
        assert dialog._list.count() == 1

        dialog._search_input.setText("")
        assert dialog._list.count() == 2

    def test_no_matches_shows_empty_list(self, qtbot):
        """No matches shows empty list."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "action1",
                "name": "Action 1",
                "description": "First",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("nonexistent")
        assert dialog._list.count() == 0


class TestCommandPaletteDialogScoring:
    """Tests for match scoring algorithm."""

    def test_exact_name_match_scores_highest(self, qtbot):
        """Exact name match scores highest."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "test",
                "name": "test",
                "description": "Exact match",
                "shortcut": "",
                "category": "Test",
            },
            {
                "id": "test_action",
                "name": "Test Action",
                "description": "Contains test",
                "shortcut": "",
                "category": "Test",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("test")

        # Exact match should be first
        assert dialog._list.item(0).data(Qt.ItemDataRole.UserRole) == "test"

    def test_starts_with_scores_higher_than_contains(self, qtbot):
        """Starts with query scores higher than contains."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "copy_item",
                "name": "Copy Item",
                "description": "Copy",
                "shortcut": "",
                "category": "Edit",
            },
            {
                "id": "recopy",
                "name": "Item Copy",
                "description": "Copy again",
                "shortcut": "",
                "category": "Edit",
            },
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("copy")

        # "Copy Item" starts with "copy", should be first
        assert dialog._list.item(0).data(Qt.ItemDataRole.UserRole) == "copy_item"


class TestCommandPaletteDialogFuzzyMatch:
    """Tests for fuzzy matching."""

    def test_fuzzy_match_checks_char_order(self, qtbot):
        """Fuzzy match checks if chars appear in order."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        # Should match
        assert dialog._fuzzy_match("cp", "copy") is True
        assert dialog._fuzzy_match("cpy", "copy") is True
        assert dialog._fuzzy_match("opy", "copy") is True

        # Should not match (wrong order)
        assert dialog._fuzzy_match("pc", "copy") is False
        assert dialog._fuzzy_match("yc", "copy") is False

    def test_fuzzy_match_with_spaces(self, qtbot):
        """Fuzzy match works with spaces in text."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        assert dialog._fuzzy_match("oi", "open item") is True
        assert dialog._fuzzy_match("openit", "open item") is True


class TestCommandPaletteDialogExecution:
    """Tests for action execution."""

    def test_enter_key_executes_selected_action(self, qtbot):
        """Enter key executes selected action."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "test_action",
                "name": "Test",
                "description": "Test",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Press enter
        dialog._search_input.returnPressed.emit()

        callback.assert_called_once_with("test_action")

    def test_double_click_executes_action(self, qtbot):
        """Double-clicking item executes action."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "clicked_action",
                "name": "Clicked",
                "description": "Test",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        item = dialog._list.item(0)
        dialog._on_item_double_clicked(item)

        callback.assert_called_once_with("clicked_action")

    def test_execution_closes_dialog(self, qtbot):
        """Executing action accepts (closes) dialog."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        actions = [
            {
                "id": "test_action",
                "name": "Test",
                "description": "Test",
                "shortcut": "",
                "category": "Test",
            }
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            dialog._search_input.returnPressed.emit()


class TestCommandPaletteDialogKeyNavigation:
    """Tests for keyboard navigation."""

    def test_escape_closes_dialog(self, qtbot):
        """Escape key closes dialog."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        callback = MagicMock()
        dialog = CommandPaletteDialog([], callback)
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
            dialog.keyPressEvent(event)

    def test_up_arrow_moves_selection_up(self, qtbot):
        """Up arrow key moves selection up."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        actions = [
            {"id": "action1", "name": "Action 1", "description": "", "shortcut": "", "category": ""},
            {"id": "action2", "name": "Action 2", "description": "", "shortcut": "", "category": ""},
            {"id": "action3", "name": "Action 3", "description": "", "shortcut": "", "category": ""},
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Select second item
        dialog._list.setCurrentRow(1)
        assert dialog._list.currentRow() == 1

        # Press up arrow
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        assert dialog._list.currentRow() == 0

    def test_down_arrow_moves_selection_down(self, qtbot):
        """Down arrow key moves selection down."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        actions = [
            {"id": "action1", "name": "Action 1", "description": "", "shortcut": "", "category": ""},
            {"id": "action2", "name": "Action 2", "description": "", "shortcut": "", "category": ""},
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # First item selected by default
        assert dialog._list.currentRow() == 0

        # Press down arrow
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        assert dialog._list.currentRow() == 1

    def test_up_arrow_at_top_stays_at_top(self, qtbot):
        """Up arrow at first item stays at first."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        actions = [
            {"id": "action1", "name": "Action 1", "description": "", "shortcut": "", "category": ""},
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        assert dialog._list.currentRow() == 0

        # Press up arrow
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        # Should still be at 0
        assert dialog._list.currentRow() == 0

    def test_down_arrow_at_bottom_stays_at_bottom(self, qtbot):
        """Down arrow at last item stays at last."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent

        actions = [
            {"id": "action1", "name": "Action 1", "description": "", "shortcut": "", "category": ""},
            {"id": "action2", "name": "Action 2", "description": "", "shortcut": "", "category": ""},
        ]

        callback = MagicMock()
        dialog = CommandPaletteDialog(actions, callback)
        qtbot.addWidget(dialog)

        # Move to last item
        dialog._list.setCurrentRow(1)
        assert dialog._list.currentRow() == 1

        # Press down arrow
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        dialog.keyPressEvent(event)

        # Should still be at 1
        assert dialog._list.currentRow() == 1


class TestCommandPaletteItemWidget:
    """Tests for CommandPaletteItem widget."""

    def test_creates_item_widget(self, qtbot):
        """CommandPaletteItem widget is created."""
        from gui_qt.dialogs.command_palette import CommandPaletteItem

        widget = CommandPaletteItem(
            name="Test Action",
            description="Does something",
            shortcut="Ctrl+T",
            category="Testing",
        )
        qtbot.addWidget(widget)

        assert widget is not None

    def test_item_widget_without_shortcut(self, qtbot):
        """CommandPaletteItem works without shortcut."""
        from gui_qt.dialogs.command_palette import CommandPaletteItem

        widget = CommandPaletteItem(
            name="Test",
            description="Test",
            shortcut="",
            category="Test",
        )
        qtbot.addWidget(widget)

        assert widget is not None


class TestCommandPaletteDialogMatchScore:
    """Tests for _match_score method."""

    def test_match_score_returns_zero_for_no_match(self, qtbot):
        """Match score returns 0 for no match."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        action = {
            "name": "Copy",
            "description": "Copy to clipboard",
            "category": "Edit",
        }

        score = dialog._match_score("paste", action)
        assert score == 0

    def test_match_score_for_exact_match(self, qtbot):
        """Match score is high for exact name match."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        action = {
            "name": "copy",
            "description": "Copy to clipboard",
            "category": "Edit",
        }

        score = dialog._match_score("copy", action)
        assert score >= 100

    def test_match_score_for_starts_with(self, qtbot):
        """Match score is good for starts with match."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        action = {
            "name": "Copy Item",
            "description": "Copy",
            "category": "Edit",
        }

        score = dialog._match_score("copy", action)
        # Score can be higher due to multiple matches (starts with, contains in description, etc.)
        assert score >= 60  # At least 60 for starts with match

    def test_match_score_for_contains(self, qtbot):
        """Match score exists for contains match."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog

        dialog = CommandPaletteDialog([], MagicMock())
        qtbot.addWidget(dialog)

        action = {
            "name": "Item Copy",
            "description": "Copy",
            "category": "Edit",
        }

        score = dialog._match_score("copy", action)
        assert score > 0
