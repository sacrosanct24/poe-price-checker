"""Tests for gui_qt/services/price_alert_service.py - Price alert monitoring."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from gui_qt.services.price_alert_service import (
    PriceAlertService,
    get_price_alert_service,
    shutdown_price_alert_service,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_ctx():
    """Create mock AppContext."""
    ctx = MagicMock()

    # Mock config
    ctx.config = MagicMock()
    ctx.config.alerts_enabled = True
    ctx.config.alert_polling_interval_minutes = 15
    ctx.config.alert_default_cooldown_minutes = 30
    ctx.config.league = "Settlers"
    ctx.config.current_game = MagicMock()
    ctx.config.current_game.value = "poe1"

    # Mock database
    ctx.db = MagicMock()
    ctx.db.get_active_price_alerts.return_value = []
    ctx.db.get_all_price_alerts.return_value = []
    ctx.db.create_price_alert.return_value = 1
    ctx.db.get_price_alert.return_value = None
    ctx.db.update_price_alert.return_value = True
    ctx.db.delete_price_alert.return_value = True
    ctx.db.should_alert_trigger.return_value = False
    ctx.db.record_alert_trigger.return_value = True
    ctx.db._price_alert_repo = MagicMock()

    # Mock poe.ninja
    ctx.poe_ninja = MagicMock()
    ctx.poe_ninja.get_currency_price.return_value = None
    ctx.poe_ninja.find_item_price.return_value = None

    # Mock poe2.ninja
    ctx.poe2_ninja = MagicMock()
    ctx.poe2_ninja.get_currency_price.return_value = (0, None)
    ctx.poe2_ninja.find_item_price.return_value = None

    return ctx


@pytest.fixture
def service(mock_ctx, qapp):
    """Create PriceAlertService instance."""
    return PriceAlertService(mock_ctx)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    shutdown_price_alert_service()
    yield
    shutdown_price_alert_service()


class TestPriceAlertServiceInit:
    """Tests for PriceAlertService initialization."""

    def test_init_with_defaults(self, mock_ctx, qapp):
        """Should initialize with default values."""
        service = PriceAlertService(mock_ctx)

        assert service._enabled is True
        assert service._is_checking is False
        assert service._last_check is None
        assert service._active_alerts == []
        assert service._check_timer is None

    def test_init_loads_disabled_config(self, mock_ctx, qapp):
        """Should load disabled state from config."""
        mock_ctx.config.alerts_enabled = False

        service = PriceAlertService(mock_ctx)

        assert service._enabled is False

    def test_init_loads_custom_interval(self, mock_ctx, qapp):
        """Should load custom check interval from config."""
        mock_ctx.config.alert_polling_interval_minutes = 30

        service = PriceAlertService(mock_ctx)

        assert service._interval_ms == 30 * 60 * 1000

    def test_init_clamps_interval_minimum(self, mock_ctx, qapp):
        """Should clamp interval to minimum."""
        mock_ctx.config.alert_polling_interval_minutes = 1  # Too short

        service = PriceAlertService(mock_ctx)

        assert service._interval_ms >= service.MIN_INTERVAL_MS

    def test_init_clamps_interval_maximum(self, mock_ctx, qapp):
        """Should clamp interval to maximum."""
        mock_ctx.config.alert_polling_interval_minutes = 120  # Too long

        service = PriceAlertService(mock_ctx)

        assert service._interval_ms <= service.MAX_INTERVAL_MS

    def test_init_handles_missing_config_attrs(self, mock_ctx, qapp):
        """Should handle missing config attributes."""
        # Remove config attrs to use defaults
        del mock_ctx.config.alerts_enabled
        del mock_ctx.config.alert_polling_interval_minutes

        service = PriceAlertService(mock_ctx)

        # Should use defaults
        assert service._enabled is True
        assert service._interval_ms == service.DEFAULT_INTERVAL_MS


class TestPriceAlertServiceLifecycle:
    """Tests for service start/stop lifecycle."""

    def test_start_with_no_alerts_does_nothing(self, service, mock_ctx, qapp):
        """Starting with no alerts should not create timer."""
        mock_ctx.db.get_active_price_alerts.return_value = []

        service.start()

        assert service._check_timer is None

    def test_start_with_alerts_creates_timer(self, service, mock_ctx, qapp):
        """Starting with alerts should create and start timer."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test Item", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.start()

        assert service._check_timer is not None
        assert service._last_check is not None
        service.stop()

    def test_start_when_disabled_does_nothing(self, mock_ctx, qapp):
        """Starting when disabled should do nothing."""
        mock_ctx.config.alerts_enabled = False
        service = PriceAlertService(mock_ctx)

        service.start()

        assert service._check_timer is None

    def test_start_twice_no_duplicate(self, service, mock_ctx, qapp):
        """Starting twice should not create duplicate timer."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.start()
        first_timer = service._check_timer

        service.start()

        assert service._check_timer is first_timer
        service.stop()

    def test_stop_clears_timer(self, service, mock_ctx, qapp):
        """Stopping should clear timer."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.start()
        assert service._check_timer is not None

        service.stop()

        assert service._check_timer is None

    def test_is_running(self, service, mock_ctx, qapp):
        """is_running should reflect timer state."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        assert service.is_running() is False

        service.start()
        assert service.is_running() is True

        service.stop()
        assert service.is_running() is False

    def test_is_checking_initial(self, service):
        """Initially should not be checking."""
        assert service.is_checking() is False


class TestPriceAlertServiceInterval:
    """Tests for interval configuration."""

    def test_set_interval(self, service):
        """Should update interval."""
        service.set_interval(45)

        assert service._interval_ms == 45 * 60 * 1000

    def test_set_interval_clamps_minimum(self, service):
        """Should clamp to minimum."""
        service.set_interval(1)

        assert service._interval_ms >= service.MIN_INTERVAL_MS

    def test_set_interval_clamps_maximum(self, service):
        """Should clamp to maximum."""
        service.set_interval(1000)

        assert service._interval_ms <= service.MAX_INTERVAL_MS

    def test_set_interval_updates_running_timer(self, service, mock_ctx, qapp):
        """Should update running timer."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.start()
        service.set_interval(30)

        assert service._check_timer is not None
        assert service._check_timer.interval() == 30 * 60 * 1000
        service.stop()


