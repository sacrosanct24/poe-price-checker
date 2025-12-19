"""Tests for gui_qt/styles.py - Theme system and color definitions."""


import pytest

from gui_qt.styles import (
    Theme,
    THEME_DISPLAY_NAMES,
    THEME_CATEGORIES,
    RARITY_COLORS,
    RARITY_COLORS_COLORBLIND,
    VALUE_COLORS,
    VALUE_COLORS_COLORBLIND,
    STAT_COLORS,
    STATUS_COLORS,
    DARK_THEME,
    LIGHT_THEME,
    DRACULA_THEME,
    NORD_THEME,
    THEME_COLORS,
    COLORBLIND_THEMES,
    THEME_BANNER_MAP,
    ThemeManager,
    get_theme_manager,
    get_rarity_color,
    get_value_color,
)


class TestThemeEnum:
    """Tests for Theme enum."""

    def test_all_themes_defined(self):
        """Should have all expected theme values."""
        expected_themes = [
            "dark", "light", "system",
            "high_contrast_dark", "high_contrast_light",
            "solarized_dark", "solarized_light",
            "dracula", "nord", "monokai", "gruvbox_dark",
            "colorblind_deuteranopia", "colorblind_protanopia", "colorblind_tritanopia",
        ]
        actual_themes = [t.value for t in Theme]
        for expected in expected_themes:
            assert expected in actual_themes, f"Missing theme: {expected}"

    def test_theme_from_value(self):
        """Should create Theme from string value."""
        assert Theme("dark") == Theme.DARK
        assert Theme("light") == Theme.LIGHT
        assert Theme("dracula") == Theme.DRACULA

    def test_themes_have_unique_values(self):
        """Each theme should have a unique string value for serialization."""
        values = [t.value for t in Theme]
        assert len(values) == len(set(values)), "Theme values should be unique"

    def test_themes_are_hashable_for_dict_keys(self):
        """Themes should be usable as dictionary keys."""
        theme_handlers = {Theme.DARK: "dark_handler", Theme.LIGHT: "light_handler"}
        assert theme_handlers[Theme.DARK] == "dark_handler"


class TestThemeDisplayNames:
    """Tests for THEME_DISPLAY_NAMES mapping."""

    def test_all_themes_have_display_names(self):
        """Every theme should have a display name."""
        for theme in Theme:
            assert theme in THEME_DISPLAY_NAMES, f"Missing display name for {theme}"

    def test_display_names_are_strings(self):
        """Display names should be non-empty strings."""
        for theme, name in THEME_DISPLAY_NAMES.items():
            assert isinstance(name, str)
            assert len(name) > 0

    def test_specific_display_names(self):
        """Check specific display names."""
        assert THEME_DISPLAY_NAMES[Theme.DARK] == "Dark"
        assert THEME_DISPLAY_NAMES[Theme.LIGHT] == "Light"
        assert THEME_DISPLAY_NAMES[Theme.DRACULA] == "Dracula"
        assert "Deuteranopia" in THEME_DISPLAY_NAMES[Theme.COLORBLIND_DEUTERANOPIA]


class TestThemeCategories:
    """Tests for THEME_CATEGORIES organization."""

    def test_categories_defined(self):
        """Should have expected categories."""
        assert "Standard" in THEME_CATEGORIES
        assert "High Contrast" in THEME_CATEGORIES
        assert "Color Schemes" in THEME_CATEGORIES
        assert "Accessibility" in THEME_CATEGORIES

    def test_standard_themes(self):
        """Standard category should contain base themes."""
        assert Theme.DARK in THEME_CATEGORIES["Standard"]
        assert Theme.LIGHT in THEME_CATEGORIES["Standard"]
        assert Theme.SYSTEM in THEME_CATEGORIES["Standard"]

    def test_accessibility_themes(self):
        """Accessibility category should contain colorblind themes."""
        accessibility = THEME_CATEGORIES["Accessibility"]
        assert Theme.COLORBLIND_DEUTERANOPIA in accessibility
        assert Theme.COLORBLIND_PROTANOPIA in accessibility
        assert Theme.COLORBLIND_TRITANOPIA in accessibility

    def test_color_schemes(self):
        """Color schemes should contain popular themes."""
        schemes = THEME_CATEGORIES["Color Schemes"]
        assert Theme.DRACULA in schemes
        assert Theme.NORD in schemes
        assert Theme.MONOKAI in schemes


class TestRarityColors:
    """Tests for rarity color definitions."""

    def test_all_rarities_defined(self):
        """Should define colors for all PoE rarities."""
        expected_rarities = [
            "unique", "rare", "magic", "normal", "currency",
            "gem", "divination", "prophecy",
        ]
        for rarity in expected_rarities:
            assert rarity in RARITY_COLORS
            assert rarity in RARITY_COLORS_COLORBLIND

    def test_colors_are_hex(self):
        """Rarity colors should be hex format."""
        for color in RARITY_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7

    def test_colorblind_safe_colors_different(self):
        """Colorblind colors should differ from standard."""
        # At least some should be different for accessibility
        different_count = sum(
            1 for k in RARITY_COLORS
            if RARITY_COLORS[k] != RARITY_COLORS_COLORBLIND[k]
        )
        assert different_count > 0


class TestValueColors:
    """Tests for value indicator colors."""

    def test_value_levels_defined(self):
        """Should define high, medium, low value colors."""
        assert "high_value" in VALUE_COLORS
        assert "medium_value" in VALUE_COLORS
        assert "low_value" in VALUE_COLORS

    def test_colorblind_value_colors(self):
        """Colorblind variant should have same keys."""
        for key in VALUE_COLORS:
            assert key in VALUE_COLORS_COLORBLIND


class TestStatColors:
    """Tests for stat colors."""

    def test_stat_colors_defined(self):
        """Should define life, es, mana colors."""
        assert "life" in STAT_COLORS
        assert "es" in STAT_COLORS
        assert "mana" in STAT_COLORS


class TestStatusColors:
    """Tests for status colors."""

    def test_status_colors_defined(self):
        """Should define status indicator colors."""
        expected = ["upgrade", "fractured", "synthesised", "corrupted", "crafted"]
        for status in expected:
            assert status in STATUS_COLORS


class TestThemeColorDictionaries:
    """Tests for theme color dictionaries."""

    def test_dark_theme_keys(self):
        """Dark theme should have all required keys."""
        required_keys = [
            "background", "surface", "surface_alt", "surface_hover",
            "border", "text", "text_secondary", "accent", "accent_blue",
            "accent_hover", "button_hover", "button_disabled_bg",
            "button_disabled_text", "alternate_row",
        ]
        for key in required_keys:
            assert key in DARK_THEME, f"Missing key in DARK_THEME: {key}"

    def test_light_theme_keys(self):
        """Light theme should have same keys as dark."""
        for key in DARK_THEME:
            assert key in LIGHT_THEME

    def test_all_themes_have_required_keys(self):
        """All theme dicts should have required keys."""
        for theme, colors in THEME_COLORS.items():
            assert "background" in colors, f"{theme} missing background"
            assert "text" in colors, f"{theme} missing text"
            assert "accent" in colors, f"{theme} missing accent"

    def test_solarized_themes(self):
        """Solarized themes should exist."""
        assert Theme.SOLARIZED_DARK in THEME_COLORS
        assert Theme.SOLARIZED_LIGHT in THEME_COLORS

    def test_dracula_theme(self):
        """Dracula theme should have distinct pink accent."""
        assert "#ff79c6" in DRACULA_THEME.values()

    def test_nord_theme(self):
        """Nord theme should have frost-like accent."""
        assert "88c0d0" in NORD_THEME["accent"].lower()


class TestColorblindThemes:
    """Tests for colorblind theme set."""

    def test_colorblind_themes_defined(self):
        """COLORBLIND_THEMES should contain accessibility themes."""
        assert Theme.COLORBLIND_DEUTERANOPIA in COLORBLIND_THEMES
        assert Theme.COLORBLIND_PROTANOPIA in COLORBLIND_THEMES
        assert Theme.COLORBLIND_TRITANOPIA in COLORBLIND_THEMES

    def test_non_colorblind_not_included(self):
        """Standard themes should not be in colorblind set."""
        assert Theme.DARK not in COLORBLIND_THEMES
        assert Theme.LIGHT not in COLORBLIND_THEMES
        assert Theme.DRACULA not in COLORBLIND_THEMES


