"""
gui_qt.mixins - Mixin classes for main window functionality.

Mixins help decompose the main window into smaller, focused pieces:
- ShortcutsMixin: Keyboard shortcut registration and handling
- MenuBarMixin: Menu bar creation with declarative MenuBuilder
- BackgroundServicesMixin: Background worker and service management
"""

from gui_qt.mixins.shortcuts_mixin import ShortcutsMixin
from gui_qt.mixins.menu_bar_mixin import MenuBarMixin
from gui_qt.mixins.background_services_mixin import BackgroundServicesMixin

__all__ = [
    "ShortcutsMixin",
    "MenuBarMixin",
    "BackgroundServicesMixin",
]
