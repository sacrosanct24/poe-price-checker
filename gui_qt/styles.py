"""
gui_qt.styles - Theme system and color definitions for PoE Price Checker.

Supports multiple themes including:
- Dark and Light base themes
- High contrast options
- Colorblind-friendly themes (Deuteranopia, Protanopia, Tritanopia)
- Popular color schemes (Solarized, Dracula, Nord, Monokai)
"""

from enum import Enum
from typing import Dict, Callable, Optional
import logging
import threading

logger = logging.getLogger(__name__)


class Theme(Enum):
    """Available application themes."""
    # Base themes
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"

    # High contrast
    HIGH_CONTRAST_DARK = "high_contrast_dark"
    HIGH_CONTRAST_LIGHT = "high_contrast_light"

    # Popular color schemes
    SOLARIZED_DARK = "solarized_dark"
    SOLARIZED_LIGHT = "solarized_light"
    DRACULA = "dracula"
    NORD = "nord"
    MONOKAI = "monokai"
    GRUVBOX_DARK = "gruvbox_dark"

    # Colorblind-friendly themes
    COLORBLIND_DEUTERANOPIA = "colorblind_deuteranopia"  # Red-green (most common)
    COLORBLIND_PROTANOPIA = "colorblind_protanopia"      # Red-blind
    COLORBLIND_TRITANOPIA = "colorblind_tritanopia"      # Blue-yellow


# Theme display names for UI
THEME_DISPLAY_NAMES = {
    Theme.DARK: "Dark",
    Theme.LIGHT: "Light",
    Theme.SYSTEM: "System Default",
    Theme.HIGH_CONTRAST_DARK: "High Contrast Dark",
    Theme.HIGH_CONTRAST_LIGHT: "High Contrast Light",
    Theme.SOLARIZED_DARK: "Solarized Dark",
    Theme.SOLARIZED_LIGHT: "Solarized Light",
    Theme.DRACULA: "Dracula",
    Theme.NORD: "Nord",
    Theme.MONOKAI: "Monokai",
    Theme.GRUVBOX_DARK: "Gruvbox Dark",
    Theme.COLORBLIND_DEUTERANOPIA: "Colorblind: Deuteranopia",
    Theme.COLORBLIND_PROTANOPIA: "Colorblind: Protanopia",
    Theme.COLORBLIND_TRITANOPIA: "Colorblind: Tritanopia",
}

# Theme categories for menu organization
THEME_CATEGORIES = {
    "Standard": [Theme.DARK, Theme.LIGHT, Theme.SYSTEM],
    "High Contrast": [Theme.HIGH_CONTRAST_DARK, Theme.HIGH_CONTRAST_LIGHT],
    "Color Schemes": [Theme.SOLARIZED_DARK, Theme.SOLARIZED_LIGHT, Theme.DRACULA,
                     Theme.NORD, Theme.MONOKAI, Theme.GRUVBOX_DARK],
    "Accessibility": [Theme.COLORBLIND_DEUTERANOPIA, Theme.COLORBLIND_PROTANOPIA,
                     Theme.COLORBLIND_TRITANOPIA],
}


# ============================================================================
# PoE Rarity Colors (consistent across themes, with colorblind variants)
# ============================================================================

RARITY_COLORS = {
    "unique": "#af6025",      # Unique items (orange-brown)
    "rare": "#ffff77",        # Rare items (yellow)
    "magic": "#8888ff",       # Magic items (blue)
    "normal": "#c8c8c8",      # Normal items (white/gray)
    "currency": "#aa9e82",    # Currency items (tan)
    "gem": "#1ba29b",         # Gems (teal)
    "divination": "#0ebaff",  # Divination cards (light blue)
    "prophecy": "#b54bff",    # Prophecy (purple)
}

