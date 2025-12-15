"""
Price Context Calculator - Provides CHEAP/AVERAGE/EXPENSIVE labels for prices.

Calculates price context based on configurable thresholds by item class and rarity,
helping users understand if a price is typical for that item type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class PriceContext:
    """Price context information for display."""

    label: str  # "CHEAP", "AVERAGE", "EXPENSIVE"
    color: str  # Hex color for display
    explanation: str  # Human-readable explanation
    thresholds: Tuple[float, float]  # (cheap_max, expensive_min) used

    @property
    def is_cheap(self) -> bool:
        return self.label == "CHEAP"

    @property
    def is_expensive(self) -> bool:
        return self.label == "EXPENSIVE"

    @property
    def is_average(self) -> bool:
        return self.label == "AVERAGE"


class PriceContextCalculator:
    """
    Calculates price context (CHEAP/AVERAGE/EXPENSIVE) based on thresholds.

    Thresholds are loaded from config and can be customized per item class
    and rarity combination.

    Usage:
        calc = PriceContextCalculator(config)
        context = calc.get_context(50.0, "Rings", "Rare")
        print(f"Price is {context.label}")  # "Price is AVERAGE"
    """

    # Context label colors
    COLORS = {
        "CHEAP": "#4CAF50",     # Green - good buy opportunity
        "AVERAGE": "#2196F3",   # Blue - fair market price
        "EXPENSIVE": "#FF9800", # Orange - premium pricing
    }

    # Default thresholds if config unavailable
    DEFAULT_THRESHOLDS: Dict[str, Dict[str, List[float]]] = {
        "_default": {"_default": [10, 100]},
    }

    def __init__(self, config: Optional["Config"] = None):
        """
        Initialize the price context calculator.

        Args:
            config: Config instance to load thresholds from.
                   If None, uses hardcoded defaults.
        """
        self._config = config
        self._thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, Dict[str, List[float]]]:
        """Load thresholds from config or use defaults."""
        if self._config is None:
            return self.DEFAULT_THRESHOLDS.copy()

        try:
            config_data = self._config.data
            price_context = config_data.get("price_context", {})
            thresholds = price_context.get("thresholds", {})

            if thresholds:
                logger.debug(f"Loaded {len(thresholds)} item class thresholds from config")
                return thresholds
            else:
                logger.debug("No thresholds in config, using defaults")
                return self.DEFAULT_THRESHOLDS.copy()

        except Exception as e:
            logger.warning(f"Failed to load thresholds from config: {e}")
            return self.DEFAULT_THRESHOLDS.copy()

    def is_enabled(self) -> bool:
        """Check if price context feature is enabled in config."""
        if self._config is None:
            return True

        try:
            config_data = self._config.data
            price_context = config_data.get("price_context", {})
            return price_context.get("enabled", True)
        except Exception:
            return True

    def get_context(
        self,
        price: float,
        item_class: str,
        rarity: str,
    ) -> PriceContext:
        """
        Get price context for an item.

        Args:
            price: Item price in chaos orbs
            item_class: Item class (e.g., "Rings", "Body Armours")
            rarity: Item rarity (e.g., "Rare", "Unique")

        Returns:
            PriceContext with label, color, and explanation
        """
        # Get thresholds for this item type
        thresholds = self._get_thresholds(item_class, rarity)
        cheap_max, expensive_min = thresholds

        # Determine context
        if price <= 0:
            label = "AVERAGE"
            explanation = "No price data available"
        elif price <= cheap_max:
            label = "CHEAP"
            explanation = self._format_explanation(price, item_class, rarity, "cheap", thresholds)
        elif price >= expensive_min:
            label = "EXPENSIVE"
            explanation = self._format_explanation(price, item_class, rarity, "expensive", thresholds)
        else:
            label = "AVERAGE"
            explanation = self._format_explanation(price, item_class, rarity, "typical", thresholds)

        return PriceContext(
            label=label,
            color=self.COLORS[label],
            explanation=explanation,
            thresholds=thresholds,
        )

    def _get_thresholds(self, item_class: str, rarity: str) -> Tuple[float, float]:
        """
        Get thresholds for a specific item class and rarity.

        Falls back through: exact match -> item class default -> global default
        """
        # Try exact match
        if item_class in self._thresholds:
            class_thresholds = self._thresholds[item_class]
            if rarity in class_thresholds:
                t = class_thresholds[rarity]
                return (float(t[0]), float(t[1]))

            # Try _default rarity for this class
            if "_default" in class_thresholds:
                t = class_thresholds["_default"]
                return (float(t[0]), float(t[1]))

        # Try normalized item class (lowercase, underscores)
        normalized = self._normalize_item_class(item_class)
        for key in self._thresholds:
            if self._normalize_item_class(key) == normalized:
                class_thresholds = self._thresholds[key]
                if rarity in class_thresholds:
                    t = class_thresholds[rarity]
                    return (float(t[0]), float(t[1]))
                if "_default" in class_thresholds:
                    t = class_thresholds["_default"]
                    return (float(t[0]), float(t[1]))

        # Use global default
        if "_default" in self._thresholds:
            default_thresholds = self._thresholds["_default"]
            if "_default" in default_thresholds:
                t = default_thresholds["_default"]
                return (float(t[0]), float(t[1]))

        # Hardcoded fallback
        return (10.0, 100.0)

    def _normalize_item_class(self, item_class: str) -> str:
        """Normalize item class for matching."""
        return item_class.lower().replace(" ", "_")

    def _format_explanation(
        self,
        price: float,
        item_class: str,
        rarity: str,
        context_type: str,
        thresholds: Tuple[float, float],
    ) -> str:
        """Format a human-readable explanation."""
        cheap_max, expensive_min = thresholds

        # Simplify item class for display
        display_class = item_class.lower()
        if display_class.endswith("s"):
            display_class = display_class[:-1]  # rings -> ring

        display_rarity = rarity.lower()

        if context_type == "cheap":
            return f"{price:.0f}c is cheap for {display_rarity} {display_class} (under {cheap_max:.0f}c)"
        elif context_type == "expensive":
            return f"{price:.0f}c is expensive for {display_rarity} {display_class} (over {expensive_min:.0f}c)"
        else:
            return f"{price:.0f}c is typical for {display_rarity} {display_class} ({cheap_max:.0f}-{expensive_min:.0f}c range)"

    def get_all_thresholds(self) -> Dict[str, Dict[str, List[float]]]:
        """Get all configured thresholds (for settings UI)."""
        return self._thresholds.copy()

    def set_thresholds(
        self,
        item_class: str,
        rarity: str,
        cheap_max: float,
        expensive_min: float,
    ) -> None:
        """
        Set thresholds for an item class/rarity combination.

        Args:
            item_class: Item class name
            rarity: Rarity name
            cheap_max: Maximum price to be considered cheap
            expensive_min: Minimum price to be considered expensive
        """
        if item_class not in self._thresholds:
            self._thresholds[item_class] = {}

        self._thresholds[item_class][rarity] = [cheap_max, expensive_min]

        # Save to config if available
        self._save_thresholds()

    def _save_thresholds(self) -> None:
        """Save current thresholds to config."""
        if self._config is None:
            return

        try:
            config_data = self._config.data
            if "price_context" not in config_data:
                config_data["price_context"] = {}

            config_data["price_context"]["thresholds"] = self._thresholds
            self._config.save()
            logger.debug("Saved price context thresholds to config")

        except Exception as e:
            logger.error(f"Failed to save thresholds to config: {e}")


# Convenience function for quick access
def get_price_context(
    price: float,
    item_class: str,
    rarity: str,
    config: Optional["Config"] = None,
) -> PriceContext:
    """
    Quick access function to get price context.

    Args:
        price: Item price in chaos
        item_class: Item class (e.g., "Rings")
        rarity: Item rarity (e.g., "Rare")
        config: Optional config for thresholds

    Returns:
        PriceContext with label, color, explanation
    """
    calc = PriceContextCalculator(config)
    return calc.get_context(price, item_class, rarity)