class TestThemeBannerMap:
    """Tests for THEME_BANNER_MAP."""

    def test_all_themes_have_banner_mapping(self):
        """Every theme should map to a banner folder."""
        for theme in Theme:
            assert theme in THEME_BANNER_MAP

    def test_banner_values_are_strings(self):
        """Banner folder names should be strings."""
        for folder in THEME_BANNER_MAP.values():
            assert isinstance(folder, str)
            assert len(folder) > 0


class TestThemeManager:
    """Tests for ThemeManager class."""

    @pytest.fixture
    def fresh_manager(self):
        """Create a fresh ThemeManager (bypass singleton)."""
        # Reset singleton and clear callbacks
        ThemeManager.reset_for_testing()
        manager = ThemeManager()
        yield manager
        # Reset again for cleanup
        ThemeManager.reset_for_testing()

    def test_singleton_pattern(self):
        """Should return same instance."""
        ThemeManager.reset_for_testing()
        m1 = ThemeManager()
        m2 = ThemeManager()
        assert m1 is m2
        ThemeManager.reset_for_testing()

    def test_default_theme_is_dark(self, fresh_manager):
        """Default theme should be dark."""
        assert fresh_manager.current_theme == Theme.DARK

    def test_set_theme(self, fresh_manager):
        """Should change current theme."""
        fresh_manager.set_theme(Theme.LIGHT)
        assert fresh_manager.current_theme == Theme.LIGHT

    def test_set_theme_updates_colors(self, fresh_manager):
        """Setting theme should update colors dict."""
        fresh_manager.set_theme(Theme.DARK)
        dark_bg = fresh_manager.colors["background"]

        fresh_manager.set_theme(Theme.LIGHT)
        light_bg = fresh_manager.colors["background"]

        assert dark_bg != light_bg

    def test_set_theme_by_name(self, fresh_manager):
        """Should set theme by string name."""
        result = fresh_manager.set_theme_by_name("nord")
        assert result is True
        assert fresh_manager.current_theme == Theme.NORD

    def test_set_theme_by_name_invalid(self, fresh_manager):
        """Should return False for invalid theme name."""
        result = fresh_manager.set_theme_by_name("invalid_theme")
        assert result is False

    def test_toggle_theme_from_dark(self, fresh_manager):
        """Toggle from dark should go to light."""
        fresh_manager.set_theme(Theme.DARK)
        new_theme = fresh_manager.toggle_theme()
        assert new_theme == Theme.LIGHT

    def test_toggle_theme_from_light(self, fresh_manager):
        """Toggle from light should go to dark."""
        fresh_manager.set_theme(Theme.LIGHT)
        new_theme = fresh_manager.toggle_theme()
        assert new_theme == Theme.DARK

    def test_colors_include_rarity(self, fresh_manager):
        """Colors should include rarity colors."""
        assert "unique" in fresh_manager.colors
        assert "rare" in fresh_manager.colors

    def test_colors_include_values(self, fresh_manager):
        """Colors should include value colors."""
        assert "high_value" in fresh_manager.colors
        assert "medium_value" in fresh_manager.colors

    def test_colorblind_theme_uses_safe_colors(self, fresh_manager):
        """Colorblind themes should use colorblind-safe colors."""
        fresh_manager.set_theme(Theme.COLORBLIND_DEUTERANOPIA)
        # Colorblind-safe unique color
        assert fresh_manager.colors["unique"] == RARITY_COLORS_COLORBLIND["unique"]

    def test_register_callback(self, fresh_manager):
        """Should register and call theme change callbacks."""
        callback_called = []

        def on_theme_change(theme):
            callback_called.append(theme)

        fresh_manager.register_callback(on_theme_change)
        fresh_manager.set_theme(Theme.NORD)

        assert len(callback_called) == 1
        assert callback_called[0] == Theme.NORD

    def test_unregister_callback(self, fresh_manager):
        """Should unregister callbacks."""
        callback_called = []

        def on_theme_change(theme):
            callback_called.append(theme)

        fresh_manager.register_callback(on_theme_change)
        fresh_manager.unregister_callback(on_theme_change)
        fresh_manager.set_theme(Theme.NORD)

        assert len(callback_called) == 0

    def test_callback_error_handled(self, fresh_manager):
        """Should handle callback errors gracefully."""
        def bad_callback(theme):
            raise ValueError("Test error")

        fresh_manager.register_callback(bad_callback)
        # Should not raise
        fresh_manager.set_theme(Theme.LIGHT)

    def test_get_available_themes(self, fresh_manager):
        """Should return theme categories."""
        themes = fresh_manager.get_available_themes()
        assert "Standard" in themes
        assert "Accessibility" in themes

    def test_get_theme_display_name(self, fresh_manager):
        """Should return display name for theme."""
        name = fresh_manager.get_theme_display_name(Theme.DRACULA)
        assert name == "Dracula"

    def test_get_stylesheet(self, fresh_manager):
        """Should generate stylesheet string."""
        stylesheet = fresh_manager.get_stylesheet()
        assert isinstance(stylesheet, str)
        assert "QMainWindow" in stylesheet
        assert "QPushButton" in stylesheet
        assert "QLineEdit" in stylesheet

    def test_stylesheet_uses_theme_colors(self, fresh_manager):
        """Stylesheet should contain theme colors."""
        fresh_manager.set_theme(Theme.DARK)
        stylesheet = fresh_manager.get_stylesheet()
        # Dark theme background color
        assert DARK_THEME["background"] in stylesheet


