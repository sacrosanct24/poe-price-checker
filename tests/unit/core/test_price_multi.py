# tests/core/test_price_multi.py
from __future__ import annotations

from typing import Any, Iterable, Mapping

import logging

from core.price_multi import (
    MultiSourcePriceService,
    ExistingServiceAdapter,
    RESULT_COLUMNS,
    PriceSource,
)
# tests/unit/core/test_price_multi.py
import pytest
pytestmark = pytest.mark.unit


class FakeUnderlyingService:
    """
    Simple fake for the existing single-source PriceService.

    It just returns whatever rows we configure it with.
    """

    def __init__(self, rows: list[Mapping[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> list[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


class FakeSource:
    """
    Minimal PriceSource implementation for testing MultiSourcePriceService.
    """

    def __init__(self, name: str, rows: list[Mapping[str, Any]]) -> None:
        self.name = name
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> Iterable[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


class ErrorSource:
    """
    PriceSource that always raises, to verify error isolation in the aggregator.
    """

    def __init__(self, name: str = "error_source") -> None:
        self.name = name
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> Iterable[Mapping[str, Any]]:
        self.calls.append(item_text)
        raise RuntimeError("boom")


def test_existing_service_adapter_normalizes_rows_and_sets_source() -> None:
    base_rows = [
        {
            "item_name": "Hat",
            "chaos_value": 12.3,
            # deliberately omit some fields like variant, links, divine_value, listing_count
        }
    ]
    underlying = FakeUnderlyingService(base_rows)
    adapter = ExistingServiceAdapter(name="poe_ninja", service=underlying)

    result = adapter.check_item("some item")

    assert len(result) == 1
    row = result[0]

    # Source should be set to adapter name
    assert row["source"] == "poe_ninja"

    # All expected columns should exist
    for col in RESULT_COLUMNS:
        assert col in row

    # Underlying service should have been called with the original text
    assert underlying.calls == ["some item"]


def test_multi_source_aggregator_combines_rows_from_multiple_sources() -> None:
    source_a = FakeSource(
        name="source_a",
        rows=[
            {
                "item_name": "Ring A",
                "variant": "",
                "links": "",
                "chaos_value": 10,
                "divine_value": 0.05,
                "listing_count": 5,
            }
        ],
    )
    source_b = FakeSource(
        name="source_b",
        rows=[
            {
                "item_name": "Ring B",
                "variant": "",
                "links": "",
                "chaos_value": 20,
                "divine_value": 0.1,
                "listing_count": 10,
            }
        ],
    )

    service = MultiSourcePriceService(sources=[source_a, source_b])

    rows = service.check_item("rare ring")

    # We should get rows from both sources
    assert len(rows) == 2
    sources_seen = {row["source"] for row in rows}
    assert sources_seen == {"source_a", "source_b"}

    # All expected columns should be present
    for row in rows:
        for col in RESULT_COLUMNS:
            assert col in row

    # Both sources should have been called with the same text
    assert source_a.calls == ["rare ring"]
    assert source_b.calls == ["rare ring"]


def test_multi_source_aggregator_skips_errored_sources() -> None:
    good_source = FakeSource(
        name="good_source",
        rows=[
            {
                "item_name": "Amulet",
                "variant": "",
                "links": "",
                "chaos_value": 5,
                "divine_value": 0.02,
                "listing_count": 3,
            }
        ],
    )
    bad_source = ErrorSource(name="bad_source")

    service = MultiSourcePriceService(sources=[good_source, bad_source])

    rows = service.check_item("some amulet")

    # We still get results from the good source
    assert len(rows) == 1
    assert rows[0]["source"] == "good_source"

    # Both sources were called
    assert good_source.calls == ["some amulet"]
    assert bad_source.calls == ["some amulet"]


def test_multi_source_aggregator_returns_empty_for_blank_input_and_does_not_call_sources() -> None:
    source = FakeSource(name="only_source", rows=[])
    service = MultiSourcePriceService(sources=[source])

    rows = service.check_item("   ")  # whitespace

    assert rows == []
    # No calls because input is effectively empty
    assert source.calls == []
