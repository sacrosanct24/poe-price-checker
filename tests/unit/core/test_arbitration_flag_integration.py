from core.price_multi import MultiSourcePriceService


class DummySource:
    def __init__(self, name: str, rows: list[dict]):
        self.name = name
        self._rows = rows

    def check_item(self, item_text: str):
        # Attach source name to rows if missing
        out = []
        for r in self._rows:
            d = dict(r)
            d.setdefault("source", self.name)
            out.append(d)
        return out


def _make_service(use_arbitration: bool) -> MultiSourcePriceService:
    s1 = DummySource("A", [
        {"item_name": "X", "chaos_value": 10.0, "listing_count": 5, "confidence": "medium"}
    ])
    s2 = DummySource("B", [
        {"item_name": "X", "chaos_value": 11.0, "listing_count": 10, "confidence": "high"}
    ])
    return MultiSourcePriceService([s1, s2], on_change_enabled_state=None, use_arbitration=use_arbitration)


def test_no_arbitration_flag_returns_only_source_rows():
    svc = _make_service(use_arbitration=False)
    rows = svc.check_item("Some Item Text")
    # Should contain exactly the concatenated rows from sources (order not guaranteed across threads)
    assert len(rows) == 2
    assert not any(r.get("is_arbitrated") for r in rows)
    sources = {r["source"] for r in rows}
    assert sources == {"A", "B"}


def test_with_arbitration_flag_inserts_arbitrated_row():
    svc = _make_service(use_arbitration=True)
    rows = svc.check_item("Some Item Text")
    # Should insert one arbitrated row at top + original two rows
    assert len(rows) == 3
    top = rows[0]
    assert top.get("is_arbitrated") is True
    # Expect it to choose source B due to higher confidence/listing_count
    assert top.get("source") in {"B", "arbitrated"}
    # Remaining rows must include original sources
    remaining_sources = {r["source"] for r in rows[1:]}
    assert remaining_sources == {"A", "B"}
