"""Tests for gui_qt/dialogs/local_builds_dialog.py - Local PoB builds browser."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem

from gui_qt.dialogs.local_builds_dialog import (
    ScanWorker,
    LocalBuildsDialog,
)


# =============================================================================
# ScanWorker Tests
# =============================================================================


class TestScanWorkerInit:
    """Tests for ScanWorker initialization."""

    def test_init_stores_scanner(self):
        """Should store scanner reference."""
        scanner = MagicMock()
        worker = ScanWorker(scanner)
        assert worker._scanner is scanner

    def test_init_default_load_metadata(self):
        """Should default to loading metadata."""
        scanner = MagicMock()
        worker = ScanWorker(scanner)
        assert worker._load_metadata is True

    def test_init_with_load_metadata_false(self):
        """Should allow disabling metadata loading."""
        scanner = MagicMock()
        worker = ScanWorker(scanner, load_metadata=False)
        assert worker._load_metadata is False

    def test_has_signals(self):
        """Should have expected signals."""
        scanner = MagicMock()
        worker = ScanWorker(scanner)
        assert hasattr(worker, 'finished')
        assert hasattr(worker, 'progress')


class TestScanWorkerRun:
    """Tests for ScanWorker.run()."""

    def test_run_emits_progress_on_start(self):
        """Should emit progress when starting scan."""
        scanner = MagicMock()
        scanner.scan_builds.return_value = []
        worker = ScanWorker(scanner, load_metadata=False)

        progress_messages = []
        worker.progress.connect(progress_messages.append)
        worker.run()

        assert len(progress_messages) >= 1
        assert "Scanning" in progress_messages[0]

    def test_run_calls_scan_builds(self):
        """Should call scanner.scan_builds with force_refresh."""
        scanner = MagicMock()
        scanner.scan_builds.return_value = []
        worker = ScanWorker(scanner, load_metadata=False)

        worker.run()

        scanner.scan_builds.assert_called_once_with(force_refresh=True)

    def test_run_emits_finished_with_builds(self):
        """Should emit finished with build list."""
        scanner = MagicMock()
        mock_builds = [MagicMock(), MagicMock()]
        scanner.scan_builds.return_value = mock_builds
        worker = ScanWorker(scanner, load_metadata=False)

        result = []
        worker.finished.connect(result.append)
        worker.run()

        assert len(result) == 1
        assert result[0] == mock_builds

    def test_run_loads_metadata_when_enabled(self):
        """Should load metadata for each build when enabled."""
        scanner = MagicMock()
        build1 = MagicMock()
        build2 = MagicMock()
        scanner.scan_builds.return_value = [build1, build2]
        worker = ScanWorker(scanner, load_metadata=True)

        worker.run()

        assert scanner.load_build_metadata.call_count == 2
        scanner.load_build_metadata.assert_any_call(build1)
        scanner.load_build_metadata.assert_any_call(build2)


# =============================================================================
# LocalBuildsDialog Tests
# =============================================================================


class TestLocalBuildsDialogInit:
    """Tests for LocalBuildsDialog initialization."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_sets_title(self, mock_get_scanner, qtbot):
        """Should set window title."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Import Local PoB Build"

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_sets_minimum_size(self, mock_get_scanner, qtbot):
        """Should set minimum window size."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 800
        assert dialog.minimumHeight() == 500

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_path_label(self, mock_get_scanner, qtbot):
        """Should create path label."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._path_label is not None

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_browse_button(self, mock_get_scanner, qtbot):
        """Should create browse button."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._browse_btn is not None
        assert dialog._browse_btn.text() == "Browse..."

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_refresh_button(self, mock_get_scanner, qtbot):
        """Should create refresh button."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._refresh_btn is not None
        assert dialog._refresh_btn.text() == "Refresh"

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_search_input(self, mock_get_scanner, qtbot):
        """Should create search input field."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._search_input is not None
        assert "Filter" in dialog._search_input.placeholderText()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_table(self, mock_get_scanner, qtbot):
        """Should create builds table with correct columns."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._table is not None
        assert dialog._table.columnCount() == 5

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_import_button_disabled(self, mock_get_scanner, qtbot):
        """Should create disabled import button."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._import_btn is not None
        assert dialog._import_btn.text() == "Import Selected"
        assert not dialog._import_btn.isEnabled()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_cancel_button(self, mock_get_scanner, qtbot):
        """Should create cancel button."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._cancel_btn is not None
        assert dialog._cancel_btn.text() == "Cancel"

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_creates_set_active_checkbox(self, mock_get_scanner, qtbot):
        """Should create set active checkbox, checked by default."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert dialog._set_active_cb is not None
        assert dialog._set_active_cb.isChecked()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_init_progress_bar_hidden(self, mock_get_scanner, qtbot):
        """Should hide progress bar initially."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)
        assert not dialog._progress.isVisible()


class TestLocalBuildsDialogWithScanner:
    """Tests for dialog with valid scanner path."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_shows_path_when_detected(self, mock_get_scanner, qtbot):
        """Should display detected path."""
        mock_scanner = MagicMock()
        mock_scanner.builds_path = Path("C:/Users/Test/PoB/Builds")
        mock_scanner.scan_builds.return_value = []
        mock_get_scanner.return_value = mock_scanner

        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        # Wait for any worker to finish
        if dialog._worker:
            dialog._worker.wait(1000)

        assert "PoB" in dialog._path_label.text() or "Builds" in dialog._path_label.text()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_shows_not_found_message_when_no_path(self, mock_get_scanner, qtbot):
        """Should show not found message when path not detected."""
        mock_scanner = MagicMock()
        mock_scanner.builds_path = None
        mock_get_scanner.return_value = mock_scanner

        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        assert "not found" in dialog._path_label.text().lower() or "Browse" in dialog._path_label.text()


