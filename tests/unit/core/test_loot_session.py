"""Tests for loot_session.py - Loot tracking session management."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from core.loot_session import (
    SessionState,
    LootDrop,
    MapRun,
    LootSession,
    LootSessionManager,
)


# =============================================================================
# LootDrop Tests
# =============================================================================


class TestLootDropBasics:
    """Basic tests for LootDrop dataclass."""

    @pytest.fixture
    def sample_drop(self):
        """Create a sample drop for testing."""
        return LootDrop(
            id="drop-1",
            item_name="Divine Orb",
            item_base_type="Currency",
            stack_size=1,
            chaos_value=150.0,
            divine_value=1.0,
            rarity="Currency",
            item_class="Currency",
            detected_at=datetime.now(),
        )

    def test_total_value_single_stack(self, sample_drop):
        """Total value equals chaos value for stack of 1."""
        assert sample_drop.total_value == 150.0

    def test_total_value_multi_stack(self):
        """Total value multiplies by stack size."""
        drop = LootDrop(
            id="drop-1",
            item_name="Chaos Orb",
            item_base_type="Currency",
            stack_size=10,
            chaos_value=1.0,
            divine_value=0.007,
            rarity="Currency",
            item_class="Currency",
            detected_at=datetime.now(),
        )
        assert drop.total_value == 10.0

    def test_to_dict(self, sample_drop):
        """Can serialize to dictionary."""
        data = sample_drop.to_dict()
        assert data["id"] == "drop-1"
        assert data["item_name"] == "Divine Orb"
        assert data["chaos_value"] == 150.0
        assert "detected_at" in data

    def test_from_dict(self):
        """Can deserialize from dictionary."""
        data = {
            "id": "drop-2",
            "item_name": "Exalted Orb",
            "item_base_type": "Currency",
            "stack_size": 3,
            "chaos_value": 40.0,
            "divine_value": 0.27,
            "rarity": "Currency",
            "item_class": "Currency",
            "detected_at": "2024-01-15T10:30:00",
        }
        drop = LootDrop.from_dict(data)
        assert drop.id == "drop-2"
        assert drop.item_name == "Exalted Orb"
        assert drop.stack_size == 3
        assert drop.chaos_value == 40.0

    def test_from_dict_defaults(self):
        """from_dict uses defaults for missing optional fields."""
        data = {
            "id": "drop-3",
            "item_name": "Unknown Item",
            "detected_at": "2024-01-15T10:30:00",
        }
        drop = LootDrop.from_dict(data)
        assert drop.stack_size == 1
        assert drop.chaos_value == 0.0
        assert drop.rarity == "Normal"


class TestLootDropOptionalFields:
    """Tests for optional fields in LootDrop."""

    def test_source_tab_defaults_none(self):
        """source_tab defaults to None."""
        drop = LootDrop(
            id="1",
            item_name="Test",
            item_base_type="Test",
            stack_size=1,
            chaos_value=0,
            divine_value=0,
            rarity="Normal",
            item_class="",
            detected_at=datetime.now(),
        )
        assert drop.source_tab is None

    def test_raw_item_data_defaults_none(self):
        """raw_item_data defaults to None."""
        drop = LootDrop(
            id="1",
            item_name="Test",
            item_base_type="Test",
            stack_size=1,
            chaos_value=0,
            divine_value=0,
            rarity="Normal",
            item_class="",
            detected_at=datetime.now(),
        )
        assert drop.raw_item_data is None


# =============================================================================
# MapRun Tests
# =============================================================================


class TestMapRunBasics:
    """Basic tests for MapRun dataclass."""

    @pytest.fixture
    def sample_map_run(self):
        """Create a sample map run."""
        return MapRun(
            id="run-1",
            map_name="Glacier Map",
            area_level=83,
            started_at=datetime.now() - timedelta(minutes=5),
            ended_at=datetime.now(),
        )

    def test_duration_seconds(self, sample_map_run):
        """duration_seconds calculates correctly."""
        duration = sample_map_run.duration_seconds
        assert duration is not None
        assert 290 <= duration <= 310  # ~5 minutes

    def test_duration_seconds_no_end(self):
        """duration_seconds is None if not ended."""
        run = MapRun(
            id="run-1",
            map_name="Test Map",
            area_level=80,
            started_at=datetime.now(),
        )
        assert run.duration_seconds is None

    def test_duration_timedelta(self, sample_map_run):
        """duration property returns timedelta."""
        duration = sample_map_run.duration
        assert isinstance(duration, timedelta)
        assert duration.total_seconds() > 0

    def test_duration_in_progress(self):
        """duration calculates from now if not ended."""
        run = MapRun(
            id="run-1",
            map_name="Test Map",
            area_level=80,
            started_at=datetime.now() - timedelta(minutes=2),
        )
        duration = run.duration
        assert duration is not None
        assert duration.total_seconds() >= 120


class TestMapRunDrops:
    """Tests for MapRun drop handling."""

    def test_total_chaos_value_empty(self):
        """Total value is 0 with no drops."""
        run = MapRun(
            id="run-1",
            map_name="Test Map",
            area_level=80,
            started_at=datetime.now(),
        )
        assert run.total_chaos_value == 0

    def test_total_chaos_value_with_drops(self):
        """Total value sums all drops."""
        drops = [
            LootDrop(
                id="1", item_name="Divine", item_base_type="Currency",
                stack_size=1, chaos_value=150, divine_value=1,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
            LootDrop(
                id="2", item_name="Exalted", item_base_type="Currency",
                stack_size=2, chaos_value=40, divine_value=0.27,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
        ]
        run = MapRun(
            id="run-1",
            map_name="Test Map",
            area_level=80,
            started_at=datetime.now(),
            drops=drops,
        )
        # 150 + (40 * 2) = 230
        assert run.total_chaos_value == 230

    def test_drop_count(self):
        """drop_count returns number of drops."""
        drops = [
            LootDrop(
                id="1", item_name="Test", item_base_type="Test",
                stack_size=1, chaos_value=0, divine_value=0,
                rarity="Normal", item_class="", detected_at=datetime.now(),
            ),
            LootDrop(
                id="2", item_name="Test2", item_base_type="Test",
                stack_size=1, chaos_value=0, divine_value=0,
                rarity="Normal", item_class="", detected_at=datetime.now(),
            ),
        ]
        run = MapRun(
            id="run-1",
            map_name="Test Map",
            area_level=80,
            started_at=datetime.now(),
            drops=drops,
        )
        assert run.drop_count == 2

    def test_to_dict(self):
        """Can serialize map run to dict."""
        run = MapRun(
            id="run-1",
            map_name="Glacier Map",
            area_level=83,
            started_at=datetime(2024, 1, 15, 10, 0, 0),
            ended_at=datetime(2024, 1, 15, 10, 5, 0),
        )
        data = run.to_dict()
        assert data["id"] == "run-1"
        assert data["map_name"] == "Glacier Map"
        assert data["area_level"] == 83
        assert "started_at" in data


# =============================================================================
# LootSession Tests
# =============================================================================


class TestLootSessionBasics:
    """Basic tests for LootSession dataclass."""

    @pytest.fixture
    def sample_session(self):
        """Create a sample session."""
        return LootSession(
            id="session-1",
            name="Morning Farming",
            league="Settlers",
            started_at=datetime.now() - timedelta(hours=1),
            state=SessionState.ACTIVE,
        )

    def test_duration(self, sample_session):
        """Duration calculates from start."""
        duration = sample_session.duration
        assert duration is not None
        assert duration.total_seconds() >= 3600  # ~1 hour

    def test_duration_seconds(self, sample_session):
        """duration_seconds returns float."""
        assert sample_session.duration_seconds >= 3600

    def test_total_maps_empty(self, sample_session):
        """total_maps is 0 with no runs."""
        assert sample_session.total_maps == 0

    def test_total_maps_with_runs(self):
        """total_maps counts map runs."""
        session = LootSession(
            id="1",
            name="Test",
            league="Settlers",
            started_at=datetime.now(),
            map_runs=[
                MapRun(id="1", map_name="Map1", area_level=80, started_at=datetime.now()),
                MapRun(id="2", map_name="Map2", area_level=80, started_at=datetime.now()),
            ],
        )
        assert session.total_maps == 2


class TestLootSessionStatistics:
    """Tests for LootSession statistics calculations."""

    @pytest.fixture
    def session_with_data(self):
        """Create session with map runs and drops."""
        drops1 = [
            LootDrop(
                id="1", item_name="Divine", item_base_type="Currency",
                stack_size=1, chaos_value=150, divine_value=1,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
        ]
        drops2 = [
            LootDrop(
                id="2", item_name="Exalted", item_base_type="Currency",
                stack_size=2, chaos_value=40, divine_value=0.27,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
        ]
        runs = [
            MapRun(
                id="1", map_name="Map1", area_level=80,
                started_at=datetime.now() - timedelta(minutes=10),
                ended_at=datetime.now() - timedelta(minutes=5),
                drops=drops1,
            ),
            MapRun(
                id="2", map_name="Map2", area_level=80,
                started_at=datetime.now() - timedelta(minutes=5),
                ended_at=datetime.now(),
                drops=drops2,
            ),
        ]
        return LootSession(
            id="1",
            name="Test Session",
            league="Settlers",
            started_at=datetime.now() - timedelta(minutes=10),
            ended_at=datetime.now(),
            map_runs=runs,
        )

    def test_total_drops(self, session_with_data):
        """total_drops sums across all maps."""
        assert session_with_data.total_drops == 2

    def test_total_chaos_value(self, session_with_data):
        """total_chaos_value sums all drop values."""
        # 150 + (40 * 2) = 230
        assert session_with_data.total_chaos_value == 230

    def test_all_drops(self, session_with_data):
        """all_drops collects from all runs."""
        drops = session_with_data.all_drops
        assert len(drops) == 2
        assert drops[0].item_name == "Divine"
        assert drops[1].item_name == "Exalted"

    def test_top_drops(self, session_with_data):
        """top_drops returns sorted by value."""
        top = session_with_data.top_drops
        # Divine (150) should be first, Exalted (80 total) second
        assert top[0].item_name == "Divine"

    def test_avg_chaos_per_map(self, session_with_data):
        """avg_chaos_per_map calculates correctly."""
        # 230 / 2 maps = 115
        assert session_with_data.avg_chaos_per_map == 115

    def test_get_drops_by_rarity(self, session_with_data):
        """get_drops_by_rarity groups correctly."""
        by_rarity = session_with_data.get_drops_by_rarity()
        assert by_rarity["Currency"] == 2


class TestLootSessionHourlyRates:
    """Tests for hourly rate calculations."""

    def test_chaos_per_hour_zero_if_short(self):
        """chaos_per_hour is 0 if session < 1 minute."""
        session = LootSession(
            id="1",
            name="Test",
            league="Settlers",
            started_at=datetime.now() - timedelta(seconds=30),
        )
        assert session.chaos_per_hour == 0

    def test_chaos_per_hour_calculation(self):
        """chaos_per_hour calculates correctly."""
        drops = [
            LootDrop(
                id="1", item_name="Test", item_base_type="Currency",
                stack_size=1, chaos_value=100, divine_value=0.67,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
        ]
        run = MapRun(
            id="1", map_name="Map", area_level=80,
            started_at=datetime.now() - timedelta(hours=1),
            drops=drops,
        )
        session = LootSession(
            id="1",
            name="Test",
            league="Settlers",
            started_at=datetime.now() - timedelta(hours=1),
            ended_at=datetime.now(),
            map_runs=[run],
        )
        # 100 chaos in 1 hour = 100 c/hr
        assert abs(session.chaos_per_hour - 100) < 5  # Allow small variance

    def test_maps_per_hour_zero_if_short(self):
        """maps_per_hour is 0 if session < 1 minute."""
        session = LootSession(
            id="1",
            name="Test",
            league="Settlers",
            started_at=datetime.now() - timedelta(seconds=30),
        )
        assert session.maps_per_hour == 0

    def test_maps_per_hour_calculation(self):
        """maps_per_hour calculates correctly."""
        runs = [
            MapRun(id=str(i), map_name=f"Map{i}", area_level=80, started_at=datetime.now())
            for i in range(6)
        ]
        session = LootSession(
            id="1",
            name="Test",
            league="Settlers",
            started_at=datetime.now() - timedelta(hours=1),
            ended_at=datetime.now(),
            map_runs=runs,
        )
        # 6 maps in 1 hour = 6 maps/hr
        assert abs(session.maps_per_hour - 6) < 1


class TestLootSessionSerialization:
    """Tests for session serialization."""

    def test_to_dict(self):
        """Can serialize session to dict."""
        session = LootSession(
            id="session-1",
            name="Test Session",
            league="Settlers",
            started_at=datetime(2024, 1, 15, 10, 0, 0),
            state=SessionState.ACTIVE,
            auto_detected=True,
            notes="Test notes",
        )
        data = session.to_dict()
        assert data["id"] == "session-1"
        assert data["name"] == "Test Session"
        assert data["league"] == "Settlers"
        assert data["state"] == "active"
        assert data["auto_detected"] is True
        assert data["notes"] == "Test notes"


# =============================================================================
# LootSessionManager Tests
# =============================================================================


class TestLootSessionManagerInit:
    """Tests for LootSessionManager initialization."""

    def test_init_with_league(self):
        """Manager initializes with league."""
        manager = LootSessionManager(league="Settlers")
        assert manager.league == "Settlers"

    def test_init_no_active_session(self):
        """Manager starts with no active session."""
        manager = LootSessionManager(league="Settlers")
        assert manager.current_session is None
        assert not manager.is_active

    def test_init_callbacks_stored(self):
        """Callbacks are stored."""
        on_start = MagicMock()
        on_end = MagicMock()
        manager = LootSessionManager(
            league="Settlers",
            on_session_start=on_start,
            on_session_end=on_end,
        )
        assert manager.on_session_start is on_start
        assert manager.on_session_end is on_end


class TestLootSessionManagerStartSession:
    """Tests for starting sessions."""

    def test_start_session_success(self):
        """Can start a new session."""
        manager = LootSessionManager(league="Settlers")
        result = manager.start_session("Test Session")

        assert result.is_ok()
        session = result.unwrap()
        assert session.name == "Test Session"
        assert session.league == "Settlers"
        assert session.state == SessionState.PENDING

    def test_start_session_auto_name(self):
        """Session gets auto-generated name if none provided."""
        manager = LootSessionManager(league="Settlers")
        result = manager.start_session()

        assert result.is_ok()
        session = result.unwrap()
        assert "Session" in session.name

    def test_start_session_sets_current(self):
        """Starting session sets current_session."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")

        assert manager.current_session is not None
        assert manager.is_active

    def test_start_session_error_if_active(self):
        """Cannot start session if one is active."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Session 1")
        result = manager.start_session("Session 2")

        assert result.is_err()
        assert "already active" in result.error

    def test_start_session_calls_callback(self):
        """Starting session calls on_session_start callback."""
        on_start = MagicMock()
        manager = LootSessionManager(league="Settlers", on_session_start=on_start)
        manager.start_session("Test")

        on_start.assert_called_once()
        session = on_start.call_args[0][0]
        assert session.name == "Test"

    def test_start_session_auto_detected_flag(self):
        """auto_detected flag is set correctly."""
        manager = LootSessionManager(league="Settlers")
        result = manager.start_session("Test", auto_detected=True)

        session = result.unwrap()
        assert session.auto_detected is True


class TestLootSessionManagerEndSession:
    """Tests for ending sessions."""

    def test_end_session_success(self):
        """Can end an active session."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        result = manager.end_session()

        assert result.is_ok()
        session = result.unwrap()
        assert session.state == SessionState.COMPLETED
        assert session.ended_at is not None

    def test_end_session_error_if_none_active(self):
        """Cannot end if no session active."""
        manager = LootSessionManager(league="Settlers")
        result = manager.end_session()

        assert result.is_err()
        assert "No active session" in result.error

    def test_end_session_clears_current(self):
        """Ending session clears current_session."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.end_session()

        assert manager.current_session is None
        assert not manager.is_active

    def test_end_session_ends_current_map(self):
        """Ending session ends any active map run."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)

        assert manager.current_map_run is not None

        result = manager.end_session()
        session = result.unwrap()

        assert len(session.map_runs) == 1
        assert session.map_runs[0].ended_at is not None

    def test_end_session_calls_callback(self):
        """Ending session calls on_session_end callback."""
        on_end = MagicMock()
        manager = LootSessionManager(league="Settlers", on_session_end=on_end)
        manager.start_session("Test")
        manager.end_session()

        on_end.assert_called_once()


