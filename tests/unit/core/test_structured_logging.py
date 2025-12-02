import logging

import pytest

from core.price_multi import MultiSourcePriceService


class DummySource:
    def __init__(self, name: str, rows: list[dict]):
        self.name = name
        self._rows = rows

    def check_item(self, item_text: str):
        out = []
        for r in self._rows:
            d = dict(r)
            d.setdefault("source", self.name)
            out.append(d)
        return out


@pytest.mark.parametrize("use_arbitration", [False, True])
def test_price_source_done_log_includes_context(caplog, use_arbitration):
    s1 = DummySource("A", [{"item_name": "X", "chaos_value": 10.0, "listing_count": 2, "confidence": "low"}])
    s2 = DummySource("B", [{"item_name": "X", "chaos_value": 12.0, "listing_count": 5, "confidence": "medium"}])
    svc = MultiSourcePriceService(
        [s1, s2],
        base_log_context={"game": "poe1", "league": "Standard"},
        use_arbitration=use_arbitration,
    )

    logger_name = "core.price_multi"
    caplog.set_level(logging.DEBUG, logger=logger_name)

    rows = svc.check_item("Some Item")
    assert rows  # ensure run happened

    # Find price_source_done records and assert structured fields present
    records = [r for r in caplog.records if r.name == logger_name and r.msg == "price_source_done"]
    assert len(records) >= 2
    for rec in records:
        # Extras are attributes on record
        assert hasattr(rec, "source")
        assert hasattr(rec, "duration_ms")
        assert hasattr(rec, "ok")
        assert hasattr(rec, "row_count")
        # Structured context
        assert getattr(rec, "game", None) == "poe1"
        assert getattr(rec, "league", None) == "Standard"


def test_price_arbitration_done_log_includes_context(caplog):
    s1 = DummySource("A", [{"item_name": "X", "chaos_value": 10.0, "listing_count": 2, "confidence": "medium"}])
    s2 = DummySource("B", [{"item_name": "X", "chaos_value": 11.0, "listing_count": 10, "confidence": "high"}])
    svc = MultiSourcePriceService(
        [s1, s2],
        base_log_context={"game": "poe1", "league": "TradeLeague"},
        use_arbitration=True,
    )

    logger_name = "core.price_multi"
    caplog.set_level(logging.DEBUG, logger=logger_name)

    rows = svc.check_item("Some Item")
    assert rows and rows[0].get("is_arbitrated") is True

    records = [r for r in caplog.records if r.name == logger_name and r.msg == "price_arbitration_done"]
    assert len(records) == 1
    rec = records[0]
    # Check structured extras
    assert getattr(rec, "is_arbitrated", None) is True
    assert getattr(rec, "chosen_source", None) in {"A", "B", "arbitrated"}
    assert getattr(rec, "chosen_chaos", None) in {10.0, 11.0}
    assert getattr(rec, "game", None) == "poe1"
    assert getattr(rec, "league", None) == "TradeLeague"
