"""Tests for gui_qt/shortcuts.py - Keyboard shortcuts management."""

from unittest.mock import MagicMock, patch

import pytest

from gui_qt.shortcuts import (
    ShortcutCategory,
    ShortcutDef,
    DEFAULT_SHORTCUTS,
    ShortcutManager,
    get_shortcut_manager,
    get_shortcuts_help_text,
)


class TestShortcutCategory:
    """Tests for ShortcutCategory enum."""

    def test_all_categories_defined(self):
        """Should have expected categories."""
        expected = ["GENERAL", "PRICE_CHECK", "BUILD", "NAVIGATION", "VIEW", "DATA"]
        for name in expected:
            assert hasattr(ShortcutCategory, name)

    def test_category_values_are_strings(self):
        """Category values should be human-readable strings."""
        for cat in ShortcutCategory:
            assert isinstance(cat.value, str)
            assert len(cat.value) > 0

    def test_specific_values(self):
        """Check specific category values."""
        assert ShortcutCategory.GENERAL.value == "General"
        assert ShortcutCategory.PRICE_CHECK.value == "Price Checking"
        assert ShortcutCategory.BUILD.value == "Build & PoB"


class TestShortcutDef:
    """Tests for ShortcutDef dataclass."""

    def test_create_basic_shortcut(self):
        """Should create shortcut with required fields."""
        shortcut = ShortcutDef(
            action_id="test_action",
            name="Test Action",
            description="A test action",
            default_key="Ctrl+T",
            category=ShortcutCategory.GENERAL,
        )

        assert shortcut.action_id == "test_action"
        assert shortcut.name == "Test Action"
        assert shortcut.description == "A test action"
        assert shortcut.default_key == "Ctrl+T"
        assert shortcut.category == ShortcutCategory.GENERAL

    def test_default_is_global_false(self):
        """is_global should default to False."""
        shortcut = ShortcutDef(
            action_id="test",
            name="Test",
            description="Test",
            default_key="Ctrl+T",
            category=ShortcutCategory.GENERAL,
        )
        assert shortcut.is_global is False

    def test_create_global_shortcut(self):
        """Should create global shortcut."""
        shortcut = ShortcutDef(
            action_id="test",
            name="Test",
            description="Test",
            default_key="Ctrl+T",
            category=ShortcutCategory.GENERAL,
            is_global=True,
        )
        assert shortcut.is_global is True


class TestDefaultShortcuts:
    """Tests for DEFAULT_SHORTCUTS list."""

    def test_shortcuts_defined(self):
        """Should have shortcuts defined."""
        assert len(DEFAULT_SHORTCUTS) > 0

    def test_all_shortcuts_are_shortcut_def(self):
        """All entries should be ShortcutDef."""
        for shortcut in DEFAULT_SHORTCUTS:
            assert isinstance(shortcut, ShortcutDef)

    def test_unique_action_ids(self):
        """Action IDs should be unique."""
        action_ids = [s.action_id for s in DEFAULT_SHORTCUTS]
        assert len(action_ids) == len(set(action_ids))

    def test_important_shortcuts_exist(self):
        """Important shortcuts should be defined."""
        action_ids = [s.action_id for s in DEFAULT_SHORTCUTS]
        assert "check_price" in action_ids
        assert "show_command_palette" in action_ids
        assert "toggle_theme" in action_ids
        assert "show_shortcuts" in action_ids

    def test_all_categories_used(self):
        """All categories should have at least one shortcut."""
        categories_used = {s.category for s in DEFAULT_SHORTCUTS}
        for cat in ShortcutCategory:
            assert cat in categories_used, f"No shortcuts in category {cat}"

    def test_shortcuts_have_valid_keys(self):
        """Shortcuts with keys should have valid format."""
        # Some shortcuts intentionally have no keys (menu-only actions)
        shortcuts_with_keys = [s for s in DEFAULT_SHORTCUTS if s.default_key]
        assert len(shortcuts_with_keys) > 0, "At least some shortcuts should have keys"

        for shortcut in shortcuts_with_keys:
            assert len(shortcut.default_key) > 0