class TestPriceAlertServiceCRUD:
    """Tests for alert CRUD operations."""

    def test_create_alert(self, service, mock_ctx):
        """Should create alert via database."""
        mock_ctx.db.create_price_alert.return_value = 42

        alert_id = service.create_alert(
            item_name="Headhunter",
            alert_type="below",
            threshold_chaos=5000.0,
        )

        assert alert_id == 42
        mock_ctx.db.create_price_alert.assert_called_once()

    def test_create_alert_emits_signal(self, service, mock_ctx):
        """Creating alert should emit alerts_changed signal."""
        signal_received = []
        service.alerts_changed.connect(lambda: signal_received.append(True))

        service.create_alert(
            item_name="Headhunter",
            alert_type="below",
            threshold_chaos=5000.0,
        )

        assert len(signal_received) == 1

    def test_create_alert_with_custom_cooldown(self, service, mock_ctx):
        """Should use custom cooldown when provided."""
        service.create_alert(
            item_name="Headhunter",
            alert_type="below",
            threshold_chaos=5000.0,
            cooldown_minutes=60,
        )

        call_kwargs = mock_ctx.db.create_price_alert.call_args.kwargs
        assert call_kwargs["cooldown_minutes"] == 60

    def test_get_alert(self, service, mock_ctx):
        """Should get alert by ID."""
        expected = {"id": 1, "item_name": "Test"}
        mock_ctx.db.get_price_alert.return_value = expected

        result = service.get_alert(1)

        assert result == expected
        mock_ctx.db.get_price_alert.assert_called_once_with(1)

    def test_get_all_alerts(self, service, mock_ctx):
        """Should get all alerts for current league/game."""
        expected = [{"id": 1}, {"id": 2}]
        mock_ctx.db.get_all_price_alerts.return_value = expected

        result = service.get_all_alerts()

        assert result == expected

    def test_get_active_alerts_returns_copy(self, service, mock_ctx):
        """Should return a copy of active alerts."""
        service._active_alerts = [{"id": 1}]

        result = service.get_active_alerts()

        assert result == [{"id": 1}]
        assert result is not service._active_alerts

    def test_update_alert(self, service, mock_ctx):
        """Should update alert via database."""
        result = service.update_alert(
            alert_id=1,
            threshold_chaos=200.0,
            enabled=False,
        )

        assert result is True
        mock_ctx.db.update_price_alert.assert_called_once()

    def test_update_alert_emits_signal(self, service, mock_ctx):
        """Updating alert should emit alerts_changed signal."""
        signal_received = []
        service.alerts_changed.connect(lambda: signal_received.append(True))

        service.update_alert(alert_id=1, threshold_chaos=200.0)

        assert len(signal_received) == 1

    def test_delete_alert(self, service, mock_ctx):
        """Should delete alert via database."""
        result = service.delete_alert(1)

        assert result is True
        mock_ctx.db.delete_price_alert.assert_called_once_with(1)

    def test_delete_alert_emits_signal(self, service, mock_ctx):
        """Deleting alert should emit alerts_changed signal."""
        signal_received = []
        service.alerts_changed.connect(lambda: signal_received.append(True))

        service.delete_alert(1)

        assert len(signal_received) == 1

    def test_toggle_alert_enables(self, service, mock_ctx):
        """Toggle should enable disabled alert."""
        mock_ctx.db.get_price_alert.return_value = {"id": 1, "enabled": False}

        service.toggle_alert(1)

        call_kwargs = mock_ctx.db.update_price_alert.call_args.kwargs
        assert call_kwargs["enabled"] is True

    def test_toggle_alert_disables(self, service, mock_ctx):
        """Toggle should disable enabled alert."""
        mock_ctx.db.get_price_alert.return_value = {"id": 1, "enabled": True}

        service.toggle_alert(1)

        call_kwargs = mock_ctx.db.update_price_alert.call_args.kwargs
        assert call_kwargs["enabled"] is False

    def test_toggle_nonexistent_alert(self, service, mock_ctx):
        """Toggle should return False for nonexistent alert."""
        mock_ctx.db.get_price_alert.return_value = None

        result = service.toggle_alert(999)

        assert result is False


