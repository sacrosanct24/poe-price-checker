"""
poeprices.info API client for ML-based rare item price prediction.

This API uses machine learning to predict prices for rare items based on their mods.
It's especially useful for rare items which are hard to price via traditional lookups.
"""
from __future__ import annotations

import base64
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports when running as script
_script_dir = Path(__file__).parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from data_sources.base_api import BaseAPIClient

logger = logging.getLogger(__name__)


@dataclass
class PoePricesPrediction:
    """Result from poeprices.info price prediction."""

    min_price: float
    max_price: float
    currency: str  # "divine" or "chaos"
    confidence_score: float  # 0-100
    error_code: int  # 0 = success
    error_msg: str
    warning_msg: str
    mod_contributions: List[tuple[str, float]]  # [(mod_text, contribution), ...]

    @property
    def is_valid(self) -> bool:
        """Check if prediction is valid."""
        return self.error_code == 0 and self.min_price > 0

    @property
    def average_price(self) -> float:
        """Get average of min/max price."""
        return (self.min_price + self.max_price) / 2

    @property
    def price_range_str(self) -> str:
        """Get formatted price range string."""
        if self.currency == "divine":
            return f"{self.min_price:.1f}-{self.max_price:.1f} divine"
        return f"{self.min_price:.0f}-{self.max_price:.0f} chaos"

    @property
    def confidence_tier(self) -> str:
        """Get confidence tier based on score."""
        if self.confidence_score >= 80:
            return "high"
        elif self.confidence_score >= 60:
            return "medium"
        return "low"


