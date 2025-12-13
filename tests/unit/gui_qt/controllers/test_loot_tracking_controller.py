"""Tests for gui_qt/controllers/loot_tracking_controller.py - Loot tracking coordination."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from gui_qt.controllers.loot_tracking_controller import LootTrackingController
from core.loot_session import LootDrop, LootSession, MapRun, SessionState


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_ctx():
    """Create a mock application context."""
    ctx = MagicMock()
    ctx.config.league = "Settlers"
    ctx.config.poesessid = "test_session"
    ctx.config.account_name = "TestAccount"
    ctx.config.loot_tracked_tabs = ["Currency", "Maps"]
    ctx.config.loot_client_txt_path = ""
    ctx.config.loot_poll_interval = 1.0
    ctx.config.loot_high_value_threshold = 50.0
    ctx.config.loot_min_value = 1.0
    ctx.db = MagicMock()
    ctx.db.conn = MagicMock()
    ctx.db.conn.cursor.return_value = MagicMock()
    return ctx


@pytest.fixture
def controller(mock_ctx):
    """Create a LootTrackingController."""
    return LootTrackingController(mock_ctx)


@pytest.fixture
def mock_session():
    """Create a mock LootSession."""
    session = MagicMock(spec=LootSession)
    session.id = "session-123"
    session.name = "Test Session"
    session.league = "Settlers"
    session.started_at = datetime.now()
    session.ended_at = None
    session.state = SessionState.ACTIVE
    session.total_maps = 0
    session.total_drops = 0
    session.total_chaos_value = 0.0
    session.chaos_per_hour = 0.0
    session.auto_detected = False
    session.notes = ""
    session.map_runs = []
    return session


@pytest.fixture
def mock_snapshot():
    """Create a mock StashSnapshot."""
    snapshot = MagicMock()
    snapshot.total_items = 100
    snapshot.tabs = [MagicMock(), MagicMock()]
    return snapshot


@pytest.fixture
def mock_diff():
    """Create a mock StashDiff."""
    diff = MagicMock()
    diff.has_changes = True
    diff.added_items = [
        {"typeLine": "Exalted Orb", "frameType": 5, "stackSize": 2},
    ]
    diff.get_summary.return_value = "1 item added"
    return diff


# =============================================================================
# Initialization Tests
# =============================================================================


class TestLootTrackingControllerInit:
    """Tests for LootTrackingController initialization."""

    def test_init_stores_context(self, mock_ctx):
        """Should store application context."""
        controller = LootTrackingController(mock_ctx)
        assert controller._ctx is mock_ctx

    def test_init_stores_config_values(self, mock_ctx):
        """Should store config values."""
        controller = LootTrackingController(mock_ctx)
        assert controller._league == "Settlers"
        assert controller._poesessid == "test_session"
        assert controller._account_name == "TestAccount"

    def test_init_creates_session_manager(self, mock_ctx):
        """Should create session manager."""
        controller = LootTrackingController(mock_ctx)
        assert controller._session_manager is not None

    def test_init_creates_diff_engine(self, mock_ctx):
        """Should create stash diff engine."""
        controller = LootTrackingController(mock_ctx)
        assert controller._diff_engine is not None

    def test_init_no_active_workers(self, mock_ctx):
        """Should start with no active workers."""
        controller = LootTrackingController(mock_ctx)
        assert controller._snapshot_worker is None
        assert controller._diff_worker is None
        assert controller._valuation_worker is None

    def test_init_has_required_signals(self, mock_ctx):
        """Should have required signals."""
        controller = LootTrackingController(mock_ctx)
        assert hasattr(controller, 'session_started')
        assert hasattr(controller, 'session_ended')
        assert hasattr(controller, 'drops_detected')
        assert hasattr(controller, 'snapshot_started')
        assert hasattr(controller, 'snapshot_completed')
        assert hasattr(controller, 'status_message')


# =============================================================================
# Monitoring Tests
# =============================================================================


class TestLootTrackingControllerMonitoring:
    """Tests for monitoring start/stop."""

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_start_monitoring_creates_monitor(self, mock_monitor_cls, controller):
        """Should create ClientTxtMonitor."""
        mock_monitor = MagicMock()
        mock_monitor.start_monitoring.return_value = True
        mock_monitor_cls.return_value = mock_monitor

        result = controller.start_monitoring()

        assert result.is_ok()
        mock_monitor_cls.assert_called_once()

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_start_monitoring_returns_error_on_failure(self, mock_monitor_cls, controller):
        """Should return error if monitoring fails to start."""
        mock_monitor = MagicMock()
        mock_monitor.start_monitoring.return_value = False
        mock_monitor_cls.return_value = mock_monitor

        result = controller.start_monitoring()

        assert result.is_err()
        assert "Failed" in result.error

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_start_monitoring_twice_returns_error(self, mock_monitor_cls, controller):
        """Should return error if already monitoring."""
        mock_monitor = MagicMock()
        mock_monitor.is_running = True
        mock_monitor.start_monitoring.return_value = True
        mock_monitor_cls.return_value = mock_monitor

        # Start first time
        controller.start_monitoring()

        # Start again
        result = controller.start_monitoring()

        assert result.is_err()
        assert "already" in result.error.lower()

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_stop_monitoring(self, mock_monitor_cls, controller):
        """Should stop monitoring."""
        mock_monitor = MagicMock()
        mock_monitor.is_running = True
        mock_monitor.start_monitoring.return_value = True
        mock_monitor_cls.return_value = mock_monitor

        controller.start_monitoring()
        controller.stop_monitoring()

        mock_monitor.stop_monitoring.assert_called_once()
        assert controller._client_monitor is None

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_is_monitoring(self, mock_monitor_cls, controller):
        """Should report monitoring state correctly."""
        assert not controller.is_monitoring()

        mock_monitor = MagicMock()
        mock_monitor.is_running = True
        mock_monitor.start_monitoring.return_value = True
        mock_monitor_cls.return_value = mock_monitor

        controller.start_monitoring()
        assert controller.is_monitoring()

    @patch('gui_qt.controllers.loot_tracking_controller.ClientTxtMonitor')
    def test_start_monitoring_emits_status(self, mock_monitor_cls, controller):
        """Should emit status message on start."""
        mock_monitor = MagicMock()
        mock_monitor.start_monitoring.return_value = True
        mock_monitor.log_path = "/test/Client.txt"
        mock_monitor_cls.return_value = mock_monitor

        status_messages = []
        controller.status_message.connect(lambda m: status_messages.append(m))

        controller.start_monitoring()

        assert len(status_messages) >= 1


# =============================================================================
# Session Tests
# =============================================================================


class TestLootTrackingControllerSession:
    """Tests for session management."""

    def test_start_session_without_poesessid(self, mock_ctx):
        """Should return error if POESESSID not configured."""
        mock_ctx.config.poesessid = ""
        controller = LootTrackingController(mock_ctx)

        result = controller.start_session()

        assert result.is_err()
        assert "POESESSID" in result.error

    def test_start_session_without_account(self, mock_ctx):
        """Should return error if account not configured."""
        mock_ctx.config.account_name = ""
        controller = LootTrackingController(mock_ctx)

        result = controller.start_session()

        assert result.is_err()
        assert "Account" in result.error

    def test_start_session_with_name(self, controller, mock_session):
        """Should pass session name to manager."""
        controller._session_manager.start_session = MagicMock(
            return_value=MagicMock(is_ok=lambda: True, unwrap=lambda: mock_session)
        )

        with patch.object(controller, '_take_snapshot'):
            controller.start_session(name="My Session")

        controller._session_manager.start_session.assert_called_once()
        call_kwargs = controller._session_manager.start_session.call_args[1]
        assert call_kwargs["name"] == "My Session"

    def test_start_session_takes_snapshot(self, controller, mock_session):
        """Should take before snapshot on session start."""
        from core.result import Ok
        controller._session_manager.start_session = MagicMock(return_value=Ok(mock_session))

        with patch.object(controller, '_take_snapshot') as mock_take:
            controller.start_session()

        mock_take.assert_called_once_with("before")

    def test_end_session_saves_to_db(self, controller, mock_session):
        """Should save session to database on end."""
        from core.result import Ok
        controller._session_manager.end_session = MagicMock(return_value=Ok(mock_session))

        with patch.object(controller, '_save_session_to_db') as mock_save:
            controller.end_session()

        mock_save.assert_called_once_with(mock_session)

    def test_get_current_session(self, controller, mock_session):
        """Should return current session from manager."""
        # Mock the session manager's current_session property
        with patch.object(type(controller._session_manager), 'current_session',
                         new_callable=PropertyMock, return_value=mock_session):
            result = controller.get_current_session()

        assert result is mock_session

    def test_get_session_stats(self, controller):
        """Should return session stats from manager."""
        expected_stats = {"maps": 5, "drops": 10}
        controller._session_manager.get_session_stats = MagicMock(return_value=expected_stats)

        result = controller.get_session_stats()

        assert result == expected_stats


# =============================================================================
# Auto-Tracking Tests
# =============================================================================


class TestLootTrackingControllerAutoTracking:
    """Tests for auto-tracking enable/disable."""

    def test_enable_auto_tracking(self, controller):
        """Should enable auto-tracking in session manager."""
        controller.enable_auto_tracking(True)
        # Verify it was enabled
        assert controller.is_auto_tracking_enabled()

    def test_disable_auto_tracking(self, controller):
        """Should disable auto-tracking in session manager."""
        # First enable, then disable
        controller.enable_auto_tracking(True)
        controller.enable_auto_tracking(False)
        # Verify it was disabled
        assert not controller.is_auto_tracking_enabled()

    def test_is_auto_tracking_enabled(self, controller):
        """Should return auto-tracking state from manager."""
        # Initially disabled
        assert not controller.is_auto_tracking_enabled()

        # Enable and check
        controller.enable_auto_tracking(True)
        assert controller.is_auto_tracking_enabled()


# =============================================================================
# Snapshot Tests
# =============================================================================


class TestLootTrackingControllerSnapshot:
    """Tests for stash snapshot operations."""

    def test_take_manual_snapshot_before(self, controller):
        """Should take 'before' snapshot when none exists."""
        controller._before_snapshot = None

        with patch.object(controller, '_take_snapshot') as mock_take:
            controller.take_manual_snapshot()

        mock_take.assert_called_once_with("before")

    def test_take_manual_snapshot_after(self, controller, mock_snapshot):
        """Should take 'after' snapshot when before exists."""
        controller._before_snapshot = mock_snapshot

        with patch.object(controller, '_take_snapshot') as mock_take:
            controller.take_manual_snapshot()

        mock_take.assert_called_once_with("after")

    def test_take_snapshot_without_credentials(self, controller):
        """Should emit error if credentials missing."""
        controller._poesessid = ""

        errors = []
        controller.snapshot_error.connect(lambda e: errors.append(e))

        controller._take_snapshot("before")

        assert len(errors) == 1
        assert "Missing" in errors[0]

    def test_take_snapshot_creates_worker(self, controller):
        """Should create StashSnapshotWorker."""
        with patch('gui_qt.controllers.loot_tracking_controller.StashSnapshotWorker') as mock_worker_cls:
            mock_worker = MagicMock()
            mock_worker_cls.return_value = mock_worker

            controller._take_snapshot("before")

            mock_worker_cls.assert_called_once()
            mock_worker.start.assert_called_once()

    def test_take_snapshot_emits_started(self, controller):
        """Should emit snapshot_started signal."""
        started = []
        controller.snapshot_started.connect(lambda: started.append(True))

        with patch('gui_qt.controllers.loot_tracking_controller.StashSnapshotWorker'):
            controller._take_snapshot("before")

        assert len(started) == 1


# =============================================================================
# Snapshot Result Handling Tests
# =============================================================================


class TestLootTrackingControllerSnapshotResults:
    """Tests for handling snapshot results."""

    def test_on_snapshot_result_before(self, controller, mock_snapshot):
        """Should store before snapshot."""
        controller._pending_snapshot_type = "before"

        controller._on_snapshot_result(mock_snapshot)

        assert controller._before_snapshot is mock_snapshot

    def test_on_snapshot_result_after_triggers_diff(self, controller, mock_snapshot):
        """Should trigger diff computation on after snapshot."""
        controller._before_snapshot = mock_snapshot
        controller._pending_snapshot_type = "after"

        with patch.object(controller, '_compute_diff') as mock_diff:
            controller._on_snapshot_result(mock_snapshot)

        mock_diff.assert_called_once_with(mock_snapshot)

    def test_on_snapshot_result_emits_completed(self, controller, mock_snapshot):
        """Should emit snapshot_completed with item count."""
        controller._pending_snapshot_type = "before"
        mock_snapshot.total_items = 150

        completed = []
        controller.snapshot_completed.connect(lambda c: completed.append(c))

        controller._on_snapshot_result(mock_snapshot)

        assert completed == [150]

    def test_on_snapshot_error_emits_signal(self, controller):
        """Should emit snapshot_error on failure."""
        errors = []
        controller.snapshot_error.connect(lambda e: errors.append(e))

        controller._on_snapshot_error("Connection failed", "traceback...")

        assert "Connection failed" in errors[0]


# =============================================================================
# Item Value Estimation Tests
# =============================================================================


class TestLootTrackingControllerItemValue:
    """Tests for item value estimation."""

    def test_estimate_unique_item(self, controller):
        """Unique items return 0 in fallback mode (need price service)."""
        item = {"frameType": 3}  # Unique
        value = controller._estimate_item_value_fallback(item)
        assert value == 0.0  # Non-currency items return 0 in fallback

    def test_estimate_divine_orb(self, controller):
        """Should estimate divine orbs correctly in fallback mode."""
        item = {"frameType": 5, "typeLine": "Divine Orb", "stackSize": 2}
        value = controller._estimate_item_value_fallback(item)
        assert value == 300.0  # 150 * 2

    def test_estimate_exalted_orb(self, controller):
        """Should estimate exalted orbs correctly in fallback mode."""
        item = {"frameType": 5, "typeLine": "Exalted Orb", "stackSize": 3}
        value = controller._estimate_item_value_fallback(item)
        assert value == 120.0  # 40 * 3

    def test_estimate_chaos_orb(self, controller):
        """Should estimate chaos orbs correctly in fallback mode."""
        item = {"frameType": 5, "typeLine": "Chaos Orb", "stackSize": 10}
        value = controller._estimate_item_value_fallback(item)
        assert value == 10.0  # 1 * 10

    def test_estimate_divination_card(self, controller):
        """Divination cards return 0 in fallback mode (need price service)."""
        item = {"frameType": 6, "stackSize": 2}  # Divination Card
        value = controller._estimate_item_value_fallback(item)
        assert value == 0.0  # Non-currency items return 0 in fallback

    def test_estimate_gem(self, controller):
        """Gems return 0 in fallback mode (need price service)."""
        item = {"frameType": 4}  # Gem
        value = controller._estimate_item_value_fallback(item)
        assert value == 0.0  # Non-currency items return 0 in fallback

    def test_estimate_other_currency(self, controller):
        """Unknown currency returns 0 in fallback mode."""
        item = {"frameType": 5, "typeLine": "Orb of Alteration", "stackSize": 20}
        value = controller._estimate_item_value_fallback(item)
        assert value == 0.0  # Only known currency has fallback pricing


# =============================================================================
# Item Class Detection Tests
# =============================================================================


class TestLootTrackingControllerItemClass:
    """Tests for item class detection."""

    def test_get_item_class_explicit(self, controller):
        """Should use explicit itemClass field."""
        item = {"itemClass": "Two Hand Sword"}
        result = controller._get_item_class(item)
        assert result == "Two Hand Sword"

    def test_get_item_class_gem(self, controller):
        """Should infer Gem from frame type."""
        item = {"frameType": 4}
        result = controller._get_item_class(item)
        assert result == "Gem"

    def test_get_item_class_currency(self, controller):
        """Should infer Currency from frame type."""
        item = {"frameType": 5}
        result = controller._get_item_class(item)
        assert result == "Currency"

    def test_get_item_class_divination(self, controller):
        """Should infer Divination Card from frame type."""
        item = {"frameType": 6}
        result = controller._get_item_class(item)
        assert result == "Divination Card"

    def test_get_item_class_unknown(self, controller):
        """Should return Unknown for unrecognized items."""
        item = {"frameType": 0}
        result = controller._get_item_class(item)
        assert result == "Unknown"


# =============================================================================
# Session Callbacks Tests
# =============================================================================


class TestLootTrackingControllerCallbacks:
    """Tests for session manager callbacks."""

    def test_on_session_start_emits_signal(self, controller, mock_session):
        """Should emit session_started signal."""
        sessions = []
        controller.session_started.connect(lambda s: sessions.append(s))

        controller._on_session_start(mock_session)

        assert len(sessions) == 1
        assert sessions[0] is mock_session

    def test_on_session_end_emits_signal(self, controller, mock_session):
        """Should emit session_ended signal."""
        sessions = []
        controller.session_ended.connect(lambda s: sessions.append(s))

        controller._on_session_end(mock_session)

        assert len(sessions) == 1

    def test_on_drops_detected_emits_signal(self, controller):
        """Should emit drops_detected signal."""
        drops = [MagicMock(spec=LootDrop)]
        drops[0].chaos_value = 10.0

        detected = []
        controller.drops_detected.connect(lambda d: detected.append(d))

        controller._on_drops_detected(drops)

        assert len(detected) == 1
        assert detected[0] == drops

    def test_on_drops_detected_high_value(self, controller):
        """Should emit high_value_drop for valuable items."""
        drop = MagicMock(spec=LootDrop)
        drop.chaos_value = 100.0  # Above threshold of 50

        high_value = []
        controller.high_value_drop.connect(lambda d: high_value.append(d))

        controller._on_drops_detected([drop])

        assert len(high_value) == 1

    def test_on_state_change_emits_signal(self, controller):
        """Should emit session_state_changed signal."""
        states = []
        controller.session_state_changed.connect(lambda s: states.append(s))

        controller._on_state_change(SessionState.ACTIVE)

        assert states == ["active"]


# =============================================================================
# Config Update Tests
# =============================================================================


class TestLootTrackingControllerConfig:
    """Tests for configuration updates."""

    def test_update_config_reloads_values(self, controller, mock_ctx):
        """Should reload config values."""
        mock_ctx.config.league = "New League"
        mock_ctx.config.poesessid = "new_session"
        mock_ctx.config.account_name = "NewAccount"

        controller.update_config()

        assert controller._league == "New League"
        assert controller._poesessid == "new_session"
        assert controller._account_name == "NewAccount"

    def test_update_config_updates_session_manager(self, controller, mock_ctx):
        """Should update session manager league."""
        mock_ctx.config.league = "New League"

        # Patch the update_league method on the real session manager
        with patch.object(controller._session_manager, 'update_league') as mock_update:
            controller.update_config()
            mock_update.assert_called_with("New League")


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestLootTrackingControllerCleanup:
    """Tests for cleanup operations."""

    def test_cleanup_stops_monitoring(self, controller):
        """Should stop monitoring on cleanup."""
        with patch.object(controller, 'stop_monitoring') as mock_stop:
            controller.cleanup()

        mock_stop.assert_called_once()

    def test_cleanup_cancels_workers(self, controller):
        """Should cancel active workers on cleanup."""
        mock_worker = MagicMock()
        controller._snapshot_worker = mock_worker

        controller.cleanup()

        mock_worker.cancel.assert_called_once()
        assert controller._snapshot_worker is None

    def test_cancel_workers(self, controller):
        """Should cancel all worker types."""
        controller._snapshot_worker = MagicMock()
        controller._diff_worker = MagicMock()
        controller._valuation_worker = MagicMock()

        controller._cancel_workers()

        assert controller._snapshot_worker is None
        assert controller._diff_worker is None
        assert controller._valuation_worker is None


# =============================================================================
# Stats Tests
# =============================================================================


class TestLootTrackingControllerStats:
    """Tests for statistics."""

    def test_get_monitoring_stats_when_running(self, controller):
        """Should return monitor stats when running."""
        controller._client_monitor = MagicMock()
        controller._client_monitor.get_stats.return_value = {"running": True, "events": 10}

        result = controller.get_monitoring_stats()

        assert result["running"]
        assert result["events"] == 10

    def test_get_monitoring_stats_when_stopped(self, controller):
        """Should return minimal stats when not running."""
        controller._client_monitor = None

        result = controller.get_monitoring_stats()

        assert result == {"running": False}


# =============================================================================
# Edge Cases
# =============================================================================


class TestLootTrackingControllerEdgeCases:
    """Edge case tests."""

    def test_clear_snapshot_state(self, controller, mock_snapshot):
        """Should clear all snapshot state."""
        controller._before_snapshot = mock_snapshot
        controller._pending_snapshot_type = "before"

        controller._clear_snapshot_state()

        assert controller._before_snapshot is None
        assert controller._pending_snapshot_type is None

    def test_snapshot_already_in_progress(self, controller):
        """Should not start snapshot if one is in progress."""
        controller._snapshot_worker = MagicMock()  # Simulate in-progress

        with patch('gui_qt.controllers.loot_tracking_controller.StashSnapshotWorker') as mock_cls:
            controller._take_snapshot("before")

        mock_cls.assert_not_called()

    def test_diff_already_in_progress(self, controller, mock_snapshot):
        """Should not start diff if one is in progress."""
        controller._diff_worker = MagicMock()  # Simulate in-progress
        controller._before_snapshot = mock_snapshot

        with patch('gui_qt.controllers.loot_tracking_controller.StashDiffWorker') as mock_cls:
            controller._compute_diff(mock_snapshot)

        mock_cls.assert_not_called()

    def test_diff_no_changes(self, controller):
        """Should emit status when no changes in diff."""
        diff = MagicMock()
        diff.has_changes = False

        statuses = []
        controller.status_message.connect(lambda s: statuses.append(s))

        controller._on_diff_result(diff)

        assert any("No changes" in s for s in statuses)
