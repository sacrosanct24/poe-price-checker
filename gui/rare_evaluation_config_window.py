"""
Rare Item Evaluation Configuration Window

Allows manual adjustment of rare item evaluation parameters:
- Individual affix weights (1-10 scale)
- Minimum value thresholds
- Build-focused presets
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, Any, Callable, Optional


# Build-focused preset configurations
PRESETS = {
    "Life/Res Tank": {
        "life": 10,
        "resistances": 9,
        "chaos_resistance": 9,
        "energy_shield": 3,
        "spell_suppression": 6,
        "critical_strike_multiplier": 4,
        "added_physical_damage": 4,
        "movement_speed": 8,
        "flask_charges": 6,
        "cooldown_recovery": 7,
    },
    "ES Caster": {
        "life": 4,
        "resistances": 8,
        "chaos_resistance": 7,
        "energy_shield": 10,
        "spell_suppression": 4,
        "critical_strike_multiplier": 9,
        "added_physical_damage": 2,
        "movement_speed": 7,
        "flask_charges": 6,
        "cooldown_recovery": 8,
    },
    "Physical DPS": {
        "life": 8,
        "resistances": 7,
        "chaos_resistance": 6,
        "energy_shield": 3,
        "spell_suppression": 5,
        "critical_strike_multiplier": 10,
        "added_physical_damage": 10,
        "movement_speed": 8,
        "flask_charges": 6,
        "cooldown_recovery": 7,
    },
    "Spell Suppression": {
        "life": 9,
        "resistances": 8,
        "chaos_resistance": 7,
        "energy_shield": 4,
        "spell_suppression": 10,
        "critical_strike_multiplier": 6,
        "added_physical_damage": 5,
        "movement_speed": 8,
        "flask_charges": 6,
        "cooldown_recovery": 7,
    },
    "Balanced": {
        "life": 8,
        "resistances": 7,
        "chaos_resistance": 6,
        "energy_shield": 7,
        "spell_suppression": 7,
        "critical_strike_multiplier": 7,
        "added_physical_damage": 6,
        "movement_speed": 8,
        "flask_charges": 6,
        "cooldown_recovery": 6,
    },
}


class RareEvaluationConfigWindow(tk.Toplevel):
    """
    Configuration window for rare item evaluation settings.
    
    Features:
    - Affix weight adjustment (1-10 slider)
    - Minimum value thresholds
    - Build-focused presets
    - Save/load from JSON
    """
    
    def __init__(
        self,
        master: tk.Misc,
        data_dir: Path,
        on_save_callback: Optional[Callable[[], None]] = None
    ):
        super().__init__(master)
        
        self.data_dir = data_dir
        self.on_save_callback = on_save_callback
        
        # Data file path
        self.config_file = self.data_dir / "valuable_affixes.json"
        
        # Current configuration
        self.current_config: Dict[str, Any] = {}
        self.affix_vars: Dict[str, Dict[str, tk.Variable]] = {}
        
        # Window setup
        self.title("Rare Item Evaluation Settings")
        self.transient(master)
        self.resizable(True, True)
        self.geometry("700x600")
        
        # Load current config
        self._load_config()
        
        # Create UI
        self._create_ui()
        
        # Center on parent
        self._center_on_parent()
        
        # Make modal
        self.grab_set()
        self.focus_set()
    
    def _center_on_parent(self):
        """Center the window over the parent."""
        self.update_idletasks()
        
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_w = self.master.winfo_width()
        parent_h = self.master.winfo_height()
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2
        
        self.geometry(f"+{x}+{y}")
    
    def _load_config(self):
        """Load current configuration from JSON file."""
        if not self.config_file.exists():
            messagebox.showwarning(
                "Config Not Found",
                f"Configuration file not found:\n{self.config_file}\n\n"
                "Using default values."
            )
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.current_config = json.load(f)
        except Exception as e:
            messagebox.showerror(
                "Load Error",
                f"Failed to load configuration:\n{e}\n\n"
                "Using default values."
            )
    
    def _create_ui(self):
        """Create the main UI with tabs."""
        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        
        # Notebook (tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Tab 1: Affix Weights
        self.affixes_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.affixes_tab, text="Affix Weights")
        self._create_affixes_tab(self.affixes_tab)
        
        # Tab 2: Presets
        self.presets_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.presets_tab, text="Presets")
        self._create_presets_tab(self.presets_tab)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky="ew")
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._on_save
        ).grid(row=0, column=0, padx=(0, 4))
        
        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._on_reset
        ).grid(row=0, column=1, padx=(0, 4))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).grid(row=0, column=2)
        
        button_frame.columnconfigure(3, weight=1)
    
    def _create_affixes_tab(self, parent: ttk.Frame):
        """Create the affix weights tab with scrollable sliders."""
        # Create scrollable canvas
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Header
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="Adjust affix weights (1-10) and minimum value thresholds:",
            font=("", 10, "bold")
        ).pack(anchor="w")
        
        # Create controls for each affix
        row = 1
        for affix_key, affix_data in self.current_config.items():
            if affix_key.startswith("_"):  # Skip metadata keys like _comment
                continue
            
            if not isinstance(affix_data, dict):
                continue
            
            # Affix label
            affix_name = affix_key.replace("_", " ").title()
            ttk.Label(
                scrollable_frame,
                text=affix_name,
                font=("", 9, "bold")
            ).grid(row=row, column=0, sticky="w", padx=(10, 10), pady=(8, 2))
            
            # Weight slider
            weight_frame = ttk.Frame(scrollable_frame)
            weight_frame.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=(8, 2))
            
            ttk.Label(weight_frame, text="Weight:").pack(side="left")
            
            weight_var = tk.IntVar(value=affix_data.get("weight", 5))
            weight_slider = ttk.Scale(
                weight_frame,
                from_=1,
                to=10,
                orient="horizontal",
                variable=weight_var,
                length=150
            )
            weight_slider.pack(side="left", padx=(5, 5))
            
            weight_label = ttk.Label(weight_frame, text=str(weight_var.get()), width=3)
            weight_label.pack(side="left")
            
            # Update label when slider changes
            weight_slider.configure(
                command=lambda v, label=weight_label: label.config(text=str(int(float(v))))
            )
            
            # Min value entry
            min_frame = ttk.Frame(scrollable_frame)
            min_frame.grid(row=row, column=2, sticky="ew", padx=(0, 10), pady=(8, 2))
            
            ttk.Label(min_frame, text="Min Value:").pack(side="left")
            
            min_var = tk.IntVar(value=affix_data.get("min_value", 0))
            min_entry = ttk.Entry(min_frame, textvariable=min_var, width=8)
            min_entry.pack(side="left", padx=(5, 0))
            
            # Store references
            self.affix_vars[affix_key] = {
                "weight": weight_var,
                "min_value": min_var
            }
            
            row += 1
        
        # Configure column weights
        scrollable_frame.columnconfigure(0, weight=1, minsize=150)
        scrollable_frame.columnconfigure(1, weight=2, minsize=200)
        scrollable_frame.columnconfigure(2, weight=1, minsize=150)
    
    def _create_presets_tab(self, parent: ttk.Frame):
        """Create the presets tab with build-focused configurations."""
        # Header
        header_frame = ttk.Frame(parent, padding=10)
        header_frame.pack(fill="x")
        
        ttk.Label(
            header_frame,
            text="Quick Presets for Common Build Archetypes",
            font=("", 10, "bold")
        ).pack(anchor="w", pady=(0, 5))
        
        ttk.Label(
            header_frame,
            text="Click a preset to apply its weights to all affixes.",
            font=("", 9)
        ).pack(anchor="w")
        
        # Separator
        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)
        
        # Preset buttons frame
        presets_frame = ttk.Frame(parent, padding=10)
        presets_frame.pack(fill="both", expand=True)
        
        row = 0
        for preset_name, preset_weights in PRESETS.items():
            # Preset button
            preset_button = ttk.Button(
                presets_frame,
                text=preset_name,
                command=lambda p=preset_weights: self._apply_preset(p),
                width=25
            )
            preset_button.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            
            # Description
            description = self._get_preset_description(preset_name)
            ttk.Label(
                presets_frame,
                text=description,
                font=("", 9),
                foreground="#555555"
            ).grid(row=row, column=1, sticky="w", pady=5)
            
            row += 1
        
        presets_frame.columnconfigure(1, weight=1)
    
    def _get_preset_description(self, preset_name: str) -> str:
        """Get a description for a preset."""
        descriptions = {
            "Life/Res Tank": "Maximizes life and resistances for survivability",
            "ES Caster": "Optimized for energy shield and spell damage",
            "Physical DPS": "Focuses on physical damage and crit for attack builds",
            "Spell Suppression": "High value on spell suppression for evasion builds",
            "Balanced": "Equal weighting across all defensive and offensive stats"
        }
        return descriptions.get(preset_name, "")
    
    def _apply_preset(self, preset_weights: Dict[str, int]):
        """Apply a preset configuration to all affix weights."""
        for affix_key, weight in preset_weights.items():
            if affix_key in self.affix_vars:
                self.affix_vars[affix_key]["weight"].set(weight)
        
        messagebox.showinfo(
            "Preset Applied",
            "Preset has been applied to all affix weights.\n\n"
            "Click 'Save' to apply these changes."
        )
    
    def _on_save(self):
        """Save the current configuration to JSON and call the callback."""
        # Update config with current values
        for affix_key, vars_dict in self.affix_vars.items():
            if affix_key in self.current_config:
                self.current_config[affix_key]["weight"] = vars_dict["weight"].get()
                self.current_config[affix_key]["min_value"] = vars_dict["min_value"].get()
        
        # Write to file
        try:
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=2)
            
            messagebox.showinfo(
                "Saved",
                f"Configuration saved to:\n{self.config_file}"
            )
            
            # Call the callback to reload evaluator
            if self.on_save_callback:
                try:
                    self.on_save_callback()
                except Exception as e:
                    messagebox.showwarning(
                        "Reload Warning",
                        f"Settings saved, but failed to reload evaluator:\n{e}"
                    )
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Failed to save configuration:\n{e}"
            )
    
    def _on_reset(self):
        """Reset all weights to default values."""
        if not messagebox.askyesno(
            "Reset to Defaults",
            "This will reset all affix weights to their default values.\n\n"
            "Are you sure?"
        ):
            return
        
        # Apply default weights (from Balanced preset as baseline)
        default_weights = PRESETS["Balanced"]
        
        for affix_key in self.affix_vars:
            if affix_key in default_weights:
                self.affix_vars[affix_key]["weight"].set(default_weights[affix_key])
        
        messagebox.showinfo(
            "Reset Complete",
            "All weights have been reset to default values.\n\n"
            "Click 'Save' to apply these changes."
        )