class TestLootSessionManagerZoneEvents:
    """Tests for zone entry handling."""

    def test_zone_map_starts_run(self):
        """Entering map starts a map run."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", area_level=83)

        assert manager.current_map_run is not None
        assert manager.current_map_run.map_name == "Glacier Map"
        assert manager.current_map_run.area_level == 83
        assert manager.is_in_map

    def test_zone_map_sets_active_state(self):
        """Entering map sets ACTIVE state."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)

        assert manager.current_session.state == SessionState.ACTIVE

    def test_zone_hideout_ends_run(self):
        """Entering hideout ends current map run."""
        on_map_complete = MagicMock()
        manager = LootSessionManager(
            league="Settlers",
            on_map_complete=on_map_complete,
        )
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)
        manager.on_zone_entered("Celestial Hideout", "hideout")

        assert manager.current_map_run is None
        assert not manager.is_in_map
        assert manager.current_session.state == SessionState.PAUSED
        on_map_complete.assert_called_once()

    def test_zone_hideout_adds_run_to_session(self):
        """Completed map run is added to session."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)
        manager.on_zone_entered("Celestial Hideout", "hideout")

        assert len(manager.current_session.map_runs) == 1
        assert manager.current_session.map_runs[0].map_name == "Glacier Map"

    def test_zone_new_map_ends_previous(self):
        """Entering new map ends previous run."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)
        manager.on_zone_entered("Strand Map", "map", 81)

        assert manager.current_map_run.map_name == "Strand Map"
        assert len(manager.current_session.map_runs) == 1  # First map completed

    def test_zone_no_session_does_nothing(self):
        """Zone events with no session do nothing."""
        manager = LootSessionManager(league="Settlers")
        # Should not raise
        manager.on_zone_entered("Glacier Map", "map", 83)
        assert manager.current_session is None


