from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from core.pricing import PriceService
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


# -------------------------------------------------------------------
# Fakes / stubs for PriceService dependencies
# -------------------------------------------------------------------


@dataclass
class FakeConfig:
    """
    Minimal config stub that matches how PriceService actually reads config.

    Attributes used by PriceService:
      - current_game
      - league
      - games[current_game]["league"]
      - games[current_game]["divine_chaos_rate"] (optional)
      - divine_rate (optional)
    """
    current_game: GameVersion = GameVersion.POE1
    league: str = "Keepers"
    divine_rate: float | None = None

    def __post_init__(self) -> None:
        self.games: dict[str, dict[str, Any]] = {
            "poe1": {
                "league": "Keepers",
                "divine_chaos_rate": None,
            },
            "poe2": {
                "league": "Standard",
                "divine_chaos_rate": None,
            },
        }


class FakeParsedItem:
    """
    Simple parsed-item stand-in with the attributes PriceService expects.
    """

    def __init__(self, name: str = "Goldrim", base_type: str = "Leather Cap"):
        self.name = name
        self.base_type = base_type
        self.rarity = "Unique"
        self.item_level = 70
        self.links = 6
        self.variant = ""
        self.gem_level = None
        self.gem_quality = None
        self.is_corrupted = False


class FakeParser:
    def __init__(self):
        self.calls: list[str] = []

    def parse(self, text: str) -> FakeParsedItem:
        self.calls.append(text)
        return FakeParsedItem()


class FakePoeNinja:
    """
    Minimal stand-in for PoeNinjaAPI used by PriceService._lookup_price_with_poe_ninja
    and _convert_chaos_to_divines.
    """

    def __init__(self, league: str = "Keepers", chaos_value: float = 5.0, listing_count: int = 10):
        self.league = league
        self.divine_chaos_rate = 200.0  # 1 divine = 200 chaos
        self.calls: list[dict[str, Any]] = []
        self._chaos_value = chaos_value
        self._listing_count = listing_count

    def find_item_price(self, **kwargs: Any) -> dict | None:
        self.calls.append(kwargs)
        return {
            "chaosValue": self._chaos_value,
            "listingCount": self._listing_count,
        }


class FakeTradeSource:
    """
    Stand-in for TradeApiSource used by PriceService in low-level mode.
    """

    def __init__(self, league: str = "Keepers"):
        self.league = league
        self.calls: list[tuple[Any, int]] = []
        self.return_quotes: list[dict[str, Any]] = [
            {
                "original_currency": "chaos",
                "amount": 2.5,
                "stack_size": 1,
                "listing_id": "abc123",
                "seller_account": "SomeTrader",
                "listed_at": "2025-01-01T00:00:00Z",
            }
        ]

    def check_item(self, parsed_item: Any, max_results: int = 20) -> list[dict[str, Any]]:
        self.calls.append((parsed_item, max_results))
        return list(self.return_quotes)


class FakeDB:
    """
    Matches exactly the subset of Database API that PriceService uses:

      - create_price_check(...)
      - add_price_quotes_batch(check_id, rows)
      - get_latest_price_stats_for_item(...)

    We record calls for assertions.
    """

    def __init__(self):
        self.price_checks: list[dict[str, Any]] = []
        self.quotes_batches: list[tuple[int, list[dict[str, Any]]]] = []
        self._next_id = 1

    def create_price_check(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        item_base_type: str | None,
        source: str,
        query_hash: str,
    ) -> int:
        row = {
            "id": self._next_id,
            "game_version": game_version,
            "league": league,
            "item_name": item_name,
            "item_base_type": item_base_type,
            "source": source,
            "query_hash": query_hash,
        }
        self.price_checks.append(row)
        self._next_id += 1
        return row["id"]

    def add_price_quotes_batch(self, check_id: int, rows: list[Mapping[str, Any]]) -> None:
        # Store a copy to ensure immutability in tests
        self.quotes_batches.append((check_id, [dict(r) for r in rows]))

    def get_latest_price_stats_for_item(
        self,
        game_version: GameVersion,
        league: str,
        item_name: str,
        days: int,
    ) -> dict[str, Any] | None:
        # For these tests we don't simulate stats; return None so that
        # check_item uses poe.ninja chaos value directly.
        return None


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def price_service_with_trade() -> tuple[PriceService, FakeDB, FakePoeNinja, FakeTradeSource]:
    cfg = FakeConfig()
    parser = FakeParser()
    db = FakeDB()
    poe_ninja = FakePoeNinja()
    trade_source = FakeTradeSource(league="Keepers")

    svc = PriceService(
        config=cfg,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        trade_source=trade_source,
    )
    return svc, db, poe_ninja, trade_source


