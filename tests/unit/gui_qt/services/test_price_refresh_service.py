"""Tests for gui_qt/services/price_refresh_service.py - Background price refresh."""

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import pytest

from gui_qt.services.price_refresh_service import (
    PriceRefreshService,
    get_price_refresh_service,
    shutdown_price_refresh_service,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.config.background_refresh_enabled = True
    ctx.config.price_refresh_interval_minutes = 30
    ctx.config.price_change_threshold = 0.10
    ctx.poe_ninja = MagicMock()
    ctx.poe_watch = MagicMock()
    return ctx


@pytest.fixture
def service(mock_ctx, qapp):
    """Create PriceRefreshService instance."""
    return PriceRefreshService(mock_ctx)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    shutdown_price_refresh_service()
    yield
    shutdown_price_refresh_service()


class TestPriceRefreshServiceInit:
    """Tests for PriceRefreshService initialization."""

    def test_init_with_defaults(self, mock_ctx, qapp):
        """Should initialize with default values."""
        service = PriceRefreshService(mock_ctx)

        assert service._enabled is True
        assert service._is_refreshing is False
        assert service._last_refresh is None
        assert service._watched_items == {}
        assert service._change_threshold == 0.10

    def test_init_loads_disabled_config(self, mock_ctx, qapp):
        """Should load disabled state from config."""
        mock_ctx.config.background_refresh_enabled = False

        service = PriceRefreshService(mock_ctx)

        assert service._enabled is False

    def test_init_loads_custom_interval(self, mock_ctx, qapp):
        """Should load custom refresh interval."""
        mock_ctx.config.price_refresh_interval_minutes = 60

        service = PriceRefreshService(mock_ctx)

        assert service._refresh_interval_ms == 60 * 60 * 1000

    def test_init_clamps_interval_minimum(self, mock_ctx, qapp):
        """Should clamp interval to minimum."""
        mock_ctx.config.price_refresh_interval_minutes = 1  # Too short

        service = PriceRefreshService(mock_ctx)

        assert service._refresh_interval_ms >= service.MIN_REFRESH_INTERVAL_MS

    def test_init_clamps_interval_maximum(self, mock_ctx, qapp):
        """Should clamp interval to maximum."""
        mock_ctx.config.price_refresh_interval_minutes = 500  # Too long

        service = PriceRefreshService(mock_ctx)

        assert service._refresh_interval_ms <= service.MAX_REFRESH_INTERVAL_MS

    def test_init_handles_config_error(self, mock_ctx, qapp):
        """Should handle config errors gracefully."""
        # Simulate error when accessing config
        type(mock_ctx).config = property(lambda self: (_ for _ in ()).throw(RuntimeError("Config error")))

        # Should not raise
        service = PriceRefreshService(mock_ctx)
        assert service._enabled is False  # Falls back to initial False


class TestPriceRefreshServiceLifecycle:
    """Tests for service start/stop lifecycle."""

    def test_start_creates_timer(self, service, qapp):
        """Starting should create and start timer."""
        service.start()

        assert service._refresh_timer is not None
        assert service._last_refresh is not None
        service.stop()

    def test_start_when_disabled_does_nothing(self, mock_ctx, qapp):
        """Starting when disabled should do nothing."""
        mock_ctx.config.background_refresh_enabled = False
        service = PriceRefreshService(mock_ctx)

        service.start()

        assert service._refresh_timer is None

    def test_start_twice_no_duplicate(self, service, qapp):
        """Starting twice should not create duplicate timer."""
        service.start()
        first_timer = service._refresh_timer

        service.start()

        assert service._refresh_timer is first_timer
        service.stop()

    def test_stop_clears_timer(self, service, qapp):
        """Stopping should clear timer."""
        service.start()
        assert service._refresh_timer is not None

        service.stop()

        assert service._refresh_timer is None

    def test_is_running(self, service, qapp):
        """is_running should reflect timer state."""
        assert service.is_running() is False

        service.start()
        assert service.is_running() is True

        service.stop()
        assert service.is_running() is False


class TestPriceRefreshServiceStatus:
    """Tests for status and timing methods."""

    def test_is_refreshing_initial(self, service):
        """Initially should not be refreshing."""
        assert service.is_refreshing() is False

    def test_get_last_refresh_time_initial(self, service):
        """Initially should have no last refresh time."""
        assert service.get_last_refresh_time() is None

    def test_get_last_refresh_time_after_start(self, service, qapp):
        """After start should have last refresh time."""
        service.start()

        assert service.get_last_refresh_time() is not None
        service.stop()

    def test_get_time_until_next_refresh_when_stopped(self, service):
        """Should return None when timer not running."""
        result = service.get_time_until_next_refresh()
        assert result is None

    def test_get_time_until_next_refresh_when_running(self, service, qapp):
        """Should return time delta when running."""
        service.start()

        result = service.get_time_until_next_refresh()

        assert result is not None
        assert isinstance(result, timedelta)
        service.stop()


class TestPriceRefreshServiceInterval:
    """Tests for interval configuration."""

    def test_set_refresh_interval(self, service):
        """Should update interval."""
        service.set_refresh_interval(45)

        assert service._refresh_interval_ms == 45 * 60 * 1000

    def test_set_refresh_interval_clamps_minimum(self, service):
        """Should clamp to minimum."""
        service.set_refresh_interval(1)

        assert service._refresh_interval_ms >= service.MIN_REFRESH_INTERVAL_MS

    def test_set_refresh_interval_clamps_maximum(self, service):
        """Should clamp to maximum."""
        service.set_refresh_interval(1000)

        assert service._refresh_interval_ms <= service.MAX_REFRESH_INTERVAL_MS

    def test_set_refresh_interval_updates_running_timer(self, service, qapp):
        """Should update running timer."""
        service.start()

        service.set_refresh_interval(45)

        assert service._refresh_timer is not None
        service.stop()


class TestPriceRefreshServiceWatchedItems:
    """Tests for watched items functionality."""

    def test_watch_item(self, service):
        """Should add item to watch list."""
        service.watch_item("Headhunter", 150.0)

        assert "Headhunter" in service._watched_items
        assert service._watched_items["Headhunter"] == 150.0

    def test_watch_item_update(self, service):
        """Should update existing watch."""
        service.watch_item("Headhunter", 150.0)
        service.watch_item("Headhunter", 200.0)

        assert service._watched_items["Headhunter"] == 200.0

    def test_unwatch_item(self, service):
        """Should remove item from watch list."""
        service.watch_item("Headhunter", 150.0)
        service.unwatch_item("Headhunter")

        assert "Headhunter" not in service._watched_items

    def test_unwatch_item_nonexistent(self, service):
        """Should handle unwatching nonexistent item."""
        # Should not raise
        service.unwatch_item("Nonexistent")

    def test_clear_watched_items(self, service):
        """Should clear all watched items."""
        service.watch_item("Item1", 100.0)
        service.watch_item("Item2", 200.0)

        service.clear_watched_items()

        assert service._watched_items == {}


class TestPriceRefreshServiceRefresh:
    """Tests for refresh functionality."""

    def test_refresh_now_when_not_refreshing(self, service, mock_ctx):
        """refresh_now should trigger refresh."""
        service.refresh_now()

        # Should have attempted to clear caches
        mock_ctx.poe_ninja.clear_cache.assert_called_once()
        mock_ctx.poe_watch.clear_cache.assert_called_once()

    def test_refresh_now_when_already_refreshing(self, service, mock_ctx):
        """refresh_now should skip if already refreshing."""
        service._is_refreshing = True

        service.refresh_now()

        # Should not have attempted to clear caches
        mock_ctx.poe_ninja.clear_cache.assert_not_called()

    def test_do_refresh_sets_flags(self, service, mock_ctx):
        """_do_refresh should manage is_refreshing flag."""
        service._do_refresh()

        # Should have reset flag after completion
        assert service._is_refreshing is False

    def test_do_refresh_updates_last_refresh(self, service, mock_ctx):
        """_do_refresh should update last_refresh time."""
        service._do_refresh()

        assert service._last_refresh is not None

    def test_do_refresh_handles_poe_ninja_error(self, service, mock_ctx):
        """_do_refresh should handle poe.ninja errors."""
        mock_ctx.poe_ninja.clear_cache.side_effect = Exception("API error")

        # Should not raise
        service._do_refresh()

        assert service._is_refreshing is False

    def test_do_refresh_handles_poe_watch_error(self, service, mock_ctx):
        """_do_refresh should handle poe.watch errors."""
        mock_ctx.poe_watch.clear_cache.side_effect = Exception("API error")

        # Should not raise
        service._do_refresh()

        assert service._is_refreshing is False

    def test_do_refresh_handles_no_poe_ninja(self, mock_ctx, qapp):
        """_do_refresh should handle missing poe.ninja."""
        mock_ctx.poe_ninja = None
        service = PriceRefreshService(mock_ctx)

        # Should not raise
        service._do_refresh()


class TestPriceRefreshServicePriceChanges:
    """Tests for price change detection."""

    def test_check_price_changes_empty_watch_list(self, service, mock_ctx):
        """Should do nothing with empty watch list."""
        service._check_price_changes()

        mock_ctx.poe_ninja.find_item_price.assert_not_called()

    def test_check_price_changes_detects_increase(self, service, mock_ctx):
        """Should detect significant price increase."""
        service.watch_item("Test Item", 100.0)
        mock_ctx.poe_ninja.find_item_price.return_value = 120.0  # 20% increase

        # Connect signal to capture emission
        signal_received = []
        service.price_changed.connect(
            lambda name, old, new: signal_received.append((name, old, new))
        )

        service._check_price_changes()

        # Should have emitted price_changed signal
        assert len(signal_received) == 1
        assert signal_received[0] == ("Test Item", 100.0, 120.0)

    def test_check_price_changes_ignores_small_change(self, service, mock_ctx):
        """Should ignore changes below threshold."""
        service.watch_item("Test Item", 100.0)
        mock_ctx.poe_ninja.find_item_price.return_value = 105.0  # 5% increase

        signal_received = []
        service.price_changed.connect(
            lambda name, old, new: signal_received.append((name, old, new))
        )

        service._check_price_changes()

        # Should not have emitted signal
        assert len(signal_received) == 0

    def test_check_price_changes_updates_watched_price(self, service, mock_ctx):
        """Should update watched price after check."""
        service.watch_item("Test Item", 100.0)
        mock_ctx.poe_ninja.find_item_price.return_value = 120.0

        service._check_price_changes()

        assert service._watched_items["Test Item"] == 120.0

    def test_check_price_changes_handles_none_price(self, service, mock_ctx):
        """Should handle None price gracefully."""
        service.watch_item("Test Item", 100.0)
        mock_ctx.poe_ninja.find_item_price.return_value = None

        # Should not raise
        service._check_price_changes()

        # Price should not be updated
        assert service._watched_items["Test Item"] == 100.0

    def test_check_price_changes_handles_error(self, service, mock_ctx):
        """Should handle errors gracefully."""
        service.watch_item("Test Item", 100.0)
        mock_ctx.poe_ninja.find_item_price.side_effect = Exception("API error")

        # Should not raise
        service._check_price_changes()

    def test_check_price_changes_no_poe_ninja(self, mock_ctx, qapp):
        """Should handle missing poe.ninja."""
        mock_ctx.poe_ninja = None
        service = PriceRefreshService(mock_ctx)
        service.watch_item("Test Item", 100.0)

        # Should not raise
        service._check_price_changes()


class TestPriceRefreshServiceSingleton:
    """Tests for singleton functions."""

    def test_get_price_refresh_service_creates_instance(self, mock_ctx, qapp):
        """Should create instance on first call with ctx."""
        service = get_price_refresh_service(mock_ctx)

        assert service is not None
        assert isinstance(service, PriceRefreshService)

    def test_get_price_refresh_service_returns_same_instance(self, mock_ctx, qapp):
        """Should return same instance on subsequent calls."""
        service1 = get_price_refresh_service(mock_ctx)
        service2 = get_price_refresh_service()

        assert service1 is service2

    def test_get_price_refresh_service_none_without_init(self, qapp):
        """Should return None if not initialized."""
        service = get_price_refresh_service()

        assert service is None

    def test_shutdown_price_refresh_service(self, mock_ctx, qapp):
        """Should shutdown and clear singleton."""
        service = get_price_refresh_service(mock_ctx)
        service.start()

        shutdown_price_refresh_service()

        # Should have stopped timer
        assert service._refresh_timer is None

        # Should return None now
        assert get_price_refresh_service() is None


class TestPriceRefreshServiceSignals:
    """Tests for signal emissions."""

    def test_emits_status_update_on_start(self, service, qapp):
        """Should emit status_update when starting."""
        signal_received = []
        service.status_update.connect(signal_received.append)

        service.start()

        assert any("started" in msg.lower() for msg in signal_received)
        service.stop()

    def test_emits_status_update_on_stop(self, service, qapp):
        """Should emit status_update when stopping."""
        service.start()

        signal_received = []
        service.status_update.connect(signal_received.append)

        service.stop()

        assert any("stopped" in msg.lower() for msg in signal_received)

    def test_emits_refresh_started_on_refresh(self, service, mock_ctx):
        """Should emit refresh_started when refreshing."""
        signal_received = []
        service.refresh_started.connect(lambda: signal_received.append(True))

        service.refresh_now()

        assert len(signal_received) == 1

    def test_emits_refresh_finished_on_refresh(self, service, mock_ctx):
        """Should emit refresh_finished when done."""
        signal_received = []
        service.refresh_finished.connect(lambda: signal_received.append(True))

        service.refresh_now()

        assert len(signal_received) == 1

    def test_emits_prices_refreshed_on_success(self, service, mock_ctx):
        """Should emit prices_refreshed on successful refresh."""
        signal_received = []
        service.prices_refreshed.connect(lambda: signal_received.append(True))

        service.refresh_now()

        assert len(signal_received) == 1
