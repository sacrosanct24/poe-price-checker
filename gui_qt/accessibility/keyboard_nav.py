"""
Keyboard Navigation - Enhanced keyboard support for accessibility.

Provides keyboard navigation utilities including arrow key navigation,
dialog shortcuts, and skip links following WCAG 2.2 guidelines.

Usage:
    from gui_qt.accessibility.keyboard_nav import (
        KeyboardNavigator,
        install_arrow_navigation,
        install_dialog_shortcuts,
    )

    # Add arrow navigation to a list/table
    install_arrow_navigation(results_table)

    # Add standard dialog shortcuts
    install_dialog_shortcuts(dialog, on_accept=save, on_reject=cancel)
"""

from typing import Optional, Callable, Sequence

from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QKeyEvent, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QPushButton,
    QTableWidget,
    QTreeWidget,
    QListWidget,
    QTableView,
    QTreeView,
    QListView,
    QAbstractItemView,
    QApplication,
)


class KeyboardNavigator(QObject):
    """
    Event filter for enhanced keyboard navigation.

    Adds arrow key navigation and common shortcuts to widgets.
    """

    def __init__(
        self,
        parent: QWidget,
        *,
        wrap_around: bool = True,
        on_select: Optional[Callable[[int], None]] = None,
        on_activate: Optional[Callable[[int], None]] = None,
    ):
        """
        Initialize keyboard navigator.

        Args:
            parent: Widget to add navigation to
            wrap_around: Whether to wrap from last to first item
            on_select: Callback when selection changes (receives index)
            on_activate: Callback when item is activated (Enter key)
        """
        super().__init__(parent)

        self._parent = parent
        self._wrap_around = wrap_around
        self._on_select = on_select
        self._on_activate = on_activate

        # Install event filter
        parent.installEventFilter(self)

    def eventFilter(self, obj: Optional[QObject], event: Optional[QEvent]) -> bool:
        """Filter keyboard events."""
        if obj is None or event is None:
            return False
        if event.type() != QEvent.Type.KeyPress:
            return super().eventFilter(obj, event)

        key_event = event
        key = key_event.key()
        modifiers = key_event.modifiers()

        # Handle arrow keys
        if key == Qt.Key.Key_Up:
            self._navigate(-1)
            return True
        elif key == Qt.Key.Key_Down:
            self._navigate(1)
            return True
        elif key == Qt.Key.Key_Home:
            self._navigate_to(0)
            return True
        elif key == Qt.Key.Key_End:
            self._navigate_to(-1)  # -1 = last item
            return True
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._activate_current()
            return True

        return super().eventFilter(obj, event)

    def _navigate(self, delta: int) -> None:
        """Navigate by delta items."""
        current = self._get_current_index()
        count = self._get_item_count()

        if count == 0:
            return

        new_index = current + delta

        if self._wrap_around:
            new_index = new_index % count
        else:
            new_index = max(0, min(count - 1, new_index))

        self._set_current_index(new_index)

        if self._on_select:
            self._on_select(new_index)

    def _navigate_to(self, index: int) -> None:
        """Navigate to specific index."""
        count = self._get_item_count()
        if count == 0:
            return

        if index < 0:
            index = count + index  # -1 = last item

        index = max(0, min(count - 1, index))
        self._set_current_index(index)

        if self._on_select:
            self._on_select(index)

    def _activate_current(self) -> None:
        """Activate the current item."""
        if self._on_activate:
            self._on_activate(self._get_current_index())

    def _get_current_index(self) -> int:
        """Get current selection index."""
        if isinstance(self._parent, (QTableWidget, QTableView)):
            return int(self._parent.currentRow())
        elif isinstance(self._parent, (QListWidget, QListView)):
            return int(self._parent.currentRow())
        elif isinstance(self._parent, (QTreeWidget, QTreeView)):
            index = self._parent.currentIndex()
            return int(index.row()) if index.isValid() else 0
        return 0

    def _set_current_index(self, index: int) -> None:
        """Set current selection index."""
        if isinstance(self._parent, (QTableWidget, QTableView)):
            self._parent.selectRow(index)
        elif isinstance(self._parent, QListWidget):
            self._parent.setCurrentRow(index)
        elif isinstance(self._parent, QListView):
            model = self._parent.model()
            if model:
                self._parent.setCurrentIndex(model.index(index, 0))
        elif isinstance(self._parent, (QTreeWidget, QTreeView)):
            model = self._parent.model()
            if model:
                self._parent.setCurrentIndex(model.index(index, 0))

    def _get_item_count(self) -> int:
        """Get total number of items."""
        if isinstance(self._parent, QTableWidget):
            return self._parent.rowCount()
        elif isinstance(self._parent, QTableView):
            model = self._parent.model()
            return model.rowCount() if model else 0
        elif isinstance(self._parent, QListWidget):
            return self._parent.count()
        elif isinstance(self._parent, QListView):
            model = self._parent.model()
            return model.rowCount() if model else 0
        elif isinstance(self._parent, QTreeWidget):
            return self._parent.topLevelItemCount()
        elif isinstance(self._parent, QTreeView):
            model = self._parent.model()
            return model.rowCount() if model else 0
        return 0


