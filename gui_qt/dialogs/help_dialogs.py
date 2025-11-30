"""
gui_qt.dialogs.help_dialogs - Help menu dialogs.

Contains dialogs for shortcuts, tips, and about information.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)

from gui_qt.styles import COLORS, get_app_banner_pixmap, apply_window_icon
from gui_qt.shortcuts import get_shortcuts_help_text


def show_shortcuts_dialog(parent: QWidget) -> None:
    """Show keyboard shortcuts in a scrollable dialog."""
    text = get_shortcuts_help_text()

    dialog = QDialog(parent)
    dialog.setWindowTitle("Keyboard Shortcuts")
    dialog.setMinimumSize(450, 500)

    layout = QVBoxLayout(dialog)

    text_widget = QTextEdit()
    text_widget.setReadOnly(True)
    text_widget.setPlainText(text)
    text_widget.setStyleSheet(
        f"background-color: {COLORS['background']}; "
        f"color: {COLORS['text']}; "
        f"font-family: monospace; "
        f"font-size: 12px;"
    )
    layout.addWidget(text_widget)

    # Hint about command palette
    hint_label = QLabel(
        "Tip: Press Ctrl+Shift+P to open Command Palette for quick access to all actions"
    )
    hint_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; padding: 8px;")
    hint_label.setWordWrap(True)
    layout.addWidget(hint_label)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn)

    dialog.exec()


def show_tips_dialog(parent: QWidget) -> None:
    """Show usage tips dialog."""
    from PyQt6.QtWidgets import QMessageBox

    text = """Usage Tips:

1. Copy items from the game using Ctrl+C while hovering over them.

2. Paste the item text into the input box and click Check Price.

3. Right-click results for more options like recording sales.

4. Use the filter to narrow down results.

5. Import PoB builds to check for upgrade opportunities.

6. Configure rare item evaluation weights for your build.
"""
    QMessageBox.information(parent, "Usage Tips", text)


def show_about_dialog(parent: QWidget) -> None:
    """Show about dialog with logo."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("About PoE Price Checker")
    dialog.setFixedSize(400, 400)
    apply_window_icon(dialog)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(16)

    # Logo
    banner = get_app_banner_pixmap(180)
    if banner:
        logo_label = QLabel()
        logo_label.setPixmap(banner)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

    # Title
    title_label = QLabel("<h2 style='color: #3498db;'>PoE Price Checker</h2>")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title_label)

    # Version
    version_label = QLabel("Version 1.0")
    version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    version_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
    layout.addWidget(version_label)

    # Description
    desc_label = QLabel(
        "A tool for checking Path of Exile item prices.\n\n"
        "Features:\n"
        "• Multi-source pricing (poe.ninja, poe.watch, Trade API)\n"
        "• PoB build integration for upgrade checking\n"
        "• BiS item search with affix tier analysis\n"
        "• Rare item evaluation system"
    )
    desc_label.setWordWrap(True)
    desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(desc_label)

    layout.addStretch()

    # Close button
    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn)

    dialog.exec()
