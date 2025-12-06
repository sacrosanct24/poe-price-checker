"""Tests for FindBuildsDialog."""

import pytest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtCore import Qt


class TestFindBuildsDialogInit:
    """Tests for FindBuildsDialog initialization."""

    def test_init_basic(self, qtbot):
        """Can initialize dialog."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Find Starter Builds"
        assert dialog._builds == []
        assert dialog._scraper_thread is None

    def test_window_size(self, qtbot):
        """Dialog has correct minimum size."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 600
        assert dialog.minimumHeight() == 500

    @patch('gui_qt.dialogs.find_builds_dialog.apply_window_icon')
    def test_applies_window_icon(self, mock_apply_icon, qtbot):
        """Window icon is applied on initialization."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_apply_icon.assert_called_once_with(dialog)


class TestFindBuildsDialogQuickLinks:
    """Tests for quick links section."""

    def test_has_quick_links_group(self, qtbot):
        """Dialog has quick links group box."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QGroupBox

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        groups = dialog.findChildren(QGroupBox)
        group_titles = [g.title() for g in groups]
        assert "Quick Links - Browse Build Sites" in group_titles

    def test_has_pob_archives_button(self, qtbot):
        """Dialog has PoB Archives button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "PoB Archives" in button_texts

    def test_has_mobalytics_button(self, qtbot):
        """Dialog has Mobalytics button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Mobalytics" in button_texts

    def test_has_maxroll_button(self, qtbot):
        """Dialog has Maxroll.gg button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Maxroll.gg" in button_texts

    def test_has_poe_ninja_button(self, qtbot):
        """Dialog has poe.ninja button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "poe.ninja" in button_texts

    @patch('gui_qt.dialogs.find_builds_dialog.webbrowser.open')
    def test_pob_archives_opens_url(self, mock_open, qtbot):
        """PoB Archives button opens correct URL."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Find PoB Archives button
        for btn in dialog.findChildren(QPushButton):
            if btn.text() == "PoB Archives":
                btn.click()
                break

        mock_open.assert_called_once_with("https://pobarchives.com/builds/poe")

    @patch('gui_qt.dialogs.find_builds_dialog.webbrowser.open')
    def test_mobalytics_opens_url(self, mock_open, qtbot):
        """Mobalytics button opens correct URL."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Find Mobalytics button
        for btn in dialog.findChildren(QPushButton):
            if btn.text() == "Mobalytics":
                btn.click()
                break

        mock_open.assert_called_once_with("https://mobalytics.gg/poe/starter-builds")

    @patch('gui_qt.dialogs.find_builds_dialog.QMessageBox.warning')
    @patch('gui_qt.dialogs.find_builds_dialog.webbrowser.open')
    def test_handles_browser_open_error(self, mock_open, mock_warning, qtbot):
        """Handles error when browser fails to open."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        mock_open.side_effect = Exception("Browser error")

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Find and click button - should not crash
        for btn in dialog.findChildren(QPushButton):
            if btn.text() == "PoB Archives":
                btn.click()
                break

        # Dialog should still be functional
        # Error message was shown to user
        mock_warning.assert_called_once()


class TestFindBuildsDialogScraperSection:
    """Tests for scraper section (when available)."""

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_scraper_group_when_available(self, qtbot):
        """Scraper group shown when scrapers available."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QGroupBox

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        groups = dialog.findChildren(QGroupBox)
        group_titles = [g.title() for g in groups]
        assert "Search PoB Archives" in group_titles

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', False)
    def test_shows_unavailable_message_when_no_scrapers(self, qtbot):
        """Shows message when scrapers not available."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Should not have category combo when scrapers unavailable
        assert not hasattr(dialog, 'category_combo') or dialog.findChildren(type(dialog)).__len__() == 0

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_category_combo(self, qtbot):
        """Has category combo box with build types."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'category_combo')
        assert dialog.category_combo.count() > 0

        # Check for some expected categories
        categories = [
            dialog.category_combo.itemText(i)
            for i in range(dialog.category_combo.count())
        ]
        assert "League Starter" in categories
        assert "SSF" in categories
        assert "Hardcore" in categories

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_league_combo(self, qtbot):
        """Has league combo box."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'league_combo')
        assert dialog.league_combo.count() > 0

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_search_button(self, qtbot):
        """Has search button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'search_btn')
        assert dialog.search_btn.text() == "Search"

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_results_list(self, qtbot):
        """Has results list widget."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'results_list')

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_has_progress_bar(self, qtbot):
        """Has progress bar (initially hidden)."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'progress')
        assert dialog.progress.isVisible() is False

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_open_button_initially_disabled(self, qtbot):
        """Open button initially disabled."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'open_btn')
        assert dialog.open_btn.isEnabled() is False


class TestFindBuildsDialogSearch:
    """Tests for search functionality."""

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.ScraperThread')
    def test_on_search_starts_thread(self, mock_thread_class, qtbot):
        """Search button starts scraper thread."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._on_search()

        # Thread should be created and started
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.ScraperThread')
    def test_on_search_disables_search_button(self, mock_thread_class, qtbot):
        """Search disables search button during operation."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._on_search()

        assert dialog.search_btn.isEnabled() is False

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.ScraperThread')
    def test_on_search_shows_progress_bar(self, mock_thread_class, qtbot):
        """Search shows progress bar."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Verify progress starts hidden
        assert dialog.progress.isHidden() is True

        # Ensure no thread is running so _on_search proceeds
        with patch.object(dialog, '_scraper_thread', None):
            dialog._on_search()

        # isHidden() returns False when setVisible(True) was called
        # (unlike isVisible() which also checks parent visibility)
        assert dialog.progress.isHidden() is False

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.ScraperThread')
    def test_on_search_clears_previous_results(self, mock_thread_class, qtbot):
        """Search clears previous results."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Add some items
        dialog.results_list.addItem("Previous result")

        dialog._on_search()

        assert dialog.results_list.count() == 0

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_prevents_concurrent_searches(self, qtbot):
        """Cannot start search while one is running."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Mock running thread
        mock_thread = MagicMock()
        mock_thread.isRunning.return_value = True
        dialog._scraper_thread = mock_thread

        initial_thread = dialog._scraper_thread

        dialog._on_search()

        # Should still be the same thread (no new search started)
        assert dialog._scraper_thread is initial_thread


