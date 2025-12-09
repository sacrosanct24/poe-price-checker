"""
gui_qt.controllers.theme_controller - Theme and accent color management.

Handles theme initialization, switching, and persistence to config.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QApplication

from gui_qt.styles import (
    Theme, get_theme_manager,
    THEME_DISPLAY_NAMES, POE_CURRENCY_COLORS
)

if TYPE_CHECKING:
    from PyQt6.QtGui import QAction


class ThemeController:
    """
    Controller for theme and accent color management.

    Handles:
    - Theme initialization from config
    - Theme switching and persistence
    - Accent color management
    - Menu action updates
    """

    def __init__(
        self,
        config: Any,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the theme controller.

        Args:
            config: Config object with theme/accent_color attributes
            on_status: Optional callback for status messages
        """
        self._config = config
        self._on_status = on_status or (lambda msg: None)
        self._theme_actions: Dict[Theme, 'QAction'] = {}
        self._accent_actions: Dict[Optional[str], 'QAction'] = {}

    def set_theme_actions(self, actions: Dict[Theme, 'QAction']) -> None:
        """Set the theme menu actions for checkmark updates."""
        self._theme_actions = actions

    def set_accent_actions(self, actions: Dict[Optional[str], 'QAction']) -> None:
        """Set the accent menu actions for checkmark updates."""
        self._accent_actions = actions

    def initialize(self, window: Any) -> None:
        """
        Initialize theme from config and apply to window.

        Args:
            window: The main window to style
        """
        theme_manager = get_theme_manager()

        # Load theme from config
        saved_theme = getattr(self._config, 'theme', 'dark') if self._config else 'dark'
        try:
            theme = Theme(saved_theme)
        except ValueError:
            theme = Theme.DARK

        # Set theme
        theme_manager.set_theme(theme)

        # Load accent color from config
        saved_accent = getattr(self._config, 'accent_color', None) if self._config else None
        if saved_accent is not None:
            theme_manager.set_accent_color(saved_accent)

        # Apply stylesheet
        window.setStyleSheet(theme_manager.get_stylesheet())

        # Update menu checkmarks
        self._update_theme_menu_checks(theme)
        self._update_accent_menu_checks(saved_accent)

        # Register callback for future theme changes
        theme_manager.register_callback(lambda t: self._on_theme_changed(t, window))

    def set_theme(self, theme: Theme, window: Any) -> None:
        """
        Set the application theme.

        Args:
            theme: Theme to apply
            window: Main window to style
        """
        theme_manager = get_theme_manager()
        theme_manager.set_theme(theme)

        # Save to config
        if self._config:
            self._config.theme = theme.value

        # Apply stylesheet
        app = QApplication.instance()
        stylesheet = theme_manager.get_stylesheet()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(stylesheet)
        window.setStyleSheet(stylesheet)

        # Update menu checkmarks
        self._update_theme_menu_checks(theme)

        display_name = THEME_DISPLAY_NAMES.get(theme, theme.value)
        self._on_status(f"Theme changed to: {display_name}")

    def toggle_theme(self, window: Any) -> Theme:
        """
        Toggle between dark and light themes.

        Args:
            window: Main window to style

        Returns:
            The new theme
        """
        theme_manager = get_theme_manager()
        new_theme = theme_manager.toggle_theme()

        # Save to config
        if self._config:
            self._config.theme = new_theme.value

        # Apply stylesheet
        app = QApplication.instance()
        stylesheet = theme_manager.get_stylesheet()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(stylesheet)
        window.setStyleSheet(stylesheet)

        # Update menu checkmarks
        self._update_theme_menu_checks(new_theme)

        display_name = THEME_DISPLAY_NAMES.get(new_theme, new_theme.value)
        self._on_status(f"Theme toggled to: {display_name}")

        return new_theme

    def cycle_theme(self, window: Any) -> Theme:
        """
        Cycle through all available themes.

        Args:
            window: Main window to style

        Returns:
            The new theme
        """
        theme_manager = get_theme_manager()
        current = theme_manager.current_theme

        # Get all themes in order
        all_themes = list(Theme)
        try:
            current_idx = all_themes.index(current)
            next_idx = (current_idx + 1) % len(all_themes)
            next_theme = all_themes[next_idx]
        except ValueError:
            next_theme = Theme.DARK

        self.set_theme(next_theme, window)
        return next_theme

    def set_accent_color(self, accent_key: Optional[str], window: Any) -> None:
        """
        Set the application accent color.

        Args:
            accent_key: Accent color key or None for default
            window: Main window to style
        """
        theme_manager = get_theme_manager()
        theme_manager.set_accent_color(accent_key)

        # Save to config
        if self._config:
            self._config.accent_color = accent_key

        # Apply stylesheet
        app = QApplication.instance()
        stylesheet = theme_manager.get_stylesheet()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(stylesheet)
        window.setStyleSheet(stylesheet)

        # Update menu checkmarks
        self._update_accent_menu_checks(accent_key)

        # Get display name
        if accent_key is None:
            display_name = "Theme Default"
        else:
            display_name = POE_CURRENCY_COLORS.get(accent_key, {}).get("name", accent_key)
        self._on_status(f"Accent color changed to: {display_name}")

    def _update_theme_menu_checks(self, current_theme: Theme) -> None:
        """Update the checkmarks in the theme menu."""
        for theme, action in self._theme_actions.items():
            action.setChecked(theme == current_theme)

    def _update_accent_menu_checks(self, current_accent: Optional[str]) -> None:
        """Update the checkmarks in the accent menu."""
        for accent_key, action in self._accent_actions.items():
            action.setChecked(accent_key == current_accent)

    def _on_theme_changed(self, theme: Theme, window: Any) -> None:
        """Handle theme change callback from ThemeManager."""
        app = QApplication.instance()
        stylesheet = get_theme_manager().get_stylesheet()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(stylesheet)
        window.setStyleSheet(stylesheet)
        self._update_theme_menu_checks(theme)