# Colorblind-safe rarity colors (uses shapes/patterns + distinguishable colors)
RARITY_COLORS_COLORBLIND = {
    "unique": "#e69f00",      # Orange (universally visible)
    "rare": "#f0e442",        # Yellow
    "magic": "#56b4e9",       # Sky blue
    "normal": "#999999",      # Gray
    "currency": "#cc79a7",    # Pink/mauve
    "gem": "#009e73",         # Bluish green
    "divination": "#0072b2",  # Blue
    "prophecy": "#d55e00",    # Vermillion
}


# ============================================================================
# Value indicator colors
# ============================================================================

VALUE_COLORS = {
    "high_value": "#22dd22",      # High value items (green)
    "medium_value": "#dddd22",    # Medium value items (yellow)
    "low_value": "#888888",       # Low value items (gray)
}

VALUE_COLORS_COLORBLIND = {
    "high_value": "#0072b2",      # Blue (instead of green)
    "medium_value": "#e69f00",    # Orange (instead of yellow)
    "low_value": "#999999",       # Gray
}


# ============================================================================
# Stat colors for build panel
# ============================================================================

STAT_COLORS = {
    "life": "#e85050",            # Life red
    "es": "#7888ff",              # Energy shield blue
    "mana": "#5080d0",            # Mana blue
}

STAT_COLORS_COLORBLIND = {
    "life": "#d55e00",            # Vermillion (instead of red)
    "es": "#56b4e9",              # Sky blue
    "mana": "#0072b2",            # Blue
}


# ============================================================================
# Status colors
# ============================================================================

STATUS_COLORS = {
    "upgrade": "#3ba4d8",         # Upgrade indicator (divine blue)
    "fractured": "#a29162",       # Fractured items
    "synthesised": "#6a1b9a",     # Synthesised items
    "corrupted": "#d20000",       # Corrupted items
    "crafted": "#b4b4ff",         # Crafted mods (light blue)
}

STATUS_COLORS_COLORBLIND = {
    "upgrade": "#56b4e9",         # Sky blue
    "fractured": "#cc79a7",       # Pink
    "synthesised": "#0072b2",     # Blue
    "corrupted": "#d55e00",       # Vermillion (instead of red)
    "crafted": "#009e73",         # Bluish green
}


# ============================================================================
# PoE Currency Accent Colors (for user customization)
# ============================================================================

POE_CURRENCY_COLORS = {
    "chaos": {
        "name": "Chaos Orb",
        "accent": "#c8a656",           # Gold
        "accent_hover": "#d8b666",
        "accent_blue": "#3ba4d8",
    },
    "divine": {
        "name": "Divine Orb",
        "accent": "#3ba4d8",           # Blue
        "accent_hover": "#5bc4f8",
        "accent_blue": "#c8a656",      # Swap for contrast
    },
    "exalt": {
        "name": "Exalted Orb",
        "accent": "#a89090",           # Silver/gray
        "accent_hover": "#c8b0b0",
        "accent_blue": "#3ba4d8",
    },
    "mirror": {
        "name": "Mirror of Kalandra",
        "accent": "#50c8ff",           # Cyan/mirror blue
        "accent_hover": "#70e8ff",
        "accent_blue": "#c8a656",
    },
    "alchemy": {
        "name": "Orb of Alchemy",
        "accent": "#ffcc00",           # Yellow
        "accent_hover": "#ffdd44",
        "accent_blue": "#3ba4d8",
    },
    "annul": {
        "name": "Orb of Annulment",
        "accent": "#ffffff",           # White
        "accent_hover": "#e0e0ff",
        "accent_blue": "#3ba4d8",
    },
    "vaal": {
        "name": "Vaal Orb",
        "accent": "#d04040",           # Red
        "accent_hover": "#e06060",
        "accent_blue": "#50c8ff",
    },
    "ancient": {
        "name": "Ancient Orb",
        "accent": "#ff8855",           # Orange
        "accent_hover": "#ffaa77",
        "accent_blue": "#3ba4d8",
    },
    "awakener": {
        "name": "Awakener's Orb",
        "accent": "#9060d0",           # Purple
        "accent_hover": "#b080f0",
        "accent_blue": "#50c8ff",
    },
    "hinekora": {
        "name": "Hinekora's Lock",
        "accent": "#40d080",           # Green
        "accent_hover": "#60f0a0",
        "accent_blue": "#3ba4d8",
    },
}