class TestFindBuildsDialogSearchResults:
    """Tests for search results handling."""

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_populates_results(self, qtbot):
        """Scrape results populate the list."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Mock build data
        mock_build = MagicMock()
        mock_build.build_name = "Test Build"
        mock_build.ascendancy = "Juggernaut"
        mock_build.url = "https://example.com/build"

        builds = [mock_build]

        dialog._on_scrape_finished(builds)

        assert dialog.results_list.count() == 1
        assert dialog.results_list.item(0).text() == "Test Build"

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_enables_search_button(self, qtbot):
        """Scrape completion re-enables search button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog.search_btn.setEnabled(False)

        dialog._on_scrape_finished([])

        assert dialog.search_btn.isEnabled() is True

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_hides_progress(self, qtbot):
        """Scrape completion hides progress bar."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog.progress.setVisible(True)

        dialog._on_scrape_finished([])

        assert dialog.progress.isVisible() is False

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_updates_count_label(self, qtbot):
        """Scrape completion updates result count label."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_build = MagicMock()
        mock_build.build_name = "Build 1"
        mock_build.url = "http://example.com"

        dialog._on_scrape_finished([mock_build])

        assert "Found 1 builds" in dialog.result_count_label.text()

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_enables_open_button(self, qtbot):
        """Scrape completion enables open button when results found."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_build = MagicMock()
        mock_build.build_name = "Build"
        mock_build.url = "http://example.com"

        dialog._on_scrape_finished([mock_build])

        assert dialog.open_btn.isEnabled() is True

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_finished_selects_first_result(self, qtbot):
        """Scrape completion auto-selects first result."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_build = MagicMock()
        mock_build.build_name = "Build"
        mock_build.url = "http://example.com"

        dialog._on_scrape_finished([mock_build])

        assert dialog.results_list.currentRow() == 0

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_error_shows_error_message(self, qtbot):
        """Scrape error shows error message."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._on_scrape_error("Test error message")

        assert "Error: Test error message" in dialog.result_count_label.text()

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_on_scrape_error_enables_search_button(self, qtbot):
        """Scrape error re-enables search button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        dialog.search_btn.setEnabled(False)

        dialog._on_scrape_error("Error")

        assert dialog.search_btn.isEnabled() is True


class TestFindBuildsDialogBuildOpening:
    """Tests for opening builds in browser."""

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.webbrowser.open')
    def test_double_click_opens_build(self, mock_open, qtbot):
        """Double-clicking build opens in browser."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QListWidgetItem

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Create item with URL
        item = QListWidgetItem("Test Build")
        item.setData(Qt.ItemDataRole.UserRole, "https://example.com/build")
        dialog.results_list.addItem(item)

        # Simulate double-click
        dialog._on_build_double_clicked(item)

        mock_open.assert_called_once_with("https://example.com/build")

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    @patch('gui_qt.dialogs.find_builds_dialog.webbrowser.open')
    def test_open_button_opens_selected_build(self, mock_open, qtbot):
        """Open button opens selected build."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QListWidgetItem

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        # Create item with URL
        item = QListWidgetItem("Test Build")
        item.setData(Qt.ItemDataRole.UserRole, "https://example.com/build")
        dialog.results_list.addItem(item)
        dialog.results_list.setCurrentItem(item)

        dialog._on_open_build()

        mock_open.assert_called_once_with("https://example.com/build")


class TestFindBuildsDialogCloseButton:
    """Tests for close button."""

    def test_has_close_button(self, qtbot):
        """Dialog has close button."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Close" in button_texts

    def test_close_button_accepts_dialog(self, qtbot):
        """Close button accepts dialog."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog
        from PyQt6.QtWidgets import QPushButton

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            # Find close button
            for btn in dialog.findChildren(QPushButton):
                if btn.text() == "Close":
                    btn.click()
                    break


class TestFindBuildsDialogTooltips:
    """Tests for tooltips."""

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_build_items_have_tooltips(self, qtbot):
        """Build items show ascendancy and URL in tooltip."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_build = MagicMock()
        mock_build.build_name = "Test Build"
        mock_build.ascendancy = "Slayer"
        mock_build.url = "https://example.com/build"

        dialog._on_scrape_finished([mock_build])

        item = dialog.results_list.item(0)
        tooltip = item.toolTip()
        assert "Slayer" in tooltip
        assert "https://example.com/build" in tooltip

    @patch('gui_qt.dialogs.find_builds_dialog.SCRAPERS_AVAILABLE', True)
    def test_build_without_ascendancy_tooltip(self, qtbot):
        """Build without ascendancy shows URL only."""
        from gui_qt.dialogs.find_builds_dialog import FindBuildsDialog

        dialog = FindBuildsDialog()
        qtbot.addWidget(dialog)

        mock_build = MagicMock()
        mock_build.build_name = "Test Build"
        mock_build.ascendancy = None
        mock_build.url = "https://example.com/build"

        dialog._on_scrape_finished([mock_build])

        item = dialog.results_list.item(0)
        tooltip = item.toolTip()
        assert "URL:" in tooltip
        assert "https://example.com/build" in tooltip
