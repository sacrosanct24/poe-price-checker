# gui/main_window.py
from __future__ import annotations

import os
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import Any, Dict, List, Tuple
from datetime import datetime
import webbrowser

from core.app_context import AppContext, create_app_context
from core.item_parser import ParsedItem
from core.game_version import GameVersion
from core.value_rules import assess_rare_item

APP_VERSION = "0.2.0-dev"


class PriceCheckerGUI:
    """Main Tkinter window for the PoE Price Checker."""

    def __init__(self, root: tk.Tk, app_context: AppContext) -> None:
        self.root = root
        self.ctx = app_context

        self.root.title("PoE Item Price Checker")

        # --- Window size from config ---
        win_w, win_h = self.ctx.config.window_size
        self.root.geometry(f"{win_w}x{win_h}")

        self.status_var = tk.StringVar(value="Ready.")

        # This will display: "PoE1 – Standard (last price update: 2025-11-15 17:31)"
        self.game_info_var = tk.StringVar(value="")

        # UI filter state (backed by Config)
        self.min_value_var = tk.DoubleVar(value=self.ctx.config.min_value_chaos)
        self.show_vendor_var = tk.BooleanVar(value=self.ctx.config.show_vendor_items)

        # This will store the latest (ParsedItem, price_data) tuples
        self.checked_items: List[Tuple[ParsedItem, Dict[str, Any]]] = []

        self._build_menu()
        self._build_layout()
        self._update_game_info()  # Initialize league + last update display

        # Auto-focus the input box shortly after startup
        self.root.after(150, self.input_text.focus_set)

        # Hook window close to save size + close DB
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI building ----------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # --- File menu ---
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_close)

        # --- Settings menu ---
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Change League", command=self.change_league)
        # Later: menu for switching PoE1 / PoE2

        # --- Tools menu ---
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        tools_menu.add_command(
            label="Open Log File",
            command=self._open_log_file,
        )
        tools_menu.add_command(
            label="Open Config Folder",
            command=self._open_config_folder,
        )

        tools_menu.add_separator()

        tools_menu.add_command(
            label="Export Checked Items to Excel... (Planned)",
            command=lambda: self._not_implemented("Excel export"),
        )
        tools_menu.add_command(
            label="View Price History (Planned)",
            command=lambda: self._not_implemented("Price history viewer"),
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Refresh Price Data (poe.ninja)",
            command=lambda: self._not_implemented("Price data refresh"),
        )
        tools_menu.add_command(
            label="Import GGG Item JSON (Planned)",
            command=lambda: self._not_implemented("GGG item JSON import"),
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Plugin Manager (Planned)",
            command=lambda: self._not_implemented("Plugin manager"),
        )

        # --- Helpful Links menu ---
        links_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Links", menu=links_menu)

        # Official / GGG links
        official_menu = tk.Menu(links_menu, tearoff=0)
        links_menu.add_cascade(label="Official / GGG", menu=official_menu)
        official_menu.add_command(
            label="Path of Exile (PoE1)",
            command=lambda: self._open_url("https://www.pathofexile.com"),
        )
        official_menu.add_command(
            label="PoE Trade (Official)",
            command=lambda: self._open_url("https://www.pathofexile.com/trade"),
        )
        official_menu.add_command(
            label="Path of Exile 2",
            command=lambda: self._open_url("https://www.pathofexile2.com"),
        )

        # Databases / Info
        db_menu = tk.Menu(links_menu, tearoff=0)
        links_menu.add_cascade(label="Databases & Info", menu=db_menu)
        db_menu.add_command(
            label="PoE Wiki",
            command=lambda: self._open_url("https://www.poewiki.net"),
        )
        db_menu.add_command(
            label="PoEDB",
            command=lambda: self._open_url("https://poedb.tw"),
        )
        db_menu.add_command(
            label="poe.ninja (Economy)",
            command=lambda: self._open_url("https://poe.ninja"),
        )

        # Build guides
        builds_menu = tk.Menu(links_menu, tearoff=0)
        links_menu.add_cascade(label="Build Guides", menu=builds_menu)
        builds_menu.add_command(
            label="Maxroll – PoE2",
            command=lambda: self._open_url("https://maxroll.gg/poe2"),
        )
        builds_menu.add_command(
            label="Maxroll – PoE1",
            command=lambda: self._open_url("https://maxroll.gg/path-of-exile"),
        )
        builds_menu.add_command(
            label="PoE Vault",
            command=lambda: self._open_url("https://www.poe-vault.com"),
        )

        # Developer / Programming
        dev_menu = tk.Menu(links_menu, tearoff=0)
        links_menu.add_cascade(label="Dev / Programming", menu=dev_menu)
        dev_menu.add_command(
            label="GGG Trade API Thread",
            command=lambda: self._open_url(
                "https://www.pathofexile.com/forum/view-thread/3072628"
            ),
        )
        dev_menu.add_command(
            label="PoE Wiki Cargo API",
            command=lambda: self._open_url(
                "https://www.poewiki.net/wiki/Help:Cargo"
            ),
        )
        dev_menu.add_command(
            label="poe.ninja API Info (GitHub)",
            command=lambda: self._open_url(
                "https://github.com/poe-ninja/poe-ninja-api"
            ),
        )
        dev_menu.add_command(
            label="poe2scout API (Swagger)",
            command=lambda: self._open_url(
                "https://poe2scout.com/api/swagger"
            ),
        )

        # --- Help menu ---
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(
            label="About PoE Price Checker",
            command=self.show_about,
        )

    def _build_layout(self) -> None:
        # Input frame
        input_frame = ttk.LabelFrame(
            self.root,
            text="Paste items here (Ctrl+C in game, Ctrl+V here)",
            padding=10,
        )
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=10,
            wrap=tk.WORD,
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Auto-check on paste:
        # - <<Paste>> fires after paste, so we schedule a check a tick later
        self.input_text.bind("<<Paste>>", self._on_paste)
        # Ensure Ctrl+V maps to <<Paste>> consistently
        self.input_text.bind("<Control-v>", self._on_ctrl_v)

        # Buttons + filters
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.check_button = ttk.Button(
            button_frame,
            text="Check Prices",
            command=self.check_prices,
        )
        self.check_button.pack(side=tk.LEFT)

        # New: Clear button
        self.clear_button = ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_all,
        )
        self.clear_button.pack(side=tk.LEFT, padx=(5, 0))

        # --- Filters: Min chaos & vendor items ---
        ttk.Label(button_frame, text="   Min chaos:").pack(side=tk.LEFT, padx=(15, 2))
        self.min_value_entry = ttk.Entry(
            button_frame,
            width=8,
            textvariable=self.min_value_var,
        )
        self.min_value_entry.pack(side=tk.LEFT)

        self.vendor_check = ttk.Checkbutton(
            button_frame,
            text="Show vendor items",
            variable=self.show_vendor_var,
        )
        self.vendor_check.pack(side=tk.LEFT, padx=(10, 0))

        # Results frame
        results_frame = ttk.LabelFrame(self.root, text="Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = (
            "Item",
            "Rarity",
            "Item Level",
            "Stack",
            "Chaos Value",
            "Divine Value",
            "Total Value",
            "Value Flag",
        )
        self.tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.tree.heading("#0", text="#")
        self.tree.heading("Item", text="Item Name")
        self.tree.heading("Rarity", text="Rarity")
        self.tree.heading("Item Level", text="iLvl")
        self.tree.heading("Stack", text="Stack")
        self.tree.heading("Chaos Value", text="Chaos/Unit")
        self.tree.heading("Divine Value", text="Divine/Unit")
        self.tree.heading("Total Value", text="Total Value (c)")
        self.tree.heading("Value Flag", text="Value Flag")

        self.tree.column("#0", width=40, stretch=False)
        self.tree.column("Item", width=350)
        self.tree.column("Rarity", width=80, anchor=tk.CENTER)
        self.tree.column("Item Level", width=60, anchor=tk.CENTER)
        self.tree.column("Stack", width=60, anchor=tk.CENTER)
        self.tree.column("Chaos Value", width=90, anchor=tk.E)
        self.tree.column("Divine Value", width=90, anchor=tk.E)
        self.tree.column("Total Value", width=110, anchor=tk.E)
        self.tree.column("Value Flag", width=100, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Context menu for copying from results
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(
            label="Copy Item Name",
            command=self._copy_item_name,
        )
        self.tree_menu.add_command(
            label="Copy Row (tab-separated)",
            command=self._copy_row_tsv,
        )

        # Right-click on row
        self.tree.bind("<Button-3>", self._on_tree_right_click)
        # Ctrl+C to copy row as TSV
        self.tree.bind("<Control-c>", self._on_tree_ctrl_c)

        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Left: status messages
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        # Right: game + league + last update
        ttk.Label(
            status_frame,
            textvariable=self.game_info_var,
            anchor=tk.E,
        ).pack(side=tk.RIGHT)

    # ---------- Settings / State ----------

    def _update_game_info(self) -> None:
        """
        Update the display string for:
        - current game (PoE1 / PoE2)
        - league
        - last price update timestamp
        """
        cfg = self.ctx.config

        # Game label (PoE1 / PoE2)
        if cfg.current_game == GameVersion.POE1:
            game_label = "PoE1"
        elif cfg.current_game == GameVersion.POE2:
            game_label = "PoE2"
        else:
            game_label = str(cfg.current_game)

        league = cfg.league

        # last_price_update may be None, str, or datetime; normalize it
        last_update = getattr(cfg, "last_price_update", None)
        if isinstance(last_update, datetime):
            ts = last_update.strftime("%Y-%m-%d %H:%M")
        elif isinstance(last_update, str) and last_update:
            # stored as ISO string "2025-11-15T17:31:10.707953"
            try:
                dt = datetime.fromisoformat(last_update)
                ts = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts = last_update.replace("T", " ").split(".")[0]
        else:
            ts = "never"

        self.game_info_var.set(
            f"{game_label} – {league} (last price update: {ts})"
        )

    def change_league(self) -> None:
        """
        Show a small dialog with a dropdown of available leagues.

        - Uses poe.ninja's /economyleagues endpoint via PoeNinjaAPI.get_current_leagues()
        - Updates Config.league for the current game
        - Updates AppContext.poe_ninja.league if using PoE1
        """
        if not self.ctx.poe_ninja:
            messagebox.showinfo("Change League", "League selection is only available for PoE1.")
            return

        # Fetch leagues from poe.ninja
        try:
            leagues = self.ctx.poe_ninja.get_current_leagues()
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to fetch leagues from poe.ninja:\n{exc}")
            return

        if not leagues:
            messagebox.showwarning(
                "Change League",
                "No leagues were returned from poe.ninja.\n"
                "Try again later or set the league manually in the config."
            )
            return

        # Map display name → internal name
        # poe.ninja returns [{"name": "Settlers", "displayName": "Settlers"}, ...]
        display_to_name: dict[str, str] = {}
        display_values: list[str] = []

        for entry in leagues:
            internal = entry.get("name") or ""
            display = entry.get("displayName") or internal
            if not internal:
                continue
            display_to_name[display] = internal
            display_values.append(display)

        # Sort alphabetically for nicer UX
        display_values.sort(key=str.lower)

        if not display_values:
            messagebox.showwarning(
                "Change League",
                "No valid leagues were returned from poe.ninja."
            )
            return

        # Current league (internal name)
        current_league = self.ctx.config.league

        # Try to find the display name that corresponds to current_league
        initial_display = None
        for disp, name in display_to_name.items():
            if name == current_league:
                initial_display = disp
                break
        if initial_display is None:
            # Fallback to first entry
            initial_display = display_values[0]

        # --- Build the dialog window ---
        dialog = tk.Toplevel(self.root)
        dialog.title("Change League")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Select league:", anchor="w").pack(
            side=tk.TOP, fill=tk.X, padx=10, pady=(10, 4)
        )

        league_var = tk.StringVar(value=initial_display)
        combo = ttk.Combobox(
            dialog,
            textvariable=league_var,
            values=display_values,
            state="readonly",
            width=40,
        )
        combo.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        combo.focus_set()

        button_frame = tk.Frame(dialog)
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

        def on_ok() -> None:
            chosen_display = league_var.get()
            internal_name = display_to_name.get(chosen_display)
            if not internal_name:
                dialog.destroy()
                return

            # Update config and poe.ninja client
            self.ctx.config.league = internal_name
            if self.ctx.config.current_game == GameVersion.POE1 and self.ctx.poe_ninja:
                self.ctx.poe_ninja.league = internal_name

            # Refresh status bar
            self._update_game_info()
            self.status_var.set(f"League changed to {internal_name}")
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        ok_btn = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_btn.pack(side=tk.RIGHT)

        dialog.bind("<Return>", lambda _: on_ok())
        dialog.bind("<Escape>", lambda _: on_cancel())

        # Center the dialog over the main window
        self.root.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        dw = dialog.winfo_reqwidth()
        dh = dialog.winfo_reqheight()
        dialog.geometry(f"{dw}x{dh}+{x + (w - dw) // 2}+{y + (h - dh) // 2}")

    # ---------- Core actions ----------

    def check_prices(self) -> None:
        """Main entry point for checking prices of pasted items."""
        # Sync UI filters back into config
        self._sync_filters_to_config()

        raw_text = self.input_text.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("No Input", "Please paste at least one item.")
            return

        # Clear previous results
        self.tree.delete(*self.tree.get_children())
        self.checked_items.clear()

        # For now, pricing is only wired for PoE1/poe.ninja
        if self.ctx.config.current_game != GameVersion.POE1:
            messagebox.showinfo(
                "Pricing not available",
                "PoE2 pricing is not implemented yet.\n"
                "You can still parse items, but prices will be empty.",
            )

        self._set_status("Parsing items...")
        items = self._parse_items(raw_text)
        if not items:
            messagebox.showwarning("Parse Error", "No valid items were detected.")
            self._set_status("Ready.")
            return

        self._set_status("Checking prices...")

        min_filter = self.ctx.config.min_value_chaos
        show_vendor = self.ctx.config.show_vendor_items

        displayed_count = 0

        for parsed in items:
            price_data: Dict[str, Any] = self._lookup_price(parsed)

            chaos_value = self._extract_chaos_value(price_data)
            divine_value = self._extract_divine_value(price_data)
            stack_size = parsed.stack_size or 1
            effective_chaos = chaos_value or 0.0
            total_chaos = effective_chaos * stack_size

            # Persist to DB regardless of filter (so history is complete)
            try:
                self._record_in_database(parsed, chaos_value, divine_value)
            except Exception as exc:  # pragma: no cover
                print(f"DB error while recording item: {exc!r}")

            # Run rare-value assessment (for display only)
            value_flag = ""
            try:
                if (parsed.rarity or "").upper() == "RARE":
                    assessment = assess_rare_item(parsed)
                    value_flag = assessment.flag
            except Exception as exc:  # pragma: no cover
                # Fail-safe: don't break the whole check on value assessment error
                print(f"Rare value assessment error: {exc!r}")
                value_flag = ""

            # Apply min chaos filter for display
            if effective_chaos < min_filter and not show_vendor:
                # Skip showing this item in the tree
                continue

            displayed_count += 1
            self.checked_items.append((parsed, price_data))

            self.tree.insert(
                "",
                "end",
                values=(
                    parsed.get_display_name(),
                    parsed.rarity or "",
                    parsed.item_level or "",
                    stack_size,
                    f"{chaos_value:.1f}" if chaos_value is not None else "",
                    f"{divine_value:.2f}" if divine_value is not None else "",
                    f"{total_chaos:.1f}" if chaos_value is not None else "",
                    value_flag,
                ),
            )


        self._set_status(
            f"Done. Parsed {len(items)} item(s), showing {displayed_count} "
            f"(min {min_filter:.1f}c, vendor items "
            f"{'shown' if show_vendor else 'hidden'})."
        )

    def clear_all(self) -> None:
        """
        Clear input box and results table.
        """
        self.input_text.delete("1.0", tk.END)
        self.tree.delete(*self.tree.get_children())
        self.checked_items.clear()
        self.status_var.set("Cleared input and results.")

    # ---------- Helpers ----------
    # ---------- Helpers ----------

    def _sync_filters_to_config(self) -> None:
        """Validate filter widgets and persist them into Config."""
        try:
            min_val = float(self.min_value_var.get())
        except (TypeError, ValueError):
            min_val = 0.0
            self.min_value_var.set(min_val)

        self.ctx.config.min_value_chaos = min_val
        self.ctx.config.show_vendor_items = bool(self.show_vendor_var.get())

    def _set_status(self, text: str) -> None:
        """Update the status bar text and force a UI refresh."""
        self.status_var.set(text)
        # Update the event loop so the change is visible during longer operations
        self.root.update_idletasks()

    def _parse_items(self, raw_text: str) -> List[ParsedItem]:
        """
        Parse one or more items from the pasted text using ItemParser.
        """
        try:
            return self.ctx.parser.parse_multiple(raw_text)
        except Exception as exc:
            messagebox.showerror("Parse Error", f"Error parsing items:\n{exc}")
            return []

    def _lookup_price(self, item: ParsedItem) -> Dict[str, Any]:
        """
        Use PoeNinjaAPI to get the price for the given ParsedItem (PoE1 only).

        - For currency, call get_currency_overview() and match on currencyTypeName
        - For uniques/other items, delegate to PoeNinjaAPI.find_item_price()
        """
        # If no poe.ninja client (e.g. PoE2), skip pricing
        if self.ctx.config.current_game != GameVersion.POE1 or not self.ctx.poe_ninja:
            return {}

        api = self.ctx.poe_ninja

        try:
            rarity = (item.rarity or "").upper()

            # Text-parsed items don’t have item_class; official JSON items might.
            raw_item_class = getattr(item, "item_class", None)
            item_class = (raw_item_class or "").upper()


            # ---------- Currency path ----------
            if (
                rarity == "CURRENCY"
                or "CURRENCY" in item_class
                or "STACKABLE CURRENCY" in item_class
            ):
                # Prefer base_type for currency; fallback to name
                key = (item.base_type or item.name or "").strip().lower()
                if not key:
                    return {}

                # Special case: Chaos Orb is always 1c by definition.
                if key in ("chaos orb", "chaos"):
                    return {
                        "currencyTypeName": "Chaos Orb",
                        "chaosEquivalent": 1.0,
                        "chaosValue": 1.0,
                    }

                overview = api.get_currency_overview()
                lines = overview.get("lines", [])

                # First try strict match
                for line in lines:
                    c_name = line.get("currencyTypeName", "").strip().lower()
                    if not c_name:
                        continue
                    if c_name == key:
                        return line

                # Fallback: slightly fuzzy match
                for line in lines:
                    c_name = line.get("currencyTypeName", "").strip().lower()
                    if not c_name:
                        continue
                    if key in c_name or c_name in key:
                        return line

                return {}

            # ---------- Non-currency path (uniques, etc.) ----------
            item_name = item.name or ""
            base_type = item.base_type

            gem_level = getattr(item, "gem_level", None)
            gem_quality = getattr(item, "gem_quality", None)
            corrupted = bool(getattr(item, "is_corrupted", False))

            result = api.find_item_price(
                item_name=item_name,
                base_type=base_type,
                rarity=rarity or None,
                gem_level=gem_level,
                gem_quality=gem_quality,
                corrupted=corrupted,
            )
            if result is None:
                return {}

            return dict(result)

        except Exception as exc:
            messagebox.showerror("Pricing Error", f"Error fetching price:\n{exc}")
            return {}

    @staticmethod
    def _extract_chaos_value(price_data: Dict[str, Any]) -> float | None:
        """
        Normalize chaos value from poe.ninja data.
        """
        if not price_data:
            return None

        if "chaosValue" in price_data and price_data["chaosValue"] is not None:
            return float(price_data["chaosValue"])
        if "chaosEquivalent" in price_data and price_data["chaosEquivalent"] is not None:
            return float(price_data["chaosEquivalent"])
        return None

    @staticmethod
    def _extract_divine_value(price_data: Dict[str, Any]) -> float | None:
        """
        Extract divine value if present.
        """
        if not price_data:
            return None

        if "divineValue" in price_data and price_data["divineValue"] is not None:
            return float(price_data["divineValue"])
        return None

    def _record_in_database(
            self,
            item: ParsedItem,
            chaos_value: float | None,
            divine_value: float | None,
    ) -> None:
        """
        Persist a checked item to SQLite.

        We always record the checked item itself, and if a price was found
        we also record a price snapshot for history.
        """
        db = self.ctx.db
        cfg = self.ctx.config

        # Human-readable item name
        item_name = item.get_display_name()
        base_type = item.base_type

        # Even when we don't have a price, we record the lookup with 0c
        effective_chaos = chaos_value if chaos_value is not None else 0.0

        db.add_checked_item(
            game_version=cfg.current_game,
            league=cfg.league,
            item_name=item_name,
            item_base_type=base_type,
            chaos_value=effective_chaos,
        )

        # Store a price snapshot only when we have a real price
        if chaos_value is not None:
            db.add_price_snapshot(
                game_version=cfg.current_game,
                league=cfg.league,
                item_name=item_name,
                item_base_type=base_type,
                chaos_value=chaos_value,
                divine_value=divine_value,
            )


    # ---------- Utility ----------

    def _on_paste(self, event: tk.Event | None = None) -> None:
        """Handle <<Paste>> into the text box and auto-check after paste."""
        # Let the default paste complete, then check
        self.root.after(10, self._auto_check_if_not_empty)

    # ---------- Result copying helpers ----------

    def _get_selected_row(self) -> tuple | None:
        """
        Return all values from the selected Treeview row.
        Works for any number of columns.
        """
        selection = self.tree.selection()
        if not selection:
            return None

        iid = selection[0]
        values = self.tree.item(iid, "values")
        if not values:
            return None

        # Always return all columns, in order
        return tuple(values)


    def _copy_row_tsv(self, event: tk.Event | None = None) -> None:
        row = self._get_selected_row()
        if not row:
            return

        text = "\t".join("" if v is None else str(v) for v in row)
        self._copy_to_clipboard(text)
        self.status_var.set("Copied row to clipboard.")


    def _copy_item_name(self) -> None:
        """Copy just the item name from the selected row."""
        row = self._get_selected_row()
        if not row:
            return

        item_name = row[0]
        self._copy_to_clipboard(item_name)
        self.status_var.set(f"Copied item name: {item_name}")

    def _copy_to_clipboard(self, text: str) -> None:
        """Helper to put text on the system clipboard."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except Exception:
            pass

    def _on_tree_right_click(self, event: tk.Event) -> None:
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
            try:
                self.tree_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.tree_menu.grab_release()

    def _on_tree_ctrl_c(self, event: tk.Event) -> str:
        self._copy_row_tsv()
        return "break"

    def _on_ctrl_v(self, event: tk.Event | None = None) -> str:
        self.input_text.event_generate("<<Paste>>")
        return "break"

    def _auto_check_if_not_empty(self) -> None:
        text = self.input_text.get("1.0", tk.END).strip()
        if text:
            self.check_prices()

    @staticmethod
    def _open_url(url: str) -> None:
        """Open a URL in the default web browser."""
        try:
            webbrowser.open_new_tab(url)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open browser:\n{exc}")

    def _open_log_file(self) -> None:
        """Open the app.log file in Notepad (Windows) or system default."""
        try:
            log_path = os.path.join(
                os.path.expanduser("~"),
                ".poe_price_checker",
                "app.log",
            )

            if os.path.exists(log_path):
                if os.name == "nt":
                    subprocess.Popen(["notepad.exe", log_path])
                else:
                    webbrowser.open(log_path)
            else:
                messagebox.showinfo("Log File", "Log file not found.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open log file:\n{exc}")

    def _open_config_folder(self) -> None:
        """Open the .poe_price_checker directory in Explorer (or system default)."""
        try:
            folder = os.path.join(os.path.expanduser("~"), ".poe_price_checker")

            if os.path.exists(folder):
                if os.name == "nt":
                    subprocess.Popen(["explorer", folder])
                else:
                    webbrowser.open(folder)
            else:
                messagebox.showinfo("Config Folder", "Config folder not found.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open folder:\n{exc}")

    def _not_implemented(self, feature: str) -> None:
        """Show a placeholder dialog for planned features."""
        messagebox.showinfo(
            "Not Implemented Yet",
            f"{feature} is planned but not implemented yet.\n\n"
            "This menu entry is here as a preview of upcoming functionality.",
        )

    def show_about(self) -> None:
        """Show an About dialog with basic app info."""
        # Try to get config + DB paths if available
        cfg_path = getattr(
            self.ctx.config, "config_path", "~/.poe_price_checker/config.json"
        )
        db_path = getattr(self.ctx.db, "db_path", "<unknown>")

        text = (
            "PoE Price Checker\n"
            f"Version: {APP_VERSION}\n\n"
            f"Current game: {self.ctx.config.current_game.name}\n"
            f"Current league: {self.ctx.config.league}\n\n"
            f"Config file: {cfg_path}\n"
            f"Database: {db_path}\n\n"
            "GitHub: https://github.com/sacrosanct24/poe-price-checker\n"
        )
        messagebox.showinfo("About PoE Price Checker", text)

    # ---------- Shutdown ----------

    def on_close(self) -> None:
        """
        Save window size to config, close DB, and destroy the window.
        """
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            self.ctx.config.window_size = (w, h)
        except Exception:
            pass

        try:
            if self.ctx.db:
                self.ctx.db.close()
        except Exception:
            pass

        self.root.destroy()


# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------

def run_app() -> None:
    """
    Launch the PoE Price Checker Tkinter GUI.
    This is called by main.py.
    """
    root = tk.Tk()
    ctx = create_app_context()
    app = PriceCheckerGUI(root, ctx)
    root.mainloop()
