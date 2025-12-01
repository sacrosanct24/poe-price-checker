from __future__ import annotations

from typing import Any, Iterable, Mapping
import pytest

from core.price_multi import (
    MultiSourcePriceService,
    ExistingServiceAdapter,
    RESULT_COLUMNS,
    PriceSource,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------
# Fake underlying single-source PriceService
# --------------------------------------------------------

class FakeUnderlyingService:
    """
    Simulates the original PriceService before you added multi-source support.
    check_item returns the rows we inject.
    """
    def __init__(self, rows: list[Mapping[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> list[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


# --------------------------------------------------------
# Fake source (implements PriceSource)
# --------------------------------------------------------

class FakeSource(PriceSource):
    """
    A simple PriceSource that returns predefined rows.
    """
    def __init__(self, name: str, rows: list[Mapping[str, Any]]) -> None:
        self.name = name
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> Iterable[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


# --------------------------------------------------------
# Error-producing fake source
# --------------------------------------------------------

class ErrorSource(PriceSource):
    """
    A PriceSource that always raises an error.
    """

    def __init__(self, name: str = "error_source") -> None:
        self.name = name
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> Iterable[Mapping[str, Any]]:
        self.calls.append(item_text)
        raise RuntimeError("boom")


# --------------------------------------------------------
# Tests
# --------------------------------------------------------

def test_existing_service_adapter_normalizes_rows_and_sets_source() -> None:
    base_rows = [
        {
            "item_name": "Hat",
            "chaos_value": 12.3,
            # Missing fields should be default-filled
        }
    ]
    underlying = FakeUnderlyingService(base_rows)
    adapter = ExistingServiceAdapter(name="poe_ninja", service=underlying)

    result = adapter.check_item("some item")
    assert len(result) == 1

    row = result[0]
    assert row["source"] == "poe_ninja"

    # All expected columns exist
    for col in RESULT_COLUMNS:
        assert col in row

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

    svc = MultiSourcePriceService(sources=[source_a, source_b])
    rows = svc.check_item("rare ring")

    assert len(rows) == 2
    srcs = {row["source"] for row in rows}
    assert srcs == {"source_a", "source_b"}

    for row in rows:
        for col in RESULT_COLUMNS:
            assert col in row

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

    svc = MultiSourcePriceService(sources=[good_source, bad_source])
    rows = svc.check_item("some amulet")

    # Should return result from good source only
    assert len(rows) == 1
    assert rows[0]["source"] == "good_source"

    assert good_source.calls == ["some amulet"]
    assert bad_source.calls == ["some amulet"]


def test_multi_source_aggregator_returns_empty_for_blank_input_and_does_not_call_sources() -> None:
    source = FakeSource(name="only_source", rows=[])
    svc = MultiSourcePriceService(sources=[source])

    rows = svc.check_item("   ")
    assert rows == []
    assert source.calls == []
