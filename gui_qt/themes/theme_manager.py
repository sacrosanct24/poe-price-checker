"""
Theme manager - manages application themes and stylesheet generation.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional

from gui_qt.themes.theme_enum import (
    Theme,
    THEME_DISPLAY_NAMES,
    THEME_CATEGORIES,
    COLORBLIND_THEMES,
)
from gui_qt.themes.colors import (
    RARITY_COLORS,
    RARITY_COLORS_COLORBLIND,
    VALUE_COLORS,
    VALUE_COLORS_COLORBLIND,
    STAT_COLORS,
    STAT_COLORS_COLORBLIND,
    STATUS_COLORS,
    STATUS_COLORS_COLORBLIND,
    POE_CURRENCY_COLORS,
)
from gui_qt.themes.palettes import (
    DARK_THEME,
    LIGHT_THEME,
    HIGH_CONTRAST_DARK_THEME,
    HIGH_CONTRAST_LIGHT_THEME,
    SOLARIZED_DARK_THEME,
    SOLARIZED_LIGHT_THEME,
    DRACULA_THEME,
    NORD_THEME,
    MONOKAI_THEME,
    GRUVBOX_DARK_THEME,
    COLORBLIND_DEUTERANOPIA_THEME,
    COLORBLIND_PROTANOPIA_THEME,
    COLORBLIND_TRITANOPIA_THEME,
)

logger = logging.getLogger(__name__)

# Map themes to their color dictionaries
THEME_COLORS: Dict[Theme, Dict[str, str]] = {
    Theme.DARK: DARK_THEME,
    Theme.LIGHT: LIGHT_THEME,
    Theme.SYSTEM: DARK_THEME,  # Fallback, will be resolved at runtime
    Theme.HIGH_CONTRAST_DARK: HIGH_CONTRAST_DARK_THEME,
    Theme.HIGH_CONTRAST_LIGHT: HIGH_CONTRAST_LIGHT_THEME,
    Theme.SOLARIZED_DARK: SOLARIZED_DARK_THEME,
    Theme.SOLARIZED_LIGHT: SOLARIZED_LIGHT_THEME,
    Theme.DRACULA: DRACULA_THEME,
    Theme.NORD: NORD_THEME,
    Theme.MONOKAI: MONOKAI_THEME,
    Theme.GRUVBOX_DARK: GRUVBOX_DARK_THEME,
    Theme.COLORBLIND_DEUTERANOPIA: COLORBLIND_DEUTERANOPIA_THEME,
    Theme.COLORBLIND_PROTANOPIA: COLORBLIND_PROTANOPIA_THEME,
    Theme.COLORBLIND_TRITANOPIA: COLORBLIND_TRITANOPIA_THEME,
}


class ThemeManager:
    """
    Manages application themes and provides stylesheet generation.

    Usage:
        manager = ThemeManager()
        manager.set_theme(Theme.DARK)
        stylesheet = manager.get_stylesheet()
    """

    _instance: Optional['ThemeManager'] = None
    _lock: threading.Lock = threading.Lock()

    # Instance attributes - declared here for type checking
    _current_theme: Theme
    _accent_color: Optional[str]
    _colors: Dict[str, str]
    _stylesheet_cache: Dict[tuple, str]
    _theme_change_callbacks: List[Callable[['Theme'], None]]

    def __new__(cls):
        """Singleton pattern with thread-safe double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._current_theme = Theme.DARK
                    cls._instance._accent_color = None  # None = use theme default
                    cls._instance._colors = {}
                    cls._instance._stylesheet_cache = {}  # Cache by (theme, accent)
                    cls._instance._theme_change_callbacks = []  # Instance variable
                    cls._instance._update_colors()
        return cls._instance

    @property
    def current_theme(self) -> Theme:
        """Get the current theme."""
        return self._current_theme

    @property
    def colors(self) -> Dict[str, str]:
        """Get the current color palette (merged theme + rarity + value + stat + status)."""
        return self._colors

    @property
    def accent_color(self) -> Optional[str]:
        """Get the current accent color override (None = use theme default)."""
        return self._accent_color

    def _update_colors(self) -> None:
        """Update the merged color dictionary based on current theme and accent."""
        theme = self._current_theme

        # For system theme, try to detect preference
        if theme == Theme.SYSTEM:
            theme = Theme.DARK if self._is_system_dark_mode() else Theme.LIGHT

        theme_colors = THEME_COLORS.get(theme, DARK_THEME).copy()

        # Apply custom accent color if set
        if self._accent_color and self._accent_color in POE_CURRENCY_COLORS:
            accent_data = POE_CURRENCY_COLORS[self._accent_color]
            theme_colors["accent"] = accent_data["accent"]
            theme_colors["accent_hover"] = accent_data["accent_hover"]
            theme_colors["accent_blue"] = accent_data["accent_blue"]

        # Use colorblind-safe colors for accessibility themes
        if self._current_theme in COLORBLIND_THEMES:
            rarity_colors = RARITY_COLORS_COLORBLIND
            value_colors = VALUE_COLORS_COLORBLIND
            stat_colors = STAT_COLORS_COLORBLIND
            status_colors = STATUS_COLORS_COLORBLIND
        else:
            rarity_colors = RARITY_COLORS
            value_colors = VALUE_COLORS
            stat_colors = STAT_COLORS
            status_colors = STATUS_COLORS

        # Merge all color dictionaries
        self._colors = {
            **theme_colors,
            **rarity_colors,
            **value_colors,
            **stat_colors,
            **status_colors,
        }

    def _is_system_dark_mode(self) -> bool:
        """Detect if system is in dark mode."""
        import sys

        # Windows: Check registry for dark mode setting
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return bool(value == 0)  # 0 = dark mode, 1 = light mode
            except (FileNotFoundError, OSError):
                pass

        # macOS: Check Aqua variation
        if sys.platform == "darwin":
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    style_hints = app.styleHints()
                    if hasattr(style_hints, 'colorScheme'):
                        from PyQt6.QtCore import Qt
                        return style_hints.colorScheme() == Qt.ColorScheme.Dark
            except Exception:
                pass

        # Fallback: Use QPalette window background lightness
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QPalette
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                palette = app.palette()
                bg = palette.color(QPalette.ColorRole.Window)
                return bool(bg.lightness() < 128)
        except Exception:
            pass

        return True  # Default to dark

    def set_theme(self, theme: Theme) -> None:
        """Set the application theme."""
        if self._current_theme != theme:
            self._current_theme = theme
            self._update_colors()
            logger.info(f"Theme changed to: {theme.value}")

            # Notify callbacks
            for callback in self._theme_change_callbacks:
                try:
                    callback(theme)
                except Exception as e:
                    logger.error(f"Theme change callback error: {e}")

    def set_theme_by_name(self, theme_name: str) -> bool:
        """Set theme by string name. Returns True if successful."""
        try:
            theme = Theme(theme_name)
            self.set_theme(theme)
            return True
        except ValueError:
            logger.warning(f"Unknown theme: {theme_name}")
            return False

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset the singleton instance for test isolation."""
        with cls._lock:
            cls._instance = None
        logger.debug("ThemeManager reset for testing")

    def toggle_theme(self) -> Theme:
        """Toggle between dark and light themes. Returns the new theme."""
        light_themes = {Theme.LIGHT, Theme.SOLARIZED_LIGHT, Theme.HIGH_CONTRAST_LIGHT}

        if self._current_theme in light_themes:
            new_theme = Theme.DARK
        else:
            new_theme = Theme.LIGHT

        self.set_theme(new_theme)
        return new_theme

    def set_accent_color(self, accent_key: Optional[str]) -> None:
        """Set the accent color override."""
        if accent_key != self._accent_color:
            self._accent_color = accent_key
            self._update_colors()
            logger.info(f"Accent color changed to: {accent_key or 'theme default'}")

            # Notify callbacks
            for callback in self._theme_change_callbacks:
                try:
                    callback(self._current_theme)
                except Exception as e:
                    logger.error(f"Accent change callback error: {e}")

    def get_available_accent_colors(self) -> Dict[str, str]:
        """Get available accent colors with their display names."""
        return {key: data["name"] for key, data in POE_CURRENCY_COLORS.items()}

    def get_accent_color_preview(self, accent_key: str) -> Optional[str]:
        """Get the hex color for previewing an accent color."""
        if accent_key in POE_CURRENCY_COLORS:
            return POE_CURRENCY_COLORS[accent_key]["accent"]
        return None

    def register_callback(self, callback: Callable[['Theme'], None]) -> None:
        """Register a callback to be called when theme changes."""
        if callback not in self._theme_change_callbacks:
            self._theme_change_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[['Theme'], None]) -> None:
        """Unregister a theme change callback."""
        if callback in self._theme_change_callbacks:
            self._theme_change_callbacks.remove(callback)

    def get_available_themes(self) -> Dict[str, List[Theme]]:
        """Get available themes organized by category."""
        return THEME_CATEGORIES

    def get_theme_display_name(self, theme: Theme) -> str:
        """Get the display name for a theme."""
        return THEME_DISPLAY_NAMES.get(theme, theme.value)

    def clear_stylesheet_cache(self) -> None:
        """Clear the stylesheet cache."""
        self._stylesheet_cache.clear()
        logger.debug("Stylesheet cache cleared")

    def get_stylesheet(self) -> str:
        """Generate the complete application stylesheet for current theme."""
        # Check cache first
        cache_key = (self._current_theme, self._accent_color)
        if cache_key in self._stylesheet_cache:
            logger.debug(f"Stylesheet cache hit: {cache_key}")
            return self._stylesheet_cache[cache_key]

        # Generate new stylesheet
        stylesheet = _generate_stylesheet(self._colors)

        # Cache and return
        self._stylesheet_cache[cache_key] = stylesheet
        logger.debug(f"Stylesheet cached: {cache_key}")
        return stylesheet


def _generate_stylesheet(c: Dict[str, str]) -> str:
    """Generate the complete application stylesheet."""
    dark_bg = "#1a1a1e"

    return f"""