class TestPriceAlertServiceCheck:
    """Tests for alert checking functionality."""

    def test_check_now_when_not_checking(self, service, mock_ctx):
        """check_now should trigger check when not already checking."""
        service.check_now()

        mock_ctx.db.get_active_price_alerts.assert_called()

    def test_check_now_skips_when_checking(self, service, mock_ctx):
        """check_now should skip if already checking."""
        service._is_checking = True

        service.check_now()

        mock_ctx.db.get_active_price_alerts.assert_not_called()

    def test_do_check_sets_flags(self, service, mock_ctx):
        """_do_check should manage is_checking flag."""
        service._do_check()

        assert service._is_checking is False

    def test_do_check_updates_last_check(self, service, mock_ctx):
        """_do_check should update last_check time when alerts exist."""
        # Must have active alerts for last_check to be updated
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service._do_check()

        assert service._last_check is not None

    def test_do_check_emits_signals(self, service, mock_ctx):
        """_do_check should emit check_started and check_finished signals."""
        started = []
        finished = []
        service.check_started.connect(lambda: started.append(True))
        service.check_finished.connect(lambda: finished.append(True))

        service._do_check()

        assert len(started) == 1
        assert len(finished) == 1

    def test_check_single_alert_no_trigger(self, service, mock_ctx):
        """_check_single_alert should return False when not triggered."""
        mock_ctx.poe_ninja.find_item_price.return_value = {"chaosValue": 100}
        mock_ctx.db.should_alert_trigger.return_value = False

        alert = {
            "id": 1,
            "item_name": "Test",
            "alert_type": "above",
            "threshold_chaos": 200,
        }

        result = service._check_single_alert(alert)

        assert result is False

    def test_check_single_alert_triggers(self, service, mock_ctx):
        """_check_single_alert should return True and emit signal when triggered."""
        from core.game_version import GameVersion

        # Set up proper GameVersion for price lookup
        mock_ctx.config.current_game = GameVersion.POE1
        mock_ctx.poe_ninja.get_currency_price.return_value = None
        mock_ctx.poe_ninja.find_item_price.return_value = {"chaosValue": 250.0}
        mock_ctx.db.should_alert_trigger.return_value = True

        triggered_alerts = []
        service.alert_triggered.connect(
            lambda id, name, type, threshold, price: triggered_alerts.append(
                (id, name, type, threshold, price)
            )
        )

        alert = {
            "id": 1,
            "item_name": "Test Item",
            "alert_type": "above",
            "threshold_chaos": 200.0,
        }

        result = service._check_single_alert(alert)

        assert result is True
        assert len(triggered_alerts) == 1
        assert triggered_alerts[0] == (1, "Test Item", "above", 200.0, 250.0)

    def test_check_single_alert_missing_price(self, service, mock_ctx):
        """_check_single_alert should return False when price unavailable."""
        mock_ctx.poe_ninja.find_item_price.return_value = None
        mock_ctx.poe_ninja.get_currency_price.return_value = None

        alert = {
            "id": 1,
            "item_name": "Unknown Item",
            "alert_type": "below",
            "threshold_chaos": 100,
        }

        result = service._check_single_alert(alert)

        assert result is False


class TestPriceAlertServiceGetPrice:
    """Tests for price fetching functionality."""

    def test_get_item_price_from_poe1_ninja(self, service, mock_ctx):
        """Should get price from poe.ninja for PoE1."""
        from core.game_version import GameVersion
        mock_ctx.config.current_game = GameVersion.POE1
        mock_ctx.poe_ninja.find_item_price.return_value = {"chaosValue": 150.5}

        result = service._get_item_price("Test Item")

        assert result == 150.5

    def test_get_item_price_from_poe2_ninja(self, service, mock_ctx):
        """Should get price from poe2.ninja for PoE2."""
        from core.game_version import GameVersion
        mock_ctx.config.current_game = GameVersion.POE2
        mock_ctx.poe2_ninja.find_item_price.return_value = {"exaltedValue": 5.5}

        result = service._get_item_price("Test Item")

        assert result == 5.5

    def test_get_item_price_currency_first(self, service, mock_ctx):
        """Should check currency price first."""
        from core.game_version import GameVersion
        mock_ctx.config.current_game = GameVersion.POE1
        mock_ctx.poe_ninja.get_currency_price.return_value = 25.0

        result = service._get_item_price("Divine Orb")

        assert result == 25.0
        mock_ctx.poe_ninja.find_item_price.assert_not_called()

    def test_get_item_price_handles_error(self, service, mock_ctx):
        """Should handle errors gracefully."""
        mock_ctx.poe_ninja.get_currency_price.side_effect = Exception("API error")
        mock_ctx.poe_ninja.find_item_price.side_effect = Exception("API error")

        result = service._get_item_price("Test Item")

        assert result is None


class TestPriceAlertServiceSingleton:
    """Tests for singleton functions."""

    def test_get_price_alert_service_creates_instance(self, mock_ctx, qapp):
        """Should create instance on first call with ctx."""
        service = get_price_alert_service(mock_ctx)

        assert service is not None
        assert isinstance(service, PriceAlertService)

    def test_get_price_alert_service_returns_same_instance(self, mock_ctx, qapp):
        """Should return same instance on subsequent calls."""
        service1 = get_price_alert_service(mock_ctx)
        service2 = get_price_alert_service()

        assert service1 is service2

    def test_get_price_alert_service_none_without_init(self, qapp):
        """Should return None if not initialized."""
        service = get_price_alert_service()

        assert service is None

    def test_shutdown_price_alert_service(self, mock_ctx, qapp):
        """Should shutdown and clear singleton."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service = get_price_alert_service(mock_ctx)
        service.start()

        shutdown_price_alert_service()

        # Should have stopped timer
        assert service._check_timer is None

        # Should return None now
        assert get_price_alert_service() is None


class TestPriceAlertServiceSignals:
    """Tests for signal emissions."""

    def test_emits_status_update_on_start(self, service, mock_ctx, qapp):
        """Should emit status_update when starting."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        signal_received = []
        service.status_update.connect(signal_received.append)

        service.start()

        assert any("started" in msg.lower() for msg in signal_received)
        service.stop()

    def test_emits_status_update_on_stop(self, service, mock_ctx, qapp):
        """Should emit status_update when stopping."""
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.start()

        signal_received = []
        service.status_update.connect(signal_received.append)

        service.stop()

        assert any("stopped" in msg.lower() for msg in signal_received)

    def test_emits_check_started_on_check(self, service, mock_ctx):
        """Should emit check_started when checking."""
        signal_received = []
        service.check_started.connect(lambda: signal_received.append(True))

        service.check_now()

        assert len(signal_received) == 1

    def test_emits_check_finished_on_check(self, service, mock_ctx):
        """Should emit check_finished when done."""
        signal_received = []
        service.check_finished.connect(lambda: signal_received.append(True))

        service.check_now()

        assert len(signal_received) == 1


class TestPriceAlertServiceAutoStop:
    """Tests for automatic service stop when no alerts remain."""

    def test_stops_when_last_alert_deleted(self, service, mock_ctx, qapp):
        """Should stop service when last alert is deleted."""
        # Start with one alert
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]
        service.start()
        assert service.is_running() is True

        # Delete returns success, but now no active alerts
        mock_ctx.db.get_active_price_alerts.return_value = []

        service.delete_alert(1)

        assert service.is_running() is False

    def test_stops_when_last_alert_disabled(self, service, mock_ctx, qapp):
        """Should stop service when last alert is disabled."""
        # Start with one alert
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100, "enabled": True}
        ]
        service.start()
        assert service.is_running() is True

        # After update, no active alerts remain
        mock_ctx.db.get_active_price_alerts.return_value = []
        mock_ctx.db.get_price_alert.return_value = {"id": 1, "enabled": True}

        service.toggle_alert(1)

        assert service.is_running() is False


class TestPriceAlertServiceStatus:
    """Tests for status methods."""

    def test_get_last_check_time_initial(self, service):
        """Initially should have no last check time."""
        assert service.get_last_check_time() is None

    def test_get_last_check_time_after_check(self, service, mock_ctx):
        """After check should have last check time."""
        # Must have active alerts for last_check to be updated
        mock_ctx.db.get_active_price_alerts.return_value = [
            {"id": 1, "item_name": "Test", "alert_type": "above", "threshold_chaos": 100}
        ]

        service.check_now()

        assert service.get_last_check_time() is not None
        assert isinstance(service.get_last_check_time(), datetime)
