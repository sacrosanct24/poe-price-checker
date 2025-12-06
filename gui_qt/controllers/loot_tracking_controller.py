"""
Loot Tracking Controller - Coordinates loot tracking workflow.

Integrates:
- ClientTxtMonitor for zone detection
- LootSessionManager for session state
- StashDiffEngine for loot detection
- Workers for background stash fetching
- Database persistence

Usage:
    controller = LootTrackingController(ctx)
    controller.session_started.connect(self._on_session_started)
    controller.drops_detected.connect(self._on_drops_detected)
    controller.start_monitoring()
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

from PyQt6.QtCore import QObject, pyqtSignal

from core.client_txt_monitor import ClientTxtMonitor, ZoneChangeEvent, ZoneType
from core.loot_session import (
    LootDrop,
    LootSession,
    LootSessionManager,
    MapRun,
    SessionState,
)
from core.result import Err, Ok, Result
from core.stash_diff_engine import (
    StashDiff,
    StashDiffEngine,
    extract_item_value,
    get_rarity_name,
)
from gui_qt.workers.loot_tracking_worker import (
    LootValuationWorker,
    StashDiffWorker,
    StashSnapshotWorker,
)

if TYPE_CHECKING:
    from core.interfaces import IAppContext
    from data_sources.poe_stash_api import StashSnapshot

logger = logging.getLogger(__name__)


class LootTrackingController(QObject):
    """
    Controller for loot tracking workflow.

    Coordinates zone detection, session management, stash diffing, and
    UI updates through Qt signals.

    Signals:
        session_started(LootSession): Emitted when a session begins.
        session_ended(LootSession): Emitted when a session ends.
        session_state_changed(str): Emitted when session state changes.
        map_started(MapRun): Emitted when entering a map.
        map_completed(MapRun): Emitted when leaving a map.
        drops_detected(list): Emitted with list of LootDrop objects.
        snapshot_started(): Emitted when stash fetch begins.
        snapshot_completed(int): Emitted with item count on fetch complete.
        snapshot_error(str): Emitted on stash fetch error.
        status_message(str): Emitted with status updates.
        stats_updated(dict): Emitted with current session stats.
    """

    # Session signals
    session_started = pyqtSignal(object)  # LootSession
    session_ended = pyqtSignal(object)  # LootSession
    session_state_changed = pyqtSignal(str)
    map_started = pyqtSignal(object)  # MapRun
    map_completed = pyqtSignal(object)  # MapRun

    # Loot signals
    drops_detected = pyqtSignal(list)  # List[LootDrop]
    high_value_drop = pyqtSignal(object)  # LootDrop

    # Snapshot signals
    snapshot_started = pyqtSignal()
    snapshot_completed = pyqtSignal(int)  # item count
    snapshot_error = pyqtSignal(str)

    # Status signals
    status_message = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)

    def __init__(
        self,
        ctx: "IAppContext",
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the loot tracking controller.

        Args:
            ctx: Application context with config, database, etc.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._ctx = ctx
        self._config = ctx.config

        # Get config values
        self._league = self._config.league
        self._poesessid = self._config.poesessid
        self._account_name = self._config.account_name

        # Initialize components
        self._client_monitor: Optional[ClientTxtMonitor] = None
        self._session_manager = LootSessionManager(
            league=self._league,
            on_session_start=self._on_session_start,
            on_session_end=self._on_session_end,
            on_map_complete=self._on_map_complete,
            on_drops_detected=self._on_drops_detected,
            on_state_change=self._on_state_change,
        )
        self._diff_engine = StashDiffEngine(
            tracked_tabs=self._config.loot_tracked_tabs or None,
        )

        # Snapshot state
        self._before_snapshot: Optional["StashSnapshot"] = None
        self._pending_snapshot_type: Optional[str] = None  # "before" or "after"

        # Active workers
        self._snapshot_worker: Optional[StashSnapshotWorker] = None
        self._diff_worker: Optional[StashDiffWorker] = None
        self._valuation_worker: Optional[LootValuationWorker] = None

        # Stats tracking
        self._monitoring_started_at: Optional[datetime] = None

    # =========================================================================
    # Public API
    # =========================================================================

    def start_monitoring(self) -> Result[bool, str]:
        """
        Start Client.txt monitoring for zone detection.

        Returns:
            Result with True on success, error message on failure.
        """
        if self._client_monitor and self._client_monitor.is_running:
            return Err("Monitoring already active")

        # Get log path from config or auto-detect
        log_path_str = self._config.loot_client_txt_path
        log_path = Path(log_path_str) if log_path_str else None

        self._client_monitor = ClientTxtMonitor(
            log_path=log_path,
            on_zone_change=self._on_zone_change,
            poll_interval=self._config.loot_poll_interval,
        )

        if not self._client_monitor.start_monitoring():
            return Err("Failed to start Client.txt monitoring")

        self._monitoring_started_at = datetime.now()
        self.status_message.emit("Zone monitoring started")
        logger.info(f"Started monitoring: {self._client_monitor.log_path}")

        return Ok(True)

    def stop_monitoring(self):
        """Stop Client.txt monitoring."""
        if self._client_monitor:
            self._client_monitor.stop_monitoring()
            self._client_monitor = None
            self.status_message.emit("Zone monitoring stopped")
            logger.info("Stopped monitoring")

    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._client_monitor is not None and self._client_monitor.is_running

    def start_session(self, name: Optional[str] = None) -> Result[LootSession, str]:
        """
        Manually start a loot tracking session.

        Args:
            name: Optional session name.

        Returns:
            Result with the new session or error message.
        """
        if not self._poesessid:
            return Err("POESESSID not configured")
        if not self._account_name:
            return Err("Account name not configured")

        result = self._session_manager.start_session(name=name, auto_detected=False)
        if result.is_ok():
            # Take initial stash snapshot
            self._take_snapshot("before")
        return result

    def end_session(self) -> Result[LootSession, str]:
        """
        End the current session.

        Returns:
            Result with the ended session or error message.
        """
        result = self._session_manager.end_session()
        if result.is_ok():
            session = result.unwrap()
            self._save_session_to_db(session)
        return result

    def enable_auto_tracking(self, enabled: bool = True):
        """
        Enable/disable automatic session tracking.

        When enabled, sessions start automatically on map entry
        and snapshots are taken on hideout<->map transitions.

        Args:
            enabled: Whether to enable auto-tracking.
        """
        self._session_manager.enable_auto_tracking(enabled)
        state = "enabled" if enabled else "disabled"
        self.status_message.emit(f"Auto-tracking {state}")

    def is_auto_tracking_enabled(self) -> bool:
        """Check if auto-tracking is enabled."""
        return self._session_manager.is_auto_tracking_enabled()

    def take_manual_snapshot(self):
        """Take a manual stash snapshot (for diff comparison)."""
        if self._before_snapshot is None:
            self._take_snapshot("before")
        else:
            self._take_snapshot("after")

    def get_current_session(self) -> Optional[LootSession]:
        """Get the current active session."""
        return self._session_manager.current_session

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for the current session."""
        return self._session_manager.get_session_stats()

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get Client.txt monitoring statistics."""
        if self._client_monitor:
            return self._client_monitor.get_stats()
        return {"running": False}

    def update_config(self):
        """Reload configuration values."""
        self._league = self._config.league
        self._poesessid = self._config.poesessid
        self._account_name = self._config.account_name
        self._session_manager.update_league(self._league)

        # Update tracked tabs
        tracked = self._config.loot_tracked_tabs
        self._diff_engine = StashDiffEngine(
            tracked_tabs=tracked or None,
        )

    def cleanup(self):
        """Clean up resources."""
        self.stop_monitoring()
        self._cancel_workers()

    # =========================================================================
    # Zone Change Handling
    # =========================================================================

    def _on_zone_change(self, event: ZoneChangeEvent):
        """
        Handle zone change events from Client.txt monitor.

        Args:
            event: The zone change event.
        """
        logger.debug(f"Zone change: {event}")
        self.status_message.emit(f"Entered: {event.zone_name}")

        # Forward to session manager
        self._session_manager.on_zone_entered(
            zone_name=event.zone_name,
            zone_type=event.zone_type.value,
            area_level=event.area_level,
        )

        # Handle snapshots based on zone type
        if self._session_manager.is_active:
            if event.zone_type == ZoneType.MAP:
                # Entering a map - before snapshot should already be taken
                self.map_started.emit(self._session_manager.current_map_run)

            elif event.zone_type == ZoneType.HIDEOUT:
                # Returning to hideout - take after snapshot
                self._take_snapshot("after")

    # =========================================================================
    # Session Manager Callbacks
    # =========================================================================

    def _on_session_start(self, session: LootSession):
        """Handle session start."""
        logger.info(f"Session started: {session.name}")
        self.session_started.emit(session)
        self._emit_stats()

    def _on_session_end(self, session: LootSession):
        """Handle session end."""
        logger.info(f"Session ended: {session.name}")
        self.session_ended.emit(session)
        self._clear_snapshot_state()

    def _on_map_complete(self, map_run: MapRun):
        """Handle map completion."""
        logger.info(f"Map completed: {map_run.map_name}")
        self.map_completed.emit(map_run)
        self._emit_stats()

    def _on_drops_detected(self, drops: List[LootDrop]):
        """Handle new drops detected."""
        logger.info(f"Drops detected: {len(drops)} items")
        self.drops_detected.emit(drops)

        # Check for high-value drops
        threshold = self._config.loot_high_value_threshold
        for drop in drops:
            if drop.chaos_value >= threshold:
                self.high_value_drop.emit(drop)

        self._emit_stats()

    def _on_state_change(self, state: SessionState):
        """Handle session state change."""
        self.session_state_changed.emit(state.value)

    # =========================================================================
    # Stash Snapshot Operations
    # =========================================================================

    def _take_snapshot(self, snapshot_type: str):
        """
        Take a stash snapshot in the background.

        Args:
            snapshot_type: "before" or "after"
        """
        if not self._poesessid or not self._account_name:
            self.snapshot_error.emit("Missing POESESSID or account name")
            return

        if self._snapshot_worker is not None:
            logger.warning("Snapshot already in progress")
            return

        self._pending_snapshot_type = snapshot_type
        self.snapshot_started.emit()
        self.status_message.emit(f"Taking {snapshot_type} snapshot...")

        # Get tracked tabs
        tracked_tabs = self._config.loot_tracked_tabs or None

        self._snapshot_worker = StashSnapshotWorker(
            poesessid=self._poesessid,
            account_name=self._account_name,
            league=self._league,
            tracked_tabs=tracked_tabs,
            parent=self,
        )

        self._snapshot_worker.result.connect(self._on_snapshot_result)
        self._snapshot_worker.error.connect(self._on_snapshot_error)
        self._snapshot_worker.status.connect(
            lambda msg: self.status_message.emit(msg)
        )
        self._snapshot_worker.start()

    def _on_snapshot_result(self, snapshot: "StashSnapshot"):
        """Handle successful snapshot."""
        self._snapshot_worker = None
        item_count = snapshot.total_items
        snapshot_type = self._pending_snapshot_type

        logger.info(f"{snapshot_type} snapshot complete: {item_count} items")
        self.snapshot_completed.emit(item_count)
        self.status_message.emit(f"Snapshot: {item_count} items")

        if snapshot_type == "before":
            self._before_snapshot = snapshot
            self._diff_engine.set_before_snapshot(snapshot)

        elif snapshot_type == "after" and self._before_snapshot is not None:
            # Compute diff
            self._compute_diff(snapshot)

        self._pending_snapshot_type = None

    def _on_snapshot_error(self, message: str, traceback: str):
        """Handle snapshot error."""
        self._snapshot_worker = None
        self._pending_snapshot_type = None
        logger.error(f"Snapshot failed: {message}")
        self.snapshot_error.emit(message)
        self.status_message.emit(f"Snapshot error: {message}")

    def _compute_diff(self, after_snapshot: "StashSnapshot"):
        """
        Compute diff between before and after snapshots.

        Args:
            after_snapshot: The after snapshot to compare.
        """
        if self._diff_worker is not None:
            logger.warning("Diff already in progress")
            return

        self.status_message.emit("Computing loot diff...")

        self._diff_worker = StashDiffWorker(
            before_snapshot=self._before_snapshot,
            after_snapshot=after_snapshot,
            tracked_tabs=self._config.loot_tracked_tabs or None,
            parent=self,
        )

        self._diff_worker.result.connect(self._on_diff_result)
        self._diff_worker.error.connect(self._on_diff_error)
        self._diff_worker.start()

    def _on_diff_result(self, diff: StashDiff):
        """Handle diff computation result."""
        self._diff_worker = None

        if not diff.has_changes:
            self.status_message.emit("No changes detected")
            return

        logger.info(f"Diff result: {diff.get_summary()}")
        self.status_message.emit(f"Diff: {diff.get_summary()}")

        # Convert added items to LootDrops
        if diff.added_items:
            self._process_loot_items(diff.added_items)

        # Reset for next comparison
        self._before_snapshot = None
        self._diff_engine.clear()

    def _on_diff_error(self, message: str, traceback: str):
        """Handle diff error."""
        self._diff_worker = None
        logger.error(f"Diff failed: {message}")
        self.status_message.emit(f"Diff error: {message}")

    def _process_loot_items(self, items: List[Dict[str, Any]]):
        """
        Convert raw items to LootDrops and add to session.

        Args:
            items: Raw item dicts from stash API.
        """
        drops: List[LootDrop] = []
        min_value = self._config.loot_min_value

        for item in items:
            extracted = extract_item_value(item)

            # TODO: Look up actual prices from poe.ninja
            # For now, assign placeholder values
            chaos_value = self._estimate_item_value(item)

            if chaos_value < min_value:
                continue

            drop = LootDrop(
                id=str(uuid4()),
                item_name=extracted["display_name"],
                item_base_type=extracted["base_type"],
                stack_size=extracted["stack_size"],
                chaos_value=chaos_value,
                divine_value=chaos_value / 150.0,  # Approximate
                rarity=get_rarity_name(extracted["rarity"]),
                item_class=self._get_item_class(item),
                detected_at=datetime.now(),
                raw_item_data=item,
            )
            drops.append(drop)

        if drops:
            self._session_manager.add_drops(drops)

    def _estimate_item_value(self, item: Dict[str, Any]) -> float:
        """
        Estimate item value (placeholder until price service integration).

        Args:
            item: Raw item dict.

        Returns:
            Estimated chaos value.
        """
        # Basic heuristics based on rarity
        frame_type = item.get("frameType", 0)
        stack_size = item.get("stackSize", 1)

        if frame_type == 3:  # Unique
            return 10.0
        elif frame_type == 5:  # Currency
            # Some basic currency values
            type_line = item.get("typeLine", "").lower()
            if "divine" in type_line:
                return 150.0 * stack_size
            elif "exalted" in type_line:
                return 40.0 * stack_size
            elif "chaos" in type_line:
                return 1.0 * stack_size
            elif "ancient" in type_line:
                return 20.0 * stack_size
            elif "annul" in type_line:
                return 15.0 * stack_size
            return 0.5 * stack_size
        elif frame_type == 6:  # Divination Card
            return 5.0 * stack_size
        elif frame_type == 4:  # Gem
            return 2.0

        return 0.0

    def _get_item_class(self, item: Dict[str, Any]) -> str:
        """Get item class from raw item data."""
        # Try explicit field first
        if "itemClass" in item:
            return str(item["itemClass"])

        # Infer from frame type
        frame_type = item.get("frameType", 0)
        if frame_type == 4:
            return "Gem"
        elif frame_type == 5:
            return "Currency"
        elif frame_type == 6:
            return "Divination Card"

        return "Unknown"

    # =========================================================================
    # Database Operations
    # =========================================================================

    def _save_session_to_db(self, session: LootSession):
        """
        Save a completed session to the database.

        Args:
            session: The session to save.
        """
        try:
            db = self._ctx.db
            cursor = db.conn.cursor()

            # Insert session
            cursor.execute(
                """
                INSERT INTO loot_sessions (
                    id, name, league, started_at, ended_at, state,
                    total_maps, total_drops, total_chaos_value,
                    chaos_per_hour, auto_detected, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.name,
                    session.league,
                    session.started_at.isoformat(),
                    session.ended_at.isoformat() if session.ended_at else None,
                    session.state.value,
                    session.total_maps,
                    session.total_drops,
                    session.total_chaos_value,
                    session.chaos_per_hour,
                    session.auto_detected,
                    session.notes,
                ),
            )

            # Insert map runs
            for map_run in session.map_runs:
                cursor.execute(
                    """
                    INSERT INTO loot_map_runs (
                        id, session_id, map_name, area_level,
                        started_at, ended_at, drop_count, total_chaos_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        map_run.id,
                        session.id,
                        map_run.map_name,
                        map_run.area_level,
                        map_run.started_at.isoformat(),
                        map_run.ended_at.isoformat() if map_run.ended_at else None,
                        map_run.drop_count,
                        map_run.total_chaos_value,
                    ),
                )

                # Insert drops
                for drop in map_run.drops:
                    cursor.execute(
                        """
                        INSERT INTO loot_drops (
                            id, session_id, map_run_id, item_name,
                            item_base_type, stack_size, chaos_value,
                            divine_value, rarity, item_class, detected_at,
                            source_tab, raw_item_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            drop.id,
                            session.id,
                            map_run.id,
                            drop.item_name,
                            drop.item_base_type,
                            drop.stack_size,
                            drop.chaos_value,
                            drop.divine_value,
                            drop.rarity,
                            drop.item_class,
                            drop.detected_at.isoformat(),
                            drop.source_tab,
                            None,  # Skip raw data for now
                        ),
                    )

            db.conn.commit()
            logger.info(f"Saved session to database: {session.id}")

        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def load_session_history(
        self,
        limit: int = 50,
        league: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load session history from the database.

        Args:
            limit: Maximum sessions to return.
            league: Optional league filter.

        Returns:
            List of session summary dicts.
        """
        try:
            db = self._ctx.db
            cursor = db.conn.cursor()

            query = """
                SELECT id, name, league, started_at, ended_at,
                       total_maps, total_drops, total_chaos_value, chaos_per_hour
                FROM loot_sessions
                WHERE (:league IS NULL OR league = :league)
                ORDER BY started_at DESC
                LIMIT :limit
            """
            cursor.execute(
                query,
                {"league": league or self._league, "limit": limit},
            )

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row[0],
                    "name": row[1],
                    "league": row[2],
                    "started_at": row[3],
                    "ended_at": row[4],
                    "total_maps": row[5],
                    "total_drops": row[6],
                    "total_chaos_value": row[7],
                    "chaos_per_hour": row[8],
                })

            return sessions

        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            return []

    def load_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load full details for a session.

        Args:
            session_id: ID of the session to load.

        Returns:
            Dict with session details, or None if not found.
        """
        try:
            db = self._ctx.db
            cursor = db.conn.cursor()

            # Get session
            cursor.execute(
                "SELECT * FROM loot_sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            # Get map runs
            cursor.execute(
                "SELECT * FROM loot_map_runs WHERE session_id = ? ORDER BY started_at",
                (session_id,),
            )
            map_runs = cursor.fetchall()

            # Get top drops
            cursor.execute(
                """
                SELECT * FROM loot_drops
                WHERE session_id = ?
                ORDER BY chaos_value DESC
                LIMIT 20
                """,
                (session_id,),
            )
            top_drops = cursor.fetchall()

            return {
                "session": dict(row) if hasattr(row, "keys") else row,
                "map_runs": [dict(r) if hasattr(r, "keys") else r for r in map_runs],
                "top_drops": [dict(d) if hasattr(d, "keys") else d for d in top_drops],
            }

        except Exception as e:
            logger.error(f"Failed to load session details: {e}")
            return None

    # =========================================================================
    # Helpers
    # =========================================================================

    def _emit_stats(self):
        """Emit current session stats."""
        stats = self._session_manager.get_session_stats()
        if stats:
            self.stats_updated.emit(stats)

    def _clear_snapshot_state(self):
        """Clear snapshot state after session ends."""
        self._before_snapshot = None
        self._pending_snapshot_type = None
        self._diff_engine.clear()

    def _cancel_workers(self):
        """Cancel any active workers."""
        if self._snapshot_worker:
            self._snapshot_worker.cancel()
            self._snapshot_worker = None

        if self._diff_worker:
            self._diff_worker.cancel()
            self._diff_worker = None

        if self._valuation_worker:
            self._valuation_worker.cancel()
            self._valuation_worker = None
