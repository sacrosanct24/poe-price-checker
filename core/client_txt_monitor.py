"""
Client.txt Monitor for Zone Detection.

Monitors Path of Exile's Client.txt log file for zone change events to enable
automatic loot session tracking based on hideout/map transitions.

Follows the ClipboardMonitor pattern:
- Background thread with configurable polling
- Thread-safe with threading.Lock()
- Callback system for events
- Start/stop lifecycle methods

Usage:
    monitor = ClientTxtMonitor(
        on_zone_change=handle_zone_change,
        poll_interval=1.0,
    )
    monitor.start_monitoring()
    # ... later
    monitor.stop_monitoring()
"""
from __future__ import annotations

import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class ZoneType(Enum):
    """Classification of zone types in Path of Exile."""

    HIDEOUT = "hideout"
    MAP = "map"
    TOWN = "town"
    CAMPAIGN = "campaign"
    UNKNOWN = "unknown"


@dataclass
class ZoneChangeEvent:
    """Represents a zone change event detected from Client.txt."""

    timestamp: datetime
    zone_name: str
    zone_type: ZoneType
    area_level: Optional[int] = None
    raw_line: str = ""

    def __str__(self) -> str:
        level_str = f" (Level {self.area_level})" if self.area_level else ""
        return f"{self.zone_name}{level_str} [{self.zone_type.value}]"


