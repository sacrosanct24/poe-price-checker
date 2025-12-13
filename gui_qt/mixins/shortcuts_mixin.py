"""
Shortcuts mixin for keyboard shortcut registration and handling.

Extracts shortcut setup and related helper methods from main_window.py
to reduce coupling and improve maintainability.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui_qt.main_window import PriceCheckerWindow


class ShortcutsMixin:
    """
    Mixin providing keyboard shortcut functionality.

    This mixin expects the following attributes on self:
    - input_text: QPlainTextEdit for item input
    - filter_input: QLineEdit for results filtering
    - rare_eval_panel: QWidget for rare evaluation
    - _theme_controller: ThemeController instance
    - Various action methods like _show_shortcuts, _on_check_price, etc.
    """

    def _setup_shortcuts(self: "PriceCheckerWindow") -> None:
        """Setup keyboard shortcuts using the ShortcutManager."""
        from gui_qt.shortcuts import get_shortcut_manager

        manager = get_shortcut_manager()
        manager.set_window(self)

        # Register all action callbacks
        # General
        manager.register("show_shortcuts", self._show_shortcuts)
        manager.register("show_command_palette", self._show_command_palette)
        manager.register("show_tips", self._show_tips)
        manager.register("exit", lambda: (self.close(), None)[-1])

        # Price Checking
        manager.register("check_price", self._on_check_price)
        manager.register("paste_and_check", self._paste_and_check)
        manager.register("clear_input", self._clear_input)
        manager.register("focus_input", self._focus_input)
        manager.register("focus_filter", self._focus_filter)

        # Build & PoB
        manager.register("show_pob_characters", self._show_pob_characters)
        manager.register("show_bis_search", self._show_bis_search)
        manager.register("show_upgrade_finder", self._show_upgrade_finder)
        manager.register("show_upgrade_advisor", self._show_upgrade_advisor)
        manager.register("show_build_library", self._show_build_library)
        manager.register("show_build_comparison", self._show_build_comparison)
        manager.register("show_item_comparison", self._show_item_comparison)
        manager.register("show_rare_eval_config", self._show_rare_eval_config)

        # Navigation - Screen switching
        manager.register("switch_to_evaluator", self._switch_to_evaluator)
        manager.register("switch_to_advisor", self._switch_to_advisor)
        manager.register("switch_to_daytrader", self._switch_to_daytrader)
        manager.register("show_history", self._show_history)
        manager.register("show_stash_viewer", self._show_stash_viewer)
        manager.register("show_recent_sales", self._show_recent_sales)
        manager.register("show_sales_dashboard", self._show_sales_dashboard)
        manager.register("show_price_rankings", self._show_price_rankings)

        # View & Theme
        manager.register("toggle_theme", self._toggle_theme)
        manager.register("cycle_theme", self._cycle_theme)
        manager.register("toggle_rare_panel", self._toggle_rare_panel)

        # Data & Export
        manager.register("export_results", self._export_results)
        manager.register("copy_all_tsv", self._copy_all_as_tsv)
        manager.register("open_log_file", self._open_log_file)
        manager.register("open_config_folder", self._open_config_folder)
        manager.register("show_data_sources", self._show_data_sources)

        # Register all shortcuts with Qt
        manager.register_all()

    def _focus_input(self: "PriceCheckerWindow") -> None:
        """Focus the item input text area."""
        self.input_text.setFocus()

    def _focus_filter(self: "PriceCheckerWindow") -> None:
        """Focus the results filter input."""
        self.filter_input.setFocus()
        self.filter_input.selectAll()

    def _toggle_rare_panel(self: "PriceCheckerWindow") -> None:
        """Toggle the rare evaluation panel visibility."""
        self.rare_eval_panel.setVisible(not self.rare_eval_panel.isVisible())

    def _cycle_theme(self: "PriceCheckerWindow") -> None:
        """Cycle through all available themes."""
        if self._theme_controller:
            self._theme_controller.cycle_theme(self)

    def _show_command_palette(self: "PriceCheckerWindow") -> None:
        """Show the command palette for quick access to all actions."""
        from gui_qt.dialogs.command_palette import CommandPaletteDialog
        from gui_qt.shortcuts import get_shortcut_manager

        manager = get_shortcut_manager()
        actions = manager.get_action_for_palette()

        dialog = CommandPaletteDialog(
            actions=actions,
            on_action=self._execute_palette_action,
            parent=self,
        )

        # Center dialog over main window
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + 100,
        )

        dialog.exec()

    def _execute_palette_action(self: "PriceCheckerWindow", action_id: str) -> None:
        """Execute an action from the command palette."""
        from gui_qt.shortcuts import get_shortcut_manager

        manager = get_shortcut_manager()
        if not manager.trigger(action_id):
            self._set_status(f"Action not available: {action_id}")
