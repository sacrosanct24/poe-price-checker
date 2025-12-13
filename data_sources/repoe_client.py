"""
RePoE Data Client.

Provides access to RePoE (Repository of Path of Exile) data for accurate
mod/item information extracted directly from game files.

RePoE GitHub: https://github.com/brather1ng/RePoE

Key data includes:
- mods.json: Complete mod database with tiers, stat ranges, spawn weights
- base_items.json: All base item types with requirements and tags
- stat_translations.json: Maps stat IDs to in-game text
- essences.json: Essence crafting mechanics
- fossils.json: Fossil mod manipulation data
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.constants import API_TIMEOUT_EXTENDED

logger = logging.getLogger(__name__)

# RePoE raw GitHub URLs
REPOE_BASE_URL = "https://raw.githubusercontent.com/brather1ng/RePoE/master/RePoE/data"


@dataclass
class ModData:
    """Parsed mod data from RePoE."""
    mod_id: str
    name: str
    domain: str  # "item", "monster", "abyss_jewel", etc.
    generation_type: str  # "prefix", "suffix", "unique", etc.
    required_level: int
    stats: List[Dict[str, Any]]  # [{id, min, max}, ...]
    spawn_weights: List[Dict[str, Any]]  # [{tag, weight}, ...]
    groups: List[str]
    implicit_tags: List[str]
    is_essence_only: bool

    @property
    def is_prefix(self) -> bool:
        return self.generation_type == "prefix"

    @property
    def is_suffix(self) -> bool:
        return self.generation_type == "suffix"

    @property
    def stat_ranges(self) -> List[tuple[str, int, int]]:
        """Get stat ranges as (stat_id, min, max) tuples."""
        return [(s['id'], s['min'], s['max']) for s in self.stats]


@dataclass
class BaseItemData:
    """Parsed base item data from RePoE."""
    item_id: str
    name: str
    item_class: str
    inventory_width: int
    inventory_height: int
    drop_level: int
    tags: List[str]
    implicit_mods: List[str]
    requirements: Dict[str, int]  # {str, dex, int, level}


class RePoEClient:
    """
    Client for accessing RePoE game data.

    Caches downloaded data locally and provides query methods
    for mod/item information.
    """

    # Available data files
    DATA_FILES = {
        'mods': 'mods.min.json',
        'base_items': 'base_items.min.json',
        'stat_translations': 'stat_translations.min.json',
        'stats': 'stats.min.json',
        'essences': 'essences.min.json',
        'fossils': 'fossils.min.json',
        'crafting_bench': 'crafting_bench_options.min.json',
        'item_classes': 'item_classes.min.json',
        'tags': 'tags.min.json',
    }

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        auto_download: bool = True,
    ):
        """
        Initialize the RePoE client.

        Args:
            cache_dir: Directory to cache downloaded data
            auto_download: Automatically download missing data
        """
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "data" / "repoe_cache"
        self.auto_download = auto_download
        self._data_cache: Dict[str, Any] = {}

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, data_type: str) -> Path:
        """Get local cache path for data type."""
        filename = self.DATA_FILES.get(data_type, f"{data_type}.json")
        return self.cache_dir / filename

    def _download_data(self, data_type: str) -> Optional[dict]:
        """
        Download data file from RePoE GitHub.

        Args:
            data_type: Type of data to download (e.g., 'mods', 'base_items')

        Returns:
            Parsed JSON data or None on failure
        """
        filename = self.DATA_FILES.get(data_type)
        if not filename:
            logger.error(f"Unknown data type: {data_type}")
            return None

        url = f"{REPOE_BASE_URL}/{filename}"
        logger.info(f"Downloading RePoE data: {url}")

        try:
            response = requests.get(url, timeout=API_TIMEOUT_EXTENDED)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            # Cache locally
            cache_path = self._get_cache_path(data_type)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            logger.info(f"Cached {data_type} to {cache_path}")
            return data

        except requests.RequestException as e:
            logger.error(f"Network error downloading {data_type}: {e}")
            return None
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to cache {data_type}: {e}")
            return None

    def _load_data(self, data_type: str) -> Optional[dict]:
        """
        Load data from cache or download.

        Args:
            data_type: Type of data to load

        Returns:
            Parsed JSON data or None
        """
        # Check memory cache first
        if data_type in self._data_cache:
            cached: Dict[str, Any] = self._data_cache[data_type]
            return cached

        # Check local file cache
        cache_path = self._get_cache_path(data_type)
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data: Dict[str, Any] = json.load(f)
                self._data_cache[data_type] = data
                return data
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load cached {data_type}: {e}")

        # Download if auto_download enabled
        if self.auto_download:
            downloaded = self._download_data(data_type)
            if downloaded:
                self._data_cache[data_type] = downloaded
            return downloaded

        return None

    def get_mods(self) -> Optional[Dict[str, dict]]:
        """Get all mod data."""
        return self._load_data('mods')

    def get_base_items(self) -> Optional[Dict[str, dict]]:
        """Get all base item data."""
        return self._load_data('base_items')

    def get_stat_translations(self) -> Optional[Dict[str, Any]]:
        """Get stat translation data."""
        return self._load_data('stat_translations')

    def get_essences(self) -> Optional[Dict[str, dict]]:
        """Get essence data."""
        return self._load_data('essences')

    def get_fossils(self) -> Optional[Dict[str, dict]]:
        """Get fossil data."""
        return self._load_data('fossils')

    def find_mod_by_stat(
        self,
        stat_text: str,
        domain: str = "item",
    ) -> List[ModData]:
        """
        Find mods that grant a specific stat.

        Args:
            stat_text: Partial stat ID or text to search for
            domain: Mod domain filter (e.g., "item", "abyss_jewel")

        Returns:
            List of matching ModData objects
        """
        mods_data = self.get_mods()
        if not mods_data:
            return []

        results = []
        stat_lower = stat_text.lower()

        for mod_id, mod_info in mods_data.items():
            # Filter by domain
            if mod_info.get('domain') != domain:
                continue

            # Check stats
            for stat in mod_info.get('stats', []):
                if stat_lower in stat.get('id', '').lower():
                    results.append(self._parse_mod(mod_id, mod_info))
                    break

        return results

    def find_mods_for_item_tag(
        self,
        tag: str,
        generation_type: Optional[str] = None,
    ) -> List[ModData]:
        """
        Find mods that can spawn on items with a specific tag.

        Args:
            tag: Item tag (e.g., "helmet", "body_armour", "ring")
            generation_type: Filter by "prefix" or "suffix"

        Returns:
            List of matching ModData objects
        """
        mods_data = self.get_mods()
        if not mods_data:
            return []

        results = []

        for mod_id, mod_info in mods_data.items():
            # Filter by generation type
            if generation_type and mod_info.get('generation_type') != generation_type:
                continue

            # Skip non-item mods
            if mod_info.get('domain') != 'item':
                continue

            # Check spawn weights for tag
            for weight in mod_info.get('spawn_weights', []):
                if weight.get('tag') == tag and weight.get('weight', 0) > 0:
                    results.append(self._parse_mod(mod_id, mod_info))
                    break

        return results

    def get_mod_tiers(
        self,
        stat_id: str,
        domain: str = "item",
    ) -> List[tuple[str, int, int, int]]:
        """
        Get all tiers for a specific stat.

        Args:
            stat_id: Stat ID to search for
            domain: Mod domain filter

        Returns:
            List of (mod_name, min_value, max_value, required_level) sorted by value
        """
        mods = self.find_mod_by_stat(stat_id, domain)

        tiers = []
        for mod in mods:
            for stat in mod.stats:
                if stat_id in stat['id'].lower():
                    tiers.append((
                        mod.name or mod.mod_id,
                        stat['min'],
                        stat['max'],
                        mod.required_level,
                    ))

        # Sort by max value (higher = better tier typically)
        tiers.sort(key=lambda x: x[2], reverse=True)
        return tiers

    def _parse_mod(self, mod_id: str, mod_info: dict) -> ModData:
        """Parse raw mod data into ModData object."""
        return ModData(
            mod_id=mod_id,
            name=mod_info.get('name', ''),
            domain=mod_info.get('domain', ''),
            generation_type=mod_info.get('generation_type', ''),
            required_level=mod_info.get('required_level', 0),
            stats=mod_info.get('stats', []),
            spawn_weights=mod_info.get('spawn_weights', []),
            groups=mod_info.get('groups', []),
            implicit_tags=mod_info.get('implicit_tags', []),
            is_essence_only=mod_info.get('is_essence_only', False),
        )

    def find_base_item(self, name: str) -> Optional[BaseItemData]:
        """
        Find base item by name.

        Args:
            name: Base item name (e.g., "Vaal Regalia", "Hubris Circlet")

        Returns:
            BaseItemData or None
        """
        base_items = self.get_base_items()
        if not base_items:
            return None

        name_lower = name.lower()

        for item_id, item_info in base_items.items():
            if item_info.get('name', '').lower() == name_lower:
                return self._parse_base_item(item_id, item_info)

        return None

    def _parse_base_item(self, item_id: str, item_info: dict) -> BaseItemData:
        """Parse raw base item data into BaseItemData object."""
        return BaseItemData(
            item_id=item_id,
            name=item_info.get('name', ''),
            item_class=item_info.get('item_class', ''),
            inventory_width=item_info.get('inventory_width', 1),
            inventory_height=item_info.get('inventory_height', 1),
            drop_level=item_info.get('drop_level', 0),
            tags=item_info.get('tags', []),
            implicit_mods=item_info.get('implicits', []),
            requirements=item_info.get('requirements', {}),
        )

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        cached_files = [f for f in self.cache_dir.glob('*.json')]
        return {
            'cache_dir': str(self.cache_dir),
            'cached_files': len(cached_files),
            'memory_cached': list(self._data_cache.keys()),
        }

    def clear_cache(self):
        """Clear all cached data."""
        self._data_cache.clear()
        for f in self.cache_dir.glob('*.json'):
            f.unlink()
        logger.info("Cleared RePoE cache")


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("REPOE CLIENT TEST")
    print("=" * 60)

    client = RePoEClient()

    print("\n1. Testing mod data loading...")
    mods = client.get_mods()
    if mods:
        print(f"   Loaded {len(mods)} mods")

        # Find life mods
        print("\n2. Finding '+# to maximum Life' mods for items...")
        life_mods = client.find_mod_by_stat("maximum_life", domain="item")
        print(f"   Found {len(life_mods)} life mods")

        if life_mods[:3]:
            for mod in life_mods[:3]:
                print(f"   - {mod.name or mod.mod_id}: {mod.stat_ranges}")

    print("\n3. Testing mod tier lookup...")
    tiers = client.get_mod_tiers("maximum_life")
    print(f"   Found {len(tiers)} life tiers")
    if tiers[:5]:
        print("   Top 5 tiers:")
        for name, min_val, max_val, req_level in tiers[:5]:
            print(f"     {name}: {min_val}-{max_val} (ilvl {req_level})")

    print("\n4. Testing base item lookup...")
    base = client.find_base_item("Vaal Regalia")
    if base:
        print(f"   Found: {base.name}")
        print(f"   Class: {base.item_class}")
        print(f"   Tags: {base.tags[:5]}...")
        print(f"   Drop level: {base.drop_level}")

    print("\n5. Cache stats:")
    stats = client.get_cache_stats()
    print(f"   Cache dir: {stats['cache_dir']}")
    print(f"   Cached files: {stats['cached_files']}")
    print(f"   Memory cached: {stats['memory_cached']}")

    print("\n" + "=" * 60)
