from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database import Database


class RecentSalesWindow(tk.Toplevel):
    """Panel showing recent sales with search, filtering, and sorting."""

    def __init__(
        self,
        master: tk.Misc,
        db: Database,
        *,
        limit: int = 50,
    ) -> None:
        super().__init__(master)

        self.db = db
        self.limit = limit

        # Data caches
        self._all_rows: List[Dict[str, Any]] = []
        self._filtered_rows: List[Dict[str, Any]] = []
        self._iid_to_row: Dict[str, Dict[str, Any]] = {}

        # Sorting state
        self._sort_column: str = "sold_at"
        self._sort_reverse: bool = True  # newest first by default

        self.title("Recent Sales")
        self.transient(master)
        self.resizable(True, True)

        self._create_widgets()
        self._layout_widgets()
        self._load_sales_from_db()

        # Center over parent
        self.update_idletasks()
        self._center_over_parent()

        # Key bindings
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", self._open_selected_sale_details_from_key)

    # ------------------------------------------------------------------ UI creation

    def _create_widgets(self) -> None:
        # --- Top toolbar: Refresh + Limit ---
        self.toolbar = ttk.Frame(self)

        self.refresh_button = ttk.Button(
            self.toolbar,
            text="Refresh",
            command=self._load_sales_from_db,
        )

        self.limit_label = ttk.Label(self.toolbar, text="Limit:")
        self.limit_var = tk.IntVar(value=self.limit)
        self.limit_spin = ttk.Spinbox(
            self.toolbar,
            from_=10,
            to=500,
            increment=10,
            textvariable=self.limit_var,
            width=5,
            command=self._on_limit_changed,
        )

        # --- Filter bar: search + source filter ---
        self.filter_bar = ttk.Frame(self)

        self.search_label = ttk.Label(self.filter_bar, text="Search:")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.filter_bar, textvariable=self.search_var)
        self.search_entry.bind("<KeyRelease>", self._on_filter_changed)

        self.source_label = ttk.Label(self.filter_bar, text="Source:")
        self.source_var = tk.StringVar(value="All Sources")
        self.source_combo = ttk.Combobox(
            self.filter_bar,
            textvariable=self.source_var,
            state="readonly",
            width=20,
            values=["All Sources"],
        )
        self.source_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # --- Treeview with scrollbar ---
        columns = ("sold_at", "item_name", "source", "price_chaos", "notes")

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=20,
        )

        self.tree.heading("sold_at", text="Sold At", command=lambda: self._on_heading_click("sold_at"))
        self.tree.heading("item_name", text="Item", command=lambda: self._on_heading_click("item_name"))
        self.tree.heading("source", text="Source", command=lambda: self._on_heading_click("source"))
        self.tree.heading("price_chaos", text="Price (c)", command=lambda: self._on_heading_click("price_chaos"))
        self.tree.heading("notes", text="Notes", command=lambda: self._on_heading_click("notes"))

        self.tree.column("sold_at", width=140, anchor="w")
        self.tree.column("item_name", width=220, anchor="w")
        self.tree.column("source", width=120, anchor="w")
        self.tree.column("price_chaos", width=80, anchor="e")
        self.tree.column("notes", width=260, anchor="w")

        self.scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)

        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _layout_widgets(self) -> None:
        # Toolbar row
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))
        self.toolbar.columnconfigure(0, weight=0)
        self.toolbar.columnconfigure(1, weight=0)
        self.toolbar.columnconfigure(2, weight=0)
        self.toolbar.columnconfigure(3, weight=1)

        self.refresh_button.grid(row=0, column=0, padx=(0, 8))
        self.limit_label.grid(row=0, column=1, padx=(0, 4))
        self.limit_spin.grid(row=0, column=2, padx=(0, 4))

        # Filter bar row
        self.filter_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 4))
        self.filter_bar.columnconfigure(1, weight=1)

        self.search_label.grid(row=0, column=0, padx=(0, 4))
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.source_label.grid(row=0, column=2, padx=(0, 4))
        self.source_combo.grid(row=0, column=3, padx=(0, 0))

        # Tree row
        self.tree.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self.scrollbar_y.grid(row=2, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ Data loading & filtering

    def _on_limit_changed(self) -> None:
        try:
            value = int(self.limit_var.get())
        except (TypeError, ValueError):
            return
        if value <= 0:
            return
        self.limit = value
        self._load_sales_from_db()

    def _load_sales_from_db(self) -> None:
        """Load rows from the database, refresh source list, and apply filters."""
        try:
            rows = self.db.get_recent_sales(limit=self.limit)
        except Exception as exc:  # pragma: no cover - defensive
            messagebox.showerror("Database Error", f"Failed to load recent sales:\n{exc}")
            return

        # Normalize to plain dicts and cache a parsed datetime for sorting
        normalized: List[Dict[str, Any]] = []
        for r in rows:
            row_dict = dict(r)
            row_dict["_sold_at_dt"] = self._parse_dt(row_dict.get("sold_at"))
            normalized.append(row_dict)

        self._all_rows = normalized

        # Update source dropdown
        sources = sorted(
            {str(r.get("source") or "").strip() for r in self._all_rows if (r.get("source") or "").strip()}
        )
        values = ["All Sources"]
        values.extend(sources)
        self.source_combo["values"] = values
        if self.source_var.get() not in values:
            self.source_var.set("All Sources")

        self._apply_filters_and_sort()

    def _on_filter_changed(self, _event: tk.Event | None = None) -> None:
        self._apply_filters_and_sort()

    def _apply_filters_and_sort(self) -> None:
        """Apply search + source filters, then sort, then repopulate the tree."""
        search_text = self.search_var.get().strip().lower()
        source_filter = self.source_var.get()

        # Filter rows
        filtered: List[Dict[str, Any]] = []
        for row in self._all_rows:
            # Source filter
            if source_filter and source_filter != "All Sources":
                if str(row.get("source") or "") != source_filter:
                    continue

            # Search filter
            if search_text:
                haystack = " ".join(
                    [
                        str(row.get("item_name") or ""),
                        str(row.get("source") or ""),
                        str(row.get("notes") or ""),
                    ]
                ).lower()
                if search_text not in haystack:
                    continue

            filtered.append(row)

        # Sort
        key_func = self._get_sort_key(self._sort_column)
        filtered.sort(key=key_func, reverse=self._sort_reverse)

        self._filtered_rows = filtered
        self._populate_tree_from_rows(filtered)

    # ------------------------------------------------------------------ Sorting

    def _on_heading_click(self, column: str) -> None:
        """Toggle or set sort state when a column header is clicked."""
        if self._sort_column == column:
            # Toggle direction
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            # Default: descending for sold_at and price, ascending otherwise
            if column in {"sold_at", "price_chaos"}:
                self._sort_reverse = True
            else:
                self._sort_reverse = False

        self._apply_filters_and_sort()

    def _get_sort_key(self, column: str):
        def key(row: Dict[str, Any]) -> Any:
            if column == "sold_at":
                return row.get("_sold_at_dt") or datetime.min
            if column == "price_chaos":
                try:
                    return float(row.get("price_chaos") or 0.0)
                except (TypeError, ValueError):
                    return 0.0
            # textual columns
            value = row.get(column, "")
            return str(value).lower()

        return key

    # ------------------------------------------------------------------ Tree population

    def _populate_tree_from_rows(self, rows: List[Dict[str, Any]]) -> None:
        # Clear existing
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self._iid_to_row.clear()

        # Insert rows
        for row in rows:
            sold_at = self._format_dt(row.get("sold_at"))
            item_name = row.get("item_name") or ""
            source = row.get("source") or ""
            price_chaos = row.get("price_chaos")
            notes = row.get("notes") or ""

            price_str = "" if price_chaos is None else str(price_chaos)

            iid = self.tree.insert(
                "",
                "end",
                values=(sold_at, item_name, source, price_str, notes),
            )
            self._iid_to_row[iid] = row

    # ------------------------------------------------------------------ Details view

    def _on_tree_double_click(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if not item:
            return
        row = self._iid_to_row.get(item)
        if row is None:
            return
        self._show_sale_details(row)

    def _open_selected_sale_details_from_key(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        row = self._iid_to_row.get(item)
        if row is None:
            return
        self._show_sale_details(row)

    def _show_sale_details(self, row: Dict[str, Any]) -> None:
        """Open a small dialog showing full details for the selected sale."""
        dialog = tk.Toplevel(self)
        dialog.title("Sale Details")
        dialog.transient(self)
        dialog.resizable(False, False)

        # Info rows
        def add_row(parent: tk.Widget, label_text: str, value_text: str, row_idx: int) -> None:
            lbl = ttk.Label(parent, text=label_text + ":", anchor="w")
            lbl.grid(row=row_idx, column=0, sticky="w", padx=(8, 4), pady=(4, 0))
            val = ttk.Label(parent, text=value_text, anchor="w", wraplength=400, justify="left")
            val.grid(row=row_idx, column=1, sticky="w", padx=(0, 8), pady=(4, 0))

        content = ttk.Frame(dialog)
        content.grid(row=0, column=0, sticky="nsew")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        add_row(content, "ID", str(row.get("id", "")))
        add_row(content, "Item", str(row.get("item_name", "")))
        add_row(content, "Source", str(row.get("source", "")))
        add_row(content, "Sold At", self._format_dt(row.get("sold_at")))
        add_row(content, "Listed At", self._format_dt(row.get("listed_at")))

        # Price + TTS
        price_str = ""
        try:
            price_str = f'{float(row.get("price_chaos") or 0.0):g} c'
        except (TypeError, ValueError):
            price_str = str(row.get("price_chaos") or "")
        add_row(content, "Price", price_str)

        tts = row.get("time_to_sale_hours")
        tts_str = ""
        if tts is not None:
            try:
                tts_str = f"{float(tts):.2f} h"
            except (TypeError, ValueError):
                tts_str = str(tts)
        add_row(content, "Time to Sale", tts_str)

        # Notes as a multi-line text box
        notes_label = ttk.Label(content, text="Notes:", anchor="nw")
        notes_label.grid(row=7, column=0, sticky="nw", padx=(8, 4), pady=(8, 4))

        notes_text = tk.Text(content, width=60, height=6, wrap="word")
        notes_text.grid(row=7, column=1, sticky="nsew", padx=(0, 8), pady=(8, 4))
        content.grid_rowconfigure(7, weight=1)
        content.grid_columnconfigure(1, weight=1)

        notes_text.insert("1.0", str(row.get("notes") or ""))
        notes_text.configure(state="disabled")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=1, column=0, sticky="e", padx=8, pady=(0, 8))

        close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_btn.grid(row=0, column=0, padx=(0, 0))

        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        self._center_child(dialog)

    # ------------------------------------------------------------------ Helpers

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try common formats
            # 1) ISO
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
            # 2) SQLite default "YYYY-MM-DD HH:MM:SS"
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None

    def _format_dt(self, value: Any) -> str:
        dt = self._parse_dt(value)
        if not dt:
            return str(value or "")
        return dt.strftime("%Y-%m-%d %H:%M")

    def _center_over_parent(self) -> None:
        if not self.master or not self.winfo_ismapped():
            return

        self.update_idletasks()

        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()

        width = self.winfo_width()
        height = self.winfo_height()

        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _center_child(self, child: tk.Toplevel) -> None:
        if not child.winfo_ismapped():
            child.update_idletasks()

        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()

        width = child.winfo_width()
        height = child.winfo_height()

        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2

        child.geometry(f"{width}x{height}+{x}+{y}")
