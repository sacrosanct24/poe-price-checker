"""
gui.pob_character_window

Tkinter window for managing Path of Building character imports.

Features:
- List saved character profiles
- Import new characters via pastebin URL or raw PoB code
- View character equipment details
- Delete saved profiles
- Select active character for upgrade checking
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Any, Dict, List, Optional, Callable

from core.pob_integration import CharacterManager, PoBDecoder, PoBBuild, PoBItem


class PoBCharacterWindow(tk.Toplevel):
    """Window for managing PoB character profiles for upgrade checking."""

    def __init__(
        self,
        master: tk.Misc,
        character_manager: CharacterManager,
        *,
        on_profile_selected: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(master)

        self.character_manager = character_manager
        self.on_profile_selected = on_profile_selected

        # Currently selected profile name
        self._selected_profile: Optional[str] = None

        # Cache of loaded profile data
        self._profiles_cache: Dict[str, Any] = {}

        self.title("PoB Character Manager")
        self.transient(master)
        self.resizable(True, True)
        self.geometry("800x500")

        self._create_widgets()
        self._layout_widgets()
        self._load_profiles()

        # Center over parent
        self.update_idletasks()
        self._center_over_parent()

        # Key bindings
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Delete>", lambda _event: self._on_delete_profile())

    def _create_widgets(self) -> None:
        # --- Left panel: profile list ---
        self.left_frame = ttk.LabelFrame(self, text="Characters", padding=8)

        self.profile_listbox = tk.Listbox(
            self.left_frame,
            height=15,
            selectmode="browse",
            exportselection=False,
        )
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)

        self.profile_scrollbar = ttk.Scrollbar(
            self.left_frame,
            orient="vertical",
            command=self.profile_listbox.yview,
        )
        self.profile_listbox.configure(yscrollcommand=self.profile_scrollbar.set)

        # Button bar for profiles
        self.profile_buttons = ttk.Frame(self.left_frame)
        self.import_btn = ttk.Button(
            self.profile_buttons,
            text="Import...",
            command=self._on_import_profile,
        )
        self.delete_btn = ttk.Button(
            self.profile_buttons,
            text="Delete",
            command=self._on_delete_profile,
        )
        self.refresh_btn = ttk.Button(
            self.profile_buttons,
            text="Refresh",
            command=self._load_profiles,
        )
        self.set_active_btn = ttk.Button(
            self.profile_buttons,
            text="Set Active",
            command=self._on_set_active,
        )

        # --- Right panel: character details ---
        self.right_frame = ttk.LabelFrame(self, text="Character Details", padding=8)

        # Character info
        self.info_frame = ttk.Frame(self.right_frame)
        self.info_labels: Dict[str, ttk.Label] = {}

        for label_name in ["Name:", "Class:", "Level:", "Items:", "Categories:", "Status:"]:
            row = ttk.Frame(self.info_frame)
            lbl = ttk.Label(row, text=label_name, width=10, anchor="w")
            val = ttk.Label(row, text="-", anchor="w")
            lbl.pack(side="left")
            val.pack(side="left", fill="x", expand=True)
            row.pack(fill="x", pady=2)
            self.info_labels[label_name.rstrip(":")] = val

        # Equipment tree
        self.equipment_label = ttk.Label(self.right_frame, text="Equipment:")

        self.equipment_tree = ttk.Treeview(
            self.right_frame,
            columns=("slot", "item_name", "base_type", "rarity"),
            show="headings",
            selectmode="browse",
            height=10,
        )

        self.equipment_tree.heading("slot", text="Slot")
        self.equipment_tree.heading("item_name", text="Item Name")
        self.equipment_tree.heading("base_type", text="Base Type")
        self.equipment_tree.heading("rarity", text="Rarity")

        self.equipment_tree.column("slot", width=100, anchor="w")
        self.equipment_tree.column("item_name", width=180, anchor="w")
        self.equipment_tree.column("base_type", width=120, anchor="w")
        self.equipment_tree.column("rarity", width=80, anchor="w")

        self.equipment_scrollbar = ttk.Scrollbar(
            self.right_frame,
            orient="vertical",
            command=self.equipment_tree.yview,
        )
        self.equipment_tree.configure(yscrollcommand=self.equipment_scrollbar.set)

        self.equipment_tree.bind("<Double-1>", self._on_equipment_double_click)

        # --- Bottom: active profile indicator ---
        self.status_frame = ttk.Frame(self)
        self.active_label = ttk.Label(
            self.status_frame,
            text="Active Character: None",
            font=("", 10, "bold"),
        )

    def _layout_widgets(self) -> None:
        # Main layout: left panel (1/3) + right panel (2/3)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left panel layout
        self.profile_listbox.grid(row=0, column=0, sticky="nsew")
        self.profile_scrollbar.grid(row=0, column=1, sticky="ns")
        self.profile_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=1)

        # Profile buttons
        self.import_btn.pack(side="left", padx=(0, 4))
        self.delete_btn.pack(side="left", padx=(0, 4))
        self.refresh_btn.pack(side="left", padx=(0, 4))
        self.set_active_btn.pack(side="left")

        # Right panel layout
        self.info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.equipment_label.grid(row=1, column=0, columnspan=2, sticky="w")
        self.equipment_tree.grid(row=2, column=0, sticky="nsew")
        self.equipment_scrollbar.grid(row=2, column=1, sticky="ns")

        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(2, weight=1)

        # Status bar
        self.active_label.pack(side="left")

    def _load_profiles(self) -> None:
        """Load all saved profiles from the character manager."""
        self.profile_listbox.delete(0, "end")
        self._profiles_cache.clear()

        profile_names = self.character_manager.list_profiles()
        active = self.character_manager.get_active_profile()
        active_name = active.name if active else None

        # Get upgrade target
        upgrade_target = self.character_manager.get_upgrade_target()
        upgrade_target_name = upgrade_target.name if upgrade_target else None

        for name in profile_names:
            # Get the actual profile object
            profile = self.character_manager.get_profile(name)
            if not profile:
                continue

            # Build display name with status indicators
            display = name
            tags = []

            if active_name and name == active_name:
                tags.append("active")
            if upgrade_target_name and name == upgrade_target_name:
                tags.append("upgrade")
            if hasattr(profile, 'categories') and profile.categories:
                # Show categories in abbreviated form
                cat_abbrev = []
                for cat in profile.categories[:3]:  # Show max 3
                    # Convert to short form: "league_starter" -> "LS", "meta" -> "M", etc.
                    abbrev_map = {
                        "league_starter": "LS",
                        "endgame": "EG",
                        "boss_killer": "BK",
                        "mapper": "MAP",
                        "budget": "BUD",
                        "meta": "META",
                        "experimental": "EXP",
                        "reference": "REF",
                    }
                    cat_abbrev.append(abbrev_map.get(cat, cat[:3].upper()))
                tags.extend(cat_abbrev)

            if tags:
                display = f"{name} [{', '.join(tags)}]"

            self.profile_listbox.insert("end", display)

            # Cache the profile data as a dict for display
            self._profiles_cache[name] = {
                "name": profile.name,
                "build_info": {
                    "class_name": profile.build.class_name if profile.build else "",
                    "ascendancy": profile.build.ascendancy if profile.build else "",
                    "level": profile.build.level if profile.build else 0,
                },
                "items": {
                    slot: {
                        "name": item.name,
                        "base_type": item.base_type,
                        "rarity": item.rarity,
                        "implicit_mods": item.implicit_mods,
                        "explicit_mods": item.explicit_mods,
                    }
                    for slot, item in (profile.build.items.items() if profile.build else {})
                },
                "categories": getattr(profile, 'categories', []) or [],
                "is_upgrade_target": getattr(profile, 'is_upgrade_target', False),
            }

        # Update active label
        if active:
            self.active_label.config(text=f"Active Character: {active.name}")
        else:
            self.active_label.config(text="Active Character: None")

        # Clear details if no selection
        if not profile_names:
            self._clear_details()

    def _clear_details(self) -> None:
        """Clear the character details panel."""
        for label in self.info_labels.values():
            label.config(text="-")

        for item in self.equipment_tree.get_children():
            self.equipment_tree.delete(item)

    def _on_profile_select(self, event: tk.Event) -> None:
        """Handle profile selection from listbox."""
        selection = self.profile_listbox.curselection()
        if not selection:
            return

        # Get the actual profile name (strip "[tags]" suffix if present)
        display_name = self.profile_listbox.get(selection[0])
        # Remove any bracketed tags at the end: "Name [active, META]" -> "Name"
        if " [" in display_name:
            name = display_name.rsplit(" [", 1)[0].strip()
        else:
            name = display_name.strip()

        self._selected_profile = name
        self._show_profile_details(name)

    def _show_profile_details(self, name: str) -> None:
        """Display details for the selected profile."""
        profile = self._profiles_cache.get(name)
        if not profile:
            self._clear_details()
            return

        # Update info labels
        self.info_labels["Name"].config(text=profile.get("name", "-"))

        build_info = profile.get("build_info", {})
        class_name = build_info.get("class_name", "-")
        ascendancy = build_info.get("ascendancy", "")
        if ascendancy:
            class_name = f"{class_name} ({ascendancy})"
        self.info_labels["Class"].config(text=class_name)

        self.info_labels["Level"].config(text=str(build_info.get("level", "-")))

        items = profile.get("items", {})
        self.info_labels["Items"].config(text=f"{len(items)} equipped")

        # Display categories
        categories = profile.get("categories", [])
        if categories:
            # Format category names nicely: "league_starter" -> "League Starter"
            cat_display = ", ".join(
                cat.replace("_", " ").title() for cat in categories
            )
            self.info_labels["Categories"].config(text=cat_display)
        else:
            self.info_labels["Categories"].config(text="None")

        # Display status (upgrade target, active)
        status_parts = []
        if profile.get("is_upgrade_target"):
            status_parts.append("Upgrade Target")
        if name == (self.character_manager.get_active_profile().name if self.character_manager.get_active_profile() else None):
            status_parts.append("Active")
        self.info_labels["Status"].config(text=", ".join(status_parts) if status_parts else "None")

        # Populate equipment tree
        for item in self.equipment_tree.get_children():
            self.equipment_tree.delete(item)

        # Sort items by slot for consistent display
        slot_order = [
            "Weapon 1", "Weapon 2", "Weapon 1 Swap", "Weapon 2 Swap",
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Amulet", "Ring 1", "Ring 2", "Belt",
            "Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5",
        ]

        sorted_slots = sorted(
            items.keys(),
            key=lambda s: slot_order.index(s) if s in slot_order else 999
        )

        for slot in sorted_slots:
            item_data = items[slot]
            self.equipment_tree.insert(
                "",
                "end",
                values=(
                    slot,
                    item_data.get("name", "-"),
                    item_data.get("base_type", "-"),
                    item_data.get("rarity", "-"),
                ),
                tags=(item_data.get("rarity", "").lower(),),
            )

        # Configure rarity-based colors (using PoE-style colors with better readability)
        self.equipment_tree.tag_configure("unique", foreground="#af6025")  # Unique orange
        self.equipment_tree.tag_configure("rare", foreground="#ccaa00")    # Gold/tan (readable on dark/light)
        self.equipment_tree.tag_configure("magic", foreground="#8888ff")   # Magic blue
        self.equipment_tree.tag_configure("normal", foreground="#808080")  # Normal gray

    def _on_equipment_double_click(self, event: tk.Event) -> None:
        """Show item details on double-click."""
        item = self.equipment_tree.identify_row(event.y)
        if not item:
            return

        values = self.equipment_tree.item(item, "values")
        if not values:
            return

        slot = values[0]
        if not self._selected_profile:
            return

        profile = self._profiles_cache.get(self._selected_profile)
        if not profile:
            return

        items = profile.get("items", {})
        item_data = items.get(slot, {})

        if not item_data:
            return

        self._show_item_details_dialog(slot, item_data)

    def _show_item_details_dialog(self, slot: str, item_data: Dict[str, Any]) -> None:
        """Show a dialog with full item details."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Item Details: {slot}")
        dialog.transient(self)
        dialog.resizable(False, True)

        content = ttk.Frame(dialog, padding=10)
        content.pack(fill="both", expand=True)

        # Item header
        name = item_data.get("name", "Unknown")
        base = item_data.get("base_type", "")
        rarity = item_data.get("rarity", "")

        header_frame = ttk.Frame(content)
        header_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(
            header_frame,
            text=name,
            font=("", 12, "bold"),
        ).pack(anchor="w")

        if base and base != name:
            ttk.Label(header_frame, text=base).pack(anchor="w")

        ttk.Label(
            header_frame,
            text=f"Rarity: {rarity}",
            foreground="#888888",
        ).pack(anchor="w")

        # Mods
        ttk.Separator(content, orient="horizontal").pack(fill="x", pady=8)

        implicit_mods = item_data.get("implicit_mods", [])
        explicit_mods = item_data.get("explicit_mods", [])

        if implicit_mods:
            ttk.Label(content, text="Implicit Mods:", font=("", 9, "bold")).pack(anchor="w")
            for mod in implicit_mods:
                ttk.Label(content, text=f"  {mod}", foreground="#8888ff").pack(anchor="w")

        if explicit_mods:
            if implicit_mods:
                ttk.Separator(content, orient="horizontal").pack(fill="x", pady=4)
            ttk.Label(content, text="Explicit Mods:", font=("", 9, "bold")).pack(anchor="w")
            for mod in explicit_mods:
                # Check for crafted mods
                if mod.startswith("(crafted)"):
                    ttk.Label(content, text=f"  {mod}", foreground="#b4b4ff").pack(anchor="w")
                else:
                    ttk.Label(content, text=f"  {mod}").pack(anchor="w")

        # Close button
        ttk.Button(
            content,
            text="Close",
            command=dialog.destroy,
        ).pack(pady=(16, 0))

        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        # Center over parent
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _on_import_profile(self) -> None:
        """Show import dialog for adding a new character."""
        ImportPoBDialog(self, self.character_manager, on_import=self._load_profiles)

    def _on_delete_profile(self) -> None:
        """Delete the selected profile."""
        if not self._selected_profile:
            messagebox.showinfo("Delete Profile", "No profile selected.")
            return

        confirm = messagebox.askyesno(
            "Delete Profile",
            f"Are you sure you want to delete '{self._selected_profile}'?",
        )

        if not confirm:
            return

        try:
            self.character_manager.delete_profile(self._selected_profile)
            self._selected_profile = None
            self._load_profiles()
            self._clear_details()
        except Exception as exc:
            messagebox.showerror("Delete Error", f"Failed to delete profile:\n{exc}")

    def _on_set_active(self) -> None:
        """Set the selected profile as active."""
        if not self._selected_profile:
            messagebox.showinfo("Set Active", "No profile selected.")
            return

        try:
            self.character_manager.set_active_profile(self._selected_profile)
            self._load_profiles()

            if self.on_profile_selected:
                self.on_profile_selected(self._selected_profile)

            messagebox.showinfo(
                "Active Profile",
                f"'{self._selected_profile}' is now the active character for upgrade checking.",
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to set active profile:\n{exc}")

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

        self.geometry(f"+{x}+{y}")


class ImportPoBDialog(tk.Toplevel):
    """Dialog for importing a PoB character via pastebin URL or raw code."""

    def __init__(
        self,
        master: tk.Misc,
        character_manager: CharacterManager,
        *,
        on_import: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)

        self.character_manager = character_manager
        self.on_import = on_import

        self.title("Import PoB Character")
        self.transient(master)
        self.grab_set()
        self.resizable(True, False)

        self._create_widgets()

        # Center over parent
        self.update_idletasks()
        self._center_over_parent()

        self.bind("<Escape>", lambda _event: self.destroy())

    def _create_widgets(self) -> None:
        content = ttk.Frame(self, padding=16)
        content.pack(fill="both", expand=True)

        # Character name
        ttk.Label(content, text="Character Name:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(content, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # PoB code/URL
        ttk.Label(
            content,
            text="Pastebin URL or PoB Code:",
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.code_text = tk.Text(content, height=6, width=50, wrap="word")
        self.code_text.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # Help text
        help_text = (
            "Enter a Pastebin URL (e.g., https://pastebin.com/abc123)\n"
            "or paste the raw PoB build code directly."
        )
        ttk.Label(
            content,
            text=help_text,
            foreground="#666666",
            font=("", 9),
        ).grid(row=4, column=0, sticky="w", pady=(0, 12))

        # Notes (optional)
        ttk.Label(content, text="Notes (optional):").grid(row=5, column=0, sticky="w", pady=(0, 4))
        self.notes_var = tk.StringVar()
        self.notes_entry = ttk.Entry(content, textvariable=self.notes_var, width=40)
        self.notes_entry.grid(row=6, column=0, sticky="ew", pady=(0, 16))

        # Buttons
        button_frame = ttk.Frame(content)
        button_frame.grid(row=7, column=0, sticky="e")

        self.import_btn = ttk.Button(
            button_frame,
            text="Import",
            command=self._on_import,
        )
        self.import_btn.pack(side="left", padx=(0, 8))

        self.cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
        )
        self.cancel_btn.pack(side="left")

        content.columnconfigure(0, weight=1)

        # Focus name entry
        self.name_entry.focus_set()

    def _on_import(self) -> None:
        """Attempt to import the PoB build."""
        name = self.name_var.get().strip()
        code = self.code_text.get("1.0", "end").strip()
        notes = self.notes_var.get().strip()

        if not name:
            messagebox.showerror("Import Error", "Please enter a character name.")
            self.name_entry.focus_set()
            return

        if not code:
            messagebox.showerror("Import Error", "Please enter a PoB code or Pastebin URL.")
            self.code_text.focus_set()
            return

        # Check for duplicate name - list_profiles() returns list of names (strings)
        existing = self.character_manager.list_profiles()
        if name in existing:
            confirm = messagebox.askyesno(
                "Duplicate Name",
                f"A profile named '{name}' already exists.\n\nDo you want to overwrite it?",
            )
            if not confirm:
                return
            # Remove existing profile first
            self.character_manager.delete_profile(name)

        try:
            # Attempt to import
            self.import_btn.config(state="disabled")
            self.update_idletasks()

            profile = self.character_manager.add_from_pob_code(
                name=name,
                pob_code=code,
                notes=notes or None,
            )

            if profile:
                build = profile.build
                item_count = len(build.items) if build else 0

                messagebox.showinfo(
                    "Import Success",
                    f"Successfully imported '{name}'!\n\n"
                    f"Class: {build.class_name if build else 'Unknown'} "
                    f"({build.ascendancy if build else ''})\n"
                    f"Level: {build.level if build else '?'}\n"
                    f"Items: {item_count} equipped",
                )

                if self.on_import:
                    self.on_import()

                self.destroy()
            else:
                messagebox.showerror(
                    "Import Failed",
                    "Failed to import the character.\n\n"
                    "Please check that the PoB code or URL is valid.",
                )
                self.import_btn.config(state="normal")

        except Exception as exc:
            messagebox.showerror(
                "Import Error",
                f"An error occurred while importing:\n\n{exc}",
            )
            self.import_btn.config(state="normal")

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

        self.geometry(f"+{x}+{y}")