# ============================================================================
# Mod Tier Colors (for affix tier highlighting)
# ============================================================================

TIER_COLORS = {
    "t1": "#ffcc00",              # T1 - Gold (best tier)
    "t2": "#66bbff",              # T2 - Blue
    "t3": "#ffffff",              # T3 - White
    "t4": "#aaaaaa",              # T4 - Light gray
    "t5": "#888888",              # T5+ - Gray (lower tiers)
    "crafted": "#b4b4ff",         # Crafted mods - Light purple
    "implicit": "#8888ff",        # Implicit mods - Magic blue
}

TIER_COLORS_COLORBLIND = {
    "t1": "#e69f00",              # T1 - Orange (universally visible)
    "t2": "#56b4e9",              # T2 - Sky blue
    "t3": "#f0e442",              # T3 - Yellow
    "t4": "#cc79a7",              # T4 - Pink
    "t5": "#999999",              # T5+ - Gray
    "crafted": "#009e73",         # Crafted - Bluish green
    "implicit": "#0072b2",        # Implicit - Blue
}


def get_tier_color(tier: int, is_colorblind: bool = False) -> str:
    """
    Get the color for a given affix tier.

    Args:
        tier: Tier number (1 = best, 5+ = lowest)
        is_colorblind: Whether to use colorblind-friendly colors

    Returns:
        Hex color string
    """
    colors = TIER_COLORS_COLORBLIND if is_colorblind else TIER_COLORS

    if tier == 1:
        return colors["t1"]
    elif tier == 2:
        return colors["t2"]
    elif tier == 3:
        return colors["t3"]
    elif tier == 4:
        return colors["t4"]
    else:
        return colors["t5"]


# ============================================================================
# Theme Color Definitions
# ============================================================================

# Default Dark Theme (PoE-inspired)
DARK_THEME = {
    "background": "#1a1a1e",
    "surface": "#2a2a30",
    "surface_alt": "#252530",
    "surface_hover": "#3a3a42",
    "border": "#3a3a45",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#c8a656",          # Chaos orb gold
    "accent_blue": "#3ba4d8",     # Divine orb blue
    "accent_hover": "#d8b666",
    "button_hover": "#3d3d3d",
    "button_disabled_bg": "#1a1a1a",
    "button_disabled_text": "#666666",
    "alternate_row": "#252525",
}

# Default Light Theme
LIGHT_THEME = {
    "background": "#f5f5f7",
    "surface": "#ffffff",
    "surface_alt": "#f0f0f2",
    "surface_hover": "#e8e8ec",
    "border": "#d0d0d5",
    "text": "#1a1a1e",
    "text_secondary": "#606068",
    "accent": "#996515",
    "accent_blue": "#2080b0",
    "accent_hover": "#b87a20",
    "button_hover": "#e0e0e5",
    "button_disabled_bg": "#f0f0f0",
    "button_disabled_text": "#a0a0a0",
    "alternate_row": "#f8f8fa",
}

# High Contrast Dark
HIGH_CONTRAST_DARK_THEME = {
    "background": "#000000",
    "surface": "#1a1a1a",
    "surface_alt": "#0d0d0d",
    "surface_hover": "#333333",
    "border": "#ffffff",
    "text": "#ffffff",
    "text_secondary": "#cccccc",
    "accent": "#ffff00",          # Bright yellow
    "accent_blue": "#00ffff",     # Cyan
    "accent_hover": "#ffff80",
    "button_hover": "#333333",
    "button_disabled_bg": "#1a1a1a",
    "button_disabled_text": "#666666",
    "alternate_row": "#1a1a1a",
}

