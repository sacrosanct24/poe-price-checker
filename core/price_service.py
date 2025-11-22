# core/price_service.py
from __future__ import annotations

from typing import Any, List
import logging

from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from data_sources.pricing.poe_ninja import PoeNinjaAPI

LOG = logging.getLogger(__name__)


class PriceService:
    """
    High-level API used by the GUI (and CLI) to get price information
    for a pasted item.

    The GUI only cares about:

        check_item(item_text: str) -> list[dict[str, Any]]

    where each dict has keys matching RESULT_COLUMNS in gui.main_window:

        ("item_name",
         "variant",
         "links",
         "chaos_value",
         "divine_value",
         "listing_count",
         "source")
    """

    def __init__(
        self,
        config: Config,
        parser: ItemParser,
        db: Database,
        poe_ninja: PoeNinjaAPI | None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.parser = parser
        self.db = db
        self.poe_ninja = poe_ninja
        self.logger = logger or LOG

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """
        Main entrypoint for the GUI.

        - Parse the raw item text.
        - Use poe.ninja (or fallback) to get a chaos value and listing count.
        - Convert to the RESULT_COLUMNS shape used by the GUI.
        """
        item_text = (item_text or "").strip()
        if not item_text:
            return []

        # 1) Parse item text → ParsedItem
        parsed = self.parser.parse(item_text)

        # 2) Look up a price
        chaos_value: float
        listing_count: int
        source_label: str

        if self.poe_ninja is None:
            # PoE2 or pricing disabled
            self.logger.info("poe_ninja is None; returning zero-price result.")
            chaos_value = 0.0
            listing_count = 0
            source_label = "no poe.ninja (PoE2 or disabled)"
        else:
            chaos_value, listing_count, source_label = self._lookup_price_with_poe_ninja(parsed)

        # 3) Divine conversion (if we can)
        divine_value = self._convert_chaos_to_divines(chaos_value)

        # 4) Build a single-row result list.
        row = {
            "item_name": self._get_item_display_name(parsed),
            "variant": self._get_item_variant(parsed),
            "links": self._get_item_links(parsed),
            "chaos_value": f"{chaos_value:.1f}",
            "divine_value": f"{divine_value:.2f}",
            "listing_count": str(listing_count),
            "source": source_label,
        }
        return [row]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _lookup_price_with_poe_ninja(self, parsed: Any) -> tuple[float, int, str]:
        """
        Call PoeNinjaAPI to get a price for the parsed item.

        Returns:
            (chaos_value, listing_count, source_label)
        """
        if self.poe_ninja is None:
            return 0.0, 0, "no poe.ninja"

        # Extract fields from ParsedItem as flexibly as possible
        item_name = self._get_item_display_name(parsed)
        base_type = self._get_base_type(parsed)
        rarity = (self._get_rarity(parsed) or "").upper()
        gem_level = self._get_gem_level(parsed)
        gem_quality = self._get_gem_quality(parsed)
        corrupted = self._get_corrupted_flag(parsed)

        # ---------- Currency special-case ----------
        if rarity == "CURRENCY":
            return self._lookup_currency_price(item_name)

        # ---------- Everything else via find_item_price ----------
        try:
            price_data = self.poe_ninja.find_item_price(
                item_name=item_name,
                base_type=base_type,
                rarity=rarity,
                gem_level=gem_level,
                gem_quality=gem_quality,
                corrupted=corrupted,
            )
        except Exception as exc:
            self.logger.warning("poe.ninja find_item_price failed: %s", exc)
            return 0.0, 0, "poe.ninja error"

        if not price_data:
            self.logger.info("poe.ninja: no price found for '%s' (rarity=%s)", item_name, rarity)
            return 0.0, 0, "not found"

        chaos_raw = (
            price_data.get("chaosValue")
            or price_data.get("chaos_value")
            or price_data.get("chaosEquivalent")
            or 0.0
        )
        count_raw = (
            price_data.get("count")
            or price_data.get("listingCount")
            or price_data.get("listing_count")
            or 0
        )

        try:
            chaos_value = float(chaos_raw)
        except (TypeError, ValueError):
            chaos_value = 0.0

        try:
            listing_count = int(count_raw)
        except (TypeError, ValueError):
            listing_count = 0

        return chaos_value, listing_count, "poe.ninja"

    def _convert_chaos_to_divines(self, chaos_value: float) -> float:
        """
        Convert chaos to divines using, in order of preference:
        - explicit rate on Config (config.divine_rate)
        - poe.ninja's divine_chaos_rate, if non-trivial
        """
        # 1) Config override
        rate = getattr(self.config, "divine_rate", None)
        if rate:
            try:
                r = float(rate)
            except (TypeError, ValueError):
                r = 0.0
            if r > 0:
                return chaos_value / r

        # 2) poe.ninja divine/chaos rate
        if self.poe_ninja is not None:
            try:
                r = float(getattr(self.poe_ninja, "divine_chaos_rate", 0.0))
            except (TypeError, ValueError):
                r = 0.0
            if r > 0:
                return chaos_value / r

        # 3) Fallback: unknown
        return 0.0

    # ------------------------------------------------------------------ #
    # Parsed item helpers – resilient to different ParsedItem schemas
    # ------------------------------------------------------------------ #

    def _get_item_display_name(self, parsed: Any) -> str:
        """
        Best-effort extraction of a user-facing item name from ParsedItem.
        """
        for attr in ("display_name", "full_name", "name", "base_name", "item_name"):
            val = getattr(parsed, attr, None)
            if val:
                return str(val)
        return "Unknown Item"

    def _get_base_type(self, parsed: Any) -> str | None:
        for attr in ("base_type", "baseType", "base_name"):
            val = getattr(parsed, attr, None)
            if val:
                return str(val)
        return None

    def _get_rarity(self, parsed: Any) -> str | None:
        val = getattr(parsed, "rarity", None)
        if not val:
            return None
        return str(val)

    def _get_gem_level(self, parsed: Any) -> int | None:
        for attr in ("gem_level", "level"):
            val = getattr(parsed, attr, None)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
        return None

    def _get_item_variant(self, parsed: Any) -> str:
        """
        Variant / extra label – e.g., influence, fracture, special flags.

        If your ParsedItem tracks any of these as attributes, they will show up
        in the "Variant" column. Otherwise this will just be "".
        """
        for attr in ("variant", "variant_label", "influence_label", "extra_label"):
            val = getattr(parsed, attr, None)
            if val:
                return str(val)
        return ""

    def _get_gem_quality(self, parsed: Any) -> int | None:
        for attr in ("gem_quality", "quality"):
            val = getattr(parsed, attr, None)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
        return None

    def _get_corrupted_flag(self, parsed: Any) -> bool | None:
        """
        Return True/False if we know it's corrupted / not corrupted, or None if unknown.
        """
        val = getattr(parsed, "corrupted", None)
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        # Some parsers store "Corrupted"/"" strings
        s = str(val).strip().lower()
        if s in ("true", "yes", "1", "corrupted"):
            return True
        if s in ("false", "no", "0", ""):
            return False
        return None

    def _get_item_links(self, parsed: Any) -> str:
        """
        Extract number of linked sockets, if your ParsedItem tracks it.
        """
        for attr in ("links", "link_count", "socket_links"):
            val = getattr(parsed, attr, None)
            if val is not None:
                try:
                    return str(int(val))
                except (TypeError, ValueError):
                    return str(val)
        return "0"

    def _lookup_currency_price(self, item_name: str) -> tuple[float, int, str]:
        """
        Use poe.ninja's currencyoverview endpoint to price currency items
        like Divine Orb, Exalted Orb, etc.
        """
        if self.poe_ninja is None:
            return 0.0, 0, "no poe.ninja"

        key = (item_name or "").strip().lower()
        if not key:
            return 0.0, 0, "not found"

        try:
            data = self.poe_ninja.get_currency_overview()
        except Exception as exc:
            self.logger.warning("poe.ninja get_currency_overview failed: %s", exc)
            return 0.0, 0, "poe.ninja error"

        lines = data.get("lines", []) or []
        for line in lines:
            ctype = (line.get("currencyTypeName") or "").strip().lower()
            if ctype == key:
                chaos_raw = (
                    line.get("chaosEquivalent")
                    or line.get("chaosValue")
                    or 0.0
                )
                try:
                    chaos_value = float(chaos_raw)
                except (TypeError, ValueError):
                    chaos_value = 0.0

                # poe.ninja currencyoverview doesn't have a clean "listing count"
                # so we just return 0 here.
                return chaos_value, 0, "poe.ninja currency"

        self.logger.info("poe.ninja currency: no price found for '%s'", item_name)
        return 0.0, 0, "not found"
