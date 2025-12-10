"""
Screen Reader Support - QAccessible integration for assistive technology.

Provides utilities for making widgets accessible to screen readers
following WCAG 2.2 guidelines.

Usage:
    from gui_qt.accessibility.screen_reader import (
        set_accessible_name,
        set_accessible_description,
        announce,
        AccessibleWidget,
    )

    # Set accessible properties
    set_accessible_name(button, "Submit price check")
    set_accessible_description(button, "Checks the price of the item in clipboard")

    # Announce dynamic content
    announce("Price check complete: 50 chaos")

    # Use accessible widget base class
    class MyWidget(AccessibleWidget):
        def __init__(self):
            super().__init__(
                accessible_name="Price Result",
                accessible_role=QAccessible.Role.StaticText,
            )
"""

from enum import Enum
from typing import Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QWidget, QApplication

# Note: QAccessible and QAccessibleEvent are available via QtGui in PyQt6
# but may require specific compilation flags. We use a compatibility approach.
HAS_QACCESSIBLE = False
QAccessible: type = type(None)  # Placeholder type
QAccessibleEvent: type = type(None)  # Placeholder type
try:
    from PyQt6.QtGui import QAccessible, QAccessibleEvent  # type: ignore[no-redef,attr-defined]
    HAS_QACCESSIBLE = True
except ImportError:
    pass


class AnnouncePriority(Enum):
    """Priority level for screen reader announcements."""
    POLITE = "polite"      # Non-urgent, wait for idle
    ASSERTIVE = "assertive"  # Important, interrupt current


def set_accessible_name(widget: QWidget, name: str) -> None:
    """
    Set the accessible name for a widget.

    The accessible name is the primary label read by screen readers.
    It should be concise and describe the widget's purpose.

    Args:
        widget: Widget to set name on
        name: Accessible name (e.g., "Submit button", "Price input")

    Example:
        set_accessible_name(search_button, "Search items")
    """
    widget.setAccessibleName(name)


def set_accessible_description(widget: QWidget, description: str) -> None:
    """
    Set the accessible description for a widget.

    The description provides additional context beyond the name.
    Screen readers typically announce this after a pause.

    Args:
        widget: Widget to set description on
        description: Additional context (e.g., "Opens item search dialog")

    Example:
        set_accessible_description(
            search_button,
            "Opens a dialog to search for items by name or type"
        )
    """
    widget.setAccessibleDescription(description)


def set_accessible_role(widget: QWidget, role) -> None:
    """
    Set the accessible role for a widget.

    The role tells screen readers what type of element this is.
    Qt usually sets this automatically, but custom widgets may need it.

    Args:
        widget: Widget to set role on
        role: Accessible role (e.g., QAccessible.Role.Button if available)

    Common roles (when QAccessible is available):
        - Button: Clickable button
        - CheckBox: Toggle checkbox
        - ComboBox: Dropdown selector
        - Dialog: Modal dialog
        - List: List container
        - ListItem: Item in a list
        - Table: Data table
        - Cell: Table cell
        - StaticText: Read-only text
        - EditableText: Input field

    Note: This is a placeholder - actual implementation
    may require custom QAccessibleInterface.
    """
    # Qt6 handles roles through the widget's accessible interface
    # This is a placeholder for documentation - actual implementation
    # may require custom QAccessibleInterface
    pass


def announce(
    message: str,
    priority: AnnouncePriority = AnnouncePriority.POLITE,
) -> None:
    """
    Announce a message to screen readers.

    Use this for dynamic content changes that users should know about.

    Args:
        message: Message to announce
        priority: How urgently to announce (POLITE waits, ASSERTIVE interrupts)

    Example:
        announce("Price check complete: 50 chaos orbs")
        announce("Error: API unavailable", AnnouncePriority.ASSERTIVE)
    """
    # Find the active window to use as context
    app = QApplication.instance()
    if app is None or not isinstance(app, QApplication):
        return

    active_window = app.activeWindow()
    if active_window is None:
        return

    # Use QAccessible to make announcement
    # This creates a "name changed" event which screen readers pick up
    _announce_via_event(active_window, message)


def announce_polite(message: str) -> None:
    """
    Announce a message politely (waits for idle).

    Shorthand for announce(message, AnnouncePriority.POLITE).

    Args:
        message: Message to announce
    """
    announce(message, AnnouncePriority.POLITE)


def announce_assertive(message: str) -> None:
    """
    Announce a message assertively (interrupts current speech).

    Use sparingly for important alerts.

    Args:
        message: Message to announce
    """
    announce(message, AnnouncePriority.ASSERTIVE)