class ClientTxtMonitor:
    """
    Monitors Path of Exile's Client.txt log file for zone change events.

    Features:
    - Background thread monitors log file for new lines
    - Parses zone entry messages to detect hideout/map transitions
    - Callbacks for zone change events
    - Thread-safe operation

    Pattern matching for PoE1/PoE2:
    - Zone entry: "You have entered [zone name]."
    - Area level: "Generating level N area..."
    """

    # Regex patterns for zone detection
    # Format: "2024/01/15 12:34:56 ... You have entered The Hideout."
    ZONE_ENTRY_PATTERN = re.compile(
        r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*You have entered (.+)\.",
        re.IGNORECASE,
    )

    # Area level pattern (appears before zone entry)
    AREA_LEVEL_PATTERN = re.compile(
        r"Generating level (\d+) area",
        re.IGNORECASE,
    )

    # Zone classification keywords
    HIDEOUT_KEYWORDS = ["hideout", "haven", "menagerie"]
    TOWN_KEYWORDS = [
        "lioneye's watch",
        "the forest encampment",
        "the sarn encampment",
        "highgate",
        "overseer's tower",
        "oriath",
        "karui shores",
        "the rogue harbour",
        # PoE2 towns
        "clearfell encampment",
        "ardura caravan",
        "the crossroads encampment",
    ]
    MAP_KEYWORDS = [
        "map",
        "the temple of atzoatl",
        "delve",
        "heist",
        "sanctum",
        "the lord's labyrinth",
        "uber",
        "simulacrum",
        "the maven's crucible",
        # PoE2 endgame
        "the trial",
        "pinnacle",
    ]

    # Default PoE log file locations
    DEFAULT_POE1_PATHS = [
        Path("C:/Program Files (x86)/Grinding Gear Games/Path of Exile/logs/Client.txt"),
        Path("C:/Program Files/Grinding Gear Games/Path of Exile/logs/Client.txt"),
        Path.home() / "Games/Path of Exile/logs/Client.txt",
    ]
    DEFAULT_POE2_PATHS = [
        Path("C:/Program Files/Grinding Gear Games/Path of Exile 2/logs/Client.txt"),
        Path("C:/Program Files (x86)/Grinding Gear Games/Path of Exile 2/logs/Client.txt"),
    ]
    STEAM_POE1_PATHS = [
        Path("C:/Program Files (x86)/Steam/steamapps/common/Path of Exile/logs/Client.txt"),
        Path("C:/Program Files/Steam/steamapps/common/Path of Exile/logs/Client.txt"),
    ]
    STEAM_POE2_PATHS = [
        Path("C:/Program Files (x86)/Steam/steamapps/common/Path of Exile 2/logs/Client.txt"),
        Path("C:/Program Files/Steam/steamapps/common/Path of Exile 2/logs/Client.txt"),
    ]

    def __init__(
        self,
        log_path: Optional[Path] = None,
        on_zone_change: Optional[Callable[[ZoneChangeEvent], None]] = None,
        poll_interval: float = 1.0,
    ):
        """
        Initialize the Client.txt monitor.

        Args:
            log_path: Path to Client.txt. If None, auto-detect.
            on_zone_change: Callback when zone change is detected.
            poll_interval: Seconds between file checks (default 1.0).
        """
        self.log_path = log_path or self._detect_log_path()
        self.on_zone_change = on_zone_change
        self.poll_interval = poll_interval

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_position = 0
        self._last_zone: Optional[str] = None
        self._pending_area_level: Optional[int] = None

        # Statistics
        self.zones_detected = 0
        self.map_entries = 0
        self.hideout_entries = 0
        self.lines_processed = 0

    def _detect_log_path(self) -> Path:
        """
        Auto-detect the Client.txt path.

        Checks common installation locations for PoE1 and PoE2.

        Returns:
            Path to Client.txt (may not exist yet).
        """
        # Check all known paths
        all_paths = (
            self.DEFAULT_POE1_PATHS
            + self.DEFAULT_POE2_PATHS
            + self.STEAM_POE1_PATHS
            + self.STEAM_POE2_PATHS
        )

        for path in all_paths:
            if path.exists():
                logger.info(f"Auto-detected Client.txt: {path}")
                return path

        # Fallback - user must configure
        logger.warning("Could not auto-detect Client.txt location")
        return self.DEFAULT_POE1_PATHS[0]

    def _classify_zone(self, zone_name: str) -> ZoneType:
        """
        Classify a zone by its name.

        Args:
            zone_name: The zone name from the log.

        Returns:
            ZoneType classification.
        """
        zone_lower = zone_name.lower()

        # Check hideout first (most specific)
        if any(kw in zone_lower for kw in self.HIDEOUT_KEYWORDS):
            return ZoneType.HIDEOUT

        # Check towns
        if any(kw in zone_lower for kw in self.TOWN_KEYWORDS):
            return ZoneType.TOWN

        # Check maps/endgame
        if any(kw in zone_lower for kw in self.MAP_KEYWORDS):
            return ZoneType.MAP

        # Heuristic: act areas are campaign
        if re.match(r"^the .+$", zone_lower) or "act " in zone_lower:
            return ZoneType.CAMPAIGN

        # Unknown areas default to campaign during leveling
        # or map during endgame - we'll treat as unknown
        return ZoneType.UNKNOWN

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """
        Parse a timestamp from a log line.

        Args:
            ts_str: Timestamp string in format "2024/01/15 12:34:56"

        Returns:
            Parsed datetime, or current time if parsing fails.
        """
        try:
            return datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            return datetime.now()

    def _parse_log_line(self, line: str) -> Optional[ZoneChangeEvent]:
        """
        Parse a log line for zone change information.

        Args:
            line: A single line from Client.txt

        Returns:
            ZoneChangeEvent if zone entry found, None otherwise.
        """
        # Check for area level (store for next zone entry)
        level_match = self.AREA_LEVEL_PATTERN.search(line)
        if level_match:
            self._pending_area_level = int(level_match.group(1))
            return None

        # Check for zone entry
        match = self.ZONE_ENTRY_PATTERN.search(line)
        if not match:
            return None

        timestamp_str = match.group(1)
        zone_name = match.group(2).strip()
        zone_type = self._classify_zone(zone_name)

        # Use pending area level if we have one
        area_level = self._pending_area_level
        self._pending_area_level = None

        return ZoneChangeEvent(
            timestamp=self._parse_timestamp(timestamp_str),
            zone_name=zone_name,
            zone_type=zone_type,
            area_level=area_level,
            raw_line=line.strip(),
        )

    def _poll_loop(self):
        """Background thread loop that polls the log file for changes."""
        logger.info(f"Client.txt monitor started: {self.log_path}")

        # Start from end of file to avoid processing old entries
        try:
            if self.log_path.exists():
                self._last_position = self.log_path.stat().st_size
                logger.debug(f"Starting from position {self._last_position}")
        except OSError as e:
            logger.warning(f"Could not get initial file size: {e}")

        while self._running:
            try:
                self._check_for_new_lines()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Client.txt poll error: {e}")
                time.sleep(5.0)  # Longer delay on error

        logger.info("Client.txt monitor stopped")

    def _check_for_new_lines(self):
        """Check for new lines in the log file."""
        if not self.log_path.exists():
            return

        try:
            current_size = self.log_path.stat().st_size

            # Handle file truncation/rotation
            if current_size < self._last_position:
                logger.info("Client.txt was truncated, starting from beginning")
                self._last_position = 0

            # No new content
            if current_size <= self._last_position:
                return

            # Read new lines
            with open(
                self.log_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                f.seek(self._last_position)
                new_lines = f.readlines()
                self._last_position = f.tell()

            # Process each line
            for line in new_lines:
                self.lines_processed += 1
                event = self._parse_log_line(line)

                # Only emit if zone actually changed
                if event and event.zone_name != self._last_zone:
                    self._last_zone = event.zone_name
                    self._handle_zone_change(event)

        except OSError as e:
            logger.debug(f"Error reading log file: {e}")

    def _handle_zone_change(self, event: ZoneChangeEvent):
        """
        Handle a detected zone change.

        Args:
            event: The zone change event to handle.
        """
        with self._lock:
            self.zones_detected += 1
            if event.zone_type == ZoneType.MAP:
                self.map_entries += 1
            elif event.zone_type == ZoneType.HIDEOUT:
                self.hideout_entries += 1

        logger.info(f"Zone change: {event}")

        if self.on_zone_change:
            try:
                self.on_zone_change(event)
            except Exception as e:
                logger.error(f"Zone change callback error: {e}")

    def start_monitoring(self) -> bool:
        """
        Start background log file monitoring.

        Returns:
            True if started successfully, False if already running.
        """
        if self._running:
            logger.warning("Client.txt monitor already running")
            return False

        if not self.log_path.exists():
            logger.warning(f"Client.txt not found at {self.log_path}")
            # Continue anyway - file might appear when game starts

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="ClientTxtMonitor",
        )
        self._monitor_thread.start()
        return True

    def stop_monitoring(self):
        """Stop background log file monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    @property
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running

    def get_stats(self) -> dict:
        """
        Get monitoring statistics.

        Returns:
            Dict with monitoring stats.
        """
        return {
            "running": self._running,
            "log_path": str(self.log_path),
            "log_exists": self.log_path.exists(),
            "zones_detected": self.zones_detected,
            "map_entries": self.map_entries,
            "hideout_entries": self.hideout_entries,
            "lines_processed": self.lines_processed,
            "last_zone": self._last_zone,
        }

    def get_last_zone(self) -> Optional[str]:
        """Get the last detected zone name."""
        return self._last_zone

    def cleanup(self):
        """Clean up resources."""
        self.stop_monitoring()


def detect_client_txt_path() -> Optional[Path]:
    """
    Utility function to detect Client.txt path without creating a monitor.

    Returns:
        Path to Client.txt if found, None otherwise.
    """
    monitor = ClientTxtMonitor()
    path = monitor.log_path
    if path.exists():
        return path
    return None


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("CLIENT.TXT MONITOR TEST")
    print("=" * 60)

    def on_zone(event: ZoneChangeEvent):
        print(f"  -> Zone change: {event}")

    monitor = ClientTxtMonitor(on_zone_change=on_zone)

    print(f"\nLog path: {monitor.log_path}")
    print(f"Log exists: {monitor.log_path.exists()}")

    # Test zone classification
    print("\nTesting zone classification:")
    test_zones = [
        "Karui Shores",
        "The Blood Aqueduct",
        "Glacier Map",
        "Celestial Hideout",
        "The Temple of Atzoatl",
        "The Rogue Harbour",
        "Some Random Zone",
    ]
    for zone in test_zones:
        zone_type = monitor._classify_zone(zone)
        print(f"  {zone}: {zone_type.value}")

    # Test log line parsing
    print("\nTesting log line parsing:")
    test_lines = [
        "2024/01/15 12:34:56 123456 [INFO Client 1234] : You have entered Celestial Hideout.",
        "2024/01/15 12:35:00 123456 [DEBUG Client 1234] Generating level 83 area",
        "2024/01/15 12:35:01 123456 [INFO Client 1234] : You have entered Glacier Map.",
        "Some random log line that doesn't match",
    ]
    for line in test_lines:
        event = monitor._parse_log_line(line)
        if event:
            print(f"  Parsed: {event}")
        else:
            print(f"  No match: {line[:50]}...")

    # Interactive monitoring test
    if monitor.log_path.exists():
        print("\nStarting live monitoring (press Ctrl+C to stop)...")
        monitor.start_monitoring()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass  # User requested exit, continue to cleanup
        monitor.stop_monitoring()
    else:
        print("\nClient.txt not found - skipping live test")

    print("\n" + "=" * 60)
    print("Stats:", monitor.get_stats())