class PoePricesAPI(BaseAPIClient):
    """
    Client for poeprices.info ML price prediction API.

    This API takes raw item text (base64 encoded) and returns
    a price prediction based on machine learning analysis of
    the item's modifiers.

    Especially useful for rare items where direct price lookup
    isn't possible.
    """

    def __init__(self, league: str = "Standard"):
        """
        Initialize poeprices.info API client.

        Args:
            league: League name (e.g., "Standard", "Phrecia")
        """
        super().__init__(
            base_url="https://www.poeprices.info",
            rate_limit=0.5,  # Conservative rate limit
            cache_ttl=1800,  # Cache for 30 minutes
            user_agent="PoE-Price-Checker/2.5 (GitHub: sacrosanct24/poe-price-checker)",
        )

        self.league = league
        self.request_count = 0

        logger.info(f"Initialized PoePricesAPI for league: {league}")

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and params."""
        if params:
            league = params.get('l', '')
            # Use hash of encoded item for cache key (item text can be long)
            item_hash = hash(params.get('i', ''))
            return f"{endpoint}:{league}:{item_hash}"
        return endpoint

    def _encode_item_text(self, item_text: str) -> str:
        """
        Base64 encode item text for API submission.

        Args:
            item_text: Raw item text (from Ctrl+C in game)

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(item_text.encode('utf-8')).decode('utf-8')

    def predict_price(
        self,
        item_text: str,
        league: Optional[str] = None,
    ) -> PoePricesPrediction:
        """
        Get price prediction for an item.

        Args:
            item_text: Raw item text (from Ctrl+C in game)
            league: League override (uses instance league if None)

        Returns:
            PoePricesPrediction with price estimate and confidence
        """
        self.request_count += 1
        league = league or self.league

        # Encode item text
        encoded_item = self._encode_item_text(item_text)

        logger.info(f"[poeprices] Requesting price prediction for league: {league}")

        try:
            # Make API request
            params = {
                'l': league,
                'i': encoded_item,
            }

            response = self.get("api", params=params)

            # Parse response
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"[poeprices] API request failed: {e}")
            return PoePricesPrediction(
                min_price=0,
                max_price=0,
                currency="chaos",
                confidence_score=0,
                error_code=-1,
                error_msg=str(e),
                warning_msg="",
                mod_contributions=[],
            )

    def _parse_response(self, response: Dict[str, Any]) -> PoePricesPrediction:
        """
        Parse API response into PoePricesPrediction.

        Args:
            response: Raw API response dict

        Returns:
            PoePricesPrediction object
        """
        error_code = response.get('error', 0)
        error_msg = response.get('error_msg', '')

        # Handle errors
        if error_code != 0:
            logger.warning(f"[poeprices] API returned error {error_code}: {error_msg}")
            return PoePricesPrediction(
                min_price=0,
                max_price=0,
                currency="chaos",
                confidence_score=0,
                error_code=error_code,
                error_msg=error_msg,
                warning_msg=response.get('warning_msg', ''),
                mod_contributions=[],
            )

        # Parse mod contributions
        mod_contributions = []
        pred_explanation = response.get('pred_explanation', [])
        if pred_explanation:
            for item in pred_explanation:
                if isinstance(item, list) and len(item) >= 2:
                    mod_text = str(item[0])
                    contribution = float(item[1])
                    mod_contributions.append((mod_text, contribution))

        return PoePricesPrediction(
            min_price=float(response.get('min', 0)),
            max_price=float(response.get('max', 0)),
            currency=response.get('currency', 'chaos'),
            confidence_score=float(response.get('pred_confidence_score', 0)),
            error_code=0,
            error_msg='',
            warning_msg=response.get('warning_msg', ''),
            mod_contributions=mod_contributions,
        )

    def predict_price_from_parsed_item(
        self,
        parsed_item: Any,  # ParsedItem from item_parser
        league: Optional[str] = None,
    ) -> PoePricesPrediction:
        """
        Get price prediction for a ParsedItem.

        This reconstructs the item text format expected by poeprices.info.

        Args:
            parsed_item: ParsedItem instance
            league: League override

        Returns:
            PoePricesPrediction
        """
        # Reconstruct item text
        item_text = self._reconstruct_item_text(parsed_item)
        return self.predict_price(item_text, league)

    def _reconstruct_item_text(self, parsed_item: Any) -> str:
        """
        Reconstruct item text from ParsedItem for API submission.

        Args:
            parsed_item: ParsedItem instance

        Returns:
            Reconstructed item text string
        """
        lines = []

        # Item class (if available)
        if hasattr(parsed_item, 'item_class') and parsed_item.item_class:
            lines.append(f"Item Class: {parsed_item.item_class}")

        # Rarity
        if parsed_item.rarity:
            lines.append(f"Rarity: {parsed_item.rarity}")

        # Name and base type
        if parsed_item.name:
            lines.append(parsed_item.name)
        if parsed_item.base_type:
            lines.append(parsed_item.base_type)

        lines.append("--------")

        # Requirements (if available)
        if hasattr(parsed_item, 'requirements') and parsed_item.requirements:
            lines.append("Requirements:")
            for req_name, req_val in parsed_item.requirements.items():
                lines.append(f"{req_name}: {req_val}")
            lines.append("--------")

        # Item level
        if parsed_item.item_level:
            lines.append(f"Item Level: {parsed_item.item_level}")

        # Sockets
        if hasattr(parsed_item, 'sockets') and parsed_item.sockets:
            lines.append(f"Sockets: {parsed_item.sockets}")

        lines.append("--------")

        # Implicit mods
        if parsed_item.implicit_mods:
            for mod in parsed_item.implicit_mods:
                lines.append(mod)
            lines.append("--------")

        # Explicit mods
        if parsed_item.explicit_mods:
            for mod in parsed_item.explicit_mods:
                lines.append(mod)

        return "\n".join(lines)

    def get_top_contributing_mods(
        self,
        prediction: PoePricesPrediction,
        top_n: int = 5,
    ) -> List[tuple[str, float]]:
        """
        Get the top N mods contributing to price.

        Args:
            prediction: PoePricesPrediction with mod contributions
            top_n: Number of top mods to return

        Returns:
            List of (mod_text, contribution) sorted by contribution
        """
        if not prediction.mod_contributions:
            return []

        # Sort by absolute contribution value (can be negative)
        sorted_mods = sorted(
            prediction.mod_contributions,
            key=lambda x: abs(x[1]),
            reverse=True,
        )

        return sorted_mods[:top_n]


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    api = PoePricesAPI(league="Standard")

    print("=" * 60)
    print("POEPRICES.INFO API TEST")
    print("=" * 60)

    # Test with a rare item
    test_item = """Item Class: Body Armours
Rarity: Rare
Dread Shell
Vaal Regalia
--------
Quality: +20% (augmented)
Energy Shield: 437 (augmented)
--------
Requirements:
Level: 68
Int: 194
--------
Sockets: B-B-B-B-B-B
--------
Item Level: 86
--------
+87 to maximum Energy Shield
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+35% to Lightning Resistance
14% increased Stun and Block Recovery"""

    print("\n1. Testing price prediction...")
    print("Item: Vaal Regalia with Life + ES + Triple Res")

    try:
        prediction = api.predict_price(test_item)

        if prediction.is_valid:
            print("\n[OK] Prediction successful!")
            print(f"  Price range: {prediction.price_range_str}")
            print(f"  Average: {prediction.average_price:.2f} {prediction.currency}")
            print(f"  Confidence: {prediction.confidence_score:.1f}% ({prediction.confidence_tier})")

            print("\n  Top contributing mods:")
            top_mods = api.get_top_contributing_mods(prediction)
            for mod, contribution in top_mods:
                print(f"    {mod}: {contribution:.4f}")
        else:
            print("\n[FAIL] Prediction failed!")
            print(f"  Error code: {prediction.error_code}")
            print(f"  Error: {prediction.error_msg}")

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Total API requests: {api.request_count}")
    print(f"Cache size: {api.get_cache_size()}")

    api.close()
