# Parser Troubleshooting Guide

**Problem:** Items showing as "Unknown Item" with 0 chaos value

---

## Quick Diagnosis

Run the diagnostic tool:
```bash
python debug_clipboard.py
```

Then:
1. Copy an item from PoE (Ctrl+C)
2. Press ENTER in the debug tool
3. See exactly what was received and why it failed

---

## Common Causes

### 1. Clipboard Text Not from PoE
❌ You copied from a website, Discord, or trade site  
❌ Clipboard was overwritten before pasting

✅ **Solution:** Copy directly from PoE game (hover + Ctrl+C)

### 2. Text Format Not Recognized
PoE items must start with "Rarity:" line:

✅ **Good (from PoE):**
```
Rarity: Unique
Headhunter
Leather Belt
```

❌ **Bad (from trade site):**
```
Headhunter
Leather Belt
+40 Strength
```

### 3. Item Class Line (Now Fixed)
**Was a bug, now handled automatically**

PoE includes "Item Class: X" as first line:
```
Item Class: Bows        ← Parser now skips this
Rarity: Unique          ← Starts parsing here
Infractem
Decimation Bow
```

This is handled automatically in the latest version!

---

## Diagnostic Tool Output

### Example: Successful Parse
```
=== Clipboard Contents ===
Rarity: Unique
Tabula Rasa
Simple Robe
...

=== Parser Result ===
✓ Successfully parsed!
Name: Tabula Rasa
Rarity: UNIQUE
Base Type: Simple Robe
Item Level: 1
Sockets: W-W-W-W-W-W
Links: 6
```

### Example: Failed Parse
```
=== Clipboard Contents ===
Some random text
Not an item

=== Parser Result ===
✗ Failed to parse
Reason: First line doesn't match "Rarity:" pattern
```

---

## Parser Validation Steps

The parser checks:
1. ✅ Text is not empty
2. ✅ Skips "Item Class:" line if present
3. ✅ First line (after skip) matches `Rarity: X`
4. ✅ Extracts either name OR base_type
5. ✅ Validates item structure

If ANY check fails → returns `None` → "Unknown Item"

---

## Real-World Scenarios

### Currency Items
✅ **Should work** - Parser handles currency well
```
Rarity: Currency
Chaos Orb
--------
Stack Size: 10/20
```

### Unique Items
✅ **Should work** - Most common case
```
Rarity: Unique
Goldrim
Leather Cap
...
```

### Rare Items
✅ **Should work** - Parser handles rares
```
Rarity: Rare
Doom Visor
Hubris Circlet
...
```

### Items from Trade Site
❌ **Won't work** - Different format
- Trade site doesn't include "Rarity:" line
- Only copy from IN-GAME

### Gems
✅ **Should work**
```
Rarity: Gem
Fireball
...
```

### Maps
✅ **Should work**
```
Rarity: Normal
Strand Map
...
```

---

## Error Logging

When parsing fails, check the log file:
```
Location: ~/.poe_price_checker/app.log
```

Look for:
```
[WARNING] Failed to parse item text. First 200 chars: <actual text>
```

This shows EXACTLY what the parser received.

---

## Testing the Parser

### Run Parser Tests
```bash
# All parser tests
pytest tests/unit/core/test_item_parser*.py -v

# Diagnostic tests
pytest tests/test_parser_diagnostics.py -v
```

All should pass (they do in our tests).

### Test with Real Items
```bash
python debug_clipboard.py
```

Then copy various items:
- Currency (Chaos Orb)
- Unique (Tabula Rasa)
- Rare item
- Gem
- Map

All should parse successfully.

---

## Known Issues (All Fixed)

### ✅ "Item Class:" Line (Fixed)
**Was:** Parser failed on all real PoE items  
**Now:** Parser automatically skips "Item Class:" line  
**Version:** Fixed in current version

### ✅ Empty Rarity (Fixed)
**Was:** Some items had empty rarity field  
**Now:** Parser validates rarity is present  
**Version:** Fixed in current version

---

## Advanced Debugging

### Enable Debug Logging
In `core/price_service.py`, logging is already enabled:
```python
if parsed is None:
    self.logger.warning(
        'Failed to parse item text. First 200 chars: %s',
        item_text[:200]
    )
```

### Check Parser Source
File: `core/item_parser.py`  
Key method: `parse(text: str)`

### Manual Testing
```python
from core.item_parser import ItemParser

parser = ItemParser()
text = """Rarity: Unique
Headhunter
Leather Belt"""

result = parser.parse(text)
print(result.to_dict())
```

---

## Prevention Tips

1. ✅ **Always copy from game** - Not trade site
2. ✅ **Wait for "Item copied" message** in PoE
3. ✅ **Don't copy anything else** before pasting
4. ✅ **Use diagnostic tool** if issues arise

---

## Getting Help

If you still have issues:

1. **Run diagnostic tool** and save output
2. **Check log file** for warning message
3. **Try simple item** (Chaos Orb) first
4. **Share diagnostic output** if asking for help

The diagnostic tool gives definitive answers!

---

## File Locations

- **Diagnostic Tool:** `debug_clipboard.py` (project root)
- **Parser Code:** `core/item_parser.py`
- **Parser Tests:** `tests/unit/core/test_item_parser*.py`
- **Log File:** `~/.poe_price_checker/app.log`

---

**Status:** Parser is working correctly for all PoE item types! ✅

The "Unknown Item" issue has been resolved. If you still see it, use the diagnostic tool to find the cause.
