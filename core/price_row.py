from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union, Any, Dict


LinksType = Union[str, int, None]


@dataclass
class PriceRow:
    """Normalized price result row across sources.

    This is a typed shape to help API/GUI layers and future refactors.
    Existing call sites may still pass dictionaries; adapters in
    MultiSourcePriceService will normalize objects to dicts for output.
    """

    source: str
    item_name: str = ""
    variant: str = ""
    links: LinksType = None
    chaos_value: Optional[float] = None
    divine_value: Optional[float] = None
    listing_count: Optional[int] = None
    confidence: str = ""
    explanation: str = ""


# --- Contract helpers ---
RESULT_COLUMNS: tuple[str, ...] = (
    "item_name",
    "variant",
    "links",
    "chaos_value",
    "divine_value",
    "listing_count",
    "source",
)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def to_dict(row: Union[Dict[str, Any], PriceRow]) -> Dict[str, Any]:
    """Best-effort convert a `PriceRow` or mapping to a dict."""
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(vars(row))
    except Exception:
        # Fallback resilient extraction
        return {col: getattr(row, col, None) for col in RESULT_COLUMNS}


def validate_and_normalize_row(row: Union[Dict[str, Any], PriceRow]) -> Dict[str, Any]:
    """Normalize a row to a dict with expected keys and sane types.

    - Ensures all RESULT_COLUMNS exist (missing become empty string or None).
    - Coerces chaos_value/divine_value to float or None.
    - Coerces listing_count to int or None.
    - Coerces source/item_name/variant to strings.
    """
    data = to_dict(row)
    out: Dict[str, Any] = {}

    out["source"] = str(data.get("source", ""))
    out["item_name"] = str(data.get("item_name", ""))
    out["variant"] = str(data.get("variant", ""))
    out["links"] = data.get("links", None)
    out["chaos_value"] = _coerce_float(data.get("chaos_value"))
    out["divine_value"] = _coerce_float(data.get("divine_value"))
    out["listing_count"] = _coerce_int(data.get("listing_count"))

    # Pass-through of optional metadata if present
    if "confidence" in data:
        out["confidence"] = str(data.get("confidence") or "")
    if "explanation" in data:
        out["explanation"] = data.get("explanation")

    # Ensure all expected columns exist for downstream users expecting keys
    for col in RESULT_COLUMNS:
        out.setdefault(col, None if col in ("chaos_value", "divine_value", "listing_count") else "")

    return out
