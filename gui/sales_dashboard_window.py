from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, List

from core.database import Database


class SalesDashboardWindow(tk.Toplevel):
    """Simple analytics panel summarizing sales over time."""

    def __init__(
        self,
        master: tk.Misc,
        db: Database,
        *,
        days: int = 30,
    ) -> None:
        super().__init__(master)

        self.db = db
        self.days = days

        self.title("Sales Dashboard")
        self.transient(master)
        self.resizable(True, True)

        self._all_daily_rows: List[Dict[str, Any]] = []
        self._iid_to_row: Dict[str, Dict[str, Any]] = {}

        self._create_widgets()
        self._layout_widgets()
        self._refresh_data()

        self.update_idletasks()
        self._center_over_parent()

        self.bind("<Escape>", lambda _e: self.destroy())

    # ------------------------------------------------------------------ UI creation

    def _create_widgets(self) -> None:
        # Top controls: days + refresh
        self.controls = ttk.Frame(self)

        self.days_label = ttk.Label(self.controls, text="Days:")
        self.days_var = tk.IntVar(value=self.days)
        self.days_spin = ttk.Spinbox(
            self.controls,
            from_=7,
            to=365,
            increment=7,
            textvariable=self.days_var,
            width=6,
            command=self._on_days_changed,
        )

        self.refresh_button = ttk.Button(
            self.controls,
            text="Refresh",
            command=self._refresh_data,
        )

        # Overall stats section
        self.summary_frame = ttk.LabelFrame(self, text="Overall Summary")

        self.total_sales_label = ttk.Label(self.summary_frame, text="Total Sales:")
        self.total_sales_value = ttk.Label(self.summary_frame, text="-")

        self.total_chaos_label = ttk.Label(self.summary_frame, text="Total Chaos:")
        self.total_chaos_value = ttk.Label(self.summary_frame, text="-")

        self.avg_chaos_label = ttk.Label(self.summary_frame, text="Avg Chaos / Sale:")
        self.avg_chaos_value = ttk.Label(self.summary_frame, text="-")

        # Daily breakdown table
        self.daily_frame = ttk.LabelFrame(self, text="Daily Sales (Most Recent First)")

        columns = ("day", "sale_count", "total_chaos", "avg_chaos")
        self.tree = ttk.Treeview(
            self.daily_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=12,
        )

        self.tree.heading("day", text="Day")
        self.tree.heading("sale_count", text="# Sales")
        self.tree.heading("total_chaos", text="Total (c)")
        self.tree.heading("avg_chaos", text="Avg (c)")

        self.tree.column("day", width=110, anchor="w")
        self.tree.column("sale_count", width=80, anchor="e")
        self.tree.column("total_chaos", width=100, anchor="e")
        self.tree.column("avg_chaos", width=100, anchor="e")

        self.scrollbar_y = ttk.Scrollbar(self.daily_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar_y.set)

    def _layout_widgets(self) -> None:
        # Controls
        self.controls.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.controls.columnconfigure(3, weight=1)

        self.days_label.grid(row=0, column=0, padx=(0, 4))
        self.days_spin.grid(row=0, column=1, padx=(0, 8))
        self.refresh_button.grid(row=0, column=2)

        # Summary frame
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        for i in range(3):
            self.summary_frame.columnconfigure(i, weight=1)

        # Place summary labels in a row
        self.total_sales_label.grid(row=0, column=0, sticky="w", padx=(8, 4), pady=4)
        self.total_sales_value.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=4)

        self.total_chaos_label.grid(row=0, column=2, sticky="w", padx=(8, 4), pady=4)
        self.total_chaos_value.grid(row=0, column=3, sticky="w", padx=(0, 16), pady=4)

        self.avg_chaos_label.grid(row=0, column=4, sticky="w", padx=(8, 4), pady=4)
        self.avg_chaos_value.grid(row=0, column=5, sticky="w", padx=(0, 8), pady=4)

        # Daily frame
        self.daily_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(4, 8))
        self.scrollbar_y.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=(4, 8))

        self.daily_frame.grid_rowconfigure(0, weight=1)
        self.daily_frame.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------ Data loading

    def _on_days_changed(self) -> None:
        try:
            value = int(self.days_var.get())
        except (TypeError, ValueError):
            return
        if value <= 0:
            return
        self.days = value
        self._refresh_data()

    def _refresh_data(self) -> None:
        """Load summary + daily stats from DB and populate UI."""
        try:
            overall = self.db.get_sales_summary()
            daily_rows = self.db.get_daily_sales_summary(days=self.days)
        except Exception as exc:  # pragma: no cover - defensive
            messagebox.showerror("Database Error", f"Failed to load sales dashboard data:\n{exc}")
            return

        # Update overall labels
        total_sales = overall.get("total_sales", 0)
        total_chaos = float(overall.get("total_chaos", 0.0))
        avg_chaos = float(overall.get("avg_chaos", 0.0))

        self.total_sales_value.config(text=f"{total_sales}")
        self.total_chaos_value.config(text=f"{total_chaos:,.1f} c")
        self.avg_chaos_value.config(text=f"{avg_chaos:,.2f} c")

        # Normalize daily rows to dicts
        normalized: List[Dict[str, Any]] = []
        for r in daily_rows:
            row_dict = dict(r)
            normalized.append(row_dict)
        self._all_daily_rows = normalized

        self._populate_daily_table(normalized)

    def _populate_daily_table(self, rows: List[Dict[str, Any]]) -> None:
        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._iid_to_row.clear()

        for row in rows:
            day = str(row.get("day") or "")
            sale_count = int(row.get("sale_count") or 0)
            total_chaos = float(row.get("total_chaos") or 0.0)
            avg_chaos = float(row.get("avg_chaos") or 0.0)

            iid = self.tree.insert(
                "",
                "end",
                values=(
                    day,
                    f"{sale_count}",
                    f"{total_chaos:,.1f}",
                    f"{avg_chaos:,.2f}",
                ),
            )
            self._iid_to_row[iid] = row

    # ------------------------------------------------------------------ Helpers

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
