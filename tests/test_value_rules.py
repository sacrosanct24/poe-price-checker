# tests/test_value_rules.py

import pytest

from core.item_parser import ParsedItem
from core.value_rules import assess_rare_item


def make_rare_item(
    *,
    raw_text: str = "",
    name: str = "Test Rare",
    base_type: str = "Hubris Circlet",
    item_level: int = 84,
    implicits=None,
    explicits=None,
    enchants=None,
) -> ParsedItem:
    """Minimal helper to construct a ParsedItem for value-rule tests."""
    return ParsedItem(
        raw_text=raw_text or "dummy",
        rarity="RARE",
        name=name,
        base_type=base_type,
        item_level=item_level,
        implicits=implicits or [],
        explicits=explicits or [],
        enchants=enchants or [],
        is_corrupted=False,
    )


def test_fractured_rare_flagged_as_fracture_base():
    item = make_rare_item(
        explicits=[
            "+71 to maximum Energy Shield (fractured)",
            "+37% to Lightning Resistance",
        ]
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "fracture_base"
    # At least one reason should mention "fractured" or the rule name
    assert any("fractured" in r.lower() for r in assessment.reasons)


def test_high_life_rare_flagged_as_craft_base():
    item = make_rare_item(
        base_type="Astral Plate",
        item_level=84,
        explicits=[
            "+98 to maximum Life",
            "+45% to Cold Resistance",
            "+38% to Lightning Resistance",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag in {"craft_base", "check_trade"}
    assert any("life" in r.lower() for r in assessment.reasons)


def test_multi_damage_mods_flagged_as_check_trade():
    item = make_rare_item(
        base_type="Bone Helmet",
        item_level=86,
        explicits=[
            "+30% to Damage over Time Multiplier",
            "Non-Channelling Skills have -8 to Total Mana Cost",
            "+74 to maximum Life",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "check_trade"
    assert any("damage" in r.lower() or "trade" in r.lower() for r in assessment.reasons)


def test_obvious_junk_rare_is_junk():
    item = make_rare_item(
        base_type="Iron Greaves",
        item_level=50,
        explicits=[
            "+22% to Fire Resistance",
            "+19% to Cold Resistance",
            "+35 to maximum Mana",
        ],
    )

    assessment = assess_rare_item(item)

    assert assessment.flag == "junk"
    assert any("no rare value rules matched" in r.lower() for r in assessment.reasons)


def test_non_rare_items_always_junk():
    """Non-rare items should not be treated as valuable by this module."""
    non_rare = ParsedItem(
        raw_text="dummy",
        rarity="UNIQUE",
        name="Shavronne's Wrappings",
        base_type="Occultist's Vestment",
        item_level=85,
        implicits=[],
        explicits=[],
        enchants=[],
        is_corrupted=False,
    )

    assessment = assess_rare_item(non_rare)

    assert assessment.flag == "junk"
    assert any("not a rare item" in r.lower() for r in assessment.reasons)
