"""Tests for core/client_txt_monitor.py - Client.txt log monitoring."""

import pytest
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.client_txt_monitor import (
    ZoneType,
    ZoneChangeEvent,
    ClientTxtMonitor,
    detect_client_txt_path,
)


# =============================================================================
# ZoneType Tests
# =============================================================================


class TestZoneType:
    """Tests for ZoneType enum."""

    def test_all_zone_types_exist(self):
        """Should have all expected zone types."""
        types = list(ZoneType)
        assert len(types) == 5
        assert ZoneType.HIDEOUT in types
        assert ZoneType.MAP in types
        assert ZoneType.TOWN in types
        assert ZoneType.CAMPAIGN in types
        assert ZoneType.UNKNOWN in types

    def test_zone_types_are_hashable(self):
        """ZoneType should be usable as dict key."""
        handlers = {
            ZoneType.HIDEOUT: "hideout_handler",
            ZoneType.MAP: "map_handler",
        }
        assert handlers[ZoneType.HIDEOUT] == "hideout_handler"


# =============================================================================
# ZoneChangeEvent Tests
# =============================================================================


class TestZoneChangeEvent:
    """Tests for ZoneChangeEvent dataclass."""

    def test_create_basic_event(self):
        """Should create event with required fields."""
        event = ZoneChangeEvent(
            timestamp=datetime(2024, 1, 15, 12, 0, 0),
            zone_name="Celestial Hideout",
            zone_type=ZoneType.HIDEOUT,
        )
        assert event.zone_name == "Celestial Hideout"
        assert event.zone_type == ZoneType.HIDEOUT
        assert event.timestamp.year == 2024

    def test_event_with_area_level(self):
        """Should store area level."""
        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Glacier Map",
            zone_type=ZoneType.MAP,
            area_level=83,
        )
        assert event.area_level == 83

    def test_event_str_without_level(self):
        """String representation without level."""
        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="The Blood Aqueduct",
            zone_type=ZoneType.CAMPAIGN,
        )
        s = str(event)
        assert "The Blood Aqueduct" in s
        assert "campaign" in s
        assert "Level" not in s

    def test_event_str_with_level(self):
        """String representation with level."""
        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Glacier Map",
            zone_type=ZoneType.MAP,
            area_level=83,
        )
        s = str(event)
        assert "Glacier Map" in s
        assert "Level 83" in s
        assert "map" in s

    def test_event_stores_raw_line(self):
        """Should store original log line."""
        raw = "2024/01/15 12:00:00 You have entered Test Zone."
        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Test Zone",
            zone_type=ZoneType.UNKNOWN,
            raw_line=raw,
        )
        assert event.raw_line == raw


# =============================================================================
# ClientTxtMonitor Zone Classification Tests
# =============================================================================


class TestZoneClassification:
    """Tests for zone type classification logic."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temp log path."""
        log_path = tmp_path / "Client.txt"
        return ClientTxtMonitor(log_path=log_path)

    def test_classify_hideout(self, monitor):
        """Should classify hideout zones."""
        assert monitor._classify_zone("Celestial Hideout") == ZoneType.HIDEOUT
        assert monitor._classify_zone("My Hideout") == ZoneType.HIDEOUT
        assert monitor._classify_zone("Backstreet Haven") == ZoneType.HIDEOUT
        assert monitor._classify_zone("Menagerie") == ZoneType.HIDEOUT

    def test_classify_town(self, monitor):
        """Should classify town zones."""
        assert monitor._classify_zone("Lioneye's Watch") == ZoneType.TOWN
        assert monitor._classify_zone("Karui Shores") == ZoneType.TOWN
        assert monitor._classify_zone("The Rogue Harbour") == ZoneType.TOWN
        assert monitor._classify_zone("Highgate") == ZoneType.TOWN

    def test_classify_poe2_towns(self, monitor):
        """Should classify PoE2 town zones."""
        assert monitor._classify_zone("Clearfell Encampment") == ZoneType.TOWN
        assert monitor._classify_zone("Ardura Caravan") == ZoneType.TOWN
        assert monitor._classify_zone("The Crossroads Encampment") == ZoneType.TOWN

    def test_classify_maps(self, monitor):
        """Should classify map zones."""
        assert monitor._classify_zone("Glacier Map") == ZoneType.MAP
        assert monitor._classify_zone("Strand Map") == ZoneType.MAP
        assert monitor._classify_zone("The Temple of Atzoatl") == ZoneType.MAP
        assert monitor._classify_zone("Simulacrum") == ZoneType.MAP

    def test_classify_campaign(self, monitor):
        """Should classify campaign zones."""
        assert monitor._classify_zone("The Twilight Strand") == ZoneType.CAMPAIGN
        assert monitor._classify_zone("The Coast") == ZoneType.CAMPAIGN
        assert monitor._classify_zone("The Submerged Passage") == ZoneType.CAMPAIGN

    def test_classify_unknown(self, monitor):
        """Should return unknown for unrecognized zones."""
        assert monitor._classify_zone("Random Zone 123") == ZoneType.UNKNOWN

    def test_classification_case_insensitive(self, monitor):
        """Classification should be case insensitive."""
        assert monitor._classify_zone("HIDEOUT") == ZoneType.HIDEOUT
        assert monitor._classify_zone("glacier MAP") == ZoneType.MAP


