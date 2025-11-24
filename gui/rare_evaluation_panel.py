"""
Rare evaluation panel widget for GUI.

Shows rare item evaluation results in a dedicated panel.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Any

from core.rare_item_evaluator import RareItemEvaluation


class RareEvaluationPanel(ttk.LabelFrame):
    """
    Panel that displays rare item evaluation results.
    
    Shows:
    - Tier badge (Excellent/Good/Average/Vendor)
    - Estimated value
    - Score breakdown
    - Matched affixes
    - Build matches (if available)
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="Rare Item Evaluation", padding=8, **kwargs)
        
        self._create_widgets()
        self._evaluation: Optional[RareItemEvaluation] = None
        
        # Show empty state initially
        self.clear()
    
    def _create_widgets(self):
        """Create all UI elements."""
        # Tier badge and value (row 0)
        tier_frame = ttk.Frame(self)
        tier_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        self.tier_label = ttk.Label(
            tier_frame,
            text="",
            font=("", 12, "bold")
        )
        self.tier_label.grid(row=0, column=0, sticky="w")
        
        self.value_label = ttk.Label(
            tier_frame,
            text="",
            font=("", 10)
        )
        self.value_label.grid(row=0, column=1, sticky="w", padx=(12, 0))
        
        tier_frame.columnconfigure(1, weight=1)
        
        # Scores (row 1)
        score_frame = ttk.Frame(self)
        score_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        
        ttk.Label(score_frame, text="Total Score:").grid(row=0, column=0, sticky="w")
        self.total_score_label = ttk.Label(score_frame, text="")
        self.total_score_label.grid(row=0, column=1, sticky="w", padx=(4, 0))
        
        ttk.Label(score_frame, text="Base:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.base_score_label = ttk.Label(score_frame, text="")
        self.base_score_label.grid(row=0, column=3, sticky="w", padx=(4, 0))
        
        ttk.Label(score_frame, text="Affixes:").grid(row=0, column=4, sticky="w", padx=(12, 0))
        self.affix_score_label = ttk.Label(score_frame, text="")
        self.affix_score_label.grid(row=0, column=5, sticky="w", padx=(4, 0))
        
        # Affixes list (row 2)
        affixes_label = ttk.Label(self, text="Valuable Affixes:")
        affixes_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 4))
        
        # Scrollable text widget for affixes
        self.affixes_text = tk.Text(
            self,
            height=6,
            wrap="word",
            state="disabled",
            font=("", 9)
        )
        self.affixes_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        
        affixes_scroll = ttk.Scrollbar(self, orient="vertical", command=self.affixes_text.yview)
        affixes_scroll.grid(row=3, column=2, sticky="ns")
        self.affixes_text.configure(yscrollcommand=affixes_scroll.set)
        
        # Configure row/column weights
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
    
    def display_evaluation(self, evaluation: RareItemEvaluation):
        """
        Display evaluation results.
        
        Args:
            evaluation: RareItemEvaluation object
        """
        self._evaluation = evaluation
        
        # Update tier badge
        tier = evaluation.tier.upper()
        tier_colors = {
            "EXCELLENT": "#006400",  # dark green
            "GOOD": "#0000CD",        # medium blue
            "AVERAGE": "#FF8C00",     # dark orange
            "VENDOR": "#8B0000",      # dark red
            "NOT_RARE": "#808080"     # gray
        }
        color = tier_colors.get(tier, "#000000")
        self.tier_label.config(text=tier, foreground=color)
        
        # Update value
        self.value_label.config(text=f"Est. Value: {evaluation.estimated_value}")
        
        # Update scores
        self.total_score_label.config(text=f"{evaluation.total_score}/100")
        self.base_score_label.config(text=f"{evaluation.base_score}/50")
        self.affix_score_label.config(text=f"{evaluation.affix_score}/100")
        
        # Update affixes list
        self.affixes_text.configure(state="normal")
        self.affixes_text.delete("1.0", "end")
        
        if evaluation.matched_affixes:
            lines = []
            for match in evaluation.matched_affixes:
                value_str = f" [{int(match.value)}]" if match.value else ""
                weight_str = f" (weight: {match.weight})"
                line = f"[OK] {match.affix_type}: {match.mod_text}{value_str}{weight_str}"
                lines.append(line)
            
            self.affixes_text.insert("1.0", "\n".join(lines))
        else:
            self.affixes_text.insert("1.0", "No valuable affixes found.\n\nThis item has:")
            
            reasons = []
            if not evaluation.is_valuable_base:
                reasons.append("- Not a high-tier base type")
            if not evaluation.has_high_ilvl:
                reasons.append("- Item level too low (need 84+)")
            if not evaluation.matched_affixes:
                reasons.append("- No high-tier affixes above minimum thresholds")
            
            if reasons:
                self.affixes_text.insert("end", "\n\n" + "\n".join(reasons))
        
        self.affixes_text.configure(state="disabled")
        
        # Show the panel
        self.grid()
    
    def clear(self):
        """Clear the evaluation display."""
        self._evaluation = None
        
        self.tier_label.config(text="", foreground="#000000")
        self.value_label.config(text="")
        self.total_score_label.config(text="")
        self.base_score_label.config(text="")
        self.affix_score_label.config(text="")
        
        self.affixes_text.configure(state="normal")
        self.affixes_text.delete("1.0", "end")
        self.affixes_text.insert("1.0", "Paste a rare item to see evaluation...")
        self.affixes_text.configure(state="disabled")
    
    def hide(self):
        """Hide the panel."""
        self.grid_remove()
    
    def show(self):
        """Show the panel."""
        self.grid()
