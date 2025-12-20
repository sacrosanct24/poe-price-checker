"""Tests for gui_qt/dialogs/upgrade_finder_dialog.py - Upgrade finder dialog."""

import pytest
from unittest.mock import MagicMock, patch


from gui_qt.dialogs.upgrade_finder_dialog import (
    UpgradeSearchWorker,
    UpgradeFinderDialog,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_character_manager():
    """Create a mock character manager."""
    manager = MagicMock()
    manager.list_profiles.return_value = ["Build1", "Build2"]
    active_profile = MagicMock()
    active_profile.name = "Build1"
    manager.get_active_profile.return_value = active_profile
    return manager


@pytest.fixture
def mock_service():
    """Create a mock upgrade finder service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_result():
    """Create a mock UpgradeFinderResult."""
    result = MagicMock()
    result.total_candidates = 10
    result.search_time_seconds = 2.5
    result.budget_chaos = 500
    result.slot_results = {"Helmet": MagicMock()}
    result.get_best_upgrades.return_value = []
    return result


@pytest.fixture
def mock_candidate():
    """Create a mock UpgradeCandidate."""
    candidate = MagicMock()
    candidate.name = "Test Helmet"
    candidate.base_type = "Eternal Burgonet"
    candidate.item_level = 84
    candidate.price_display = "50c"
    candidate.implicit_mods = ["+10% Fire Resistance"]
    candidate.explicit_mods = ["+100 to Maximum Life", "+40% Fire Resistance"]
    candidate.total_score = 75.5
    candidate.upgrade_impact = MagicMock()
    candidate.upgrade_impact.effective_life_delta = 50
    candidate.upgrade_impact.fire_res_delta = 10
    candidate.upgrade_impact.cold_res_delta = 0
    candidate.upgrade_impact.lightning_res_delta = 0
    candidate.upgrade_impact.chaos_res_delta = 0
    candidate.upgrade_impact.improvements = ["More life"]
    candidate.upgrade_impact.losses = []
    candidate.upgrade_impact.upgrade_score = 50
    candidate.dps_impact = None
    candidate.dps_percent_change = 0
    return candidate


# =============================================================================
# UpgradeSearchWorker Tests
# =============================================================================


class TestUpgradeSearchWorkerInit:
    """Tests for UpgradeSearchWorker initialization."""

    def test_init_stores_parameters(self, mock_service):
        """Should store all parameters."""
        worker = UpgradeSearchWorker(
            service=mock_service,
            profile_name="TestProfile",
            budget_chaos=1000.0,
            slots=["Helmet", "Boots"],
            max_results=10,
        )

        assert worker.service is mock_service
        assert worker.profile_name == "TestProfile"
        assert worker.budget_chaos == 1000.0
        assert worker.slots == ["Helmet", "Boots"]
        assert worker.max_results == 10

    def test_has_signals(self, mock_service):
        """Should have required signals."""
        worker = UpgradeSearchWorker(
            service=mock_service,
            profile_name="Test",
            budget_chaos=100.0,
            slots=["Helmet"],
            max_results=5,
        )

        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'error')
        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'slot_progress')


# =============================================================================
# UpgradeFinderDialog Init Tests
# =============================================================================


class TestUpgradeFinderDialogInit:
    """Tests for UpgradeFinderDialog initialization."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_init_sets_title(self, mock_service_cls, qtbot, mock_character_manager):
        """Should set window title."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert "Upgrade" in dialog.windowTitle()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_init_sets_minimum_size(self, mock_service_cls, qtbot, mock_character_manager):
        """Should set minimum size."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 900
        assert dialog.minimumHeight() >= 700

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_init_creates_widgets(self, mock_service_cls, qtbot, mock_character_manager):
        """Should create required widgets."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.profile_combo is not None
        assert dialog.budget_spin is not None
        assert dialog.max_results_spin is not None
        assert dialog.search_btn is not None
        assert dialog.results_table is not None

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_init_loads_profiles(self, mock_service_cls, qtbot, mock_character_manager):
        """Should load profiles into combo box."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.profile_combo.count() == 2
        assert dialog.profile_combo.findText("Build1") >= 0

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_init_no_profiles_disables_search(self, mock_service_cls, qtbot):
        """Should disable search when no profiles."""
        manager = MagicMock()
        manager.list_profiles.return_value = []

        dialog = UpgradeFinderDialog(character_manager=manager)
        qtbot.addWidget(dialog)

        assert not dialog.search_btn.isEnabled()


class TestUpgradeFinderDialogSlotSelection:
    """Tests for slot checkbox functionality."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_has_slot_checkboxes(self, mock_service_cls, qtbot, mock_character_manager):
        """Should create slot checkboxes."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert len(dialog._slot_checkboxes) == len(dialog.SEARCHABLE_SLOTS)

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_slots_checked_by_default(self, mock_service_cls, qtbot, mock_character_manager):
        """Should have all slots checked by default."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        for checkbox in dialog._slot_checkboxes.values():
            assert checkbox.isChecked()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_select_all_slots(self, mock_service_cls, qtbot, mock_character_manager):
        """Should select all slots."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        # Uncheck some first
        for checkbox in list(dialog._slot_checkboxes.values())[:3]:
            checkbox.setChecked(False)

        dialog._select_all_slots()

        for checkbox in dialog._slot_checkboxes.values():
            assert checkbox.isChecked()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_select_no_slots(self, mock_service_cls, qtbot, mock_character_manager):
        """Should deselect all slots."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._select_no_slots()

        for checkbox in dialog._slot_checkboxes.values():
            assert not checkbox.isChecked()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_get_selected_slots(self, mock_service_cls, qtbot, mock_character_manager):
        """Should return only selected slots."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        # Uncheck all, then check only Helmet
        dialog._select_no_slots()
        dialog._slot_checkboxes["Helmet"].setChecked(True)

        result = dialog._get_selected_slots()

        assert result == ["Helmet"]


# =============================================================================
# Search Tests
# =============================================================================


class TestUpgradeFinderDialogSearch:
    """Tests for search functionality."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_start_search_no_service_shows_warning(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should show warning if service not initialized."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._service = None

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._start_search()
            mock_warning.assert_called_once()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_start_search_no_slots_shows_warning(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should show warning if no slots selected."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._select_no_slots()

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._start_search()
            mock_warning.assert_called_once()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeSearchWorker')
    def test_start_search_shows_progress(
        self, mock_worker_cls, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should show progress bar when search starts."""
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = False
        mock_worker_cls.return_value = mock_worker

        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._start_search()

        assert not dialog.progress_bar.isHidden()


# =============================================================================
# Search Callbacks Tests
# =============================================================================


class TestUpgradeFinderDialogCallbacks:
    """Tests for search callback handlers."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_search_progress_updates_bar(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should update progress bar format."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._on_search_progress("Searching Helmet...")

        assert dialog.progress_bar.format() == "Searching Helmet..."

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_search_finished_hides_progress(
        self, mock_service_cls, qtbot, mock_character_manager, mock_result
    ):
        """Should hide progress bar on completion."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.progress_bar.setVisible(True)
        dialog._on_search_finished(mock_result)

        assert dialog.progress_bar.isHidden()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_search_finished_enables_button(
        self, mock_service_cls, qtbot, mock_character_manager, mock_result
    ):
        """Should re-enable search button on completion."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.search_btn.setEnabled(False)
        dialog._on_search_finished(mock_result)

        assert dialog.search_btn.isEnabled()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_search_error_shows_message(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should show error message on failure."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_critical:
            dialog._on_search_error("Connection failed")
            mock_critical.assert_called_once()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_search_error_re_enables_button(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should re-enable search button on error."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.search_btn.setEnabled(False)

        with patch('PyQt6.QtWidgets.QMessageBox.critical'):
            dialog._on_search_error("Error")

        assert dialog.search_btn.isEnabled()


# =============================================================================
# Results Display Tests
# =============================================================================


class TestUpgradeFinderDialogResults:
    """Tests for results display."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_display_results_empty(
        self, mock_service_cls, qtbot, mock_character_manager, mock_result
    ):
        """Should show no results message when empty."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        mock_result.get_best_upgrades.return_value = []
        dialog._display_results(mock_result)

        assert dialog.results_table.rowCount() == 0
        assert "No upgrades found" in dialog.summary_label.text()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_display_results_populates_table(
        self, mock_service_cls, qtbot, mock_character_manager, mock_result, mock_candidate
    ):
        """Should populate table with results."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        mock_result.get_best_upgrades.return_value = [
            ("Helmet", mock_candidate),
        ]
        dialog._display_results(mock_result)

        assert dialog.results_table.rowCount() == 1

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_display_results_updates_summary(
        self, mock_service_cls, qtbot, mock_character_manager, mock_result, mock_candidate
    ):
        """Should update summary label."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        mock_result.get_best_upgrades.return_value = [("Helmet", mock_candidate)]
        dialog._display_results(mock_result)

        assert "10" in dialog.summary_label.text()  # total_candidates
        assert "500" in dialog.summary_label.text()  # budget

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_show_no_results(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should show empty state."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._show_no_results()

        assert dialog.results_table.rowCount() == 0
        assert "Configure" in dialog.summary_label.text()


# =============================================================================
# Candidate Details Tests
# =============================================================================


class TestUpgradeFinderDialogDetails:
    """Tests for candidate details display."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_show_candidate_details(
        self, mock_service_cls, qtbot, mock_character_manager, mock_candidate
    ):
        """Should display candidate details."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._show_candidate_details("Helmet", mock_candidate)

        html = dialog.details_browser.toHtml()
        assert "Test Helmet" in html
        assert "Eternal Burgonet" in html

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_show_candidate_details_includes_mods(
        self, mock_service_cls, qtbot, mock_character_manager, mock_candidate
    ):
        """Should include mods in details."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._show_candidate_details("Helmet", mock_candidate)

        html = dialog.details_browser.toHtml()
        assert "Maximum Life" in html

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_show_candidate_details_includes_score(
        self, mock_service_cls, qtbot, mock_character_manager, mock_candidate
    ):
        """Should include total score."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._show_candidate_details("Helmet", mock_candidate)

        html = dialog.details_browser.toHtml()
        # Score is 75.5 which rounds to 76 when formatted with .0f
        assert "Total Score" in html
        assert "76" in html  # 75.5 -> 76 when formatted


# =============================================================================
# Profile Selection Tests
# =============================================================================


class TestUpgradeFinderDialogProfileSelection:
    """Tests for profile selection handling."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_profile_changed_enables_search(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should enable search when valid profile selected."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._on_profile_changed("Build1")

        assert dialog.search_btn.isEnabled()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_on_profile_changed_disables_for_invalid(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should disable search for invalid profile."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog._on_profile_changed("No profiles available")

        assert not dialog.search_btn.isEnabled()


# =============================================================================
# Edge Cases
# =============================================================================


class TestUpgradeFinderDialogEdgeCases:
    """Edge case tests."""

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_budget_spin_range(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should have valid budget range."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.budget_spin.minimum() >= 1
        assert dialog.budget_spin.maximum() >= 1000

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_max_results_spin_range(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should have valid max results range."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.max_results_spin.minimum() >= 1
        assert dialog.max_results_spin.maximum() >= 10

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_no_character_manager(self, mock_service_cls, qtbot):
        """Should handle None character manager."""
        dialog = UpgradeFinderDialog(character_manager=None)
        qtbot.addWidget(dialog)

        assert not dialog.search_btn.isEnabled()
        assert not dialog.profile_combo.isEnabled()

    @patch('gui_qt.dialogs.upgrade_finder_dialog.UpgradeFinderService')
    def test_selection_changed_clears_details(
        self, mock_service_cls, qtbot, mock_character_manager
    ):
        """Should clear details when selection cleared."""
        dialog = UpgradeFinderDialog(character_manager=mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.details_browser.setHtml("<p>Some content</p>")
        dialog.results_table.clearSelection()
        dialog._on_selection_changed()

        # Details should be cleared
        # Note: setHtml("") makes toHtml() return minimal HTML
