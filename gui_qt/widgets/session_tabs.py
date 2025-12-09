"""
Session Tabs Widget for multiple price-checking sessions.

Each session maintains its own:
- Item input text
- Results table data
- Item inspector state
- Filter state
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QSplitter,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QMenu,
    QInputDialog,
)

from gui_qt.styles import COLORS
from gui_qt.widgets.results_table import ResultsTableWidget
from gui_qt.widgets.item_inspector import ItemInspectorWidget
from gui_qt.widgets.rare_evaluation_panel import RareEvaluationPanelWidget
from gui_qt.widgets.ai_analysis_panel import AIAnalysisPanelWidget
from gui_qt.widgets.quick_verdict_panel import QuickVerdictPanel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """State for a single price-checking session."""
    name: str
    input_text: str = ""
    results: List[Dict[str, Any]] = field(default_factory=list)
    filter_text: str = ""
    source_filter: str = "All sources"
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()


class SessionPanel(QWidget):
    """A single session panel with input, results, and inspector.

    Signals:
        check_price_requested(item_text: str):
            Emitted when user clicks "Check Price" button or presses Enter.
            The item_text is the raw pasted item text from Path of Exile.

        row_selected(row_data: Dict[str, Any]):
            Emitted when user selects a row in the results table.
            Contains item_name, chaos_value, divine_value, source, and _item (ParsedItem).

        pin_requested(items: List[Dict[str, Any]]):
            Emitted when user requests to pin selected items.
            Each dict contains the full row data for the item.

        compare_requested(items: List[Dict[str, Any]]):
            Emitted when user requests to compare 2-3 selected items.
            Each dict contains the full row data including _item (ParsedItem).
    """

    check_price_requested: pyqtSignal = pyqtSignal(str)
    row_selected: pyqtSignal = pyqtSignal(dict)
    pin_requested: pyqtSignal = pyqtSignal(list)
    compare_requested: pyqtSignal = pyqtSignal(list)
    ai_analysis_requested: pyqtSignal = pyqtSignal(str, list)  # item_text, price_results
    update_meta_requested: pyqtSignal = pyqtSignal()  # Meta weights update request

    def __init__(self, session_name: str = "Session 1", parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.session_name = session_name
        self._all_results: List[Dict[str, Any]] = []

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the session panel widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Top area: input + item inspector (horizontal split)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Input area
        input_group = QGroupBox("Item Input")
        input_layout = QVBoxLayout(input_group)

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText(
            "Paste item text here (Ctrl+C from game, then Ctrl+V here)...\n\n"
            "Or select an item from PoB Equipment panel on the left."
        )
        self.input_text.setMinimumHeight(100)
        input_layout.addWidget(self.input_text)

        # Button row
        btn_layout = QHBoxLayout()

        self.check_btn = QPushButton("Check Price")
        self.check_btn.clicked.connect(self._on_check_price)
        self.check_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.check_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)

        top_splitter.addWidget(input_group)

        # Right: Item inspector
        inspector_group = QGroupBox("Item Inspector")
        inspector_layout = QVBoxLayout(inspector_group)
        self.item_inspector = ItemInspectorWidget()
        inspector_layout.addWidget(self.item_inspector)
        top_splitter.addWidget(inspector_group)

        # Give Item Inspector more space
        top_splitter.setSizes([300, 500])
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
        self.results_table.row_selected.connect(self._on_row_selected)
        self.results_table.pin_requested.connect(lambda items: self.pin_requested.emit(items))
        self.results_table.compare_requested.connect(lambda items: self.compare_requested.emit(items))
        self.results_table.ai_analysis_requested.connect(self.ai_analysis_requested.emit)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group, stretch=1)

        # Bottom: Rare evaluation panel (hidden by default)
        self.rare_eval_panel = RareEvaluationPanelWidget()
        self.rare_eval_panel.setVisible(False)
        layout.addWidget(self.rare_eval_panel)

        # Forward the update_meta_requested signal
        self.rare_eval_panel.update_meta_requested.connect(self._on_update_meta_requested)

        # Bottom: Quick verdict panel (casual player summary)
        self.quick_verdict_panel = QuickVerdictPanel()
        self.quick_verdict_panel.setVisible(False)
        layout.addWidget(self.quick_verdict_panel)

        # Bottom: AI analysis panel (hidden by default)
        self.ai_panel = AIAnalysisPanelWidget()
        self.ai_panel.setVisible(False)
        layout.addWidget(self.ai_panel)

    def _on_check_price(self) -> None:
        """Handle check price button click."""
        text = self.input_text.toPlainText().strip()
        if text:
            self.check_price_requested.emit(text)

    def _on_clear(self) -> None:
        """Clear the input and results."""
        self.input_text.clear()
        self._all_results = []
        self.results_table.set_data([])
        self.item_inspector.clear()
        self.rare_eval_panel.setVisible(False)
        self.quick_verdict_panel.clear()
        self.quick_verdict_panel.setVisible(False)
        self.ai_panel.clear()
        self.ai_panel.setVisible(False)

    def _on_update_meta_requested(self) -> None:
        """Forward update meta request to parent."""
        self.update_meta_requested.emit()

    def set_rare_evaluator(self, evaluator: Any) -> None:
        """Set the rare item evaluator for meta info display."""
        self.rare_eval_panel.set_evaluator(evaluator)

    def _on_row_selected(self, row_data: Dict[str, Any]) -> None:
        """Handle row selection in results table."""
        self.row_selected.emit(row_data)
        # Update item inspector
        if row_data:
            self.item_inspector.set_item(row_data)

    def _apply_filter(self) -> None:
        """Apply text and source filters to results."""
        filter_text = self.filter_input.text().lower()
        source = self.source_filter.currentText()

        filtered = []
        for row in self._all_results:
            # Text filter
            if filter_text:
                name = str(row.get("item_name", "")).lower()
                if filter_text not in name:
                    continue

            # Source filter
            if source != "All sources":
                if row.get("source", "") != source:
                    continue

            filtered.append(row)

        self.results_table.set_data(filtered, calculate_trends=False)

    def set_results(self, results: List[Dict[str, Any]]) -> None:
        """Set the results for this session."""
        self._all_results = results

        # Update source filter options
        sources = set()
        for r in results:
            src = r.get("source", "")
            if src:
                sources.add(src)

        current = self.source_filter.currentText()
        self.source_filter.clear()
        self.source_filter.addItem("All sources")
        for src in sorted(sources):
            self.source_filter.addItem(src)

        # Restore selection if still valid
        idx = self.source_filter.findText(current)
        if idx >= 0:
            self.source_filter.setCurrentIndex(idx)

        self._apply_filter()

    def get_state(self) -> SessionState:
        """Get the current state of this session."""
        return SessionState(
            name=self.session_name,
            input_text=self.input_text.toPlainText(),
            results=self._all_results.copy(),
            filter_text=self.filter_input.text(),
            source_filter=self.source_filter.currentText(),
        )

    def restore_state(self, state: SessionState) -> None:
        """Restore session state."""
        self.session_name = state.name
        self.input_text.setPlainText(state.input_text)
        self._all_results = state.results.copy()
        self.filter_input.setText(state.filter_text)

        # Restore source filter after setting results
        self.set_results(self._all_results)
        idx = self.source_filter.findText(state.source_filter)
        if idx >= 0:
            self.source_filter.setCurrentIndex(idx)


class SessionTabWidget(QTabWidget):
    """Tab widget for managing multiple price-checking sessions.

    Supports up to MAX_SESSIONS concurrent sessions with add/close/rename.
    Each session maintains independent state (input, results, filters).

    Signals:
        check_price_requested(item_text: str, session_index: int):
            Emitted when a session requests a price check.
            item_text: The raw item text to price check.
            session_index: Index of the requesting session tab.

        row_selected(row_data: Dict[str, Any]):
            Emitted when user selects a result row in any session.
            Forwarded from the active SessionPanel.

        pin_requested(items: List[Dict[str, Any]]):
            Emitted when user requests to pin items from any session.
            Forwarded from the active SessionPanel.

        compare_requested(items: List[Dict[str, Any]]):
            Emitted when user requests to compare items from any session.
            Forwarded from the active SessionPanel.

        update_meta_requested():
            Emitted when user requests to update meta weights.
            Forwarded from the active SessionPanel's rare evaluation panel.
    """

    MAX_SESSIONS = 10

    check_price_requested: pyqtSignal = pyqtSignal(str, int)
    row_selected: pyqtSignal = pyqtSignal(dict)
    pin_requested: pyqtSignal = pyqtSignal(list)
    compare_requested: pyqtSignal = pyqtSignal(list)
    ai_analysis_requested: pyqtSignal = pyqtSignal(str, list)  # item_text, price_results
    update_meta_requested: pyqtSignal = pyqtSignal()  # Meta weights update request

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._session_counter = 0
        self._rare_evaluator = None  # Reference to rare evaluator for panels

        # Enable close buttons and movable tabs
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self._on_tab_close_requested)

        # Add "+" button for new tab
        self.setCornerWidget(self._create_add_button(), Qt.Corner.TopRightCorner)

        # Context menu for tabs
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)

        # Create initial session
        self._add_session()

    def _create_add_button(self) -> QPushButton:
        """Create the add session button."""
        btn = QPushButton("+")
        btn.setFixedSize(24, 24)
        btn.setToolTip("New Session (Ctrl+T)")
        btn.clicked.connect(self._add_session)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["surface_hover"]};
            }}
        """)
        return btn

    def _on_tab_close_requested(self, index: int) -> None:
        """Handle tab close request."""
        if self.count() <= 1:
            # Don't close the last tab, just clear it
            panel = self.widget(0)
            if isinstance(panel, SessionPanel):
                panel._on_clear()
            return

        self.removeTab(index)

    def _show_tab_context_menu(self, pos) -> None:
        """Show context menu for tab."""
        tab_bar = self.tabBar()
        index = tab_bar.tabAt(pos)

        if index < 0:
            return

        menu = QMenu(self)

        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self._rename_tab(index))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self._duplicate_tab(index))

        menu.addSeparator()

        close_action = menu.addAction("Close")
        close_action.triggered.connect(lambda: self._on_tab_close_requested(index))
        close_action.setEnabled(self.count() > 1)

        close_others_action = menu.addAction("Close Others")
        close_others_action.triggered.connect(lambda: self._close_other_tabs(index))
        close_others_action.setEnabled(self.count() > 1)

        menu.exec(tab_bar.mapToGlobal(pos))

    def _rename_tab(self, index: int) -> None:
        """Rename a tab."""
        current_name = self.tabText(index)
        new_name, ok = QInputDialog.getText(
            self, "Rename Session", "Session name:", text=current_name
        )
        if ok and new_name:
            self.setTabText(index, new_name)
            panel = self.widget(index)
            if isinstance(panel, SessionPanel):
                panel.session_name = new_name

    def _duplicate_tab(self, index: int) -> None:
        """Duplicate a tab."""
        source_panel = self.widget(index)
        if not isinstance(source_panel, SessionPanel):
            return

        state = source_panel.get_state()
        state.name = f"{state.name} (copy)"

        new_panel = self._add_session(state.name)
        if new_panel:
            new_panel.restore_state(state)

    def _close_other_tabs(self, keep_index: int) -> None:
        """Close all tabs except the specified one."""
        # Remove tabs from end to start to avoid index shifting issues
        for i in range(self.count() - 1, -1, -1):
            if i != keep_index:
                self.removeTab(i)

    def get_current_panel(self) -> Optional[SessionPanel]:
        """Get the currently active session panel."""
        widget = self.currentWidget()
        if isinstance(widget, SessionPanel):
            return widget
        return None

    def get_panel(self, index: int) -> Optional[SessionPanel]:
        """Get session panel at index."""
        widget = self.widget(index)
        if isinstance(widget, SessionPanel):
            return widget
        return None

    def set_results_for_session(self, index: int, results: List[Dict[str, Any]]) -> None:
        """Set results for a specific session."""
        panel = self.get_panel(index)
        if panel:
            panel.set_results(results)

    def set_ai_configured_callback(self, callback: Optional[callable]) -> None:
        """Set the AI configured callback on all session panels' results tables.

        Args:
            callback: Function that returns True if AI is configured.
        """
        for i in range(self.count()):
            panel = self.get_panel(i)
            if panel:
                panel.results_table.set_ai_configured_callback(callback)
        # Store for future sessions
        self._ai_configured_callback = callback

    def _add_session(self, name: Optional[str] = None) -> SessionPanel:
        """Add a new session tab."""
        if self.count() >= self.MAX_SESSIONS:
            logger.warning(f"Maximum sessions ({self.MAX_SESSIONS}) reached")
            return None

        self._session_counter += 1
        session_name = name or f"Session {self._session_counter}"

        panel = SessionPanel(session_name)
        panel.check_price_requested.connect(
            lambda text, idx=self.count(): self.check_price_requested.emit(text, idx)
        )
        panel.row_selected.connect(self.row_selected.emit)
        panel.pin_requested.connect(self.pin_requested.emit)
        panel.compare_requested.connect(self.compare_requested.emit)
        panel.ai_analysis_requested.connect(self.ai_analysis_requested.emit)
        panel.update_meta_requested.connect(self.update_meta_requested.emit)

        # Set rare evaluator if we have one
        if self._rare_evaluator:
            panel.set_rare_evaluator(self._rare_evaluator)

        # Set AI callback if we have one
        if hasattr(self, '_ai_configured_callback') and self._ai_configured_callback:
            panel.results_table.set_ai_configured_callback(self._ai_configured_callback)

        idx = self.addTab(panel, session_name)
        self.setCurrentIndex(idx)

        logger.info(f"Added session: {session_name}")
        return panel

    def set_rare_evaluator(self, evaluator: Any) -> None:
        """Set the rare item evaluator for all session panels."""
        self._rare_evaluator = evaluator
        # Update all existing panels
        for i in range(self.count()):
            panel = self.widget(i)
            if isinstance(panel, SessionPanel):
                panel.set_rare_evaluator(evaluator)
