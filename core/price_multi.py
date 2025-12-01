import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable, Mapping, Union

try:
    # Optional import for stronger typing; code works without it
    from core.price_row import PriceRow
except Exception:  # pragma: no cover - typing convenience only
    PriceRow = Any  # type: ignore

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
        raw_results = self.service.check_item(item_text)  # type: ignore[call-arg]
        rows: list[dict[str, Any]] = []

        for row in raw_results:
            if isinstance(row, dict):
                data = dict(row)
            elif type(row).__name__ == "PriceRow":  # avoid hard dependency at runtime
                # Support dataclass-based rows
                try:
                    data = dict(vars(row))
                except Exception:
                    data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}
            else:
                data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}

            data.setdefault("item_name", "")
            data.setdefault("variant", "")
            data.setdefault("links", "")
            data.setdefault("chaos_value", "")
            data.setdefault("divine_value", "")
            data.setdefault("listing_count", "")
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
    ) -> None:
        if not sources:
            raise ValueError("MultiSourcePriceService requires at least one PriceSource.")
        self._sources: list[PriceSource] = list(sources)
        self._max_workers = max_workers or min(8, len(self._sources))

        # Track enabled source names; default = all enabled
        self._enabled_names: set[str] = {s.name for s in self._sources}

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
                    logger.debug(
                        "price_source_done",
                        extra={
                            "source": source.name,
                            "duration_ms": round(dur_ms, 2),
                            "ok": ok,
                            "row_count": len(rows) if isinstance(rows, list) else 0,
                        },
                    )
                    # do not continue here; allow successful rows to be processed below

                for row in rows:
                    if isinstance(row, dict):
                        data = dict(row)
                    elif type(row).__name__ == "PriceRow":  # support typed rows
                        try:
                            data = dict(vars(row))
                        except Exception:
                            data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}
                    else:
                        data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}

                    data.setdefault("source", source.name)
                    data.setdefault("item_name", "")
                    data.setdefault("variant", "")
                    data.setdefault("links", "")
                    data.setdefault("chaos_value", "")
                    data.setdefault("divine_value", "")
                    data.setdefault("listing_count", "")

                    results.append(data)

        return results
