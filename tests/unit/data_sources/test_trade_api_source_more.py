from __future__ import annotations

from typing import Any, Mapping, List
import logging
import pytest

from core.price_multi import RESULT_COLUMNS
from data_sources.pricing.trade_api import TradeApiSource


pytestmark = pytest.mark.unit


# ----------------------------------------------------------------------
# High-level FakeTradeClient
# ----------------------------------------------------------------------

class FakeTradeClient:
    """
    High-level mode client:
    - Must expose .league
    - Must implement search_and_fetch(item_text, league)
    - Must return rows already shaped like RESULT_COLUMNS
    """

    def __init__(self, listings: list[Mapping[str, Any]], league: str = "Crucible"):
        self._listings = list(listings)
        self.league = league
        self.calls: list[tuple[str, str]] = []

    def search_and_fetch(self, item_text: str, league: str) -> list[Mapping[str, Any]]:
        self.calls.append((item_text, league))
        return list(self._listings)


# ----------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------

def make_source_with_fake_client(
    listings: list[Mapping[str, Any]],
    league: str = "Crucible",
    name: str = "trade_test",
):
    client = FakeTradeClient(listings, league=league)
    source = TradeApiSource(
        client=client,
        league=league,
        name=name,
        logger=logging.getLogger("test.trade.more"),
    )
    return source, client


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_high_level_invokes_client_and_returns_rows():
    listings = [
        {
            "item_name": "Goldrim",
            "variant": "",
            "links": "0",
            "chaos_value": 2.0,
            "divine_value": 0.01,
            "listing_count": 5,
        }
    ]

    source, client = make_source_with_fake_client(listings)

    # High-level check: only item text is passed
    rows = source.check_item("Some Goldrim")

    # Client should have been called exactly once
    assert client.calls == [("Some Goldrim", "Crucible")]

    # Should return exactly the listings we provided
    assert len(rows) == 1

    row = rows[0]
    for col in RESULT_COLUMNS:
        assert col in row

    assert row["item_name"] == "Goldrim"
    assert row["chaos_value"] == 2.0
    assert row["listing_count"] == 5


def test_missing_fields_get_defaulted():
    listings = [
        {
            "item_name": "Rare Shield",
            "chaos_value": 20.0,
            # missing: variant, links, divine_value, listing_count
        }
    ]

    source, client = make_source_with_fake_client(listings)

    rows = source.check_item("Rare Shield")

    assert len(rows) == 1
    row = rows[0]

    for col in RESULT_COLUMNS:
        assert col in row

    assert row["item_name"] == "Rare Shield"
    assert row["chaos_value"] == 20.0
    # defaults:
    assert row["variant"] == ""
    assert row["links"] == ""
    assert row["divine_value"] == ""
    assert row["listing_count"] == ""


def test_blank_item_text_returns_empty_and_does_not_call_client():
    listings = [
        {
            "item_name": "X",
            "variant": "",
            "links": "",
            "chaos_value": 1,
            "divine_value": 0.01,
            "listing_count": 2,
        }
    ]

    source, client = make_source_with_fake_client(listings)

    rows = source.check_item("   ")
    assert rows == []
    assert client.calls == []
