"""
Mapping from affix types to PoE Trade API stat IDs.

The official PoE trade API uses specific stat IDs for filtering.
This module maps our affix types (from valuable_affixes.json) to
the corresponding trade API stat IDs.

References:
- Official Trade API: https://www.pathofexile.com/trade
- Stat IDs can be found by inspecting network requests on the trade site
"""

from typing import Dict, Optional, Tuple


# Mapping: affix_type -> (stat_id, is_pseudo)
# Pseudo stats aggregate multiple mods (e.g., total life from all sources)
# Explicit stats are specific mod IDs

AFFIX_TO_STAT_ID: Dict[str, Tuple[str, bool]] = {
    # === Defensive Stats ===
    "life": ("pseudo.pseudo_total_life", True),
    "energy_shield": ("pseudo.pseudo_total_energy_shield", True),

    # === Resistances ===
    "resistances": ("pseudo.pseudo_total_elemental_resistance", True),
    # Individual resistances (if needed for specific filtering)
    "fire_resistance": ("pseudo.pseudo_total_fire_resistance", True),
    "cold_resistance": ("pseudo.pseudo_total_cold_resistance", True),
    "lightning_resistance": ("pseudo.pseudo_total_lightning_resistance", True),
    "chaos_resistance": ("pseudo.pseudo_total_chaos_resistance", True),

    # === Movement ===
    "movement_speed": ("explicit.stat_2250533757", False),  # increased Movement Speed

    # === Offensive Stats ===
    "critical_strike_multiplier": ("pseudo.pseudo_global_critical_strike_multiplier", True),
    "added_physical_damage": ("pseudo.pseudo_adds_physical_damage", True),

    # === Utility ===
    "spell_suppression": ("explicit.stat_3325883026", False),  # Suppress Spell Damage
    "flask_charges": ("explicit.stat_2213025270", False),  # Flask Charges gained
    "cooldown_recovery": ("explicit.stat_838869912", False),  # Cooldown Recovery Rate
}


# Mapping: affix_type -> minimum value thresholds for filtering
# These are conservative - we only filter for T1/T2 values to get comparable items
AFFIX_MIN_VALUES: Dict[str, int] = {
    "life": 70,  # T2+ life
    "energy_shield": 45,  # T3+ ES
    "resistances": 35,  # T3+ single res
    "chaos_resistance": 20,  # T3+ chaos res
    "movement_speed": 25,  # T1 movement
    "critical_strike_multiplier": 25,  # T1 crit multi
    "spell_suppression": 15,  # T1 suppression
}


def get_stat_id(affix_type: str) -> Optional[Tuple[str, bool]]:
    """
    Get trade API stat ID for an affix type.

    Args:
        affix_type: Affix type from valuable_affixes.json (e.g., "life", "resistances")

    Returns:
        (stat_id, is_pseudo) tuple, or None if not mapped
    """
    return AFFIX_TO_STAT_ID.get(affix_type)


def get_min_value(affix_type: str, actual_value: Optional[float] = None) -> Optional[int]:
    """
    Get minimum value threshold for trade filtering.

    Args:
        affix_type: Affix type from valuable_affixes.json
        actual_value: Actual rolled value on the item

    Returns:
        Minimum value for filtering, or None if no threshold defined

    Strategy:
        - If actual_value provided, use 80% of it (to find similar items)
        - Otherwise use conservative T2+ threshold from AFFIX_MIN_VALUES
    """
    if actual_value is not None and actual_value > 0:
        # Use 80% of actual value as minimum
        return int(actual_value * 0.8)

    # Fallback to conservative threshold
    return AFFIX_MIN_VALUES.get(affix_type)


def build_stat_filters(
    matched_affixes: list,
    max_filters: int = 4
) -> list[dict]:
    """
    Build trade API stat filters from matched affixes.

    Args:
        matched_affixes: List of AffixMatch objects from rare_item_evaluator
        max_filters: Maximum number of filters to add (default: 4)

    Returns:
        List of filter dicts for trade API stats array

    Strategy:
        - Prioritize T1/T2 affixes (they're most valuable)
        - Limit to max_filters to avoid over-constraining the search
        - Use actual rolled values when available
    """
    filters = []

    # Sort by tier (T1 first) and weight (higher first)
    sorted_affixes = sorted(
        matched_affixes,
        key=lambda m: (
            0 if getattr(m, 'tier', 'tier3') == 'tier1' else
            1 if getattr(m, 'tier', 'tier3') == 'tier2' else 2,
            -getattr(m, 'weight', 0)
        )
    )

    for match in sorted_affixes[:max_filters]:
        affix_type = getattr(match, 'affix_type', None)
        if not affix_type:
            continue

        stat_mapping = get_stat_id(affix_type)
        if not stat_mapping:
            continue

        stat_id, _ = stat_mapping

        # Get minimum value for filtering
        actual_value = getattr(match, 'value', None)
        min_value = get_min_value(affix_type, actual_value)

        if min_value is None:
            continue

        # Build filter
        filter_dict = {
            "id": stat_id,
            "value": {"min": min_value}
        }

        # Add optional max value for very specific searches
        # (commented out for now - makes searches too restrictive)
        # if actual_value is not None:
        #     filter_dict["value"]["max"] = int(actual_value * 1.2)

        filters.append(filter_dict)

    return filters
