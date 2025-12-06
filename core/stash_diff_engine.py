"""
Stash Diff Engine for Detecting New Loot.

Compares stash snapshots taken before and after map runs to identify
items that were added (loot) or removed (sales/crafting).

Usage:
    engine = StashDiffEngine()
    engine.set_before_snapshot(before_snapshot)
    diff = engine.compute_diff(after_snapshot)

    for item in diff.added_items:
        print(f"New loot: {item.get('typeLine')}")
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from data_sources.poe_stash_api import StashSnapshot, StashTab

logger = logging.getLogger(__name__)


@dataclass
class ItemFingerprint:
    """
    Unique identifier for a stash item based on its properties.

    Creates a fingerprint that can identify the same item across snapshots,
    even if it moves within the same tab. Items are matched by content rather
    than just position.
    """

    name: str
    base_type: str
    stack_size: int
    position: Tuple[int, int]  # (x, y) in tab
    tab_id: str
    item_hash: str  # Hash of relevant properties
    rarity: int = 0
    ilvl: int = 0

    @classmethod
    def from_item(cls, item: Dict[str, Any], tab_id: str) -> "ItemFingerprint":
        """
        Create fingerprint from raw stash item data.

        Args:
            item: Raw item dict from stash API.
            tab_id: ID of the tab containing this item.

        Returns:
            ItemFingerprint for the item.
        """
        # Get item name (can be empty for white items)
        name = item.get("name", "") or ""
        base_type = item.get("typeLine", "") or ""
        stack_size = item.get("stackSize", 1)
        x = item.get("x", 0)
        y = item.get("y", 0)
        rarity = item.get("frameType", 0)
        ilvl = item.get("ilvl", 0)

        # Create hash from stable properties
        # Include mods for unique identification of rares
        hash_parts = [
            name,
            base_type,
            str(ilvl),
            str(rarity),
            tab_id,
        ]

        # Add explicit mods for rare items to differentiate
        if "explicitMods" in item:
            hash_parts.extend(sorted(item["explicitMods"]))

        # Add implicit mods
        if "implicitMods" in item:
            hash_parts.extend(sorted(item["implicitMods"]))

        # Add sockets if present
        if "sockets" in item:
            socket_str = "".join(
                f"{s.get('group', 0)}{s.get('sColour', '')}"
                for s in item.get("sockets", [])
            )
            hash_parts.append(socket_str)

        hash_input = "|".join(hash_parts)
        item_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        return cls(
            name=name,
            base_type=base_type,
            stack_size=stack_size,
            position=(x, y),
            tab_id=tab_id,
            item_hash=item_hash,
            rarity=rarity,
            ilvl=ilvl,
        )

    @property
    def display_name(self) -> str:
        """Get display name for the item."""
        if self.name:
            return f"{self.name} {self.base_type}".strip()
        return self.base_type

    @property
    def position_key(self) -> str:
        """Get a key based on position in tab."""
        return f"{self.tab_id}:{self.position[0]},{self.position[1]}"

    @property
    def content_key(self) -> str:
        """Get a key based on item content (position-independent)."""
        return f"{self.tab_id}:{self.item_hash}"


@dataclass
class StackChange:
    """Represents a change in stack size for an item."""

    item: Dict[str, Any]
    delta: int  # Positive = gained, negative = lost
    fingerprint: "ItemFingerprint"

    @property
    def is_gain(self) -> bool:
        return self.delta > 0

    @property
    def is_loss(self) -> bool:
        return self.delta < 0


@dataclass
class StashDiff:
    """Result of comparing two stash snapshots."""

    added_items: List[Dict[str, Any]] = field(default_factory=list)
    removed_items: List[Dict[str, Any]] = field(default_factory=list)
    stack_changes: List[StackChange] = field(default_factory=list)
    before_total_items: int = 0
    after_total_items: int = 0
    computed_at: datetime = field(default_factory=datetime.now)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return bool(self.added_items or self.removed_items or self.stack_changes)

    @property
    def loot_count(self) -> int:
        """Number of new items (potential loot)."""
        return len(self.added_items) + sum(
            1 for sc in self.stack_changes if sc.is_gain
        )

    @property
    def items_gained(self) -> int:
        """Total items gained (including stack increases)."""
        added = len(self.added_items)
        stack_gains = sum(sc.delta for sc in self.stack_changes if sc.is_gain)
        return added + stack_gains

    @property
    def items_lost(self) -> int:
        """Total items lost (including stack decreases)."""
        removed = len(self.removed_items)
        stack_losses = sum(abs(sc.delta) for sc in self.stack_changes if sc.is_loss)
        return removed + stack_losses

    def get_summary(self) -> str:
        """Get a summary string of changes."""
        parts = []
        if self.added_items:
            parts.append(f"+{len(self.added_items)} new")
        if self.removed_items:
            parts.append(f"-{len(self.removed_items)} removed")
        if self.stack_changes:
            gains = sum(1 for sc in self.stack_changes if sc.is_gain)
            losses = sum(1 for sc in self.stack_changes if sc.is_loss)
            if gains:
                parts.append(f"+{gains} stacks increased")
            if losses:
                parts.append(f"-{losses} stacks decreased")
        return ", ".join(parts) if parts else "No changes"


class StashDiffEngine:
    """
    Engine for comparing stash snapshots to detect loot.

    Identifies added and removed items between two points in time,
    handling stack size changes for stackable items.

    Usage:
        engine = StashDiffEngine()
        engine.set_before_snapshot(snapshot1)
        diff = engine.compute_diff(snapshot2)

        for item in diff.added_items:
            # Process new loot
            pass
    """

    def __init__(
        self,
        tracked_tabs: Optional[List[str]] = None,
        ignore_currency_changes: bool = False,
    ):
        """
        Initialize the diff engine.

        Args:
            tracked_tabs: Optional list of tab names to track.
                         If None, tracks all tabs.
            ignore_currency_changes: If True, ignore small currency stack changes.
        """
        self._tracked_tabs: Optional[Set[str]] = (
            set(tracked_tabs) if tracked_tabs else None
        )
        self._ignore_currency_changes = ignore_currency_changes
        self._before_snapshot: Optional["StashSnapshot"] = None
        self._before_fingerprints: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]] = {}
        self._before_position_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]] = {}

    def _should_track_tab(self, tab_name: str) -> bool:
        """Check if a tab should be tracked."""
        if self._tracked_tabs is None:
            return True
        return tab_name in self._tracked_tabs

    def set_before_snapshot(self, snapshot: "StashSnapshot"):
        """
        Set the 'before' snapshot for comparison.

        Args:
            snapshot: The stash state before the map run.
        """
        self._before_snapshot = snapshot
        self._before_fingerprints = {}
        self._before_position_map = {}

        self._build_fingerprint_maps(
            snapshot,
            self._before_fingerprints,
            self._before_position_map,
        )

        total_items = len(self._before_fingerprints)
        logger.debug(f"Set before snapshot: {total_items} items tracked")

    def _build_fingerprint_maps(
        self,
        snapshot: "StashSnapshot",
        content_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]],
        position_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]],
    ):
        """
        Build fingerprint maps for a snapshot.

        Args:
            snapshot: Stash snapshot to process.
            content_map: Map to fill with content-based keys.
            position_map: Map to fill with position-based keys.
        """
        for tab in snapshot.tabs:
            if not self._should_track_tab(tab.name):
                continue

            self._process_tab_items(tab, content_map, position_map)

            # Process child tabs (for folder stashes)
            for child in tab.children:
                self._process_tab_items(child, content_map, position_map)

    def _process_tab_items(
        self,
        tab: "StashTab",
        content_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]],
        position_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]],
    ):
        """Process items from a single tab."""
        for item in tab.items:
            fp = ItemFingerprint.from_item(item, tab.id)

            # Store by content (for detecting same items)
            content_key = fp.content_key
            if content_key not in content_map:
                content_map[content_key] = (fp, item)

            # Store by position (for detecting moves)
            position_key = fp.position_key
            position_map[position_key] = (fp, item)

    def compute_diff(self, after_snapshot: "StashSnapshot") -> StashDiff:
        """
        Compute the diff between before and after snapshots.

        Args:
            after_snapshot: The 'after' stash state.

        Returns:
            StashDiff with added, removed, and changed items.
        """
        if not self._before_snapshot:
            logger.warning("No before snapshot set - returning empty diff")
            return StashDiff()

        # Build maps for after snapshot
        after_content_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]] = {}
        after_position_map: Dict[str, Tuple[ItemFingerprint, Dict[str, Any]]] = {}

        self._build_fingerprint_maps(
            after_snapshot,
            after_content_map,
            after_position_map,
        )

        # Compare content maps
        before_keys = set(self._before_fingerprints.keys())
        after_keys = set(after_content_map.keys())

        added_keys = after_keys - before_keys
        removed_keys = before_keys - after_keys
        common_keys = before_keys & after_keys

        added_items: List[Dict[str, Any]] = []
        removed_items: List[Dict[str, Any]] = []
        stack_changes: List[StackChange] = []

        # Process added items
        for key in added_keys:
            fp, item = after_content_map[key]
            added_items.append(item)
            logger.debug(f"Added: {fp.display_name}")

        # Process removed items
        for key in removed_keys:
            fp, item = self._before_fingerprints[key]
            removed_items.append(item)
            logger.debug(f"Removed: {fp.display_name}")

        # Check for stack size changes on common items
        for key in common_keys:
            before_fp, before_item = self._before_fingerprints[key]
            after_fp, after_item = after_content_map[key]

            before_stack = before_fp.stack_size
            after_stack = after_fp.stack_size

            if before_stack != after_stack:
                delta = after_stack - before_stack

                # Optionally ignore small currency changes
                if self._ignore_currency_changes and before_fp.rarity == 5:  # Currency
                    if abs(delta) < 5:
                        continue

                stack_changes.append(
                    StackChange(
                        item=after_item,
                        delta=delta,
                        fingerprint=after_fp,
                    )
                )
                logger.debug(
                    f"Stack change: {after_fp.display_name} "
                    f"{before_stack} -> {after_stack} ({delta:+d})"
                )

        diff = StashDiff(
            added_items=added_items,
            removed_items=removed_items,
            stack_changes=stack_changes,
            before_total_items=len(self._before_fingerprints),
            after_total_items=len(after_content_map),
            computed_at=datetime.now(),
        )

        logger.info(f"Stash diff computed: {diff.get_summary()}")

        return diff

    def get_added_items_with_fingerprints(
        self, diff: StashDiff
    ) -> List[Tuple[Dict[str, Any], ItemFingerprint]]:
        """
        Get added items paired with their fingerprints.

        Useful for generating LootDrop objects.

        Args:
            diff: The computed diff.

        Returns:
            List of (item, fingerprint) tuples.
        """
        result = []
        for item in diff.added_items:
            # Reconstruct fingerprint - we need a tab_id
            # For now, use empty string - caller should enhance
            fp = ItemFingerprint.from_item(item, "")
            result.append((item, fp))
        return result

    def clear(self):
        """Clear the stored before snapshot."""
        self._before_snapshot = None
        self._before_fingerprints = {}
        self._before_position_map = {}
        logger.debug("Diff engine cleared")

    @property
    def has_before_snapshot(self) -> bool:
        """Check if a before snapshot is set."""
        return self._before_snapshot is not None


# Utility functions


def extract_item_value(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key fields from an item for display/storage.

    Args:
        item: Raw item dict from stash API.

    Returns:
        Simplified dict with key fields.
    """
    name = item.get("name", "") or ""
    base_type = item.get("typeLine", "") or ""

    return {
        "name": name,
        "base_type": base_type,
        "display_name": f"{name} {base_type}".strip() if name else base_type,
        "stack_size": item.get("stackSize", 1),
        "rarity": item.get("frameType", 0),
        "ilvl": item.get("ilvl", 0),
        "identified": item.get("identified", True),
        "corrupted": item.get("corrupted", False),
        "icon": item.get("icon", ""),
    }