class TestGetThemeManager:
    """Tests for get_theme_manager function."""

    def test_returns_manager(self):
        """Should return ThemeManager instance."""
        ThemeManager.reset_for_testing()
        manager = get_theme_manager()
        assert isinstance(manager, ThemeManager)
        ThemeManager.reset_for_testing()

    def test_returns_same_instance(self):
        """Should return same instance on repeated calls."""
        ThemeManager.reset_for_testing()
        m1 = get_theme_manager()
        m2 = get_theme_manager()
        assert m1 is m2
        ThemeManager.reset_for_testing()


class TestGetRarityColor:
    """Tests for get_rarity_color function."""

    def test_returns_color_for_rarity(self):
        """Should return color for known rarity."""
        ThemeManager.reset_for_testing()
        color = get_rarity_color("unique")
        assert isinstance(color, str)
        assert color.startswith("#")
        ThemeManager.reset_for_testing()

    def test_case_insensitive(self):
        """Should handle different cases."""
        color1 = get_rarity_color("Unique")
        color2 = get_rarity_color("UNIQUE")
        color3 = get_rarity_color("unique")
        assert color1 == color2 == color3

    def test_unknown_returns_text_color(self):
        """Should return text color for unknown rarity."""
        color = get_rarity_color("unknown_rarity")
        # Should return text color from current theme
        assert isinstance(color, str)


class TestGetValueColor:
    """Tests for get_value_color function."""

    def test_high_value(self):
        """Should return high value color for >= 100."""
        ThemeManager.reset_for_testing()
        color = get_value_color(150)
        assert isinstance(color, str)
        ThemeManager.reset_for_testing()

    def test_medium_value(self):
        """Should return medium value color for >= 10."""
        color = get_value_color(50)
        assert isinstance(color, str)

    def test_low_value(self):
        """Should return low value color for < 10."""
        color = get_value_color(5)
        assert isinstance(color, str)

    def test_threshold_100(self):
        """100 should be high value."""
        high = get_value_color(100)
        medium = get_value_color(99)
        # They should be different colors
        assert high != medium

    def test_threshold_10(self):
        """10 should be medium value."""
        medium = get_value_color(10)
        low = get_value_color(9)
        # They should be different colors
        assert medium != low

    def test_zero_value(self):
        """Zero should return low value color."""
        color = get_value_color(0)
        assert isinstance(color, str)

    def test_negative_value(self):
        """Negative values should return low value color."""
        color = get_value_color(-10)
        assert isinstance(color, str)
