"""
gui_qt.main_window

PyQt6 GUI for the PoE Price Checker.

- Paste or type item text into the input box.
- Click "Check Price" (or press Ctrl+Enter) to run a price check.
- View results in the table.
- Right-click a result row to open in browser, copy it, or view details.
- File menu: open log file, open config folder, export TSV, exit.
- View menu: session history, data sources, column visibility, recent sales, sales dashboard.
- Dev menu: paste sample items of various types (map, currency, unique, etc.).
- Help menu: shortcuts, usage tips, about.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QAction, QClipboard, QKeySequence, QShortcut, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QTableView,
    QHeaderView,
    QMenu,
    QMenuBar,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QDialog,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
)

from gui_qt.styles import APP_STYLESHEET, COLORS, get_rarity_color, get_value_color
from gui_qt.widgets.results_table import ResultsTableWidget
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget

if TYPE_CHECKING:
    from core.app_context import AppContext


# Sample items for Dev menu (abbreviated for brevity - full versions below)
SAMPLE_ITEMS: Dict[str, List[str]] = {
    "map": [
        """Rarity: Normal
Cemetery Map
--------
Map Tier: 5
--------
Travel to this Map by using it in a personal Map Device.
""",
    ],
    "currency": [
        """Rarity: Currency
Chaos Orb
--------
Stack Size: 1/10
--------
Reforges a rare item with new random modifiers
""",
        """Rarity: Currency
Divine Orb
--------
Stack Size: 1/10
--------
Randomises the numeric values of the random modifiers on an item
""",
    ],
    "unique": [
        """Rarity: Unique
Tabula Rasa
Simple Robe
--------
Sockets: W-W-W-W-W-W
--------
Item Level: 68
--------
Item has no Level requirement
""",
        """Rarity: Unique
Headhunter
Leather Belt
--------
Requires Level 40
--------
+40 to maximum Life
+50 to Strength
+20% to Fire Resistance
When you Kill a Rare monster, you gain its Modifiers for 20 seconds
""",
    ],
    "rare": [
        """Rarity: Rare
Gale Gyre
Opal Ring
--------
Requires Level 80
--------
Item Level: 84
--------
+29% to Fire and Lightning Resistances
+16% to all Elemental Resistances
+55 to Maximum Life
+38% to Global Critical Strike Multiplier
""",
    ],
    "gem": [
        """Rarity: Gem
Vaal Grace
--------
Level: 21
Quality: +23%
--------
Casts an aura that grants evasion to you and nearby allies.
""",
    ],
    "divination": [
        """Rarity: Divination Card