def get_rarity_name(frame_type: int) -> str:
    """
    Get rarity name from frame type.

    Args:
        frame_type: PoE item frame type (0-9).

    Returns:
        Rarity name string.
    """
    rarity_map = {
        0: "Normal",
        1: "Magic",
        2: "Rare",
        3: "Unique",
        4: "Gem",
        5: "Currency",
        6: "Divination Card",
        7: "Quest",
        8: "Prophecy",
        9: "Foil/Relic",
    }
    return rarity_map.get(frame_type, "Unknown")


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("STASH DIFF ENGINE TEST")
    print("=" * 60)

    # Create mock snapshots for testing
    from dataclasses import dataclass as dc, field as f
    from typing import List as L, Dict as D

    @dc
    class MockTab:
        id: str
        name: str
        index: int
        type: str
        items: L[D] = f(default_factory=list)
        folder: str = None
        children: L = f(default_factory=list)

    @dc
    class MockSnapshot:
        account_name: str
        league: str
        tabs: L[MockTab] = f(default_factory=list)
        total_items: int = 0
        fetched_at: str = ""

    # Before snapshot
    before_items = [
        {"name": "", "typeLine": "Chaos Orb", "stackSize": 100, "x": 0, "y": 0, "frameType": 5},
        {"name": "", "typeLine": "Exalted Orb", "stackSize": 5, "x": 1, "y": 0, "frameType": 5},
        {"name": "Starforge", "typeLine": "Infernal Sword", "x": 2, "y": 0, "frameType": 3, "ilvl": 83},
    ]
    before_tab = MockTab(id="tab1", name="Currency", index=0, type="CurrencyStash", items=before_items)
    before_snapshot = MockSnapshot(account_name="test", league="Settlers", tabs=[before_tab])

    # After snapshot (added Divine, increased Chaos, removed Starforge)
    after_items = [
        {"name": "", "typeLine": "Chaos Orb", "stackSize": 150, "x": 0, "y": 0, "frameType": 5},
        {"name": "", "typeLine": "Exalted Orb", "stackSize": 5, "x": 1, "y": 0, "frameType": 5},
        {"name": "", "typeLine": "Divine Orb", "stackSize": 1, "x": 3, "y": 0, "frameType": 5},
    ]
    after_tab = MockTab(id="tab1", name="Currency", index=0, type="CurrencyStash", items=after_items)
    after_snapshot = MockSnapshot(account_name="test", league="Settlers", tabs=[after_tab])

    # Test diff
    engine = StashDiffEngine()
    engine.set_before_snapshot(before_snapshot)
    diff = engine.compute_diff(after_snapshot)

    print(f"\nDiff summary: {diff.get_summary()}")
    print(f"Added items: {len(diff.added_items)}")
    for item in diff.added_items:
        print(f"  + {item.get('typeLine')}")

    print(f"Removed items: {len(diff.removed_items)}")
    for item in diff.removed_items:
        name = item.get("name", "")
        base = item.get("typeLine", "")
        print(f"  - {name} {base}".strip())

    print(f"Stack changes: {len(diff.stack_changes)}")
    for sc in diff.stack_changes:
        print(f"  ~ {sc.fingerprint.base_type}: {sc.delta:+d}")

    print(f"\nItems gained: {diff.items_gained}")
    print(f"Items lost: {diff.items_lost}")
