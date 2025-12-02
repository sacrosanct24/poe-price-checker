from core.price_arbitration import arbitrate_rows


def test_arbitrate_rows_picks_high_confidence_over_medium():
    rows = [
        {"source": "A", "chaos_value": 100.0, "listing_count": 5, "confidence": "medium"},
        {"source": "B", "chaos_value": 98.0, "listing_count": 3, "confidence": "high"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_uses_listing_count_as_tiebreaker():
    rows = [
        {"source": "A", "chaos_value": 10.0, "listing_count": 2, "confidence": "medium"},
        {"source": "B", "chaos_value": 10.5, "listing_count": 10, "confidence": "medium"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_prefers_value_closer_to_median_when_counts_equal():
    # Median is 10.0; pick row closer to 10.0
    rows = [
        {"source": "A", "chaos_value": 8.0, "listing_count": 5, "confidence": "low"},
        {"source": "B", "chaos_value": 12.0, "listing_count": 5, "confidence": "low"},
        {"source": "C", "chaos_value": 10.1, "listing_count": 5, "confidence": "low"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "C"


def test_arbitrate_rows_uses_source_priority_last():
    rows = [
        {"source": "A", "chaos_value": 10.0, "listing_count": 5, "confidence": "medium"},
        {"source": "B", "chaos_value": 10.0, "listing_count": 5, "confidence": "medium"},
    ]
    chosen = arbitrate_rows(rows, source_priority=["B", "A"])  # prefer B
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_ignores_rows_without_numeric_value():
    rows = [
        {"source": "A", "chaos_value": None, "listing_count": 0, "confidence": "none"},
        {"source": "B", "chaos_value": 5.0, "listing_count": 1, "confidence": "low"},
    ]
    chosen = arbitrate_rows(rows)
    assert chosen is not None
    assert chosen["source"] == "B"


def test_arbitrate_rows_returns_none_for_empty_or_unusable():
    assert arbitrate_rows([]) is None
    assert arbitrate_rows([{"source": "A", "chaos_value": None}]) is None