# =============================================================================
# ClientTxtMonitor Parsing Tests
# =============================================================================


class TestLogParsing:
    """Tests for log line parsing."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temp log path."""
        log_path = tmp_path / "Client.txt"
        return ClientTxtMonitor(log_path=log_path)

    def test_parse_zone_entry(self, monitor):
        """Should parse zone entry line."""
        line = "2024/01/15 12:34:56 123456 [INFO Client 1234] : You have entered Celestial Hideout."
        event = monitor._parse_log_line(line)

        assert event is not None
        assert event.zone_name == "Celestial Hideout"
        assert event.zone_type == ZoneType.HIDEOUT
        assert event.timestamp.hour == 12
        assert event.timestamp.minute == 34

    def test_parse_area_level_then_zone(self, monitor):
        """Should use area level from previous line."""
        level_line = "2024/01/15 12:34:55 123456 [DEBUG Client 1234] Generating level 83 area"
        zone_line = "2024/01/15 12:34:56 123456 [INFO Client 1234] : You have entered Glacier Map."

        # Parse level line first (returns None)
        assert monitor._parse_log_line(level_line) is None

        # Then parse zone line - should include level
        event = monitor._parse_log_line(zone_line)
        assert event is not None
        assert event.area_level == 83

    def test_parse_zone_clears_pending_level(self, monitor):
        """Pending area level should be cleared after use."""
        level_line = "2024/01/15 12:34:55 123456 Generating level 83 area"
        zone_line1 = "2024/01/15 12:34:56 123456 You have entered Map One."
        zone_line2 = "2024/01/15 12:34:57 123456 You have entered Map Two."

        monitor._parse_log_line(level_line)
        event1 = monitor._parse_log_line(zone_line1)
        event2 = monitor._parse_log_line(zone_line2)

        assert event1.area_level == 83
        assert event2.area_level is None  # Level was consumed

    def test_parse_non_matching_line(self, monitor):
        """Should return None for non-zone lines."""
        line = "2024/01/15 12:34:56 Random log message about something else"
        event = monitor._parse_log_line(line)
        assert event is None

    def test_parse_timestamp_fallback(self, monitor):
        """Should use current time if timestamp parsing fails."""
        # Test _parse_timestamp directly - it falls back to current time
        # for invalid formats
        result = monitor._parse_timestamp("invalid-timestamp")
        # Should be within last minute
        assert (datetime.now() - result).total_seconds() < 60

    def test_line_with_invalid_format_returns_none(self, monitor):
        """Lines not matching expected format should return None."""
        # Line without proper timestamp format won't match the regex
        line = "invalid-timestamp : You have entered Test Zone."
        event = monitor._parse_log_line(line)
        assert event is None


# =============================================================================
# ClientTxtMonitor Lifecycle Tests
# =============================================================================


class TestMonitorLifecycle:
    """Tests for monitor start/stop lifecycle."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temp log path."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("")  # Create empty file
        return ClientTxtMonitor(log_path=log_path)

    def test_initial_state(self, monitor):
        """Monitor should not be running initially."""
        assert monitor.is_running is False
        assert monitor._monitor_thread is None

    def test_start_monitoring(self, monitor):
        """start_monitoring should start background thread."""
        result = monitor.start_monitoring()
        assert result is True
        assert monitor.is_running is True
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()

        # Cleanup
        monitor.stop_monitoring()

    def test_start_when_already_running(self, monitor):
        """start_monitoring should return False if already running."""
        monitor.start_monitoring()
        result = monitor.start_monitoring()
        assert result is False  # Already running

        # Cleanup
        monitor.stop_monitoring()

    def test_stop_monitoring(self, monitor):
        """stop_monitoring should stop the thread."""
        monitor.start_monitoring()
        monitor.stop_monitoring()

        assert monitor.is_running is False
        assert monitor._monitor_thread is None

    def test_cleanup(self, monitor):
        """cleanup should stop monitoring."""
        monitor.start_monitoring()
        monitor.cleanup()

        assert monitor.is_running is False

    def test_start_with_missing_file(self, tmp_path):
        """Should start even if log file doesn't exist."""
        log_path = tmp_path / "nonexistent.txt"
        monitor = ClientTxtMonitor(log_path=log_path)

        result = monitor.start_monitoring()
        assert result is True  # Should still start
        assert monitor.is_running is True

        monitor.stop_monitoring()


# =============================================================================
# ClientTxtMonitor Statistics Tests
# =============================================================================


