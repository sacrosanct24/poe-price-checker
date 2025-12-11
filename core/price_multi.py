import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable, Mapping, Union, Callable

from core.price_arbitration import arbitrate_rows
from core.price_row import PriceRow, validate_and_normalize_row

logger = logging.getLogger(__name__)

RESULT_COLUMNS: tuple[str, ...] = (
    "item_name",
    "variant",
    "links",
    "chaos_value",
    "divine_value",
    "listing_count",
    "source",
)


@runtime_checkable
class PriceSource(Protocol):
    name: str
    def check_item(self, item_text: str) -> Iterable[Union[dict[str, Any], PriceRow]]: ...


@dataclass
class ExistingServiceAdapter(PriceSource):
    name: str
    service: Any

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        raw_results = self.service.check_item(item_text)
        rows: list[dict[str, Any]] = []

        for row in raw_results:
            data = validate_and_normalize_row(row)
            # Override/ensure source label corresponds to this adapter
            data["source"] = self.name

            rows.append(data)

        return rows


class MultiSourcePriceService:
    """
    Aggregates multiple PriceSource implementations.

    - Runs sources in parallel using ThreadPoolExecutor.
    - Flattens all results into one list.
    - Allows enabling/disabling sources by name (for GUI toggling).
    """

    def __init__(
        self,
        sources: list[PriceSource],
        max_workers: int | None = None,
        on_change_enabled_state: Callable[[dict[str, bool]], None] | None = None,
        base_log_context: Mapping[str, Any] | None = None,
        use_arbitration: bool = False,
    ) -> None:
        if not sources:
            raise ValueError("MultiSourcePriceService requires at least one PriceSource.")
        self._sources: list[PriceSource] = list(sources)
        self._max_workers = max_workers or min(8, len(self._sources))

        # Track enabled source names; default = all enabled
        self._enabled_names: set[str] = {s.name for s in self._sources}
        # Optional persistence callback invoked when enabled state changes
        self._on_change_enabled_state = on_change_enabled_state
        # Feature flag for cross-source arbitration
        self._use_arbitration: bool = bool(use_arbitration)
        # Structured logging base context (e.g., game, league)
        self._base_log_context: dict[str, Any] = dict(base_log_context or {})

    @property
    def sources(self) -> list[PriceSource]:
        """Return all configured sources (read-only view)."""
        return list(self._sources)

    # ----- New: GUI-facing state helpers ---------------------------------

    def get_enabled_state(self) -> dict[str, bool]:
        """
        Return a mapping of source_name -> enabled_flag.
        Used by the GUI to populate checkboxes.
        """
        return {s.name: (s.name in self._enabled_names) for s in self._sources}

    def set_enabled_state(self, enabled: Mapping[str, bool]) -> None:
        """
        Update which sources are enabled based on a mapping
        of source_name -> enabled_flag.
        """
        new_enabled: set[str] = set()
        for s in self._sources:
            if enabled.get(s.name, True):
                new_enabled.add(s.name)
        # Avoid ending up with an empty set silently; fall back to all enabled
        self._enabled_names = new_enabled or {s.name for s in self._sources}
        # Persist via callback if provided
        if self._on_change_enabled_state is not None:
            try:
                self._on_change_enabled_state(self.get_enabled_state())
            except Exception:  # defensive: do not let persistence errors bubble
                logger.exception("Failed to persist enabled sources state")

    # ---------------------------------------------------------------------

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """
        Run a price check against all *enabled* sources in parallel.

        Returns a flat list of rows. Each row is a dict with RESULT_COLUMNS.
        """
        if not item_text.strip():
            return []

        # Only active sources participate
        active_sources = [s for s in self._sources if s.name in self._enabled_names]
        if not active_sources:
            return []

        results: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_source = {
                executor.submit(source.check_item, item_text): source
                for source in active_sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                start = time.perf_counter()
                try:
                    rows = future.result()
                    ok = True
                except Exception as e:
                    logger.warning(
                        f"Price source '{source.name}' failed: {e}",
                        exc_info=True
                    )
                    ok = False
                    rows = []
                finally:
                    dur_ms = (time.perf_counter() - start) * 1000.0
                    extra_fields = {
                        "source": source.name,
                        "duration_ms": round(dur_ms, 2),
                        "ok": ok,
                        "row_count": len(rows) if isinstance(rows, list) else 0,
                    }
                    extra_fields.update(self._base_log_context)
                    logger.debug(
                        "price_source_done",
                        extra=extra_fields,
                    )
                    # do not continue here; allow successful rows to be processed below

                for row in rows:
                    data = validate_and_normalize_row(row)
                    if not data.get("source"):
                        data["source"] = source.name
                    results.append(data)
        
        # Optionally add an arbitrated display row at the top without
        # changing existing rows, guarded by feature flag
        if self._use_arbitration and arbitrate_rows is not None:
            try:
                priority = [s.name for s in active_sources]
                chosen = arbitrate_rows(results, source_priority=priority)
            except Exception:
                chosen = None
            if chosen:
                display = dict(chosen)
                # Mark row as arbitrated and normalize source label
                display["source"] = display.get("source", "") or "arbitrated"
                display["is_arbitrated"] = True
                results.insert(0, display)
                # Structured log for arbitration decision
                arb_extra = {
                    "chosen_source": display.get("source"),
                    "chosen_chaos": display.get("chaos_value"),
                    "is_arbitrated": True,
                }
                arb_extra.update(self._base_log_context)
                logger.debug("price_arbitration_done", extra=arb_extra)

        return results
