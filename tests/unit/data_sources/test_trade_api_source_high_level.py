from __future__ import annotations

import logging
from typing import Any, Mapping
import pytest

from core.price_multi import RESULT_COLUMNS
from data_sources.pricing.trade_api import TradeApiSource

pytestmark = pytest.mark.unit


# --------------------------------------------------------
# Fake high-level client (used for check_item on raw text)
# --------------------------------------------------------

class FakeTradeClient:
    """
    High-level mode client: must expose:
      - league
      - search_and_fetch(item_text, league)
    and must return listings already shaped like RESULT_COLUMNS rows.
    """
    def __init__(self, listings: list[Mapping[str, Any]], league: str = "Crucible"):
        self._listings = list(listings)
        self.league = league
        self.calls: list[tuple[str, str]] = []

    def search_and_fetch(self, item_text: str, league: str):
        self.calls.append((item_text, league))
        return list(self._listings)


# --------------------------------------------------------
# Helper: Build source with correct constructor
# --------------------------------------------------------

def make_source(listings: list[Mapping[str, Any]], league="Crucible", name="trade_api_test"):
    fake = FakeTradeClient(listings=listings, league=league)
    src = TradeApiSource(
        client=fake,
        league=league,
        name=name,
        logger=logging.getLogger("test.trade.high"),
    )
    return src, fake


# --------------------------------------------------------
# Tests
# --------------------------------------------------------

def test_blank_input_returns_empty_and_client_not_called():
    source, client = make_source([])
    assert source.check_item("   ") == []
    assert client.calls == []


def test_basic_row_normalization_and_source_field():
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

    source, client = make_source(listings, league="Crucible", name="trade_api")

    rows = source.check_item("Goldrim")
    assert len(rows) == 1

    row = rows[0]
    for col in RESULT_COLUMNS:
        assert col in row

    assert row["source"] == "trade_api"
    assert client.calls == [("Goldrim", "Crucible")]


def test_multiple_rows_pass_through_unchanged_shape():
    listings = [
        {"item_name": "A", "variant": "", "links": "", "chaos_value": 1.0, "divine_value": 0.01, "listing_count": 3},
        {"item_name": "B", "variant": "", "links": "", "chaos_value": 2.0, "divine_value": 0.02, "listing_count": 4},
    ]

    source, client = make_source(listings)

    rows = source.check_item("test")
    assert len(rows) == 2
    assert [r["item_name"] for r in rows] == ["A", "B"]


def test_client_without_search_and_fetch_returns_empty():
    class NoSearch:
        league = "Crucible"

    source = TradeApiSource(
        client=NoSearch(),
        league="Crucible",
        name="trade_api",
        logger=logging.getLogger("test.trade.high"),
    )

    assert source.check_item("Goldrim") == []


def test_missing_fields_are_present_but_defaulted():
    listings = [
        {
            "item_name": "Weird Shield",
            "chaos_value": 50.0,
            # missing: variant, links, divine_value, listing_count
        }
    ]

    source, client = make_source(listings)

    rows = source.check_item("Shield")
    assert len(rows) == 1
    row = rows[0]

    for col in RESULT_COLUMNS:
        assert col in row
    assert row["item_name"] == "Weird Shield"
    assert row["chaos_value"] == 50.0
