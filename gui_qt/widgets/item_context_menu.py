"""
gui_qt.widgets.item_context_menu

Universal context menu for PoE items across the application.
Provides consistent "Ask AI", "Inspect", "Price Check", and "Copy" actions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMenu, QWidget, QApplication

logger = logging.getLogger(__name__)


@dataclass
class ItemContext:
    """Context data for an item in the context menu.

    Attributes:
        item_name: Display name of the item.
        item_text: Full item text (clipboard format) for price checking.
        chaos_value: Price in chaos orbs (if known).
        divine_value: Price in divine orbs (if known).
        source: Price source (e.g., "poe.ninja", "poeprices").
        parsed_item: Optional ParsedItem object for inspection.
        extra_data: Any additional data needed by callbacks.
    """

    item_name: str
    item_text: str = ""
    chaos_value: float = 0
    divine_value: float = 0
    source: str = ""
    parsed_item: Optional[Any] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    def get_price_results(self) -> List[Dict[str, Any]]:
        """Build price results list for AI analysis."""
        return [{
            "item_name": self.item_name,
            "chaos_value": self.chaos_value,
            "divine_value": self.divine_value,
            "source": self.source,
        }]


class ItemContextMenuManager(QObject):
    """
    Manager for universal item context menus.

    Emits signals for actions that need to be handled by parent widgets.
    Can be configured with callbacks for checking capabilities (e.g., AI configured).

    Signals:
        ai_analysis_requested: Emitted with (item_text, price_results) for AI analysis.
        inspect_requested: Emitted with ItemContext for item inspection.
        price_check_requested: Emitted with item_text for price checking.
        upgrade_analysis_requested: Emitted with (slot, item_text) for upgrade analysis.

    Example:
        menu_manager = ItemContextMenuManager()
        menu_manager.set_ai_configured_callback(lambda: config.has_ai_configured())
        menu_manager.ai_analysis_requested.connect(self._on_ai_analysis)

        # In context menu handler:
        menu_manager.show_menu(position, item_context, parent_widget)
    """

    # Signals for actions
    ai_analysis_requested = pyqtSignal(str, list)  # item_text, price_results
    inspect_requested = pyqtSignal(object)  # ItemContext
    price_check_requested = pyqtSignal(str)  # item_text
    upgrade_analysis_requested = pyqtSignal(str, str)  # slot, item_text

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._ai_configured_callback: Optional[Callable[[], bool]] = None
        self._show_inspect: bool = True
        self._show_price_check: bool = True
        self._show_ai: bool = True
        self._show_copy: bool = True
        self._show_upgrade_analysis: bool = False

    def set_ai_configured_callback(self, callback: Optional[Callable[[], bool]]) -> None:
        """Set callback to check if AI is configured.

        Args:
            callback: Function returning True if AI is ready to use.
        """
        self._ai_configured_callback = callback

    def set_options(
        self,
        show_inspect: bool = True,
        show_price_check: bool = True,
        show_ai: bool = True,
        show_copy: bool = True,
        show_upgrade_analysis: bool = False,
    ) -> None:
        """Configure which menu options to show.

        Args:
            show_inspect: Show "Inspect Item" option.
            show_price_check: Show "Price Check" option.
            show_ai: Show "Ask AI" option.
            show_copy: Show "Copy" submenu.
            show_upgrade_analysis: Show "Analyze Upgrades" option (for PoB equipment).
        """
        self._show_inspect = show_inspect
        self._show_price_check = show_price_check
        self._show_ai = show_ai
        self._show_copy = show_copy
        self._show_upgrade_analysis = show_upgrade_analysis

    def show_menu(
        self,
        global_pos,
        item: ItemContext,
        parent: QWidget,
        slot: str = "",
    ) -> None:
        """Show the context menu at the given position.

        Args:
            global_pos: Global screen position for the menu.
            item: ItemContext with item data.
            parent: Parent widget for the menu.
            slot: Equipment slot name (for upgrade analysis).
        """
        menu = self.build_menu(item, parent, slot=slot)
        menu.exec(global_pos)

    def build_menu(self, item: ItemContext, parent: QWidget, slot: str = "") -> QMenu:
        """Build and return the context menu without showing it.

        Args:
            item: ItemContext with item data.
            parent: Parent widget for the menu.
            slot: Equipment slot name (for upgrade analysis).

        Returns:
            Configured QMenu ready to show.
        """
        menu = QMenu(parent)

        # Inspect Item
        if self._show_inspect:
            inspect_action = menu.addAction("Inspect Item")
            inspect_action.triggered.connect(
                lambda: self.inspect_requested.emit(item)
            )

        # Price Check
        if self._show_price_check and item.item_text:
            price_check_action = menu.addAction("Price Check")
            price_check_action.triggered.connect(
                lambda: self.price_check_requested.emit(item.item_text)
            )

        # Ask AI About This Item
        if self._show_ai:
            ai_configured = (
                self._ai_configured_callback() if self._ai_configured_callback else False
            )
            ai_action = menu.addAction("Ask AI About This Item")
            ai_action.setEnabled(ai_configured)
            if not ai_configured:
                ai_action.setToolTip("Configure AI in Settings > AI")
            ai_action.triggered.connect(
                lambda: self._trigger_ai_analysis(item)
            )

        # Analyze Upgrades (for PoB equipment slots)
        if self._show_upgrade_analysis and slot:
            ai_configured = (
                self._ai_configured_callback() if self._ai_configured_callback else False
            )
            upgrade_action = menu.addAction(f"Analyze Upgrades for {slot}")
            upgrade_action.setEnabled(ai_configured)
            if not ai_configured:
                upgrade_action.setToolTip("Configure AI in Settings > AI")
            # Capture slot in closure
            slot_name = slot
            item_text = item.item_text
            upgrade_action.triggered.connect(
                lambda: self.upgrade_analysis_requested.emit(slot_name, item_text)
            )

        # Add separator before copy actions
        if self._show_copy and (self._show_inspect or self._show_price_check or self._show_ai):
            menu.addSeparator()

        # Copy submenu
        if self._show_copy:
            copy_menu = menu.addMenu("Copy")

            copy_name_action = copy_menu.addAction("Item Name")
            copy_name_action.triggered.connect(
                lambda: self._copy_to_clipboard(item.item_name)
            )

            if item.item_text:
                copy_text_action = copy_menu.addAction("Item Text")
                copy_text_action.triggered.connect(
                    lambda: self._copy_to_clipboard(item.item_text)
                )

            if item.chaos_value:
                copy_price_action = copy_menu.addAction("Price (Chaos)")
                copy_price_action.triggered.connect(
                    lambda: self._copy_to_clipboard(f"{item.chaos_value:.0f}c")
                )

        return menu

    def _trigger_ai_analysis(self, item: ItemContext) -> None:
        """Trigger AI analysis for the item."""
        # Use item_text if available, otherwise use item_name
        text = item.item_text if item.item_text else item.item_name
        price_results = item.get_price_results()
        self.ai_analysis_requested.emit(text, price_results)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            logger.debug(f"Copied to clipboard: {text[:50]}...")


# Module-level convenience instance
_default_manager: Optional[ItemContextMenuManager] = None


def get_item_context_menu_manager() -> ItemContextMenuManager:
    """Get the default shared context menu manager.

    Returns:
        Shared ItemContextMenuManager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = ItemContextMenuManager()
    return _default_manager


def reset_for_testing() -> None:
    """Reset the shared manager for test isolation."""
    global _default_manager
    _default_manager = None
