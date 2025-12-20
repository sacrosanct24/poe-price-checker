"""
Tests for gui_qt.shortcuts module.

Tests the keyboard shortcuts management system.
"""

import pytest
from unittest.mock import MagicMock

from gui_qt.shortcuts import (
    ShortcutCategory,
    ShortcutDef,
    ShortcutManager,
    DEFAULT_SHORTCUTS,
    get_shortcut_manager,
    get_shortcuts_help_text,
)


class TestShortcutCategory:
    """Tests for ShortcutCategory enum."""

    def test_all_categories_exist(self):
        """Verify all expected categories are defined."""
        assert ShortcutCategory.GENERAL.value == "General"
        assert ShortcutCategory.PRICE_CHECK.value == "Price Checking"
        assert ShortcutCategory.BUILD.value == "Build & PoB"
        assert ShortcutCategory.NAVIGATION.value == "Navigation"
        assert ShortcutCategory.VIEW.value == "View & Theme"
        assert ShortcutCategory.DATA.value == "Data & Export"


class TestShortcutDef:
    """Tests for ShortcutDef dataclass."""

    def test_shortcut_def_creation(self):
        """Test creating a ShortcutDef."""
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
        assert shortcut.is_global is False

    def test_shortcut_def_global(self):
        """Test creating a global ShortcutDef."""
        shortcut = ShortcutDef(
            action_id="global_action",
            name="Global Action",
            description="A global action",
            default_key="F1",
            category=ShortcutCategory.GENERAL,
            is_global=True,
        )

        assert shortcut.is_global is True


class TestDefaultShortcuts:
    """Tests for DEFAULT_SHORTCUTS list."""

    def test_default_shortcuts_not_empty(self):
        """Test that default shortcuts list is not empty."""
        assert len(DEFAULT_SHORTCUTS) > 0

    def test_all_shortcuts_have_unique_ids(self):
        """Test that all shortcuts have unique action IDs."""
        ids = [s.action_id for s in DEFAULT_SHORTCUTS]
        assert len(ids) == len(set(ids)), "Duplicate action IDs found"

    def test_all_shortcuts_have_unique_keys(self):
        """Test that shortcuts with keys have unique default keys (empty keys are ok)."""
        # Filter out empty keys - those are "no shortcut" entries (e.g., navigation shortcuts)
        keys = [s.default_key for s in DEFAULT_SHORTCUTS if s.default_key]
        assert len(keys) == len(set(keys)), "Duplicate default keys found"

    def test_expected_shortcuts_exist(self):
        """Test that expected shortcuts are defined."""
        action_ids = {s.action_id for s in DEFAULT_SHORTCUTS}

        # General
        assert "show_shortcuts" in action_ids
        assert "show_command_palette" in action_ids

        # Price Check
        assert "check_price" in action_ids
        assert "paste_and_check" in action_ids
        assert "clear_input" in action_ids

        # Build & PoB (Phase 1: merged features)
        assert "show_build_manager" in action_ids
        assert "show_item_planning_hub" in action_ids
        assert "show_item_comparison" in action_ids

        # Navigation
        assert "show_history" in action_ids
        assert "show_stash_viewer" in action_ids

        # View & Theme
        assert "toggle_theme" in action_ids

    def test_shortcuts_have_valid_categories(self):
        """Test all shortcuts have valid categories."""
        for shortcut in DEFAULT_SHORTCUTS:
            assert isinstance(shortcut.category, ShortcutCategory)


