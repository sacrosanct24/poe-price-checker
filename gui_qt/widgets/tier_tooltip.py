"""
Mod Tier Education Tooltips.

Provides educational tooltips explaining:
- What tier a mod is
- Roll ranges for each tier
- How the mod compares to ideal

Part of Phase 3: Teaching & Learning features.
"""
from __future__ import annotations

from typing import Optional

from core.affix_tier_calculator import AFFIX_TIER_DATA
from core.build_priorities import AVAILABLE_STATS


def get_tier_tooltip(stat_type: str, current_value: int, current_tier: int) -> str:
    """
    Generate an educational tooltip for a mod tier.

    Args:
        stat_type: The stat type key (e.g., "life", "fire_resistance")
        current_value: The current value of the mod
        current_tier: The detected tier number

    Returns:
        HTML-formatted tooltip text
    """
    # Get stat display name
    stat_name = AVAILABLE_STATS.get(stat_type, stat_type.replace("_", " ").title())

    # Get tier data
    tier_data = AFFIX_TIER_DATA.get(stat_type, [])
    if not tier_data:
        return f"<b>{stat_name}</b><br>Tier data not available"

    # Build tooltip
    lines = [
        f"<b>{stat_name}</b>",
        f"<br><span style='color: #888;'>Current: {current_value} (T{current_tier})</span>",
        "<br>",
        "<b>All Tiers:</b>",
    ]

    for tier, ilvl_req, min_val, max_val in tier_data:
        # Highlight current tier
        if tier == current_tier:
            prefix = "<span style='color: #4CAF50; font-weight: bold;'>&#10148; "
            suffix = "</span>"
        else:
            prefix = "<span style='color: #ccc;'>  "
            suffix = "</span>"

        tier_label = f"T{tier}"
        range_str = f"{min_val}-{max_val}" if min_val != max_val else str(min_val)
        lines.append(f"{prefix}{tier_label}: {range_str} (ilvl {ilvl_req}+){suffix}")

    # Add improvement note
    if current_tier > 1:
        # Get T1 data
        t1_max = tier_data[0][3]
        improvement = t1_max - current_value
        if improvement > 0:
            lines.append(f"<br><span style='color: #FFA726;'>T1 would give up to +{improvement}</span>")

    # Add roll quality
    current_tier_data = next(
        (t for t in tier_data if t[0] == current_tier), None
    )
    if current_tier_data:
        _, _, min_roll, max_roll = current_tier_data
        if max_roll > min_roll:
            roll_quality = ((current_value - min_roll) / (max_roll - min_roll)) * 100
            quality_color = _get_quality_color(roll_quality)
            lines.append(
                f"<br><span style='color: {quality_color};'>"
                f"Roll quality: {roll_quality:.0f}% of T{current_tier} range</span>"
            )

    return "<br>".join(lines)


def get_quick_tier_info(stat_type: str, value: int) -> str:
    """
    Get a quick one-line tier description.

    Args:
        stat_type: The stat type key
        value: The current value

    Returns:
        Quick description string
    """
    tier_data = AFFIX_TIER_DATA.get(stat_type, [])
    if not tier_data:
        return ""

    # Find tier
    for tier, ilvl_req, min_val, max_val in tier_data:
        if min_val <= value <= max_val:
            range_str = f"{min_val}-{max_val}"
            return f"T{tier} ({range_str})"

    # Above T1
    if value > tier_data[0][3]:
        return "T1+ (elevated)"

    return "T?"


def get_all_tiers_text(stat_type: str) -> str:
    """
    Get a text representation of all tiers for a stat.

    Args:
        stat_type: The stat type key

    Returns:
        Multi-line text showing all tiers
    """
    stat_name = AVAILABLE_STATS.get(stat_type, stat_type.replace("_", " ").title())
    tier_data = AFFIX_TIER_DATA.get(stat_type, [])

    if not tier_data:
        return f"{stat_name}: No tier data"

    lines = [f"=== {stat_name} Tiers ==="]
    for tier, ilvl_req, min_val, max_val in tier_data:
        range_str = f"{min_val}-{max_val}" if min_val != max_val else str(min_val)
        lines.append(f"  T{tier}: {range_str} (requires ilvl {ilvl_req})")

    return "\n".join(lines)


