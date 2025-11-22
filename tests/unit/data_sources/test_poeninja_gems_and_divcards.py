# tests/test_poeninja_gems_and_divcards.py

import pytest

from data_sources.pricing.poe_ninja import PoeNinjaAPI
# tests/unit/core/test_price_multi.py
import pytest
pytestmark = pytest.mark.unit


@pytest.fixture
def poe_ninja():
    # Use a dummy league; we won't actually call the real API in these tests.
    return PoeNinjaAPI(league="Standard")


def test_find_item_price_gem_exact_match(poe_ninja, monkeypatch):
    """
    Ensure that find_item_price for rarity='GEM' selects the correct line
    based on gem name, level, quality, and corrupted flag.
    """

    fake_overview = {
        "lines": [
            {
                "name": "Awakened Multistrike Support",
                "gemLevel": 1,
                "gemQuality": 20,
                "corrupted": True,
                "chaosValue": 187813.0,
            },
            {
                "name": "Awakened Multistrike Support",
                "gemLevel": 5,
                "gemQuality": 20,
                "corrupted": False,
                "chaosValue": 250000.0,
            },
        ]
    }

    # Monkeypatch the skill gem overview to return our fake data
    monkeypatch.setattr(
        poe_ninja,
        "get_skill_gem_overview",
        lambda: fake_overview,
    )

    result = poe_ninja.find_item_price(
        item_name="Awakened Multistrike Support",
        base_type=None,
        rarity="GEM",
        gem_level=1,
        gem_quality=20,
        corrupted=True,
    )

    assert result is not None
    assert result["gemLevel"] == 1
    assert result["gemQuality"] == 20
    assert bool(result["corrupted"]) is True
    assert result["chaosValue"] == pytest.approx(187813.0)


def test_find_item_price_gem_best_fallback(poe_ninja, monkeypatch):
    """
    If we don't specify level/quality/corruption, the helper should fall back
    to the candidate with highest chaosValue for the given gem name.
    """

    fake_overview = {
        "lines": [
            {
                "name": "Awakened Multistrike Support",
                "gemLevel": 1,
                "gemQuality": 20,
                "corrupted": True,
                "chaosValue": 187813.0,
            },
            {
                "name": "Awakened Multistrike Support",
                "gemLevel": 5,
                "gemQuality": 20,
                "corrupted": False,
                "chaosValue": 250000.0,
            },
        ]
    }

    monkeypatch.setattr(
        poe_ninja,
        "get_skill_gem_overview",
        lambda: fake_overview,
    )

    result = poe_ninja.find_item_price(
        item_name="Awakened Multistrike Support",
        base_type=None,
        rarity="GEM",
        gem_level=None,
        gem_quality=None,
        corrupted=None,
    )

    assert result is not None
    # Should pick the highest chaosValue candidate (level 5 in this fake set)
    assert result["gemLevel"] == 5
    assert result["chaosValue"] == pytest.approx(250000.0)


def test_find_item_price_divination_card(poe_ninja, monkeypatch):
    """
    Ensure that divination cards can be resolved via the itemoverview('DivinationCard')
    data when rarity is DIVINATION or DIVINATION CARD.
    """

    fake_div_cards = {
        "lines": [
            {
                "name": "The Nurse",
                "chaosValue": 69.3,
                "divineValue": 0.21,
            },
            {
                "name": "The Doctor",
                "chaosValue": 600.0,
                "divineValue": 1.8,
            },
        ]
    }

    # Monkeypatch the internal _get_item_overview used for DivinationCard lookups
    def fake_get_item_overview(item_type: str):
        assert item_type == "DivinationCard"
        return fake_div_cards

    monkeypatch.setattr(
        poe_ninja,
        "_get_item_overview",
        fake_get_item_overview,
    )

    # Test with rarity 'DIVINATION'
    result = poe_ninja.find_item_price(
        item_name="The Nurse",
        base_type=None,
        rarity="DIVINATION",
    )

    assert result is not None
    assert result["name"] == "The Nurse"
    assert result["chaosValue"] == pytest.approx(69.3)

    # And with 'DIVINATION CARD' just to be safe if your implementation supports it
    result2 = poe_ninja.find_item_price(
        item_name="The Nurse",
        base_type=None,
        rarity="DIVINATION CARD",
    )

    assert result2 is not None
    assert result2["name"] == "The Nurse"
