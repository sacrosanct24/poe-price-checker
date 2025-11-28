"""
Build Filter Widget - Reusable PoE1/PoE2 class/ascendancy filter.

Provides cascading dropdowns:
1. Game Version (PoE1/PoE2)
2. Class (filtered by game version)
3. Ascendancy (filtered by class)
"""
from __future__ import annotations

import logging
from typing import Optional, List, Callable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QLabel,
)

from core.game_data import (
    GameVersion,
    get_classes_for_game,
    get_all_ascendancies,
    ClassInfo,
)

logger = logging.getLogger(__name__)


class BuildFilterWidget(QWidget):
    """
    Reusable widget for filtering builds by PoE version, class, and ascendancy.

    Signals:
        filter_changed: Emitted when any filter value changes
    """

    filter_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        show_labels: bool = True,
        horizontal: bool = True,
        include_all_option: bool = True,
    ):
        """
        Initialize the build filter widget.

        Args:
            parent: Parent widget
            show_labels: Whether to show labels for each dropdown
            horizontal: Lay out horizontally (True) or vertically (False)
            include_all_option: Whether to include "All" option in dropdowns
        """
        super().__init__(parent)

        self._show_labels = show_labels
        self._horizontal = horizontal
        self._include_all = include_all_option
        self._updating = False  # Prevent signal loops

        self._create_widgets()
        self._setup_connections()
        self._populate_game_versions()

    def _create_widgets(self) -> None:
        """Create the dropdown widgets."""
        if self._horizontal:
            layout = QHBoxLayout(self)
        else:
            layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Game version dropdown
        if self._show_labels:
            layout.addWidget(QLabel("Game:"))
        self.game_combo = QComboBox()
        self.game_combo.setMinimumWidth(80)
        layout.addWidget(self.game_combo)

        # Class dropdown
        if self._show_labels:
            layout.addWidget(QLabel("Class:"))
        self.class_combo = QComboBox()
        self.class_combo.setMinimumWidth(100)
        layout.addWidget(self.class_combo)

        # Ascendancy dropdown
        if self._show_labels:
            layout.addWidget(QLabel("Ascendancy:"))
        self.ascendancy_combo = QComboBox()
        self.ascendancy_combo.setMinimumWidth(140)
        layout.addWidget(self.ascendancy_combo)

        # Add stretch if horizontal
        if self._horizontal:
            layout.addStretch()

    def _setup_connections(self) -> None:
        """Connect signals."""
        self.game_combo.currentIndexChanged.connect(self._on_game_changed)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        self.ascendancy_combo.currentIndexChanged.connect(self._on_ascendancy_changed)

    def _populate_game_versions(self) -> None:
        """Populate the game version dropdown."""
        self._updating = True
        self.game_combo.clear()

        if self._include_all:
            self.game_combo.addItem("All Games", None)

        self.game_combo.addItem("PoE 1", GameVersion.POE1)
        self.game_combo.addItem("PoE 2", GameVersion.POE2)

        self._updating = False
        self._on_game_changed()

    def _on_game_changed(self) -> None:
        """Handle game version change - update class dropdown."""
        if self._updating:
            return

        self._updating = True
        self.class_combo.clear()

        game_version = self.game_combo.currentData()

        if self._include_all:
            self.class_combo.addItem("All Classes", None)

        if game_version is None:
            # "All Games" selected - show classes from both
            all_classes = set()
            for gv in [GameVersion.POE1, GameVersion.POE2]:
                all_classes.update(get_classes_for_game(gv).keys())
            for class_name in sorted(all_classes):
                self.class_combo.addItem(class_name, class_name)
        else:
            # Specific game selected
            classes = get_classes_for_game(game_version)
            for class_name in sorted(classes.keys()):
                self.class_combo.addItem(class_name, class_name)

        self._updating = False
        self._on_class_changed()

    def _on_class_changed(self) -> None:
        """Handle class change - update ascendancy dropdown."""
        if self._updating:
            return

        self._updating = True
        self.ascendancy_combo.clear()

        game_version = self.game_combo.currentData()
        class_name = self.class_combo.currentData()

        if self._include_all:
            self.ascendancy_combo.addItem("All Ascendancies", None)

        ascendancies = self._get_ascendancies_for_selection(game_version, class_name)
        for asc_name in sorted(ascendancies):
            self.ascendancy_combo.addItem(asc_name, asc_name)

        self._updating = False
        self._emit_filter_changed()

    def _on_ascendancy_changed(self) -> None:
        """Handle ascendancy change."""
        if self._updating:
            return
        self._emit_filter_changed()

    def _emit_filter_changed(self) -> None:
        """Emit filter_changed signal."""
        self.filter_changed.emit()

    def _get_ascendancies_for_selection(
        self,
        game_version: Optional[GameVersion],
        class_name: Optional[str]
    ) -> List[str]:
        """
        Get list of ascendancies based on current selection.

        Args:
            game_version: Selected game version or None for all
            class_name: Selected class name or None for all

        Returns:
            List of ascendancy names
        """
        ascendancies = []

        games = [game_version] if game_version else [GameVersion.POE1, GameVersion.POE2]

        for gv in games:
            classes = get_classes_for_game(gv)

            if class_name:
                # Specific class selected
                if class_name in classes:
                    class_info = classes[class_name]
                    ascendancies.extend(asc.name for asc in class_info.ascendancies)
            else:
                # All classes
                for class_info in classes.values():
                    ascendancies.extend(asc.name for asc in class_info.ascendancies)

        return list(set(ascendancies))  # Remove duplicates

    # Public API

    def get_game_version(self) -> Optional[GameVersion]:
        """Get selected game version or None for all."""
        return self.game_combo.currentData()

    def get_class_name(self) -> Optional[str]:
        """Get selected class name or None for all."""
        return self.class_combo.currentData()

    def get_ascendancy(self) -> Optional[str]:
        """Get selected ascendancy or None for all."""
        return self.ascendancy_combo.currentData()

    def get_filter(self) -> dict:
        """
        Get current filter as a dictionary.

        Returns:
            Dict with keys: game_version, class_name, ascendancy
            Values are None if "All" is selected
        """
        return {
            "game_version": self.get_game_version(),
            "class_name": self.get_class_name(),
            "ascendancy": self.get_ascendancy(),
        }

    def set_filter(
        self,
        game_version: Optional[GameVersion] = None,
        class_name: Optional[str] = None,
        ascendancy: Optional[str] = None
    ) -> None:
        """
        Set the filter values programmatically.

        Args:
            game_version: Game version to select
            class_name: Class to select
            ascendancy: Ascendancy to select
        """
        self._updating = True

        # Set game version
        for i in range(self.game_combo.count()):
            if self.game_combo.itemData(i) == game_version:
                self.game_combo.setCurrentIndex(i)
                break

        self._updating = False
        self._on_game_changed()

        # Set class
        self._updating = True
        for i in range(self.class_combo.count()):
            if self.class_combo.itemData(i) == class_name:
                self.class_combo.setCurrentIndex(i)
                break

        self._updating = False
        self._on_class_changed()

        # Set ascendancy
        self._updating = True
        for i in range(self.ascendancy_combo.count()):
            if self.ascendancy_combo.itemData(i) == ascendancy:
                self.ascendancy_combo.setCurrentIndex(i)
                break

        self._updating = False
        self._emit_filter_changed()

    def matches_build(
        self,
        build_class: str = "",
        build_ascendancy: str = ""
    ) -> bool:
        """
        Check if a build matches the current filter.

        Args:
            build_class: The build's class name
            build_ascendancy: The build's ascendancy name

        Returns:
            True if the build matches all filter criteria
        """
        filter_data = self.get_filter()

        # Check game version (inferred from class/ascendancy)
        if filter_data["game_version"]:
            from core.game_data import detect_game_version
            build_version = detect_game_version(build_class, build_ascendancy)
            if build_version and build_version != filter_data["game_version"]:
                return False

        # Check class
        if filter_data["class_name"]:
            if build_class.lower() != filter_data["class_name"].lower():
                return False

        # Check ascendancy
        if filter_data["ascendancy"]:
            if build_ascendancy.lower() != filter_data["ascendancy"].lower():
                return False

        return True

    def reset(self) -> None:
        """Reset all filters to "All"."""
        self._updating = True
        self.game_combo.setCurrentIndex(0)
        self._updating = False
        self._on_game_changed()


# Testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout

    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Build Filter Widget Test")
    window.setMinimumSize(500, 200)

    central = QWidget()
    layout = QVBoxLayout(central)

    # Horizontal filter with labels
    filter1 = BuildFilterWidget(show_labels=True, horizontal=True)
    layout.addWidget(QLabel("Horizontal with labels:"))
    layout.addWidget(filter1)

    # Vertical filter without labels
    filter2 = BuildFilterWidget(show_labels=False, horizontal=False)
    layout.addWidget(QLabel("Vertical without labels:"))
    layout.addWidget(filter2)

    # Display filter changes
    result_label = QLabel("Filter: (none)")
    layout.addWidget(result_label)

    def on_filter_changed():
        f = filter1.get_filter()
        text = f"Game: {f['game_version']}, Class: {f['class_name']}, Asc: {f['ascendancy']}"
        result_label.setText(text)

    filter1.filter_changed.connect(on_filter_changed)

    layout.addStretch()

    window.setCentralWidget(central)
    window.show()

    sys.exit(app.exec())