class TestLootSessionManagerAutoTracking:
    """Tests for auto-tracking functionality."""

    def test_auto_tracking_disabled_by_default(self):
        """Auto-tracking is disabled by default."""
        manager = LootSessionManager(league="Settlers")
        assert not manager.is_auto_tracking_enabled()

    def test_enable_auto_tracking(self):
        """Can enable auto-tracking."""
        manager = LootSessionManager(league="Settlers")
        manager.enable_auto_tracking(True)
        assert manager.is_auto_tracking_enabled()

    def test_auto_tracking_starts_session_on_map(self):
        """With auto-tracking, entering map starts session."""
        manager = LootSessionManager(league="Settlers")
        manager.enable_auto_tracking(True)
        manager.on_zone_entered("Glacier Map", "map", 83)

        assert manager.current_session is not None
        assert manager.current_session.auto_detected is True

    def test_auto_tracking_disabled_no_session(self):
        """Without auto-tracking, entering map does nothing."""
        manager = LootSessionManager(league="Settlers")
        manager.on_zone_entered("Glacier Map", "map", 83)

        assert manager.current_session is None


class TestLootSessionManagerDrops:
    """Tests for drop handling."""

    @pytest.fixture
    def sample_drops(self):
        """Create sample drops."""
        return [
            LootDrop(
                id="1", item_name="Divine Orb", item_base_type="Currency",
                stack_size=1, chaos_value=150, divine_value=1,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
            LootDrop(
                id="2", item_name="Exalted Orb", item_base_type="Currency",
                stack_size=2, chaos_value=40, divine_value=0.27,
                rarity="Currency", item_class="Currency", detected_at=datetime.now(),
            ),
        ]

    def test_add_drops_to_current_map(self, sample_drops):
        """Drops are added to current map run."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)
        manager.add_drops(sample_drops)

        assert manager.current_map_run.drop_count == 2

    def test_add_drops_calls_callback(self, sample_drops):
        """Adding drops calls on_drops_detected callback."""
        on_drops = MagicMock()
        manager = LootSessionManager(
            league="Settlers",
            on_drops_detected=on_drops,
        )
        manager.start_session("Test")
        manager.on_zone_entered("Glacier Map", "map", 83)
        manager.add_drops(sample_drops)

        on_drops.assert_called_once_with(sample_drops)

    def test_add_drops_no_map_creates_synthetic(self, sample_drops):
        """Drops without active map create synthetic run."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test")
        # Note: No zone entered, so no active map
        manager.add_drops(sample_drops)

        assert len(manager.current_session.map_runs) == 1
        assert manager.current_session.map_runs[0].map_name == "Hideout Activity"

    def test_add_drops_empty_list(self):
        """Adding empty list does nothing."""
        on_drops = MagicMock()
        manager = LootSessionManager(
            league="Settlers",
            on_drops_detected=on_drops,
        )
        manager.start_session("Test")
        manager.add_drops([])

        on_drops.assert_not_called()


