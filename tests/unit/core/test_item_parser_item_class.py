"""
Tests for "Item Class:" line handling in PoE clipboard text.

PoE includes "Item Class: <type>" as the first line in clipboard text,
which the parser needs to skip to find the "Rarity:" line.
"""
from __future__ import annotations

import pytest
from core.item_parser import ItemParser

pytestmark = pytest.mark.unit


def test_parse_with_item_class_line():
    """Parser should handle 'Item Class:' line at the start"""
    parser = ItemParser()
    
    text = """Item Class: Bows
Rarity: Unique
Infractem
Decimation Bow
--------
Item Level: 85"""
    
    result = parser.parse(text)
    
    assert result is not None
    assert result.rarity == "UNIQUE"
    assert result.name == "Infractem"
    assert result.base_type == "Decimation Bow"
    assert result.item_level == 85


def test_parse_without_item_class_line_still_works():
    """Parser should work with or without 'Item Class:' line"""
    parser = ItemParser()
    
    text = """Rarity: Unique
Goldrim
Leather Cap
--------
Item Level: 10"""
    
    result = parser.parse(text)
    
    assert result is not None
    assert result.rarity == "UNIQUE"
    assert result.name == "Goldrim"
    assert result.base_type == "Leather Cap"


def test_parse_item_class_currency():
    """Parser should handle currency items with Item Class"""
    parser = ItemParser()
    
    text = """Item Class: Stackable Currency
Rarity: Currency
Chaos Orb
--------
Stack Size: 5/10"""
    
    result = parser.parse(text)
    
    assert result is not None
    assert result.rarity == "CURRENCY"
    assert result.name == "Chaos Orb"
    assert result.stack_size == 5
    assert result.max_stack_size == 10


def test_parse_item_class_armor():
    """Parser should handle armor items with Item Class"""
    parser = ItemParser()
    
    text = """Item Class: Body Armours
Rarity: Unique
Tabula Rasa
Simple Robe
--------
Sockets: W-W-W-W-W-W"""
    
    result = parser.parse(text)
    
    assert result is not None
    assert result.rarity == "UNIQUE"
    assert result.name == "Tabula Rasa"
    assert result.base_type == "Simple Robe"
    assert result.sockets == "W-W-W-W-W-W"
    assert result.links == 6


def test_parse_only_item_class_no_rarity_fails():
    """Parser should reject text with only 'Item Class:' and no 'Rarity:'"""
    parser = ItemParser()
    
    text = """Item Class: Bows
Some Item Name
Bow Type"""
    
    result = parser.parse(text)
    
    assert result is None


def test_real_world_infractem_bow():
    """Test the actual Infractem bow that was failing in production"""
    parser = ItemParser()
    
    text = """Item Class: Bows
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
Arrows Pierce all Targets"""
    
    result = parser.parse(text)
    
    assert result is not None
    assert result.rarity == "UNIQUE"
    assert result.name == "Infractem"
    assert result.base_type == "Decimation Bow"
    assert result.item_level == 85
    assert result.quality == 6
    assert result.sockets == "G-G R-G G-G"
    assert result.links == 2  # Two separate groups
    assert len(result.implicits) == 1
    assert len(result.explicits) > 5  # Should have multiple explicit mods
