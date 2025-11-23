from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Mapping, Optional

import requests

from data_sources.base_api import BaseAPIClient
from core.price_multi import RESULT_COLUMNS

logger = logging.getLogger(__name__)


class PoeTradeClient(BaseAPIClient):
    """
    Low-level HTTP client for the official Path of Exile trade API.

    Thin wrapper around BaseAPIClient so other components (e.g. TradeApiSource)
    can share rate limiting, caching, and base_url.
    """

    def __init__(
        self,
        league: str = "Standard",
        *,
        logger: Optional[logging.Logger] = None,
        rate_limit: float = 0.33,  # ~1 request per 3 seconds
        cache_ttl: int = 60,       # short TTL for trade listings
        user_agent: Optional[str] = None,
    ) -> None:
        super().__init__(
            base_url="https://www.pathofexile.com/api/trade",
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            user_agent=(
                user_agent
                or "PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)"
            ),
        )

        self.league = league
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info(
            "Initialized PoeTradeClient for league=%s (rate=%.2f req/s, cache_ttl=%ds)",
            league,
            rate_limit,
            cache_ttl,
        )

    # ------------------------------------------------------------------ #
    # BaseAPIClient abstract method
    # ------------------------------------------------------------------ #

    def _get_cache_key(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        **_: Any,
    ) -> str:
        """
        Build a deterministic cache key for a request.

        We keep it simple:
            METHOD:PATH?sorted_query_params

        Body is ignored for trade API calls since we mostly use GET with
        query parameters, and BaseAPIClient already scopes by base_url.
        """
        method = (method or "GET").upper()
        key = f"{method}:{path}"

        if params:
            # sort query params for stability
            items = sorted((str(k), str(v)) for k, v in params.items())
            query = "&".join(f"{k}={v}" for k, v in items)
            key = f"{key}?{query}"

        return key


