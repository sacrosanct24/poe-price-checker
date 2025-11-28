---
title: Keyboard Shortcuts
status: current
stability: stable
last_reviewed: 2025-11-28
---

# Keyboard Shortcuts

Quick reference for all keyboard shortcuts in PoE Price Checker.

## Quick Reference

| Shortcut | Action | Category |
|----------|--------|----------|
| F1 | Show Keyboard Shortcuts | General |
| Ctrl+K | Command Palette | General |
| Alt+F4 | Exit Application | General |
| Ctrl+Return | Check Price | Price Checking |
| Ctrl+Shift+V | Paste and Check | Price Checking |
| Ctrl+L | Clear Input | Price Checking |
| Ctrl+B | PoB Characters | Build & PoB |
| Ctrl+Shift+B | BiS Search | Build & PoB |
| Ctrl+Shift+I | Compare Items | Build & PoB |
| Ctrl+H | History | Navigation |
| Ctrl+Shift+S | Stash Viewer | Navigation |
| Ctrl+Shift+T | Toggle Theme | View & Theme |

## Categories

### General

| Shortcut | Action | Description |
|----------|--------|-------------|
| F1 | Keyboard Shortcuts | Show this shortcuts reference dialog |
| Ctrl+K | Command Palette | Open command palette for quick actions |
| Alt+F4 | Exit | Close the application |

### Price Checking

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+Return | Check Price | Price check the current item in the input area |
| Ctrl+Shift+V | Paste and Check | Paste from clipboard and immediately price check |
| Ctrl+L | Clear Input | Clear the item input area |

### Build & PoB

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+B | PoB Characters | Open PoB character/build management window |
| Ctrl+Shift+B | BiS Search | Open Best-in-Slot search dialog |
| Ctrl+Shift+I | Compare Items | Open side-by-side item comparison dialog |

### Navigation

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+H | History | Open price check history |
| Ctrl+Shift+S | Stash Viewer | Open stash tab viewer |

### View & Theme

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl+Shift+T | Toggle Theme | Switch between dark and light themes |

## Command Palette

The Command Palette (Ctrl+K) provides quick access to all actions:

1. Press **Ctrl+K** to open
2. Type to filter actions
3. Click or press Enter to execute

The palette shows:
- Action name and description
- Keyboard shortcut (if assigned)
- Category for organization

## Customizing Shortcuts (Future)

Shortcut customization is planned for a future release. The system supports:
- Custom key bindings per action
- Saving/loading custom configurations
- Reset to defaults

## Technical Details

### ShortcutManager

The shortcuts system uses a centralized `ShortcutManager` singleton:

```python
from gui_qt.shortcuts import get_shortcut_manager

manager = get_shortcut_manager()

# Register a callback
manager.register("show_shortcuts", show_shortcuts_dialog)

# Get current key binding
key = manager.get_key("check_price")  # Returns "Ctrl+Return"

# Trigger an action programmatically
manager.trigger("show_shortcuts")
```

### Adding New Shortcuts

To add a new shortcut to the system:

1. Define it in `gui_qt/shortcuts.py`:
```python
ShortcutDef(
    action_id="my_action",
    name="My Action",
    description="Does something useful",
    default_key="Ctrl+Shift+M",
    category=ShortcutCategory.GENERAL,
)
```

2. Register the handler in your window/dialog:
```python
shortcut_manager.register("my_action", self._my_action_handler)
```

3. The shortcut will automatically appear in:
   - The shortcuts help dialog (F1)
   - The command palette (Ctrl+K)

### Global Shortcuts

Some shortcuts are marked as `is_global=True`, meaning they work even when the application doesn't have focus. Currently, all shortcuts require the application to be focused.

## Related Features

- [Item Comparison Guide](ITEM_COMPARISON_GUIDE.md) - Ctrl+Shift+I
- [BiS Search Guide](BIS_SEARCH_GUIDE.md) - Ctrl+Shift+B
- [Rare Evaluator Quick Start](RARE_EVALUATOR_QUICK_START.md) - Price checking workflow
