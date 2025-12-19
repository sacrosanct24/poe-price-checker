"""Test the Infractem bow that was failing"""

from core.item_parser import ItemParser

# Your actual item from the clipboard
INFRACTEM = """Item Class: Bows
Rarity: Unique
Infractem
Decimation Bow
--------
Bow
Quality: +6% (augmented)
Physical Damage: 128-281 (augmented)
Critical Strike Chance: 7.45% (augmented)
Attacks per Second: 1.20
--------
Requirements:
Level: 53
Dex: 170 (unmet)
--------
Sockets: G-G R-G G-G 
--------
Item Level: 85
--------
49% increased Critical Strike Chance (implicit)
--------
+30 to Dexterity
70% increased Physical Damage
Adds 27 to 40 Physical Damage
10% increased Movement Speed
+352 to Accuracy Rating
Cannot Leech Life
Arrows Pierce all Targets
--------
Mark us with mercy, then press on with care,
Execute us steadily, notch away at our despair."""

parser = ItemParser()
result = parser.parse(INFRACTEM)

print("=" * 80)
print("TESTING INFRACTEM BOW")
print("=" * 80)

if result is None:
    print("X STILL FAILED TO PARSE")
else:
    print("OK SUCCESS! Parser fixed!")
    print(f"\nRarity: {result.rarity}")
    print(f"Name: {result.name}")
    print(f"Base Type: {result.base_type}")
    print(f"Display Name: {result.get_display_name()}")
    print(f"Item Level: {result.item_level}")
    print(f"Quality: {result.quality}")
    print(f"Sockets: {result.sockets}")
    print(f"Links: {result.links}")
    print(f"Requirements: {result.requirements}")
    print(f"Implicits: {len(result.implicits)}")
    print(f"Explicits: {len(result.explicits)}")
    print("\nExplicit mods:")
    for mod in result.explicits:
        print(f"  - {mod}")

print("=" * 80)
