"""
Loot Session Management.

Manages the lifecycle of loot tracking sessions, coordinating between
Client.txt zone detection and stash snapshot diffing.

Sessions can be:
- Auto-detected: Based on hideout<->map transitions
- Manual: Start/stop via UI buttons

Usage:
    manager = LootSessionManager(
        league="Settlers",
        on_session_start=handle_start,
        on_drops_detected=handle_drops,
    )
    manager.start_session("Morning Farming")
    manager.on_zone_entered("Glacier Map", "map", area_level=83)
    manager.add_drops([drop1, drop2])
    manager.end_session()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from core.result import Err, Ok, Result

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """State of a loot tracking session."""

    IDLE = "idle"  # No session active
    PENDING = "pending"  # Session started, waiting for map entry
    ACTIVE = "active"  # Currently tracking a map run
    PAUSED = "paused"  # In hideout between maps
    COMPLETED = "completed"  # Session finished


@dataclass
class LootDrop:
    """
    Represents a single item drop tracked during a session.

    Stores item details along with pricing information for analytics.
    """

    id: str
    item_name: str
    item_base_type: Optional[str]
    stack_size: int
    chaos_value: float
    divine_value: float
    rarity: str
    item_class: str
    detected_at: datetime
    source_tab: Optional[str] = None
    raw_item_data: Optional[Dict[str, Any]] = None

    @property
    def total_value(self) -> float:
        """Total chaos value including stack size."""
        return self.chaos_value * self.stack_size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "item_name": self.item_name,
            "item_base_type": self.item_base_type,
            "stack_size": self.stack_size,
            "chaos_value": self.chaos_value,
            "divine_value": self.divine_value,
            "rarity": self.rarity,
            "item_class": self.item_class,
            "detected_at": self.detected_at.isoformat(),
            "source_tab": self.source_tab,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LootDrop":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            item_name=data["item_name"],
            item_base_type=data.get("item_base_type"),
            stack_size=data.get("stack_size", 1),
            chaos_value=data.get("chaos_value", 0.0),
            divine_value=data.get("divine_value", 0.0),
            rarity=data.get("rarity", "Normal"),
            item_class=data.get("item_class", ""),
            detected_at=datetime.fromisoformat(data["detected_at"]),
            source_tab=data.get("source_tab"),
        )


@dataclass
class MapRun:
    """
    Represents a single map run within a session.

    Tracks the map name, duration, and all drops found during the run.
    """

    id: str
    map_name: str
    area_level: Optional[int]
    started_at: datetime
    ended_at: Optional[datetime] = None
    drops: List[LootDrop] = field(default_factory=list)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of the map run in seconds."""
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @property
    def duration(self) -> Optional[timedelta]:
        """Duration as timedelta."""
        if self.ended_at and self.started_at:
            return self.ended_at - self.started_at
        if self.started_at:
            return datetime.now() - self.started_at
        return None

    @property
    def total_chaos_value(self) -> float:
        """Total chaos value of all drops in this map."""
        return sum(d.total_value for d in self.drops)

    @property
    def drop_count(self) -> int:
        """Number of drops in this map."""
        return len(self.drops)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "map_name": self.map_name,
            "area_level": self.area_level,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "drops": [d.to_dict() for d in self.drops],
        }


