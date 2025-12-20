# tests/unit/gui_qt/screens/test_ai_advisor_screen.py
"""Tests for AIAdvisorScreen."""

import pytest


from gui_qt.screens.ai_advisor_screen import BuildActionsPanel
from gui_qt.screens.base_screen import BaseScreen


class TestBuildActionsPanel:
    """Tests for BuildActionsPanel widget."""

    @pytest.fixture
    def panel(self, qtbot):
        """Create BuildActionsPanel instance."""
        panel = BuildActionsPanel()
        qtbot.addWidget(panel)
        return panel

    def test_inherits_from_qframe(self, panel):
        """BuildActionsPanel should be a QFrame."""
        from PyQt6.QtWidgets import QFrame
        assert isinstance(panel, QFrame)

    def test_has_compare_button(self, panel):
        """Panel should have Compare Builds button."""
        assert panel._compare_btn is not None
        assert "Compare" in panel._compare_btn.text()

    def test_has_bis_button(self, panel):
        """Panel should have Find BiS button."""
        assert panel._bis_btn is not None
        assert "BiS" in panel._bis_btn.text()

    def test_has_upgrade_button(self, panel):
        """Panel should have Upgrade Finder button."""
        assert panel._upgrade_btn is not None
        assert "Upgrade" in panel._upgrade_btn.text()

    def test_has_item_compare_button(self, panel):
        """Panel should have Compare Items button."""
        assert panel._item_compare_btn is not None
        assert "Compare" in panel._item_compare_btn.text()

    def test_has_library_button(self, panel):
        """Panel should have Build Library button."""
        assert panel._library_btn is not None
        assert "Library" in panel._library_btn.text()

    def test_compare_clicked_signal(self, qtbot, panel):
        """compare_clicked should emit when Compare button clicked."""
        with qtbot.waitSignal(panel.compare_clicked, timeout=1000):
            panel._compare_btn.click()

    def test_bis_clicked_signal(self, qtbot, panel):
        """bis_clicked should emit when BiS button clicked."""
        with qtbot.waitSignal(panel.bis_clicked, timeout=1000):
            panel._bis_btn.click()

    def test_upgrade_finder_clicked_signal(self, qtbot, panel):
        """upgrade_finder_clicked should emit when Upgrade button clicked."""
        with qtbot.waitSignal(panel.upgrade_finder_clicked, timeout=1000):
            panel._upgrade_btn.click()

    def test_item_compare_clicked_signal(self, qtbot, panel):
        """item_compare_clicked should emit when Compare Items button clicked."""
        with qtbot.waitSignal(panel.item_compare_clicked, timeout=1000):
            panel._item_compare_btn.click()

    def test_library_clicked_signal(self, qtbot, panel):
        """library_clicked should emit when Library button clicked."""
        with qtbot.waitSignal(panel.library_clicked, timeout=1000):
            panel._library_btn.click()


class TestAIAdvisorScreenImport:
    """Tests for AIAdvisorScreen class import and structure."""

    def test_can_import_screen(self):
        """AIAdvisorScreen should be importable."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert AIAdvisorScreen is not None

    def test_inherits_from_base_screen(self):
        """AIAdvisorScreen should inherit from BaseScreen."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert issubclass(AIAdvisorScreen, BaseScreen)

    def test_has_required_signals(self):
        """AIAdvisorScreen should define required signals."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        # Check signal attributes exist on class
        assert hasattr(AIAdvisorScreen, 'upgrade_analysis_requested')
        assert hasattr(AIAdvisorScreen, 'compare_builds_requested')
        assert hasattr(AIAdvisorScreen, 'bis_search_requested')
        assert hasattr(AIAdvisorScreen, 'library_requested')
        assert hasattr(AIAdvisorScreen, 'upgrade_finder_requested')
        assert hasattr(AIAdvisorScreen, 'item_compare_requested')
        assert hasattr(AIAdvisorScreen, 'price_check_requested')

    def test_has_screen_name_property(self):
        """AIAdvisorScreen should have screen_name property."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        # Check the property exists
        assert hasattr(AIAdvisorScreen, 'screen_name')


class TestAIAdvisorScreenMethods:
    """Tests for AIAdvisorScreen method signatures."""

    def test_show_analysis_result_method_exists(self):
        """show_analysis_result method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'show_analysis_result')
        assert callable(getattr(AIAdvisorScreen, 'show_analysis_result'))

    def test_show_analysis_error_method_exists(self):
        """show_analysis_error method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'show_analysis_error')
        assert callable(getattr(AIAdvisorScreen, 'show_analysis_error'))

    def test_get_upgrade_advisor_method_exists(self):
        """get_upgrade_advisor method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'get_upgrade_advisor')
        assert callable(getattr(AIAdvisorScreen, 'get_upgrade_advisor'))

    def test_set_character_manager_method_exists(self):
        """set_character_manager method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'set_character_manager')
        assert callable(getattr(AIAdvisorScreen, 'set_character_manager'))

    def test_on_enter_method_exists(self):
        """on_enter method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'on_enter')

    def test_on_leave_method_exists(self):
        """on_leave method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'on_leave')

    def test_refresh_method_exists(self):
        """refresh method should exist."""
        from gui_qt.screens.ai_advisor_screen import AIAdvisorScreen
        assert hasattr(AIAdvisorScreen, 'refresh')