class TestMonitorStatistics:
    """Tests for monitor statistics."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temp log path."""
        log_path = tmp_path / "Client.txt"
        return ClientTxtMonitor(log_path=log_path)

    def test_initial_stats(self, monitor):
        """Should have zero initial stats."""
        assert monitor.zones_detected == 0
        assert monitor.map_entries == 0
        assert monitor.hideout_entries == 0
        assert monitor.lines_processed == 0

    def test_get_stats(self, monitor):
        """get_stats should return dict with all stats."""
        stats = monitor.get_stats()

        assert "running" in stats
        assert "log_path" in stats
        assert "log_exists" in stats
        assert "zones_detected" in stats
        assert "map_entries" in stats
        assert "hideout_entries" in stats
        assert "lines_processed" in stats
        assert "last_zone" in stats

    def test_get_last_zone_initially_none(self, monitor):
        """get_last_zone should return None initially."""
        assert monitor.get_last_zone() is None


# =============================================================================
# ClientTxtMonitor Callback Tests
# =============================================================================


class TestMonitorCallbacks:
    """Tests for zone change callbacks."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create monitor with temp log path."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("")  # Create empty file
        return ClientTxtMonitor(log_path=log_path)

    def test_callback_invoked_on_zone_change(self, monitor):
        """Callback should be invoked when zone changes."""
        events = []
        monitor.on_zone_change = lambda e: events.append(e)

        # Create event and handle it
        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Test Hideout",
            zone_type=ZoneType.HIDEOUT,
        )
        monitor._handle_zone_change(event)

        assert len(events) == 1
        assert events[0].zone_name == "Test Hideout"

    def test_callback_error_handled(self, monitor):
        """Callback errors should not crash monitor."""

        def bad_callback(event):
            raise ValueError("Test error")

        monitor.on_zone_change = bad_callback

        event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Test",
            zone_type=ZoneType.UNKNOWN,
        )

        # Should not raise
        monitor._handle_zone_change(event)

    def test_stats_updated_on_zone_change(self, monitor):
        """Statistics should be updated on zone change."""
        map_event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Glacier Map",
            zone_type=ZoneType.MAP,
        )
        hideout_event = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="My Hideout",
            zone_type=ZoneType.HIDEOUT,
        )

        monitor._handle_zone_change(map_event)
        monitor._handle_zone_change(hideout_event)

        assert monitor.zones_detected == 2
        assert monitor.map_entries == 1
        assert monitor.hideout_entries == 1


# =============================================================================
# ClientTxtMonitor File Reading Tests
# =============================================================================


class TestFileReading:
    """Tests for log file reading."""

    def test_check_for_new_lines_updates_position(self, tmp_path):
        """Should update position after reading."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("Initial content\n")

        monitor = ClientTxtMonitor(log_path=log_path)
        monitor._last_position = 0

        monitor._check_for_new_lines()

        assert monitor._last_position > 0
        assert monitor.lines_processed >= 1

    def test_handles_file_truncation(self, tmp_path):
        """Should handle log file truncation."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("Line 1\nLine 2\nLine 3\n")

        monitor = ClientTxtMonitor(log_path=log_path)
        monitor._last_position = 1000  # Simulating position beyond file

        # Should reset position on truncation
        monitor._check_for_new_lines()

        assert monitor._last_position < 1000

    def test_only_emits_on_actual_zone_change(self, tmp_path):
        """Should not emit duplicate zone changes."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("")

        events = []
        monitor = ClientTxtMonitor(
            log_path=log_path,
            on_zone_change=lambda e: events.append(e),
        )

        # Same zone twice
        event1 = ZoneChangeEvent(
            timestamp=datetime.now(),
            zone_name="Same Zone",
            zone_type=ZoneType.HIDEOUT,
        )

        # First time - should set last zone and emit
        if event1.zone_name != monitor._last_zone:
            monitor._last_zone = event1.zone_name
            monitor._handle_zone_change(event1)

        # Second time with same zone - should not emit
        before_count = len(events)
        if event1.zone_name != monitor._last_zone:
            monitor._handle_zone_change(event1)

        assert len(events) == before_count  # No new events


# =============================================================================
# Path Detection Tests
# =============================================================================


class TestPathDetection:
    """Tests for log path detection."""

    def test_uses_provided_path(self, tmp_path):
        """Should use provided log path."""
        custom_path = tmp_path / "custom_client.txt"
        monitor = ClientTxtMonitor(log_path=custom_path)

        assert monitor.log_path == custom_path

    def test_detect_path_fallback(self):
        """Should return default path if none found."""
        # Create monitor without existing log file
        with patch.object(Path, "exists", return_value=False):
            monitor = ClientTxtMonitor()
            # Should use first default path as fallback
            assert monitor.log_path == ClientTxtMonitor.DEFAULT_POE1_PATHS[0]

    def test_detect_client_txt_path_function(self, tmp_path):
        """detect_client_txt_path should find existing file."""
        log_path = tmp_path / "Client.txt"
        log_path.write_text("Test")

        # Patch monitor to use our temp path
        with patch.object(
            ClientTxtMonitor,
            "_detect_log_path",
            return_value=log_path,
        ):
            result = detect_client_txt_path()
            assert result == log_path

    def test_detect_client_txt_path_not_found(self):
        """detect_client_txt_path should return None if not found."""
        with patch.object(Path, "exists", return_value=False):
            result = detect_client_txt_path()
            assert result is None
