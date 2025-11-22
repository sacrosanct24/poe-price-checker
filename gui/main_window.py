"""
gui.main_window

Tkinter GUI for the PoE Price Checker.

- Paste or type item text into the input box.
- Click "Check Price" (or press Ctrl+Enter) to run a price check.
- View results in the table.
- Right–click a result row to copy it or copy it as TSV.
- File menu: open log file, open config folder, exit.
- Help menu: About dialog.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, TYPE_CHECKING

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


if TYPE_CHECKING:  # pragma: no cover
    from core.app_context import AppContext  # type: ignore


# Columns used by the real GUI results table.
RESULT_COLUMNS: tuple[str, ...] = (
    "item_name",
    "variant",
    "links",
    "chaos_value",
    "divine_value",
    "listing_count",
    "source",
)


class ResultsTable:
    """
    Helper class that owns the results Treeview and its scrollbar.

    This is used by the real GUI. The tests, however, create their own fake Treeview
    and attach it directly to a PriceCheckerGUI instance as `gui.tree`, so this class
    is not involved in the test path.
    """

    def __init__(self, parent: ttk.Frame, columns: tuple[str, ...]) -> None:
        self.columns = columns
        self._sort_reverse: dict[str, bool] = {}

        # Treeview + scrollbar
        self.tree = ttk.Treeview(
            parent,
            columns=self.columns,
            show="headings",
            selectmode="extended",
        )

        for col in self.columns:
            # Use a heading command so clicking the header sorts by that column.
            self.tree.heading(
                col,
                text=col.replace("_", " ").title(),
                command=lambda c=col: self._on_heading_click(c),
            )
            self.tree.column(col, width=100, anchor="w")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Remove all rows from the table."""
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

    def insert_rows(self, rows: Iterable[Mapping[str, Any] | Any]) -> None:
        """
        Insert rows into the table.

        Each row may be:
            - a mapping-like object with keys matching self.columns; or
            - an arbitrary object with attributes named like self.columns.
        """
        for row in rows:
            values: list[str] = []
            for col in self.columns:
                if isinstance(row, Mapping):
                    val = row.get(col, "")
                else:
                    val = getattr(row, col, "")
                values.append("" if val is None else str(val))
            self.tree.insert("", "end", values=values)

        # After inserting, adjust column widths based on content.
        self.autosize_columns()

    def get_selected_row_values(self) -> tuple[Any, ...]:
        """Return the values of the first selected row, or an empty tuple."""
        selection = self.tree.selection()
        if not selection:
            return ()
        item_id = selection[0]
        values = self.tree.item(item_id, "values")
        return tuple(values)

    def iter_rows(self) -> Iterable[tuple[Any, ...]]:
        """Yield all rows as tuples of values (in insertion order)."""
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            yield tuple(values)

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_tsv(self, include_header: bool = False) -> str:
        """
        Return the table contents as a TSV string.

        If include_header is True, the first line will be a header row made
        from the column names.
        """
        lines: list[str] = []

        if include_header:
            header = "\t".join(self.columns)
            lines.append(header)

        for row in self.iter_rows():
            lines.append("\t".join("" if v is None else str(v) for v in row))

        return "\n".join(lines)

    def export_tsv(self, path: str | Path, include_header: bool = False) -> None:
        """
        Write the table contents to a TSV file at the given path.

        Raises OSError if the file cannot be written.
        """
        tsv = self.to_tsv(include_header=include_header)
        p = Path(path)
        p.write_text(tsv, encoding="utf-8")

    # ------------------------------------------------------------------
    # Sorting & autosize
    # ------------------------------------------------------------------

    def _on_heading_click(self, column: str) -> None:
        """Handle clicks on a column header: toggle sort order and sort."""
        reverse = self._sort_reverse.get(column, False)
        # Toggle
        reverse = not reverse
        self._sort_reverse[column] = reverse
        self.sort_by_column(column, reverse=reverse)

    def sort_by_column(self, column: str, reverse: bool = False) -> None:
        """
        Sort table rows by a given column.

        Attempts numeric sort when possible, falling back to string sort.
        """
        if column not in self.columns:
            return

        col_index = self.columns.index(column)
        children = list(self.tree.get_children())

        def coerce(value: Any) -> Any:
            s = "" if value is None else str(value)
            try:
                # Try numeric comparison first (good for chaos/divine values)
                return float(s)
            except ValueError:
                return s.lower()

        # Build list of (key, item_id) and sort it.
        keyed = []
        for item_id in children:
            values = self.tree.item(item_id, "values") or ()
            val = values[col_index] if col_index < len(values) else ""
            keyed.append((coerce(val), item_id))

        keyed.sort(key=lambda pair: pair[0], reverse=reverse)

        # Reorder items in the tree to match the sorted order.
        for index, (_, item_id) in enumerate(keyed):
            self.tree.move(item_id, "", index)

    def autosize_columns(self, min_width: int = 80, max_width: int = 320) -> None:
        """
        Adjust column widths based on header + cell text lengths.

        Width is approximate: we use character count as a proxy and convert to
        pixels with a fixed factor.
        """
        # Rough "pixels per character" heuristic.
        px_per_char = 7

        for col in self.columns:
            # Start with header text length.
            header_text = self.tree.heading(col, "text") or ""
            max_chars = len(str(header_text))

            # Check each cell in this column.
            col_index = self.columns.index(col)
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, "values") or ()
                if col_index < len(values):
                    cell_text = "" if values[col_index] is None else str(values[col_index])
                    max_chars = max(max_chars, len(cell_text))

            # Convert to pixels: chars * px_per_char + some padding.
            width = max_chars * px_per_char + 20
            width = max(min_width, min(max_width, width))
            self.tree.column(col, width=width)