# High Contrast Light
HIGH_CONTRAST_LIGHT_THEME = {
    "background": "#ffffff",
    "surface": "#ffffff",
    "surface_alt": "#f0f0f0",
    "surface_hover": "#e0e0e0",
    "border": "#000000",
    "text": "#000000",
    "text_secondary": "#333333",
    "accent": "#0000cc",          # Dark blue
    "accent_blue": "#000099",
    "accent_hover": "#0000ff",
    "button_hover": "#e0e0e0",
    "button_disabled_bg": "#f0f0f0",
    "button_disabled_text": "#666666",
    "alternate_row": "#f5f5f5",
}

# Solarized Dark
SOLARIZED_DARK_THEME = {
    "background": "#002b36",
    "surface": "#073642",
    "surface_alt": "#002b36",
    "surface_hover": "#094959",
    "border": "#586e75",
    "text": "#839496",
    "text_secondary": "#657b83",
    "accent": "#b58900",          # Yellow
    "accent_blue": "#268bd2",     # Blue
    "accent_hover": "#cb4b16",    # Orange
    "button_hover": "#094959",
    "button_disabled_bg": "#002b36",
    "button_disabled_text": "#586e75",
    "alternate_row": "#073642",
}

# Solarized Light
SOLARIZED_LIGHT_THEME = {
    "background": "#fdf6e3",
    "surface": "#eee8d5",
    "surface_alt": "#fdf6e3",
    "surface_hover": "#e4ddc8",
    "border": "#93a1a1",
    "text": "#657b83",
    "text_secondary": "#839496",
    "accent": "#b58900",
    "accent_blue": "#268bd2",
    "accent_hover": "#cb4b16",
    "button_hover": "#e4ddc8",
    "button_disabled_bg": "#fdf6e3",
    "button_disabled_text": "#93a1a1",
    "alternate_row": "#eee8d5",
}

# Dracula
DRACULA_THEME = {
    "background": "#282a36",
    "surface": "#44475a",
    "surface_alt": "#343746",
    "surface_hover": "#555970",
    "border": "#6272a4",
    "text": "#f8f8f2",
    "text_secondary": "#6272a4",
    "accent": "#ff79c6",          # Pink
    "accent_blue": "#8be9fd",     # Cyan
    "accent_hover": "#ff92d0",
    "button_hover": "#555970",
    "button_disabled_bg": "#343746",
    "button_disabled_text": "#6272a4",
    "alternate_row": "#343746",
}

# Nord
NORD_THEME = {
    "background": "#2e3440",
    "surface": "#3b4252",
    "surface_alt": "#2e3440",
    "surface_hover": "#434c5e",
    "border": "#4c566a",
    "text": "#eceff4",
    "text_secondary": "#d8dee9",
    "accent": "#88c0d0",          # Frost
    "accent_blue": "#81a1c1",     # Storm
    "accent_hover": "#8fbcbb",
    "button_hover": "#434c5e",
    "button_disabled_bg": "#2e3440",
    "button_disabled_text": "#4c566a",
    "alternate_row": "#3b4252",
}

# Monokai
MONOKAI_THEME = {
    "background": "#272822",
    "surface": "#3e3d32",
    "surface_alt": "#272822",
    "surface_hover": "#49483e",
    "border": "#75715e",
    "text": "#f8f8f2",
    "text_secondary": "#75715e",
    "accent": "#f92672",          # Pink
    "accent_blue": "#66d9ef",     # Cyan
    "accent_hover": "#fd5ff0",
    "button_hover": "#49483e",
    "button_disabled_bg": "#272822",
    "button_disabled_text": "#75715e",
    "alternate_row": "#3e3d32",
}

