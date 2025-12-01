"""
Pricing estimation policy and helpers.

This module centralizes configurable thresholds and rounding rules used
by price display logic, so they can be tuned and unit-tested without
editing the main service code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayPolicy:
    # Confidence thresholds
    high_count: int = 20
    medium_count: int = 8

    # Spread thresholds (as ratios)
    high_spread: float = 0.35
    medium_spread: float = 0.6
    low_conf_spread: float = 0.8

    # Rounding steps (in chaos) for different price bands
    step_ge_100: float = 5.0   # >= 100c → round to nearest 5c
    step_ge_10: float = 1.0    # >= 10c  → round to nearest 1c


# Default policy used across the app. Consider sourcing from Config later.
DEFAULT_POLICY = DisplayPolicy()

# Active policy can be customized at runtime (e.g., from Config)
_ACTIVE_POLICY: DisplayPolicy = DEFAULT_POLICY


def get_active_policy() -> DisplayPolicy:
    """Return the current active DisplayPolicy (may be customized at runtime)."""
    return _ACTIVE_POLICY


def set_active_policy(policy: DisplayPolicy) -> None:
    """Set the active DisplayPolicy."""
    global _ACTIVE_POLICY
    _ACTIVE_POLICY = policy


def set_active_policy_from_dict(data: dict) -> None:
    """Set active policy from a mapping, using defaults for missing keys."""
    if not isinstance(data, dict):
        return
    # Use DEFAULTS as base so calling with {} resets to defaults and
    # to avoid leaking overrides across tests/runs.
    base = DEFAULT_POLICY
    try:
        policy = DisplayPolicy(
            high_count=int(data.get("high_count", base.high_count)),
            medium_count=int(data.get("medium_count", base.medium_count)),
            high_spread=float(data.get("high_spread", base.high_spread)),
            medium_spread=float(data.get("medium_spread", base.medium_spread)),
            low_conf_spread=float(data.get("low_conf_spread", base.low_conf_spread)),
            step_ge_100=float(data.get("step_ge_100", base.step_ge_100)),
            step_ge_10=float(data.get("step_ge_10", base.step_ge_10)),
        )
    except Exception:
        # If any cast fails, keep current policy
        return
    set_active_policy(policy)


def round_to_step(value: float, step: float) -> float:
    """Round numeric value to nearest multiple of step.

    Example: round_to_step(123.4, 5.0) -> 125.0
    """
    if step <= 0:
        return value
    return round(value / step) * step
