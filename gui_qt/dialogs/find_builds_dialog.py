"""
Find Builds Dialog - Browse and discover builds from external sources.
"""
from __future__ import annotations

import logging
import webbrowser
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QProgressBar,
    QMessageBox,
)

from gui_qt.styles import COLORS, apply_window_icon

logger = logging.getLogger(__name__)


# Import scrapers
try:
    from data_sources.build_scrapers import (
        PoBArchivesScraper,
        BuildSourceProvider,
        ScrapedBuild,
    )
    SCRAPERS_AVAILABLE = True
except ImportError:
    SCRAPERS_AVAILABLE = False
    PoBArchivesScraper = None  # type: ignore[assignment]
    BuildSourceProvider = None  # type: ignore[assignment]
    ScrapedBuild = None  # type: ignore[assignment]


class ScraperThread(QThread):
    """Background thread for scraping builds."""

    finished = pyqtSignal(list)  # Emits list of ScrapedBuild
    error = pyqtSignal(str)

    def __init__(
        self,
        category: str,
        league: str,
        limit: int = 20,
        parent=None,
    ):
        super().__init__(parent)
        self.category = category
        self.league = league
        self.limit = limit

    def run(self):
        try:
            scraper = PoBArchivesScraper()
            builds = scraper.scrape_builds_by_category(
                category=self.category,
                limit=self.limit,
                league=self.league,
                fetch_pob_codes=False,  # Just get metadata
            )
            self.finished.emit(builds)
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            self.error.emit(str(e))