def install_arrow_navigation(
    widget: QWidget,
    *,
    wrap_around: bool = True,
    on_select: Optional[Callable[[int], None]] = None,
    on_activate: Optional[Callable[[int], None]] = None,
) -> KeyboardNavigator:
    """
    Install arrow key navigation on a list/table widget.

    Args:
        widget: Widget to add navigation to
        wrap_around: Whether to wrap from last to first
        on_select: Callback when selection changes
        on_activate: Callback when Enter pressed

    Returns:
        KeyboardNavigator instance

    Example:
        nav = install_arrow_navigation(
            results_table,
            on_activate=lambda i: open_item(i)
        )
    """
    return KeyboardNavigator(
        widget,
        wrap_around=wrap_around,
        on_select=on_select,
        on_activate=on_activate,
    )


def install_dialog_shortcuts(
    dialog: QDialog,
    *,
    on_accept: Optional[Callable[[], None]] = None,
    on_reject: Optional[Callable[[], None]] = None,
    accept_key: Qt.Key = Qt.Key.Key_Return,
    reject_key: Qt.Key = Qt.Key.Key_Escape,
) -> None:
    """
    Install standard dialog keyboard shortcuts.

    Adds:
    - Enter/Return: Accept dialog (or trigger on_accept)
    - Escape: Reject dialog (or trigger on_reject)
    - Alt+letter: Button mnemonics

    Args:
        dialog: Dialog to configure
        on_accept: Custom accept handler (default: dialog.accept)
        on_reject: Custom reject handler (default: dialog.reject)
        accept_key: Key for accept action
        reject_key: Key for reject action
    """
    # Escape to close
    escape_shortcut = QShortcut(QKeySequence(reject_key), dialog)
    escape_shortcut.activated.connect(on_reject or dialog.reject)

    # Enter to accept (only if no focused button)
    def maybe_accept():
        focused = dialog.focusWidget()
        if isinstance(focused, QPushButton):
            focused.click()
        elif on_accept:
            on_accept()
        else:
            dialog.accept()

    enter_shortcut = QShortcut(QKeySequence(accept_key), dialog)
    enter_shortcut.activated.connect(maybe_accept)


def add_button_mnemonic(button: QPushButton, letter: str) -> None:
    """
    Add Alt+letter shortcut to a button.

    The button text will show the underlined letter.

    Args:
        button: Button to add mnemonic to
        letter: Letter to use (case-insensitive)

    Example:
        add_button_mnemonic(save_button, "S")  # Alt+S triggers Save
    """
    text = button.text()

    # Find the letter in the text
    letter_lower = letter.lower()
    for i, char in enumerate(text):
        if char.lower() == letter_lower:
            # Insert & before the letter
            new_text = text[:i] + "&" + text[i:]
            button.setText(new_text)
            return

    # Letter not in text, add shortcut anyway
    shortcut = QShortcut(QKeySequence(f"Alt+{letter}"), button.window())
    shortcut.activated.connect(button.click)


def setup_button_mnemonics(buttons: dict[str, QPushButton]) -> None:
    """
    Set up Alt+letter shortcuts for multiple buttons.

    Args:
        buttons: Dictionary of letter -> button

    Example:
        setup_button_mnemonics({
            "S": save_button,
            "C": cancel_button,
            "H": help_button,
        })
    """
    for letter, button in buttons.items():
        add_button_mnemonic(button, letter)