class TradeApiSource:
    """
    Wrapper around trade data that supports two modes:

    1) High-level "price source" mode (used in tests):
       - check_item(item_text: str) ->
         list of GUI-style rows with RESULT_COLUMNS, using
         client.search_and_fetch(item_text, league).

    2) Low-level listing mode (used by PriceService):
       - check_item(parsed_item: ParsedItem, max_results=20) ->
         list of quote dicts with original_currency/amount/etc.,
         using the official PoE trade HTTP API (search + fetch).
    """

    BASE_URL = "https://www.pathofexile.com/api/trade"

    def __init__(
        self,
        client: Optional[PoeTradeClient] = None,
        *,
        league: Optional[str] = None,
        name: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        **_: Any,
    ) -> None:
        """
        Wrap a PoeTradeClient.

        Parameters:
            client: PoeTradeClient instance for this league. If omitted,
                    a new one will be created using `league`.
            league: Optional league name override (e.g. "Keepers").
            name: Optional logical name for this source (e.g. "trade_api").
            logger: Logger to use; defaults to module logger.
            session: Optional requests.Session (used in tests to inject fakes).
        """
        self.logger = logger or logging.getLogger(__name__)

        # Decide which league to use and ensure we have a client
        if client is None:
            effective_league = league or "Standard"
            client = PoeTradeClient(league=effective_league, logger=self.logger)
        else:
            effective_league = league or client.league

        self.client = client
        self.league = effective_league
        self.name = name or "trade_api"

        # Session for low-level HTTP mode
        if session is not None:
            self.session = session
        elif hasattr(self.client, "session"):
            self.session = self.client.session
        else:
            self.session = requests.Session()

        self.logger.info(
            "Initialized TradeApiSource(name=%s, league=%s)",
            self.name,
            self.league,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_item(
        self,
        item_or_parsed: Any,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Overloaded behavior:

        - If `item_or_parsed` is a string, use high-level test-friendly mode:
          call client.search_and_fetch(item_text, league) and normalize into
          GUI-style rows with RESULT_COLUMNS.

        - Otherwise, treat it as a ParsedItem and use low-level HTTP mode to
          fetch listings and return quote dicts for PriceService.
        """
        # Test / high-level mode (string input)
        if isinstance(item_or_parsed, str):
            return self._check_item_text(item_or_parsed)

        # Runtime / low-level mode (ParsedItem)
        return self._check_parsed_item(item_or_parsed, max_results=max_results)

    # ------------------------------------------------------------------ #
    # High-level mode for tests (FakeTradeClient)
    # ------------------------------------------------------------------ #

    def _check_item_text(self, item_text: str) -> List[Dict[str, Any]]:
        """
        High-level mode: item_text -> search_and_fetch -> GUI-style rows.

        Used by unit tests via FakeTradeClient, and by any callers that
        treat this as a PriceSource.
        """
        self.logger.info(
            "TradeApiSource._check_item_text called for league=%s", self.league
        )

        # Blank item text: do NOT call the client, just return no rows.
        if not item_text or item_text.strip() == "":
            self.logger.info(
                "TradeApiSource._check_item_text: blank item_text; returning 0 rows."
            )
            return []

        # If the client exposes search_and_fetch (as in FakeTradeClient),
        # use it. This is what the tests expect.
        search_fn = getattr(self.client, "search_and_fetch", None)
        if not callable(search_fn):
            self.logger.warning(
                "TradeApiSource._check_item_text: client has no search_and_fetch; "
                "returning 0 rows."
            )
            return []

        listings: List[Mapping[str, Any]] = list(
            search_fn(item_text, self.league)
        )

        rows: List[Dict[str, Any]] = []
        for listing in listings:
            row: Dict[str, Any] = {col: "" for col in RESULT_COLUMNS}
            # Populate from listing keys that exist
            if "item_name" in listing:
                row["item_name"] = listing["item_name"]
            if "variant" in listing:
                row["variant"] = listing["variant"]
            if "links" in listing:
                row["links"] = listing["links"]
            if "chaos_value" in listing:
                row["chaos_value"] = listing["chaos_value"]
            if "divine_value" in listing:
                row["divine_value"] = listing["divine_value"]
            if "listing_count" in listing:
                row["listing_count"] = listing["listing_count"]

            # Source label must match what tests expect
            row["source"] = self.name

            rows.append(row)

        self.logger.info(
            "TradeApiSource._check_item_text: returning %d row(s) for %r in league=%s",
            len(rows),
            item_text,
            self.league,
        )
        return rows

    # ------------------------------------------------------------------ #
    # Low-level mode for PriceService (ParsedItem -> quotes)
    # ------------------------------------------------------------------ #

    def _check_parsed_item(
        self,
        parsed_item: Any,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Low-level mode: ParsedItem -> PoE trade search+fetch -> quote dicts.

        This is what PriceService uses to get listing-level quotes to
        save into price_quotes.
        """
        self.logger.info(
            "TradeApiSource._check_parsed_item called for league=%s", self.league
        )

        if parsed_item is None:
            self.logger.info(
                "TradeApiSource._check_parsed_item: parsed_item is None; returning 0 quotes."
            )
            return []

        # 1) Build a simple search query JSON based on ParsedItem
        query = self._build_query(parsed_item)

        # If the query has no name/type at all, treat as blank
        q_inner = query.get("query", {})
        q_name = (q_inner.get("name") or "").strip() if isinstance(q_inner, dict) else ""
        q_type = (q_inner.get("type") or "").strip() if isinstance(q_inner, dict) else ""
        if not q_name and not q_type:
            self.logger.info(
                "TradeApiSource._check_parsed_item: blank query (no name/type); returning 0 quotes."
            )
            return []

        # 2) POST /search/{league}
        search_id, result_ids = self._search(query, max_results=max_results)
        if not search_id or not result_ids:
            self.logger.info(
                "TradeApiSource._check_parsed_item: no result_ids for item; search_id=%s",
                search_id,
            )
            return []

        # 3) GET /fetch/{id1,id2,...}?query=search_id
        listings = self._fetch_listings(search_id, result_ids)

        # 4) Normalize into simple quote dicts (for PriceService)
        quotes: List[Dict[str, Any]] = []
        for listing in listings:
            q = self._normalize_listing(listing)
            if q is not None:
                quotes.append(q)

        self.logger.info(
            "TradeApiSource._check_parsed_item: normalized %d/%d listings into quotes "
            "for league=%s",
            len(quotes),
            len(listings),
            self.league,
        )

        return quotes

    # ------------------------------------------------------------------ #
    # Internal helpers (low-level HTTP mode)
    # ------------------------------------------------------------------ #

    def _build_query(self, parsed_item: Any) -> Dict[str, Any]:
        """
        Very basic query builder.

        For uniques, we usually specify name + type.
        For now we assume PoE1 uniques like Tabula Rasa; you can extend
        this to handle rares, maps, etc. as your ParsedItem grows.
        """
        name = getattr(parsed_item, "name", None) or getattr(
            parsed_item, "display_name", None
        )
        base_type = getattr(parsed_item, "base_type", None) or getattr(
            parsed_item, "base_name", None
        )

        name_str = str(name or "").strip()
        base_str = str(base_type or "").strip()

        query: Dict[str, Any] = {
            "query": {
                "status": {"option": "online"},
                "stats": [{"type": "and", "filters": []}],
            },
            "sort": {"price": "asc"},
        }

        if name_str:
            query["query"]["name"] = name_str
        if base_str:
            query["query"]["type"] = base_str

        return query

    def _search(
        self,
        query: Dict[str, Any],
        *,
        max_results: int,
    ) -> tuple[Optional[str], List[str]]:
        """
        POST /search/{league} and return (search_id, [result_ids]).
        """
        url = f"{self.BASE_URL}/search/{self.league}"
        self.logger.info("Trade API search: %s", url)

        try:
            query_snippet = json.dumps(query)[:800]
        except TypeError:
            query_snippet = str(query)[:800]
        self.logger.debug("Trade API search payload (truncated): %s", query_snippet)

        resp = self.session.post(url, json=query, timeout=15)
        self.logger.debug("Trade API search status=%s", resp.status_code)
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError:
            self.logger.exception("Trade API search returned non-JSON response")
            return None, []

        raw_snippet = json.dumps(data, default=str)[:1200]
        self.logger.debug("Trade API search raw JSON (truncated): %s", raw_snippet)

        search_id = data.get("id")
        result_ids = data.get("result") or []
        if not isinstance(result_ids, list):
            self.logger.warning(
                "Trade API search 'result' field is not a list: %r", type(result_ids)
            )
            result_ids = []

        total = data.get("total", len(result_ids))
        trimmed_result_ids = result_ids[:max_results]

        self.logger.info(
            "Trade API search parsed: search_id=%s total=%s result_count=%s (using %s)",
            search_id,
            total,
            len(result_ids),
            len(trimmed_result_ids),
        )

        if not trimmed_result_ids:
            self.logger.warning(
                "Trade API search returned 0 usable result_ids for search_id=%s "
                "(total=%s)",
                search_id,
                total,
            )

        return search_id, trimmed_result_ids

    def _fetch_listings(
        self,
        search_id: str,
        result_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        GET /fetch/{id1,id2,...}?query=search_id
        """
        if not result_ids:
            self.logger.warning(
                "Trade API fetch skipped: no result_ids for search_id=%s",
                search_id,
            )
            return []

        listings: List[Dict[str, Any]] = []
        batch_size = 10

        for i in range(0, len(result_ids), batch_size):
            batch_ids = result_ids[i : i + batch_size]
            ids_str = ",".join(batch_ids)
            url = f"{self.BASE_URL}/fetch/{ids_str}"
            params = {"query": search_id}

            self.logger.info(
                "Trade API fetch: %s (batch size=%d, query=%s)",
                url,
                len(batch_ids),
                search_id,
            )

            resp = self.session.get(url, params=params, timeout=15)
            self.logger.debug("Trade API fetch status=%s", resp.status_code)
            resp.raise_for_status()

            try:
                data = resp.json()
            except ValueError:
                self.logger.exception(
                    "Trade API fetch returned non-JSON response for search_id=%s",
                    search_id,
                )
                continue

            batch_results = data.get("result") or []
            self.logger.info(
                "Trade API fetch parsed: search_id=%s, batch_results=%d",
                search_id,
                len(batch_results),
            )

            listings.extend(batch_results)

        self.logger.info(
            "Trade API fetch total listings: %d for search_id=%s",
            len(listings),
            search_id,
        )

        return listings

    def _normalize_listing(self, listing: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert raw trade listing JSON into a simple quote dict for PriceService.

        We *do not* convert currencies here; we return amount + currency,
        plus some helpful metadata.

        Returns None if no price is present (e.g. "mirrored", not-for-sale, etc.).
        """
        listing_id = listing.get("id")
        l = listing.get("listing") or {}
        item = listing.get("item") or {}

        try:
            price = l.get("price")
            if not price:
                return None

            amount_raw = price.get("amount")
            currency = price.get("currency")

            try:
                amount = float(amount_raw)
            except (TypeError, ValueError):
                amount = None

            if amount is None or not currency:
                return None

            account = (l.get("account") or {}).get("name")
            listed_at = l.get("indexed")
            stack_size = item.get("stackSize")

            return {
                "source": "trade",
                "price_chaos": None,
                "original_currency": str(currency).lower(),
                "amount": amount,
                "stack_size": stack_size,
                "listing_id": listing_id,
                "seller_account": account,
                "listed_at": listed_at,
            }

        except Exception as exc:
            self.logger.exception(
                "Failed to normalize trade listing; skipping. listing_id=%s, error=%s",
                listing_id,
                exc,
            )
            return None
