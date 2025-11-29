"""
Price check worker for background item price lookups.
"""

from typing import TYPE_CHECKING, Tuple, List, Any

from gui_qt.workers.base_worker import BaseWorker

if TYPE_CHECKING:
    from core.app_context import AppContext


class PriceCheckWorker(BaseWorker):
    """
    Worker for running price checks in a background thread.

    Parses item text and fetches prices from the price service.
    Emits a tuple of (parsed_item, results) on success.
    """

    def __init__(self, ctx: "AppContext", item_text: str):
        """
        Initialize the price check worker.

        Args:
            ctx: Application context with parser and price service
            item_text: Raw item text to parse and price
        """
        super().__init__()
        self.ctx = ctx
        self.item_text = item_text

    def _execute(self) -> Tuple[Any, List[Any]]:
        """
        Parse the item and fetch prices.

        Returns:
            Tuple of (parsed_item, price_results)

        Raises:
            ValueError: If item text could not be parsed
        """
        # Parse item
        parsed = self.ctx.parser.parse(self.item_text)
        if not parsed:
            raise ValueError("Could not parse item text")

        # Check for cancellation before expensive operation
        if self.is_cancelled:
            raise InterruptedError("Price check cancelled")

        # Get prices (pass item text, not parsed object)
        results = self.ctx.price_service.check_item(self.item_text)

        return (parsed, results)
