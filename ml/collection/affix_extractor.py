"""Affix extraction for ML collection."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from core.item_parser import ParsedItem
from data_sources.mod_database import ModDatabase

logger = logging.getLogger(__name__)

_VALUE_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_TIER_RE = re.compile(r"Tier\s*(\d+)", re.IGNORECASE)


class AffixExtractor:
    """
    Extracts structured affix data from ParsedItem.

    Uses ModDatabase to:
    - Resolve affix_id from mod text
    - Determine tier from roll value
    - Compute roll_percentile within tier
    """

    def __init__(
        self,
        mod_database: ModDatabase,
        logger_override: Optional[logging.Logger] = None,
    ) -> None:
        self.db = mod_database
        self.logger = logger_override or logger

    def extract(self, item: ParsedItem) -> List[Dict[str, Any]]:
        """Extract affix data from a parsed item."""
        mods: List[str] = []
        if item.explicits:
            mods.extend(item.explicits)
        if item.implicits:
            mods.extend(item.implicits)

        extracted: List[Dict[str, Any]] = []
        for mod_text in mods:
            result = self._extract_mod(mod_text)
            if result:
                extracted.append(result)
        return extracted

    def _extract_mod(self, mod_text: str) -> Optional[Dict[str, Any]]:
        text = (mod_text or "").strip()
        if not text:
            return None

        pattern = _build_like_pattern(text)
        value = _extract_value(text)
        mods = self.db.find_mods_by_stat_text(pattern)
        if not mods:
            self.logger.debug("No mod match for '%s' (pattern=%s)", text, pattern)
            return None

        match = _select_mod_match(mods, value)
        if not match:
            self.logger.debug("No viable tier for '%s'", text)
            return None

        tier_num = _parse_tier(match.get("tier_text"))
        min_val, max_val = _parse_mod_range(match)
        roll_percentile = _compute_roll_percentile(value, min_val, max_val)

        return {
            "affix_id": match.get("id"),
            "tier": tier_num,
            "roll_percentile": roll_percentile,
            "value": value,
        }


def _extract_value(text: str) -> Optional[float]:
    values = _VALUE_RE.findall(text)
    if not values:
        return None
    try:
        return float(values[0])
    except ValueError:
        return None


def _build_like_pattern(text: str) -> str:
    cleaned = re.sub(r"\([^)]*\)", "", text)
    cleaned = cleaned.replace("#", "%")
    cleaned = re.sub(r"[-+]?\d+(?:\.\d+)?%?", "%", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    pattern = f"%{cleaned}%"
    return re.sub(r"%+", "%", pattern)


def _select_mod_match(mods: List[Dict[str, Any]], value: Optional[float]) -> Optional[Dict[str, Any]]:
    if not mods:
        return None

    candidates: List[tuple[int, Dict[str, Any]]] = []
    for mod in mods:
        min_val, max_val = _parse_mod_range(mod)
        if value is None or min_val is None or max_val is None:
            tier_num = _parse_tier(mod.get("tier_text")) or 99
            candidates.append((tier_num, mod))
            continue

        if min_val <= value <= max_val:
            tier_num = _parse_tier(mod.get("tier_text")) or 99
            candidates.append((tier_num, mod))

    if not candidates:
        candidates = [(_parse_tier(mod.get("tier_text")) or 99, mod) for mod in mods]

    candidates.sort(key=lambda entry: entry[0])
    return candidates[0][1]


def _parse_mod_range(mod: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    stat_text = (mod.get("stat_text_raw") or mod.get("stat_text") or "").strip()
    if not stat_text:
        return None, None

    range_match = re.search(r"\((\d+)-(\d+)\)", stat_text)
    if range_match:
        return float(range_match.group(1)), float(range_match.group(2))

    single_match = _VALUE_RE.search(stat_text)
    if single_match:
        val = float(single_match.group(0))
        return val, val

    return None, None


def _parse_tier(tier_text: Optional[str]) -> Optional[int]:
    if not tier_text:
        return None
    match = _TIER_RE.search(tier_text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _compute_roll_percentile(
    value: Optional[float],
    min_val: Optional[float],
    max_val: Optional[float],
) -> Optional[float]:
    if value is None or min_val is None or max_val is None:
        return None
    if max_val == min_val:
        return 1.0
    percentile = (value - min_val) / (max_val - min_val)
    if percentile < 0.0:
        return 0.0
    if percentile > 1.0:
        return 1.0
    return percentile
