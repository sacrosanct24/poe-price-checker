from __future__ import annotations

import pytest

from core.pricing import PriceService


pytestmark = pytest.mark.unit


# -------------------------------------------------------------------
# Fakes for currency pricing path
# -------------------------------------------------------------------


class FakeConfig:
    """
    Minimal config for exercising the currency branch of PriceService.
    """
    current_game = "poe1"
    games = {"poe1": {"league": "Crucible"}}
    league = "Crucible"
    divine_rate = None  # let PriceService fall back to poe.ninja / defaults


class FakeParser:
    """
    Parser that always returns a CURRENCY item with the given display text.
    """

    def parse(self, text: str):
        class P:
            rarity = "CURRENCY"
            # PriceService uses _get_item_display_name, which looks at:
            # display_name, name, base_type in that order.
            display_name = text
            name = text
            base_type = text
            gem_level = None
            gem_quality = None
            is_corrupted = False
        return P()


class FakeDB:
    """
    Minimal subset of Database API used by PriceService.
    We don't assert on persistence here, only that it doesn't crash.
    """

    def __init__(self):
        self.check_rows = []
        self.quote_rows = []

    def create_price_check(
        self,
        game_version,
        league,
        item_name,
        item_base_type,
        source,
        query_hash,
    ):
        row_id = len(self.check_rows) + 1
        self.check_rows.append(
            {
                "id": row_id,
                "game_version": game_version,
                "league": league,
                "item_name": item_name,
                "item_base_type": item_base_type,
                "source": source,
                "query_hash": query_hash,
            }
        )
        return row_id

    def add_price_quotes_batch(self, check_id, rows):
        for r in rows:
            self.quote_rows.append((check_id, r))

    def get_latest_price_stats_for_item(
        self,
        game_version,
        league,
        item_name,
        days,
    ):
        return None  # force PriceService to use direct poe.ninja value


class FakePoeNinja:
    """
    Fake PoeNinjaAPI for currency pricing.

    Implements get_currency_price for O(1) lookups.
    """

    def __init__(self):
        self.league = "Crucible"
        self._calls = 0
        self._currency_data = {
            "chaos orb": {"chaosEquivalent": 1.0},
            "divine orb": {"chaosEquivalent": 200.0},
        }

    def get_currency_overview(self):
        self._calls += 1
        return {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0},
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 200.0},
            ]
        }

    def get_currency_price(self, currency_name: str) -> tuple:
        """O(1) indexed lookup for currency prices."""
        self._calls += 1
        key = (currency_name or "").strip().lower()
        item = self._currency_data.get(key)
        if item:
            return float(item.get("chaosEquivalent", 0.0)), "poe.ninja currency"
        return 0.0, "not found"


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_lookup_currency_price_divine():
    """
    When the parsed item is CURRENCY with name 'Divine Orb',
    PriceService should use poe.ninja's currencyoverview endpoint,
    find the matching entry, and surface a 200.0 chaos price.
    """
    config = FakeConfig()
    db = FakeDB()
    parser = FakeParser()
    ninja = FakePoeNinja()

    svc = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=ninja,
        trade_source=None,
    )

    rows = svc.check_item("Divine Orb")
    assert len(rows) == 1

    row = rows[0]
    # PriceService formats chaos values with one decimal place
    assert row["chaos_value"] == "200.0"
    # Ensure we used the currencyoverview endpoint exactly once
    assert ninja._calls == 1


def test_unknown_currency_falls_back_to_zero_price():
    """
    If the currency name is not present in poe.ninja's overview,
    PriceService should fall back to a 0.0 chaos value.
    """
    config = FakeConfig()
    db = FakeDB()
    parser = FakeParser()
    ninja = FakePoeNinja()

    svc = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=ninja,
        trade_source=None,
    )

    rows = svc.check_item("Some Unknown Currency")
    assert len(rows) == 1

    row = rows[0]
    assert row["chaos_value"] == "0.0"
    assert ninja._calls == 1
