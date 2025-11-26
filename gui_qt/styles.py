"""
gui_qt.styles - Qt Style Sheets and color definitions for PoE Price Checker.

Uses Path of Exile's color scheme for item rarities and values.
"""

# PoE Rarity Colors
COLORS = {
    # Rarity colors
    "unique": "#af6025",      # Unique items (orange-brown)
    "rare": "#ffff77",        # Rare items (yellow)
    "magic": "#8888ff",       # Magic items (blue)
    "normal": "#c8c8c8",      # Normal items (white/gray)
    "currency": "#aa9e82",    # Currency items (tan)
    "gem": "#1ba29b",         # Gems (teal)
    "divination": "#0ebaff",  # Divination cards (light blue)
    "prophecy": "#b54bff",    # Prophecy (purple)

    # Value indicators
    "high_value": "#22dd22",      # High value items (green)
    "medium_value": "#dddd22",    # Medium value items (yellow)
    "low_value": "#888888",       # Low value items (gray)

    # UI colors
    "background": "#1a1a1a",      # Dark background
    "surface": "#2d2d2d",         # Slightly lighter surface
    "border": "#444444",          # Border color
    "text": "#e0e0e0",            # Primary text
    "text_secondary": "#a0a0a0",  # Secondary text
    "accent": "#c8a656",          # PoE gold accent

    # Status colors
    "upgrade": "#44aaff",         # Upgrade indicator (blue)
    "fractured": "#a29162",       # Fractured items
    "synthesised": "#6a1b9a",     # Synthesised items
    "corrupted": "#d20000",       # Corrupted items
}


# Main application stylesheet
APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["background"]};
}}

QWidget {{
    color: {COLORS["text"]};
    font-size: 13px;
}}

QMenuBar {{
    background-color: {COLORS["surface"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

QMenuBar::item {{
    padding: 6px 12px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS["accent"]};
    color: black;
}}

QMenu {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
}}

QMenu::item {{
    padding: 6px 24px;
}}

QMenu::item:selected {{
    background-color: {COLORS["accent"]};
    color: black;
}}

QGroupBox {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px;
    selection-background-color: {COLORS["accent"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS["accent"]};
}}

QPushButton {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 70px;
}}

QPushButton:hover {{
    background-color: #3d3d3d;
    border-color: {COLORS["accent"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["accent"]};
    color: black;
}}

QPushButton:disabled {{
    background-color: #1a1a1a;
    color: #666666;
}}

QComboBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {COLORS["accent"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: black;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
}}

QTableView, QTreeView, QListView {{
    background-color: {COLORS["surface"]};
    alternate-background-color: #252525;
    border: 1px solid {COLORS["border"]};
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: black;
}}

QTableView::item, QTreeView::item, QListView::item {{
    padding: 4px;
}}

QHeaderView::section {{
    background-color: #383838;
    border: none;
    border-right: 1px solid {COLORS["border"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 6px;
    font-weight: bold;
}}

QHeaderView::section:hover {{
    background-color: #454545;
}}

QScrollBar:vertical {{
    background-color: {COLORS["background"]};
    width: 14px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS["border"]};
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #555555;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS["background"]};
    height: 14px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS["border"]};
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #555555;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QStatusBar {{
    background-color: {COLORS["surface"]};
    border-top: 1px solid {COLORS["border"]};
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS["accent"]};
    color: black;
}}

QTabBar::tab:hover:!selected {{
    background-color: #3d3d3d;
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS["border"]};
    border-radius: 3px;
    background-color: {COLORS["surface"]};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
}}

QSlider::groove:horizontal {{
    height: 6px;
    background-color: {COLORS["border"]};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background-color: {COLORS["accent"]};
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: #d8b666;
}}

QProgressBar {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS["accent"]};
    border-radius: 3px;
}}

QToolTip {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    color: {COLORS["text"]};
    padding: 4px;
}}

QSplitter::handle {{
    background-color: {COLORS["border"]};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QLabel {{
    background: transparent;
}}
"""


def get_rarity_color(rarity: str) -> str:
    """Get the color for an item rarity."""
    rarity_lower = rarity.lower()
    return COLORS.get(rarity_lower, COLORS["text"])


def get_value_color(chaos_value: float) -> str:
    """Get the color based on chaos value."""
    if chaos_value >= 100:
        return COLORS["high_value"]
    elif chaos_value >= 10:
        return COLORS["medium_value"]
    else:
        return COLORS["low_value"]
