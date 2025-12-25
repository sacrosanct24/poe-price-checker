"""Polling service for ML data collection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4

from core.database import Database
from core.game_version import GameVersion
from core.item_parser import ParsedItem
from data_sources.mod_database import ModDatabase

if TYPE_CHECKING:
    from data_sources.pricing.poe_ninja import PoeNinjaAPI
    from data_sources.pricing.trade_api import PoeTradeClient

from ml.collection.affix_extractor import AffixExtractor
from ml.collection.config import ML_COLLECTION_CONFIG

logger = logging.getLogger(__name__)

CurrencyConverter = Callable[[float, str], Optional[float]]


@dataclass
class MLRunStats:
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    listings_fetched: int = 0
    listings_new: int = 0
    listings_updated: int = 0
    errors: int = 0
    error_details: List[str] = field(default_factory=list)


class MLPollingService:
    """
    Polls Trade API for listings at configured interval.

    Config:
        - base_types: list of base types to poll
        - frequency_minutes: polling interval (default 30)
        - league: target league
        - game_id: poe1 or poe2
        - enabled: on/off flag

    Uses existing Trade API integration and rate limiting.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        db: Optional[Database] = None,
        mod_database: Optional[ModDatabase] = None,
        trade_client: Optional["PoeTradeClient"] = None,
        price_converter: Optional[CurrencyConverter] = None,
        logger_override: Optional[logging.Logger] = None,
    ) -> None:
        self.config = _merge_config(config)
        self.enabled = bool(self.config.get("enabled", True))
        self.league = str(self.config.get("league") or "Standard")
        self.game_id = str(self.config.get("game_id") or "poe1")
        self.frequency_minutes = int(self.config.get("frequency_minutes") or 30)
        self.max_listings_per_base = int(self.config.get("max_listings_per_base") or 100)
        self.base_types = _flatten_base_types(self.config.get("base_types"))
        self.logger = logger_override or logger

        self.db = db or Database()
        self.mod_db = mod_database or ModDatabase()
        self.affix_extractor = AffixExtractor(self.mod_db, logger_override=self.logger)

        game_version = GameVersion.from_string(self.game_id) or GameVersion.POE1
        if trade_client is not None:
            self.trade_client = trade_client
        else:
            from data_sources.pricing.trade_api import PoeTradeClient

            self.trade_client = PoeTradeClient(
                league=self.league,
                game_version=game_version,
                logger=self.logger,
            )
        self.price_converter = price_converter or DefaultPriceConverter(
            league=self.league,
            game_id=self.game_id,
            logger_override=self.logger,
        )

    def poll_once(self) -> Tuple[MLRunStats, List[str]]:
        """Run a single polling cycle."""
        run_id = uuid4().hex
        started_at = _now_iso()
        stats = MLRunStats(run_id=run_id, started_at=started_at)
        seen_listing_ids: List[str] = []

        if not self.enabled:
            self.logger.info("ML polling disabled; skipping run_id=%s", run_id)
            return stats, seen_listing_ids

        self.logger.info("Collection run started: run_id=%s", run_id)
        self._log_gap_if_needed()
        self._record_run_start(run_id, started_at)

        for base_type in self.base_types:
            try:
                listings = self._fetch_listings_for_base(base_type)
                stats.listings_fetched += len(listings)
                self.logger.info("Polling %s: %d listings", base_type, len(listings))
                new_count, updated_count, seen_ids = self._process_listings(listings)
                stats.listings_new += new_count
                stats.listings_updated += updated_count
                seen_listing_ids.extend(seen_ids)
            except Exception as exc:
                stats.errors += 1
                msg = f"Polling failed for base '{base_type}': {exc}"
                stats.error_details.append(msg)
                self.logger.exception(msg)

        stats.completed_at = _now_iso()
        self._record_run_complete(stats)
        self.logger.info(
            "Collection run completed: fetched=%s, new=%s, updated=%s, errors=%s",
            stats.listings_fetched,
            stats.listings_new,
            stats.listings_updated,
            stats.errors,
        )

        return stats, seen_listing_ids

    def _fetch_listings_for_base(self, base_type: str) -> List[Dict[str, Any]]:
        query = _build_trade_query(base_type)
        search = self.trade_client.post(f"search/{self.league}", data=query)
        search_id = search.get("id")
        result_ids = search.get("result") or []
        if not search_id or not isinstance(result_ids, list):
            return []

        result_ids = result_ids[: self.max_listings_per_base]
        if not result_ids:
            return []

        listings: List[Dict[str, Any]] = []
        for batch in _chunked(result_ids, 10):
            ids_str = ",".join(batch)
            data = self.trade_client.get(
                f"fetch/{ids_str}",
                params={"query": search_id},
                use_cache=False,
            )
            batch_results = data.get("result") or []
            if isinstance(batch_results, list):
                listings.extend(batch_results)

        return listings

    def _process_listings(self, listings: Iterable[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        now = _now_iso()
        new_count = 0
        updated_count = 0
        seen_ids: List[str] = []

        with self.db.transaction() as conn:
            for listing in listings:
                record = self._build_listing_record(listing, now)
                if record is None:
                    continue

                listing_id = record["listing_id"]
                existing = conn.execute(
                    "SELECT id FROM ml_listings WHERE listing_id = ?",
                    (listing_id,),
                ).fetchone()

                if existing:
                    conn.execute(
                        """
                        UPDATE ml_listings
                        SET item_class = ?,
                            base_type = ?,
                            ilvl = ?,
                            influences = ?,
                            flags = ?,
                            affixes = ?,
                            price_chaos = ?,
                            original_currency = ?,
                            original_amount = ?,
                            seller_account = ?,
                            last_seen_at = ?
                        WHERE listing_id = ?
                        """,
                        (
                            record["item_class"],
                            record["base_type"],
                            record["ilvl"],
                            record["influences"],
                            record["flags"],
                            record["affixes"],
                            record["price_chaos"],
                            record["original_currency"],
                            record["original_amount"],
                            record["seller_account"],
                            record["last_seen_at"],
                            listing_id,
                        ),
                    )
                    updated_count += 1
                else:
                    conn.execute(
                        """
                        INSERT INTO ml_listings (
                            listing_id,
                            game_id,
                            league,
                            item_class,
                            base_type,
                            ilvl,
                            influences,
                            flags,
                            affixes,
                            price_chaos,
                            original_currency,
                            original_amount,
                            seller_account,
                            first_seen_at,
                            last_seen_at,
                            listing_state
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record["listing_id"],
                            record["game_id"],
                            record["league"],
                            record["item_class"],
                            record["base_type"],
                            record["ilvl"],
                            record["influences"],
                            record["flags"],
                            record["affixes"],
                            record["price_chaos"],
                            record["original_currency"],
                            record["original_amount"],
                            record["seller_account"],
                            record["first_seen_at"],
                            record["last_seen_at"],
                            record["listing_state"],
                        ),
                    )
                    new_count += 1

                seen_ids.append(listing_id)

        return new_count, updated_count, seen_ids

    def _build_listing_record(
        self,
        listing: Dict[str, Any],
        now_iso: str,
    ) -> Optional[Dict[str, Any]]:
        listing_id = listing.get("id")
        listing_info = listing.get("listing") or {}
        item_info = listing.get("item") or {}

        if not listing_id:
            return None
        listing_id = str(listing_id)

        price_info = listing_info.get("price") or {}
        amount_raw = price_info.get("amount")
        currency_raw = price_info.get("currency")
        if amount_raw is None or currency_raw is None:
            return None

        try:
            amount = float(amount_raw)
        except (TypeError, ValueError):
            return None

        price_chaos = self.price_converter(amount, str(currency_raw))
        if price_chaos is None:
            return None

        parsed = ParsedItem.from_stash_item(item_info)
        base_type = parsed.base_type or item_info.get("baseType") or item_info.get("typeLine")
        if not base_type:
            return None

        influences = parsed.influences or []
        flags = {
            "corrupted": parsed.is_corrupted,
            "mirrored": parsed.is_mirrored,
            "fractured": parsed.is_fractured,
            "synthesised": parsed.is_synthesised,
        }
        affixes = self.affix_extractor.extract(parsed)

        return {
            "listing_id": listing_id,
            "game_id": self.game_id,
            "league": self.league,
            "item_class": _extract_item_class(item_info) or "Unknown",
            "base_type": base_type,
            "ilvl": parsed.item_level,
            "influences": json.dumps(influences),
            "flags": json.dumps(flags),
            "affixes": json.dumps(affixes),
            "price_chaos": price_chaos,
            "original_currency": str(currency_raw).lower(),
            "original_amount": amount,
            "seller_account": _extract_seller_account(listing_info),
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "listing_state": "LIVE",
        }

    def _record_run_start(self, run_id: str, started_at: str) -> None:
        self.db._execute(
            """
            INSERT INTO ml_collection_runs (run_id, game_id, league, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, self.game_id, self.league, started_at),
        )

    def _record_run_complete(self, stats: MLRunStats) -> None:
        self.db._execute(
            """
            UPDATE ml_collection_runs
            SET completed_at = ?,
                listings_fetched = ?,
                listings_new = ?,
                listings_updated = ?,
                errors = ?,
                error_details = ?
            WHERE run_id = ?
            """,
            (
                stats.completed_at,
                stats.listings_fetched,
                stats.listings_new,
                stats.listings_updated,
                stats.errors,
                json.dumps(stats.error_details),
                stats.run_id,
            ),
        )

    def _log_gap_if_needed(self) -> None:
        row = self.db._execute_fetchone(
            """
            SELECT MAX(last_seen_at) AS last_seen
            FROM ml_listings
            WHERE league = ? AND game_id = ?
            """,
            (self.league, self.game_id),
        )
        if not row:
            return

        last_seen = _parse_timestamp(row["last_seen"])
        if not last_seen:
            return

        now = datetime.now(timezone.utc)
        gap_minutes = (now - last_seen).total_seconds() / 60
        if gap_minutes > (self.frequency_minutes * 2):
            self.logger.warning(
                "Collection gap detected: last_seen_at=%s gap_minutes=%.1f",
                last_seen.isoformat(timespec="seconds"),
                gap_minutes,
            )


def _merge_config(overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config = dict(ML_COLLECTION_CONFIG)
    if overrides:
        config.update(overrides)
    return config


def _flatten_base_types(base_types: Any) -> List[str]:
    if isinstance(base_types, dict):
        flattened: List[str] = []
        for values in base_types.values():
            if isinstance(values, list):
                flattened.extend(values)
        return flattened
    if isinstance(base_types, list):
        return base_types
    return []


def _build_trade_query(base_type: str) -> Dict[str, Any]:
    return {
        "query": {
            "status": {"option": "online"},
            "type": base_type,
            "stats": [{"type": "and", "filters": []}],
        },
        "sort": {"price": "asc"},
    }


def _chunked(values: List[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _extract_item_class(item_info: Dict[str, Any]) -> Optional[str]:
    item_class = item_info.get("itemClass")
    if isinstance(item_class, str) and item_class:
        return item_class

    category = item_info.get("category")
    if isinstance(category, dict) and category:
        return next(iter(category.keys()), None)
    if isinstance(category, str) and category:
        return category
    return None


def _extract_seller_account(listing_info: Dict[str, Any]) -> Optional[str]:
    account = listing_info.get("account") or {}
    name = account.get("name")
    if name:
        return str(name)
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


class DefaultPriceConverter:
    """Convert listing prices to chaos using poe.ninja for PoE1."""

    def __init__(
        self,
        league: str,
        game_id: str,
        logger_override: Optional[logging.Logger] = None,
        poe_ninja: Optional["PoeNinjaAPI"] = None,
    ) -> None:
        self.league = league
        self.game_id = game_id
        self.logger = logger_override or logger
        self.poe_ninja = poe_ninja if poe_ninja is not None else self._build_poe_ninja()

    def __call__(self, amount: float, currency: str) -> Optional[float]:
        if amount is None or currency is None:
            return None

        curr = str(currency).strip().lower()
        if curr in {"chaos", "chaos orb", "c"}:
            return float(amount)

        if self.poe_ninja is None:
            return None

        currency_name = _currency_name(curr)
        if not currency_name:
            return None

        chaos_value, _ = self.poe_ninja.get_currency_price(currency_name)
        if chaos_value <= 0:
            return None

        return float(amount) * float(chaos_value)

    def _build_poe_ninja(self) -> Optional[PoeNinjaAPI]:
        if self.game_id != "poe1":
            return None
        from data_sources.pricing.poe_ninja import PoeNinjaAPI

        return PoeNinjaAPI(league=self.league)


def _currency_name(curr: str) -> Optional[str]:
    mapping = {
        "divine": "Divine Orb",
        "divine orb": "Divine Orb",
        "d": "Divine Orb",
        "exalted": "Exalted Orb",
        "exalted orb": "Exalted Orb",
        "ex": "Exalted Orb",
        "chaos": "Chaos Orb",
        "chaos orb": "Chaos Orb",
        "c": "Chaos Orb",
    }
    return mapping.get(curr)
