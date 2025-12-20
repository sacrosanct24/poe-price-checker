"""
Window State Persistence - Save and restore window geometry and state.

Provides utilities for persisting window size, position, splitter positions,
and other UI state across application sessions.

Usage:
    from gui_qt.services.window_state import (
        WindowStateManager,
        save_window_state,
        restore_window_state,
    )

    # Use the manager
    state_mgr = WindowStateManager()

    # Save on close
    state_mgr.save_window(self, "main_window")

    # Restore on show
    state_mgr.restore_window(self, "main_window")

    # Or use convenience functions
    save_window_state(window, "main_window")
    restore_window_state(window, "main_window")
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QMainWindow, QSplitter

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QTableView

logger = logging.getLogger(__name__)


@dataclass
class WindowGeometry:
    """Window geometry state."""
    x: int = 100
    y: int = 100
    width: int = 800
    height: int = 600
    maximized: bool = False
    full_screen: bool = False


@dataclass
class SplitterState:
    """Splitter position state."""
    sizes: List[int] = field(default_factory=list)
    orientation: str = "horizontal"  # or "vertical"


@dataclass
class TableColumnState:
    """Table column configuration."""
    widths: Dict[int, int] = field(default_factory=dict)
    hidden: List[int] = field(default_factory=list)
    order: List[int] = field(default_factory=list)


@dataclass
class WindowState:
    """Complete window state."""
    geometry: WindowGeometry = field(default_factory=WindowGeometry)
    splitters: Dict[str, SplitterState] = field(default_factory=dict)
    tables: Dict[str, TableColumnState] = field(default_factory=dict)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "geometry": asdict(self.geometry),
            "splitters": {k: asdict(v) for k, v in self.splitters.items()},
            "tables": {k: asdict(v) for k, v in self.tables.items()},
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WindowState":
        """Create from dict."""
        state = cls()

        if "geometry" in data:
            state.geometry = WindowGeometry(**data["geometry"])

        if "splitters" in data:
            for key, splitter_data in data["splitters"].items():
                state.splitters[key] = SplitterState(**splitter_data)

        if "tables" in data:
            for key, table_data in data["tables"].items():
                state.tables[key] = TableColumnState(**table_data)

        if "custom" in data:
            state.custom = data["custom"]

        return state


class WindowStateManager:
    """
    Manages window state persistence.

    Saves and restores window geometry, splitter positions,
    table column configurations, and custom state.
    """

    STATE_FILE = "window_state.json"

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            storage_dir: Directory for state storage (default: app config dir)
        """
        if storage_dir is None:
            try:
                from core.config import get_config_dir
                storage_dir = get_config_dir()
            except ImportError:
                storage_dir = Path.home() / ".poe-price-checker"

        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._storage_dir / self.STATE_FILE

        self._states: Dict[str, WindowState] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all saved states from disk."""
        try:
            if self._state_file.exists():
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, state_data in data.items():
                        self._states[key] = WindowState.from_dict(state_data)
                logger.debug(f"Loaded {len(self._states)} window states")
        except Exception as e:
            logger.error(f"Failed to load window states: {e}")

    def _save_all(self) -> None:
        """Save all states to disk."""
        try:
            data = {key: state.to_dict() for key, state in self._states.items()}
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self._states)} window states")
        except Exception as e:
            logger.error(f"Failed to save window states: {e}")

    def get_state(self, key: str) -> WindowState:
        """Get state for a window, creating if needed."""
        if key not in self._states:
            self._states[key] = WindowState()
        return self._states[key]

    def save_window(
        self,
        window: QWidget,
        key: str,
        *,
        splitters: Optional[Dict[str, QSplitter]] = None,
        tables: Optional[Dict[str, "QTableView"]] = None,
        custom: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save window state.

        Args:
            window: Window widget
            key: Unique identifier for this window
            splitters: Optional dict of splitter name -> QSplitter
            tables: Optional dict of table name -> QTableView
            custom: Optional custom state to persist
        """
        state = self.get_state(key)

        # Save geometry
        if isinstance(window, QMainWindow):
            state.geometry.maximized = window.isMaximized()
            state.geometry.full_screen = window.isFullScreen()

        # Get geometry (normal geometry if maximized)
        if isinstance(window, QMainWindow) and window.isMaximized():
            # Use normalGeometry for maximized windows
            geom = window.normalGeometry()
        else:
            geom = window.geometry()

        state.geometry.x = geom.x()
        state.geometry.y = geom.y()
        state.geometry.width = geom.width()
        state.geometry.height = geom.height()

        # Save splitter positions
        if splitters:
            for name, splitter in splitters.items():
                state.splitters[name] = SplitterState(
                    sizes=splitter.sizes(),
                    orientation="vertical" if splitter.orientation() == Qt.Orientation.Vertical else "horizontal",
                )

        # Save table column states
        if tables:
            for name, table in tables.items():
                self._save_table_state(state, name, table)

        # Save custom state
        if custom:
            state.custom.update(custom)

        self._save_all()
        logger.debug(f"Saved state for window: {key}")

    def restore_window(
        self,
        window: QWidget,
        key: str,
        *,
        splitters: Optional[Dict[str, QSplitter]] = None,
        tables: Optional[Dict[str, "QTableView"]] = None,
    ) -> Dict[str, Any]:
        """
        Restore window state.

        Args:
            window: Window widget
            key: Unique identifier for this window
            splitters: Optional dict of splitter name -> QSplitter
            tables: Optional dict of table name -> QTableView

        Returns:
            Custom state dict (empty if none saved)
        """
        if key not in self._states:
            return {}

        state = self._states[key]

        # Restore geometry
        geom = state.geometry

        # Validate geometry is on-screen
        from PyQt6.QtWidgets import QApplication
        screens = QApplication.screens()
        if screens:
            # Get combined screen geometry
            combined = screens[0].availableGeometry()
            for screen in screens[1:]:
                combined = combined.united(screen.availableGeometry())

            # Ensure window is at least partially visible
            if geom.x + geom.width < combined.left() + 50:
                geom.x = combined.left()
            if geom.x > combined.right() - 50:
                geom.x = combined.right() - 200
            if geom.y + geom.height < combined.top() + 50:
                geom.y = combined.top()
            if geom.y > combined.bottom() - 50:
                geom.y = combined.bottom() - 200

        window.setGeometry(geom.x, geom.y, geom.width, geom.height)

        # Restore maximized/fullscreen state
        if isinstance(window, QMainWindow):
            if geom.full_screen:
                window.showFullScreen()
            elif geom.maximized:
                window.showMaximized()

        # Restore splitter positions
        if splitters:
            for name, splitter in splitters.items():
                if name in state.splitters:
                    splitter_state = state.splitters[name]
                    if splitter_state.sizes:
                        splitter.setSizes(splitter_state.sizes)

        # Restore table column states
        if tables:
            for name, table in tables.items():
                if name in state.tables:
                    self._restore_table_state(state.tables[name], table)

        logger.debug(f"Restored state for window: {key}")
        return state.custom.copy()

    def _save_table_state(
        self,
        state: WindowState,
        name: str,
        table: "QTableView",
    ) -> None:
        """Save table column configuration."""
        header = table.horizontalHeader()
        if not header:
            return

        column_state = TableColumnState()

        # Save column widths
        for i in range(header.count()):
            width = header.sectionSize(i)
            if width > 0:
                column_state.widths[i] = width

        # Save hidden columns
        for i in range(header.count()):
            if header.isSectionHidden(i):
                column_state.hidden.append(i)

        # Save column order
        if header.sectionsMovable():
            column_state.order = [
                header.logicalIndex(i) for i in range(header.count())
            ]

        state.tables[name] = column_state

    def _restore_table_state(
        self,
        column_state: TableColumnState,
        table: "QTableView",
    ) -> None:
        """Restore table column configuration."""
        header = table.horizontalHeader()
        if not header:
            return

        # Restore column order first
        if column_state.order and header.sectionsMovable():
            for visual_idx, logical_idx in enumerate(column_state.order):
                if logical_idx < header.count():
                    current_visual = header.visualIndex(logical_idx)
                    if current_visual != visual_idx:
                        header.moveSection(current_visual, visual_idx)

        # Restore column widths
        for col_idx, width in column_state.widths.items():
            if col_idx < header.count():
                header.resizeSection(col_idx, width)

        # Restore hidden columns
        for col_idx in column_state.hidden:
            if col_idx < header.count():
                header.hideSection(col_idx)

    def save_custom(self, key: str, name: str, value: Any) -> None:
        """
        Save a custom value.

        Args:
            key: Window identifier
            name: Custom value name
            value: Value to save (must be JSON serializable)
        """
        state = self.get_state(key)
        state.custom[name] = value
        self._save_all()

    def get_custom(self, key: str, name: str, default: Any = None) -> Any:
        """
        Get a custom value.

        Args:
            key: Window identifier
            name: Custom value name
            default: Default if not found

        Returns:
            Saved value or default
        """
        state = self.get_state(key)
        return state.custom.get(name, default)

    def clear(self, key: str) -> None:
        """Clear state for a window."""
        if key in self._states:
            del self._states[key]
            self._save_all()

    def clear_all(self) -> None:
        """Clear all saved states."""
        self._states.clear()
        try:
            if self._state_file.exists():
                self._state_file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete state file: {e}")


# Global instance
_manager: Optional[WindowStateManager] = None


def get_window_state_manager() -> WindowStateManager:
    """Get the global window state manager."""
    global _manager
    if _manager is None:
        _manager = WindowStateManager()
    return _manager


def save_window_state(
    window: QWidget,
    key: str,
    **kwargs,
) -> None:
    """
    Convenience function to save window state.

    Args:
        window: Window widget
        key: Unique identifier
        **kwargs: Additional arguments for save_window
    """
    get_window_state_manager().save_window(window, key, **kwargs)


def restore_window_state(
    window: QWidget,
    key: str,
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function to restore window state.

    Args:
        window: Window widget
        key: Unique identifier
        **kwargs: Additional arguments for restore_window

    Returns:
        Custom state dict
    """
    return get_window_state_manager().restore_window(window, key, **kwargs)
