from __future__ import annotations

from typing import Any, Mapping
import logging

import pytest

from core.price_multi import RESULT_COLUMNS
from data_sources.pricing.trade_api import TradeApiSource, PoeTradeClient

pytestmark = pytest.mark.unit


class FakeTradeClient(PoeTradeClient):
    """
    Fake client that subclasses PoeTradeClient but overrides HTTP behavior.

    It exposes:
      - .league
      - .search_and_fetch(item_text, league)
    and returns preconfigured, already-normalized listing rows.
    """

    def __init__(self, listings: list[Mapping[str, Any]], league: str = "Crucible") -> None:
        super().__init__(logger=logging.getLogger("test.fake_trade_client"))
        self._listings = list(listings)
        self.league = league
        self.calls: list[tuple[str, str]] = []

    def search_and_fetch(self, item_text: str, league: str) -> list[Mapping[str, Any]]:
        self.calls.append((item_text, league))
        return list(self._listings)


def _make_source_with_fake_client(
    listings: list[Mapping[str, Any]],
    league: str = "Crucible",
    name: str = "trade_api",
) -> tuple[TradeApiSource, FakeTradeClient]:
    client = FakeTradeClient(listings=listings, league=league)
    source = TradeApiSource(
        client=client,
        league=league,
        name=name,
        logger=logging.getLogger("test.trade_api_source"),
    )
    return source, client


def test_trade_api_source_returns_empty_for_blank_input() -> None:
    """Blank or whitespace-only item text should short-circuit and not call the client."""
    source, client = _make_source_with_fake_client([])

    rows = source.check_item("   ")

    assert rows == []
    assert client.calls == []


def test_trade_api_source_normalizes_fake_listings() -> None:
    """
    High-level flow:

    - TradeApiSource.check_item(item_text) delegates to FakeTradeClient.search_and_fetch.
    - Client returns already-normalized listing dicts.
    - TradeApiSource ensures every row has RESULT_COLUMNS and the correct source name.
    """
    fake_listings = [
        {
            "item_name": "Cool Sword",
            "variant": "Base",
            "links": "6L",
            "chaos_value": 123.4,
            "divine_value": 0.6,
            "listing_count": 10,
        },
        {
            # Missing some optional fields, which should be default-filled.
            "item_name": "Weird Shield",
            "chaos_value": 50.0,
        },
    ]

    source, client = _make_source_with_fake_client(fake_listings, league="Crucible", name="trade_api")

    rows = source.check_item("Some Cool Sword")

    # Client should be called once with the item text and league
    assert client.calls == [("Some Cool Sword", "Crucible")]

    # Should return as many rows as client listings
    assert len(rows) == 2

    for row in rows:
        # All expected columns present
        for col in RESULT_COLUMNS:
            assert col in row
        # Source name should be set
        assert row["source"] == "trade_api"

    # Spot-check a couple of values for the first fake listing
    first = rows[0]
    assert first["item_name"] == "Cool Sword"
    assert first["links"] == "6L"
    assert first["chaos_value"] == 123.4

    # Second listing had missing fields; they should be defaulted to ""
    second = rows[1]
    assert second["item_name"] == "Weird Shield"
    assert second["chaos_value"] == 50.0
    # fields like variant/links/divine_value/listing_count should be present (possibly "")
    for col in ("variant", "links", "divine_value", "listing_count"):
        assert col in second