class FindBuildsDialog(QDialog):
    """
    Dialog for discovering builds from external sources.

    Features:
    - Quick links to popular build sites
    - Scrape builds from pobarchives.com
    - Filter by category (League Starter, SSF, etc.)
    """

    build_selected = pyqtSignal(str)  # Emits build URL

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("Find Starter Builds")
        self.setMinimumSize(600, 500)
        apply_window_icon(self)

        self._builds: List = []
        self._scraper_thread: Optional[ScraperThread] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        layout = QVBoxLayout(self)

        # Quick links section
        quick_links_group = QGroupBox("Quick Links - Browse Build Sites")
        quick_links_layout = QVBoxLayout(quick_links_group)

        # Description
        desc = QLabel(
            "Click a button to open the site in your browser. "
            "Find a build you like and copy the PoB code to import."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']};")
        quick_links_layout.addWidget(desc)

        # Site buttons
        sites_row = QHBoxLayout()

        btn_pobarchives = QPushButton("PoB Archives")
        btn_pobarchives.setToolTip("Community builds with pobb.in links")
        btn_pobarchives.clicked.connect(
            lambda: self._open_url("https://pobarchives.com/builds/poe")
        )
        sites_row.addWidget(btn_pobarchives)

        btn_mobalytics = QPushButton("Mobalytics")
        btn_mobalytics.setToolTip("Curated starter builds with guides")
        btn_mobalytics.clicked.connect(
            lambda: self._open_url("https://mobalytics.gg/poe/starter-builds")
        )
        sites_row.addWidget(btn_mobalytics)

        btn_maxroll = QPushButton("Maxroll.gg")
        btn_maxroll.setToolTip("In-depth build guides")
        btn_maxroll.clicked.connect(
            lambda: self._open_url("https://maxroll.gg/poe/build-guides")
        )
        sites_row.addWidget(btn_maxroll)

        btn_poeninja = QPushButton("poe.ninja")
        btn_poeninja.setToolTip("Ladder character builds")
        btn_poeninja.clicked.connect(
            lambda: self._open_url("https://poe.ninja/builds")
        )
        sites_row.addWidget(btn_poeninja)

        quick_links_layout.addLayout(sites_row)
        layout.addWidget(quick_links_group)

        # Scraper section
        scraper_group = QGroupBox("Search PoB Archives")
        scraper_layout = QVBoxLayout(scraper_group)

        if not SCRAPERS_AVAILABLE:
            no_scraper = QLabel("Build scraper not available")
            no_scraper.setStyleSheet(f"color: {COLORS['corrupted']};")
            scraper_layout.addWidget(no_scraper)
        else:
            # Filter row
            filter_row = QHBoxLayout()

            filter_row.addWidget(QLabel("Category:"))
            self.category_combo = QComboBox()
            self.category_combo.addItem("League Starter", "league_starter")
            self.category_combo.addItem("SSF", "ssf")
            self.category_combo.addItem("Hardcore", "hardcore")
            self.category_combo.addItem("Mapping", "mapping")
            self.category_combo.addItem("Bossing", "bossing")
            self.category_combo.addItem("Budget", "budget")
            filter_row.addWidget(self.category_combo)

            filter_row.addWidget(QLabel("League:"))
            self.league_combo = QComboBox()
            self.league_combo.addItem("3.27 (Keepers)", "poe1_current")
            self.league_combo.addItem("3.26 (Phrecia)", "poe1_3.26")
            self.league_combo.addItem("PoE2 Current", "poe2_current")
            filter_row.addWidget(self.league_combo)

            self.search_btn = QPushButton("Search")
            self.search_btn.clicked.connect(self._on_search)
            filter_row.addWidget(self.search_btn)

            filter_row.addStretch()
            scraper_layout.addLayout(filter_row)

            # Progress bar
            self.progress = QProgressBar()
            self.progress.setVisible(False)
            self.progress.setRange(0, 0)  # Indeterminate
            scraper_layout.addWidget(self.progress)

            # Results list
            self.results_list = QListWidget()
            self.results_list.itemDoubleClicked.connect(self._on_build_double_clicked)
            scraper_layout.addWidget(self.results_list)

            # Result actions
            result_actions = QHBoxLayout()

            self.open_btn = QPushButton("Open in Browser")
            self.open_btn.setEnabled(False)
            self.open_btn.clicked.connect(self._on_open_build)
            result_actions.addWidget(self.open_btn)

            result_count = QLabel("")
            self.result_count_label = result_count
            result_actions.addWidget(result_count)

            result_actions.addStretch()
            scraper_layout.addLayout(result_actions)

        layout.addWidget(scraper_group)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _open_url(self, url: str) -> None:
        """Open URL in default browser."""
        try:
            webbrowser.open(url)
            logger.info(f"Opened browser: {url}")
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open browser:\n{e}"
            )

    def _on_search(self) -> None:
        """Start scraping builds."""
        if self._scraper_thread and self._scraper_thread.isRunning():
            return

        category = self.category_combo.currentData()
        league = self.league_combo.currentData()

        self.search_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.results_list.clear()
        self.result_count_label.setText("Searching...")

        self._scraper_thread = ScraperThread(
            category=category,
            league=league,
            limit=20,
            parent=self,
        )
        self._scraper_thread.finished.connect(self._on_scrape_finished)
        self._scraper_thread.error.connect(self._on_scrape_error)
        self._scraper_thread.start()

    def _on_scrape_finished(self, builds: List) -> None:
        """Handle scraping completion."""
        self.search_btn.setEnabled(True)
        self.progress.setVisible(False)

        self._builds = builds
        self.results_list.clear()

        for build in builds:
            item = QListWidgetItem()
            item.setText(f"{build.build_name}")
            if build.ascendancy:
                item.setToolTip(f"Ascendancy: {build.ascendancy}\nURL: {build.url}")
            else:
                item.setToolTip(f"URL: {build.url}")
            item.setData(Qt.ItemDataRole.UserRole, build.url)
            self.results_list.addItem(item)

        self.result_count_label.setText(f"Found {len(builds)} builds")
        self.open_btn.setEnabled(len(builds) > 0)

        # Auto-select first item
        if builds:
            self.results_list.setCurrentRow(0)

    def _on_scrape_error(self, error_msg: str) -> None:
        """Handle scraping error."""
        self.search_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.result_count_label.setText(f"Error: {error_msg}")

    def _on_build_double_clicked(self, item: QListWidgetItem) -> None:
        """Open build URL on double-click."""
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self._open_url(url)

    def _on_open_build(self) -> None:
        """Open selected build in browser."""
        item = self.results_list.currentItem()
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url:
                self._open_url(url)
