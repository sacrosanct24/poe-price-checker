"""
gui_qt.controllers.results_context_controller - Results table context menu controller.

Extracts the results context menu functionality from main_window.py:
- Context menu creation and display
- Copy row / copy as TSV
- Price explanation dialog
- Record sale dialog
- AI item analysis

Usage:
    controller = ResultsContextController(ctx=app_context, parent=main_window)
    controller.show_context_menu(pos, results_table)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from gui_qt.widgets.results_table import ResultsTableWidget
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class ResultsContextController:
    """
    Controller for results table context menu operations.

    Handles:
    - Context menu display
    - Row copying (plain text and TSV)
    - Price explanation dialogs
    - Sale recording
    - AI item analysis
    """

    def __init__(
        self,
        ctx: "AppContext",
        parent: QWidget,
        on_status: Optional[Callable[[str], None]] = None,
        on_toast_success: Optional[Callable[[str], None]] = None,
        on_toast_error: Optional[Callable[[str], None]] = None,
        on_ai_analysis: Optional[Callable[[str, List[Dict[str, Any]]], None]] = None,
        ai_configured: Optional[Callable[[], bool]] = None,
    ):
        """
        Initialize the results context controller.

        Args:
            ctx: Application context with database access.
            parent: Parent widget for dialogs.
            on_status: Callback for status bar messages.
            on_toast_success: Callback for success toast notifications.
            on_toast_error: Callback for error toast notifications.
            on_ai_analysis: Callback to trigger AI analysis (item_text, price_results).
            ai_configured: Callback to check if AI is configured.
        """
        self._ctx = ctx
        self._parent = parent
        self._on_status = on_status or (lambda msg: None)
        self._on_toast_success = on_toast_success or (lambda msg: None)
        self._on_toast_error = on_toast_error or (lambda msg: None)
        self._on_ai_analysis = on_ai_analysis
        self._ai_configured = ai_configured or (lambda: False)

    def show_context_menu(
        self,
        pos,
        results_table: "ResultsTableWidget",
    ) -> None:
        """
        Show context menu for results table.

        Args:
            pos: Position where to show the menu.
            results_table: The results table widget.
        """
        menu = QMenu(self._parent)

        selected = results_table.get_selected_row()
        if selected:
            copy_action = menu.addAction("Copy Row")
            if copy_action:
                copy_action.triggered.connect(
                    lambda: self._copy_selected_row(results_table)
                )

            copy_tsv_action = menu.addAction("Copy as TSV")
            if copy_tsv_action:
                copy_tsv_action.triggered.connect(
                    lambda: self._copy_row_as_tsv(results_table)
                )

            menu.addSeparator()

            explain_action = menu.addAction("Why This Price?")
            if explain_action:
                explain_action.triggered.connect(
                    lambda: self._explain_price(results_table)
                )

            menu.addSeparator()

            record_sale_action = menu.addAction("Record Sale...")
            if record_sale_action:
                record_sale_action.triggered.connect(
                    lambda: self._record_sale(results_table)
                )

            # AI Analysis option
            if self._on_ai_analysis is not None:
                menu.addSeparator()
                ai_action = menu.addAction("Ask AI About This Item")
                if ai_action:
                    ai_action.setEnabled(self._ai_configured())
                    if not self._ai_configured():
                        ai_action.setToolTip("Configure AI in Settings > AI")
                    ai_action.triggered.connect(
                        lambda: self._ask_ai_about_item(results_table)
                    )

        menu.exec(results_table.mapToGlobal(pos))

    def _copy_selected_row(self, results_table: "ResultsTableWidget") -> None:
        """Copy selected row to clipboard as formatted text."""
        row = results_table.get_selected_row()
        if row:
            text = " | ".join(
                f"{k}: {v}" for k, v in row.items() if k != "price_explanation"
            )
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
            self._on_status("Row copied to clipboard")

    def _copy_row_as_tsv(self, results_table: "ResultsTableWidget") -> None:
        """Copy selected row as TSV."""
        row = results_table.get_selected_row()
        if row:
            values = [
                str(row.get(col, ""))
                for col in results_table.columns
                if col != "price_explanation"
            ]
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText("\t".join(values))
            self._on_status("Row copied as TSV")

    def _explain_price(self, results_table: "ResultsTableWidget") -> None:
        """Show price explanation dialog."""
        from core.price_service import PriceExplanation
        from gui_qt.styles import COLORS

        row = results_table.get_selected_row()
        if not row:
            return

        explanation_json = row.get("price_explanation", "")
        if not explanation_json or explanation_json == "{}":
            # Show basic info even without explanation
            self._show_basic_price_info(row)
            return

        try:
            explanation = PriceExplanation.from_json(explanation_json)
            lines = explanation.to_summary_lines()

            if not lines:
                lines = ["No explanation details available."]

            # Build header
            item_name = row.get("item_name", "Unknown")
            chaos = row.get("chaos_value", 0)
            divine = row.get("divine_value", 0)

            header = f"Item: {item_name}\n"
            header += f"Price: {chaos:.1f}c"
            if divine:
                header += f" ({divine:.2f} divine)"
            header += "\n" + "─" * 40 + "\n"

            text = header + "\n".join(lines)

            # Use a dialog with more room for text
            dialog = QDialog(self._parent)
            dialog.setWindowTitle("Price Explanation")
            dialog.setMinimumSize(450, 350)

            layout = QVBoxLayout(dialog)

            # Text display
            text_widget = QTextEdit()
            text_widget.setReadOnly(True)
            text_widget.setPlainText(text)
            text_widget.setStyleSheet(
                f"background-color: {COLORS['background']}; color: {COLORS['text']};"
            )
            layout.addWidget(text_widget)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.exec()

        except Exception as e:
            QMessageBox.information(
                self._parent,
                "Price Explanation",
                f"Could not parse price explanation: {e}",
            )

    def _show_basic_price_info(self, row: Dict[str, Any]) -> None:
        """Show basic price info when no detailed explanation available."""
        item_name = row.get("item_name", "Unknown")
        source = row.get("source", "Unknown")
        chaos = row.get("chaos_value", 0)
        divine = row.get("divine_value", 0)

        text = f"Item: {item_name}\n"
        text += f"Source: {source}\n"
        text += f"Price: {chaos:.1f}c"
        if divine:
            text += f" ({divine:.2f} divine)"
        text += "\n\nNo detailed explanation available for this price."

        QMessageBox.information(self._parent, "Price Explanation", text)

    def _record_sale(self, results_table: "ResultsTableWidget") -> None:
        """Record a sale for the selected item."""
        row = results_table.get_selected_row()
        if not row:
            return

        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(
            self._parent,
            item_name=row.get("item_name", ""),
            suggested_price=row.get("chaos_value", 0),
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            price, notes = dialog.get_values()
            try:
                # record_sale may not be on interface, use getattr
                db_record = getattr(self._ctx.db, 'record_sale', None)
                if db_record:
                    db_record(
                        item_name=row.get("item_name", ""),
                        chaos_value=price,
                        source=row.get("source", ""),
                        notes=notes,
                    )
                self._on_status(f"Sale recorded: {row.get('item_name', '')} for {price}c")
                if self._on_toast_success:
                    self._on_toast_success(f"Sale recorded: {price:.0f}c")
            except Exception as e:
                QMessageBox.critical(
                    self._parent, "Error", f"Failed to record sale: {e}"
                )

    def _ask_ai_about_item(self, results_table: "ResultsTableWidget") -> None:
        """Trigger AI analysis for the selected item."""
        if self._on_ai_analysis is None:
            return

        row = results_table.get_selected_row()
        if not row:
            return

        # Build item text from the row data
        # We need to reconstruct something that looks like item text
        item_name = row.get("item_name", "Unknown Item")
        source = row.get("source", "")
        chaos_value = row.get("chaos_value", 0)
        divine_value = row.get("divine_value", 0)

        # Build a simple item representation
        item_text = f"{item_name}"

        # Build price results list
        price_results: List[Dict[str, Any]] = [{
            "item_name": item_name,
            "chaos_value": chaos_value,
            "divine_value": divine_value,
            "source": source,
        }]

        # Call the AI analysis callback
        self._on_ai_analysis(item_text, price_results)


def get_results_context_controller(
    ctx: "AppContext",
    parent: QWidget,
    on_status: Optional[Callable[[str], None]] = None,
    on_toast_success: Optional[Callable[[str], None]] = None,
    on_toast_error: Optional[Callable[[str], None]] = None,
    on_ai_analysis: Optional[Callable[[str, List[Dict[str, Any]]], None]] = None,
    ai_configured: Optional[Callable[[], bool]] = None,
) -> ResultsContextController:
    """
    Factory function to create a ResultsContextController.

    Args:
        ctx: Application context.
        parent: Parent widget.
        on_status: Status callback.
        on_toast_success: Success toast callback.
        on_toast_error: Error toast callback.
        on_ai_analysis: Callback to trigger AI analysis.
        ai_configured: Callback to check if AI is configured.

    Returns:
        Configured ResultsContextController instance.
    """
    return ResultsContextController(
        ctx=ctx,
        parent=parent,
        on_status=on_status,
        on_toast_success=on_toast_success,
        on_toast_error=on_toast_error,
        on_ai_analysis=on_ai_analysis,
        ai_configured=ai_configured,
    )
