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


class TestPoeTradeClientCacheKey:
    """Tests for PoeTradeClient._get_cache_key method."""

    def test_cache_key_basic(self):
        """Basic cache key generation."""
        client = PoeTradeClient(league="Standard")
        key = client._get_cache_key("GET", "/test/path")
        assert key == "GET:/test/path"

    def test_cache_key_with_params(self):
        """Cache key with query params should be sorted."""
        client = PoeTradeClient(league="Standard")
        key = client._get_cache_key("GET", "/test", params={"b": "2", "a": "1"})
        assert "a=1" in key
        assert "b=2" in key
        # Params should be sorted
        assert key.index("a=1") < key.index("b=2")

    def test_cache_key_method_uppercase(self):
        """Method should be uppercased."""
        client = PoeTradeClient(league="Standard")
        key = client._get_cache_key("get", "/test")
        assert key.startswith("GET:")

    def test_cache_key_none_method_defaults_to_get(self):
        """None method should default to GET."""
        client = PoeTradeClient(league="Standard")
        key = client._get_cache_key(None, "/test")
        assert key.startswith("GET:")


class TestTradeApiSourceInfluenceFilters:
    """Tests for influence filter handling in _build_query."""

    def test_build_query_with_shaper_influence(self):
        """Should add shaper_item filter for Shaper influence."""
        source, _ = _make_source_with_fake_client([])

        class ShaperItem:
            name = "Shaper Helmet"
            base_type = "Hubris Circlet"
            rarity = "RARE"
            influences = ["Shaper"]

        query = source._build_query(ShaperItem())

        # Shaper influence should be in type_filters
        filters = query.get("query", {}).get("filters", {})
        type_filters = filters.get("type_filters", {}).get("filters", {})
        assert "shaper_item" in type_filters
        assert type_filters["shaper_item"]["option"] == "true"

    def test_build_query_with_exarch_influence(self):
        """Should add searing_item filter for Exarch influence."""
        source, _ = _make_source_with_fake_client([])

        class ExarchItem:
            name = "Exarch Helmet"
            base_type = "Hubris Circlet"
            rarity = "RARE"
            influences = ["Exarch"]

        query = source._build_query(ExarchItem())

        # Exarch influence should be in misc_filters
        filters = query.get("query", {}).get("filters", {})
        misc_filters = filters.get("misc_filters", {}).get("filters", {})
        assert "searing_item" in misc_filters

    def test_build_query_with_multiple_influences(self):
        """Should handle multiple influences."""
        source, _ = _make_source_with_fake_client([])

        class DualInfluenceItem:
            name = "Dual Influence"
            base_type = "Astral Plate"
            rarity = "RARE"
            influences = ["Hunter", "Warlord"]

        query = source._build_query(DualInfluenceItem())

        filters = query.get("query", {}).get("filters", {})
        type_filters = filters.get("type_filters", {}).get("filters", {})
        assert "hunter_item" in type_filters
        assert "warlord_item" in type_filters


class TestTradeApiSourceNormalizeListing:
    """Tests for _normalize_listing edge cases."""

    def test_normalize_listing_no_price(self):
        """Should return None for listing without price."""
        source, _ = _make_source_with_fake_client([])

        listing = {
            "id": "123",
            "listing": {},
            "item": {}
        }
        result = source._normalize_listing(listing)
        assert result is None

    def test_normalize_listing_invalid_amount(self):
        """Should return None for invalid amount."""
        source, _ = _make_source_with_fake_client([])

        listing = {
            "id": "123",
            "listing": {
                "price": {
                    "amount": "not_a_number",
                    "currency": "chaos"
                }
            },
            "item": {}
        }
        result = source._normalize_listing(listing)
        assert result is None

    def test_normalize_listing_no_currency(self):
        """Should return None for missing currency."""
        source, _ = _make_source_with_fake_client([])

        listing = {
            "id": "123",
            "listing": {
                "price": {
                    "amount": 10,
                    "currency": None
                }
            },
            "item": {}
        }
        result = source._normalize_listing(listing)
        assert result is None

    def test_normalize_listing_exception_handling(self):
        """Should return None and log on unexpected exception."""
        source, _ = _make_source_with_fake_client([])

        # Create a nested dict that will raise an exception inside the try block
        class BadPriceDict(dict):
            def get(self, key, default=None):
                if key == "amount":
                    raise RuntimeError("Unexpected error")
                return super().get(key, default)

        listing = {
            "id": "123",
            "listing": {
                "price": BadPriceDict({"amount": 10, "currency": "chaos"})
            },
            "item": {}
        }
        result = source._normalize_listing(listing)
        assert result is None