class ArrowNavigationMixin:
    """
    Mixin to add arrow navigation to custom widgets.

    Example:
        class MyList(QWidget, ArrowNavigationMixin):
            def __init__(self):
                super().__init__()
                self.setup_arrow_navigation()

            def get_item_count(self):
                return len(self._items)

            def get_current_index(self):
                return self._selected_index

            def set_current_index(self, index):
                self._selected_index = index
                self.update()
    """

    _arrow_nav_wrap: bool = True
    _arrow_nav_enabled: bool = True

    def setup_arrow_navigation(self, wrap_around: bool = True) -> None:
        """
        Enable arrow key navigation.

        Args:
            wrap_around: Whether to wrap from last to first
        """
        self._arrow_nav_wrap = wrap_around
        self._arrow_nav_enabled = True

        # Make sure widget can receive focus
        if isinstance(self, QWidget):
            if self.focusPolicy() == Qt.FocusPolicy.NoFocus:
                self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle arrow key navigation."""
        if not self._arrow_nav_enabled:
            super().keyPressEvent(event)
            return

        key = event.key()

        if key == Qt.Key.Key_Up:
            self._arrow_navigate(-1)
        elif key == Qt.Key.Key_Down:
            self._arrow_navigate(1)
        elif key == Qt.Key.Key_Home:
            self._arrow_navigate_to(0)
        elif key == Qt.Key.Key_End:
            self._arrow_navigate_to(self.get_item_count() - 1)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.on_item_activated(self.get_current_index())
        else:
            super().keyPressEvent(event)

    def _arrow_navigate(self, delta: int) -> None:
        """Navigate by delta items."""
        count = self.get_item_count()
        if count == 0:
            return

        current = self.get_current_index()
        new_index = current + delta

        if self._arrow_nav_wrap:
            new_index = new_index % count
        else:
            new_index = max(0, min(count - 1, new_index))

        self.set_current_index(new_index)
        self.on_selection_changed(new_index)

    def _arrow_navigate_to(self, index: int) -> None:
        """Navigate to specific index."""
        count = self.get_item_count()
        if count == 0:
            return

        index = max(0, min(count - 1, index))
        self.set_current_index(index)
        self.on_selection_changed(index)

    # Override these in subclasses
    def get_item_count(self) -> int:
        """Get total number of items."""
        return 0

    def get_current_index(self) -> int:
        """Get current selection index."""
        return 0

    def set_current_index(self, index: int) -> None:
        """Set current selection index."""
        pass

    def on_selection_changed(self, index: int) -> None:
        """Called when selection changes."""
        pass

    def on_item_activated(self, index: int) -> None:
        """Called when item is activated (Enter key)."""
        pass


class SkipLink(QPushButton):
    """
    Skip link for keyboard navigation.

    Appears when focused, allows users to skip to main content.
    Common accessibility pattern for screen reader users.
    """

    def __init__(
        self,
        text: str = "Skip to main content",
        target: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize skip link.

        Args:
            text: Link text
            target: Widget to focus when activated
            parent: Parent widget
        """
        super().__init__(text, parent)

        self._target = target

        # Style: invisible until focused
        self.setStyleSheet("""
            QPushButton {
                position: absolute;
                left: -9999px;
                background: #8b5cf6;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:focus {
                left: 8px;
                top: 8px;
                position: relative;
            }
        """)

        self.clicked.connect(self._skip_to_target)

    def set_target(self, target: QWidget) -> None:
        """Set the skip target."""
        self._target = target

    def _skip_to_target(self) -> None:
        """Focus the target widget."""
        if self._target:
            self._target.setFocus()


def create_shortcut(
    parent: QWidget,
    key_sequence: str,
    callback: Callable[[], None],
    context: Qt.ShortcutContext = Qt.ShortcutContext.WidgetShortcut,
) -> QShortcut:
    """
    Create a keyboard shortcut.

    Args:
        parent: Widget the shortcut belongs to
        key_sequence: Key sequence string (e.g., "Ctrl+S", "Alt+F4")
        callback: Function to call when shortcut triggered
        context: Shortcut context (widget, window, or application)

    Returns:
        QShortcut instance

    Example:
        create_shortcut(window, "Ctrl+S", save_document)
    """
    shortcut = QShortcut(QKeySequence(key_sequence), parent)
    shortcut.setContext(context)
    shortcut.activated.connect(callback)
    return shortcut


def create_shortcut_group(
    parent: QWidget,
    shortcuts: dict[str, Callable[[], None]],
) -> list[QShortcut]:
    """
    Create multiple keyboard shortcuts.

    Args:
        parent: Widget the shortcuts belong to
        shortcuts: Dictionary of key sequence -> callback

    Returns:
        List of QShortcut instances

    Example:
        shortcuts = create_shortcut_group(window, {
            "Ctrl+S": save,
            "Ctrl+O": open_file,
            "Ctrl+N": new_file,
        })
    """
    return [
        create_shortcut(parent, key, callback)
        for key, callback in shortcuts.items()
    ]
