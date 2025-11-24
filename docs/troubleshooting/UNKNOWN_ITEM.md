# Troubleshooting "Unknown Item" Issues

## Problem
The app shows "Unknown Item" with 0 chaos value and empty rarity.

## Log Evidence
```
[INFO] poe.ninja: no price found for 'Unknown Item' (rarity=)
[INFO] TradeApiSource._check_parsed_item: parsed_item is None
[INFO] PriceService._save_trade_quotes_for_check: item_name=<unknown>
```

## Root Cause
The item parser is returning `None`, which means it couldn't parse the clipboard text.

## Why This Happens

1. **Clipboard text isn't from PoE**
   - You copied something else (a website, Discord message, etc.)
   - The clipboard was overwritten before pasting

2. **Text doesn't start with "Rarity:"**
   - PoE items always start with "Rarity: Normal/Magic/Rare/Unique/etc."
   - If missing, the parser rejects it immediately

3. **Text is empty or corrupted**
   - Clipboard encoding issues (rare on Windows)
   - Very unusual item formats the parser doesn't recognize

## How to Fix

### Step 1: Use the Debug Tool

Run this in your project directory:
```bash
python debug_clipboard.py
```

Then:
1. Copy an item from PoE (Ctrl+C while hovering over it)
2. Press ENTER in the debug tool
3. It will show you EXACTLY what text was received and why parsing failed

### Step 2: Check the Item in PoE

Make sure you're:
- ✅ Hovering over the item
- ✅ Pressing Ctrl+C (not just clicking)
- ✅ Seeing the "Item copied" message in PoE
- ✅ Not copying anything else before pasting

### Step 3: Try Different Items

Test with simple items first:
- ✅ Currency (Chaos Orb, Divine Orb)
- ✅ Common uniques (Tabula Rasa, Goldrim)  
- ✅ Normal maps

If these fail too, it's a clipboard issue.
If only specific items fail, there might be a parser bug.

## Improvements Made

### Better Error Logging
The price service now logs the first 200 characters of failed parse attempts:

```python
[WARNING] Failed to parse item text. First 200 chars: <shows actual text>
```

This will appear in your log file (`~/.poe_price_checker/app.log`)

### Debug Tool
`debug_clipboard.py` - Shows exactly what the clipboard contains and how the parser interprets it.

### Parser Validation
The parser validates that items have:
- A "Rarity:" line at the start
- At least a name OR base type
- Proper structure with separator lines

## Common Scenarios

### "Unknown Item" After Copying Currency
✅ Should work fine - if it doesn't, run the debug tool

### "Unknown Item" After Copying Rare Item
✅ Should work - parser handles rare items well

### "Unknown Item" After Copying from Trade Site
❌ Expected - trade site format is different from game clipboard format
⚠️ Only copy items from IN-GAME, not from pathofexile.com/trade

### "Unknown Item" After Alt-Tabbing
⚠️ Clipboard might have been overwritten
Solution: Copy the item again after tabbing back to the app

## Testing Parser with Real Items

Run the parser diagnostic tests:
```bash
python -m pytest tests/test_parser_diagnostics.py -v
```

This tests:
- Currency
- Uniques
- Rare items
- Gems
- Maps

All should pass (they do in our tests).

## Next Steps

1. **Run `debug_clipboard.py`** - This will tell you exactly what's wrong
2. **Check the log file** - Look for the WARNING about failed parse
3. **Share the debug output** - If you're still stuck, share what the debug tool shows

## Example: Good vs Bad Clipboard Text

### ✅ Good (from PoE game):
```
Rarity: Unique
Goldrim
Leather Cap
--------
Evasion Rating: 33
--------
+30% to all Elemental Resistances
```

### ❌ Bad (from trade site):
```
Goldrim
Leather Cap
33 Evasion
+30% to all Elemental Resistances
```
^^ Missing "Rarity:" line - parser will reject this

### ❌ Bad (random text):
```
Just some text
Not an item
```
^^ Obviously not an item format

## Technical Details

### Parser Validation Steps
1. ✅ Text must not be empty
2. ✅ First line must match `^Rarity:\s*(\w+)`
3. ✅ Must extract either a name OR base_type
4. ✅ Item must survive structure validation

If ANY of these fail → parser returns None → "Unknown Item"

### What Happens with None
```python
parsed = self.parser.parse(item_text)
if parsed is None:
    # Now logs warning with first 200 chars
    return []  # Empty result list
```

The GUI then shows empty results or "Unknown Item" placeholder.

## File Locations

- **Log file**: `~/.poe_price_checker/app.log`
- **Debug tool**: `debug_clipboard.py` (project root)
- **Parser code**: `core/item_parser.py`
- **Parser tests**: `tests/test_parser_diagnostics.py`

## Still Having Issues?

1. Run the debug tool and save the output
2. Check the log file for the WARNING message
3. Try copying a simple currency item (Chaos Orb)
4. Make sure you're copying FROM THE GAME, not from trade websites

The debug tool will give you definitive answers!