QMainWindow {{
    background-color: {c["background"]};
}}

QWidget {{
    color: {c["text"]};
    font-size: 13px;
}}

QMenuBar {{
    background-color: {c["surface"]};
    border-bottom: 1px solid {c["border"]};
}}

QMenuBar::item {{
    padding: 6px 12px;
}}

QMenuBar::item:selected {{
    background-color: {c["accent"]};
    color: {dark_bg};
}}

QMenu {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
}}

QMenu::item {{
    padding: 6px 24px;
}}

QMenu::item:selected {{
    background-color: {c["accent"]};
    color: {dark_bg};
}}

QGroupBox {{
    border: 1px solid {c["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: bold;
    background-color: {c["surface_alt"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 2px 8px;
    color: {c["accent"]};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {c["accent"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c["accent_blue"]};
}}

QPushButton {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 70px;
}}

QPushButton:hover {{
    background-color: {c["button_hover"]};
    border-color: {c["accent"]};
}}

QPushButton:pressed {{
    background-color: {c["accent"]};
    color: {dark_bg};
}}

QPushButton:disabled {{
    background-color: {c["button_disabled_bg"]};
    color: {c["button_disabled_text"]};
}}

QComboBox {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 6px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {c["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    selection-background-color: {c["accent"]};
    selection-color: {dark_bg};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 4px;
}}

QTableView, QTreeView, QListView {{
    background-color: {c["surface"]};
    alternate-background-color: {c["alternate_row"]};
    border: 1px solid {c["border"]};
    gridline-color: {c["border"]};
    selection-background-color: {c["accent"]};
    selection-color: {dark_bg};
}}

QTableView::item, QTreeView::item, QListView::item {{
    padding: 4px;
}}

QHeaderView::section {{
    background-color: {c["surface_alt"]};
    border: none;
    border-right: 1px solid {c["border"]};
    border-bottom: 2px solid {c["accent"]};
    padding: 8px 6px;
    font-weight: bold;
    color: {c["accent"]};
}}

QHeaderView::section:hover {{
    background-color: {c["surface"]};
    color: {c["accent_hover"]};
}}

QScrollBar:vertical {{
    background-color: {c["background"]};
    width: 14px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {c["border"]};
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c["accent_blue"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {c["background"]};
    height: 14px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {c["border"]};
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {c["accent_blue"]};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QStatusBar {{
    background-color: {c["surface"]};
    border-top: 1px solid {c["border"]};
}}

QTabWidget::pane {{
    border: 1px solid {c["border"]};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {c["accent"]};
    color: {dark_bg};
}}

QTabBar::tab:hover:!selected {{
    background-color: {c["surface"]};
    border-color: {c["accent_blue"]};
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {c["border"]};
    border-radius: 3px;
    background-color: {c["surface"]};
}}

QCheckBox::indicator:checked {{
    background-color: {c["accent"]};
    border-color: {c["accent"]};
}}

QSlider::groove:horizontal {{
    height: 6px;
    background-color: {c["border"]};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background-color: {c["accent"]};
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {c["accent_hover"]};
}}

QProgressBar {{
    border: 1px solid {c["border"]};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {c["accent"]};
    border-radius: 3px;
}}

QToolTip {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    color: {c["text"]};
    padding: 4px;
}}

QSplitter::handle {{
    background-color: {c["border"]};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QLabel {{
    background: transparent;
}}

QTextBrowser {{
    background-color: {c["surface"]};
    border: 1px solid {c["border"]};
    border-radius: 4px;
}}

QDialog {{
    background-color: {c["background"]};
}}
"""


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