def get_tier_badge_style(tier: Optional[int]) -> dict:
    """
    Get styling for a tier badge.

    Args:
        tier: Tier number (1 = best)

    Returns:
        Dict with 'background', 'color', 'label' keys
    """
    if tier == 1:
        return {
            "background": "#4CAF50",  # Green
            "color": "white",
            "label": "T1",
            "description": "Top tier - best possible",
        }
    elif tier == 2:
        return {
            "background": "#2196F3",  # Blue
            "color": "white",
            "label": "T2",
            "description": "Second tier - very good",
        }
    elif tier == 3:
        return {
            "background": "#9E9E9E",  # Grey
            "color": "white",
            "label": "T3",
            "description": "Third tier - decent",
        }
    elif tier == 4:
        return {
            "background": "#795548",  # Brown
            "color": "white",
            "label": "T4",
            "description": "Fourth tier - mediocre",
        }
    elif tier is not None and tier >= 5:
        return {
            "background": "#F44336",  # Red
            "color": "white",
            "label": f"T{tier}",
            "description": "Low tier - poor",
        }
    else:
        return {
            "background": "#424242",  # Dark grey
            "color": "#888",
            "label": "???",
            "description": "Unknown tier",
        }


def _get_quality_color(quality: float) -> str:
    """Get color based on roll quality percentage."""
    if quality >= 90:
        return "#4CAF50"  # Green - excellent
    elif quality >= 70:
        return "#8BC34A"  # Light green - good
    elif quality >= 50:
        return "#FFC107"  # Amber - average
    elif quality >= 30:
        return "#FF9800"  # Orange - below average
    else:
        return "#F44336"  # Red - poor


def generate_tier_education_html(stat_type: str) -> str:
    """
    Generate full HTML education content for a stat type.

    Args:
        stat_type: The stat type key

    Returns:
        Full HTML document for education display
    """
    stat_name = AVAILABLE_STATS.get(stat_type, stat_type.replace("_", " ").title())
    tier_data = AFFIX_TIER_DATA.get(stat_type, [])

    if not tier_data:
        return f"<p>No tier data available for {stat_name}</p>"

    html = f"""
    <h3 style="color: #E0E0E0; margin-bottom: 8px;">{stat_name}</h3>
    <p style="color: #888; font-size: 12px;">
        Higher tiers require higher item levels to spawn.
        The value can roll anywhere within the tier's range.
    </p>
    <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
        <tr style="background: #333; color: #E0E0E0;">
            <th style="padding: 6px; text-align: left;">Tier</th>
            <th style="padding: 6px; text-align: center;">Range</th>
            <th style="padding: 6px; text-align: center;">Item Level</th>
            <th style="padding: 6px; text-align: left;">Notes</th>
        </tr>
    """

    for i, (tier, ilvl_req, min_val, max_val) in enumerate(tier_data):
        bg_color = "#2a2a2a" if i % 2 == 0 else "#1e1e1e"
        tier_style = get_tier_badge_style(tier)
        range_str = f"{min_val}-{max_val}" if min_val != max_val else str(min_val)

        notes = ""
        if tier == 1:
            notes = "Best possible"
        elif tier == len(tier_data):
            notes = "Lowest tier"

        html += f"""
        <tr style="background: {bg_color}; color: #E0E0E0;">
            <td style="padding: 6px;">
                <span style="background: {tier_style['background']}; color: {tier_style['color']};
                       padding: 2px 6px; border-radius: 3px; font-weight: bold;">
                    T{tier}
                </span>
            </td>
            <td style="padding: 6px; text-align: center; font-family: monospace;">
                {range_str}
            </td>
            <td style="padding: 6px; text-align: center;">
                {ilvl_req}+
            </td>
            <td style="padding: 6px; color: #888;">
                {notes}
            </td>
        </tr>
        """

    html += "</table>"

    # Add tips
    html += """
    <div style="margin-top: 12px; padding: 8px; background: #1a1a2e; border-radius: 4px;">
        <p style="color: #888; font-size: 11px; margin: 0;">
            <b style="color: #4CAF50;">Tip:</b>
            Items found in high-level maps (T16+) can roll T1 mods.
            Use Divine Orbs to re-roll values within the same tier.
        </p>
    </div>
    """

    return html
