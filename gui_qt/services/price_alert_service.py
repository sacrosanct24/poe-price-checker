"""
Price Alert Service - Background monitoring and notifications for price thresholds.

Provides automatic background checking of configured price alerts and emits
notifications when prices cross defined thresholds.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from core.app_context import AppContext

logger = logging.getLogger(__name__)


class PriceAlertService(QObject):
    """
    Background service for monitoring price alerts.

    Features:
    - Periodic checking of active price alerts
    - Configurable polling intervals (5-60 minutes)
    - Cooldown enforcement per alert
    - Signals for tray and toast notifications
    """

    # Emitted when an alert triggers: (alert_id, item_name, alert_type, threshold, current_price)
    alert_triggered = pyqtSignal(int, str, str, float, float)

    # Emitted when the alert list changes (add/remove/update)
    alerts_changed = pyqtSignal()

    # Emitted with status updates
    status_update = pyqtSignal(str)

    # Emitted when check cycle starts/ends
    check_started = pyqtSignal()
    check_finished = pyqtSignal()

    # Interval bounds (in milliseconds)
    MIN_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes
    MAX_INTERVAL_MS = 60 * 60 * 1000  # 60 minutes
    DEFAULT_INTERVAL_MS = 15 * 60 * 1000  # 15 minutes

    def __init__(
        self,
        ctx: "AppContext",
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the price alert service.

        Args:
            ctx: Application context with database, config, and price services.
            parent: Parent QObject for lifecycle management.
        """
        super().__init__(parent)

        self._ctx = ctx
        self._enabled = False
        self._check_timer: Optional[QTimer] = None
        self._interval_ms = self.DEFAULT_INTERVAL_MS
        self._is_checking = False

        # Cache of active alerts for quick lookup
        self._active_alerts: List[Dict[str, Any]] = []

        # Track last check time
        self._last_check: Optional[datetime] = None

        # Load config
        self._load_config()

    def _load_config(self) -> None:
        """Load alert settings from config."""
        try:
            config = self._ctx.config

            # Check if alerts are enabled
            self._enabled = getattr(config, 'alerts_enabled', True)

            # Get polling interval from config (in minutes)
            interval_minutes = getattr(config, 'alert_polling_interval_minutes', 15)
            self._interval_ms = max(
                self.MIN_INTERVAL_MS,
                min(interval_minutes * 60 * 1000, self.MAX_INTERVAL_MS)
            )

        except Exception as e:
            logger.warning(f"Failed to load alert config: {e}")

    def start(self) -> None:
        """Start the background alert checking service."""
        if not self._enabled:
            logger.info("Price alerts are disabled")
            return

        if self._check_timer is not None:
            logger.debug("Alert service already running")
            return

        # Load active alerts from database
        self._refresh_alert_cache()

        if not self._active_alerts:
            logger.info("No active alerts to monitor")
            return

        logger.info(
            f"Starting price alert service (interval: "
            f"{self._interval_ms // 60000} minutes, "
            f"{len(self._active_alerts)} active alerts)"
        )

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._on_check_timer)
        self._check_timer.start(self._interval_ms)

        # Record start time
        self._last_check = datetime.now()

        self.status_update.emit(
            f"Price alert monitoring started ({len(self._active_alerts)} alerts)"
        )

    def stop(self) -> None:
        """Stop the background alert checking service."""
        if self._check_timer is not None:
            self._check_timer.stop()
            self._check_timer.deleteLater()
            self._check_timer = None
            logger.info("Price alert service stopped")
            self.status_update.emit("Price alert monitoring stopped")

    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._check_timer is not None and self._check_timer.isActive()

    def is_checking(self) -> bool:
        """Check if an alert check is currently in progress."""
        return self._is_checking

    def get_last_check_time(self) -> Optional[datetime]:
        """Get the time of the last alert check."""
        return self._last_check

    def set_interval(self, minutes: int) -> None:
        """
        Set the checking interval.

        Args:
            minutes: Check interval in minutes (5-60).
        """
        self._interval_ms = max(
            self.MIN_INTERVAL_MS,
            min(minutes * 60 * 1000, self.MAX_INTERVAL_MS)
        )

        # Restart timer if running
        if self._check_timer is not None:
            self._check_timer.setInterval(self._interval_ms)

        logger.info(f"Alert check interval set to {minutes} minutes")

    def check_now(self) -> None:
        """Trigger an immediate alert check."""
        if self._is_checking:
            logger.debug("Alert check already in progress")
            return

        self._do_check()

    # ------------------------------------------------------------------
    # Alert CRUD Operations
    # ------------------------------------------------------------------

    def create_alert(
        self,
        item_name: str,
        alert_type: str,
        threshold_chaos: float,
        item_base_type: Optional[str] = None,
        cooldown_minutes: Optional[int] = None,
    ) -> int:
        """
        Create a new price alert.

        Args:
            item_name: Name of the item to monitor.
            alert_type: "above" or "below".
            threshold_chaos: Price threshold in chaos orbs.
            item_base_type: Optional base type for the item.
            cooldown_minutes: Minutes between triggers (uses default if None).

        Returns:
            ID of the created alert.
        """
        config = self._ctx.config
        game_version = config.current_game.value
        league = config.league

        if cooldown_minutes is None:
            cooldown_minutes = getattr(config, 'alert_default_cooldown_minutes', 30)

        alert_id = self._ctx.db.create_price_alert(
            item_name=item_name,
            league=league,
            game_version=game_version,
            alert_type=alert_type,
            threshold_chaos=threshold_chaos,
            item_base_type=item_base_type,
            cooldown_minutes=cooldown_minutes,
        )

        logger.info(
            f"Created price alert: {item_name} {alert_type} {threshold_chaos}c "
            f"(id={alert_id})"
        )

        self._refresh_alert_cache()
        self.alerts_changed.emit()

        # Start service if not running and this is the first alert
        if not self.is_running() and self._enabled:
            self.start()

        return alert_id

    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Get a single alert by ID."""
        return self._ctx.db.get_price_alert(alert_id)

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Get all alerts for the current league/game."""
        config = self._ctx.config
        return self._ctx.db.get_all_price_alerts(
            league=config.league,
            game_version=config.current_game.value,
        )

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get cached active alerts."""
        return self._active_alerts.copy()

    def update_alert(
        self,
        alert_id: int,
        threshold_chaos: Optional[float] = None,
        alert_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        cooldown_minutes: Optional[int] = None,
    ) -> bool:
        """Update an existing alert."""
        success = self._ctx.db.update_price_alert(
            alert_id,
            threshold_chaos=threshold_chaos,
            alert_type=alert_type,
            enabled=enabled,
            cooldown_minutes=cooldown_minutes,
        )

        if success:
            self._refresh_alert_cache()
            self.alerts_changed.emit()

            # Stop service if no more active alerts
            if not self._active_alerts and self.is_running():
                self.stop()

        return success

    def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert."""
        success = self._ctx.db.delete_price_alert(alert_id)

        if success:
            logger.info(f"Deleted price alert id={alert_id}")
            self._refresh_alert_cache()
            self.alerts_changed.emit()

            # Stop service if no more active alerts
            if not self._active_alerts and self.is_running():
                self.stop()

        return success

    def toggle_alert(self, alert_id: int) -> bool:
        """Toggle an alert's enabled state."""
        alert = self.get_alert(alert_id)
        if alert is None:
            return False

        new_state = not alert.get("enabled", True)
        return self.update_alert(alert_id, enabled=new_state)

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    def _refresh_alert_cache(self) -> None:
        """Refresh the cache of active alerts from the database."""
        try:
            config = self._ctx.config
            self._active_alerts = self._ctx.db.get_active_price_alerts(
                league=config.league,
                game_version=config.current_game.value,
            )
            logger.debug(f"Refreshed alert cache: {len(self._active_alerts)} active alerts")
        except Exception as e:
            logger.error(f"Failed to refresh alert cache: {e}")
            self._active_alerts = []

    def _on_check_timer(self) -> None:
        """Handle check timer tick."""
        self._do_check()

    def _do_check(self) -> None:
        """Perform the actual alert check."""
        if self._is_checking:
            return

        self._is_checking = True
        self.check_started.emit()

        try:
            # Refresh cache in case alerts were modified elsewhere
            self._refresh_alert_cache()

            if not self._active_alerts:
                logger.debug("No active alerts to check")
                return

            logger.debug(f"Checking {len(self._active_alerts)} price alerts...")

            triggered_count = 0
            for alert in self._active_alerts:
                try:
                    if self._check_single_alert(alert):
                        triggered_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to check alert for '{alert.get('item_name')}': {e}"
                    )

            self._last_check = datetime.now()

            if triggered_count > 0:
                logger.info(f"Triggered {triggered_count} price alerts")
                self.status_update.emit(f"Triggered {triggered_count} price alerts")
            else:
                logger.debug("No alerts triggered")

        except Exception as e:
            logger.error(f"Alert check failed: {e}")
            self.status_update.emit(f"Alert check failed: {e}")

        finally:
            self._is_checking = False
            self.check_finished.emit()

    def _check_single_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Check a single alert and trigger if conditions are met.

        Args:
            alert: Alert dict from database.

        Returns:
            True if alert triggered, False otherwise.
        """
        alert_id = alert.get("id")
        item_name = alert.get("item_name", "")
        alert_type = alert.get("alert_type", "")
        threshold = alert.get("threshold_chaos", 0.0)

        if not item_name or not alert_type:
            return False

        # Get current price
        current_price = self._get_item_price(item_name, alert.get("item_base_type"))
        if current_price is None:
            logger.debug(f"Could not get price for '{item_name}'")
            return False

        # Update last known price
        self._ctx.db._price_alert_repo.update_last_price(alert_id, current_price)

        # Check if should trigger (threshold + cooldown)
        if not self._ctx.db.should_alert_trigger(alert_id, current_price):
            return False

        # Record the trigger
        self._ctx.db.record_alert_trigger(alert_id, current_price)

        # Emit signal
        logger.info(
            f"Alert triggered: {item_name} is {current_price:.1f}c "
            f"({alert_type} {threshold:.1f}c)"
        )
        self.alert_triggered.emit(
            alert_id,
            item_name,
            alert_type,
            threshold,
            current_price,
        )

        return True

    def _get_item_price(
        self,
        item_name: str,
        item_base_type: Optional[str] = None,
    ) -> Optional[float]:
        """
        Get the current price for an item.

        Args:
            item_name: Item name.
            item_base_type: Optional base type.

        Returns:
            Price in chaos, or None if not found.
        """
        try:
            # Try poe.ninja / poe2.ninja first
            config = self._ctx.config
            game_version = config.current_game

            from core.game_version import GameVersion

            if game_version == GameVersion.POE2 and self._ctx.poe2_ninja:
                # Try currency first
                price, source = self._ctx.poe2_ninja.get_currency_price(item_name)
                if price > 0:
                    return price

                # Try item search
                result = self._ctx.poe2_ninja.find_item_price(item_name, item_base_type)
                if result:
                    return result.get("exaltedValue") or result.get("chaosValue")

            elif game_version == GameVersion.POE1 and self._ctx.poe_ninja:
                # Try currency first
                price = self._ctx.poe_ninja.get_currency_price(item_name)
                if price and price > 0:
                    return price

                # Try item search
                result = self._ctx.poe_ninja.find_item_price(item_name, item_base_type)
                if result:
                    return result.get("chaosValue")

        except Exception as e:
            logger.debug(f"Error getting price for '{item_name}': {e}")

        return None


# Singleton instance
_price_alert_service: Optional[PriceAlertService] = None


def get_price_alert_service(
    ctx: Optional["AppContext"] = None,
) -> Optional[PriceAlertService]:
    """
    Get the global price alert service instance.

    Args:
        ctx: Application context (required for first call).

    Returns:
        The price alert service, or None if not initialized.
    """
    global _price_alert_service

    if _price_alert_service is None and ctx is not None:
        _price_alert_service = PriceAlertService(ctx)

    return _price_alert_service


def shutdown_price_alert_service() -> None:
    """Shutdown the global price alert service."""
    global _price_alert_service

    if _price_alert_service is not None:
        _price_alert_service.stop()
        _price_alert_service = None
