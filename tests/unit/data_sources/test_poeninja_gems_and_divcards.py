from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from data_sources.pricing.poe_ninja import PoeNinjaAPI

pytestmark = pytest.mark.unit


# ------------------------------------------------------------------
# GEM PRICE LOOKUP
# ------------------------------------------------------------------

def test_find_gem_price_finds_exact_match():
    payload = {
        "lines": [
            {
                "name": "Raise Spectre",
                "gemLevel": 21,
                "gemQuality": 20,
                "chaosValue": 120.0,
                "listingCount": 5,
            },
            {
                "name": "Raise Spectre",
                "gemLevel": 20,
                "gemQuality": 20,
                "chaosValue": 10.0,
                "listingCount": 50,
            },
        ]
    }

    api = PoeNinjaAPI(league="Standard")

    # Mock the get_skill_gem_overview to return our test data
    with patch.object(api, 'get_skill_gem_overview', return_value=payload):
        result = api._find_gem_price(
            name="Raise Spectre",
            gem_level=21,
            gem_quality=20,
            corrupted=False,
        )

    assert result is not None
    assert result["chaosValue"] == 120.0
    assert result["listingCount"] == 5


def test_find_gem_price_returns_none_when_no_match():
    payload = {"lines": []}
    api = PoeNinjaAPI(league="Standard")

    # Mock the get_skill_gem_overview to return empty data
    with patch.object(api, 'get_skill_gem_overview', return_value=payload):
        result = api._find_gem_price(
            name="Raise Spectre",
            gem_level=20,
            gem_quality=20,
            corrupted=False,
        )

    assert result is None


# ------------------------------------------------------------------
# NORMAL OVERVIEW LOOKUP (cards, uniques, etc.)
# ------------------------------------------------------------------

def test_find_from_overview_by_name_matches_case_insensitive():
    payload = {
        "lines": [
            {"name": "The Doctor", "chaosValue": 1200, "listingCount": 10},
            {"name": "The Fiend", "chaosValue": 500, "listingCount": 20},
        ]
    }
    api = PoeNinjaAPI()

    # Mock the _get_item_overview to return our test data
    with patch.object(api, '_get_item_overview', return_value=payload):
        r = api._find_from_overview_by_name("DivinationCard", "the doctor")

    assert r is not None
    assert r["chaosValue"] == 1200


def test_find_from_overview_by_name_returns_none_if_missing():
    payload = {
        "lines": [{"name": "The Fiend", "chaosValue": 500}]
    }
    api = PoeNinjaAPI()

    # Mock the _get_item_overview to return our test data
    with patch.object(api, '_get_item_overview', return_value=payload):
        result = api._find_from_overview_by_name("DivinationCard", "The Hoarder")

    assert result is None


# ------------------------------------------------------------------
# FULL find_item_price
# ------------------------------------------------------------------

def test_find_item_price_gem_flow():
    payload = {
        "lines": [
            {
                "name": "Raise Spectre",
                "gemLevel": 21,
                "gemQuality": 20,
                "chaosValue": 100.0,
                "listingCount": 10,
            }
        ]
    }

    api = PoeNinjaAPI(league="Standard")

    # Mock the get_skill_gem_overview to return our test data
    with patch.object(api, 'get_skill_gem_overview', return_value=payload):
        result = api.find_item_price(
            item_name="Raise Spectre",
            base_type="Raise Spectre",
            rarity="Gem",
            gem_level=21,
            gem_quality=20,
            corrupted=False,
        )

    assert result is not None
    assert result["chaosValue"] == 100.0
    assert result["listingCount"] == 10


def test_find_item_price_falls_back_to_zero_when_not_found():
    payload = {"lines": []}
    api = PoeNinjaAPI(league="Standard")

    # Mock all the _get_item_overview calls to return empty data
    with patch.object(api, '_get_item_overview', return_value=payload):
        result = api.find_item_price(
            item_name="Unknown Item",
            base_type="Unknown Item",
            rarity="Unique",
            gem_level=None,
            gem_quality=None,
            corrupted=False,
        )

    # When not found, find_item_price returns None, not a dict with 0.0
    assert result is None