@dataclass
class LootSession:
    """
    Represents a loot tracking session.

    A session can contain multiple map runs and tracks aggregate statistics.
    Sessions persist across application restarts.
    """

    id: str
    name: str
    league: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    state: SessionState = SessionState.IDLE
    map_runs: List[MapRun] = field(default_factory=list)
    auto_detected: bool = False
    notes: str = ""

    @property
    def duration(self) -> Optional[timedelta]:
        """Total session duration."""
        if self.ended_at and self.started_at:
            return self.ended_at - self.started_at
        if self.started_at:
            return datetime.now() - self.started_at
        return None

    @property
    def duration_seconds(self) -> float:
        """Total session duration in seconds."""
        duration = self.duration
        return duration.total_seconds() if duration else 0.0

    @property
    def total_maps(self) -> int:
        """Number of maps completed in this session."""
        return len(self.map_runs)

    @property
    def total_drops(self) -> int:
        """Total number of drops across all maps."""
        return sum(run.drop_count for run in self.map_runs)

    @property
    def total_chaos_value(self) -> float:
        """Total chaos value across all maps."""
        return sum(run.total_chaos_value for run in self.map_runs)

    @property
    def chaos_per_hour(self) -> float:
        """Chaos value earned per hour."""
        duration = self.duration
        if not duration or duration.total_seconds() < 60:
            return 0.0
        hours = duration.total_seconds() / 3600
        return self.total_chaos_value / hours

    @property
    def maps_per_hour(self) -> float:
        """Maps completed per hour."""
        duration = self.duration
        if not duration or duration.total_seconds() < 60:
            return 0.0
        hours = duration.total_seconds() / 3600
        return self.total_maps / hours

    @property
    def avg_map_time_seconds(self) -> float:
        """Average time per map in seconds."""
        if not self.map_runs:
            return 0.0
        total_time = sum(
            run.duration_seconds or 0
            for run in self.map_runs
            if run.duration_seconds
        )
        completed_runs = sum(1 for run in self.map_runs if run.duration_seconds)
        return total_time / completed_runs if completed_runs else 0.0

    @property
    def avg_chaos_per_map(self) -> float:
        """Average chaos value per map."""
        if not self.map_runs:
            return 0.0
        return self.total_chaos_value / len(self.map_runs)

    @property
    def all_drops(self) -> List[LootDrop]:
        """All drops across all map runs."""
        drops = []
        for run in self.map_runs:
            drops.extend(run.drops)
        return drops

    @property
    def top_drops(self) -> List[LootDrop]:
        """Top 10 drops by value."""
        return sorted(self.all_drops, key=lambda d: d.total_value, reverse=True)[:10]

    def get_drops_by_rarity(self) -> Dict[str, int]:
        """Get drop counts grouped by rarity."""
        counts: Dict[str, int] = {}
        for drop in self.all_drops:
            rarity = drop.rarity or "Unknown"
            counts[rarity] = counts.get(rarity, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "league": self.league,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "state": self.state.value,
            "map_runs": [run.to_dict() for run in self.map_runs],
            "auto_detected": self.auto_detected,
            "notes": self.notes,
        }


