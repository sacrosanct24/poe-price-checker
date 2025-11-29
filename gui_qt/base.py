"""
gui_qt.base - Base classes and utilities for PyQt6 GUI components.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QWidget,
)

from core.interfaces import IAppContext


class BaseWindow(QMainWindow):
    """Base class for main windows with common functionality."""

    def __init__(
        self,
        ctx: IAppContext,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx

    def center_on_screen(self) -> None:
        """Center the window on the primary screen."""
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            frame_geo = self.frameGeometry()
            frame_geo.moveCenter(screen_geo.center())
            self.move(frame_geo.topLeft())

    def center_on_parent(self) -> None:
        """Center the window over its parent."""
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            parent_geo = parent.geometry()
            self_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - self_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self_geo.height()) // 2
            self.move(x, y)
        else:
            self.center_on_screen()


class BaseDialog(QDialog):
    """Base class for dialog windows with common functionality."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "",
    ) -> None:
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)

        # Standard dialog flags
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )

    def center_on_parent(self) -> None:
        """Center the dialog over its parent."""
        parent = self.parent()
        if parent and isinstance(parent, QWidget):
            parent_geo = parent.geometry()
            self_geo = self.geometry()
            x = parent_geo.x() + (parent_geo.width() - self_geo.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self_geo.height()) // 2
            self.move(x, y)

    def show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an information message box."""
        QMessageBox.information(self, title, message)

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Show a yes/no confirmation dialog."""
        result = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes
