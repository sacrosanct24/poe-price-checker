"""
Price Refresh Service - Background price updates.

Provides automatic background refresh of price data from poe.ninja and poe.watch,
keeping the cache fresh without user intervention.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class PriceRefreshService(QObject):
    """
    Background service for refreshing price data.

    Features:
    - Periodic refresh of poe.ninja/poe.watch caches
    - Configurable refresh intervals
    - Price change detection and notifications
    - Adaptive refresh based on volatility
    """

    # Emitted when prices are refreshed
    prices_refreshed = pyqtSignal()

    # Emitted when a significant price change is detected
    price_changed = pyqtSignal(str, float, float)  # item_name, old_price, new_price

    # Emitted with refresh status updates
    status_update = pyqtSignal(str)  # message

    # Emitted when refresh starts/ends
    refresh_started = pyqtSignal()
    refresh_finished = pyqtSignal()

    # Default intervals (in milliseconds)
    DEFAULT_REFRESH_INTERVAL_MS = 30 * 60 * 1000  # 30 minutes
    MIN_REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes minimum
    MAX_REFRESH_INTERVAL_MS = 4 * 60 * 60 * 1000  # 4 hours maximum

    def __init__(
        self,
        ctx: "AppContext",
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the price refresh service.

        Args:
            ctx: Application context with price service and config.
            parent: Parent QObject for lifecycle management.
        """
        super().__init__(parent)

        self._ctx = ctx
        self._enabled = False
        self._refresh_timer: Optional[QTimer] = None
        self._refresh_interval_ms = self.DEFAULT_REFRESH_INTERVAL_MS
        self._is_refreshing = False

        # Track last refresh time
        self._last_refresh: Optional[datetime] = None

        # Track watched items for price change detection
        self._watched_items: Dict[str, float] = {}  # item_name -> last_known_price

        # Price change threshold (10% by default)
        self._change_threshold = 0.10

        # Load config
        self._load_config()

    def _load_config(self) -> None:
        """Load refresh settings from config."""
        try:
            config = self._ctx.config

            # Check if refresh is enabled
            self._enabled = getattr(config, 'background_refresh_enabled', True)

            # Get refresh interval from config (in minutes)
            interval_minutes = getattr(config, 'price_refresh_interval_minutes', 30)
            self._refresh_interval_ms = max(
                self.MIN_REFRESH_INTERVAL_MS,
                min(interval_minutes * 60 * 1000, self.MAX_REFRESH_INTERVAL_MS)
            )

            # Price change threshold
            self._change_threshold = getattr(config, 'price_change_threshold', 0.10)

        except Exception as e:
            logger.warning(f"Failed to load refresh config: {e}")

    def start(self) -> None:
        """Start the background refresh service."""
        if not self._enabled:
            logger.info("Background price refresh is disabled")
            return

        if self._refresh_timer is not None:
            logger.debug("Refresh service already running")
            return

        logger.info(
            f"Starting price refresh service (interval: "
            f"{self._refresh_interval_ms // 60000} minutes)"
        )

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh_timer)
        self._refresh_timer.start(self._refresh_interval_ms)

        # Record start time
        self._last_refresh = datetime.now()

        self.status_update.emit("Background price refresh started")

    def stop(self) -> None:
        """Stop the background refresh service."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer.deleteLater()
            self._refresh_timer = None
            logger.info("Price refresh service stopped")
            self.status_update.emit("Background price refresh stopped")

    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._refresh_timer is not None and self._refresh_timer.isActive()

    def is_refreshing(self) -> bool:
        """Check if a refresh is currently in progress."""
        return self._is_refreshing

    def get_last_refresh_time(self) -> Optional[datetime]:
        """Get the time of the last successful refresh."""
        return self._last_refresh

    def get_time_until_next_refresh(self) -> Optional[timedelta]:
        """Get time until the next scheduled refresh."""
        if self._refresh_timer is None or self._last_refresh is None:
            return None

        next_refresh = self._last_refresh + timedelta(
            milliseconds=self._refresh_interval_ms
        )
        return max(timedelta(0), next_refresh - datetime.now())

    def set_refresh_interval(self, minutes: int) -> None:
        """
        Set the refresh interval.

        Args:
            minutes: Refresh interval in minutes.
        """
        self._refresh_interval_ms = max(
            self.MIN_REFRESH_INTERVAL_MS,
            min(minutes * 60 * 1000, self.MAX_REFRESH_INTERVAL_MS)
        )

        # Restart timer if running
        if self._refresh_timer is not None:
            self._refresh_timer.setInterval(self._refresh_interval_ms)

        logger.info(f"Refresh interval set to {minutes} minutes")

    def refresh_now(self) -> None:
        """Trigger an immediate refresh."""
        if self._is_refreshing:
            logger.debug("Refresh already in progress")
            return

        self._do_refresh()

    def watch_item(self, item_name: str, current_price: float) -> None:
        """
        Add an item to the watch list for price change detection.

        Args:
            item_name: Name of the item to watch.
            current_price: Current known price.
        """
        self._watched_items[item_name] = current_price

    def unwatch_item(self, item_name: str) -> None:
        """Remove an item from the watch list."""
        self._watched_items.pop(item_name, None)

    def clear_watched_items(self) -> None:
        """Clear all watched items."""
        self._watched_items.clear()

    def _on_refresh_timer(self) -> None:
        """Handle refresh timer tick."""
        self._do_refresh()

    def _do_refresh(self) -> None:
        """Perform the actual refresh."""
        if self._is_refreshing:
            return

        self._is_refreshing = True
        self.refresh_started.emit()
        self.status_update.emit("Refreshing prices...")

        try:
            # Refresh poe.ninja cache
            if self._ctx.poe_ninja:
                logger.debug("Refreshing poe.ninja prices...")
                try:
                    # Force cache refresh by calling with fresh=True if available
                    # Otherwise just let normal cache expiry handle it
                    self._ctx.poe_ninja.clear_cache()
                except Exception as e:
                    logger.warning(f"Failed to clear poe.ninja cache: {e}")

            # Refresh poe.watch cache
            if self._ctx.poe_watch:
                logger.debug("Refreshing poe.watch prices...")
                try:
                    self._ctx.poe_watch.clear_cache()
                except Exception as e:
                    logger.warning(f"Failed to clear poe.watch cache: {e}")

            # Check watched items for price changes
            self._check_price_changes()

            self._last_refresh = datetime.now()
            logger.info("Price refresh completed")
            self.status_update.emit(
                f"Prices refreshed at {self._last_refresh.strftime('%H:%M')}"
            )
            self.prices_refreshed.emit()

        except Exception as e:
            logger.error(f"Price refresh failed: {e}")
            self.status_update.emit(f"Price refresh failed: {e}")

        finally:
            self._is_refreshing = False
            self.refresh_finished.emit()

    def _check_price_changes(self) -> None:
        """Check watched items for significant price changes."""
        if not self._watched_items or not self._ctx.poe_ninja:
            return

        for item_name, old_price in list(self._watched_items.items()):
            try:
                # Try to get new price
                new_price = self._ctx.poe_ninja.find_item_price(item_name)
                if new_price is None:
                    continue

                # Check for significant change
                if old_price > 0:
                    change_pct = abs(new_price - old_price) / old_price
                    if change_pct >= self._change_threshold:
                        logger.info(
                            f"Price change detected for '{item_name}': "
                            f"{old_price:.1f}c -> {new_price:.1f}c ({change_pct:.1%})"
                        )
                        self.price_changed.emit(item_name, old_price, new_price)

                # Update tracked price
                self._watched_items[item_name] = new_price

            except Exception as e:
                logger.debug(f"Failed to check price for '{item_name}': {e}")


# Singleton instance
_price_refresh_service: Optional[PriceRefreshService] = None


def get_price_refresh_service(
    ctx: Optional["AppContext"] = None,
) -> Optional[PriceRefreshService]:
    """
    Get the global price refresh service instance.

    Args:
        ctx: Application context (required for first call).

    Returns:
        The price refresh service, or None if not initialized.
    """
    global _price_refresh_service

    if _price_refresh_service is None and ctx is not None:
        _price_refresh_service = PriceRefreshService(ctx)

    return _price_refresh_service


def shutdown_price_refresh_service() -> None:
    """Shutdown the global price refresh service."""
    global _price_refresh_service

    if _price_refresh_service is not None:
        _price_refresh_service.stop()
        _price_refresh_service = None
