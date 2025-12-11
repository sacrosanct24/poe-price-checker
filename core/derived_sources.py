# core/derived_sources.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.price_multi import PriceSource, RESULT_COLUMNS
from core.pricing import PriceService


@dataclass
class UndercutPriceSource(PriceSource):
    """
    A synthetic PriceSource that derives a suggested listing price by
    applying an undercut factor to the base PriceService results.

    For example, if poe_ninja says 100c and undercut_factor=0.9,
    this source will emit ~90c rows with source="suggested_undercut".
    """

    name: str
    base_service: PriceService
    undercut_factor: float = 0.9

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        item_text = (item_text or "").strip()
        if not item_text:
            return []

        # Ask the base service for its rows (poe_ninja-based)
        base_rows = self.base_service.check_item(item_text)

        derived: list[dict[str, Any]] = []

        for row in base_rows:
            if isinstance(row, Mapping):
                data: dict[str, Any] = dict(row)
            else:
                # Fallback: pull attributes
                data = {col: getattr(row, col, "") for col in RESULT_COLUMNS}

            # Extract chaos/divine as numbers if possible
            chaos_raw = data.get("chaos_value", "")
            divine_raw = data.get("divine_value", "")

            try:
                chaos_val = float(chaos_raw)
            except (TypeError, ValueError):
                chaos_val = 0.0

            try:
                divine_val = float(divine_raw)
            except (TypeError, ValueError):
                divine_val = 0.0

            # Apply undercut
            chaos_undercut = chaos_val * self.undercut_factor
            divine_undercut = divine_val * self.undercut_factor

            data["chaos_value"] = chaos_undercut
            data["divine_value"] = divine_undercut

            # Ensure source is clearly labeled
            data["source"] = self.name

            # Ensure all expected columns exist
            for col in RESULT_COLUMNS:
                data.setdefault(col, "")

            derived.append(data)

        return derived
