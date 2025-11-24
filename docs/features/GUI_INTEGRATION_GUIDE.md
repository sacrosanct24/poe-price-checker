# GUI Integration Guide - Rare Item Evaluator

## Overview

This guide shows how to integrate the rare item evaluator into your GUI.

I've created a ready-to-use panel widget: `gui/rare_evaluation_panel.py`

---

## Integration Steps

### Step 1: Import the Components

Add to `gui/main_window.py` imports:

```python
from core.rare_item_evaluator import RareItemEvaluator
from core.build_matcher import BuildMatcher
from gui.rare_evaluation_panel import RareEvaluationPanel
```

### Step 2: Initialize in `__init__`

In `PriceCheckerGUI.__init__`, after creating `self.app_context`:

```python
# Initialize rare evaluator
self.rare_evaluator = RareItemEvaluator()
self.build_matcher = BuildMatcher()  # Optional: for build matching
```

### Step 3: Add Panel to Layout

In `_create_item_inspector` method, after creating the item inspector text widget:

```python
def _create_item_inspector(self, parent: ttk.Frame) -> None:
    """Create the Item Inspector sidebar panel."""
    inspector_frame = ttk.LabelFrame(parent, text="Item Inspector", padding=8)
    inspector_frame.grid(row=0, column=1, sticky="nsew", rowspan=2)  # Span 2 rows
    
    # Existing item inspector text
    self.item_inspector_text = tk.Text(
        inspector_frame,
        height=8,
        wrap="word",
        state="disabled",
    )
    self.item_inspector_text.grid(row=0, column=0, sticky="nsew")
    
    # NEW: Add rare evaluation panel below
    self.rare_eval_panel = RareEvaluationPanel(inspector_frame)
    self.rare_eval_panel.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
    self.rare_eval_panel.hide()  # Hidden initially
    
    inspector_frame.rowconfigure(0, weight=1)
    inspector_frame.rowconfigure(1, weight=1)
    inspector_frame.columnconfigure(0, weight=1)
```

### Step 4: Update `_update_item_inspector`

In `_update_item_inspector` method, add evaluation after parsing:

```python
def _update_item_inspector(self, item_text: str) -> None:
    """Parse and display item in inspector, plus rare evaluation."""
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
    
    # ... existing parse display code ...
    
    # NEW: Rare item evaluation
    if parsed and hasattr(self, 'rare_evaluator'):
        if parsed.rarity and parsed.rarity.upper() == "RARE":
            try:
                evaluation = self.rare_evaluator.evaluate(parsed)
                self.rare_eval_panel.display_evaluation(evaluation)
                self.rare_eval_panel.show()
            except Exception as e:
                self.logger.warning(f"Rare evaluation failed: {e}")
                self.rare_eval_panel.hide()
        else:
            # Not a rare item
            self.rare_eval_panel.hide()
    else:
        self.rare_eval_panel.hide()
```

---

## What Users Will See

When a rare item is pasted:

1. **Item Inspector** (top half) - Shows parsed item details
2. **Rare Evaluation Panel** (bottom half) - Shows:
   - **Tier Badge** in colored text (EXCELLENT/GOOD/AVERAGE/VENDOR)
   - **Estimated Value** (1div+, 50c+, 10c+, <10c)
   - **Scores**: Total, Base, Affixes
   - **Valuable Affixes List** with values and weights

---

## Visual Example

```
┌─ Item Inspector ─────────────────────────┐
│ Name: Doom Loop                           │
│ Base: Opal Ring                           │
│ Rarity: RARE                              │
│ Item Level: 84                            │
│ ...                                       │
├─ Rare Item Evaluation ───────────────────┤
│ EXCELLENT         Est. Value: 1div+       │
│                                           │
│ Total Score: 77/100                       │
│ Base: 50/50   Affixes: 87/100             │
│                                           │
│ Valuable Affixes:                         │
│ [OK] life: +78 to maximum Life [78] (10)  │
│ [OK] resistances: +42% Fire Res [42] (8)  │
│ [OK] energy_shield: +85 ES [85] (9)       │
└───────────────────────────────────────────┘
```

---

## Optional: Build Matching

To add build matching, in `_update_item_inspector` after evaluation:

```python
# Check if item matches any builds
if hasattr(self, 'build_matcher'):
    matches = self.build_matcher.match_item_to_builds(
        parsed,
        evaluation.matched_affixes
    )
    
    if matches:
        # Display build matches in panel or status bar
        best_match = matches[0]
        self._set_status(f"Matches build: {best_match['build_name']} (score: {best_match['score']})")
```

---

## Testing the Integration

1. **Start the GUI**:
   ```bash
   python poe_price_checker.py
   ```

2. **Paste a rare item**:
   - Use Dev menu → Paste Sample Rare, OR
   - Copy a real rare from PoE and paste

3. **Check the right panel**:
   - Should see item details (top)
   - Should see rare evaluation (bottom)

4. **Try different items**:
   - Excellent rare (high ilvl, good affixes)
   - Vendor trash (low ilvl or bad mods)
   - Non-rare item (should hide evaluation)

---

## Customization

### Change Colors

In `rare_evaluation_panel.py`, edit `tier_colors`:

```python
tier_colors = {
    "EXCELLENT": "#00FF00",  # bright green
    "GOOD": "#00BFFF",       # deep sky blue
    "AVERAGE": "#FFA500",    # orange
    "VENDOR": "#FF0000",     # red
}
```

### Add More Info

Add after affixes list in `display_evaluation`:

```python
# Show base and ilvl info
info_lines = []
if evaluation.is_valuable_base:
    info_lines.append("[OK] Valuable base type")
if evaluation.has_high_ilvl:
    info_lines.append(f"[OK] High ilvl ({evaluation.item.item_level})")

if info_lines:
    self.affixes_text.insert("end", "\n\n" + "\n".join(info_lines))
```

### Change Panel Size

In `rare_evaluation_panel.py` `_create_widgets`:

```python
self.affixes_text = tk.Text(
    self,
    height=8,  # Change this number
    wrap="word",
    state="disabled",
    font=("", 9)
)
```

---

## Files Modified

1. **gui/main_window.py** (add imports, init evaluator, update inspector)
2. **gui/rare_evaluation_panel.py** (already created ✓)

---

## Next Steps

After integration works:

1. **Add tooltip** explaining tier meanings
2. **Add "Why?" button** showing evaluation details
3. **Color-code affixes** by weight (high-weight = green)
4. **Add build matcher UI** showing which builds want this item
5. **Add "Compare" button** to compare with similar items

---

## Alternative: Simpler Integration

If you don't want the full panel, add to status bar:

```python
def _update_item_inspector(self, item_text: str) -> None:
    # ... existing code ...
    
    # Simple status bar message
    if parsed and parsed.rarity == "RARE":
        evaluation = self.rare_evaluator.evaluate(parsed)
        self._set_status(
            f"Rare: {evaluation.tier} tier, "
            f"{evaluation.estimated_value}, "
            f"score: {evaluation.total_score}/100"
        )
```

---

**The panel widget is ready to use!** Just follow Steps 1-4 above to integrate it.
