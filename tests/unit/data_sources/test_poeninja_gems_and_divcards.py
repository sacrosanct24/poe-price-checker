from __future__ import annotations

import pytest
from data_sources.pricing.poe_ninja import PoeNinjaAPI

pytestmark = pytest.mark.unit


# ------------------------------------------------------------------
# Fake HTTP Session
# ------------------------------------------------------------------

class FakeSession:
    def __init__(self, responses):
        # Map of partial URL → payload
        self.responses = responses
        self.calls = []

    def get(self, url, headers=None, timeout=10):
        self.calls.append(url)

        payload = None
        for key, val in self.responses.items():
            if key in url:
                payload = val
                break
        if payload is None:
            raise AssertionError(f"No fake response for URL: {url}")

        class R:
            status_code = 200
            def __init__(self, data): self.data = data
            def raise_for_status(self): pass
            def json(self): return self.data

        return R(payload)


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

    session = FakeSession({
        "itemoverview": payload
    })

    api = PoeNinjaAPI(league="Standard")
    api.session = session

    class G:
        name = "Raise Spectre"
        base_type = "Raise Spectre"
        gem_level = 21
        gem_quality = 20
        rarity = "Gem"
        is_corrupted = False

    result = api._find_gem_price(G(), payload["lines"])
    assert result["chaosValue"] == 120.0
    assert result["listingCount"] == 5


def test_find_gem_price_returns_none_when_no_match():
    payload = {"lines": []}
    api = PoeNinjaAPI(league="Standard")
    api.session = FakeSession({"itemoverview": payload})

    class G:
        name = "Raise Spectre"
        base_type = "Raise Spectre"
        gem_level = 20
        gem_quality = 20
        rarity = "Gem"
        is_corrupted = False

    assert api._find_gem_price(G(), payload["lines"]) is None


# ------------------------------------------------------------------
# NORMAL OVERVIEW LOOKUP (cards, uniques, etc.)
# ------------------------------------------------------------------

def test_find_from_overview_by_name_matches_case_insensitive():
    lines = [
        {"name": "The Doctor", "chaosValue": 1200, "listingCount": 10},
        {"name": "The Fiend", "chaosValue": 500, "listingCount": 20},
    ]
    api = PoeNinjaAPI()
    r = api._find_from_overview_by_name("the doctor", lines)
    assert r["chaosValue"] == 1200


def test_find_from_overview_by_name_returns_none_if_missing():
    lines = [{"name": "The Fiend", "chaosValue": 500}]
    api = PoeNinjaAPI()
    assert api._find_from_overview_by_name("The Hoarder", lines) is None


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
    api.session = FakeSession({"itemoverview": payload})

    class G:
        name = "Raise Spectre"
        base_type = "Raise Spectre"
        rarity = "Gem"
        gem_level = 21
        gem_quality = 20
        is_corrupted = False

    result = api.find_item_price(G())
    assert result is not None
    assert result["chaosValue"] == 100.0
    assert result["listingCount"] == 10


def test_find_item_price_falls_back_to_zero_when_not_found():
    payload = {"lines": []}
    api = PoeNinjaAPI(league="Standard")
    api.session = FakeSession({"itemoverview": payload})

    class Item:
        name = "Unknown Item"
        base_type = "Unknown Item"
        rarity = "Unique"
        gem_level = None
        gem_quality = None
        is_corrupted = False

    result = api.find_item_price(Item())
    assert result["chaosValue"] == 0.0
