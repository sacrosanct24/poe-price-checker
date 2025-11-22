# data_sources/pricing/trade_api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import logging

from core.price_multi import PriceSource, RESULT_COLUMNS


class PoeTradeClient:
    """
    Thin client for the official PoE Trade API.

    This is intentionally a stub/skeleton:
      - Add HTTP session handling here (requests / httpx / aiohttp, etc.)
      - Add search + fetch logic here later.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("poe_price_checker.trade_api")

    def search_and_fetch(self, item_text: str, league: str) -> list[Mapping[str, Any]]:
        """
        High-level helper: perform a full search + fetch cycle for the given item.

        For now this is just a stub returning an empty result list. Later you'll:
          - Parse the item_text into a structured ParsedItem (you already have ItemParser).
          - Build the Trade API search payload.
          - POST to /api/trade/search/<league>.
          - GET /api/trade/fetch/<ids>?query=<search_id>.
          - Extract price + listing details.
        """
        self.logger.info("Trade API search stub called for league=%s", league)

        # TODO: implement real HTTP calls and response parsing.
        return []


@dataclass
class TradeApiSource(PriceSource):
    """
    PriceSource implementation backed by the official Trade API.

    Responsibilities:
      - Use PoeTradeClient to talk to the HTTP API.
      - Convert raw listings into normalized rows with RESULT_COLUMNS.
      - Tag each row with `source = self.name` (usually 'trade_api').
    """

    name: str
    client: PoeTradeClient
    league: str
    logger: logging.Logger

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """
        Run a price check for a single item using the Trade API.

        Returns a list of normalized dict rows with keys:
          item_name, variant, links, chaos_value, divine_value,
          listing_count, source
        """
        item_text = (item_text or "").strip()
        if not item_text:
            return []

        self.logger.info("TradeApiSource.check_item called for league=%s", self.league)

        raw_listings = self.client.search_and_fetch(item_text=item_text, league=self.league)

        rows: list[dict[str, Any]] = []

        # In the real implementation, `raw_listings` would be the parsed JSON from
        # the Trade API, and you’d iterate through the listings to extract usable
        # price + item information. For now we simply normalize an empty list.
        for listing in raw_listings:
            # Skeleton normalization – adapt once you know the data shape.
            data: dict[str, Any] = {}

            # These will eventually come from the parsed Trade API response.
            data["item_name"] = listing.get("item_name", "")  # TODO
            data["variant"] = listing.get("variant", "")  # TODO
            data["links"] = listing.get("links", "")  # TODO

            # Price normalization: convert whatever currency into chaos/divine.
            data["chaos_value"] = listing.get("chaos_value", "")  # TODO
            data["divine_value"] = listing.get("divine_value", "")  # TODO

            # This might be per-listing, or aggregated; design choice:
            data["listing_count"] = listing.get("listing_count", "")  # TODO

            # Ensure source is always set
            data["source"] = self.name

            # Ensure all expected keys exist
            for col in RESULT_COLUMNS:
                data.setdefault(col, "")

            rows.append(data)

        return rows