The Doctor
--------
Stack Size: 1/8
--------
Headhunter
Leather Belt
""",
    ],
}


class PriceCheckWorker(QObject):
    """Worker for running price checks in a background thread."""

    finished = pyqtSignal(object)  # Emits result or exception
    error = pyqtSignal(str)

    def __init__(self, ctx: "AppContext", item_text: str):
        super().__init__()
        self.ctx = ctx
        self.item_text = item_text

    def run(self):
        """Run the price check."""
        try:
            # Parse item
            parsed = self.ctx.parser.parse_item(self.item_text)
            if not parsed:
                self.error.emit("Could not parse item text")
                return

            # Get price
            results = self.ctx.price_service.check_price(parsed)
            self.finished.emit((parsed, results))
        except Exception as e:
            self.error.emit(str(e))


class PriceCheckerWindow(QMainWindow):
    """Main window for the PoE Price Checker application."""

    def __init__(self, ctx: "AppContext", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

        # State
        self._all_results: List[Dict[str, Any]] = []
        self._check_in_progress = False
        self._history: List[Dict[str, Any]] = []

        # Child windows (cached references)
        self._recent_sales_window = None
        self._sales_dashboard_window = None
        self._pob_character_window = None
        self._rare_eval_config_window = None

        # PoB integration
        self._character_manager = None
        self._upgrade_checker = None

        # Rare item evaluator
        self._rare_evaluator = None
        self._init_rare_evaluator()

        # Initialize PoB character manager
        self._init_character_manager()

        # Setup UI
        self.setWindowTitle("PoE Price Checker")
        self.setMinimumSize(1100, 650)
        self.resize(1200, 700)

        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        self._setup_shortcuts()

        # Apply stylesheet
        self.setStyleSheet(APP_STYLESHEET)

        self._set_status("Ready")

    def _init_rare_evaluator(self) -> None:
        """Initialize the rare item evaluator."""
        try:
            from core.rare_item_evaluator import RareItemEvaluator
            data_dir = Path(__file__).parent.parent / "data"
            self._rare_evaluator = RareItemEvaluator(data_dir=data_dir)
        except Exception as e:
            self.logger.warning(f"Failed to initialize rare evaluator: {e}")

    def _init_character_manager(self) -> None:
        """Initialize the PoB character manager."""
        try:
            from core.pob_integration import CharacterManager
            storage_path = Path(__file__).parent.parent / "data" / "characters.json"
            self._character_manager = CharacterManager(storage_path=storage_path)
        except Exception as e:
            self.logger.warning(f"Failed to initialize character manager: {e}")

    # -------------------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_log_action = QAction("Open &Log File", self)
        open_log_action.triggered.connect(self._open_log_file)
        file_menu.addAction(open_log_action)

        open_config_action = QAction("Open &Config Folder", self)
        open_config_action.triggered.connect(self._open_config_folder)
        file_menu.addAction(open_config_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Results (TSV)...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export_results)
        file_menu.addAction(export_action)

        copy_all_action = QAction("Copy &All as TSV", self)
        copy_all_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_all_action.triggered.connect(self._copy_all_as_tsv)
        file_menu.addAction(copy_all_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        history_action = QAction("Session &History", self)
        history_action.triggered.connect(self._show_history)
        view_menu.addAction(history_action)

        sources_action = QAction("Data &Sources", self)
        sources_action.triggered.connect(self._show_data_sources)
        view_menu.addAction(sources_action)

        view_menu.addSeparator()

        recent_sales_action = QAction("&Recent Sales", self)
        recent_sales_action.triggered.connect(self._show_recent_sales)
        view_menu.addAction(recent_sales_action)

        dashboard_action = QAction("Sales &Dashboard", self)
        dashboard_action.triggered.connect(self._show_sales_dashboard)
        view_menu.addAction(dashboard_action)

        view_menu.addSeparator()

        pob_action = QAction("&PoB Characters", self)
        pob_action.triggered.connect(self._show_pob_characters)
        view_menu.addAction(pob_action)

        rare_eval_action = QAction("Rare Item &Settings", self)
        rare_eval_action.triggered.connect(self._show_rare_eval_config)
        view_menu.addAction(rare_eval_action)

        view_menu.addSeparator()

        # Column visibility submenu
        columns_menu = view_menu.addMenu("&Columns")
        self._column_actions: Dict[str, QAction] = {}
        for col in ["item_name", "variant", "links", "chaos_value", "divine_value",
                    "listing_count", "source", "upgrade"]:
            action = QAction(col.replace("_", " ").title(), self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda checked, c=col: self._toggle_column(c, checked))
            columns_menu.addAction(action)
            self._column_actions[col] = action

        # Dev menu
        dev_menu = menubar.addMenu("&Dev")

        paste_menu = dev_menu.addMenu("Paste &Sample")
        for item_type in SAMPLE_ITEMS.keys():
            action = QAction(item_type.title(), self)
            action.triggered.connect(lambda checked, t=item_type: self._paste_sample(t))
            paste_menu.addAction(action)

        dev_menu.addSeparator()

        clear_db_action = QAction("&Wipe Database...", self)
        clear_db_action.triggered.connect(self._wipe_database)
        dev_menu.addAction(clear_db_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        tips_action = QAction("Usage &Tips", self)
        tips_action.triggered.connect(self._show_tips)
        help_menu.addAction(tips_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # -------------------------------------------------------------------------
    # Central Widget
    # -------------------------------------------------------------------------

    def _create_central_widget(self) -> None:
        """Create the main content area."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top area: input + item inspector (horizontal split)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Input area
        input_group = QGroupBox("Item Input")
        input_layout = QVBoxLayout(input_group)

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText(
            "Paste item text here (Ctrl+C from game, then Ctrl+V here)..."
        )
        self.input_text.setMinimumHeight(120)
        input_layout.addWidget(self.input_text)

        # Button row
        btn_layout = QHBoxLayout()

        self.check_btn = QPushButton("Check Price")
        self.check_btn.clicked.connect(self._on_check_price)
        self.check_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.check_btn)

        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)

        top_splitter.addWidget(input_group)

        # Right: Item inspector
        inspector_group = QGroupBox("Item Inspector")
        inspector_layout = QVBoxLayout(inspector_group)
        self.item_inspector = ItemInspectorWidget()
        inspector_layout.addWidget(self.item_inspector)
        top_splitter.addWidget(inspector_group)

        top_splitter.setSizes([500, 300])
        layout.addWidget(top_splitter)

        # Middle: Results area
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type to filter results...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_input)

        filter_layout.addWidget(QLabel("Source:"))
        self.source_filter = QComboBox()
        self.source_filter.addItem("All sources")
        self.source_filter.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.source_filter)

        results_layout.addLayout(filter_layout)

        # Results table
        self.results_table = ResultsTableWidget()
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._show_results_context_menu)
        self.results_table.row_selected.connect(self._on_result_selected)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group, stretch=1)

        # Bottom: Rare evaluation panel (hidden by default)
        self.rare_eval_panel = RareEvaluationPanelWidget()
        self.rare_eval_panel.setVisible(False)
        layout.addWidget(self.rare_eval_panel)

    # -------------------------------------------------------------------------
    # Status Bar
    # -------------------------------------------------------------------------

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Summary label (right side)
        self.summary_label = QLabel()
        self.status_bar.addPermanentWidget(self.summary_label)

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        self.status_bar.showMessage(message)

    def _update_summary(self) -> None:
        """Update the summary label."""
        count = len(self._all_results)
        if count == 0:
            self.summary_label.setText("No results")
        else:
            total_chaos = sum(r.get("chaos_value", 0) or 0 for r in self._all_results)
            self.summary_label.setText(f"{count} items | {total_chaos:.1f}c total")

    # -------------------------------------------------------------------------
    # Shortcuts
    # -------------------------------------------------------------------------

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Ctrl+Enter to check price
        check_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        check_shortcut.activated.connect(self._on_check_price)

        # Escape to clear input
        clear_shortcut = QShortcut(QKeySequence("Escape"), self)
        clear_shortcut.activated.connect(self._clear_input)

        # Ctrl+V to paste and check
        paste_check_shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        paste_check_shortcut.activated.connect(self._paste_and_check)

    # -------------------------------------------------------------------------
    # Price Checking
    # -------------------------------------------------------------------------

    def _on_check_price(self) -> None:
        """Handle Check Price button click."""
        if self._check_in_progress:
            return

        item_text = self.input_text.toPlainText().strip()
        if not item_text:
            self._set_status("No item text to check")
            return

        self._check_in_progress = True
        self.check_btn.setEnabled(False)
        self._set_status("Checking price...")

        # Run price check
        try:
            parsed = self.ctx.parser.parse_item(item_text)
            if not parsed:
                self._set_status("Could not parse item text")
                self._check_in_progress = False
                self.check_btn.setEnabled(True)
                return

            # Update item inspector
            self.item_inspector.set_item(parsed)

            # Get price results
            results = self.ctx.price_service.check_price(parsed)

            # Convert to display format
            self._all_results = []
            for result in results:
                row = {
                    "item_name": result.item_name or parsed.name or "",
                    "variant": result.variant or "",
                    "links": result.links or "",
                    "chaos_value": result.chaos_value or 0,
                    "divine_value": result.divine_value or 0,
                    "listing_count": result.listing_count or 0,
                    "source": result.source or "",
                    "upgrade": "",
                    "price_explanation": json.dumps(result.explanation.__dict__) if result.explanation else "",
                }

                # Check for upgrade potential
                if self._upgrade_checker and hasattr(parsed, 'slot'):
                    is_upgrade = self._upgrade_checker.is_upgrade(parsed)
                    if is_upgrade:
                        row["upgrade"] = "Yes"

                self._all_results.append(row)

            # Update display
            self.results_table.set_data(self._all_results)
            self._update_summary()

            # Update sources filter
            sources = set(r.get("source", "") for r in self._all_results)
            self.source_filter.clear()
            self.source_filter.addItem("All sources")
            for source in sorted(sources):
                if source:
                    self.source_filter.addItem(source)

            # Evaluate rare items
            if parsed.rarity == "Rare" and self._rare_evaluator:
                try:
                    evaluation = self._rare_evaluator.evaluate(parsed)
                    self.rare_eval_panel.set_evaluation(evaluation)
                    self.rare_eval_panel.setVisible(True)
                except Exception as e:
                    self.logger.warning(f"Rare evaluation failed: {e}")
                    self.rare_eval_panel.setVisible(False)
            else:
                self.rare_eval_panel.setVisible(False)

            # Add to history
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "item": parsed.name or item_text[:50],
                "results_count": len(results),
            })

            self._set_status(f"Found {len(results)} price result(s)")

        except Exception as e:
            self.logger.exception("Price check failed")
            self._set_status(f"Error: {e}")
        finally:
            self._check_in_progress = False
            self.check_btn.setEnabled(True)

    def _clear_input(self) -> None:
        """Clear the input text."""
        self.input_text.clear()
        self.item_inspector.clear()

    def _paste_and_check(self) -> None:
        """Paste from clipboard and immediately check price."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.input_text.setPlainText(text)
            self._on_check_price()

    # -------------------------------------------------------------------------
    # Results Filtering
    # -------------------------------------------------------------------------

    def _apply_filter(self) -> None:
        """Apply text and source filters to results."""
        text_filter = self.filter_input.text().lower()
        source_filter = self.source_filter.currentText()

        filtered = []
        for row in self._all_results:
            # Source filter
            if source_filter != "All sources":
                if row.get("source", "") != source_filter:
                    continue

            # Text filter
            if text_filter:
                searchable = " ".join(str(v).lower() for v in row.values())
                if text_filter not in searchable:
                    continue

            filtered.append(row)

        self.results_table.set_data(filtered)

    # -------------------------------------------------------------------------
    # Results Context Menu
    # -------------------------------------------------------------------------

    def _show_results_context_menu(self, pos) -> None:
        """Show context menu for results table."""
        menu = QMenu(self)

        selected = self.results_table.get_selected_row()
        if selected:
            copy_action = menu.addAction("Copy Row")
            copy_action.triggered.connect(self._copy_selected_row)

            copy_tsv_action = menu.addAction("Copy as TSV")
            copy_tsv_action.triggered.connect(self._copy_row_as_tsv)

            menu.addSeparator()

            explain_action = menu.addAction("Why This Price?")
            explain_action.triggered.connect(self._explain_price)

            menu.addSeparator()

            record_sale_action = menu.addAction("Record Sale...")
            record_sale_action.triggered.connect(self._record_sale)

        menu.exec(self.results_table.mapToGlobal(pos))

    def _on_result_selected(self, row_data: Dict[str, Any]) -> None:
        """Handle result row selection."""
        # Could update item inspector or show details
        pass

    def _copy_selected_row(self) -> None:
        """Copy selected row to clipboard."""
        row = self.results_table.get_selected_row()
        if row:
            text = " | ".join(f"{k}: {v}" for k, v in row.items() if k != "price_explanation")
            QApplication.clipboard().setText(text)
            self._set_status("Row copied to clipboard")

    def _copy_row_as_tsv(self) -> None:
        """Copy selected row as TSV."""
        row = self.results_table.get_selected_row()
        if row:
            values = [str(row.get(col, "")) for col in self.results_table.columns
                     if col != "price_explanation"]
            QApplication.clipboard().setText("\t".join(values))
            self._set_status("Row copied as TSV")

    def _explain_price(self) -> None:
        """Show price explanation dialog."""
        row = self.results_table.get_selected_row()
        if not row:
            return

        explanation_json = row.get("price_explanation", "")
        if not explanation_json:
            QMessageBox.information(
                self, "Price Explanation",
                "No detailed explanation available for this price."
            )
            return

        try:
            explanation = json.loads(explanation_json)
            text = f"Source: {explanation.get('source', 'Unknown')}\n"
            text += f"Method: {explanation.get('method', 'Unknown')}\n"
            text += f"Confidence: {explanation.get('confidence', 'Unknown')}\n"
            if explanation.get('notes'):
                text += f"\nNotes: {explanation.get('notes')}"

            QMessageBox.information(self, "Price Explanation", text)
        except json.JSONDecodeError:
            QMessageBox.information(
                self, "Price Explanation",
                "Could not parse price explanation."
            )

    def _record_sale(self) -> None:
        """Record a sale for the selected item."""
        row = self.results_table.get_selected_row()
        if not row:
            return

        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(
            self,
            item_name=row.get("item_name", ""),
            suggested_price=row.get("chaos_value", 0),
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            price, notes = dialog.get_values()
            try:
                self.ctx.db.record_sale(
                    item_name=row.get("item_name", ""),
                    chaos_value=price,
                    source=row.get("source", ""),
                    notes=notes,
                )
                self._set_status(f"Sale recorded: {row.get('item_name', '')} for {price}c")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to record sale: {e}")

    # -------------------------------------------------------------------------
    # Column Visibility
    # -------------------------------------------------------------------------

    def _toggle_column(self, column: str, visible: bool) -> None:
        """Toggle column visibility."""
        self.results_table.set_column_visible(column, visible)

    # -------------------------------------------------------------------------
    # Menu Actions
    # -------------------------------------------------------------------------

    def _open_log_file(self) -> None:
        """Open the log file in the default viewer."""
        log_path = Path(__file__).parent.parent / "logs" / "price_checker.log"
        if log_path.exists():
            os.startfile(str(log_path))
        else:
            QMessageBox.information(self, "Log File", "No log file found.")

    def _open_config_folder(self) -> None:
        """Open the config folder."""
        config_path = Path(__file__).parent.parent / "data"
        if config_path.exists():
            os.startfile(str(config_path))
        else:
            QMessageBox.information(self, "Config Folder", "Config folder not found.")

    def _export_results(self) -> None:
        """Export results to TSV file."""
        if not self._all_results:
            QMessageBox.information(self, "Export", "No results to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "", "TSV Files (*.tsv);;All Files (*)"
        )

        if path:
            try:
                self.results_table.export_tsv(path)
                self._set_status(f"Exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def _copy_all_as_tsv(self) -> None:
        """Copy all results as TSV."""
        tsv = self.results_table.to_tsv(include_header=True)
        QApplication.clipboard().setText(tsv)
        self._set_status("All results copied as TSV")

    def _show_history(self) -> None:
        """Show session history dialog."""
        if not self._history:
            QMessageBox.information(self, "Session History", "No items checked this session.")
            return

        text = "Session History:\n\n"
        for entry in self._history[-20:]:  # Last 20
            text += f"{entry['timestamp']}: {entry['item']} ({entry['results_count']} results)\n"

        QMessageBox.information(self, "Session History", text)

    def _show_data_sources(self) -> None:
        """Show data sources dialog."""
        text = "Data Sources:\n\n"
        text += "- poe.ninja: Real-time economy data\n"
        text += "- poe.watch: Alternative price source\n"
        text += "- Trade API: Official trade site data\n"

        QMessageBox.information(self, "Data Sources", text)

    def _show_recent_sales(self) -> None:
        """Show recent sales window."""
        from gui_qt.windows.recent_sales_window import RecentSalesWindow

        if self._recent_sales_window is None or not self._recent_sales_window.isVisible():
            self._recent_sales_window = RecentSalesWindow(self.ctx, self)

        self._recent_sales_window.show()
        self._recent_sales_window.raise_()

    def _show_sales_dashboard(self) -> None:
        """Show sales dashboard window."""
        from gui_qt.windows.sales_dashboard_window import SalesDashboardWindow

        if self._sales_dashboard_window is None or not self._sales_dashboard_window.isVisible():
            self._sales_dashboard_window = SalesDashboardWindow(self.ctx, self)

        self._sales_dashboard_window.show()
        self._sales_dashboard_window.raise_()

    def _show_pob_characters(self) -> None:
        """Show PoB character manager window."""
        from gui_qt.windows.pob_character_window import PoBCharacterWindow

        if self._character_manager is None:
            QMessageBox.warning(
                self, "PoB Characters",
                "Character manager not initialized."
            )
            return

        if self._pob_character_window is None or not self._pob_character_window.isVisible():
            self._pob_character_window = PoBCharacterWindow(
                self._character_manager,
                self,
                on_profile_selected=self._on_pob_profile_selected,
            )

        self._pob_character_window.show()
        self._pob_character_window.raise_()

    def _on_pob_profile_selected(self, profile_name: str) -> None:
        """Handle PoB profile selection."""
        try:
            from core.pob_integration import UpgradeChecker
            profile = self._character_manager.get_profile(profile_name)
            if profile and profile.build:
                self._upgrade_checker = UpgradeChecker(profile.build)
                self._set_status(f"Upgrade checking enabled for: {profile_name}")
        except Exception as e:
            self.logger.warning(f"Failed to setup upgrade checker: {e}")

    def _show_rare_eval_config(self) -> None:
        """Show rare evaluation config window."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        data_dir = Path(__file__).parent.parent / "data"

        if self._rare_eval_config_window is None or not self._rare_eval_config_window.isVisible():
            self._rare_eval_config_window = RareEvalConfigWindow(
                data_dir,
                self,
                on_save=self._reload_rare_evaluator,
            )

        self._rare_eval_config_window.show()
        self._rare_eval_config_window.raise_()

    def _reload_rare_evaluator(self) -> None:
        """Reload the rare item evaluator."""
        self._init_rare_evaluator()
        self._set_status("Rare evaluation settings reloaded")

    def _paste_sample(self, item_type: str) -> None:
        """Paste a sample item of the given type."""
        samples = SAMPLE_ITEMS.get(item_type, [])
        if samples:
            sample = random.choice(samples)
            self.input_text.setPlainText(sample)
            self._set_status(f"Pasted sample {item_type}")

    def _wipe_database(self) -> None:
        """Wipe the database after confirmation."""
        result = QMessageBox.warning(
            self,
            "Wipe Database",
            "Are you sure you want to delete all recorded sales?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            try:
                self.ctx.db.wipe()
                self._set_status("Database wiped")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to wipe database: {e}")

    def _show_shortcuts(self) -> None:
        """Show keyboard shortcuts."""
        text = """Keyboard Shortcuts:

Ctrl+Enter - Check price
Ctrl+Shift+V - Paste and check
Ctrl+E - Export results
Ctrl+Shift+C - Copy all as TSV
Escape - Clear input
Alt+F4 - Exit
"""
        QMessageBox.information(self, "Keyboard Shortcuts", text)

    def _show_tips(self) -> None:
        """Show usage tips."""
        text = """Usage Tips:

1. Copy items from the game using Ctrl+C while hovering over them.

2. Paste the item text into the input box and click Check Price.

3. Right-click results for more options like recording sales.

4. Use the filter to narrow down results.

5. Import PoB builds to check for upgrade opportunities.

6. Configure rare item evaluation weights for your build.
"""
        QMessageBox.information(self, "Usage Tips", text)

    def _show_about(self) -> None:
        """Show about dialog."""
        text = """PoE Price Checker

A tool for checking Path of Exile item prices.

Uses data from poe.ninja and other sources.

Built with PyQt6.
"""
        QMessageBox.about(self, "About", text)


def run(ctx: "AppContext") -> None:
    """Run the PyQt6 application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Consistent cross-platform look

    window = PriceCheckerWindow(ctx)
    window.show()

    sys.exit(app.exec())
