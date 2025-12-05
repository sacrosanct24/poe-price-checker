"""Tests for gui_qt.widgets.item_context_menu."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QWidget, QMenu

from gui_qt.widgets.item_context_menu import (
    ItemContext,
    ItemContextMenuManager,
    get_item_context_menu_manager,
    reset_for_testing,
)


class TestItemContext:
    """Tests for ItemContext dataclass."""

    def test_basic_creation(self):
        """Test creating a basic ItemContext."""
        ctx = ItemContext(item_name="Headhunter")
        assert ctx.item_name == "Headhunter"
        assert ctx.item_text == ""
        assert ctx.chaos_value == 0
        assert ctx.divine_value == 0
        assert ctx.source == ""
        assert ctx.parsed_item is None
        assert ctx.extra_data == {}

    def test_full_creation(self):
        """Test creating an ItemContext with all fields."""
        ctx = ItemContext(
            item_name="Mageblood",
            item_text="Rarity: Unique\nMageblood",
            chaos_value=50000,
            divine_value=300,
            source="poe.ninja",
            parsed_item={"mock": "item"},
            extra_data={"slot": "Belt"},
        )
        assert ctx.item_name == "Mageblood"
        assert ctx.item_text == "Rarity: Unique\nMageblood"
        assert ctx.chaos_value == 50000
        assert ctx.divine_value == 300
        assert ctx.source == "poe.ninja"
        assert ctx.parsed_item == {"mock": "item"}
        assert ctx.extra_data == {"slot": "Belt"}

    def test_get_price_results(self):
        """Test building price results list."""
        ctx = ItemContext(
            item_name="Ashes of the Stars",
            chaos_value=15000,
            divine_value=100,
            source="poe.ninja",
        )
        results = ctx.get_price_results()
        assert len(results) == 1
        assert results[0]["item_name"] == "Ashes of the Stars"
        assert results[0]["chaos_value"] == 15000
        assert results[0]["divine_value"] == 100
        assert results[0]["source"] == "poe.ninja"


class TestItemContextMenuManager:
    """Tests for ItemContextMenuManager."""

    @pytest.fixture
    def manager(self, qtbot):
        """Create a menu manager."""
        return ItemContextMenuManager()

    @pytest.fixture
    def parent_widget(self, qtbot):
        """Create a parent widget."""
        widget = QWidget()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def item_context(self):
        """Create a sample item context."""
        return ItemContext(
            item_name="Test Item",
            item_text="Rarity: Rare\nTest Item",
            chaos_value=100,
            divine_value=1,
            source="test",
        )

    def test_default_options(self, manager):
        """Test default option states."""
        # Default should show all options
        assert manager._show_inspect is True
        assert manager._show_price_check is True
        assert manager._show_ai is True
        assert manager._show_copy is True

    def test_set_options(self, manager):
        """Test setting options."""
        manager.set_options(
            show_inspect=False,
            show_price_check=True,
            show_ai=False,
            show_copy=True,
        )
        assert manager._show_inspect is False
        assert manager._show_price_check is True
        assert manager._show_ai is False
        assert manager._show_copy is True

    def test_set_ai_configured_callback(self, manager):
        """Test setting AI configured callback."""
        callback = MagicMock(return_value=True)
        manager.set_ai_configured_callback(callback)
        assert manager._ai_configured_callback is callback

    def test_build_menu_all_options(self, manager, parent_widget, item_context):
        """Test building menu with all options."""
        menu = manager.build_menu(item_context, parent_widget)
        assert isinstance(menu, QMenu)

        # Get action names
        action_names = [a.text() for a in menu.actions()]
        assert "Inspect Item" in action_names
        assert "Price Check" in action_names
        assert "Ask AI About This Item" in action_names

    def test_build_menu_no_inspect(self, manager, parent_widget, item_context):
        """Test building menu without inspect option."""
        manager.set_options(show_inspect=False)
        menu = manager.build_menu(item_context, parent_widget)
        action_names = [a.text() for a in menu.actions()]
        assert "Inspect Item" not in action_names

    def test_build_menu_no_price_check(self, manager, parent_widget, item_context):
        """Test building menu without price check option."""
        manager.set_options(show_price_check=False)
        menu = manager.build_menu(item_context, parent_widget)
        action_names = [a.text() for a in menu.actions()]
        assert "Price Check" not in action_names

    def test_build_menu_no_ai(self, manager, parent_widget, item_context):
        """Test building menu without AI option."""
        manager.set_options(show_ai=False)
        menu = manager.build_menu(item_context, parent_widget)
        action_names = [a.text() for a in menu.actions()]
        assert "Ask AI About This Item" not in action_names

    def test_ai_action_disabled_when_not_configured(self, manager, parent_widget, item_context):
        """Test AI action is disabled when not configured."""
        manager.set_ai_configured_callback(lambda: False)
        menu = manager.build_menu(item_context, parent_widget)

        ai_action = None
        for action in menu.actions():
            if action.text() == "Ask AI About This Item":
                ai_action = action
                break

        assert ai_action is not None
        assert not ai_action.isEnabled()

    def test_ai_action_enabled_when_configured(self, manager, parent_widget, item_context):
        """Test AI action is enabled when configured."""
        manager.set_ai_configured_callback(lambda: True)
        menu = manager.build_menu(item_context, parent_widget)

        ai_action = None
        for action in menu.actions():
            if action.text() == "Ask AI About This Item":
                ai_action = action
                break

        assert ai_action is not None
        assert ai_action.isEnabled()

    def test_inspect_signal_emitted(self, manager, parent_widget, item_context, qtbot):
        """Test that inspect signal is emitted."""
        with qtbot.waitSignal(manager.inspect_requested, timeout=1000):
            menu = manager.build_menu(item_context, parent_widget)
            for action in menu.actions():
                if action.text() == "Inspect Item":
                    action.trigger()
                    break

    def test_price_check_signal_emitted(self, manager, parent_widget, item_context, qtbot):
        """Test that price check signal is emitted."""
        with qtbot.waitSignal(manager.price_check_requested, timeout=1000):
            menu = manager.build_menu(item_context, parent_widget)
            for action in menu.actions():
                if action.text() == "Price Check":
                    action.trigger()
                    break

    def test_ai_analysis_signal_emitted(self, manager, parent_widget, item_context, qtbot):
        """Test that AI analysis signal is emitted."""
        manager.set_ai_configured_callback(lambda: True)

        with qtbot.waitSignal(manager.ai_analysis_requested, timeout=1000):
            menu = manager.build_menu(item_context, parent_widget)
            for action in menu.actions():
                if action.text() == "Ask AI About This Item":
                    action.trigger()
                    break

    def test_copy_submenu_present(self, manager, parent_widget, item_context):
        """Test that copy submenu is present."""
        menu = manager.build_menu(item_context, parent_widget)

        # Look for the copy submenu
        copy_menu = None
        for action in menu.actions():
            if action.text() == "Copy":
                copy_menu = action.menu()
                break

        assert copy_menu is not None

    def test_copy_name_action(self, manager, parent_widget, item_context):
        """Test copy name action is present."""
        menu = manager.build_menu(item_context, parent_widget)

        # Find copy submenu
        for action in menu.actions():
            if action.text() == "Copy":
                copy_menu = action.menu()
                action_names = [a.text() for a in copy_menu.actions()]
                assert "Item Name" in action_names
                break


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_item_context_menu_manager_returns_same_instance(self):
        """Test that get_item_context_menu_manager returns singleton."""
        reset_for_testing()
        manager1 = get_item_context_menu_manager()
        manager2 = get_item_context_menu_manager()
        assert manager1 is manager2

    def test_reset_for_testing_clears_instance(self):
        """Test that reset_for_testing clears the singleton."""
        manager1 = get_item_context_menu_manager()
        reset_for_testing()
        manager2 = get_item_context_menu_manager()
        assert manager1 is not manager2
