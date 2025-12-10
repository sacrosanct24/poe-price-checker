"""
gui_qt.controllers.pob_controller - Path of Building integration controller.

Extracts PoB integration logic from main_window.py:
- Character manager initialization
- Build stats management for item inspector
- Profile selection and upgrade checking
- Window focus management for price checks

Usage:
    controller = PoBController(ctx=app_context, logger=logger)
    controller.initialize()
    controller.on_profile_changed("MyBuild")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMainWindow

if TYPE_CHECKING:
    from core.app_context import AppContext
    from core.pob_integration import CharacterManager, UpgradeChecker
    from core.dps_impact_calculator import DPSStats
    from gui_qt.widgets.item_inspector import BuildStats


class PoBController:
    """
    Controller for Path of Building integration.

    Handles:
    - Character manager initialization and storage
    - Build stats synchronization with item inspector
    - Profile selection and upgrade checker setup
    - Window focus management for PoB price checks
    """

    def __init__(
        self,
        ctx: "AppContext",
        logger: Optional[logging.Logger] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the PoB controller.

        Args:
            ctx: Application context.
            logger: Logger instance.
            on_status: Callback to set status bar message.
        """
        self._ctx = ctx
        self._logger = logger or logging.getLogger(__name__)
        self._on_status = on_status

        self._character_manager: Optional["CharacterManager"] = None
        self._upgrade_checker: Optional["UpgradeChecker"] = None

    @property
    def character_manager(self) -> Optional["CharacterManager"]:
        """Get the character manager instance."""
        return self._character_manager

    @property
    def upgrade_checker(self) -> Optional["UpgradeChecker"]:
        """Get the upgrade checker instance."""
        return self._upgrade_checker

    def initialize(self) -> bool:
        """
        Initialize the PoB character manager.

        Returns:
            True if initialization succeeded.
        """
        try:
            from core.pob_integration import CharacterManager

            storage_path = Path(__file__).parent.parent.parent / "data" / "characters.json"
            self._character_manager = CharacterManager(storage_path=storage_path)
            self._logger.info("PoB character manager initialized")
            return True
        except Exception as e:
            self._logger.warning(f"Failed to initialize character manager: {e}")
            return False

    def get_build_stats(self) -> Optional[tuple[Any, Any]]:
        """
        Get build stats and DPS stats from the active profile.

        Returns:
            Tuple of (BuildStats, DPSStats) or None if unavailable.
        """
        if not self._character_manager:
            return None

        try:
            from gui_qt.widgets.item_inspector import BuildStats
            from core.dps_impact_calculator import DPSStats

            profile = self._character_manager.get_active_profile()
            if profile and profile.build and profile.build.stats:
                build_stats = BuildStats.from_pob_stats(profile.build.stats)
                dps_stats = DPSStats.from_pob_stats(profile.build.stats)
                return (build_stats, dps_stats)
        except Exception as e:
            self._logger.warning(f"Failed to get build stats: {e}")

        return None

    def update_inspector_stats(self, item_inspector: Any) -> None:
        """
        Update an item inspector with build stats from the active profile.

        Args:
            item_inspector: ItemInspectorWidget to update.
        """
        if not self._character_manager:
            self._logger.debug("No character manager available")
            return

        try:
            stats = self.get_build_stats()
            if stats:
                build_stats, dps_stats = stats
                item_inspector.set_build_stats(build_stats)
                item_inspector.set_dps_stats(dps_stats)
                self._logger.info(
                    f"Set build stats: life={build_stats.total_life}, "
                    f"life_inc={build_stats.life_inc}%"
                )
                if dps_stats.combined_dps > 0:
                    self._logger.info(
                        f"Set DPS stats: {dps_stats.combined_dps:.0f} DPS, "
                        f"type={dps_stats.primary_damage_type.value}"
                    )
            else:
                item_inspector.set_build_stats(None)
                item_inspector.set_dps_stats(None)
        except Exception as e:
            self._logger.warning(f"Failed to update build stats: {e}")

    def on_profile_selected(
        self,
        profile_name: str,
        price_controller: Any,
    ) -> None:
        """
        Handle PoB profile selection - setup upgrade checker.

        Args:
            profile_name: Name of the selected profile.
            price_controller: PriceCheckController to update.
        """
        try:
            from core.pob_integration import UpgradeChecker

            if not self._character_manager:
                return
            profile = self._character_manager.get_profile(profile_name)
            if profile and profile.build:
                self._upgrade_checker = UpgradeChecker(profile.build)
                price_controller.set_upgrade_checker(self._upgrade_checker)
                if self._on_status:
                    self._on_status(f"Upgrade checking enabled for: {profile_name}")
        except Exception as e:
            self._logger.warning(f"Failed to setup upgrade checker: {e}")

    def on_profile_changed(
        self,
        profile_name: str,
        item_inspector: Any,
    ) -> None:
        """
        Handle PoB profile change - update build stats.

        Args:
            profile_name: Name of the new profile.
            item_inspector: ItemInspectorWidget to update.
        """
        if not profile_name or profile_name.startswith("("):
            # Invalid selection (empty or placeholder like "(No profiles)")
            item_inspector.set_build_stats(None)
            return

        # Set the active profile
        if self._character_manager:
            self._character_manager.set_active_profile(profile_name)

        # Update build stats
        self.update_inspector_stats(item_inspector)

    def handle_pob_price_check(
        self,
        item_text: str,
        input_text_widget: Any,
        main_window: QMainWindow,
        check_callback: Callable[[], None],
    ) -> None:
        """
        Handle price check request from PoB window.

        Args:
            item_text: Item text to check.
            input_text_widget: Input text widget to populate.
            main_window: Main window to bring to front.
            check_callback: Callback to trigger price check.
        """
        # Populate the input text
        input_text_widget.setPlainText(item_text)

        # Bring main window to front
        self.bring_window_to_front(main_window)

        # Auto-run the price check after a brief delay
        QTimer.singleShot(100, check_callback)

    @staticmethod
    def bring_window_to_front(window: QMainWindow) -> None:
        """
        Aggressively bring a window to front on Windows.

        Args:
            window: Window to bring to front.
        """
        # Save current state
        old_state = window.windowState()

        # Method 1: Show normal first
        window.showNormal()

        # Method 2: Temporarily set always on top, then remove it
        window.setWindowFlags(window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        window.show()
        window.setWindowFlags(window.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        window.show()

        # Method 3: Standard Qt activation
        window.raise_()
        window.activateWindow()

        # Method 4: Try Windows API if available
        try:
            import ctypes
            hwnd = int(window.winId())
            # SW_RESTORE = 9, brings window to foreground
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except (AttributeError, OSError):
            # AttributeError: ctypes.windll not available on non-Windows
            # OSError: Windows API call failed
            pass

        # Restore maximized state if needed
        try:
            # Handle both int (from mock) and WindowState (from real Qt)
            maximized_flag = Qt.WindowState.WindowMaximized
            if hasattr(old_state, 'value'):
                is_maximized = old_state.value & maximized_flag.value
            else:
                is_maximized = old_state & maximized_flag.value
            if is_maximized:
                window.showMaximized()
        except (TypeError, AttributeError):
            # Skip if can't determine state
            pass


def get_pob_controller(
    ctx: "AppContext",
    logger: Optional[logging.Logger] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> PoBController:
    """
    Factory function to create a PoBController.

    Args:
        ctx: Application context.
        logger: Logger instance.
        on_status: Status callback.

    Returns:
        Configured PoBController instance.
    """
    return PoBController(
        ctx=ctx,
        logger=logger,
        on_status=on_status,
    )