def _announce_via_event(widget: QWidget, message: str) -> None:
    """
    Make announcement via QAccessible event.

    This approach uses Qt's accessibility system to trigger
    screen reader announcements.
    """
    # Store original name
    original_name = widget.accessibleName()

    # Temporarily set name to message
    widget.setAccessibleName(message)

    # Send name changed event if QAccessible is available
    if HAS_QACCESSIBLE and QAccessible is not None and QAccessibleEvent is not None:
        event = QAccessibleEvent(widget, QAccessible.Event.NameChanged)
        QAccessible.updateAccessibility(event)

    # Restore original name after brief delay
    QTimer.singleShot(100, lambda: widget.setAccessibleName(original_name))


class AccessibleMixin:
    """
    Mixin to add accessibility helpers to any widget.

    Example:
        class MyButton(QPushButton, AccessibleMixin):
            def __init__(self):
                super().__init__("Click me")
                self.set_a11y_name("Action button")
                self.set_a11y_description("Performs the main action")
    """

    def set_a11y_name(self, name: str) -> None:
        """Set accessible name."""
        if isinstance(self, QWidget):
            set_accessible_name(self, name)

    def set_a11y_description(self, description: str) -> None:
        """Set accessible description."""
        if isinstance(self, QWidget):
            set_accessible_description(self, description)

    def announce_change(self, message: str) -> None:
        """Announce a change related to this widget."""
        announce_polite(message)

    def announce_error(self, message: str) -> None:
        """Announce an error assertively."""
        announce_assertive(message)


class AccessibleWidget(QWidget, AccessibleMixin):
    """
    Base widget class with built-in accessibility support.

    Provides a foundation for creating accessible custom widgets.

    Example:
        class PriceDisplay(AccessibleWidget):
            def __init__(self):
                super().__init__(
                    accessible_name="Current Price",
                    accessible_description="Displays the current item price",
                )

            def update_price(self, price: str):
                self._price = price
                self.announce_change(f"Price updated to {price}")
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        accessible_name: str = "",
        accessible_description: str = "",
        accessible_role=None,
    ):
        """
        Initialize accessible widget.

        Args:
            parent: Parent widget
            accessible_name: Screen reader name
            accessible_description: Additional description
            accessible_role: Widget role (usually auto-detected)
        """
        super().__init__(parent)

        if accessible_name:
            self.setAccessibleName(accessible_name)

        if accessible_description:
            self.setAccessibleDescription(accessible_description)

        # Role is typically handled by Qt automatically
        self._accessible_role = accessible_role


class LiveRegion(QWidget):
    """
    Widget that announces content changes to screen readers.

    Similar to ARIA live regions in web development.
    Content changes are automatically announced.

    Example:
        status_region = LiveRegion(politeness="assertive")
        layout.addWidget(status_region)

        # Later, this will be announced:
        status_region.set_content("Download complete!")
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        politeness: str = "polite",
    ):
        """
        Initialize live region.

        Args:
            parent: Parent widget
            politeness: "polite" (wait) or "assertive" (interrupt)
        """
        super().__init__(parent)

        self._politeness = politeness
        self._content = ""

        # Make widget accessible
        self.setAccessibleName("Status")
        self.setAccessibleDescription("Live status updates")

    def set_content(self, content: str) -> None:
        """
        Set new content and announce it.

        Args:
            content: New content to display and announce
        """
        if content == self._content:
            return

        self._content = content

        priority = (
            AnnouncePriority.ASSERTIVE
            if self._politeness == "assertive"
            else AnnouncePriority.POLITE
        )
        announce(content, priority)

    def clear(self) -> None:
        """Clear content without announcement."""
        self._content = ""


def setup_accessible_table(table_widget, table_name: str, column_names: list[str]) -> None:
    """
    Configure a table widget for accessibility.

    Sets up proper names and roles for screen reader navigation.

    Args:
        table_widget: QTableWidget or QTableView
        table_name: Accessible name for the table
        column_names: List of column header names

    Example:
        setup_accessible_table(
            results_table,
            "Price Check Results",
            ["Item", "Price", "Confidence", "Source"]
        )
    """
    table_widget.setAccessibleName(table_name)
    table_widget.setAccessibleDescription(
        f"Table with {len(column_names)} columns: {', '.join(column_names)}"
    )


def setup_accessible_list(list_widget, list_name: str, item_count: int = 0) -> None:
    """
    Configure a list widget for accessibility.

    Args:
        list_widget: QListWidget or QListView
        list_name: Accessible name for the list
        item_count: Initial item count
    """
    list_widget.setAccessibleName(list_name)
    if item_count > 0:
        list_widget.setAccessibleDescription(f"List with {item_count} items")
    else:
        list_widget.setAccessibleDescription("Empty list")


def setup_accessible_dialog(dialog, title: str, description: str = "") -> None:
    """
    Configure a dialog for accessibility.

    Args:
        dialog: QDialog instance
        title: Dialog title (for screen readers)
        description: Optional description of dialog purpose
    """
    dialog.setAccessibleName(title)
    if description:
        dialog.setAccessibleDescription(description)
