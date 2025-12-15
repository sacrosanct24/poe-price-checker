"""
Accessibility Package - WCAG 2.2 AA compliance utilities.

This package provides accessibility features for the PyQt6 application:
- Screen reader support via QAccessible
- Focus management and visible focus indicators
- Keyboard navigation enhancements

Usage:
    from gui_qt.accessibility import (
        # Screen reader support
        set_accessible_name,
        set_accessible_description,
        announce,
        AccessibleWidget,

        # Focus management
        FocusManager,
        set_focus_order,
        apply_focus_style,

        # Keyboard navigation
        KeyboardNavigator,
        install_arrow_navigation,
    )
"""

from gui_qt.accessibility.screen_reader import (
    set_accessible_name,
    set_accessible_description,
    set_accessible_role,
    announce,
    announce_polite,
    announce_assertive,
    AccessibleWidget,
    AccessibleMixin,
    setup_accessible_table,
)
from gui_qt.accessibility.focus_manager import (
    FocusManager,
    get_focus_manager,
    set_focus_order,
    apply_focus_style,
    FocusRing,
    FocusStyleMixin,
)
from gui_qt.accessibility.keyboard_nav import (
    KeyboardNavigator,
    install_arrow_navigation,
    install_dialog_shortcuts,
    ArrowNavigationMixin,
    add_button_mnemonic,
    setup_button_mnemonics,
    create_shortcut,
)

__all__ = [
    # Screen reader
    "set_accessible_name",
    "set_accessible_description",
    "set_accessible_role",
    "announce",
    "announce_polite",
    "announce_assertive",
    "AccessibleWidget",
    "AccessibleMixin",
    "setup_accessible_table",
    # Focus management
    "FocusManager",
    "get_focus_manager",
    "set_focus_order",
    "apply_focus_style",
    "FocusRing",
    "FocusStyleMixin",
    # Keyboard navigation
    "KeyboardNavigator",
    "install_arrow_navigation",
    "install_dialog_shortcuts",
    "ArrowNavigationMixin",
    "add_button_mnemonic",
    "setup_button_mnemonics",
    "create_shortcut",
]
