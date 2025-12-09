"""
gui_qt.controllers.view_menu_controller - View menu management controller.

Extracts View menu creation from main_window.py.
Follows UX best practices: View menu contains display/appearance options only.

Contents:
- Session history and stash viewer windows
- Theme submenu with categories
- Accent color submenu
- Column visibility submenu

Usage:
    controller = ViewMenuController(
        on_history=self._show_history,
        on_stash_viewer=self._show_stash_viewer,
        on_set_theme=self._set_theme,
        on_toggle_theme=self._toggle_theme,
        on_set_accent=self._set_accent_color,
        on_toggle_column=self._toggle_column,
    )
    theme_actions, accent_actions, column_actions = controller.create_view_menu(menubar)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMenuBar

from gui_qt.styles import (
    Theme,
    THEME_CATEGORIES, THEME_DISPLAY_NAMES, POE_CURRENCY_COLORS
)

if TYPE_CHECKING:
    pass


class ViewMenuController:
    """
    Controller for View menu creation and management.

    Handles:
    - Theme submenu with category groupings
    - Accent color submenu with PoE currency colors
    - Column visibility submenu
    - Session history and stash viewer actions
    """

    # Default columns available in the results table
    DEFAULT_COLUMNS = [
        "item_name", "variant", "links", "chaos_value", "divine_value",
        "listing_count", "source", "upgrade"
    ]

    def __init__(
        self,
        on_history: Callable[[], None],
        on_stash_viewer: Callable[[], None],
        on_set_theme: Callable[[Theme], None],
        on_toggle_theme: Callable[[], None],
        on_set_accent: Callable[[Optional[str]], None],
        on_toggle_column: Callable[[str, bool], None],
        parent: Any = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the ViewMenuController.

        Args:
            on_history: Callback to show session history.
            on_stash_viewer: Callback to show stash viewer.
            on_set_theme: Callback to set theme.
            on_toggle_theme: Callback to toggle dark/light theme.
            on_set_accent: Callback to set accent color.
            on_toggle_column: Callback to toggle column visibility.
            parent: Parent widget for actions.
            logger: Logger instance.
        """
        self._on_history = on_history
        self._on_stash_viewer = on_stash_viewer
        self._on_set_theme = on_set_theme
        self._on_toggle_theme = on_toggle_theme
        self._on_set_accent = on_set_accent
        self._on_toggle_column = on_toggle_column
        self._parent = parent
        self._logger = logger or logging.getLogger(__name__)

        # Store action references for external access
        self._theme_actions: Dict[Theme, QAction] = {}
        self._accent_actions: Dict[Optional[str], QAction] = {}
        self._column_actions: Dict[str, QAction] = {}

    @property
    def theme_actions(self) -> Dict[Theme, QAction]:
        """Get the theme action dictionary."""
        return self._theme_actions

    @property
    def accent_actions(self) -> Dict[Optional[str], QAction]:
        """Get the accent action dictionary."""
        return self._accent_actions

    @property
    def column_actions(self) -> Dict[str, QAction]:
        """Get the column action dictionary."""
        return self._column_actions

    def create_view_menu(
        self,
        menubar: QMenuBar,
    ) -> tuple[Dict[Theme, QAction], Dict[Optional[str], QAction], Dict[str, QAction]]:
        """
        Create the View menu with all submenus.

        Args:
            menubar: The menu bar to add the View menu to.

        Returns:
            Tuple of (theme_actions, accent_actions, column_actions) dictionaries.
        """
        view_menu = menubar.addMenu("&View")
        if not view_menu:
            return self._theme_actions, self._accent_actions, self._column_actions

        # Window visibility section
        history_action = QAction("Session &History", self._parent)
        history_action.triggered.connect(self._on_history)
        view_menu.addAction(history_action)

        stash_action = QAction("&Stash Viewer", self._parent)
        stash_action.triggered.connect(self._on_stash_viewer)
        view_menu.addAction(stash_action)

        view_menu.addSeparator()

        # Theme submenu
        self._create_theme_submenu(view_menu)

        view_menu.addSeparator()

        # Quick toggle theme action
        toggle_theme_action = QAction("&Quick Toggle Dark/Light", self._parent)
        toggle_theme_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_theme_action.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(toggle_theme_action)

        # Accent color submenu
        self._create_accent_submenu(view_menu)

        view_menu.addSeparator()

        # Column visibility submenu
        self._create_columns_submenu(view_menu)

        return self._theme_actions, self._accent_actions, self._column_actions

    def _create_theme_submenu(self, view_menu) -> None:
        """Create the Theme submenu with category groupings."""
        theme_menu = view_menu.addMenu("&Theme")

        for category, themes in THEME_CATEGORIES.items():
            # Add separator and category label for non-Standard categories
            if category != "Standard":
                theme_menu.addSeparator()
                label_action = QAction(f"[ {category} ]", self._parent)
                label_action.setEnabled(False)
                theme_menu.addAction(label_action)

            # Add theme actions
            for theme in themes:
                display_name = THEME_DISPLAY_NAMES.get(theme, theme.value)
                action = QAction(display_name, self._parent)
                action.setCheckable(True)
                action.triggered.connect(
                    lambda checked, t=theme: self._on_set_theme(t)
                )
                theme_menu.addAction(action)
                self._theme_actions[theme] = action

    def _create_accent_submenu(self, view_menu) -> None:
        """Create the Accent Color submenu."""
        accent_menu = view_menu.addMenu("&Accent Color")

        # Default (no accent) option
        default_action = QAction("Theme Default", self._parent)
        default_action.setCheckable(True)
        default_action.triggered.connect(lambda: self._on_set_accent(None))
        accent_menu.addAction(default_action)
        self._accent_actions[None] = default_action

        accent_menu.addSeparator()

        # Currency color options
        for key, data in POE_CURRENCY_COLORS.items():
            action = QAction(data["name"], self._parent)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked, k=key: self._on_set_accent(k)
            )
            accent_menu.addAction(action)
            self._accent_actions[key] = action

    def _create_columns_submenu(self, view_menu) -> None:
        """Create the Columns visibility submenu."""
        columns_menu = view_menu.addMenu("&Columns")

        for col in self.DEFAULT_COLUMNS:
            display_name = col.replace("_", " ").title()
            action = QAction(display_name, self._parent)
            action.setCheckable(True)
            action.setChecked(True)  # All visible by default
            action.triggered.connect(
                lambda checked, c=col: self._on_toggle_column(c, checked)
            )
            columns_menu.addAction(action)
            self._column_actions[col] = action


def get_view_menu_controller(
    on_history: Callable[[], None],
    on_stash_viewer: Callable[[], None],
    on_set_theme: Callable[[Theme], None],
    on_toggle_theme: Callable[[], None],
    on_set_accent: Callable[[Optional[str]], None],
    on_toggle_column: Callable[[str, bool], None],
    parent: Any = None,
    logger: Optional[logging.Logger] = None,
) -> ViewMenuController:
    """
    Factory function to create a ViewMenuController.

    Args:
        on_history: Callback to show session history.
        on_stash_viewer: Callback to show stash viewer.
        on_set_theme: Callback to set theme.
        on_toggle_theme: Callback to toggle dark/light theme.
        on_set_accent: Callback to set accent color.
        on_toggle_column: Callback to toggle column visibility.
        parent: Parent widget for actions.
        logger: Logger instance.

    Returns:
        Configured ViewMenuController instance.
    """
    return ViewMenuController(
        on_history=on_history,
        on_stash_viewer=on_stash_viewer,
        on_set_theme=on_set_theme,
        on_toggle_theme=on_toggle_theme,
        on_set_accent=on_set_accent,
        on_toggle_column=on_toggle_column,
        parent=parent,
        logger=logger,
    )
