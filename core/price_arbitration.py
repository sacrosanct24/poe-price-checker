from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable, Optional, Union

from core.price_row import PriceRow

ConfidenceRank = {"high": 3, "medium": 2, "low": 1, "none": 0, "unknown": 0}


def _to_dict(row: Union[dict[str, Any], PriceRow]) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    # Support dataclass PriceRow or objects with attributes
    try:
        return dict(vars(row))
    except Exception:
        return {
            "source": getattr(row, "source", ""),
            "item_name": getattr(row, "item_name", ""),
            "variant": getattr(row, "variant", ""),
            "links": getattr(row, "links", None),
            "chaos_value": getattr(row, "chaos_value", None),
            "divine_value": getattr(row, "divine_value", None),
            "listing_count": getattr(row, "listing_count", None),
            "confidence": getattr(row, "confidence", ""),
            "explanation": getattr(row, "explanation", ""),
        }


def arbitrate_rows(
    rows: Iterable[Union[dict[str, Any], PriceRow]],
    source_priority: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    """Pick a single display row from multiple source rows.

    Tie-breakers (in order):
      1. Confidence (high > medium > low > none/unknown)
      2. Listing count (more is better)
      3. Chaos value stability heuristic (prefer closer to group median, when possible)
      4. Source priority order (if provided)

    Returns a dict representation of the chosen row or None if input is empty
    or contains no usable rows (no chaos values).
    """

    materialized = [_to_dict(r) for r in rows]
    if not materialized:
        return None

    # Only consider rows with a numeric chaos_value
    usable = []
    for r in materialized:
        val = r.get("chaos_value")
        try:
            r_val = float(val) if val is not None else None
        except (TypeError, ValueError):
            r_val = None
        if r_val is None:
            continue
        rec = dict(r)
        rec["chaos_value"] = r_val
        # normalize confidence
        conf = str(rec.get("confidence") or "").lower()
        rec["_conf_rank"] = ConfidenceRank.get(conf, 0)
        # normalize listing_count
        try:
            rec["_count_norm"] = int(rec.get("listing_count") or 0)
        except (TypeError, ValueError):
            rec["_count_norm"] = 0
        usable.append(rec)

    if not usable:
        return None

    # Pre-compute median for simple stability heuristic
    vals: list[float] = sorted([float(u["chaos_value"]) for u in usable])
    mid = len(vals) // 2
    median: float = vals[mid] if len(vals) % 2 == 1 else (vals[mid - 1] + vals[mid]) / 2.0

    def stability_score(v: float) -> float:
        # Smaller distance to median is better -> we will sort by abs diff ascending
        return abs(v - median)

    # Source priority map for deterministic final tie-breaker
    priority_map = {name: idx for idx, name in enumerate(source_priority or [])}

    def sort_key(r: dict[str, Any]):
        return (
            -r["_conf_rank"],
            -r["_count_norm"],
            stability_score(r["chaos_value"]),
            priority_map.get(r.get("source", ""), float("inf")),
            r.get("source", ""),  # final deterministic tie-breaker
        )

    usable.sort(key=sort_key)
    chosen = usable[0]
    # Drop helper fields
    chosen.pop("_conf_rank", None)
    chosen.pop("_count_norm", None)
    return chosen
