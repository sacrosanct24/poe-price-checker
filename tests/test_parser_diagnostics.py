"""
Diagnostic tests to help debug parser issues in real-world usage.
Run this to test various item formats and see what fails.
"""
from __future__ import annotations

import pytest
from core.item_parser import ItemParser

# Real-world samples that should work
REAL_WORLD_SAMPLES = {
    "currency": """Rarity: Currency
Chaos Orb
--------
Stack Size: 5/10
--------
Reforges a rare item with new random modifiers
--------
Right click this item then left click a rare item to apply it.""",
    
    "unique": """Rarity: Unique
Goldrim
Leather Cap
--------
Evasion Rating: 33
--------
Requires Level 1
--------
+30% to all Elemental Resistances
10% increased Rarity of Items found
--------
The heart of gold is a currency in itself.""",
    
    "rare_item": """Rarity: Rare
Doom Visor
Hubris Circlet
--------
Energy Shield: 120
--------
Requires Level 69, 154 Int
--------
Item Level: 84
--------
+50 to maximum Life
+30% to Fire Resistance
+25% to Cold Resistance""",
    
    "gem": """Rarity: Gem
Cyclone
--------
Attack, AoE, Movement, Channeling, Melee
Level: 20
Quality: +20%
Mana Cost: 2
--------
Requires Level 28, 68 Str
--------
Deals 48% of Base Damage
38% increased Attack Speed""",
    
    "map": """Rarity: Normal
Strand Map
--------
Map Tier: 5
Item Level: 72
--------
Travel to this Map by using it in a personal Map Device.""",

    "influenced_rare_boots": """Item Class: Boots
Rarity: Rare
Carrion Spark
Precursor Greaves
--------
Quality: +20% (augmented)
Armour: 582 (augmented)
--------
Requirements:
Level: 78
Str: 155
--------
Sockets: R-R-R-R 
--------
Item Level: 81
--------
7% increased Life Regeneration rate (implicit)
+15% to Fire Resistance (implicit)
--------
+36 to Strength
+90 to maximum Life
Regenerate 49 Life per second
+34% to Chaos Resistance
30% increased Movement Speed
44% increased Armour (crafted)
Searing Exarch Item
Eater of Worlds Item""",
}


@pytest.mark.parametrize("item_type,text", REAL_WORLD_SAMPLES.items())
def test_real_world_items(item_type, text):
    """Test that real-world item formats parse correctly"""
    parser = ItemParser()
    result = parser.parse(text)
    
    assert result is not None, f"Failed to parse {item_type}: {text[:100]}"
    assert result.rarity is not None
    assert result.name is not None or result.base_type is not None
    
    display = result.get_display_name()
    assert display != "Unknown Item", f"{item_type} parsed but display name is Unknown"
    
    print(f"\n{item_type}:")
    print(f"  Rarity: {result.rarity}")
    print(f"  Name: {result.name}")
    print(f"  Base: {result.base_type}")
    print(f"  Display: {display}")


def test_empty_input():
    """Parser should handle empty input gracefully"""
    parser = ItemParser()
    assert parser.parse("") is None
    assert parser.parse("   \n\n  ") is None


def test_malformed_input():
    """Parser should handle malformed input"""
    parser = ItemParser()
    
    # No rarity line
    result = parser.parse("Just some random text\nNo rarity here")
    assert result is None
    
    # Only rarity, nothing else
    result = parser.parse("Rarity: Unique")
    assert result is None  # Should fail validation


def test_minimal_valid_item():
    """Test minimal valid item structure"""
    parser = ItemParser()
    
    # Minimal valid structure
    text = """Rarity: Normal
Some Item Name"""
    
    result = parser.parse(text)
    assert result is not None
    assert result.rarity == "NORMAL"
    assert result.name == "Some Item Name"


def test_item_class_prefix():
    """Test items with Item Class: prefix (PoE clipboard format)"""
    parser = ItemParser()

    # With Item Class prefix
    text = """Item Class: Boots
Rarity: Rare
Speed Treads
Sorcerer Boots
--------
Item Level: 75"""

    result = parser.parse(text)
    assert result is not None
    assert result.rarity == "RARE"
    assert result.name == "Speed Treads"
    assert result.base_type == "Sorcerer Boots"
    assert result.item_level == 75


def test_item_class_only():
    """Test incomplete clipboard with only Item Class line"""
    parser = ItemParser()

    # Only Item Class, no Rarity (incomplete clipboard)
    text = "Item Class: Boots"

    result = parser.parse(text)
    # Should return None because there's no Rarity line
    assert result is None


def test_item_class_with_blank_lines():
    """Test Item Class with blank lines before Rarity"""
    parser = ItemParser()

    # With blank lines between Item Class and Rarity
    text = """Item Class: Weapons


Rarity: Unique
Some Unique Weapon
Two Hand Sword"""

    result = parser.parse(text)
    assert result is not None
    assert result.rarity == "UNIQUE"
    assert result.name == "Some Unique Weapon"


if __name__ == "__main__":
    # Run diagnostics
    parser = ItemParser()
    
    print("=" * 70)
    print("ITEM PARSER DIAGNOSTIC TEST")
    print("=" * 70)
    
    for item_type, text in REAL_WORLD_SAMPLES.items():
        print(f"\n{'='*70}")
        print(f"Testing: {item_type}")
        print(f"{'='*70}")
        
        result = parser.parse(text)
        
        if result is None:
            print("❌ FAILED TO PARSE")
            print(f"Raw text:\n{text}")
        else:
            print("✅ Successfully parsed")
            print(f"  Rarity: {result.rarity}")
            print(f"  Name: {result.name}")
            print(f"  Base Type: {result.base_type}")
            print(f"  Display Name: {result.get_display_name()}")
            print(f"  Item Level: {result.item_level}")
            
    print(f"\n{'='*70}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*70}")