# Gruvbox Dark
GRUVBOX_DARK_THEME = {
    "background": "#282828",
    "surface": "#3c3836",
    "surface_alt": "#282828",
    "surface_hover": "#504945",
    "border": "#665c54",
    "text": "#ebdbb2",
    "text_secondary": "#a89984",
    "accent": "#fabd2f",          # Yellow
    "accent_blue": "#83a598",     # Aqua
    "accent_hover": "#fe8019",    # Orange
    "button_hover": "#504945",
    "button_disabled_bg": "#282828",
    "button_disabled_text": "#665c54",
    "alternate_row": "#3c3836",
}

# Colorblind: Deuteranopia (red-green, most common ~6% of males)
COLORBLIND_DEUTERANOPIA_THEME = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#56b4e9",          # Sky blue (safe)
    "accent_blue": "#0072b2",     # Blue
    "accent_hover": "#7bc8f0",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}

# Colorblind: Protanopia (red-blind)
COLORBLIND_PROTANOPIA_THEME = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#e69f00",          # Orange (safe)
    "accent_blue": "#56b4e9",     # Sky blue
    "accent_hover": "#f0b020",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}

# Colorblind: Tritanopia (blue-yellow)
COLORBLIND_TRITANOPIA_THEME = {
    "background": "#1e2029",
    "surface": "#2a2d38",
    "surface_alt": "#252830",
    "surface_hover": "#3a3e4a",
    "border": "#404552",
    "text": "#e8e8ec",
    "text_secondary": "#9898a8",
    "accent": "#d55e00",          # Vermillion (safe)
    "accent_blue": "#cc79a7",     # Pink
    "accent_hover": "#e87830",
    "button_hover": "#3a3e4a",
    "button_disabled_bg": "#1e2029",
    "button_disabled_text": "#666666",
    "alternate_row": "#252830",
}