class TestLootSessionManagerStats:
    """Tests for session statistics."""

    def test_get_session_stats_empty(self):
        """Stats are empty dict with no session."""
        manager = LootSessionManager(league="Settlers")
        stats = manager.get_session_stats()
        assert stats == {}

    def test_get_session_stats_with_session(self):
        """Stats include session data."""
        manager = LootSessionManager(league="Settlers")
        manager.start_session("Test Session")

        stats = manager.get_session_stats()
        assert stats["name"] == "Test Session"
        assert stats["state"] == "pending"
        assert "duration_minutes" in stats
        assert "total_maps" in stats
        assert "chaos_per_hour" in stats


class TestLootSessionManagerUtilities:
    """Tests for utility methods."""

    def test_update_league(self):
        """Can update league for new sessions."""
        manager = LootSessionManager(league="Settlers")
        manager.update_league("Affliction")
        assert manager.league == "Affliction"

    def test_callback_error_handling(self):
        """Callbacks that raise don't break manager."""
        def bad_callback(session):
            raise ValueError("Callback error")

        manager = LootSessionManager(
            league="Settlers",
            on_session_start=bad_callback,
        )

        # Should not raise
        result = manager.start_session("Test")
        assert result.is_ok()


class TestSessionStateEnum:
    """Tests for SessionState enum."""

    def test_idle_value(self):
        """IDLE has correct value."""
        assert SessionState.IDLE.value == "idle"

    def test_pending_value(self):
        """PENDING has correct value."""
        assert SessionState.PENDING.value == "pending"

    def test_active_value(self):
        """ACTIVE has correct value."""
        assert SessionState.ACTIVE.value == "active"

    def test_paused_value(self):
        """PAUSED has correct value."""
        assert SessionState.PAUSED.value == "paused"

    def test_completed_value(self):
        """COMPLETED has correct value."""
        assert SessionState.COMPLETED.value == "completed"
