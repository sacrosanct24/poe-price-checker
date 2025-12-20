"""
Passive Tree Data Provider.

Fetches and caches passive skill tree data from official PoE sources.
Provides node lookups by ID including name, type (notable/keystone/small).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests

from core.constants import API_TIMEOUT_EXTENDED

logger = logging.getLogger(__name__)

# Passive tree data URLs
# GGG publishes official tree data via GitHub skilltree-export
# Note: This is PoE1 data. PoE2 may have different node IDs.
SKILLTREE_DATA_URL = "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json"


@dataclass
class PassiveNode:
    """Represents a passive tree node."""
    node_id: int
    name: str
    is_notable: bool
    is_keystone: bool
    is_mastery: bool
    is_ascendancy: bool
    stats: List[str]

    @property
    def node_type(self) -> str:
        """Get node type as string."""
        if self.is_keystone:
            return "keystone"
        elif self.is_notable:
            return "notable"
        elif self.is_mastery:
            return "mastery"
        elif self.is_ascendancy:
            return "ascendancy"
        else:
            return "small"

    @property
    def is_small(self) -> bool:
        """Check if this is a small (non-notable, non-keystone) node."""
        return not (self.is_notable or self.is_keystone or self.is_mastery)


class PassiveTreeDataProvider:
    """
    Provides passive tree node data lookups.

    Fetches tree data from official sources and caches locally.
    """

    CACHE_FILENAME = "passive_tree.json"

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the passive tree data provider.

        Args:
            cache_dir: Directory to cache downloaded data
        """
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "data" / "repoe_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._nodes: Dict[int, PassiveNode] = {}
        self._loaded = False

    @property
    def cache_path(self) -> Path:
        """Get the cache file path."""
        return self.cache_dir / self.CACHE_FILENAME

    def _download_tree_data(self) -> Optional[dict]:
        """
        Download passive tree data from official GGG skilltree-export.

        Returns:
            Parsed JSON data or None on failure
        """
        logger.info(f"Downloading passive tree data from {SKILLTREE_DATA_URL}")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(SKILLTREE_DATA_URL, headers=headers, timeout=API_TIMEOUT_EXTENDED)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            # Cache locally
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            logger.info(f"Cached passive tree data to {self.cache_path} ({len(data.get('nodes', {}))} nodes)")
            return data

        except Exception as e:
            logger.error(f"Failed to download passive tree data: {e}")
            return None

    def _load_data(self) -> bool:
        """
        Load passive tree data from cache or download.

        Returns:
            True if data was loaded successfully
        """
        if self._loaded:
            return True

        data = None

        # Try loading from cache first
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info("Loaded passive tree data from cache")
            except Exception as e:
                logger.warning(f"Failed to load cached tree data: {e}")

        # Download if not cached
        if not data:
            data = self._download_tree_data()

        if not data:
            return False

        # Parse nodes
        self._parse_tree_data(data)
        self._loaded = True
        return True

    def _parse_tree_data(self, data: dict) -> None:
        """
        Parse tree data JSON into PassiveNode objects.

        Args:
            data: Raw tree data JSON
        """
        nodes_data = data.get("nodes", {})

        for node_id_str, node_info in nodes_data.items():
            try:
                node_id = int(node_id_str)

                # Skip root/start nodes
                if node_info.get("isProxy") or node_info.get("isJewelSocket"):
                    continue

                node = PassiveNode(
                    node_id=node_id,
                    name=node_info.get("name", f"Node {node_id}"),
                    is_notable=node_info.get("isNotable", False),
                    is_keystone=node_info.get("isKeystone", False),
                    is_mastery=node_info.get("isMastery", False),
                    is_ascendancy=node_info.get("ascendancyName") is not None,
                    stats=node_info.get("stats", []),
                )

                self._nodes[node_id] = node

            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping node {node_id_str}: {e}")

    def get_node(self, node_id: int) -> Optional[PassiveNode]:
        """
        Get node data by ID.

        Args:
            node_id: Passive node ID

        Returns:
            PassiveNode or None if not found
        """
        self._load_data()
        return self._nodes.get(node_id)

    def get_node_name(self, node_id: int) -> str:
        """
        Get node name by ID.

        Args:
            node_id: Passive node ID

        Returns:
            Node name or "Unknown" if not found
        """
        node = self.get_node(node_id)
        return node.name if node else f"Node {node_id}"

    def get_nodes_by_ids(self, node_ids: List[int]) -> Dict[int, PassiveNode]:
        """
        Get multiple nodes by their IDs.

        Args:
            node_ids: List of node IDs

        Returns:
            Dict mapping node_id -> PassiveNode (only found nodes)
        """
        self._load_data()
        return {nid: self._nodes[nid] for nid in node_ids if nid in self._nodes}

    def categorize_nodes(
        self,
        node_ids: List[int]
    ) -> tuple[List[PassiveNode], List[PassiveNode], List[PassiveNode]]:
        """
        Categorize nodes into notables, keystones, and small nodes.

        Args:
            node_ids: List of node IDs to categorize

        Returns:
            Tuple of (notables, keystones, small_nodes) lists
        """
        self._load_data()

        notables = []
        keystones = []
        small_nodes = []

        for node_id in node_ids:
            node = self._nodes.get(node_id)
            if not node:
                # Unknown node - treat as small
                small_nodes.append(PassiveNode(
                    node_id=node_id,
                    name=f"Node {node_id}",
                    is_notable=False,
                    is_keystone=False,
                    is_mastery=False,
                    is_ascendancy=False,
                    stats=[],
                ))
                continue

            if node.is_keystone:
                keystones.append(node)
            elif node.is_notable:
                notables.append(node)
            else:
                small_nodes.append(node)

        return notables, keystones, small_nodes

    def is_loaded(self) -> bool:
        """Check if data has been loaded."""
        return self._loaded

    def get_stats(self) -> dict:
        """Get statistics about loaded data."""
        if not self._loaded:
            return {"loaded": False, "node_count": 0}

        notables = sum(1 for n in self._nodes.values() if n.is_notable)
        keystones = sum(1 for n in self._nodes.values() if n.is_keystone)
        masteries = sum(1 for n in self._nodes.values() if n.is_mastery)
        small = sum(1 for n in self._nodes.values() if n.is_small)

        return {
            "loaded": True,
            "node_count": len(self._nodes),
            "notables": notables,
            "keystones": keystones,
            "masteries": masteries,
            "small_nodes": small,
        }

    def clear_cache(self) -> None:
        """Clear cached data."""
        self._nodes.clear()
        self._loaded = False
        if self.cache_path.exists():
            self.cache_path.unlink()
        logger.info("Cleared passive tree cache")


# Singleton instance for easy access
_provider: Optional[PassiveTreeDataProvider] = None


def get_passive_tree_provider() -> PassiveTreeDataProvider:
    """Get the singleton PassiveTreeDataProvider instance."""
    global _provider
    if _provider is None:
        _provider = PassiveTreeDataProvider()
    return _provider


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Passive Tree Data Provider Test")
    print("=" * 60)

    provider = PassiveTreeDataProvider()

    print("\nLoading data...")
    provider._load_data()

    stats = provider.get_stats()
    print("\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test looking up some nodes
    test_ids = [1, 100, 1000, 10000, 50000]
    print(f"\nLooking up test nodes: {test_ids}")
    for node_id in test_ids:
        node = provider.get_node(node_id)
        if node:
            print(f"  {node_id}: {node.name} ({node.node_type})")
        else:
            print(f"  {node_id}: Not found")
