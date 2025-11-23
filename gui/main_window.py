"""
gui.main_window

Tkinter GUI for the PoE Price Checker.

- Paste or type item text into the input box.
- Click "Check Price" (or press Ctrl+Enter) to run a price check.
- View results in the table.
- Right–click a result row to open in browser, copy it, copy it as TSV, or view details.
- File menu: open log file, open config folder, export TSV, copy all as TSV, exit.
- View menu: session history, data sources, column visibility, recent sales, sales dashboard.
- Dev menu: paste sample items of various types (map, currency, unique, etc.).
- Help menu: shortcuts, usage tips, about.
"""

from __future__ import annotations

import logging
import os
import random
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, TYPE_CHECKING, Callable

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import messagebox
from urllib.parse import quote_plus  # currently unused but kept for future URL tweaks

from gui.recent_sales_window import RecentSalesWindow
from gui.sales_dashboard_window import SalesDashboardWindow

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

# ----------------------------------------------------------------------
# Sample item texts for development convenience (Dev → Paste Sample ...).
# These are approximate PoE clipboard formats, good enough for testing.
# ----------------------------------------------------------------------
SAMPLE_ITEMS: dict[str, list[str]] = {
    "map": [
        """Rarity: Normal
Cemetery Map
--------
Map Tier: 5
Atlas Region: Haewark Hamlet
Item Level: 73
--------
Travel to this Map by using it in the Templar Laboratory or a personal Map Device. Maps can only be used once.
""",
        """Rarity: Magic
Volcano Map of Exposure
--------
Map Tier: 10
Atlas Region: Lex Proxima
Item Level: 80
--------
Item Quantity: +24%
Item Rarity: +16%
Monster Pack Size: +8%
--------
Monsters deal 25% extra Fire Damage
Monsters have 30% Fire Resistance
--------
Travel to this Map by using it in the Templar Laboratory or a personal Map Device. Maps can only be used once.
""",
    ],
    "currency": [
        """Rarity: Currency
Chaos Orb
--------
Stack Size: 1/10
--------
Reforges a rare item with new random modifiers
--------
Right click this item then left click a rare item to apply it.
""",
        """Rarity: Currency
Orb of Alchemy
--------
Stack Size: 1/20
--------
Upgrades a normal item to a rare item
--------
Right click this item then left click a normal item to apply it.
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
--------
A white canvas awaits new colours.
""",
        """Rarity: Unique
Goldrim
Leather Cap
--------
Evasion Rating: 33
--------
Requires Level 1
--------
+30% to all Elemental Resistances
10% increased Rarity of Items found
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
Cyclone
--------
Attack, AoE, Movement, Channeling, Melee
Level: 20
Quality: +20%
Mana Cost: 2
--------
Requires Level 70, 95 Str
--------
Channel this skill to move towards a targeted location while spinning, damaging nearby enemies.
""",
    ],
}


