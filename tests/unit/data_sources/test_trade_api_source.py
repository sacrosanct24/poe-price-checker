# tests/data_sources/pricing/test_trade_api_source.py
from __future__ import annotations

from typing import Any, Mapping, List

import logging

from core.price_multi import RESULT_COLUMNS
from data_sources.pricing.trade_api import TradeApiSource, PoeTradeClient
# tests/unit/core/test_price_multi.py
import pytest
pytestmark = pytest.mark.unit


class FakeTradeClient(PoeTradeClient):
    """
    Fake client that returns predefined listings instead of doing HTTP.
    """

    def __init__(self, listings: list[Mapping[str, Any]]) -> None:
        super().__init__(logger=logging.getLogger("test.fake_trade_client"))
        self._listings = listings
        self.calls: list[tuple[str, str]] = []

    def search_and_fetch(self, item_text: str, league: str) -> list[Mapping[str, Any]]:
        self.calls.append((item_text, league))
        return list(self._listings)


def test_trade_api_source_returns_empty_for_blank_input() -> None:
    client = FakeTradeClient(listings=[])
    logger = logging.getLogger("test.trade_api_source.blank")
    source = TradeApiSource(
        name="trade_api",
        client=client,
        league="Standard",
        logger=logger,
    )

    rows = source.check_item("   ")

    assert rows == []
    # Client should not be called for blank input
    assert client.calls == []


def test_trade_api_source_normalizes_fake_listings() -> None:
    fake_listings = [
        {
            "item_name": "Cool Sword",
            "variant": "Base",
            "links": "6L",
            "chaos_value": 123.4,
            "divine_value": 0.6,
            "listing_count": 7,
        },
        {
            # Deliberately missing some fields to test defaults
            "item_name": "Weird Shield",
            "chaos_value": 50.0,
        },
    ]

    client = FakeTradeClient(listings=fake_listings)
    logger = logging.getLogger("test.trade_api_source.normalization")
    source = TradeApiSource(
        name="trade_api",
        client=client,
        league="Crucible",
        logger=logger,
    )

    rows = source.check_item("some item text")

    # Client should have been called once with the item text + league
    assert client.calls == [("some item text", "Crucible")]

    # We should have one row per listing
    assert len(rows) == len(fake_listings)

    for row in rows:
        # All expected columns must exist
        for col in RESULT_COLUMNS:
            assert col in row

        # Source column must be set correctly
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
