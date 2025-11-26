"""
Tests for PyQt6 GUI module imports.

These tests verify that all PyQt6 GUI components can be imported successfully.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_pyqt6_available():
    """Test that PyQt6 is installed and importable."""
    import PyQt6
    from PyQt6.QtWidgets import QApplication
    assert QApplication is not None


def test_gui_qt_main_window_imports():
    """Test main window module imports."""
    from gui_qt.main_window import PriceCheckerWindow, run
    assert PriceCheckerWindow is not None
    assert run is not None


def test_gui_qt_styles_imports():
    """Test styles module imports."""
    from gui_qt.styles import APP_STYLESHEET, COLORS, get_rarity_color, get_value_color
    assert APP_STYLESHEET is not None
    assert COLORS is not None
    assert callable(get_rarity_color)
    assert callable(get_value_color)


def test_gui_qt_widgets_imports():
    """Test widget module imports."""
    from gui_qt.widgets import (
        ResultsTableWidget,
        ItemInspectorWidget,
        RareEvaluationPanelWidget,
    )
    assert ResultsTableWidget is not None
    assert ItemInspectorWidget is not None
    assert RareEvaluationPanelWidget is not None


def test_gui_qt_windows_imports():
    """Test window module imports."""
    from gui_qt.windows import (
        RecentSalesWindow,
        SalesDashboardWindow,
        PoBCharacterWindow,
        RareEvalConfigWindow,
        PriceRankingsWindow,
    )
    assert RecentSalesWindow is not None
    assert SalesDashboardWindow is not None
    assert PoBCharacterWindow is not None
    assert RareEvalConfigWindow is not None
    assert PriceRankingsWindow is not None


def test_gui_qt_dialogs_imports():
    """Test dialog module imports."""
    from gui_qt.dialogs import RecordSaleDialog
    assert RecordSaleDialog is not None


def test_color_functions():
    """Test color utility functions."""
    from gui_qt.styles import get_rarity_color, get_value_color, COLORS

    # Rarity colors
    assert get_rarity_color("unique") == COLORS["unique"]
    assert get_rarity_color("rare") == COLORS["rare"]
    assert get_rarity_color("magic") == COLORS["magic"]
    assert get_rarity_color("normal") == COLORS["normal"]
    assert get_rarity_color("unknown") == COLORS["text"]  # Fallback

    # Value colors
    assert get_value_color(100) == COLORS["high_value"]
    assert get_value_color(50) == COLORS["medium_value"]
    assert get_value_color(5) == COLORS["low_value"]