class RecordSaleDialog:
    """
    Simple modal dialog to confirm/edit a sale before recording it.

    It lets the user confirm the chaos price and optionally add notes.
    On success, it calls the provided `on_submit` callback.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        item_name: str,
        source: str,
        default_chaos_value: float,
        on_submit: Callable[[float, str | None], None],
    ) -> None:
        self._parent = parent
        self._on_submit = on_submit

        self.top = tk.Toplevel(parent)
        self.top.title("Record Sale")
        self.top.transient(parent)
        self.top.grab_set()

        # Basic layout
        frame = ttk.Frame(self.top, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")

        self.top.columnconfigure(0, weight=1)
        self.top.rowconfigure(0, weight=1)

        # Item name (read-only)
        ttk.Label(frame, text="Item:").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=item_name, font=("", 10, "bold")).grid(
            row=0, column=1, sticky="w"
        )

        # Source (read-only)
        ttk.Label(frame, text="Source:").grid(row=1, column=0, sticky="w")
        ttk.Label(frame, text=source).grid(row=1, column=1, sticky="w")

        # Chaos price
        ttk.Label(frame, text="Sale price (chaos):").grid(row=2, column=0, sticky="w")
        self.price_var = tk.StringVar()
        if default_chaos_value > 0:
            self.price_var.set(f"{default_chaos_value:.1f}")
        self.price_entry = ttk.Entry(frame, textvariable=self.price_var, width=10)
        self.price_entry.grid(row=2, column=1, sticky="w")
        self.price_entry.focus_set()

        # Notes
        ttk.Label(frame, text="Notes (optional):").grid(row=3, column=0, sticky="nw")
        self.notes_text = tk.Text(frame, width=40, height=4)
        self.notes_text.grid(row=3, column=1, sticky="nsew", pady=(2, 4))

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="e", pady=(8, 0))

        ok_button = ttk.Button(button_frame, text="Record Sale", command=self._on_ok)
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        ok_button.grid(row=0, column=0, padx=(0, 8))
        cancel_button.grid(row=0, column=1)

        # Keybindings
        self.top.bind("<Return>", lambda e: self._on_ok())
        self.top.bind("<Escape>", lambda e: self._on_cancel())

        # Allow resizing a bit
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

        # Center over parent
        self._center_over_parent()

    def _center_over_parent(self) -> None:
        self.top.update_idletasks()
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        parent_w = self._parent.winfo_width()
        parent_h = self._parent.winfo_height()

        w = self.top.winfo_width()
        h = self.top.winfo_height()

        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2

        self.top.geometry(f"+{x}+{y}")

    def _on_ok(self) -> None:
        raw_price = self.price_var.get().strip()
        if not raw_price:
            messagebox.showerror("Record Sale", "Please enter a chaos price.")
            return

        try:
            chaos_value = float(raw_price)
        except ValueError:
            messagebox.showerror(
                "Record Sale", f"Invalid chaos value: {raw_price!r}. Please enter a number."
            )
            return

        notes = self.notes_text.get("1.0", "end").strip()
        if notes == "":
            notes = None

        try:
            self._on_submit(chaos_value, notes)
        finally:
            self.top.destroy()

    def _on_cancel(self) -> None:
        self.top.destroy()


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

        # Track which columns are currently hidden and their base widths
        self._hidden_columns: set[str] = set()
        self._base_column_widths: dict[str, int] = {}

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
            # Remember an initial base width; autosize will refine it later.
            self._base_column_widths[col] = 100

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        # Configure visual tags for row highlighting
        self._configure_tags()

    # ------------------------------------------------------------------
    # Tag configuration & row classification
    # ------------------------------------------------------------------

    def _configure_tags(self) -> None:
        """
        Configure Treeview tags used for row highlighting.

        Colors are intentionally mild so they don't make the table unreadable.
        """
        # High-value items: strong green text
        self.tree.tag_configure(
            "high_value",
            foreground="#006400",  # dark green
        )

        # Medium-value items: blue text
        self.tree.tag_configure(
            "medium_value",
            foreground="#00008B",  # dark blue
        )

        # Fractured items: light red-tinted background
        self.tree.tag_configure(
            "fractured_item",
            background="#ffe5e5",
        )

        # Craft bases: light purple/blue background
        self.tree.tag_configure(
            "craft_base",
            background="#e5e5ff",
        )

    def _compute_tags_for_values(self, values: list[str]) -> tuple[str, ...]:
        """
        Decide which tags should apply to a row based on its values.

        `values` is ordered according to self.columns.
        """
        tags: list[str] = []

        data = {col: (values[idx] if idx < len(values) else "") for idx, col in enumerate(self.columns)}

        # High / medium value based on chaos_value column
        chaos_str = (data.get("chaos_value") or "").strip()
        try:
            chaos_val = float(chaos_str)
        except ValueError:
            chaos_val = 0.0

        if chaos_val >= 50:
            tags.append("high_value")
        elif chaos_val >= 10:
            tags.append("medium_value")

        # Fractured items: look at item_name / variant for "fracture"/"fractured"
        name = (data.get("item_name") or "").lower()
        variant = (data.get("variant") or "").lower()

        if "fractured" in name or "fractured" in variant or "fracture" in name or "fracture" in variant:
            tags.append("fractured_item")

        # Craft bases: check source/name/variant for "craft"
        source = (data.get("source") or "").lower()
        if "craft" in source or "craft" in name or "craft" in variant:
            tags.append("craft_base")

        return tuple(tags)

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

            tags = self._compute_tags_for_values(values)
            self.tree.insert("", "end", values=values, tags=tags)

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
                return float(s)
            except ValueError:
                return s.lower()

        keyed = []
        for item_id in children:
            values = self.tree.item(item_id, "values") or ()
            val = values[col_index] if col_index < len(values) else ""
            keyed.append((coerce(val), item_id))

        keyed.sort(key=lambda pair: pair[0], reverse=reverse)

        for index, (_, item_id) in enumerate(keyed):
            self.tree.move(item_id, "", index)

    def autosize_columns(self, min_width: int = 80, max_width: int = 320) -> None:
        """
        Adjust column widths based on header + cell text lengths.

        Width is approximate: we use character count as a proxy and convert to
        pixels with a fixed factor.
        """
        px_per_char = 7

        for col in self.columns:
            if col in self._hidden_columns:
                continue

            header_text = self.tree.heading(col, "text") or ""
            max_chars = len(str(header_text))

            col_index = self.columns.index(col)
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, "values") or ()
                if col_index < len(values):
                    cell_text = "" if values[col_index] is None else str(values[col_index])
                    max_chars = max(max_chars, len(cell_text))

            width = max_chars * px_per_char + 20
            width = max(min_width, min(max_width, width))
            self.tree.column(col, width=width)

            self._base_column_widths[col] = width

    # ------------------------------------------------------------------
    # Column visibility
    # ------------------------------------------------------------------

    def set_column_visibility(self, visibility: Mapping[str, bool]) -> None:
        """
        Show/hide columns based on a mapping of column name -> visible flag.

        We implement hiding by shrinking the column width/minwidth to 0 and
        disabling stretch. Showing restores the last known base width.
        """
        for col in self.columns:
            visible = visibility.get(col, True)

            if visible:
                self._hidden_columns.discard(col)
                base_width = self._base_column_widths.get(col, 100)
                self.tree.column(col, width=base_width, minwidth=20, stretch=True)
                self.tree.heading(col, text=col.replace("_", " ").title())
            else:
                try:
                    current_width = int(self.tree.column(col, "width"))
                except (ValueError, tk.TclError):
                    current_width = self._base_column_widths.get(col, 100)

                if col not in self._hidden_columns:
                    self._base_column_widths[col] = current_width

                self._hidden_columns.add(col)
                self.tree.column(col, width=0, minwidth=0, stretch=False)


class PriceCheckerGUI:
    """Main GUI class for the PoE Price Checker."""

    def __init__(self, root: tk.Tk, app_context: Any) -> None:
        # Core references
        self.root = root
        self.ctx = app_context          # main context reference
        self.app_context = app_context  # kept for compatibility

        # Child windows
        self._recent_sales_window: RecentSalesWindow | None = None
        self._sales_dashboard_window: SalesDashboardWindow | None = None

        # Logger & window basics
        self.logger = self._resolve_logger()
        self.root.title("PoE Price Checker")
        self.root.geometry("1100x650")

        # Menubar
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # Main containers
        self.main_frame = ttk.Frame(self.root, padding=8)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=2)
        self.main_frame.rowconfigure(1, weight=1)  # results row

        # Status bar var
        self.status_var = tk.StringVar(value="Ready")

        # Summary bar var (last price check summary)
        self.summary_var = tk.StringVar(value="No recent price summary.")

        # Filter text & backing store for all rows
        self.filter_var = tk.StringVar(value="")
        self._all_result_rows: list[Mapping[str, Any]] = []

        # Source filter (GUI shortcut to filter by 'source' column)
        self.source_filter_var = tk.StringVar(value="All sources")
        self._source_filter_value: str | None = None

        # Column visibility dialog state
        self._column_visibility_vars: dict[str, tk.BooleanVar] = {}
        self._column_visibility_window: tk.Toplevel | None = None

        # Session history
        self._history: list[dict[str, Any]] = []
        self._history_window: tk.Toplevel | None = None
        self._history_listbox: tk.Listbox | None = None

        # Data sources dialog
        self._sources_window: tk.Toplevel | None = None
        self._source_vars: dict[str, tk.BooleanVar] = {}

        # Async check state
        self._check_in_progress: bool = False

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
        logger = logging.getLogger("poe_price_checker.gui")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def _on_wipe_database(self) -> None:
        """
        Prompt the user and, if confirmed, wipe all data tables via Database.wipe_all_data.
        """
        msg = (
            "This will delete ALL saved data:\n\n"
            "  • Checked items\n"
            "  • Sales history\n"
            "  • Price history snapshots\n"
            "  • Plugin state\n\n"
            "This cannot be undone.\n\n"
            "Are you sure you want to wipe the database?"
        )
        if not messagebox.askyesno("Wipe Database", msg, parent=self.root):
            return

        try:
            self.ctx.db.wipe_all_data()
        except Exception as exc:
            self.logger.exception("Failed to wipe database: %s", exc)
            messagebox.showerror(
                "Error",
                f"Failed to wipe database.\n\n{exc}",
                parent=self.root,
            )
            return

        # Clear UI state as well
        try:
            self._clear_results_table()
        except Exception:
            pass

        self._set_status("Database wiped: all data cleared.")
        messagebox.showinfo(
            "Database Wiped",
            "All database tables have been cleared.",
            parent=self.root,
        )

    def _open_recent_sales_window(self) -> None:
        """Open (or focus) the Recent Sales panel."""
        if self._recent_sales_window is not None and self._recent_sales_window.winfo_exists():
            self._recent_sales_window.deiconify()
            self._recent_sales_window.lift()
            self._recent_sales_window.focus_set()
            return

        self._recent_sales_window = RecentSalesWindow(
            master=self.root,
            db=self.ctx.db,
            limit=50,
        )
        self._recent_sales_window.focus_set()

    def _open_sales_dashboard_window(self) -> None:
        """Open (or focus) the Sales Dashboard panel."""
        if (
            self._sales_dashboard_window is not None
            and self._sales_dashboard_window.winfo_exists()
        ):
            self._sales_dashboard_window.deiconify()
            self._sales_dashboard_window.lift()
            self._sales_dashboard_window.focus_set()
            return

        self._sales_dashboard_window = SalesDashboardWindow(
            master=self.root,
            db=self.ctx.db,
            days=30,
        )
        self._sales_dashboard_window.focus_set()

    def _create_menu(self) -> None:
        """Create the main menubar and all top-level menus."""

        # -------------------------
        # File menu
        # -------------------------
        file_menu = tk.Menu(self.menubar, tearoff=False)
        file_menu.add_command(label="Open Log File", command=self._open_log_file)
        file_menu.add_command(label="Open Config Folder", command=self._open_config_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Export TSV...", command=self._export_results_tsv)
        file_menu.add_command(label="Copy All Rows as TSV", command=self._copy_all_rows_as_tsv)
        file_menu.add_separator()
        file_menu.add_command(
            label="Wipe Database…",
            command=self._on_wipe_database,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menubar.add_cascade(label="File", menu=file_menu)

        # -------------------------
        # View menu
        # -------------------------
        view_menu = tk.Menu(self.menubar, tearoff=False)
        view_menu.add_command(label="Session History...", command=self._show_history_window)
        view_menu.add_command(label="Data Sources...", command=self._show_sources_dialog)
        view_menu.add_separator()
        view_menu.add_command(label="Recent Sales…", command=self._open_recent_sales_window)
        view_menu.add_command(label="Sales Dashboard…", command=self._open_sales_dashboard_window)
        self.menubar.add_cascade(label="View", menu=view_menu)

        # -------------------------
        # Dev menu
        # -------------------------
        dev_menu = tk.Menu(self.menubar, tearoff=False)
        dev_menu.add_command(label="Paste Sample Map", command=lambda: self._paste_sample_item("map"))
        dev_menu.add_command(label="Paste Sample Currency", command=lambda: self._paste_sample_item("currency"))
        dev_menu.add_command(label="Paste Sample Unique", command=lambda: self._paste_sample_item("unique"))
        dev_menu.add_command(label="Paste Sample Rare", command=lambda: self._paste_sample_item("rare"))
        dev_menu.add_command(label="Paste Sample Gem", command=lambda: self._paste_sample_item("gem"))
        self.menubar.add_cascade(label="Dev", menu=dev_menu)

        # -------------------------
        # Help menu
        # -------------------------
        help_menu = tk.Menu(self.menubar, tearoff=False)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="Usage Tips", command=self._show_usage_tips)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about_dialog)
        self.menubar.add_cascade(label="Help", menu=help_menu)

        # Final: assign to root (safe even if already set)
        self.root.config(menu=self.menubar)

    # -------------------------------------------------------------------------
    # Layout pieces
    # -------------------------------------------------------------------------

    def _create_input_area(self) -> None:
        """Create the item input frame (text box + buttons) and the item inspector sidebar."""
        top_row = ttk.Frame(self.main_frame)
        top_row.grid(row=0, column=0, columnspan=2, sticky="nsew")
        top_row.columnconfigure(0, weight=3)
        top_row.columnconfigure(1, weight=2)

        # --- Item Input (left) ---
        input_frame = ttk.LabelFrame(top_row, text="Item Input", padding=8)
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.input_text = tk.Text(input_frame, height=8, wrap="word", undo=True)
        self.input_text.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=(0, 6))

        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        self.check_button = ttk.Button(input_frame, text="Check Price", command=self._on_check_clicked)
        self.clear_button = ttk.Button(input_frame, text="Clear", command=self._on_clear_clicked)
        self.paste_button = ttk.Button(input_frame, text="Paste", command=self._on_paste_button_clicked)

        self.check_button.grid(row=1, column=0, sticky="w", padx=(0, 4))
        self.clear_button.grid(row=1, column=1, sticky="w", padx=(0, 4))
        self.paste_button.grid(row=1, column=2, sticky="e")

        # --- Item Inspector (right) ---
        self._create_item_inspector(top_row)

    def _create_item_inspector(self, parent: ttk.Frame) -> None:
        """Create the Item Inspector sidebar panel."""
        inspector_frame = ttk.LabelFrame(parent, text="Item Inspector", padding=8)
        inspector_frame.grid(row=0, column=1, sticky="nsew")

        self.item_inspector_text = tk.Text(
            inspector_frame,
            height=8,
            wrap="word",
            state="disabled",
        )
        self.item_inspector_text.grid(row=0, column=0, sticky="nsew")

        inspector_frame.rowconfigure(0, weight=1)
        inspector_frame.columnconfigure(0, weight=1)

    # -------------------------------------------------------------------------
    # Item Inspector
    # -------------------------------------------------------------------------

    def _update_item_inspector(self, item_text: str) -> None:
        """
        Parse the given item text (if a parser is available) and display
        a compact summary in the Item Inspector sidebar.

        If parsing fails, show a small fallback message instead of the
        raw clipboard text.
        """
        if not hasattr(self, "item_inspector_text"):
            return

        item_text = (item_text or "").strip()
        lines: list[str] = []

        parser = getattr(self.app_context, "parser", None)
        parsed = None

        if parser is not None and hasattr(parser, "parse"):
            try:
                parsed = parser.parse(item_text)
            except Exception:
                parsed = None

        if parsed is None:
            # Fallback: no parse – show a helpful note + first line.
            first_line = item_text.splitlines()[0] if item_text else ""
            if parser is None:
                lines.append("Parser: not available.")
            else:
                lines.append("Parser: failed to parse item.")
            if first_line:
                lines.append("")
                lines.append(f"First line: {first_line}")
        else:
            # Parse succeeded – show key fields.
            def get_attr(name: str, default: str = "") -> str:
                val = getattr(parsed, name, default)
                if val is None:
                    return default
                return str(val)

            name = get_attr("name") or get_attr("item_name")
            base = get_attr("base_type") or get_attr("type_line")
            rarity = get_attr("rarity")
            variant = get_attr("variant")
            ilvl = get_attr("item_level") or get_attr("ilvl")
            map_tier = get_attr("map_tier")
            gem_level = get_attr("gem_level")
            quality = get_attr("quality")
            sockets = get_attr("sockets")
            links = get_attr("links")
            influences = getattr(parsed, "influences", None)
            tags = getattr(parsed, "tags", None)

            lines.append(f"Name: {name or '(unknown)'}")
            if base and base != name:
                lines.append(f"Base: {base}")
            if rarity:
                lines.append(f"Rarity: {rarity}")
            if variant:
                lines.append(f"Variant: {variant}")
            if ilvl:
                lines.append(f"Item Level: {ilvl}")
            if map_tier:
                lines.append(f"Map Tier: {map_tier}")
            if gem_level:
                lines.append(f"Gem Level: {gem_level}")
            if quality:
                lines.append(f"Quality: {quality}")
            if sockets or links:
                lines.append(f"Sockets/Links: {sockets or '-'} ({links or '0'}L)")
            if influences:
                lines.append(f"Influences: {influences}")
            if tags:
                lines.append(f"Tags: {tags}")

        text = "\n".join(lines) if lines else "No item loaded."

        self.item_inspector_text.configure(state="normal")
        self.item_inspector_text.delete("1.0", "end")
        self.item_inspector_text.insert("1.0", text)
        self.item_inspector_text.configure(state="disabled")

    def _create_results_area(self) -> None:
        """Create the results frame, filter bar, summary banner, and attach a ResultsTable."""
        results_frame = ttk.LabelFrame(self.main_frame, text="Results", padding=8)
        results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        self.main_frame.rowconfigure(1, weight=1)

        # --- Filter bar (row 0) ---
        filter_frame = ttk.Frame(results_frame)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        filter_label = ttk.Label(filter_frame, text="Filter:")
        filter_label.grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=40)
        self.filter_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        clear_filter_btn = ttk.Button(filter_frame, text="Clear", command=self._on_clear_filter)
        clear_filter_btn.grid(row=0, column=2, sticky="w", padx=(0, 4))

        gear_button = ttk.Button(filter_frame, text="⚙", width=3, command=self._show_column_visibility_dialog)
        gear_button.grid(row=0, column=3, sticky="e")

        source_label = ttk.Label(filter_frame, text="Source:")
        source_label.grid(row=0, column=4, sticky="w", padx=(8, 4))

        self.source_filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.source_filter_var,
            state="readonly",
            width=18,
        )
        self._populate_source_filter_options()
        self.source_filter_combo.grid(row=0, column=5, sticky="w")

        self.source_filter_combo.bind("<<ComboboxSelected>>", self._on_source_filter_change)
        self.filter_entry.bind("<KeyRelease>", self._on_filter_change)

        filter_frame.columnconfigure(1, weight=1)

        # --- Summary banner (row 1) ---
        summary_frame = ttk.Frame(results_frame)
        summary_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        summary_label = ttk.Label(
            summary_frame,
            textvariable=self.summary_var,
            anchor="w",
        )
        summary_label.grid(row=0, column=0, sticky="w")

        # Copy button for summary
        copy_summary_btn = ttk.Button(
            summary_frame,
            text="Copy",
            command=self._copy_last_summary,
            width=8,
        )
        copy_summary_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        summary_frame.columnconfigure(0, weight=1)

        # --- Results table (row 2) ---
        results_table_frame = ttk.Frame(results_frame)
        results_table_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")

        results_frame.rowconfigure(2, weight=1)
        results_frame.columnconfigure(0, weight=1)

        self.results_table = ResultsTable(results_table_frame, RESULT_COLUMNS)
        self.results_tree = self.results_table.tree

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

        self.tree_menu.add_command(
            label="Open in Browser",
            command=self._open_selected_row_trade_url_or_details,
        )
        self.tree_menu.add_command(
            label="View Details...",
            command=self._view_selected_row_details,
        )
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="Copy Row", command=self._copy_selected_row)
        self.tree_menu.add_command(
            label="Copy Row as TSV",
            command=self._copy_selected_row_as_tsv,
        )
        self.tree_menu.add_separator()
        self.tree_menu.add_command(
            label="Record Sale...",
            command=self._record_sale_for_selected_row,
        )

        self.results_tree.bind("<Button-3>", self._on_tree_right_click)
        self.results_tree.bind("<Button-2>", self._on_tree_right_click)  # macOS sometimes uses Button-2
        self.results_tree.bind("<Double-1>", self._on_tree_double_click)

    def _create_bindings(self) -> None:
        self.root.bind("<Control-Return>", self._on_check_clicked)
        self.root.bind("<Control-K>", self._on_clear_clicked)
        self.root.bind("<F5>", self._on_check_clicked)

        self.input_text.bind("<<Paste>>", self._on_paste)

    # -------------------------------------------------------------------------
    # Status helpers
    # -------------------------------------------------------------------------

    def _set_status(self, message: str) -> None:
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

    def _export_results_tsv(self) -> None:
        if not hasattr(self, "results_table"):
            messagebox.showinfo("Export TSV", "No results table is available to export.")
            return

        if not list(self.results_table.iter_rows()):
            if not messagebox.askyesno(
                "Export TSV",
                "There are no results in the table.\n\nExport an empty file anyway?",
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

        if not file_path:
            self._set_status("Export cancelled.")
            return

        try:
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

    def _copy_all_rows_as_tsv(self) -> None:
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

    def _open_path_in_explorer(self, path: Path) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Failed to open path %s: %s", path, exc)
            messagebox.showerror("Error", f"Failed to open path:\n{path}\n\n{exc}")

    def _show_shortcuts(self) -> None:
        messagebox.showinfo(
            "Keyboard Shortcuts",
            (
                "Keyboard & Mouse Shortcuts\n\n"
                "• Ctrl+Enter   – Check prices\n"
                "• F5           – Re-check prices\n"
                "• Ctrl+K       – Clear input and results\n"
                "• Right-click  – Row context menu (Browser / Copy / Details)\n"
                "• Double-click – Open in browser (trade site)\n"
                "• Paste button – Paste item from clipboard and auto-check\n"
            ),
        )

    def _show_usage_tips(self) -> None:
        messagebox.showinfo(
            "Usage Tips",
            (
                "Usage Tips\n\n"
                "• Paste your Path of Exile item text into the input box,\n"
                "  then press Ctrl+Enter or click \"Check Price\".\n\n"
                "• The Results table shows key data like chaos/divine value\n"
                "  and listing counts; click column headers to sort.\n\n"
                "• Use the Filter box and Source dropdown above the results\n"
                "  to narrow down by text and by data source.\n\n"
                "• Right-click a row to:\n"
                "  – Open in Browser\n"
                "  – View Details\n"
                "  – Copy Row\n"
                "  – Copy Row as TSV\n\n"
                "• File → Open Log File / Config Folder\n"
                "  Quick access for debugging and configuration.\n\n"
                "• File → Export TSV...\n"
                "  Save all current results to a .tsv file with headers.\n\n"
                "• View → Session History...\n"
                "  View and restore previous price checks from this session.\n\n"
                "• View → Data Sources...\n"
                "  Enable or disable specific price sources.\n\n"
                "• View → Recent Sales…, Sales Dashboard…\n"
                "  Inspect recorded sales and daily performance.\n\n"
                "• Dev → Paste Sample ...\n"
                "  Quickly load example items (map, currency, unique, etc.) for testing.\n"
            ),
        )

    def _show_about_dialog(self) -> None:
        messagebox.showinfo(
            "About PoE Price Checker",
            "PoE Price Checker\n\n"
            "GUI front-end for Path of Exile item price checks.\n"
            "Multi-source, with history, aggregates, and dev tools.",
        )

    # -------------------------------------------------------------------------
    # Input / action handlers
    # -------------------------------------------------------------------------

    def _get_input_text(self) -> str:
        return self.input_text.get("1.0", "end").strip()

    def _record_sale_for_selected_row(self) -> None:
        """Open dialog to record a sale for the selected row."""
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("No item selected", "Please select a row first.")
            return

        # Map row tuple -> dict using current columns
        if hasattr(self, "results_table"):
            columns = self.results_table.columns
        else:
            columns = RESULT_COLUMNS

        data: dict[str, Any] = {}
        for col, val in zip(columns, row):
            data[col] = val

        item_name = str(data.get("item_name", "") or "")
        source = str(data.get("source", "") or "")
        chaos_raw = data.get("chaos_value", "")

        try:
            default_chaos = float(chaos_raw or 0.0)
        except (TypeError, ValueError):
            default_chaos = 0.0

        def on_submit(final_chaos: float, notes: str | None) -> None:
            """Callback when the dialog is submitted."""
            self._save_sale(
                item_name=item_name,
                source=source,
                chaos_value=final_chaos,
                notes=notes,
            )

        RecordSaleDialog(
            parent=self.root,
            item_name=item_name,
            source=source,
            default_chaos_value=default_chaos,
            on_submit=on_submit,
        )

    def _save_sale(self, item_name: str, source: str, chaos_value: float, notes: str | None) -> None:
        """
        Persist a sale via the Database helper and update the status bar.
        """
        db = self.ctx.db
        try:
            sale_id = db.record_instant_sale(
                item_name=item_name,
                source=source,
                price_chaos=chaos_value,
                notes=notes,
            )
        except Exception as exc:
            self.logger.exception("Failed to record sale for %s: %s", item_name, exc)
            messagebox.showerror(
                "Record Sale",
                f"Failed to record sale for {item_name!r}:\n{exc}",
            )
            return

        self._set_status(
            f"Recorded sale #{sale_id} for {item_name!r} at {chaos_value:.1f} chaos."
        )

    def _on_check_clicked(self, event: tk.Event | None = None) -> None:  # type: ignore[override]
        del event
        if self._check_in_progress:
            self._set_status("Price check already in progress...")
            return

        text = self._get_input_text()
        if not text:
            self._set_status("No item text to check.")
            return

        self._set_status("Checking prices...")
        self._check_in_progress = True
        self.root.after(10, self._run_price_check)

    def _run_price_check(self) -> None:
        try:
            text = self._get_input_text()
            if not text:
                self._set_status("No item text to check.")
                return

            # Update the item inspector before we potentially clear input.
            self._update_item_inspector(text)

            price_service = getattr(self.app_context, "price_service", None)
            if price_service is None:
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
                    ],
                    input_text=text,
                )
                self._set_status("price_service not configured; showing dummy result.")
                return

            try:
                results = price_service.check_item(text)  # type: ignore[call-arg]
            except Exception as exc:  # pragma: no cover
                self.logger.exception("Error during price check: %s", exc)
                messagebox.showerror("Error", f"An error occurred while checking prices:\n{exc}")
                self._set_status("Error during price check.")
                return

            self._clear_results()
            self._insert_result_rows(results, input_text=text)
        finally:
            self._check_in_progress = False

    def _build_aggregate_rows_for_check(
        self,
        rows: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build synthetic 'aggregate' rows per logical item across sources.

        Grouping key: (item_name, variant, links)
        """
        if not rows:
            return []

        grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}

        for row in rows:
            name = str(row.get("item_name", "") or "")
            variant = str(row.get("variant", "") or "")
            links = str(row.get("links", "") or "")
            key = (name, variant, links)
            grouped.setdefault(key, []).append(row)

        aggregates: list[dict[str, Any]] = []

        for (name, variant, links), group_rows in grouped.items():
            chaos_vals: list[float] = []
            divine_vals: list[float] = []
            listing_counts: list[int] = []

            for r in group_rows:
                try:
                    cv = float(r.get("chaos_value", 0) or 0)
                    chaos_vals.append(cv)
                except (TypeError, ValueError):
                    pass

                try:
                    dv = float(r.get("divine_value", 0) or 0)
                    divine_vals.append(dv)
                except (TypeError, ValueError):
                    pass

                try:
                    lc = int(r.get("listing_count", 0) or 0)
                    listing_counts.append(lc)
                except (TypeError, ValueError):
                    pass

            def mean(xs: list[float]) -> float:
                return sum(xs) / len(xs) if xs else 0.0

            chaos_avg = mean(chaos_vals)
            divine_avg = mean(divine_vals)
            total_listings = sum(listing_counts) if listing_counts else 0

            agg_row: dict[str, Any] = {
                "item_name": name,
                "variant": variant,
                "links": links,
                "chaos_value": chaos_avg,
                "divine_value": divine_avg,
                "listing_count": total_listings,
                "source": "aggregate",
            }

            aggregates.append(agg_row)

        return aggregates

    def _insert_result_rows(
        self,
        rows: Iterable[Mapping[str, Any] | Any],
        *,
        input_text: str | None = None,
    ) -> None:
        """
        Insert rows into the results table.

        - Normalizes incoming rows to dicts with RESULT_COLUMNS keys.
        - Builds synthetic 'aggregate' rows per logical item across sources.
        - Prepends new rows (aggregate + per-source) to the backing store.
        - Re-applies any active filters.
        - Adds an entry to session history.
        """
        if not hasattr(self, "results_table"):
            return

        # Normalize incoming rows
        canonical_rows: list[Mapping[str, Any]] = []
        for row in rows:
            if isinstance(row, Mapping):
                canonical_rows.append({col: row.get(col, "") for col in RESULT_COLUMNS})
            else:
                canonical_rows.append({col: getattr(row, col, "") for col in RESULT_COLUMNS})

        # Aggregate rows for this check
        aggregate_rows = self._build_aggregate_rows_for_check(canonical_rows)
        this_check_rows: list[Mapping[str, Any]] = aggregate_rows + canonical_rows

        # Prepend to backing store
        existing = getattr(self, "_all_result_rows", [])
        self._all_result_rows = this_check_rows + list(existing)

        # Update the summary banner for this check
        self._update_summary_banner(aggregate_rows, canonical_rows)

        # Re-apply active filters
        active_text_filter = (self.filter_var.get() or "").strip()
        self._apply_filter(active_text_filter)

        # Update status
        total_rows = sum(1 for _ in self.results_table.iter_rows())
        self._set_status(f"Price check complete. {total_rows} row(s).")

        # Add to history using only the per-source rows
        self._add_history_entry(canonical_rows, input_text=input_text)

    def _clear_results(self) -> None:
        if hasattr(self, "results_table"):
            self.results_table.clear()
        self._all_result_rows = []
        if hasattr(self, "summary_var"):
            self.summary_var.set("No recent price summary.")

    def _on_clear_clicked(self, event: tk.Event | None = None) -> None:  # type: ignore[override]
        del event
        self.input_text.delete("1.0", "end")
        self._clear_results()
        self._update_item_inspector("")
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
        del event
        self.root.after(10, self._auto_check_if_not_empty)  # type: ignore[arg-type]

    def _auto_check_if_not_empty(self) -> None:
        if self._get_input_text():
            self._on_check_clicked()

    def _paste_sample_item(self, category: str) -> None:
        key = (category or "").lower()
        items = SAMPLE_ITEMS.get(key)

        if not items:
            messagebox.showinfo(
                "Sample Item",
                f"No sample items are defined for category '{category}'.",
            )
            return

        sample_text = random.choice(items)

        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", sample_text)

        self._auto_check_if_not_empty()
        self._set_status(f"Pasted sample {category} item and started price check.")

    # -------------------------------------------------------------------------
    # Summary banner
    # -------------------------------------------------------------------------

    def _update_summary_banner(
        self,
        aggregate_rows: list[Mapping[str, Any]],
        per_source_rows: list[Mapping[str, Any]],
    ) -> None:
        """
        Compute a one-line summary for the most recent price check and
        update the summary_var used by the banner above the table.
        """
        if not hasattr(self, "summary_var"):
            return

        if not aggregate_rows and not per_source_rows:
            self.summary_var.set("No recent price summary.")
            return

        # Prefer an aggregate row if available; otherwise fall back to the first per-source row.
        row: Mapping[str, Any] | None = None
        if aggregate_rows:
            row = aggregate_rows[0]
        elif per_source_rows:
            row = per_source_rows[0]

        if row is None:
            self.summary_var.set("No recent price summary.")
            return

        name = str(row.get("item_name", "") or "Unknown Item")
        variant = str(row.get("variant", "") or "").strip()
        links = str(row.get("links", "") or "").strip()

        def as_float(value: Any) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        chaos = as_float(row.get("chaos_value", 0))
        divine = as_float(row.get("divine_value", 0))
        try:
            listings = int(row.get("listing_count", 0) or 0)
        except (TypeError, ValueError):
            listings = 0

        # Compute which sources participated.
        source_names = sorted(
            {
                str(r.get("source", "") or "")
                for r in per_source_rows
                if (r.get("source", "") or "") != "aggregate"
            }
        )
        source_names = [s for s in source_names if s]

        # Build a concise human-readable label
        parts: list[str] = []

        base_label = name
        detail_bits: list[str] = []
        if links:
            detail_bits.append(f"{links}L")
        if variant:
            detail_bits.append(variant)
        if detail_bits:
            base_label += " (" + ", ".join(detail_bits) + ")"
        parts.append(base_label)

        if chaos or divine:
            parts.append(f"– {chaos:.1f}c")
            if divine:
                parts[-1] += f" ({divine:.2f}d)"
        if listings:
            parts.append(f"{listings} listing(s) total")

        if source_names:
            parts.append("sources: " + ", ".join(source_names))

        summary_text = " ".join(parts) if parts else "No recent price summary."
        self.summary_var.set(summary_text)

    # -------------------------------------------------------------------------
    # Filtering helpers
    # -------------------------------------------------------------------------

    def _populate_source_filter_options(self) -> None:
        values: list[str] = ["All sources"]

        service = getattr(self.app_context, "price_service", None)
        if service is not None and hasattr(service, "get_enabled_state"):
            try:
                state = service.get_enabled_state()
                names = sorted(state.keys())
                values.extend(names)
            except Exception:
                pass

        if hasattr(self, "source_filter_combo"):
            self.source_filter_combo["values"] = values

        self.source_filter_var.set("All sources")
        self._source_filter_value = None

    def _on_filter_change(self, event: tk.Event | None = None) -> None:
        del event
        text = self.filter_var.get()
        self._apply_filter(text)

    def _on_clear_filter(self) -> None:
        self.filter_var.set("")
        self.source_filter_var.set("All sources")
        self._source_filter_value = None
        self._apply_filter("")

    def _on_source_filter_change(self, event: tk.Event | None = None) -> None:
        del event
        selected = (self.source_filter_var.get() or "").strip()
        if not selected or selected == "All sources":
            self._source_filter_value = None
        else:
            self._source_filter_value = selected
        self._apply_filter(self.filter_var.get())

    def _apply_filter(self, filter_text: str) -> None:
        if not hasattr(self, "results_table"):
            return

        text = (filter_text or "").strip().lower()

        if not self._all_result_rows:
            self.results_table.clear()
            self._set_status("No results to filter.")
            return

        if not text and self._source_filter_value is None:
            rows_to_show = self._all_result_rows
        else:
            rows_to_show = [
                row
                for row in self._all_result_rows
                if self._row_matches_filter(row, text)
                and self._row_matches_source_filter(row)
            ]

        self.results_table.clear()
        self.results_table.insert_rows(rows_to_show)

        total_rows = sum(1 for _ in self.results_table.iter_rows())
        any_filter = bool(text or self._source_filter_value)
        if any_filter:
            self._set_status(f"Filter applied ({total_rows} row(s) match).")
        else:
            self._set_status(f"Filter cleared. {total_rows} row(s).")

    def _row_matches_filter(self, row: Mapping[str, Any] | Any, text: str) -> bool:
        if not text:
            return True

        for col in RESULT_COLUMNS:
            if isinstance(row, Mapping):
                val = row.get(col, "")
            else:
                val = getattr(row, col, "")
            s = "" if val is None else str(val)
            if text in s.lower():
                return True
        return False

    def _row_matches_source_filter(self, row: Mapping[str, Any] | Any) -> bool:
        if not self._source_filter_value:
            return True

        target = self._source_filter_value.lower()

        if isinstance(row, Mapping):
            val = row.get("source", "")
        else:
            val = getattr(row, "source", "")

        s = "" if val is None else str(val).lower()
        return s == target

    # -------------------------------------------------------------------------
    # Column visibility dialog
    # -------------------------------------------------------------------------

    def _show_column_visibility_dialog(self) -> None:
        if self._column_visibility_window is not None:
            try:
                if self._column_visibility_window.winfo_exists():
                    self._column_visibility_window.lift()
                    return
            except tk.TclError:
                pass

        win = tk.Toplevel(self.root)
        win.title("Column Visibility")
        win.transient(self.root)
        win.resizable(False, False)

        self._column_visibility_window = win
        self._column_visibility_vars = {}

        ttk.Label(win, text="Show / hide columns:").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4)
        )

        current_visibility: dict[str, bool] = {}
        for col in RESULT_COLUMNS:
            info = self.results_tree.column(col)
            try:
                width = int(info.get("width", 0))
                minwidth = int(info.get("minwidth", 0))
            except (ValueError, TypeError):
                width = 0
                minwidth = 0
            visible = not (width == 0 and minwidth == 0)
            current_visibility[col] = visible

        for row_index, col in enumerate(RESULT_COLUMNS, start=1):
            label = col.replace("_", " ").title()
            var = tk.BooleanVar(value=current_visibility.get(col, True))
            self._column_visibility_vars[col] = var
            chk = ttk.Checkbutton(win, text=label, variable=var)
            chk.grid(row=row_index, column=0, columnspan=3, sticky="w", padx=12, pady=2)

        btn_frame = ttk.Frame(win)
        btn_frame.grid(row=len(RESULT_COLUMNS) + 1, column=0, columnspan=3, pady=(8, 8), padx=8, sticky="e")

        select_all_btn = ttk.Button(btn_frame, text="Select All", command=self._columns_select_all)
        select_all_btn.grid(row=0, column=0, padx=(0, 4))

        select_none_btn = ttk.Button(btn_frame, text="Select None", command=self._columns_select_none)
        select_none_btn.grid(row=0, column=1, padx=(0, 4))

        apply_btn = ttk.Button(btn_frame, text="Apply", command=self._columns_apply_visibility)
        apply_btn.grid(row=0, column=2, padx=(0, 4))

        close_btn = ttk.Button(btn_frame, text="Close", command=win.destroy)
        close_btn.grid(row=0, column=3)

        win.columnconfigure(0, weight=1)

    def _columns_select_all(self) -> None:
        for var in self._column_visibility_vars.values():
            var.set(True)

    def _columns_select_none(self) -> None:
        for var in self._column_visibility_vars.values():
            var.set(False)

    def _columns_apply_visibility(self) -> None:
        if not hasattr(self, "results_table"):
            return

        visibility: dict[str, bool] = {
            col: var.get() for col, var in self._column_visibility_vars.items()
        }

        self.results_table.set_column_visibility(visibility)
        visible_count = sum(1 for v in visibility.values() if v)
        total = len(visibility)
        self._set_status(f"Updated column visibility: {visible_count}/{total} visible.")

    # -------------------------------------------------------------------------
    # Data sources dialog
    # -------------------------------------------------------------------------

    def _show_sources_dialog(self) -> None:
        service = getattr(self.app_context, "price_service", None)
        if service is None or not hasattr(service, "get_enabled_state"):
            messagebox.showinfo(
                "Data Sources",
                "The current price service does not support source toggling.",
            )
            return

        if self._sources_window is not None:
            try:
                if self._sources_window.winfo_exists():
                    self._sources_window.lift()
                    return
            except tk.TclError:
                self._sources_window = None

        state = service.get_enabled_state()
        if not state:
            messagebox.showinfo("Data Sources", "No data sources are configured.")
            return

        win = tk.Toplevel(self.root)
        win.title("Data Sources")
        win.transient(self.root)
        win.resizable(False, False)

        self._sources_window = win
        self._source_vars = {}

        ttk.Label(
            win,
            text="Enable or disable data sources for price checks:",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))

        for idx, (name, enabled) in enumerate(state.items(), start=1):
            var = tk.BooleanVar(value=enabled)
            self._source_vars[name] = var
            chk = ttk.Checkbutton(win, text=name, variable=var)
            chk.grid(row=idx, column=0, columnspan=3, sticky="w", padx=12, pady=2)

        btn_frame = ttk.Frame(win)
        btn_frame.grid(
            row=len(state) + 1,
            column=0,
            columnspan=3,
            pady=(8, 8),
            padx=8,
            sticky="e",
        )

        select_all_btn = ttk.Button(btn_frame, text="Select All", command=self._sources_select_all)
        select_all_btn.grid(row=0, column=0, padx=(0, 4))

        select_none_btn = ttk.Button(btn_frame, text="Select None", command=self._sources_select_none)
        select_none_btn.grid(row=0, column=1, padx=(0, 4))

        apply_btn = ttk.Button(btn_frame, text="Apply", command=self._sources_apply_visibility)
        apply_btn.grid(row=0, column=2, padx=(0, 4))

        close_btn = ttk.Button(btn_frame, text="Close", command=win.destroy)
        close_btn.grid(row=0, column=3)

        win.columnconfigure(0, weight=1)

    def _sources_select_all(self) -> None:
        for var in self._source_vars.values():
            var.set(True)

    def _sources_select_none(self) -> None:
        for var in self._source_vars.values():
            var.set(False)

    def _sources_apply_visibility(self) -> None:
        service = getattr(self.app_context, "price_service", None)
        if service is None or not hasattr(service, "set_enabled_state"):
            return

        enabled_state = {name: var.get() for name, var in self._source_vars.items()}
        service.set_enabled_state(enabled_state)

        enabled_count = sum(1 for v in enabled_state.values() if v)
        total = len(enabled_state)
        self._set_status(f"Updated data sources: {enabled_count}/{total} enabled.")
        self._populate_source_filter_options()

    # -------------------------------------------------------------------------
    # Treeview helpers (used by tests)
    # -------------------------------------------------------------------------

    def _get_tree(self) -> Any:
        tree = getattr(self, "tree", None)
        if tree is not None:
            return tree
        return getattr(self, "results_tree", None)

    def _get_selected_row(self) -> tuple[Any, ...]:
        if hasattr(self, "results_table"):
            tree = self._get_tree()
            if tree is self.results_table.tree:
                return self.results_table.get_selected_row_values()

        tree = self._get_tree()
        if tree is None:
            return ()

        selection = tree.selection()
        if not selection:
            return ()

        item_id = selection[0]
        values = tree.item(item_id, "values")
        return tuple(values)

    def _get_selected_row_values(self) -> tuple[str, ...] | None:
        """
        Return the values tuple for the first selected row, or None if
        nothing is selected. (Used by some tests.)
        """
        tree = getattr(self, "results_tree", None)
        if tree is None:
            return None

        selection = tree.selection()
        if not selection:
            return None

        row_id = selection[0]
        values = tree.item(row_id, "values")  # type: ignore[no-any-return]
        return tuple(values) if values is not None else None

    def _copy_row_tsv(self) -> None:
        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected to copy.")
            return

        line = "\t".join(str(v) for v in row)

        copy_fn = getattr(self, "_copy_to_clipboard", None)
        if callable(copy_fn):
            copy_fn(line)
        else:
            self._set_clipboard(line)

        self._set_status("Row copied as TSV to clipboard.")

    # -------------------------------------------------------------------------
    # Treeview context menu / details / copy helpers
    # -------------------------------------------------------------------------

    def _on_tree_right_click(self, event: tk.Event) -> None:
        region = self.results_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.results_tree.identify_row(event.y)
        if not row_id:
            return

        if row_id not in self.results_tree.selection():
            self.results_tree.selection_set(row_id)

        try:
            self.tree_menu.tk_popup(event.x_root, event.y_root)
        finally:  # pragma: no cover
            self.tree_menu.grab_release()

    def _on_tree_double_click(self, event: tk.Event) -> None:
        region = self.results_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.results_tree.identify_row(event.y)
        if not row_id:
            return

        if row_id not in self.results_tree.selection():
            self.results_tree.selection_set(row_id)

        self._open_selected_row_trade_url_or_details()

    def _open_selected_row_trade_url_or_details(self) -> None:
        """
        Attempt to open a trade URL for the selected row in the default browser.

        - If the row has a 'trade_url' field, open it directly.
        - Otherwise, open the generic trade search page for the current league.
        - On any failure, fall back to showing the item details dialog.
        """
        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected.")
            messagebox.showinfo("Item Details", "No row is currently selected.")
            return

        if hasattr(self, "results_table"):
            columns = self.results_table.columns
        else:
            columns = RESULT_COLUMNS

        data: dict[str, Any] = {}
        for col, val in zip(columns, row):
            data[col] = val

        item_name = str(data.get("item_name", "") or "").strip()
        source_name = str(data.get("source", "") or "").strip()
        trade_url = str(data.get("trade_url", "") or "").strip() if "trade_url" in data else ""

        league = ""
        try:
            cfg = getattr(self.app_context, "config", None)
            if cfg is not None:
                game = cfg.current_game
                game_cfg = cfg.get_game_config(game)
                league = getattr(game_cfg, "league", "") or ""
        except Exception:
            league = ""

        try:
            if trade_url:
                url = trade_url
            else:
                base_url = "https://www.pathofexile.com/trade/search"
                if league:
                    url = f"{base_url}/{league}"
                else:
                    url = base_url

            webbrowser.open_new_tab(url)

            if trade_url and item_name:
                self._set_status(f"Opened trade listing for '{item_name}' ({source_name or 'trade'}).")
            elif trade_url:
                self._set_status("Opened trade listing.")
            elif item_name:
                self._set_status(f"Opened trade search page for league '{league or 'unknown'}'.")
            else:
                self._set_status("Opened trade search page.")
        except Exception:
            self._view_selected_row_details()

    def _view_selected_row_details(self, event: tk.Event | None = None) -> None:
        del event

        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected.")
            messagebox.showinfo("Item Details", "No row is currently selected.")
            return

        if hasattr(self, "results_table"):
            columns = self.results_table.columns
        else:
            columns = RESULT_COLUMNS

        lines: list[str] = []
        for col, val in zip(columns, row):
            label = col.replace("_", " ").title()
            lines.append(f"{label}: {val}")

        if not lines:
            messagebox.showinfo("Item Details", "No data for the selected row.")
            return

        messagebox.showinfo("Item Details", "\n".join(lines))

    def _copy_last_summary(self) -> None:
        """
        Copy the most recent price summary line to the clipboard.
        """
        text = (self.summary_var.get() or "").strip()
        if not text or text == "No recent price summary.":
            self._set_status("No price summary to copy.")
            return

        self._set_clipboard(text)
        self._set_status("Last price summary copied to clipboard.")

    def _copy_selected_row(self) -> None:
        row = self._get_selected_row()
        if not row:
            self._set_status("No row selected to copy.")
            return

        text = " ".join(str(v) for v in row)
        self._set_clipboard(text)
        self._set_status("Row copied to clipboard.")

    def _copy_selected_row_as_tsv(self) -> None:
        self._copy_row_tsv()

    def _set_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

    # -------------------------------------------------------------------------
    # Session history
    # -------------------------------------------------------------------------

    def _add_history_entry(
        self,
        rows: list[Mapping[str, Any]],
        input_text: str | None = None,
    ) -> None:
        """
        Add a new history entry for the latest price check.

        If input_text is not provided, fall back to reading from the input widget.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if input_text is None:
            try:
                input_text = self._get_input_text()
            except Exception:
                input_text = ""

        summary = self._build_history_summary(rows)
        self._history.append(
            {
                "timestamp": timestamp,
                "summary": summary,
                "rows": rows,
                "input_text": input_text,
            }
        )

        if self._history_window is not None and self._history_listbox is not None:
            try:
                if self._history_window.winfo_exists():
                    self._refresh_history_listbox()
            except tk.TclError:
                pass

    def _build_history_summary(self, rows: list[Mapping[str, Any]]) -> str:
        if not rows:
            return "No results"

        first = rows[0]
        name = str(first.get("item_name", "") or "Unknown Item")
        chaos = str(first.get("chaos_value", "") or "0")
        count = len(rows)
        return f"{name} ({count} row(s), {chaos}c)"

    def _show_history_window(self) -> None:
        if self._history_window is not None:
            try:
                if self._history_window.winfo_exists():
                    self._history_window.lift()
                    return
            except tk.TclError:
                pass

        win = tk.Toplevel(self.root)
        win.title("Session History")
        win.transient(self.root)
        win.geometry("500x300")

        self._history_window = win

        label = ttk.Label(win, text="Previous price checks (this session):")
        label.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 4))

        self._history_listbox = tk.Listbox(win, height=10)
        self._history_listbox.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=8)

        scrollbar = ttk.Scrollbar(win, orient="vertical", command=self._history_listbox.yview)
        scrollbar.grid(row=1, column=4, sticky="ns")
        self._history_listbox.configure(yscrollcommand=scrollbar.set)

        win.rowconfigure(1, weight=1)
        win.columnconfigure(0, weight=1)

        btn_frame = ttk.Frame(win)
        btn_frame.grid(row=2, column=0, columnspan=5, pady=(8, 8), padx=8, sticky="e")

        load_input_btn = ttk.Button(btn_frame, text="Load Input", command=self._history_load_input)
        load_input_btn.grid(row=0, column=0, padx=(0, 4))

        restore_results_btn = ttk.Button(btn_frame, text="Restore Results", command=self._history_restore_results)
        restore_results_btn.grid(row=0, column=1, padx=(0, 4))

        clear_btn = ttk.Button(btn_frame, text="Clear History", command=self._history_clear)
        clear_btn.grid(row=0, column=2, padx=(0, 4))

        close_btn = ttk.Button(btn_frame, text="Close", command=win.destroy)
        close_btn.grid(row=0, column=3)

        self._refresh_history_listbox()

    def _refresh_history_listbox(self) -> None:
        if self._history_listbox is None:
            return

        self._history_listbox.delete(0, "end")
        for idx, entry in enumerate(self._history, start=1):
            ts = entry.get("timestamp", "")
            summary = entry.get("summary", "")
            label = f"{idx}. [{ts}] {summary}"
            self._history_listbox.insert("end", label)

    def _get_selected_history_index(self) -> int | None:
        if self._history_listbox is None:
            return None
        selection = self._history_listbox.curselection()
        if not selection:
            return None
        return int(selection[0])

    def _history_load_input(self) -> None:
        idx = self._get_selected_history_index()
        if idx is None:
            messagebox.showinfo("Session History", "No history entry selected.")
            return

        entry = self._history[idx]
        text = entry.get("input_text", "") or ""

        self.input_text.delete("1.0", "end")
        self.input_text.insert("1.0", text)
        self._set_status("Loaded input from history (no price check run yet).")

    def _history_restore_results(self) -> None:
        if not hasattr(self, "results_table"):
            return

        idx = self._get_selected_history_index()
        if idx is None:
            messagebox.showinfo("Session History", "No history entry selected.")
            return

        entry = self._history[idx]
        rows = entry.get("rows", []) or []

        if not isinstance(rows, list):
            rows = []

        self._all_result_rows = rows
        self.results_table.clear()
        self.results_table.insert_rows(rows)

        total = sum(1 for _ in self.results_table.iter_rows())
        self._set_status(f"Restored {total} row(s) from history.")

    def _history_clear(self) -> None:
        self._history.clear()
        if self._history_listbox is not None:
            self._history_listbox.delete(0, "end")
        self._set_status("History cleared.")

    # -------------------------------------------------------------------------
    # Convenience entrypoint
    # -------------------------------------------------------------------------


def run(app_context: Any) -> None:
    """
    Convenience function to run the GUI directly.
    """
    root = tk.Tk()
    root.withdraw()
    gui = PriceCheckerGUI(root, app_context)
    root.deiconify()
    root.mainloop()
