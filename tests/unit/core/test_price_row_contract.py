from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import math

from core.price_row import PriceRow, validate_and_normalize_row


def test_validate_and_normalize_from_dict_with_string_numbers():
    raw = {
        "source": "poe_ninja",
        "item_name": "Exalted Orb",
        "variant": "",
        "links": "",
        "chaos_value": "123.45",
        "divine_value": "0.5",
        "listing_count": "42",
        "confidence": "high",
        "explanation": {"why": "test"},
    }
    out = validate_and_normalize_row(raw)
    assert out["source"] == "poe_ninja"
    assert out["item_name"] == "Exalted Orb"
    assert math.isclose(out["chaos_value"], 123.45)
    assert math.isclose(out["divine_value"], 0.5)
    assert out["listing_count"] == 42
    assert out["confidence"] == "high"
    # Ensure all expected keys exist
    for key in ("item_name", "variant", "links", "chaos_value", "divine_value", "listing_count", "source"):
        assert key in out


def test_validate_and_normalize_from_pricerow_dataclass():
    row = PriceRow(
        source="watch",
        item_name="Orb of Alchemy",
        chaos_value=2.3,
        divine_value=None,
        listing_count=7,
        confidence="medium",
        explanation="ok",
    )
    out = validate_and_normalize_row(row)
    assert out["source"] == "watch"
    assert out["item_name"] == "Orb of Alchemy"
    assert math.isclose(out["chaos_value"], 2.3)
    assert out["divine_value"] is None
    assert out["listing_count"] == 7
    assert out["confidence"] == "medium"


def test_validate_and_normalize_missing_values_and_types():
    # Missing keys should be present in output with sensible defaults
    out = validate_and_normalize_row({"source": "X"})
    assert out["source"] == "X"
    assert out["item_name"] == ""
    assert out["variant"] == ""
    assert out["links"] is None or out["links"] == ""  # link is permissive
    assert out["chaos_value"] is None
    assert out["divine_value"] is None
    assert out["listing_count"] is None


def test_validate_and_normalize_from_attribute_object():
    @dataclass
    class RowLike:
        source: str = "S"
        item_name: str = "Item"
        chaos_value: Any = "3.14"
        listing_count: Any = "9"
        confidence: str = "low"

    obj = RowLike()
    out = validate_and_normalize_row(obj)
    assert out["source"] == "S"
    assert out["item_name"] == "Item"
    assert math.isclose(out["chaos_value"], 3.14)
    assert out["listing_count"] == 9
    assert out.get("confidence") == "low"
