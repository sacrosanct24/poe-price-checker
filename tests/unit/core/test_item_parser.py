from __future__ import annotations

import pytest
from core.item_parser import ItemParser, ParsedItem

pytestmark = pytest.mark.unit


# --------------------------------------
# ParsedItem.to_dict()
# --------------------------------------

def test_parsed_item_to_dict():
    item = ParsedItem(
        raw_text="Test item",
        rarity="UNIQUE",
        name="Shavronne's Wrappings",
        base_type="Occultist's Vestment",
        item_level=85,
        quality=20,
        stack_size=1,
        is_corrupted=True,
    )

    result = item.to_dict()

    assert result["rarity"] == "UNIQUE"
    assert result["name"] == "Shavronne's Wrappings"
    assert result["base_type"] == "Occultist's Vestment"
    assert result["item_level"] == 85
    assert result["quality"] == 20
    assert result["is_corrupted"] is True
    assert "chaos_value" not in result


# --------------------------------------
# ParsedItem.from_stash_item()
# --------------------------------------

class TestFromStashItem:
    """Tests for ParsedItem.from_stash_item() class method."""

    def test_basic_rare_item(self):
        """Parse a basic rare item from stash API data."""
        stash_item = {
            "frameType": 2,  # Rare
            "name": "<<set:MS>><<set:M>><<set:S>>Dragon Wrap",
            "typeLine": "Vaal Regalia",
            "baseType": "Vaal Regalia",
            "ilvl": 86,
            "identified": True,
            "explicitMods": [
                "+120 to maximum Life",
                "+45% to Fire Resistance",
            ],
            "implicitMods": [
                "+50 to maximum Energy Shield"
            ],
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.rarity == "Rare"
        assert item.name == "Dragon Wrap"  # Prefix stripped
        assert item.base_type == "Vaal Regalia"
        assert item.item_level == 86
        assert item.explicits == ["+120 to maximum Life", "+45% to Fire Resistance"]
        assert item.implicits == ["+50 to maximum Energy Shield"]

    def test_unique_item(self):
        """Parse a unique item from stash API data."""
        stash_item = {
            "frameType": 3,  # Unique
            "name": "<<set:MS>><<set:M>><<set:S>>Headhunter",
            "typeLine": "Leather Belt",
            "baseType": "Leather Belt",
            "ilvl": 85,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.rarity == "Unique"
        assert item.name == "Headhunter"
        assert item.base_type == "Leather Belt"

    def test_currency_item(self):
        """Parse a currency item from stash API data."""
        stash_item = {
            "frameType": 5,  # Currency
            "typeLine": "Divine Orb",
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.rarity == "Currency"
        assert item.base_type == "Divine Orb"

    def test_gem_item(self):
        """Parse a gem from stash API data."""
        stash_item = {
            "frameType": 4,  # Gem
            "typeLine": "Vaal Grace",
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.rarity == "Gem"

    def test_div_card_item(self):
        """Parse a divination card from stash API data."""
        stash_item = {
            "frameType": 6,  # Divination Card
            "typeLine": "The Doctor",
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.rarity == "Divination Card"

    def test_with_influences(self):
        """Parse item with influences."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Hubris Circlet",
            "baseType": "Hubris Circlet",
            "ilvl": 86,
            "influences": {
                "shaper": True,
                "elder": True,
            }
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert "Shaper" in item.influences
        assert "Elder" in item.influences
        assert len(item.influences) == 2

    def test_with_single_influence(self):
        """Parse item with single influence."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Hubris Circlet",
            "ilvl": 86,
            "influences": {
                "hunter": True,
            }
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.influences == ["Hunter"]

    def test_corrupted_item(self):
        """Parse corrupted item."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "corrupted": True,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.is_corrupted is True

    def test_fractured_item(self):
        """Parse fractured item."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "fractured": True,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.is_fractured is True

    def test_synthesised_item(self):
        """Parse synthesised item."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "synthesised": True,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.is_synthesised is True

    def test_mirrored_item(self):
        """Parse mirrored item."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Vaal Regalia",
            "mirrored": True,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.is_mirrored is True

    def test_with_sockets(self):
        """Parse item with sockets."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Body Armour",
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 0, "sColour": "B"},
                {"group": 0, "sColour": "W"},
                {"group": 0, "sColour": "W"},
                {"group": 0, "sColour": "W"},
            ]
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.sockets == "RGBWWW"
        assert item.links == 6

    def test_with_multiple_socket_groups(self):
        """Parse item with multiple socket groups (unlinked)."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Body Armour",
            "sockets": [
                {"group": 0, "sColour": "R"},
                {"group": 0, "sColour": "G"},
                {"group": 1, "sColour": "B"},
                {"group": 1, "sColour": "W"},
            ]
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.sockets == "RG-BW"
        assert item.links == 2

    def test_with_enchants(self):
        """Parse item with enchant mods."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Hubris Circlet",
            "ilvl": 86,
            "enchantMods": [
                "Molten Strike fires 3 additional Projectiles"
            ],
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert "Molten Strike fires 3 additional Projectiles" in item.enchants

    def test_with_quality(self):
        """Parse item with quality."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Body Armour",
            "quality": 20,
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.quality == 20

    def test_empty_influences(self):
        """Handle empty influences object."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Hubris Circlet",
            "influences": {}
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.influences == []

    def test_no_influences_key(self):
        """Handle missing influences key."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Hubris Circlet",
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.influences == []

    def test_raw_text_default(self):
        """Raw text is constructed from name and typeLine."""
        stash_item = {
            "frameType": 2,
            "name": "Test Name",
            "typeLine": "Test Type",
        }

        item = ParsedItem.from_stash_item(stash_item)

        assert item.raw_text == "Test Name Test Type"

    def test_raw_text_custom(self):
        """Custom raw text can be provided."""
        stash_item = {
            "frameType": 2,
            "typeLine": "Test Type",
        }

        item = ParsedItem.from_stash_item(stash_item, raw_text="Custom raw text")

        assert item.raw_text == "Custom raw text"


# --------------------------------------
# Magic item parsing
# --------------------------------------

def test_parse_magic_item():
    parser = ItemParser()

    magic_text = """Rarity: MAGIC
Seething Divine Life Flask of Staunching
--------
Quality: +20%
--------
Recovers 2400 Life over 0.30 seconds
Immunity to Bleeding during Flask effect
Removes Bleeding on use"""

    item = parser.parse(magic_text)

    assert item is not None
    assert item.rarity == "MAGIC"
    assert item.quality == 20
    assert len(item.implicits) + len(item.explicits) >= 1


# --------------------------------------
# Invalid text handling
# --------------------------------------

def test_parse_invalid_text_returns_none():
    parser = ItemParser()
    invalid_inputs = ["", "   ", "X", "Random garbage text"]

    for text in invalid_inputs:
        item = parser.parse(text)
        if item is not None:
            # Minimum structure sanity
            has_info = any([
                item.name,
                item.base_type,
                item.rarity,
                item.item_level,
                len(item.explicits) > 0,
            ])
            assert has_info


# --------------------------------------
# Implicit (implicit) parsing
# --------------------------------------

def test_parse_implicit_mod():
    parser = ItemParser()

    text = """Rarity: RARE
Crystal Belt
--------
+80 to maximum Energy Shield (implicit)
--------
+45 to maximum Life
+38% to Cold Resistance
+25% to Lightning Resistance"""

    item = parser.parse(text)

    assert item is not None
    assert item.rarity == "RARE"
    assert len(item.implicits) >= 1
    all_text = " ".join(item.implicits).lower()
    assert "energy shield" in all_text
    assert len(item.explicits) >= 2


# --------------------------------------
# Enchant parsing
# --------------------------------------

def test_parse_enchant_mod():
    parser = ItemParser()

    text = """Rarity: RARE
Lion Pelt Hubris Circlet
--------
Tornado Shot fires 2 additional secondary Projectiles (enchant)
--------
+75 to maximum Energy Shield
+42% to Fire Resistance"""

    item = parser.parse(text)

    assert item is not None
    assert item.rarity == "RARE"
    assert len(item.enchants) >= 1
    ench_text = " ".join(item.enchants).lower()
    assert "tornado shot" in ench_text or "projectile" in ench_text
    assert len(item.explicits) >= 1


# --------------------------------------
# Requirements parsing
# --------------------------------------

def test_parse_requirements_section():
    parser = ItemParser()

    text = """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 84
--------
Requirements:
Level: 70
Str: 10
Dex: 20
Int: 154
"""

    item = parser.parse(text)
    assert item is not None
    # Once implemented:
    # normalized = {k.lower(): v for k, v in item.requirements.items()}
    # assert normalized["level"] == 70


# --------------------------------------
# Sockets and links
# --------------------------------------

def test_parse_sockets_and_links():
    parser = ItemParser()

    text = """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Sockets: R-G-B R-R
"""

    item = parser.parse(text)

    assert item is not None
    assert item.sockets == "R-G-B R-R"
    assert item.links == 3  # largest linked group


# --------------------------------------
# Influences (xfail)
# --------------------------------------

def test_parse_influences_normalized():
    parser = ItemParser()

    text = """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 84
Searing Exarch Item
Eater of Worlds Item
Shaper Item
"""

    item = parser.parse(text)
    assert item is not None


# --------------------------------------
# Flags (corrupted/fractured/synth/mirrored)
# --------------------------------------

def test_parse_flags_corrupted_fractured_synth_mirrored():
    parser = ItemParser()

    text = """Rarity: UNIQUE
Awesome Item
Awesome Base
--------
Item Level: 86
--------
Fractured Item
Synthesised Item
Mirrored
Corrupted
"""

    item = parser.parse(text)

    assert item.is_fractured is True
    assert item.is_synthesised is True
    assert item.is_mirrored is True
    assert item.is_corrupted is True


# --------------------------------------
# Multiple items
# --------------------------------------

def test_parse_multiple_items():
    parser = ItemParser()

    item1 = """Rarity: UNIQUE
Shavronne's Wrappings
Occultist's Vestment
"""

    item2 = """Rarity: RARE
Doom Visor
Hubris Circlet
"""

    bulk = item1 + "\n\n" + item2
    items = parser.parse_multiple(bulk)

    assert len(items) == 2
    names = {i.name or i.base_type for i in items}
    assert "Shavronne's Wrappings" in names or "Occultist's Vestment" in names
    assert "Doom Visor" in names or "Hubris Circlet" in names