class PriceCheckerGUI:
    """Main GUI class for the PoE Price Checker."""

    def __init__(self, root: tk.Tk, app_context: Any) -> None:
        self.root = root
        self.app_context = app_context

        self.logger = self._resolve_logger()
        self.root.title("PoE Price Checker")
        self.root.geometry("900x600")

        # Main containers
        self.main_frame = ttk.Frame(self.root, padding=8)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Status bar var
        self.status_var = tk.StringVar(value="Ready")

        # Build UI pieces
        self._create_menu()
        self._create_input_area()
        self._create_results_area()
        self._create_status_bar()
        self._create_bindings()

        self._set_status("Ready")

    # -------------------------------------------------------------------------
    # Setup helpers
    # -------------------------------------------------------------------------

    def _resolve_logger(self) -> logging.Logger:
        logger = getattr(self.app_context, "logger", None)
        if isinstance(logger, logging.Logger):
            return logger
        # Fallback logger
        logger = logging.getLogger("poe_price_checker.gui")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open Log File", command=self._open_log_file)
        file_menu.add_command(label="Open Config Folder", command=self._open_config_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Export TSV...", command=self._export_results_tsv)
        file_menu.add_command(label="Copy All Rows as TSV", command=self._copy_all_rows_as_tsv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)


        # Help menu
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="Usage Tips", command=self._show_usage_tips)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
    # -------------------------------------------------------------------------
    # Layout pieces
    # -------------------------------------------------------------------------

    def _create_input_area(self) -> None:
        """Create the item input frame (text box + buttons)."""
        input_frame = ttk.LabelFrame(self.main_frame, text="Item Input", padding=8)
        input_frame.grid(row=0, column=0, sticky="nsew")

        # Text box
        self.input_text = tk.Text(input_frame, height=8, wrap="word", undo=True)
        self.input_text.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=(0, 6))

        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        # Buttons
        self.check_button = ttk.Button(input_frame, text="Check Price", command=self._on_check_clicked)
        self.clear_button = ttk.Button(input_frame, text="Clear", command=self._on_clear_clicked)
        self.paste_button = ttk.Button(input_frame, text="Paste", command=self._on_paste_button_clicked)

        self.check_button.grid(row=1, column=0, sticky="w", padx=(0, 4))
        self.clear_button.grid(row=1, column=1, sticky="w", padx=(0, 4))
        self.paste_button.grid(row=1, column=2, sticky="e")

    def _create_results_area(self) -> None:
        """Create the results frame and attach a ResultsTable."""
        results_frame = ttk.LabelFrame(self.main_frame, text="Results", padding=8)
        results_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        # Use ResultsTable helper
        self.results_table = ResultsTable(results_frame, RESULT_COLUMNS)
        # For compatibility with the rest of the GUI and tests,
        # keep a direct reference to the underlying Treeview.
        self.results_tree = self.results_table.tree

        # Context menu for tree
        self._create_tree_context_menu()

    def _create_status_bar(self) -> None:
        """Create the bottom status bar."""
        status_frame = ttk.Frame(self.root, padding=(8, 2))
        status_frame.grid(row=1, column=0, sticky="ew")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor="w")
        status_label.grid(row=0, column=0, sticky="w")
        status_frame.columnconfigure(0, weight=1)

    def _create_tree_context_menu(self) -> None:
        self.tree_menu = tk.Menu(self.results_tree, tearoff=False)
        self.tree_menu.add_command(label="Copy Row", command=self._copy_selected_row)
        self.tree_menu.add_command(label="Copy Row as TSV", command=self._copy_selected_row_as_tsv)

        self.results_tree.bind("<Button-3>", self._on_tree_right_click)
        # macOS sometimes uses Button-2; harmless on other platforms
        self.results_tree.bind("<Button-2>", self._on_tree_right_click)

    def _create_bindings(self) -> None:
        # Key bindings
        self.root.bind("<Control-Return>", self._on_check_clicked)  # Ctrl+Enter
        self.root.bind("<Control-K>", self._on_clear_clicked)       # Ctrl+K clear
        self.root.bind("<F5>", self._on_check_clicked)              # F5 re-check

        # Paste detection in text widget
        self.input_text.bind("<<Paste>>", self._on_paste)

    # -------------------------------------------------------------------------
    # Status helpers
    # -------------------------------------------------------------------------

    def _set_status(self, message: str) -> None:
        """
        Update the status bar and log the status if a logger is available.

        Defensive so it also works on the fake GUI used in tests.
        """
        if hasattr(self, "status_var"):
            self.status_var.set(message)

        logger = getattr(self, "logger", None)
        if isinstance(logger, logging.Logger):
            logger.info("Status: %s", message)

    # -------------------------------------------------------------------------
    # Menu commands
    # -------------------------------------------------------------------------

    def _open_log_file(self) -> None:
        path = getattr(self.app_context, "log_file_path", None)
        if not path:
            messagebox.showinfo("Log File", "Log file path is not configured.")
            return

        log_path = Path(path)
        if not log_path.exists():
            messagebox.showwarning("Log File", f"Log file does not exist:\n{log_path}")
            return

        self._open_path_in_explorer(log_path)
    def _show_shortcuts(self) -> None:
        """Show a small cheat sheet of keyboard & mouse shortcuts."""
        messagebox.showinfo(
            "Keyboard Shortcuts",
            (
                "Keyboard & Mouse Shortcuts\n\n"
                "• Ctrl+Enter   – Check prices\n"
                "• F5           – Re-check prices\n"
                "• Ctrl+K       – Clear input and results\n"
                "• Right-click  – Show row context menu (Copy / Copy as TSV)\n"
                "• Paste button – Paste item from clipboard and auto-check\n"
            ),
        )

    def _show_usage_tips(self) -> None:
        """Show helpful usage tips, including the menu items we’ve added."""
        messagebox.showinfo(
            "Usage Tips",
            (
                "Usage Tips\n\n"
                "• Paste your Path of Exile item text into the input box,\n"
                "  then press Ctrl+Enter or click \"Check Price\".\n\n"
                "• The Results table shows key data like chaos/divine value\n"
                "  and listing counts; click column headers to sort.\n\n"
                "• Right-click a row to:\n"
                "  – Copy Row (space-separated)\n"
                "  – Copy Row as TSV (tab-separated)\n\n"
                "• File → Open Log File\n"
                "  Open the current log file for debugging.\n\n"
                "• File → Open Config Folder\n"
                "  Jump straight to the config directory.\n\n"
                "• File → Export TSV...\n"
                "  Save all current results to a .tsv file with headers.\n"
            ),
        )

    def _open_config_folder(self) -> None:
        cfg = getattr(self.app_context, "config_dir", None)
        if not cfg:
            messagebox.showinfo("Config Folder", "Config folder is not configured.")
            return

        cfg_path = Path(cfg)
        if not cfg_path.exists():
            messagebox.showwarning("Config Folder", f"Config folder does not exist:\n{cfg_path}")
            return

        self._open_path_in_explorer(cfg_path)

    def _copy_all_rows_as_tsv(self) -> None:
        """
        Copy all rows in the results table as TSV to the clipboard.

        Uses ResultsTable.to_tsv(include_header=True).
        """
        if not hasattr(self, "results_table"):
            messagebox.showinfo("Copy All Rows as TSV", "No results table is available.")
            return

        rows = list(self.results_table.iter_rows())
        if not rows:
            messagebox.showinfo(
                "Copy All Rows as TSV",
                "There are no rows in the results table to copy.",
            )
            self._set_status("No rows to copy.")
            return

        tsv_text = self.results_table.to_tsv(include_header=True)
        self._set_clipboard(tsv_text)
        self._set_status("All rows copied as TSV to clipboard.")
        messagebox.showinfo(
            "Copy All Rows as TSV",
            "All results have been copied to the clipboard as TSV.\n\n"
            "You can now paste into Excel, Google Sheets, or a text editor.",
        )

    def _export_results_tsv(self) -> None:
        """
        Prompt for a file path and export the current results table to TSV.

        Uses ResultsTable.export_tsv under the hood.
        """
        if not hasattr(self, "results_table"):
            messagebox.showinfo("Export TSV", "No results table is available to export.")
            return

        # If there are no rows, give a gentle heads-up.
        if not list(self.results_table.iter_rows()):
            if not messagebox.askyesno(
                "Export TSV",
                "There are no results in the table.\n\n"
                "Export an empty file anyway?",
                icon=messagebox.QUESTION,
            ):
                return

        initial_dir = str(Path.home())
        default_name = "poe_price_results.tsv"

        file_path = filedialog.asksaveasfilename(
            title="Export Results as TSV",
            defaultextension=".tsv",
            filetypes=[("TSV files", "*.tsv"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile=default_name,
        )

        # User cancelled
        if not file_path:
            self._set_status("Export cancelled.")
            return

        try:
            # Include header row for clarity
            self.results_table.export_tsv(file_path, include_header=True)
        except OSError as exc:
            self.logger.exception("Failed to export TSV to %s: %s", file_path, exc)
            messagebox.showerror(
                "Export TSV",
                f"Failed to export results to:\n{file_path}\n\n{exc}",
            )
            self._set_status("Export TSV failed.")
            return

        self._set_status(f"Exported results to {file_path}")
        messagebox.showinfo("Export TSV", f"Results exported to:\n{file_path}")

    def _open_path_in_explorer(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as exc:  # pragma: no cover - OS specific
            self.logger.exception("Failed to open path %s: %s", path, exc)
            messagebox.showerror("Error", f"Failed to open path:\n{path}\n\n{exc}")

    def _show_about_dialog(self) -> None:
        messagebox.showinfo(
            "About PoE Price Checker",
            "PoE Price Checker\n\n"
            "GUI front-end for Path of Exile item price checks.\n"
            "Paste item text, run checks, and copy results.",
        )

    # -------------------------------------------------------------------------
    # Input / action handlers
    # -------------------------------------------------------------------------

    def _get_input_text(self) -> str:
        return self.input_text.get("1.0", "end").strip()

    def _on_check_clicked(self, event: tk.Event | None = None) -> None:  # type: ignore[override]
        del event  # unused
        text = self._get_input_text()
        if not text:
            self._set_status("No item text to check.")
            return

        self._set_status("Checking prices...")
        # Small delay to keep UI responsive
        self.root.after(10, self._run_price_check)

    def _run_price_check(self) -> None:
        text = self._get_input_text()
        if not text:
            self._set_status("No item text to check.")
            return

        price_service = getattr(self.app_context, "price_service", None)
        if price_service is None:
            # Fallback: just insert a dummy row so GUI is still usable in isolation
            self.logger.warning("price_service not available on app_context; inserting dummy result.")
            self._clear_results()
            self._insert_result_rows(
                [
                    {
                        "item_name": "Dummy Item",
                        "variant": "N/A",
                        "links": "N/A",
                        "chaos_value": "0",
                        "divine_value": "0",
                        "listing_count": "0",
                        "source": "no price_service",
                    }
                ]
            )
            self._set_status("price_service not configured; showing dummy result.")
            return

        try:
            results = price_service.check_item(text)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - depends on service
            self.logger.exception("Error during price check: %s", exc)
            messagebox.showerror("Error", f"An error occurred while checking prices:\n{exc}")
            self._set_status("Error during price check.")
            return

        self._clear_results()

        try:
            self._insert_result_rows(results)
            self._set_status("Price check complete.")
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Error inserting results: %s", exc)
            messagebox.showerror("Error", f"Failed to display results:\n{exc}")
            self._set_status("Failed to display results.")

    def _insert_result_rows(self, rows: Iterable[Mapping[str, Any] | Any]) -> None:
        """
        Insert rows into the results table.

        Delegates to ResultsTable for the real GUI.
        """
        if hasattr(self, "results_table"):
            self.results_table.insert_rows(rows)

    def _clear_results(self) -> None:
        """Clear all rows from the results table."""
        if hasattr(self, "results_table"):
            self.results_table.clear()

    def _on_clear_clicked(self, event: tk.Event | None = None) -> None:  # type: ignore[override]
        del event
        self.input_text.delete("1.0", "end")
        self._clear_results()
        self._set_status("Cleared.")

    def _on_paste_button_clicked(self) -> None:
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        if text:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
            self._auto_check_if_not_empty()

    def _on_paste(self, event: tk.Event | None = None) -> None:
        """
        Handle <<Paste>> into the text box and auto-check after paste.

        We schedule a short delay so the default paste operation completes first.
        """
        del event
        # Let the default paste complete, then check
        self.root.after(10, self._auto_check_if_not_empty)  # type: ignore[arg-type]

    def _auto_check_if_not_empty(self) -> None:
        if self._get_input_text():
            self._on_check_clicked()

    # -------------------------------------------------------------------------
    # Treeview helpers (used by tests)
    # -------------------------------------------------------------------------

    def _get_tree(self) -> Any:
        """
        Return the Treeview-like object in use.

        In the real GUI this is self.results_tree.
        In tests, a fake Treeview is attached as self.tree.
        """
        tree = getattr(self, "tree", None)
        if tree is not None:
            return tree
        return getattr(self, "results_tree", None)

    def _get_selected_row(self) -> tuple[Any, ...]:
        """
        Return the values of the currently selected row as a tuple.

        Works with:
          - real GUI: uses ResultsTable (via self.results_table)
          - tests:    uses self.tree (a fake Treeview) or self.results_tree
        """
        # Real GUI path: prefer ResultsTable if present and tree matches
        if hasattr(self, "results_table"):
            tree = self._get_tree()
            if tree is self.results_table.tree:
                return self.results_table.get_selected_row_values()

        # Test / fallback path: use whichever Treeview-like object _get_tree returns
        tree = self._get_tree()
        if tree is None:
            return ()

        selection = tree.selection()
        if not selection:
            return ()

        item_id = selection[0]
        values = tree.item(item_id, "values")
        return tuple(values)

    def _copy_row_tsv(self) -> None:
        """
        Copy the selected row as TSV.

        Tests call this on a fake GUI:
            gui._copy_row_tsv()
        and expect it to:
          - read from gui.tree (via _get_selected_row)
          - call gui._copy_to_clipboard(tsv_string) if present
        """
        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected to copy.")
            return

        line = "\t".join(str(v) for v in row)

        # Tests stub _copy_to_clipboard; real GUI uses _set_clipboard.
        copy_fn = getattr(self, "_copy_to_clipboard", None)
        if callable(copy_fn):
            copy_fn(line)
        else:
            self._set_clipboard(line)

        self._set_status("Row copied as TSV to clipboard.")

    # -------------------------------------------------------------------------
    # Treeview context menu / copy helpers
    # -------------------------------------------------------------------------

    def _on_tree_right_click(self, event: tk.Event) -> None:
        region = self.results_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.results_tree.identify_row(event.y)
        if not row_id:
            return

        # Ensure the row is selected before showing the menu
        if row_id not in self.results_tree.selection():
            self.results_tree.selection_set(row_id)

        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:  # pragma: no cover - Tk internal
            self.tree_menu.grab_release()

    def _copy_selected_row(self) -> None:
        """
        Context menu → copy selected row as space-separated text.
        """
        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected to copy.")
            return

        text = " ".join(str(v) for v in row)
        self._set_clipboard(text)
        self._set_status("Row copied to clipboard.")

    def _copy_selected_row_as_tsv(self) -> None:
        """
        Context menu → copy selected row as TSV.
        Reuses the same core logic as _copy_row_tsv.
        """
        self._copy_row_tsv()

    def _set_clipboard(self, text: str) -> None:
        # Helper so tests can monkeypatch if needed
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        # Update to ensure clipboard is populated even if app closes soon
        try:
            self.root.update_idletasks()
        except tk.TclError:
            # In headless or teardown scenarios, this may fail; ignore.
            pass


# -------------------------------------------------------------------------
# Optional convenience entrypoint
# -------------------------------------------------------------------------

def run(app_context: Any) -> None:
    """
    Convenience function to run the GUI directly.
    """
    root = tk.Tk()
    root.withdraw()  # Start hidden to avoid flash; we deiconify after setup
    gui = PriceCheckerGUI(root, app_context)
    root.deiconify()
    root.mainloop()