# Map themes to their color dictionaries
THEME_COLORS = {
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

# Themes that should use colorblind-safe colors
COLORBLIND_THEMES = {
    Theme.COLORBLIND_DEUTERANOPIA,
    Theme.COLORBLIND_PROTANOPIA,
    Theme.COLORBLIND_TRITANOPIA,
}

# Map themes to banner asset folders
# Banner variants: default, glow_free, high_contrast, ultra_dark_cyan, minimalist_dark, minimalist_dark_alt
THEME_BANNER_MAP = {
    Theme.DARK: "default",
    Theme.LIGHT: "glow_free",
    Theme.SYSTEM: "default",
    Theme.HIGH_CONTRAST_DARK: "high_contrast",
    Theme.HIGH_CONTRAST_LIGHT: "high_contrast",
    Theme.SOLARIZED_DARK: "minimalist_dark_alt",
    Theme.SOLARIZED_LIGHT: "glow_free",
    Theme.DRACULA: "ultra_dark_cyan",
    Theme.NORD: "minimalist_dark",
    Theme.MONOKAI: "default",
    Theme.GRUVBOX_DARK: "default",
    Theme.COLORBLIND_DEUTERANOPIA: "minimalist_dark",
    Theme.COLORBLIND_PROTANOPIA: "minimalist_dark",
    Theme.COLORBLIND_TRITANOPIA: "minimalist_dark",
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
    _theme_change_callbacks: list[Callable[['Theme'], None]]

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
                    cls._instance._theme_change_callbacks = []  # Instance variable, not class
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
        """Detect if system is in dark mode.

        Uses platform-specific APIs for accurate detection:
        - Windows: Registry key for AppsUseLightTheme
        - macOS: Aqua variation detection
        - Linux/Other: QPalette window lightness fallback
        """
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
                return value == 0  # 0 = dark mode, 1 = light mode
            except (FileNotFoundError, OSError):
                pass  # Registry key not found, fall through to QPalette

        # macOS: Check Aqua variation
        if sys.platform == "darwin":
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    # Qt6 approach - check style hints
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
            if app:
                palette = app.palette()
                bg = palette.color(QPalette.ColorRole.Window)
                return bg.lightness() < 128
        except Exception:
            pass  # No app instance, assume dark theme

        return True  # Default to dark

    def set_theme(self, theme: Theme) -> None:
        """Set the application theme."""
        if self._current_theme != theme:
            self._current_theme = theme
            self._update_colors()
            # Note: Don't clear entire cache - old entries may still be useful
            # if user switches back to previous theme
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
        """
        Reset the singleton instance for test isolation.

        Call this in test fixtures (e.g., pytest's autouse fixture) to ensure
        tests don't affect each other through shared ThemeManager state.

        Note: Callbacks are now instance variables and are automatically cleaned
        up when the instance is reset. No need to explicitly clear them.

        Example:
            @pytest.fixture(autouse=True)
            def reset_theme():
                yield
                ThemeManager.reset_for_testing()
        """
        with cls._lock:
            cls._instance = None
        logger.debug("ThemeManager reset for testing")

    def toggle_theme(self) -> Theme:
        """Toggle between dark and light themes. Returns the new theme."""
        # Simple toggle between dark/light variants
        light_themes = {Theme.LIGHT, Theme.SOLARIZED_LIGHT, Theme.HIGH_CONTRAST_LIGHT}

        if self._current_theme in light_themes:
            new_theme = Theme.DARK
        else:
            new_theme = Theme.LIGHT

        self.set_theme(new_theme)
        return new_theme

    def set_accent_color(self, accent_key: Optional[str]) -> None:
        """
        Set the accent color override.

        Args:
            accent_key: Key from POE_CURRENCY_COLORS (e.g., "chaos", "divine")
                       or None to use theme default.
        """
        if accent_key != self._accent_color:
            self._accent_color = accent_key
            self._update_colors()
            logger.info(f"Accent color changed to: {accent_key or 'theme default'}")

            # Notify callbacks (same as theme change)
            for callback in self._theme_change_callbacks:
                try:
                    callback(self._current_theme)
                except Exception as e:
                    logger.error(f"Accent change callback error: {e}")

    def get_available_accent_colors(self) -> Dict[str, str]:
        """
        Get available accent colors with their display names.

        Returns:
            Dict mapping accent key to display name (e.g., {"chaos": "Chaos Orb"})
        """
        return {key: data["name"] for key, data in POE_CURRENCY_COLORS.items()}

    def get_accent_color_preview(self, accent_key: str) -> Optional[str]:
        """
        Get the hex color for previewing an accent color.

        Args:
            accent_key: Key from POE_CURRENCY_COLORS

        Returns:
            Hex color string or None if not found
        """
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

    def get_available_themes(self) -> Dict[str, list]:
        """Get available themes organized by category."""
        return THEME_CATEGORIES

    def get_theme_display_name(self, theme: Theme) -> str:
        """Get the display name for a theme."""
        return THEME_DISPLAY_NAMES.get(theme, theme.value)

    def clear_stylesheet_cache(self) -> None:
        """Clear the stylesheet cache. Useful when theme definitions change."""
        self._stylesheet_cache.clear()
        logger.debug("Stylesheet cache cleared")

    def get_stylesheet(self) -> str:
        """Generate the complete application stylesheet for current theme.

        Uses caching to avoid regenerating stylesheets for the same theme/accent combination.
        """
        # Check cache first
        cache_key = (self._current_theme, self._accent_color)
        if cache_key in self._stylesheet_cache:
            logger.debug(f"Stylesheet cache hit: {cache_key}")
            return self._stylesheet_cache[cache_key]

        # Generate new stylesheet
        c = self._colors

        # Dark background for menu selection text
        dark_bg = "#1a1a1e"

        stylesheet = f"""
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

        # Cache and return
        self._stylesheet_cache[cache_key] = stylesheet
        logger.debug(f"Stylesheet cached: {cache_key}")
        return stylesheet


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# Legacy compatibility - COLORS dict that updates with theme
def _get_colors() -> Dict[str, str]:
    """Get colors from theme manager (for backwards compatibility)."""
    return get_theme_manager().colors


# Create a proxy object for COLORS that always returns current theme colors
class _ColorsProxy(dict):
    """Proxy for COLORS that delegates to theme manager."""

    def __getitem__(self, key):
        return get_theme_manager().colors.get(key, "#ffffff")

    def get(self, key, default=None):
        return get_theme_manager().colors.get(key, default)

    def __contains__(self, key):
        return key in get_theme_manager().colors

    def keys(self):
        return get_theme_manager().colors.keys()

    def values(self):
        return get_theme_manager().colors.values()

    def items(self):
        return get_theme_manager().colors.items()


# Legacy COLORS dict - now a proxy to theme manager
COLORS = _ColorsProxy()


# Legacy APP_STYLESHEET - now a function that returns current theme stylesheet
def get_app_stylesheet() -> str:
    """Get the application stylesheet for current theme."""
    return get_theme_manager().get_stylesheet()


# For backwards compatibility, APP_STYLESHEET as a string (dark theme)
APP_STYLESHEET = get_theme_manager().get_stylesheet()


def get_rarity_color(rarity: str) -> str:
    """Get the color for an item rarity."""
    rarity_lower = rarity.lower()
    return get_theme_manager().colors.get(rarity_lower, get_theme_manager().colors["text"])


def get_value_color(chaos_value: float) -> str:
    """Get the color based on chaos value."""
    c = get_theme_manager().colors
    if chaos_value >= 100:
        return c.get("high_value", "#22dd22")
    elif chaos_value >= 10:
        return c.get("medium_value", "#dddd22")
    else:
        return c.get("low_value", "#888888")


def get_app_icon():
    """Get the application icon as a QIcon."""
    from pathlib import Path
    from PyQt6.QtGui import QIcon

    base = Path(__file__).parent.parent / "assets"
    for name in ("icon.png", "icon.ico"):
        path = base / name
        if path.exists():
            return QIcon(str(path))
    return None


def get_app_banner_pixmap(size: int = 180, theme: Optional[Theme] = None):
    """Get the application banner as a scaled QPixmap.

    Args:
        size: Size to scale the banner to
        theme: Theme to get banner for (defaults to current theme)

    Returns:
        QPixmap scaled to the requested size, or None if not found
    """
    from pathlib import Path
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt

    base = Path(__file__).parent.parent / "assets"

    # Get theme-specific banner
    if theme is None:
        theme = get_theme_manager().current_theme

    banner_folder = THEME_BANNER_MAP.get(theme, "default")

    # Try theme-specific banner first
    theme_banner = base / "banners" / banner_folder / "banner_large.png"
    if theme_banner.exists():
        pixmap = QPixmap(str(theme_banner))
        return pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    # Fallback to main banner
    fallback = base / "banner.png"
    if fallback.exists():
        pixmap = QPixmap(str(fallback))
        return pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    return None


def get_theme_icon_pixmap(size: int = 64, theme: Optional[Theme] = None):
    """Get the theme-specific icon as a QPixmap.

    Args:
        size: Size to get (16, 32, 48, 64, or 128)
        theme: Theme to get icon for (defaults to current theme)

    Returns:
        QPixmap at the requested size, or None if not found
    """
    from pathlib import Path
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt

    base = Path(__file__).parent.parent / "assets"

    if theme is None:
        theme = get_theme_manager().current_theme

    banner_folder = THEME_BANNER_MAP.get(theme, "default")

    # Find best size match
    available_sizes = [128, 64, 48, 32, 16]
    target_size = min(available_sizes, key=lambda x: abs(x - size))

    icon_path = base / "banners" / banner_folder / f"icon_{target_size}.png"
    if icon_path.exists():
        pixmap = QPixmap(str(icon_path))
        if pixmap.width() != size:
            return pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        return pixmap

    return None


def apply_window_icon(window):
    """Apply the application icon to a window or dialog."""
    icon = get_app_icon()
    if icon:
        window.setWindowIcon(icon)
