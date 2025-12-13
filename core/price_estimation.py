"""
Pricing estimation policy and helpers.

This module centralizes configurable thresholds and rounding rules used
by price display logic, so they can be tuned and unit-tested without
editing the main service code.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Any


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


# Default policy used across the app.
DEFAULT_POLICY = DisplayPolicy()


class PolicyManager:
    """
    Thread-safe manager for DisplayPolicy state.

    Encapsulates the active policy in a class to avoid module-level
    global state with `global` statements. Provides the same interface
    as the previous module-level functions.
    """

    def __init__(self, default: DisplayPolicy = DEFAULT_POLICY) -> None:
        self._policy: DisplayPolicy = default
        self._default: DisplayPolicy = default
        self._lock = threading.Lock()

    def get_policy(self) -> DisplayPolicy:
        """Return the current active DisplayPolicy."""
        with self._lock:
            return self._policy

    def set_policy(self, policy: DisplayPolicy) -> None:
        """Set the active DisplayPolicy."""
        with self._lock:
            self._policy = policy

    def set_policy_from_dict(self, data: Dict[str, Any]) -> None:
        """Set active policy from a mapping, using defaults for missing keys."""
        if not isinstance(data, dict):
            return
        # Use defaults as base so calling with {} resets to defaults
        base = self._default
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
        except (ValueError, TypeError):
            # If any cast fails, keep current policy
            return
        self.set_policy(policy)

    def reset(self) -> None:
        """Reset to default policy."""
        with self._lock:
            self._policy = self._default


# Module-level singleton instance for backward compatibility
_policy_manager = PolicyManager()


# Backward-compatible module-level functions that delegate to the singleton
def get_active_policy() -> DisplayPolicy:
    """Return the current active DisplayPolicy (may be customized at runtime)."""
    return _policy_manager.get_policy()


def set_active_policy(policy: DisplayPolicy) -> None:
    """Set the active DisplayPolicy."""
    _policy_manager.set_policy(policy)


def set_active_policy_from_dict(data: dict) -> None:
    """Set active policy from a mapping, using defaults for missing keys."""
    _policy_manager.set_policy_from_dict(data)


def round_to_step(value: float, step: float) -> float:
    """Round numeric value to nearest multiple of step.

    Example: round_to_step(123.4, 5.0) -> 125.0
    """
    if step <= 0:
        return value
    return round(value / step) * step