@pytest.fixture
def price_service_no_trade() -> tuple[PriceService, FakeDB, FakePoeNinja]:
    cfg = FakeConfig()
    parser = FakeParser()
    db = FakeDB()
    poe_ninja = FakePoeNinja()

    svc = PriceService(
        config=cfg,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        trade_source=None,
    )
    return svc, db, poe_ninja


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_check_item_with_trade_persists_price_check_and_quotes(price_service_with_trade):
    svc, db, poe_ninja, trade_source = price_service_with_trade

    rows = svc.check_item("Rarity: Unique\nGoldrim\n--------\nSome body text\n")

    # GUI rows
    assert len(rows) == 1
    row = rows[0]
    assert row["item_name"] == "Goldrim"
    # Chaos from FakePoeNinja (5.0), divine via poe_ninja.divine_chaos_rate
    assert row["chaos_value"] == "5.0"
    assert row["listing_count"] == "10"
    assert "poe.ninja" in row["source"]

    # Parser, poe_ninja, and trade_source all invoked
    assert len(poe_ninja.calls) == 1
    assert len(trade_source.calls) == 1

    # DB should contain one price_check
    assert len(db.price_checks) == 1
    check = db.price_checks[0]
    assert check["game_version"] == GameVersion.POE1
    assert check["league"] == "Keepers"
    assert check["item_name"] == "Goldrim"
    assert check["source"] == "trade+poe.ninja"

    # DB should have one batch of price_quotes
    assert len(db.quotes_batches) == 1
    check_id, quotes = db.quotes_batches[0]
    assert check_id == check["id"]

    # Should contain one synthetic poe.ninja quote + one trade quote
    assert len(quotes) == 2

    sources = {q["source"] for q in quotes}
    assert sources == {"poe_ninja", "trade"}

    ninja_quote = next(q for q in quotes if q["source"] == "poe_ninja")
    trade_quote = next(q for q in quotes if q["source"] == "trade")

    assert ninja_quote["price_chaos"] == 5.0
    assert ninja_quote["original_currency"] == "chaos"
    assert ninja_quote["listing_id"] is None

    assert trade_quote["original_currency"] == "chaos"
    assert trade_quote["listing_id"] == "abc123"
    assert trade_quote["seller_account"] == "SomeTrader"


def test_check_item_without_trade_only_persists_poe_ninja_quote(price_service_no_trade):
    svc, db, poe_ninja = price_service_no_trade

    rows = svc.check_item("Rarity: Unique\nGoldrim\n--------\nSome body text\n")

    assert len(rows) == 1
    row = rows[0]
    assert row["item_name"] == "Goldrim"
    assert row["chaos_value"] == "5.0"
    assert "poe.ninja" in row["source"]

    # Only poe_ninja should have been used; no trade_source configured
    assert len(poe_ninja.calls) == 1

    assert len(db.price_checks) == 1
    assert len(db.quotes_batches) == 1

    check_id, quotes = db.quotes_batches[0]
    assert len(quotes) == 1

    quote = quotes[0]
    assert quote["source"] == "poe_ninja"
    assert quote["price_chaos"] == 5.0
    assert quote["original_currency"] == "chaos"


def test_resolve_game_and_league_prefers_poe_ninja_league_over_config_and_trade():
    cfg = FakeConfig()
    cfg.league = "ConfigLeague"
    cfg.games["poe1"]["league"] = "GameConfigLeague"

    parser = FakeParser()
    db = FakeDB()

    poe_ninja = FakePoeNinja(league="NinjaLeague")
    trade_source = FakeTradeSource(league="TradeLeague")

    svc = PriceService(
        config=cfg,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        trade_source=trade_source,
    )

    game_version, league = svc._resolve_game_and_league()

    # Game version from config.current_game
    assert game_version == GameVersion.POE1
    # League should prefer poe_ninja.league when present
    assert league == "NinjaLeague"