class TestShortcutManager:
    """Tests for ShortcutManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ShortcutManager instance."""
        # Reset singleton for testing
        ShortcutManager._instance = None
        return ShortcutManager()

    def test_singleton_instance(self):
        """Test singleton pattern."""
        ShortcutManager._instance = None
        manager1 = ShortcutManager.instance()
        manager2 = ShortcutManager.instance()
        assert manager1 is manager2

    def test_initialized_with_defaults(self, manager):
        """Test manager is initialized with default shortcuts."""
        shortcuts = manager.get_all_shortcuts()
        assert len(shortcuts) == len(DEFAULT_SHORTCUTS)

    def test_get_key_default(self, manager):
        """Test getting default key for an action."""
        key = manager.get_key("show_shortcuts")
        assert key == "F1"

    def test_get_key_nonexistent(self, manager):
        """Test getting key for nonexistent action."""
        key = manager.get_key("nonexistent_action")
        assert key == ""

    def test_set_custom_key(self, manager):
        """Test setting a custom key."""
        manager.set_custom_key("show_shortcuts", "F2")
        assert manager.get_key("show_shortcuts") == "F2"

    def test_reset_to_default(self, manager):
        """Test resetting a custom key to default."""
        manager.set_custom_key("show_shortcuts", "F2")
        manager.reset_to_default("show_shortcuts")
        assert manager.get_key("show_shortcuts") == "F1"

    def test_reset_all_to_defaults(self, manager):
        """Test resetting all keys to defaults."""
        manager.set_custom_key("show_shortcuts", "F2")
        manager.set_custom_key("exit", "Ctrl+Q")
        manager.reset_all_to_defaults()

        assert manager.get_key("show_shortcuts") == "F1"
        assert manager.get_key("exit") == "Alt+F4"

    def test_register_callback(self, manager):
        """Test registering a callback."""
        callback = MagicMock()
        manager.register("show_shortcuts", callback)

        assert "show_shortcuts" in manager._callbacks
        assert manager._callbacks["show_shortcuts"] is callback

    def test_trigger_callback(self, manager):
        """Test triggering a registered callback."""
        callback = MagicMock()
        manager.register("show_shortcuts", callback)

        result = manager.trigger("show_shortcuts")

        assert result is True
        callback.assert_called_once()

    def test_trigger_nonexistent_callback(self, manager):
        """Test triggering a nonexistent callback."""
        result = manager.trigger("nonexistent_action")
        assert result is False

    def test_trigger_callback_with_exception(self, manager):
        """Test triggering a callback that raises exception."""
        callback = MagicMock(side_effect=Exception("Test error"))
        manager.register("show_shortcuts", callback)

        result = manager.trigger("show_shortcuts")

        assert result is False

    def test_get_shortcut_def(self, manager):
        """Test getting shortcut definition."""
        shortcut_def = manager.get_shortcut_def("show_shortcuts")

        assert shortcut_def is not None
        assert shortcut_def.action_id == "show_shortcuts"
        assert shortcut_def.name == "Keyboard Shortcuts"

    def test_get_shortcut_def_nonexistent(self, manager):
        """Test getting nonexistent shortcut definition."""
        shortcut_def = manager.get_shortcut_def("nonexistent")
        assert shortcut_def is None

    def test_get_shortcuts_by_category(self, manager):
        """Test getting shortcuts organized by category."""
        by_category = manager.get_shortcuts_by_category()

        assert ShortcutCategory.GENERAL in by_category
        assert ShortcutCategory.PRICE_CHECK in by_category
        assert ShortcutCategory.BUILD in by_category

        # Check each category has shortcuts
        for category, shortcuts in by_category.items():
            assert len(shortcuts) > 0
            for shortcut in shortcuts:
                assert shortcut.category == category

    def test_load_from_config(self, manager):
        """Test loading custom keys from config."""
        config_data = {
            "show_shortcuts": "F2",
            "exit": "Ctrl+Q",
        }
        manager.load_from_config(config_data)

        assert manager.get_key("show_shortcuts") == "F2"
        assert manager.get_key("exit") == "Ctrl+Q"

    def test_save_to_config(self, manager):
        """Test saving custom keys to config."""
        manager.set_custom_key("show_shortcuts", "F2")
        manager.set_custom_key("exit", "Ctrl+Q")

        config_data = manager.save_to_config()

        assert config_data == {
            "show_shortcuts": "F2",
            "exit": "Ctrl+Q",
        }

    def test_get_action_for_palette(self, manager):
        """Test getting actions for command palette."""
        callback = MagicMock()
        manager.register("show_shortcuts", callback)

        actions = manager.get_action_for_palette()

        assert len(actions) > 0
        # Only registered actions should be included
        action_ids = [a["id"] for a in actions]
        assert "show_shortcuts" in action_ids

        # Check action format
        for action in actions:
            assert "id" in action
            assert "name" in action
            assert "description" in action
            assert "shortcut" in action
            assert "category" in action


class TestGetShortcutManager:
    """Tests for get_shortcut_manager function."""

    def test_returns_manager(self):
        """Test function returns a ShortcutManager instance."""
        ShortcutManager._instance = None
        manager = get_shortcut_manager()
        assert isinstance(manager, ShortcutManager)

    def test_returns_same_instance(self):
        """Test function returns the same singleton instance."""
        ShortcutManager._instance = None
        manager1 = get_shortcut_manager()
        manager2 = get_shortcut_manager()
        assert manager1 is manager2


class TestGetShortcutsHelpText:
    """Tests for get_shortcuts_help_text function."""

    def test_returns_string(self):
        """Test function returns a string."""
        ShortcutManager._instance = None
        help_text = get_shortcuts_help_text()
        assert isinstance(help_text, str)

    def test_includes_header(self):
        """Test help text includes header."""
        ShortcutManager._instance = None
        help_text = get_shortcuts_help_text()
        assert "Keyboard Shortcuts" in help_text

    def test_includes_categories(self):
        """Test help text includes category headers."""
        ShortcutManager._instance = None
        help_text = get_shortcuts_help_text()

        assert "General" in help_text
        assert "Price Checking" in help_text
        assert "Build & PoB" in help_text

    def test_includes_shortcut_keys(self):
        """Test help text includes shortcut keys."""
        ShortcutManager._instance = None
        help_text = get_shortcuts_help_text()

        assert "F1" in help_text  # show_shortcuts
        assert "Ctrl+Return" in help_text  # check_price
        assert "Ctrl+B" in help_text  # show_build_manager