class TestLocalBuildsDialogTablePopulation:
    """Tests for table population."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_populate_table_with_builds(self, mock_get_scanner, qtbot):
        """Should populate table with build info."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        # Create mock builds
        build1 = MagicMock()
        build1.display_name = "My Duelist"
        build1._ascendancy = "Champion"
        build1._class_name = "Duelist"
        build1._level = 95
        build1._main_skill = "Lacerate"
        build1.last_modified = datetime(2025, 1, 15, 10, 30)

        build2 = MagicMock()
        build2.display_name = "Lightning Witch"
        build2._ascendancy = None
        build2._class_name = "Witch"
        build2._level = None
        build2._main_skill = None
        build2.last_modified = datetime(2025, 1, 10, 8, 0)

        dialog._populate_table([build1, build2])

        assert dialog._table.rowCount() == 2

        # Check first row
        assert dialog._table.item(0, 0).text() == "My Duelist"
        assert dialog._table.item(0, 1).text() == "Champion"
        assert dialog._table.item(0, 2).text() == "95"
        assert dialog._table.item(0, 3).text() == "Lacerate"
        assert "2025-01-15" in dialog._table.item(0, 4).text()

        # Check second row with missing data
        assert dialog._table.item(1, 0).text() == "Lightning Witch"
        assert dialog._table.item(1, 1).text() == "Witch"  # Falls back to class_name
        assert dialog._table.item(1, 2).text() == ""  # No level
        assert dialog._table.item(1, 3).text() == ""  # No main skill

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_populate_stores_build_index(self, mock_get_scanner, qtbot):
        """Should store build index in item data."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        build = MagicMock()
        build.display_name = "Test Build"
        build._ascendancy = None
        build._class_name = None
        build._level = None
        build._main_skill = None
        build.last_modified = datetime.now()

        dialog._populate_table([build])

        item = dialog._table.item(0, 0)
        assert item.data(Qt.ItemDataRole.UserRole) == 0


class TestLocalBuildsDialogFilter:
    """Tests for build filtering."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_filter_shows_all_when_empty(self, mock_get_scanner, qtbot):
        """Should show all rows when filter is empty."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        # Add some test data
        build = MagicMock()
        build.display_name = "Test"
        build._ascendancy = None
        build._class_name = None
        build._level = None
        build._main_skill = None
        build.last_modified = datetime.now()
        dialog._populate_table([build, build])

        # Filter then clear
        dialog._filter_builds("xyz")
        dialog._filter_builds("")

        assert not dialog._table.isRowHidden(0)
        assert not dialog._table.isRowHidden(1)

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_filter_hides_non_matching_rows(self, mock_get_scanner, qtbot):
        """Should hide rows that don't match filter."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        build1 = MagicMock()
        build1.display_name = "Champion Build"
        build1._ascendancy = "Champion"
        build1._class_name = None
        build1._level = None
        build1._main_skill = None
        build1.last_modified = datetime.now()

        build2 = MagicMock()
        build2.display_name = "Necromancer Build"
        build2._ascendancy = "Necromancer"
        build2._class_name = None
        build2._level = None
        build2._main_skill = None
        build2.last_modified = datetime.now()

        dialog._populate_table([build1, build2])
        dialog._filter_builds("Champion")

        assert not dialog._table.isRowHidden(0)  # Champion visible
        assert dialog._table.isRowHidden(1)  # Necromancer hidden

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_filter_is_case_insensitive(self, mock_get_scanner, qtbot):
        """Should filter case-insensitively."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        build = MagicMock()
        build.display_name = "CHAMPION BUILD"
        build._ascendancy = None
        build._class_name = None
        build._level = None
        build._main_skill = None
        build.last_modified = datetime.now()

        dialog._populate_table([build])
        dialog._filter_builds("champion")

        assert not dialog._table.isRowHidden(0)


class TestLocalBuildsDialogSelection:
    """Tests for table selection handling."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_selection_enables_import_button(self, mock_get_scanner, qtbot):
        """Should enable import button when row selected."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        build = MagicMock()
        build.display_name = "Test"
        build._ascendancy = None
        build._class_name = None
        build._level = None
        build._main_skill = None
        build.last_modified = datetime.now()
        dialog._populate_table([build])

        assert not dialog._import_btn.isEnabled()

        dialog._table.selectRow(0)

        assert dialog._import_btn.isEnabled()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_clear_selection_disables_import_button(self, mock_get_scanner, qtbot):
        """Should disable import button when selection cleared."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        build = MagicMock()
        build.display_name = "Test"
        build._ascendancy = None
        build._class_name = None
        build._level = None
        build._main_skill = None
        build.last_modified = datetime.now()
        dialog._populate_table([build])

        dialog._table.selectRow(0)
        assert dialog._import_btn.isEnabled()

        dialog._table.clearSelection()
        assert not dialog._import_btn.isEnabled()