class TestShortcutManager:
    """Tests for ShortcutManager class."""

    @pytest.fixture
    def fresh_manager(self):
        """Create a fresh ShortcutManager."""
        ShortcutManager._instance = None
        manager = ShortcutManager()
        yield manager
        ShortcutManager._instance = None

    def test_singleton_pattern(self):
        """Should return same instance."""
        ShortcutManager._instance = None
        m1 = ShortcutManager.instance()
        m2 = ShortcutManager.instance()
        assert m1 is m2
        ShortcutManager._instance = None

    def test_init_loads_default_shortcuts(self, fresh_manager):
        """Should initialize with default shortcuts."""
        shortcuts = fresh_manager.get_all_shortcuts()
        assert len(shortcuts) == len(DEFAULT_SHORTCUTS)

    def test_get_key_returns_default(self, fresh_manager):
        """Should return default key when no custom key set."""
        key = fresh_manager.get_key("check_price")
        # Find expected default key
        expected = next(
            s.default_key for s in DEFAULT_SHORTCUTS if s.action_id == "check_price"
        )
        assert key == expected

    def test_get_key_returns_custom(self, fresh_manager):
        """Should return custom key when set."""
        fresh_manager.set_custom_key("check_price", "Ctrl+Shift+Return")
        key = fresh_manager.get_key("check_price")
        assert key == "Ctrl+Shift+Return"

    def test_get_key_unknown_returns_empty(self, fresh_manager):
        """Should return empty string for unknown action."""
        key = fresh_manager.get_key("unknown_action")
        assert key == ""

    def test_set_custom_key(self, fresh_manager):
        """Should set custom key."""
        fresh_manager.set_custom_key("toggle_theme", "Ctrl+Alt+T")
        assert fresh_manager.get_key("toggle_theme") == "Ctrl+Alt+T"

    def test_reset_to_default(self, fresh_manager):
        """Should reset to default key."""
        # Set custom key
        fresh_manager.set_custom_key("toggle_theme", "Ctrl+Alt+T")
        assert fresh_manager.get_key("toggle_theme") == "Ctrl+Alt+T"

        # Reset
        fresh_manager.reset_to_default("toggle_theme")

        # Should be back to default
        expected = next(
            s.default_key for s in DEFAULT_SHORTCUTS if s.action_id == "toggle_theme"
        )
        assert fresh_manager.get_key("toggle_theme") == expected

    def test_reset_all_to_defaults(self, fresh_manager):
        """Should reset all to defaults."""
        # Set multiple custom keys
        fresh_manager.set_custom_key("toggle_theme", "Ctrl+Alt+T")
        fresh_manager.set_custom_key("check_price", "F5")

        # Reset all
        fresh_manager.reset_all_to_defaults()

        # Should be back to defaults
        toggle_expected = next(
            s.default_key for s in DEFAULT_SHORTCUTS if s.action_id == "toggle_theme"
        )
        price_expected = next(
            s.default_key for s in DEFAULT_SHORTCUTS if s.action_id == "check_price"
        )
        assert fresh_manager.get_key("toggle_theme") == toggle_expected
        assert fresh_manager.get_key("check_price") == price_expected

    def test_register_callback(self, fresh_manager):
        """Should register callback."""
        callback_called = []

        def on_check_price():
            callback_called.append(True)

        fresh_manager.register("check_price", on_check_price)
        assert "check_price" in fresh_manager._callbacks

    def test_trigger_calls_callback(self, fresh_manager):
        """Should trigger registered callback."""
        callback_called = []

        def on_check_price():
            callback_called.append(True)

        fresh_manager.register("check_price", on_check_price)
        result = fresh_manager.trigger("check_price")

        assert result is True
        assert len(callback_called) == 1

    def test_trigger_unknown_returns_false(self, fresh_manager):
        """Should return False for unknown action."""
        result = fresh_manager.trigger("unknown_action")
        assert result is False

    def test_trigger_handles_callback_error(self, fresh_manager):
        """Should handle callback errors gracefully."""
        def bad_callback():
            raise ValueError("Test error")

        fresh_manager.register("check_price", bad_callback)
        result = fresh_manager.trigger("check_price")

        assert result is False

    def test_get_shortcut_def(self, fresh_manager):
        """Should return shortcut definition."""
        shortcut_def = fresh_manager.get_shortcut_def("check_price")

        assert shortcut_def is not None
        assert shortcut_def.action_id == "check_price"
        assert shortcut_def.category == ShortcutCategory.PRICE_CHECK

    def test_get_shortcut_def_unknown(self, fresh_manager):
        """Should return None for unknown action."""
        shortcut_def = fresh_manager.get_shortcut_def("unknown")
        assert shortcut_def is None

    def test_get_all_shortcuts(self, fresh_manager):
        """Should return all shortcuts."""
        shortcuts = fresh_manager.get_all_shortcuts()
        assert len(shortcuts) > 0
        assert all(isinstance(s, ShortcutDef) for s in shortcuts)

    def test_get_shortcuts_by_category(self, fresh_manager):
        """Should return shortcuts organized by category."""
        by_category = fresh_manager.get_shortcuts_by_category()

        assert isinstance(by_category, dict)
        assert ShortcutCategory.GENERAL in by_category
        assert ShortcutCategory.PRICE_CHECK in by_category

        # Check shortcuts are in correct category
        for shortcut in by_category[ShortcutCategory.PRICE_CHECK]:
            assert shortcut.category == ShortcutCategory.PRICE_CHECK

    def test_load_from_config(self, fresh_manager):
        """Should load custom keys from config."""
        config_data = {
            "toggle_theme": "F12",
            "check_price": "F5",
        }

        fresh_manager.load_from_config(config_data)

        assert fresh_manager.get_key("toggle_theme") == "F12"
        assert fresh_manager.get_key("check_price") == "F5"

    def test_save_to_config(self, fresh_manager):
        """Should save custom keys to config."""
        fresh_manager.set_custom_key("toggle_theme", "F12")
        fresh_manager.set_custom_key("check_price", "F5")

        config = fresh_manager.save_to_config()

        assert config["toggle_theme"] == "F12"
        assert config["check_price"] == "F5"

    def test_get_action_for_palette(self, fresh_manager):
        """Should return actions formatted for command palette."""
        # Register some callbacks
        fresh_manager.register("check_price", lambda: None)
        fresh_manager.register("toggle_theme", lambda: None)

        actions = fresh_manager.get_action_for_palette()

        assert isinstance(actions, list)
        assert len(actions) >= 2

        # Check action format
        for action in actions:
            assert "id" in action
            assert "name" in action
            assert "description" in action
            assert "shortcut" in action
            assert "category" in action

    def test_get_action_for_palette_only_registered(self, fresh_manager):
        """Should only return actions with callbacks."""
        # Register only one callback
        fresh_manager.register("check_price", lambda: None)

        actions = fresh_manager.get_action_for_palette()

        action_ids = [a["id"] for a in actions]
        assert "check_price" in action_ids
        # toggle_theme not registered, so not in palette
        assert "toggle_theme" not in action_ids

    def test_set_window(self, fresh_manager):
        """Should set window reference."""
        mock_window = MagicMock()
        fresh_manager.set_window(mock_window)
        assert fresh_manager._window is mock_window


