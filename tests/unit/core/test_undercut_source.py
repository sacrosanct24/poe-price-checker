import pytest

pytestmark = pytest.mark.unit

from typing import Any, Mapping

from core.derived_sources import UndercutPriceSource
from core.price_service import PriceService
from core.price_multi import RESULT_COLUMNS


class FakePriceService:
    def __init__(self, rows: list[Mapping[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    def check_item(self, item_text: str) -> list[Mapping[str, Any]]:
        self.calls.append(item_text)
        return list(self._rows)


def test_undercut_price_source_scales_values_and_sets_source() -> None:
    base_rows = [
        {
            "item_name": "Hat",
            "variant": "",
            "links": "",
            "chaos_value": 100.0,
            "divine_value": 0.5,
            "listing_count": 10,
            "source": "poe_ninja",
        }
    ]
    fake_service = FakePriceService(base_rows)

    src = UndercutPriceSource(
        name="suggested_undercut",
        base_service=fake_service,  # type: ignore[arg-type]
        undercut_factor=0.9,
    )

    rows = src.check_item("some item")

    assert fake_service.calls == ["some item"]
    assert len(rows) == 1
    row = rows[0]

    # All expected columns present
    for col in RESULT_COLUMNS:
        assert col in row

    assert row["source"] == "suggested_undercut"
    assert pytest.approx(row["chaos_value"], rel=1e-6) == 90.0
    assert pytest.approx(row["divine_value"], rel=1e-6) == 0.45
