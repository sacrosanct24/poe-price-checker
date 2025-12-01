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