class LootSessionManager:
    """
    Manages loot tracking sessions.

    Coordinates between:
    - Client.txt zone detection (auto-start/stop)
    - Stash API snapshots (diff tracking)
    - Database persistence
    - UI callbacks
    """

    def __init__(
        self,
        league: str,
        on_session_start: Optional[Callable[[LootSession], None]] = None,
        on_session_end: Optional[Callable[[LootSession], None]] = None,
        on_map_complete: Optional[Callable[[MapRun], None]] = None,
        on_drops_detected: Optional[Callable[[List[LootDrop]], None]] = None,
        on_state_change: Optional[Callable[[SessionState], None]] = None,
    ):
        """
        Initialize the session manager.

        Args:
            league: Current league name.
            on_session_start: Callback when session begins.
            on_session_end: Callback when session ends.
            on_map_complete: Callback when a map run completes.
            on_drops_detected: Callback when new drops are detected.
            on_state_change: Callback when session state changes.
        """
        self.league = league
        self.on_session_start = on_session_start
        self.on_session_end = on_session_end
        self.on_map_complete = on_map_complete
        self.on_drops_detected = on_drops_detected
        self.on_state_change = on_state_change

        self._current_session: Optional[LootSession] = None
        self._current_map_run: Optional[MapRun] = None
        self._auto_track_enabled = False

    @property
    def current_session(self) -> Optional[LootSession]:
        """Get the current active session."""
        return self._current_session

    @property
    def current_map_run(self) -> Optional[MapRun]:
        """Get the current active map run."""
        return self._current_map_run

    @property
    def is_active(self) -> bool:
        """Check if a session is currently active."""
        return (
            self._current_session is not None
            and self._current_session.state
            in (SessionState.ACTIVE, SessionState.PENDING, SessionState.PAUSED)
        )

    @property
    def is_in_map(self) -> bool:
        """Check if currently in a map run."""
        return self._current_map_run is not None

    def _set_state(self, state: SessionState):
        """Update session state and emit callback."""
        if self._current_session:
            self._current_session.state = state
            if self.on_state_change:
                try:
                    self.on_state_change(state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")

    def start_session(
        self,
        name: Optional[str] = None,
        auto_detected: bool = False,
    ) -> Result[LootSession, str]:
        """
        Start a new loot tracking session.

        Args:
            name: Session name (auto-generated if not provided).
            auto_detected: Whether session was auto-started from zone change.

        Returns:
            Result with the new session or error message.
        """
        if self._current_session and self._current_session.state in (
            SessionState.ACTIVE,
            SessionState.PENDING,
            SessionState.PAUSED,
        ):
            return Err("A session is already active")

        session_name = name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        self._current_session = LootSession(
            id=str(uuid4()),
            name=session_name,
            league=self.league,
            started_at=datetime.now(),
            state=SessionState.PENDING,
            auto_detected=auto_detected,
        )

        logger.info(f"Started loot session: {session_name}")

        if self.on_session_start:
            try:
                self.on_session_start(self._current_session)
            except Exception as e:
                logger.error(f"Session start callback error: {e}")

        return Ok(self._current_session)

    def end_session(self) -> Result[LootSession, str]:
        """
        End the current loot tracking session.

        Returns:
            Result with the ended session or error message.
        """
        if not self._current_session:
            return Err("No active session")

        # End any active map run
        if self._current_map_run:
            self._end_current_map()

        self._current_session.ended_at = datetime.now()
        self._set_state(SessionState.COMPLETED)

        _ = self._current_session

        logger.info(
            f"Ended session: {session.name} - "
            f"{session.total_maps} maps, {session.total_drops} drops, "
            f"{session.total_chaos_value:.0f}c total, "
            f"{session.chaos_per_hour:.0f}c/hr"
        )

        if self.on_session_end:
            try:
                self.on_session_end(session)
            except Exception as e:
                logger.error(f"Session end callback error: {e}")

        self._current_session = None
        return Ok(session)

    def on_zone_entered(
        self,
        zone_name: str,
        zone_type: str,
        area_level: Optional[int] = None,
    ):
        """
        Handle zone entry event from Client.txt monitor.

        Args:
            zone_name: Name of the zone entered.
            zone_type: Type of zone ("map", "hideout", "town", etc.).
            area_level: Area level if known.
        """
        # Auto-start session if enabled and entering a map
        if not self._current_session:
            if self._auto_track_enabled and zone_type == "map":
                self.start_session(auto_detected=True)
            else:
                return

        _ = self._current_session

        if zone_type == "map":
            # Entering a map - start a new map run
            if self._current_map_run:
                self._end_current_map()

            self._current_map_run = MapRun(
                id=str(uuid4()),
                map_name=zone_name,
                area_level=area_level,
                started_at=datetime.now(),
            )
            self._set_state(SessionState.ACTIVE)
            logger.debug(f"Started map run: {zone_name} (level {area_level})")

        elif zone_type == "hideout":
            # Returning to hideout - end current map run
            if self._current_map_run:
                self._end_current_map()
            self._set_state(SessionState.PAUSED)

        elif zone_type == "town":
            # In town - no action needed, might be quick visit before returning to map
            pass  # Intentional no-op: preserve state while in town

    def _end_current_map(self):
        """End the current map run and add it to the session."""
        if not self._current_map_run or not self._current_session:
            return

        self._current_map_run.ended_at = datetime.now()
        self._current_session.map_runs.append(self._current_map_run)

        if self.on_map_complete:
            try:
                self.on_map_complete(self._current_map_run)
            except Exception as e:
                logger.error(f"Map complete callback error: {e}")

        logger.debug(
            f"Completed map: {self._current_map_run.map_name} - "
            f"{self._current_map_run.drop_count} drops, "
            f"{self._current_map_run.total_chaos_value:.0f}c"
        )
        self._current_map_run = None

    def add_drops(self, drops: List[LootDrop]):
        """
        Add detected drops to the current map run.

        Args:
            drops: List of drops to add.
        """
        if not drops:
            return

        if self._current_map_run:
            self._current_map_run.drops.extend(drops)
            logger.debug(f"Added {len(drops)} drops to current map")
        elif self._current_session:
            # No active map run - might be loot from hideout/stash operations
            # Create a synthetic map run for these
            synthetic_run = MapRun(
                id=str(uuid4()),
                map_name="Hideout Activity",
                area_level=None,
                started_at=datetime.now(),
                ended_at=datetime.now(),
                drops=drops,
            )
            self._current_session.map_runs.append(synthetic_run)
            logger.debug(f"Added {len(drops)} drops to synthetic run")
        else:
            logger.warning(f"Drops detected but no active session: {len(drops)} items")
            return

        if self.on_drops_detected:
            try:
                self.on_drops_detected(drops)
            except Exception as e:
                logger.error(f"Drops detected callback error: {e}")

    def enable_auto_tracking(self, enabled: bool = True):
        """
        Enable/disable automatic session tracking based on zone changes.

        Args:
            enabled: Whether to enable auto-tracking.
        """
        self._auto_track_enabled = enabled
        logger.info(f"Auto-tracking {'enabled' if enabled else 'disabled'}")

    def is_auto_tracking_enabled(self) -> bool:
        """Check if auto-tracking is enabled."""
        return self._auto_track_enabled

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the current session.

        Returns:
            Dict with session statistics.
        """
        if not self._current_session:
            return {}

        session = self._current_session
        return {
            "id": session.id,
            "name": session.name,
            "state": session.state.value,
            "duration_minutes": session.duration_seconds / 60,
            "total_maps": session.total_maps,
            "total_drops": session.total_drops,
            "total_chaos": session.total_chaos_value,
            "chaos_per_hour": session.chaos_per_hour,
            "maps_per_hour": session.maps_per_hour,
            "avg_map_time_minutes": session.avg_map_time_seconds / 60,
            "avg_chaos_per_map": session.avg_chaos_per_map,
            "current_map": self._current_map_run.map_name if self._current_map_run else None,
        }

    def update_league(self, league: str):
        """Update the league for new sessions."""
        self.league = league


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("LOOT SESSION TEST")
    print("=" * 60)

    def on_start(session: LootSession):
        print(f"  -> Session started: {session.name}")

    def on_end(session: LootSession):
        print(f"  -> Session ended: {session.name}")
        print(f"     Maps: {session.total_maps}, Drops: {session.total_drops}")
        print(f"     Value: {session.total_chaos_value:.0f}c, Rate: {session.chaos_per_hour:.0f}c/hr")

    def on_map(run: MapRun):
        print(f"  -> Map completed: {run.map_name} - {run.drop_count} drops")

    manager = LootSessionManager(
        league="Settlers",
        on_session_start=on_start,
        on_session_end=on_end,
        on_map_complete=on_map,
    )

    # Start a session
    result = manager.start_session("Test Session")
    print(f"\nStart session result: {result}")

    # Simulate entering a map
    manager.on_zone_entered("Glacier Map", "map", area_level=83)

    # Add some drops
    drops = [
        LootDrop(
            id="1",
            item_name="Divine Orb",
            item_base_type="Currency",
            stack_size=1,
            chaos_value=150.0,
            divine_value=1.0,
            rarity="Currency",
            item_class="Currency",
            detected_at=datetime.now(),
        ),
        LootDrop(
            id="2",
            item_name="Exalted Orb",
            item_base_type="Currency",
            stack_size=2,
            chaos_value=40.0,
            divine_value=0.27,
            rarity="Currency",
            item_class="Currency",
            detected_at=datetime.now(),
        ),
    ]
    manager.add_drops(drops)

    # Return to hideout
    manager.on_zone_entered("Celestial Hideout", "hideout")

    # Run another map
    manager.on_zone_entered("Promenade Map", "map", area_level=82)
    manager.on_zone_entered("Celestial Hideout", "hideout")

    # End session
    result = manager.end_session()
    print(f"\nEnd session result: {result}")

    if result.is_ok():
        session = result.unwrap()
        print("\nSession summary:")
        print(f"  Duration: {session.duration}")
        print(f"  Maps: {session.total_maps}")
        print(f"  Drops: {session.total_drops}")
        print(f"  Total value: {session.total_chaos_value:.0f}c")
        print(f"  Rate: {session.chaos_per_hour:.0f}c/hr")
