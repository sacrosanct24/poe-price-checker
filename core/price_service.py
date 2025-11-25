# core/price_service.py
from __future__ import annotations

import logging
import re
from typing import Any, Optional
from datetime import datetime, timezone
from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion
from core.rare_item_evaluator import RareItemEvaluator
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from data_sources.pricing.poe_watch import PoeWatchAPI
from data_sources.pricing.trade_api import TradeApiSource

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
        poe_watch: PoeWatchAPI | None = None,
        trade_source: TradeApiSource | None = None,
        rare_evaluator: RareItemEvaluator | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.parser = parser
        self.db = db
        self.poe_ninja = poe_ninja
        self.poe_watch = poe_watch
        self.trade_source = trade_source
        self.rare_evaluator = rare_evaluator
        self.logger = logger or LOG

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """
        Main entrypoint for the GUI.

        - Parse the raw item text.
        - Use poe.ninja (or fallback) to get a chaos value and listing count.
        - Optionally call Trade API for per-listing quotes.
        - Persist a price_check + price_quotes snapshot.
        - Compute a robust display price from recent stats.
        - Convert to the RESULT_COLUMNS shape used by the GUI.
        """
        item_text = (item_text or "").strip()
        if not item_text:
            return []

        # 1) Parse item text → ParsedItem
        parsed = self.parser.parse(item_text)

        # 2) Look up aggregate price from poe.ninja + poe.watch (multi-source)
        chaos_value: float
        listing_count: int
        source_label: str
        confidence: str = "unknown"

        if self.poe_ninja is None and self.poe_watch is None:
            # PoE2 or pricing disabled
            self.logger.info("No pricing sources available; returning zero-price result.")
            chaos_value = 0.0
            listing_count = 0
            source_label = "no pricing sources"
        else:
            chaos_value, listing_count, source_label, confidence = self._lookup_price_multi_source(
                parsed
            )

        # 2b) For rare items: evaluate and attach evaluation for trade API filtering
        rarity = self._get_rarity(parsed)
        rare_evaluation = None

        if rarity and rarity.upper() == "RARE" and self.rare_evaluator is not None:
            try:
                # Always evaluate rares to get affix data for trade API
                rare_evaluation = self.rare_evaluator.evaluate(parsed)

                # Attach evaluation to parsed item for trade API to use
                parsed._rare_evaluation = rare_evaluation

                # Only use evaluator price if market price is missing or very low
                if chaos_value == 0.0 or chaos_value < 5.0:
                    # Convert estimated_value to chaos
                    evaluator_chaos = self._parse_estimated_value_to_chaos(
                        rare_evaluation.estimated_value
                    )

                    if evaluator_chaos is not None and evaluator_chaos > chaos_value:
                        # Use evaluator price as initial estimate
                        old_chaos = chaos_value
                        chaos_value = evaluator_chaos
                        listing_count = 0

                        # Build source label with tier and score
                        source_label = (
                            f"rare_evaluator ({rare_evaluation.tier}, "
                            f"score: {rare_evaluation.total_score}/100)"
                        )

                        # Map tier to confidence
                        tier_confidence = {
                            "excellent": "high",
                            "good": "medium",
                            "average": "low",
                            "vendor": "low"
                        }
                        confidence = tier_confidence.get(rare_evaluation.tier, "low")

                        self.logger.info(
                            "Rare item '%s' priced by evaluator: %.1fc (was: %.1fc) "
                            "[tier=%s, score=%d, will check trade API]",
                            self._get_item_display_name(parsed),
                            chaos_value,
                            old_chaos,
                            rare_evaluation.tier,
                            rare_evaluation.total_score
                        )
                    elif evaluator_chaos is not None:
                        self.logger.info(
                            "Rare item '%s' evaluator price (%.1fc) not used "
                            "(market price %.1fc is higher, will check trade API)",
                            self._get_item_display_name(parsed),
                            evaluator_chaos,
                            chaos_value
                        )
                else:
                    self.logger.info(
                        "Rare item '%s' has market price %.1fc, "
                        "but will use trade API with affix filters for validation",
                        self._get_item_display_name(parsed),
                        chaos_value
                    )

            except Exception as exc:
                self.logger.warning(
                    "Failed to evaluate rare item: %s", exc, exc_info=True
                )

        # 3) Optionally gather trade quotes
        trade_quotes: list[dict[str, Any]] = []

        if self.trade_source is not None:
            try:
                trade_quotes = self.trade_source.check_item(parsed, max_results=20)
                self.logger.info(
                    "PriceService.check_item: received %d trade quote(s) from TradeApiSource for %s",
                    len(trade_quotes),
                    getattr(parsed, "display_name", getattr(parsed, "name", "<unknown>")),
                )
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning(
                    "PriceService.check_item: TradeApiSource.check_item failed: %s", exc
                )
                trade_quotes = []
        else:
            self.logger.info("PriceService.check_item: no trade_source configured; skipping")
            trade_quotes = []

        # 4) Persist this check + quotes (poe.ninja synthetic + trade)
        try:
            self._save_trade_quotes_for_check(parsed, trade_quotes, chaos_value)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to save trade quotes: %s", exc)

        # 5) Compute robust display price from latest stats (if any)
        stats: Optional[dict[str, Any]] = None
        try:
            stats = self._get_latest_price_stats_for_item(parsed)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.exception("Failed to compute price stats: %s", exc)
            stats = None

        if stats is not None:
            price_info = self.compute_display_price(stats)
            rounded = price_info.get("rounded_price")
            if rounded is not None:
                chaos_value = float(rounded)
                # Use stats confidence, but fallback to multi-source confidence
                stats_conf = price_info.get("confidence", "unknown")
                # Combine both confidence indicators
                if stats_conf != "unknown" and confidence != "unknown":
                    # Use the lower confidence level
                    conf_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
                    final_conf = min(stats_conf, confidence, key=lambda c: conf_order.get(c, 0))
                    source_label = f"{source_label} ({final_conf})"
                elif stats_conf != "unknown":
                    source_label = f"{source_label} ({stats_conf})"
                elif confidence != "unknown":
                    source_label = f"{source_label} ({confidence})"

        # 6) Divine conversion (if we can)
        divine_value = self._convert_chaos_to_divines(chaos_value)

        # 7) Build a single-row result list.
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
    # Rare item pricing helpers
    # ------------------------------------------------------------------ #

    def _parse_estimated_value_to_chaos(self, estimated_value: str) -> Optional[float]:
        """
        Convert rare item evaluator's estimated_value string to numeric chaos.

        Examples:
            "50-200c" → 125.0 (midpoint)
            "1div+" → chaos equivalent of 1 divine
            "200c-5div" → midpoint between 200c and 5div in chaos
            "<5c" → 2.5
            "5-10c" → 7.5

        Args:
            estimated_value: String like "50-200c", "1div+", etc.

        Returns:
            Chaos value as float, or None if unparseable
        """
        if not estimated_value:
            return None

        estimated_value = estimated_value.strip().lower()

        # Pattern: "<5c" → use half the value
        match = re.match(r'<(\d+(?:\.\d+)?)c', estimated_value)
        if match:
            return float(match.group(1)) / 2.0

        # Pattern: "50c+" → use the value as-is
        match = re.match(r'(\d+(?:\.\d+)?)c\+', estimated_value)
        if match:
            return float(match.group(1))

        # Pattern: "1div+" → convert divine to chaos
        match = re.match(r'(\d+(?:\.\d+)?)div\+', estimated_value)
        if match:
            divines = float(match.group(1))
            divine_rate = self._get_divine_chaos_rate()
            if divine_rate > 0:
                return divines * divine_rate
            return None

        # Pattern: "50-200c" or "5-10c" → use midpoint
        match = re.match(r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)c', estimated_value)
        if match:
            low = float(match.group(1))
            high = float(match.group(2))
            return (low + high) / 2.0

        # Pattern: "200c-5div" → convert both to chaos and take midpoint
        match = re.match(r'(\d+(?:\.\d+)?)c-(\d+(?:\.\d+)?)div', estimated_value)
        if match:
            chaos_low = float(match.group(1))
            divines_high = float(match.group(2))
            divine_rate = self._get_divine_chaos_rate()
            if divine_rate > 0:
                chaos_high = divines_high * divine_rate
                return (chaos_low + chaos_high) / 2.0
            return chaos_low  # Fallback to chaos value

        # Pattern: "1div" → exact divine value
        match = re.match(r'(\d+(?:\.\d+)?)div', estimated_value)
        if match:
            divines = float(match.group(1))
            divine_rate = self._get_divine_chaos_rate()
            if divine_rate > 0:
                return divines * divine_rate
            return None

        # Unknown format
        self.logger.warning(f"Could not parse estimated_value: '{estimated_value}'")
        return None

    def _get_divine_chaos_rate(self) -> float:
        """
        Get current divine to chaos conversion rate.

        Returns:
            Chaos per divine, or 0.0 if unavailable
        """
        if self.poe_ninja is not None:
            try:
                rate = self.poe_ninja.ensure_divine_rate()
                if rate > 10.0:  # Sanity check
                    return rate
            except (AttributeError, Exception):
                pass

        # Fallback to config
        try:
            current_game = getattr(self.config, "current_game", None)
            games = getattr(self.config, "games", {}) or {}
            if isinstance(games, dict):
                if isinstance(current_game, GameVersion):
                    game_key = current_game.value
                else:
                    game_key = str(current_game or "poe1")
                if game_key in games:
                    game_cfg = games.get(game_key) or {}
                    rate = float(game_cfg.get("divine_chaos_rate", 0))
                    if rate > 10.0:
                        return rate
        except (TypeError, ValueError, AttributeError):
            pass

        return 0.0

    # ------------------------------------------------------------------ #
    # Price check / quote persistence
    # ------------------------------------------------------------------ #

    def _save_trade_quotes_for_check(
            self,
            parsed_item: Any,
            trade_quotes: list[dict[str, Any]],
            poe_ninja_chaos: float | None,
    ) -> None:
        """
        Persist a price_check + associated price_quotes snapshot.

        - Always writes one synthetic poe.ninja quote when poe_ninja_chaos > 0.
        - Additionally writes any trade quotes we can convert to chaos.
        """
        game_version, league = self._resolve_game_and_league()

        item_name = getattr(parsed_item, "display_name", None) or getattr(
            parsed_item, "name", "<unknown>"
        )
        base_type = getattr(parsed_item, "base_type", None)

        # 1) Insert price_check row using Database.create_price_check
        price_check_id = self.db.create_price_check(
            game_version=game_version,
            league=league,
            item_name=item_name,
            item_base_type=base_type,
            source="trade+poe.ninja",
            query_hash=None,
        )

        self.logger.info(
            "PriceService._save_trade_quotes_for_check: price_check_id=%s, "
            "item_name=%s, league=%s, raw_trade_quotes=%d",
            price_check_id,
            item_name,
            league,
            len(trade_quotes),
        )

        rows_to_save: list[dict[str, Any]] = []
        now_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # 2) Synthetic poe.ninja quote (if available)
        if poe_ninja_chaos and poe_ninja_chaos > 0:
            rows_to_save.append(
                {
                    "price_check_id": price_check_id,
                    "source": "poe_ninja",
                    "price_chaos": float(poe_ninja_chaos),
                    "original_currency": "chaos",
                    "stack_size": 1,
                    "listing_id": None,
                    "seller_account": None,
                    "listed_at": None,
                    "fetched_at": now_ts,
                }
            )

        # 3) Convert trade quotes into chaos
        convertible = 0
        skipped = 0

        for q in trade_quotes:
            curr = (q.get("original_currency") or "").lower()
            amount = q.get("amount")

            if amount is None:
                skipped += 1
                self.logger.debug("Skipping trade quote with missing amount: %r", q)
                continue

            chaos_price: float | None = None

            if curr in {"chaos", "c"}:
                chaos_price = float(amount)
            elif curr in {"divine", "divine orb", "d"}:
                if not getattr(self.poe_ninja, "divine_chaos_rate", None):
                    self.logger.debug(
                        "Skipping divine-quoted trade listing (no divine rate): %r", q
                    )
                    skipped += 1
                    continue
                chaos_price = float(amount) * float(self.poe_ninja.divine_chaos_rate)
            else:
                # Extend later with exalts etc.
                self.logger.debug(
                    "Skipping trade listing with unsupported currency '%s': %r",
                    curr,
                    q,
                )
                skipped += 1
                continue

            if chaos_price is None:
                skipped += 1
                continue

            convertible += 1

            rows_to_save.append(
                {
                    "price_check_id": price_check_id,
                    "source": "trade",
                    "price_chaos": chaos_price,
                    "original_currency": curr,
                    "stack_size": q.get("stack_size"),
                    "listing_id": q.get("listing_id"),
                    "seller_account": q.get("seller_account"),
                    "listed_at": q.get("listed_at"),
                    "fetched_at": now_ts,
                }
            )

        self.logger.info(
            "PriceService._save_trade_quotes_for_check: synthetic=%d, "
            "trade_convertible=%d, trade_skipped=%d",
            1 if poe_ninja_chaos and poe_ninja_chaos > 0 else 0,
            convertible,
            skipped,
        )

        # 4) Actually persist rows
        if rows_to_save:
            # FIX: pass price_check_id explicitly as required by Database.add_price_quotes_batch
            self.db.add_price_quotes_batch(price_check_id, rows_to_save)

        self.logger.info(
            "Saved %d price_quotes for %s (price_check_id=%s, league=%s)",
            len(rows_to_save),
            item_name,
            price_check_id,
            league,
        )

    def _get_latest_price_stats_for_item(self, parsed: Any) -> Optional[dict[str, Any]]:
        """
        Pull robust stats for the most recent price_check for this item
        in the current game/league, using Database.get_latest_price_stats_for_item.
        """
        game_version, league = self._resolve_game_and_league()
        if game_version is None or not league:
            return None

        item_name = self._get_item_display_name(parsed)
        stats = self.db.get_latest_price_stats_for_item(
            game_version=game_version,
            league=league,
            item_name=item_name,
            days=2,
        )
        return stats

    def _resolve_game_and_league(
        self,
    ) -> tuple[Optional[GameVersion], Optional[str]]:
        """
        Decide (game_version, league) using live sources first, config second.

        Priority:
          - game_version from config.current_game -> GameVersion
          - league from poe_ninja.league if available
          - else league from trade_source.league
          - else config.games[current_game]["league"]
          - else config.league (last resort)
        """
        # --- Game version ---
        current_game_raw = getattr(self.config, "current_game", "poe1")
        if isinstance(current_game_raw, GameVersion):
            current_game_key = current_game_raw.value
            game_version = current_game_raw
        else:
            current_game_key = str(current_game_raw or "poe1")
            if current_game_key.lower() == "poe2":
                game_version = GameVersion.POE2
            else:
                game_version = GameVersion.POE1

        # --- League ---
        league: Optional[str] = None

        if self.poe_ninja is not None:
            league = getattr(self.poe_ninja, "league", None) or league

        if league is None and self.trade_source is not None:
            league = getattr(self.trade_source, "league", None) or league

        if league is None:
            games_cfg = getattr(self.config, "games", {}) or {}
            if isinstance(games_cfg, dict) and current_game_key in games_cfg:
                game_cfg = games_cfg.get(current_game_key) or {}
                league = game_cfg.get("league")

        if league is None:
            league = getattr(self.config, "league", None)

        return game_version, league

    # ------------------------------------------------------------------ #
    # Display price policy (robust aggregation helper)
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_display_price(stats: dict[str, Any]) -> dict[str, Any]:
        """
        Decide a robust display price and confidence level from price stats.

        Expected keys in stats (from Database.get_price_stats_for_check):
            - count
            - min
            - max
            - mean
            - median
            - p25
            - p75
            - trimmed_mean
            - stddev

        Returns:
            {
                "display_price": Optional[float],  # raw center used
                "rounded_price": Optional[float],  # nicely rounded for UI
                "confidence": str,                 # "none" | "low" | "medium" | "high"
                "reason": str,                     # human-readable explanation
            }
        """
        count = stats.get("count") or 0
        if count == 0:
            return {
                "display_price": None,
                "rounded_price": None,
                "confidence": "none",
                "reason": "No listings found",
            }

        mean = stats.get("mean")
        median = stats.get("median")
        p25 = stats.get("p25")
        p75 = stats.get("p75")
        trimmed_mean = stats.get("trimmed_mean")
        stddev = stats.get("stddev")

        # --- Step 1: choose base center (trimmed_mean > median > mean) ---
        if count >= 12 and trimmed_mean is not None:
            base_price = float(trimmed_mean)
            center_used = "trimmed_mean"
        elif count >= 4 and median is not None:
            base_price = float(median)
            center_used = "median"
        elif mean is not None:
            base_price = float(mean)
            center_used = "mean"
        else:
            # Fallback if somehow everything is None
            return {
                "display_price": None,
                "rounded_price": None,
                "confidence": "low",
                "reason": "No valid price values",
            }

        # --- Step 2: relative spread metrics (IQR / median, stddev / mean) ---

        def safe_ratio(num: Optional[float], den: Optional[float]) -> float:
            if num is None or den is None:
                return 0.0
            try:
                dn = float(den)
            except (TypeError, ValueError):
                return 0.0
            if dn == 0:
                return 0.0
            return float(num) / dn

        iqr: Optional[float] = None
        if p25 is not None and p75 is not None:
            iqr = float(p75) - float(p25)

        iqr_ratio = safe_ratio(iqr, median)
        cv = safe_ratio(stddev, mean)  # coefficient of variation

        # --- Step 3: confidence heuristics ---
        # Default
        confidence = "low"
        reason = f"{count} listings"

        if count >= 20 and iqr_ratio <= 0.35 and cv <= 0.35:
            confidence = "high"
            reason = f"High sample size ({count}) with tight spread"
        elif count >= 8 and iqr_ratio <= 0.6 and cv <= 0.6:
            confidence = "medium"
            reason = f"Moderate sample size ({count}) with acceptable spread"
        else:
            confidence = "low"
            # If very noisy, note that in the reason
            if iqr_ratio > 0.8 or cv > 0.8:
                reason = f"Volatile prices ({count} listings, high spread)"
            else:
                reason = f"Limited or noisy data ({count} listings)"

        # --- Step 4: rounding policy for display ---

        raw = base_price
        if raw >= 100:
            # nearest 5c
            rounded = round(raw / 5.0) * 5.0
        elif raw >= 10:
            # nearest 1c
            rounded = round(raw)
        elif raw >= 1:
            # 1 decimal
            rounded = round(raw, 1)
        else:
            # 2 decimals for very cheap items
            rounded = round(raw, 2)

        return {
            "display_price": raw,
            "rounded_price": rounded,
            "confidence": confidence,
            "reason": f"{reason} (center={center_used}, iqr_ratio={iqr_ratio:.2f}, cv={cv:.2f})",
        }

    # ------------------------------------------------------------------ #
    # Multi-source pricing helpers
    # ------------------------------------------------------------------ #

    def _lookup_price_multi_source(
        self, parsed: Any
    ) -> tuple[float, int, str, str]:
        """
        Look up price using multiple sources (poe.ninja + poe.watch).

        Strategy:
        1. Get price from poe.ninja (primary, faster updates)
        2. Get price from poe.watch (secondary, validation)
        3. Compare and validate:
           - If both agree (within 20%), use ninja price with high confidence
           - If diverge significantly, average them with medium confidence
           - If one is low confidence, prefer the other
           - If only one source available, use it with appropriate confidence

        Returns:
            (chaos_value, listing_count, source_label, confidence)
        """
        item_name = self._get_item_display_name(parsed)
        base_type = self._get_base_type(parsed)
        rarity = (self._get_rarity(parsed) or "").upper()

        # DEBUG LOGGING
        self.logger.info(f"[MULTI-SOURCE] Looking up price for '{item_name}' (rarity: {rarity}, base: {base_type})")
        self.logger.info(f"[MULTI-SOURCE] Available sources: poe.ninja={self.poe_ninja is not None}, poe.watch={self.poe_watch is not None}")

        ninja_price: Optional[float] = None
        ninja_count: int = 0
        watch_price: Optional[float] = None
        watch_confidence: str = "unknown"
        watch_daily: int = 0

        # Get poe.ninja price
        if self.poe_ninja:
            self.logger.info("[MULTI-SOURCE] Querying poe.ninja...")
            try:
                ninja_price, ninja_count, _ = self._lookup_price_with_poe_ninja(parsed)
                if ninja_price == 0.0:
                    ninja_price = None
                if ninja_price is not None:
                    self.logger.info(f"[MULTI-SOURCE]   poe.ninja result: {ninja_price:.1f}c (count: {ninja_count})")
                else:
                    self.logger.info("[MULTI-SOURCE]   poe.ninja result: No data found")
            except Exception as e:
                self.logger.warning(f"[MULTI-SOURCE]   poe.ninja lookup failed: {e}")
                ninja_price = None
        else:
            self.logger.info("[MULTI-SOURCE] Skipping poe.ninja (not initialized)")

        # Get poe.watch price
        if self.poe_watch:
            self.logger.info("[MULTI-SOURCE] Querying poe.watch...")
            try:
                watch_data = self.poe_watch.find_item_price(
                    item_name=item_name,
                    base_type=base_type,
                    rarity=rarity,
                    gem_level=self._get_gem_level(parsed),
                    gem_quality=self._get_gem_quality(parsed),
                    corrupted=self._get_corrupted_flag(parsed),
                    links=self._parse_links(parsed),
                )

                if watch_data:
                    watch_price = float(watch_data.get('mean', 0) or 0)
                    if watch_price == 0.0:
                        watch_price = None
                    watch_daily = watch_data.get('daily', 0)
                    watch_low_conf = watch_data.get('lowConfidence', False)

                    # Assess poe.watch confidence
                    if watch_low_conf:
                        watch_confidence = "low"
                    elif watch_daily > 10:
                        watch_confidence = "high"
                    else:
                        watch_confidence = "medium"

                    if watch_price is not None:
                        self.logger.info(f"[MULTI-SOURCE]   poe.watch result: {watch_price:.1f}c (daily: {watch_daily}, confidence: {watch_confidence})")
                    else:
                        self.logger.info("[MULTI-SOURCE]   poe.watch result: No price data (mean=0)")
                else:
                    self.logger.info("[MULTI-SOURCE]   poe.watch result: No matching item found")

            except Exception as e:
                self.logger.warning(f"[MULTI-SOURCE]   poe.watch lookup failed: {e}", exc_info=True)
                watch_price = None
        else:
            self.logger.info("[MULTI-SOURCE] Skipping poe.watch (not initialized)")

        # Decision logic
        self.logger.info("[MULTI-SOURCE] Making pricing decision...")

        if ninja_price is not None and watch_price is not None:
            # Both sources available - compare and validate
            diff_pct = abs(ninja_price - watch_price) / max(ninja_price, watch_price)
            self.logger.info(f"[MULTI-SOURCE] Both sources available - price difference: {diff_pct*100:.1f}%")

            if diff_pct <= 0.20:  # Within 20% - good agreement
                # Use poe.ninja (faster updates) but note validation
                self.logger.info(f"[MULTI-SOURCE] ✓ Decision: Using poe.ninja {ninja_price:.1f}c (validated by poe.watch, high confidence)")
                return (
                    ninja_price,
                    ninja_count,
                    "poe.ninja (validated by poe.watch)",
                    "high"
                )
            elif watch_confidence == "low":
                # poe.watch flagged as low confidence, trust ninja
                self.logger.info(f"[MULTI-SOURCE] ✓ Decision: Using poe.ninja {ninja_price:.1f}c (poe.watch low confidence, medium confidence)")
                return (
                    ninja_price,
                    ninja_count,
                    "poe.ninja (poe.watch: low confidence)",
                    "medium"
                )
            else:
                # Significant divergence - average them
                avg_price = (ninja_price + watch_price) / 2
                self.logger.info(
                    f"[MULTI-SOURCE] ⚠ Price divergence for {item_name}: "
                    f"ninja={ninja_price:.1f}c, watch={watch_price:.1f}c, "
                    f"using average={avg_price:.1f}c (medium confidence)"
                )
                return (
                    avg_price,
                    max(ninja_count, watch_daily),
                    f"averaged (ninja: {ninja_price:.1f}c, watch: {watch_price:.1f}c)",
                    "medium"
                )

        elif ninja_price is not None:
            # Only poe.ninja available
            self.logger.info(f"[MULTI-SOURCE] ✓ Decision: Using poe.ninja only {ninja_price:.1f}c (medium confidence)")
            return (
                ninja_price,
                ninja_count,
                "poe.ninja only",
                "medium"
            )

        elif watch_price is not None:
            # Only poe.watch available
            self.logger.info(f"[MULTI-SOURCE] ✓ Decision: Using poe.watch only {watch_price:.1f}c ({watch_confidence} confidence)")
            return (
                watch_price,
                watch_daily,
                "poe.watch only",
                watch_confidence
            )

        else:
            # No prices found
            self.logger.info("[MULTI-SOURCE] ✗ Decision: No prices found from any source")
            return (0.0, 0, "not found", "none")

    def _parse_links(self, parsed: Any) -> Optional[int]:
        """Extract link count as integer."""
        links_str = self._get_item_links(parsed)
        try:
            return int(links_str)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # poe.ninja pricing helpers
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
            self.logger.info(
                "poe.ninja: no price found for '%s' (rarity=%s)", item_name, rarity
            )
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
        - explicit rate on Config (config.divine_rate OR per-game divine_chaos_rate)
        - poe.ninja's divine_chaos_rate, via ensure_divine_rate()

        All rates are interpreted as "chaos per 1 divine".
        If no sane rate is available, returns 0.0 so the UI can hide the
        divine price.
        """

        def _normalize_rate(raw: Any) -> float:
            """Return a usable chaos-per-divine rate or 0.0 if invalid / tiny."""
            try:
                r = float(raw)
            except (TypeError, ValueError):
                return 0.0
            # Realistically, 1 divine should cost more than single-digit chaos.
            return r if r > 10.0 else 0.0

        # 1) Top-level config override (if you ever add one)
        rate = _normalize_rate(getattr(self.config, "divine_rate", None))
        if rate > 0:
            return chaos_value / rate

        # 2) Per-game config: games[current_game]["divine_chaos_rate"]
        try:
            current_game = getattr(self.config, "current_game", None)
            games = getattr(self.config, "games", {}) or {}
            if isinstance(games, dict):
                if isinstance(current_game, GameVersion):
                    game_key = current_game.value
                else:
                    game_key = str(current_game or "poe1")
                if game_key in games:
                    game_cfg = games.get(game_key) or {}
                    rate = _normalize_rate(game_cfg.get("divine_chaos_rate"))
                    if rate > 0:
                        return chaos_value / rate
        except Exception:
            # Config structure weird? Just skip to poe.ninja fallback.
            pass

        # 3) poe.ninja divine/chaos rate
        if self.poe_ninja is not None:
            try:
                # This will fetch and cache the rate on first use
                raw_rate = self.poe_ninja.ensure_divine_rate()
            except AttributeError:
                # Older PoeNinjaAPI without ensure_divine_rate
                raw_rate = getattr(self.poe_ninja, "divine_chaos_rate", 0.0)

            rate = _normalize_rate(raw_rate)
            if rate > 0:
                return chaos_value / rate

        # 4) Fallback: unknown → hide divine price
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

    # ------------------------------------------------------------------ #
    # poe.ninja currency helper
    # ------------------------------------------------------------------ #

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
