from __future__ import annotations

from typing import Any, Dict
import logging

import pytest

from data_sources.pricing.trade_api import TradeApiSource

pytestmark = pytest.mark.unit


# -------------------------------------------------------------------
# Dummy ParsedItem
# -------------------------------------------------------------------


class DummyParsedItem:
    """
    Minimal stand-in for your real ParsedItem that has the attributes used by
    _build_query: name/display_name + base_type/base_name.
    """

    def __init__(self, name: str | None = None, base_type: str | None = None) -> None:
        self.name = name
        self.base_type = base_type
        # extra attrs are ignored by TradeApiSource._build_query, but harmless
        self.rarity = "Unique"
        self.item_level = 86


# -------------------------------------------------------------------
# Fake HTTP machinery for low-level mode
# -------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status_code: int = 200, json_data: Dict[str, Any] | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self) -> None:
        # For tests we just no-op; all responses are "OK".
        return None

    def json(self) -> Dict[str, Any]:
        return self._json_data


class FakeSession:
    """
    Simple fake requests.Session used by TradeApiSource in low-level mode.

    We enqueue responses for POST (search) and GET (fetch) separately so we
    can control exactly what the TradeApiSource methods see.
    """

    def __init__(self) -> None:
        self._post_responses: list[FakeResponse] = []
        self._get_responses: list[FakeResponse] = []
        self.post_calls: list[tuple[str, Dict[str, Any]]] = []
        self.get_calls: list[tuple[str, Dict[str, Any] | None]] = []

    def enqueue_post(self, response: FakeResponse) -> None:
        self._post_responses.append(response)

    def enqueue_get(self, response: FakeResponse) -> None:
        self._get_responses.append(response)

    # Match the subset of requests.Session.post/get used by TradeApiSource

    def post(self, url: str, json: Dict[str, Any], timeout: int = 15) -> FakeResponse:  # type: ignore[override]
        self.post_calls.append((url, json))
        if not self._post_responses:
            raise RuntimeError("No FakeResponse enqueued for POST")
        return self._post_responses.pop(0)

    def get(
        self,
        url: str,
        params: Dict[str, Any] | None = None,
        timeout: int = 15,
    ) -> FakeResponse:  # type: ignore[override]
        self.get_calls.append((url, params))
        if not self._get_responses:
            raise RuntimeError("No FakeResponse enqueued for GET")
        return self._get_responses.pop(0)


def _make_source_with_fake_session(
    league: str = "Crucible",
) -> tuple[TradeApiSource, FakeSession]:
    session = FakeSession()
    src = TradeApiSource(
        client=None,
        league=league,
        name="trade",
        logger=logging.getLogger("test.trade.low"),
        session=session,
    )
    return src, session


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_check_parsed_item_returns_empty_for_none() -> None:
    src, _ = _make_source_with_fake_session(league="Crucible")

    quotes = src._check_parsed_item(parsed_item=None, max_results=10)
    assert quotes == []


def test_check_parsed_item_returns_empty_for_blank_query() -> None:
    """
    When _build_query produces a query with no name/type, _check_parsed_item
    should treat it as blank input and return no quotes.
    """
    src, _ = _make_source_with_fake_session(league="Crucible")

    parsed = DummyParsedItem(name="   ", base_type="   ")
    quotes = src._check_parsed_item(parsed, max_results=10)

    assert quotes == []


def test_check_parsed_item_happy_path_search_and_fetch_normalized() -> None:
    """
    Full low-level flow:

    - _build_query uses ParsedItem to build a search query
    - _search POSTs to /search/{league} and returns (search_id, [result_ids])
    - _fetch_listings GETs /fetch/{ids}?query=search_id
    - _normalize_listing converts the first listing with a usable price into a quote
    """
    src, session = _make_source_with_fake_session(league="Crucible")
    parsed = DummyParsedItem(name="Goldrim", base_type="Leather Cap")

    # 1) Enqueue search response for POST /search/{league}
    search_json = {
        "id": "search123",
        "result": ["id1", "id2"],
    }
    session.enqueue_post(FakeResponse(json_data=search_json))

    # 2) Enqueue fetch response for GET /fetch/id1,id2?query=search123
    fetch_json = {
        "result": [
            {
                "id": "id1",
                "listing": {
                    "price": {
                        "amount": 1,
                        "currency": "chaos",
                    },
                    "account": {"name": "SomeSeller"},
                    "indexed": "2025-01-01T00:00:00Z",
                },
                "item": {
                    "stackSize": 1,
                },
            },
            {
                # This second result is missing a usable price and should be ignored
                "id": "id2",
                "listing": {
                    "price": None,
                },
                "item": {},
            },
        ]
    }
    session.enqueue_get(FakeResponse(json_data=fetch_json))

    quotes = src._check_parsed_item(parsed, max_results=10)

    # Only the first listing should have produced a normalized quote
    assert len(quotes) == 1
    q = quotes[0]

    # Basic fields from _normalize_listing
    assert q["source"] == "trade"
    assert q["original_currency"] == "chaos"
    assert q["amount"] == 1.0
    assert q["listing_id"] == "id1"
    assert q["seller_account"] == "SomeSeller"
    assert q["stack_size"] == 1

    # There should have been one POST and one GET call
    assert len(session.post_calls) == 1
    assert len(session.get_calls) == 1

    post_url, post_body = session.post_calls[0]
    assert "/search/Crucible" in post_url
    assert isinstance(post_body, dict)

    get_url, get_params = session.get_calls[0]
    assert "/fetch/" in get_url
    assert isinstance(get_params, dict | type(None))
    if isinstance(get_params, dict):
        assert get_params.get("query") == "search123"