class TestLocalBuildsDialogScanProgress:
    """Tests for scan progress handling."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_on_scan_progress_updates_format(self, mock_get_scanner, qtbot):
        """Should update progress bar format."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._on_scan_progress("Loading build 5/10...")

        assert "Loading" in dialog._progress.format() or "5/10" in dialog._progress.format()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_on_scan_finished_hides_progress(self, mock_get_scanner, qtbot):
        """Should hide progress bar on finish."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._progress.show()
        dialog._on_scan_finished([])

        assert not dialog._progress.isVisible()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_on_scan_finished_enables_table(self, mock_get_scanner, qtbot):
        """Should enable table on finish."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._table.setEnabled(False)
        dialog._on_scan_finished([])

        assert dialog._table.isEnabled()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_on_scan_finished_stores_builds(self, mock_get_scanner, qtbot):
        """Should store builds list."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        mock_builds = [MagicMock(), MagicMock()]
        # Set required attributes
        for b in mock_builds:
            b.display_name = "Test"
            b._ascendancy = None
            b._class_name = None
            b._level = None
            b._main_skill = None
            b.last_modified = datetime.now()

        dialog._on_scan_finished(mock_builds)

        assert dialog._builds == mock_builds


class TestLocalBuildsDialogStartScan:
    """Tests for starting a scan."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_start_scan_creates_worker(self, mock_get_scanner, qtbot):
        """Should create a ScanWorker when starting scan."""
        mock_scanner = MagicMock()
        mock_scanner.builds_path = None
        mock_scanner.scan_builds.return_value = []
        mock_get_scanner.return_value = mock_scanner

        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = mock_scanner
        dialog._start_scan()

        # Worker should be created
        assert dialog._worker is not None

        # Wait for worker to finish
        if dialog._worker:
            dialog._worker.wait(2000)

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_start_scan_calls_scanner(self, mock_get_scanner, qtbot):
        """Should call scanner.scan_builds."""
        mock_scanner = MagicMock()
        mock_scanner.builds_path = None
        mock_scanner.scan_builds.return_value = []
        mock_get_scanner.return_value = mock_scanner

        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = mock_scanner
        dialog._start_scan()

        # Wait for worker to finish
        if dialog._worker:
            dialog._worker.wait(2000)

        # Scanner should have been called
        mock_scanner.scan_builds.assert_called()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_start_scan_without_scanner_does_nothing(self, mock_get_scanner, qtbot):
        """Should do nothing if no scanner."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = None
        dialog._start_scan()

        # Should not crash, worker should not be created
        assert dialog._worker is None


class TestLocalBuildsDialogRefresh:
    """Tests for refresh functionality."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_refresh_calls_start_scan(self, mock_get_scanner, qtbot):
        """Should call start_scan when refreshing."""
        mock_scanner = MagicMock()
        mock_scanner.builds_path = None
        mock_get_scanner.return_value = mock_scanner

        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = mock_scanner
        with patch.object(dialog, '_start_scan') as mock_start:
            dialog._refresh_builds()
            mock_start.assert_called_once()

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_refresh_without_scanner_does_nothing(self, mock_get_scanner, qtbot):
        """Should do nothing if no scanner."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = None
        dialog._refresh_builds()  # Should not crash


class TestLocalBuildsDialogCleanup:
    """Tests for dialog cleanup."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_close_stops_worker(self, mock_get_scanner, qtbot):
        """Should stop worker on close."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        dialog._worker = mock_worker

        dialog.close()

        mock_worker.quit.assert_called_once()
        mock_worker.wait.assert_called_once()


class TestLocalBuildsDialogImport:
    """Tests for build import functionality."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_import_selected_does_nothing_without_selection(self, mock_get_scanner, qtbot):
        """Should do nothing if no selection."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._scanner = MagicMock()
        dialog._import_selected()

        # Should not call scanner
        dialog._scanner.import_to_app.assert_not_called()


class TestLocalBuildsDialogSignal:
    """Tests for build_imported signal."""

    @patch('core.pob_local_scanner.get_pob_scanner')
    def test_has_build_imported_signal(self, mock_get_scanner, qtbot):
        """Should have build_imported signal."""
        mock_get_scanner.return_value = MagicMock(builds_path=None)
        dialog = LocalBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'build_imported')
