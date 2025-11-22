from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Iterable, Protocol, runtime_checkable


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
    """
    A single price data source (PoE Ninja, Trade API, poe.watch, etc.).

    Implementations should:
      - Set a human-friendly `name` attribute.
      - Return an iterable of rows mapping RESULT_COLUMNS to values.
    """

    name: str

    def check_item(self, item_text: str) -> Iterable[dict[str, Any]]:
        ...


@dataclass
class ExistingServiceAdapter(PriceSource):
    """
    Adapter that wraps your existing single-source service and makes it
    behave like a PriceSource.

    Example:
        adapter = ExistingServiceAdapter(
            name="poe_ninja",
            service=old_price_service_instance,
        )
    """

    name: str
    service: Any

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        raw_results = self.service.check_item(item_text)  # type: ignore[call-arg]
        rows: list[dict[str, Any]] = []

        # Your existing service may already return dicts with matching keys.
        # Normalize and inject the 'source' field.
        for row in raw_results:
            if isinstance(row, dict):
                data = dict(row)
            else:
                # Fallback: pull attributes
                data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}

            data.setdefault("item_name", "")
            data.setdefault("variant", "")
            data.setdefault("links", "")
            data.setdefault("chaos_value", "")
            data.setdefault("divine_value", "")
            data.setdefault("listing_count", "")
            # Override or set source name explicitly
            data["source"] = self.name

            rows.append(data)

        return rows


class MultiSourcePriceService:
    """
    Aggregates multiple PriceSource implementations.

    - Runs sources in parallel using ThreadPoolExecutor.
    - Flattens all results into one list.
    - Keeps the 'source' column populated with the source name.
    """

    def __init__(
        self,
        sources: list[PriceSource],
        max_workers: int | None = None,
    ) -> None:
        if not sources:
            raise ValueError("MultiSourcePriceService requires at least one PriceSource.")
        self._sources = list(sources)
        self._max_workers = max_workers or min(8, len(self._sources))

    @property
    def sources(self) -> list[PriceSource]:
        return list(self._sources)

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """
        Run a price check against all configured sources in parallel.

        Returns a flat list of rows. Each row is a dict with RESULT_COLUMNS.
        """
        if not item_text.strip():
            return []

        results: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_source = {
                executor.submit(source.check_item, item_text): source
                for source in self._sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    rows = future.result()
                except Exception as exc:
                    # In a real app you'd log this; for now we just skip on error.
                    # logger.warning("Source %s failed: %s", source.name, exc)
                    continue

                for row in rows:
                    # Ensure 'source' is filled; individual sources can override.
                    if isinstance(row, dict):
                        data = dict(row)
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
