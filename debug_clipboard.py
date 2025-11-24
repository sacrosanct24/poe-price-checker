"""
Clipboard diagnostic tool to help debug parser issues.

Run this script, then copy an item from PoE and it will show you:
1. The raw clipboard text
2. What the parser thinks about it
3. Any issues it finds
"""

import tkinter as tk
from core.item_parser import ItemParser

def debug_clipboard():
    print("=" * 80)
    print("POE ITEM CLIPBOARD DEBUGGER")
    print("=" * 80)
    print("\nInstructions:")
    print("1. Copy an item from Path of Exile (Ctrl+C)")
    print("2. Press ENTER here")
    print("3. See what the parser receives and what it does with it")
    print("\n" + "=" * 80)
    
    input("\nPress ENTER after copying an item from PoE...")
    
    # Get clipboard content
    root = tk.Tk()
    root.withdraw()
    
    try:
        clipboard_text = root.clipboard_get()
    except tk.TclError:
        print("\n❌ ERROR: Could not read clipboard")
        return
    finally:
        root.destroy()
    
    print("\n" + "=" * 80)
    print("CLIPBOARD CONTENT")
    print("=" * 80)
    print(f"Length: {len(clipboard_text)} characters")
    print(f"Lines: {len(clipboard_text.splitlines())}")
    print("\nRaw text:")
    print("-" * 80)
    print(clipboard_text)
    print("-" * 80)
    
    # Show first line in detail
    lines = clipboard_text.splitlines()
    if lines:
        first_line = lines[0]
        print(f"\nFirst line: '{first_line}'")
        print(f"First line repr: {repr(first_line)}")
        print(f"Starts with 'Rarity:': {first_line.strip().startswith('Rarity:')}")
    
    # Try parsing
    print("\n" + "=" * 80)
    print("PARSER RESULT")
    print("=" * 80)
    
    parser = ItemParser()
    result = parser.parse(clipboard_text)
    
    if result is None:
        print("❌ PARSER FAILED - returned None")
        print("\nPossible issues:")
        print("- Text doesn't start with 'Rarity:'")
        print("- Text is empty or malformed")
        print("- Item structure is invalid")
        
        # Try to give helpful feedback
        if not lines:
            print("\n⚠️  Clipboard appears to be empty")
        elif not lines[0].strip().startswith("Rarity:"):
            print(f"\n⚠️  First line doesn't start with 'Rarity:'")
            print(f"   Instead it is: '{lines[0]}'")
        
    else:
        print("✅ PARSER SUCCESS")
        print(f"\nParsed item:")
        print(f"  Rarity: {result.rarity}")
        print(f"  Name: {result.name}")
        print(f"  Base Type: {result.base_type}")
        print(f"  Display Name: {result.get_display_name()}")
        print(f"  Item Level: {result.item_level}")
        print(f"  Quality: {result.quality}")
        print(f"  Corrupted: {result.is_corrupted}")
        
        if result.gem_level or result.gem_quality:
            print(f"  Gem Level: {result.gem_level}")
            print(f"  Gem Quality: {result.gem_quality}")
        
        if result.explicits:
            print(f"  Explicit Mods: {len(result.explicits)}")
        if result.implicits:
            print(f"  Implicit Mods: {len(result.implicits)}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        debug_clipboard()
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nPress ENTER to exit...")
    input()
