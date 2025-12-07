# tests/unit/gui_qt/screens/test_daytrader_screen.py
"""Tests for DaytraderScreen."""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QFrame

from gui_qt.screens.daytrader_screen import (
    QuickStatsPanel,
    QuickActionsPanel,
)
from gui_qt.screens.base_screen import BaseScreen


class TestQuickStatsPanel:
    """Tests for QuickStatsPanel widget."""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context."""
        ctx = MagicMock()
        ctx.db = MagicMock()
        ctx.db.get_total_sales.return_value = 1000
        ctx.db.get_sales_today.return_value = 5
        ctx.db.get_sales_this_week.return_value = 25
        return ctx

    @pytest.fixture
    def panel(self, qtbot, mock_ctx):
        """Create QuickStatsPanel instance."""
        panel = QuickStatsPanel(ctx=mock_ctx)
        qtbot.addWidget(panel)
        return panel

    @pytest.fixture
    def panel_no_ctx(self, qtbot):
        """Create QuickStatsPanel without context."""
        panel = QuickStatsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_inherits_from_qframe(self, panel):
        """QuickStatsPanel should be a QFrame."""
        assert isinstance(panel, QFrame)

    def test_has_revenue_label(self, panel):
        """Panel should have revenue label."""
        assert panel._revenue_label is not None

    def test_has_sold_today_label(self, panel):
        """Panel should have sold today label."""
        assert panel._sold_today_label is not None

    def test_has_sold_week_label(self, panel):
        """Panel should have sold this week label."""
        assert panel._sold_week_label is not None

    def test_refresh_updates_labels(self, panel, mock_ctx):
        """refresh should update labels from database."""
        panel.refresh()
        assert "1,000" in panel._revenue_label.text()
        assert "5" in panel._sold_today_label.text()

    def test_refresh_without_ctx_is_safe(self, panel_no_ctx):
        """refresh without context should not error."""
        panel_no_ctx.refresh()  # Should not raise


class TestQuickActionsPanel:
    """Tests for QuickActionsPanel widget."""

    @pytest.fixture
    def panel(self, qtbot):
        """Create QuickActionsPanel instance."""
        panel = QuickActionsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_inherits_from_qframe(self, panel):
        """QuickActionsPanel should be a QFrame."""
        assert isinstance(panel, QFrame)

    def test_record_sale_clicked_signal(self, qtbot, panel):
        """record_sale_clicked should emit when button clicked."""
        with qtbot.waitSignal(panel.record_sale_clicked, timeout=1000):
            panel.record_sale_clicked.emit()

    def test_snapshot_clicked_signal(self, qtbot, panel):
        """snapshot_clicked should emit when button clicked."""
        with qtbot.waitSignal(panel.snapshot_clicked, timeout=1000):
            panel.snapshot_clicked.emit()

    def test_refresh_stash_clicked_signal(self, qtbot, panel):
        """refresh_stash_clicked should emit when button clicked."""
        with qtbot.waitSignal(panel.refresh_stash_clicked, timeout=1000):
            panel.refresh_stash_clicked.emit()


class TestDaytraderScreenImport:
    """Tests for DaytraderScreen class import and structure."""

    def test_can_import_screen(self):
        """DaytraderScreen should be importable."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert DaytraderScreen is not None

    def test_inherits_from_base_screen(self):
        """DaytraderScreen should inherit from BaseScreen."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert issubclass(DaytraderScreen, BaseScreen)

    def test_has_required_signals(self):
        """DaytraderScreen should define required signals."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, 'record_sale_requested')
        assert hasattr(DaytraderScreen, 'economy_snapshot_requested')
        assert hasattr(DaytraderScreen, 'refresh_stash_requested')

    def test_has_screen_name_property(self):
        """DaytraderScreen should have screen_name property."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, 'screen_name')


class TestDaytraderScreenMethods:
    """Tests for DaytraderScreen method signatures."""

    def test_on_enter_method_exists(self):
        """on_enter method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, 'on_enter')

    def test_on_leave_method_exists(self):
        """on_leave method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, 'on_leave')

    def test_refresh_method_exists(self):
        """refresh method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, 'refresh')

    def test_create_sales_tab_method_exists(self):
        """_create_sales_tab method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, '_create_sales_tab')

    def test_create_loot_tab_method_exists(self):
        """_create_loot_tab method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, '_create_loot_tab')

    def test_create_market_tab_method_exists(self):
        """_create_market_tab method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, '_create_market_tab')

    def test_create_stash_tab_method_exists(self):
        """_create_stash_tab method should exist."""
        from gui_qt.screens.daytrader_screen import DaytraderScreen
        assert hasattr(DaytraderScreen, '_create_stash_tab')
