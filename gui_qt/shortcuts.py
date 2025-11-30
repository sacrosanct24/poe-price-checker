"""
Keyboard shortcuts management for PoE Price Checker.

Provides:
- Centralized shortcut definitions with default keys
- Configurable shortcuts saved to config
- ShortcutManager singleton for registering and triggering actions
- Command palette integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)


class ShortcutCategory(Enum):
    """Categories for organizing shortcuts."""
    GENERAL = "General"
    PRICE_CHECK = "Price Checking"
    BUILD = "Build & PoB"
    NAVIGATION = "Navigation"
    VIEW = "View & Theme"
    DATA = "Data & Export"


@dataclass
class ShortcutDef:
    """Definition of a keyboard shortcut."""
    action_id: str
    name: str
    description: str
    default_key: str
    category: ShortcutCategory
    is_global: bool = False  # If True, works even when input has focus


# Default shortcut definitions
DEFAULT_SHORTCUTS: List[ShortcutDef] = [
    # General
    ShortcutDef("show_shortcuts", "Keyboard Shortcuts", "Show all keyboard shortcuts", "F1", ShortcutCategory.GENERAL),
    ShortcutDef("show_command_palette", "Command Palette", "Open command palette for quick access", "Ctrl+Shift+P", ShortcutCategory.GENERAL),
    ShortcutDef("show_tips", "Usage Tips", "Show usage tips", "Shift+F1", ShortcutCategory.GENERAL),
    ShortcutDef("exit", "Exit Application", "Close the application", "Alt+F4", ShortcutCategory.GENERAL),

    # Price Checking
    ShortcutDef("check_price", "Check Price", "Run price check on current item", "Ctrl+Return", ShortcutCategory.PRICE_CHECK),
    ShortcutDef("paste_and_check", "Paste & Check", "Paste from clipboard and check price", "Ctrl+Shift+V", ShortcutCategory.PRICE_CHECK),
    ShortcutDef("clear_input", "Clear Input", "Clear the item input area", "Escape", ShortcutCategory.PRICE_CHECK),
    ShortcutDef("focus_input", "Focus Input", "Focus the item input area", "Ctrl+L", ShortcutCategory.PRICE_CHECK),
    ShortcutDef("focus_filter", "Focus Filter", "Focus the results filter", "Ctrl+F", ShortcutCategory.PRICE_CHECK),

    # Build & PoB
    ShortcutDef("show_pob_characters", "PoB Characters", "Open PoB character manager", "Ctrl+B", ShortcutCategory.BUILD),
    ShortcutDef("show_bis_search", "BiS Item Search", "Find best-in-slot items", "Ctrl+I", ShortcutCategory.BUILD),
    ShortcutDef("show_upgrade_finder", "Upgrade Finder", "Find gear upgrades within budget", "Ctrl+U", ShortcutCategory.BUILD),
    ShortcutDef("show_build_library", "Build Library", "Manage saved build profiles", "Ctrl+Shift+L", ShortcutCategory.BUILD),
    ShortcutDef("show_build_comparison", "Compare Builds", "Compare passive tree builds", "Ctrl+Shift+B", ShortcutCategory.BUILD),
    ShortcutDef("show_item_comparison", "Compare Items", "Side-by-side item comparison", "Ctrl+Shift+I", ShortcutCategory.BUILD),
    ShortcutDef("show_rare_eval_config", "Rare Item Settings", "Configure rare item evaluation", "Ctrl+Shift+R", ShortcutCategory.BUILD),

    # Navigation
    ShortcutDef("show_history", "Session History", "Show items checked this session", "Ctrl+H", ShortcutCategory.NAVIGATION),
    ShortcutDef("show_stash_viewer", "Stash Viewer", "Open stash tab viewer", "Ctrl+Shift+S", ShortcutCategory.NAVIGATION),
    ShortcutDef("show_recent_sales", "Recent Sales", "View recent sale records", "Ctrl+Alt+S", ShortcutCategory.NAVIGATION),
    ShortcutDef("show_sales_dashboard", "Sales Dashboard", "View sales analytics", "Ctrl+Alt+D", ShortcutCategory.NAVIGATION),
    ShortcutDef("show_price_rankings", "Price Rankings", "View top 20 price rankings", "Ctrl+Shift+T", ShortcutCategory.NAVIGATION),

    # View & Theme
    ShortcutDef("toggle_theme", "Toggle Theme", "Switch between dark and light themes", "Ctrl+T", ShortcutCategory.VIEW),
    ShortcutDef("cycle_theme", "Cycle Theme", "Cycle through all themes", "Ctrl+Alt+T", ShortcutCategory.VIEW),
    ShortcutDef("toggle_rare_panel", "Toggle Rare Panel", "Show/hide rare evaluation panel", "Ctrl+R", ShortcutCategory.VIEW),

    # Data & Export
    ShortcutDef("export_results", "Export Results", "Export results to TSV file", "Ctrl+E", ShortcutCategory.DATA),
    ShortcutDef("copy_all_tsv", "Copy All as TSV", "Copy all results as TSV", "Ctrl+Shift+C", ShortcutCategory.DATA),
    ShortcutDef("open_log_file", "Open Log File", "Open the application log", "Ctrl+Shift+L", ShortcutCategory.DATA),
    ShortcutDef("open_config_folder", "Open Config", "Open configuration folder", "Ctrl+,", ShortcutCategory.DATA),
    ShortcutDef("show_data_sources", "Data Sources", "Show data source information", "Ctrl+Shift+D", ShortcutCategory.DATA),
]


class ShortcutManager:
    """
    Manages keyboard shortcuts for the application.

    Singleton pattern - use get_shortcut_manager() to get instance.
    """

    _instance: Optional["ShortcutManager"] = None

    def __init__(self):
        self._shortcuts: Dict[str, ShortcutDef] = {}
        self._custom_keys: Dict[str, str] = {}  # action_id -> custom key
        self._callbacks: Dict[str, Callable[[], None]] = {}
        self._qt_shortcuts: Dict[str, QShortcut] = {}
        self._window: Optional[QMainWindow] = None

        # Initialize with defaults
        for shortcut_def in DEFAULT_SHORTCUTS:
            self._shortcuts[shortcut_def.action_id] = shortcut_def

    @classmethod
    def instance(cls) -> "ShortcutManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_window(self, window: QMainWindow) -> None:
        """Set the main window for shortcut registration."""
        self._window = window

    def get_key(self, action_id: str) -> str:
        """Get the current key for an action (custom or default)."""
        if action_id in self._custom_keys:
            return self._custom_keys[action_id]
        if action_id in self._shortcuts:
            return self._shortcuts[action_id].default_key
        return ""

    def set_custom_key(self, action_id: str, key: str) -> None:
        """Set a custom key for an action."""
        self._custom_keys[action_id] = key
        # Re-register if already registered
        if action_id in self._callbacks and self._window:
            self._register_shortcut(action_id)

    def reset_to_default(self, action_id: str) -> None:
        """Reset an action to its default key."""
        if action_id in self._custom_keys:
            del self._custom_keys[action_id]
            if action_id in self._callbacks and self._window:
                self._register_shortcut(action_id)

    def reset_all_to_defaults(self) -> None:
        """Reset all shortcuts to defaults."""
        self._custom_keys.clear()
        # Re-register all
        for action_id in self._callbacks:
            if self._window:
                self._register_shortcut(action_id)

    def register(self, action_id: str, callback: Callable[[], None]) -> None:
        """Register a callback for an action."""
        self._callbacks[action_id] = callback
        if self._window:
            self._register_shortcut(action_id)

    def _register_shortcut(self, action_id: str) -> None:
        """Internal: Register a Qt shortcut for an action."""
        if not self._window:
            return

        # Remove existing shortcut
        if action_id in self._qt_shortcuts:
            old_shortcut = self._qt_shortcuts[action_id]
            old_shortcut.setEnabled(False)
            old_shortcut.deleteLater()

        key = self.get_key(action_id)
        if not key:
            return

        callback = self._callbacks.get(action_id)
        if not callback:
            return

        shortcut = QShortcut(QKeySequence(key), self._window)
        shortcut.activated.connect(callback)
        self._qt_shortcuts[action_id] = shortcut

        logger.debug(f"Registered shortcut: {action_id} -> {key}")

    def register_all(self) -> None:
        """Register all shortcuts that have callbacks."""
        for action_id in self._callbacks:
            self._register_shortcut(action_id)

    def get_shortcut_def(self, action_id: str) -> Optional[ShortcutDef]:
        """Get the shortcut definition for an action."""
        return self._shortcuts.get(action_id)

    def get_all_shortcuts(self) -> List[ShortcutDef]:
        """Get all shortcut definitions."""
        return list(self._shortcuts.values())

    def get_shortcuts_by_category(self) -> Dict[ShortcutCategory, List[ShortcutDef]]:
        """Get shortcuts organized by category."""
        result: Dict[ShortcutCategory, List[ShortcutDef]] = {}
        for shortcut_def in self._shortcuts.values():
            if shortcut_def.category not in result:
                result[shortcut_def.category] = []
            result[shortcut_def.category].append(shortcut_def)
        return result

    def trigger(self, action_id: str) -> bool:
        """Programmatically trigger an action."""
        callback = self._callbacks.get(action_id)
        if callback:
            try:
                callback()
                return True
            except Exception as e:
                logger.exception(f"Error triggering action {action_id}: {e}")
        return False

    def load_from_config(self, config_data: Dict[str, str]) -> None:
        """Load custom shortcuts from config data."""
        self._custom_keys = dict(config_data)
        self.register_all()

    def save_to_config(self) -> Dict[str, str]:
        """Get custom shortcuts for saving to config."""
        return dict(self._custom_keys)

    def get_action_for_palette(self) -> List[Dict]:
        """Get actions formatted for command palette."""
        actions = []
        for shortcut_def in self._shortcuts.values():
            if shortcut_def.action_id in self._callbacks:
                actions.append({
                    "id": shortcut_def.action_id,
                    "name": shortcut_def.name,
                    "description": shortcut_def.description,
                    "shortcut": self.get_key(shortcut_def.action_id),
                    "category": shortcut_def.category.value,
                })
        return actions


def get_shortcut_manager() -> ShortcutManager:
    """Get the global shortcut manager instance."""
    return ShortcutManager.instance()


# Formatted help text generation
def get_shortcuts_help_text() -> str:
    """Generate formatted help text for all shortcuts."""
    manager = get_shortcut_manager()
    shortcuts_by_cat = manager.get_shortcuts_by_category()

    lines = ["Keyboard Shortcuts", "=" * 40, ""]

    for category in ShortcutCategory:
        shortcuts = shortcuts_by_cat.get(category, [])
        if not shortcuts:
            continue

        lines.append(f"[ {category.value} ]")
        lines.append("")

        for shortcut_def in shortcuts:
            key = manager.get_key(shortcut_def.action_id)
            # Pad key to 18 chars for alignment
            key_padded = key.ljust(18)
            lines.append(f"  {key_padded} {shortcut_def.name}")

        lines.append("")

    return "\n".join(lines)
