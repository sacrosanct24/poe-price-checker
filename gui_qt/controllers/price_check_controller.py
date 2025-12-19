"""
gui_qt.controllers.price_check_controller - Coordinates price checking workflow.

Extracts price checking business logic from main_window.py to:
- Reduce main window complexity
- Enable easier testing
- Separate concerns (parsing, pricing, formatting)

Usage:
    controller = PriceCheckController(
        parser=ctx.parser,
        price_service=ctx.price_service,
        rare_evaluator=evaluator,
    )

    # Check price and get formatted results
    result = controller.check_price(item_text)
    if result.is_ok():
        data = result.unwrap()
        # data.parsed_item, data.results, data.evaluation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.result import Result, Ok, Err

if TYPE_CHECKING:
    from core.interfaces import IItemParser, IPriceService
    from core.rare_evaluation import RareItemEvaluator, RareItemEvaluation
    from core.item_parser import ParsedItem

logger = logging.getLogger(__name__)


@dataclass
class PriceCheckResult:
    """Result of a price check operation.

    Attributes:
        parsed_item: The parsed item from item text
        results: List of price results from various sources
        formatted_rows: Results formatted for display in table
        evaluation: Optional rare item evaluation (if rare item)
        is_rare: Whether the item is rare (and has evaluation)
    """
    parsed_item: 'ParsedItem'
    results: List[Dict[str, Any]]
    formatted_rows: List[Dict[str, Any]] = field(default_factory=list)
    evaluation: Optional['RareItemEvaluation'] = None
    is_rare: bool = False

    @property
    def best_price(self) -> float:
        """Get the highest chaos value from results."""
        if not self.results:
            return 0.0
        return max(
            (r.get("chaos_value", 0) or 0)
            for r in self.results
        )

    @property
    def result_count(self) -> int:
        """Get number of price results."""
        return len(self.results)


class PriceCheckController:
    """
    Controller for price checking workflow.

    Coordinates parsing, pricing, and result formatting without
    depending on UI components. This enables:
    - Unit testing without Qt
    - Reuse in non-GUI contexts
    - Clear separation of concerns

    Signals/Slots:
        None - pure business logic class. Use Qt signals in the
        calling widget if needed.
    """

    def __init__(
        self,
        parser: 'IItemParser',
        price_service: 'IPriceService',
        rare_evaluator: Optional['RareItemEvaluator'] = None,
        upgrade_checker: Optional[Any] = None,
    ):
        """
        Initialize the controller.

        Args:
            parser: Item parser service
            price_service: Price lookup service
            rare_evaluator: Optional rare item evaluator
            upgrade_checker: Optional upgrade checker for PoB integration
        """
        self._parser = parser
        self._price_service = price_service
        self._rare_evaluator = rare_evaluator
        self._upgrade_checker = upgrade_checker

    def set_upgrade_checker(self, checker: Optional[Any]) -> None:
        """Set or update the upgrade checker."""
        self._upgrade_checker = checker

    def set_rare_evaluator(self, evaluator: Optional['RareItemEvaluator']) -> None:
        """Set or update the rare item evaluator."""
        self._rare_evaluator = evaluator

    def check_price(self, item_text: str) -> Result[PriceCheckResult, str]:
        """
        Perform a complete price check on item text.

        Args:
            item_text: Raw item text from game (Ctrl+C)

        Returns:
            Result containing PriceCheckResult on success, error message on failure
        """
        if not item_text or not item_text.strip():
            return Err("No item text provided")

        # Parse item
        try:
            parsed = self._parser.parse(item_text)
            if not parsed:
                return Err("Could not parse item text")
        except Exception as e:
            logger.exception("Item parsing failed")
            return Err(f"Parse error: {e}")

        # Get prices
        try:
            results = self._price_service.check_item(item_text)
        except Exception as e:
            logger.exception("Price lookup failed")
            return Err(f"Price lookup error: {e}")

        # Format results for display
        formatted_rows = self._format_results(parsed, results)

        # Evaluate rare items
        evaluation = None
        is_rare = parsed.rarity == "Rare"
        if is_rare and self._rare_evaluator:
            try:
                evaluation = self._rare_evaluator.evaluate(parsed)
            except Exception as e:
                logger.warning(f"Rare evaluation failed: {e}")

        return Ok(PriceCheckResult(
            parsed_item=parsed,
            results=results,
            formatted_rows=formatted_rows,
            evaluation=evaluation,
            is_rare=is_rare,
        ))

    def _format_results(
        self,
        parsed: 'ParsedItem',
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format price results for table display.

        Args:
            parsed: Parsed item
            results: Raw price results

        Returns:
            List of formatted row dictionaries
        """
        formatted = []

        for result in results:
            # Handle explanation - could be dict or object
            explanation = result.get("explanation")
            if explanation:
                if isinstance(explanation, dict):
                    explanation_str = json.dumps(explanation)
                elif hasattr(explanation, "__dict__"):
                    explanation_str = json.dumps(explanation.__dict__)
                else:
                    explanation_str = str(explanation)
            else:
                explanation_str = ""

            # Convert numeric values safely
            chaos_val = self._safe_float(result.get("chaos_value"))
            divine_val = self._safe_float(result.get("divine_value"))
            listing_count = self._safe_int(result.get("listing_count"))

            row = {
                "item_name": result.get("item_name") or parsed.name or "",
                "variant": result.get("variant") or "",
                "links": result.get("links") or "",
                "chaos_value": chaos_val,
                "divine_value": divine_val,
                "listing_count": listing_count,
                "source": result.get("source") or "",
                "upgrade": "",
                "price_explanation": explanation_str,
                "_item": parsed,  # Store for tooltip preview
            }

            # Check for upgrade potential
            if self._upgrade_checker and hasattr(parsed, 'slot'):
                try:
                    is_upgrade = self._upgrade_checker.is_upgrade(parsed)
                    if is_upgrade:
                        row["upgrade"] = "Yes"
                except Exception as e:
                    logger.debug(f"Upgrade check failed: {e}")

            formatted.append(row)

        return formatted

    @staticmethod
    def _safe_float(value: Any) -> float:
        """Safely convert value to float."""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        """Safely convert value to int."""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def parse_item(self, item_text: str) -> Result['ParsedItem', str]:
        """
        Parse item text without price checking.

        Useful for updating item inspector without full price check.

        Args:
            item_text: Raw item text

        Returns:
            Result containing ParsedItem or error message
        """
        if not item_text or not item_text.strip():
            return Err("No item text provided")

        try:
            parsed = self._parser.parse(item_text)
            if not parsed:
                return Err("Could not parse item text")
            return Ok(parsed)
        except Exception as e:
            logger.exception("Item parsing failed")
            return Err(f"Parse error: {e}")

    def evaluate_rare(
        self,
        parsed: 'ParsedItem'
    ) -> Result['RareItemEvaluation', str]:
        """
        Evaluate a rare item.

        Args:
            parsed: Parsed item to evaluate

        Returns:
            Result containing evaluation or error message
        """
        if not self._rare_evaluator:
            return Err("Rare evaluator not available")

        if parsed.rarity != "Rare":
            return Err("Item is not rare")

        try:
            evaluation = self._rare_evaluator.evaluate(parsed)
            return Ok(evaluation)
        except Exception as e:
            logger.exception("Rare evaluation failed")
            return Err(f"Evaluation error: {e}")

    def get_price_summary(self, result: PriceCheckResult) -> str:
        """
        Get a summary string for a price check result.

        Args:
            result: Price check result

        Returns:
            Summary string like "Found 3 price result(s)"
        """
        count = result.result_count
        if count == 0:
            return "No prices found"
        elif count == 1:
            return "Found 1 price result"
        else:
            return f"Found {count} price result(s)"

    def should_show_toast(self, result: PriceCheckResult) -> tuple[bool, str, str]:
        """
        Determine if a toast notification should be shown.

        Args:
            result: Price check result

        Returns:
            Tuple of (should_show, toast_type, message)
            toast_type is "success", "info", or "warning"
        """
        if not result.results:
            return False, "", ""

        best_price = result.best_price
        if best_price >= 100:
            return True, "success", f"High value item: {best_price:.0f}c"
        elif best_price >= 10:
            return True, "info", f"Found {result.result_count} result(s)"

        return False, "", ""