class TestGetShortcutManager:
    """Tests for get_shortcut_manager function."""

    def test_returns_manager(self):
        """Should return ShortcutManager instance."""
        ShortcutManager._instance = None
        manager = get_shortcut_manager()
        assert isinstance(manager, ShortcutManager)
        ShortcutManager._instance = None

    def test_returns_same_instance(self):
        """Should return same instance on repeated calls."""
        ShortcutManager._instance = None
        m1 = get_shortcut_manager()
        m2 = get_shortcut_manager()
        assert m1 is m2
        ShortcutManager._instance = None


class TestGetShortcutsHelpText:
    """Tests for get_shortcuts_help_text function."""

    def test_returns_string(self):
        """Should return formatted string."""
        ShortcutManager._instance = None
        text = get_shortcuts_help_text()
        assert isinstance(text, str)
        assert len(text) > 0
        ShortcutManager._instance = None

    def test_contains_header(self):
        """Should contain header."""
        text = get_shortcuts_help_text()
        assert "Keyboard Shortcuts" in text

    def test_contains_categories(self):
        """Should contain category headers."""
        text = get_shortcuts_help_text()
        assert "General" in text
        assert "Price Checking" in text

    def test_contains_shortcut_keys(self):
        """Should contain shortcut keys."""
        text = get_shortcuts_help_text()
        # Check for some common keys
        assert "Ctrl" in text or "F1" in text

    def test_contains_shortcut_names(self):
        """Should contain shortcut names."""
        text = get_shortcuts_help_text()
        # Check for some shortcut names
        assert "Check Price" in text or "Toggle Theme" in text


class TestShortcutManagerWithMockedQt:
    """Tests for ShortcutManager Qt integration with mocks."""

    @pytest.fixture
    def manager_with_mocked_window(self):
        """Create manager with mocked Qt window."""
        ShortcutManager._instance = None
        manager = ShortcutManager()

        # Create mock window
        mock_window = MagicMock()
        manager.set_window(mock_window)

        yield manager, mock_window
        ShortcutManager._instance = None

    def test_register_creates_qt_shortcut(self, manager_with_mocked_window):
        """Should create QShortcut when registering."""
        manager, mock_window = manager_with_mocked_window

        with patch('gui_qt.shortcuts.QShortcut') as MockShortcut:
            mock_shortcut_instance = MagicMock()
            MockShortcut.return_value = mock_shortcut_instance

            manager.register("check_price", lambda: None)

            # QShortcut should have been created
            MockShortcut.assert_called_once()

    def test_set_custom_key_updates_qt_shortcut(self, manager_with_mocked_window):
        """Should update QShortcut when custom key set."""
        manager, mock_window = manager_with_mocked_window

        with patch('gui_qt.shortcuts.QShortcut') as MockShortcut:
            mock_shortcut_instance = MagicMock()
            MockShortcut.return_value = mock_shortcut_instance

            # Register first
            manager.register("check_price", lambda: None)

            # Change key
            manager.set_custom_key("check_price", "F5")

            # Should have created new shortcut
            assert MockShortcut.call_count >= 2

    def test_register_all_creates_shortcuts_for_callbacks(self, manager_with_mocked_window):
        """Should create shortcuts for all registered callbacks."""
        manager, mock_window = manager_with_mocked_window

        # Register multiple callbacks
        manager._callbacks["check_price"] = lambda: None
        manager._callbacks["toggle_theme"] = lambda: None

        with patch('gui_qt.shortcuts.QShortcut') as MockShortcut:
            mock_shortcut_instance = MagicMock()
            MockShortcut.return_value = mock_shortcut_instance

            manager.register_all()

            # Should have created shortcuts for both
            assert MockShortcut.call_count >= 2
