"""
Affix Data Provider

Provides affix/mod data with automatic fallback:
1. Try ModDatabase (if populated from Cargo API)
2. Fall back to valuable_affixes.json (hardcoded tiers)

This allows gradual migration from JSON to database while maintaining reliability.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AffixDataProvider:
    """
    Unified interface for affix data with automatic fallback.

    Tries to use ModDatabase first (real game data), falls back to
    JSON if database is unavailable or empty.
    """

    def __init__(
        self,
        mod_database=None,
        json_path: Optional[Path] = None,
    ):
        """
        Initialize the affix data provider.

        Args:
            mod_database: ModDatabase instance (optional, will use fallback if None)
            json_path: Path to valuable_affixes.json (default: data/valuable_affixes.json)
        """
        self.db = mod_database
        self.json_path = json_path or Path("data/valuable_affixes.json")
        self._json_data: Optional[Dict] = None
        self._using_database = False

        # Try to use database if available
        if self.db and self.db.get_mod_count() > 0:
            self._using_database = True
            logger.info(f"Using ModDatabase ({self.db.get_mod_count()} mods)")
        else:
            logger.info("ModDatabase not available, using JSON fallback")
            self._load_json()

    def _load_json(self) -> None:
        """Load valuable_affixes.json as fallback."""
        try:
            with open(self.json_path, 'r') as f:
                self._json_data = json.load(f)
            logger.info(f"Loaded {len(self._json_data)} affixes from {self.json_path}")
        except FileNotFoundError:
            logger.error(f"JSON file not found: {self.json_path}")
            self._json_data = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            self._json_data = {}

    def get_affix_tiers(
        self,
        affix_type: str,
        stat_text_pattern: Optional[str] = None,
    ) -> List[Tuple[int, int, int]]:
        """
        Get tier ranges for an affix.

        Returns list of (tier_number, min_value, max_value) tuples.

        Args:
            affix_type: Affix type key (e.g., "life", "movement_speed")
            stat_text_pattern: Optional Cargo API pattern (e.g., "%to maximum Life")
                              Only used when database is available.

        Returns:
            List of (tier, min, max) tuples, e.g.:
            [(1, 100, 109), (2, 90, 99), (3, 80, 89)]
        """
        if self._using_database and stat_text_pattern:
            return self._get_tiers_from_database(stat_text_pattern)
        else:
            return self._get_tiers_from_json(affix_type)

    def _get_tiers_from_database(
        self,
        stat_text_pattern: str,
    ) -> List[Tuple[int, int, int]]:
        """Get tiers from ModDatabase using Cargo data."""
        try:
            tiers = self.db.get_affix_tiers(stat_text_pattern)
            logger.debug(f"Found {len(tiers)} tiers for '{stat_text_pattern}' from database")
            return tiers
        except Exception as e:
            logger.warning(f"Database query failed: {e}, falling back to JSON")
            return []

    def _get_tiers_from_json(
        self,
        affix_type: str,
    ) -> List[Tuple[int, int, int]]:
        """Get tiers from JSON fallback data."""
        if not self._json_data:
            return []

        affix_data = self._json_data.get(affix_type, {})
        tiers = []

        # T1
        if 'tier1_range' in affix_data:
            min_val, max_val = affix_data['tier1_range']
            tiers.append((1, min_val, max_val))

        # T2
        if 'tier2_range' in affix_data:
            min_val, max_val = affix_data['tier2_range']
            tiers.append((2, min_val, max_val))

        # T3
        if 'tier3_range' in affix_data:
            min_val, max_val = affix_data['tier3_range']
            tiers.append((3, min_val, max_val))

        logger.debug(f"Found {len(tiers)} tiers for '{affix_type}' from JSON")
        return tiers

    def get_affix_config(self, affix_type: str) -> Dict[str, Any]:
        """
        Get full affix configuration from JSON.

        This includes patterns, weights, categories, etc.
        Used for affix matching in RareItemEvaluator.

        Args:
            affix_type: Affix type key (e.g., "life")

        Returns:
            Affix configuration dict, or {} if not found
        """
        if not self._json_data:
            self._load_json()

        return self._json_data.get(affix_type, {})

    def get_all_affix_types(self) -> List[str]:
        """
        Get list of all known affix types.

        Returns:
            List of affix type keys (e.g., ["life", "resistances", ...])
        """
        if not self._json_data:
            self._load_json()

        # Filter out special keys like "_synergies", "_red_flags"
        return [
            key for key in self._json_data.keys()
            if not key.startswith('_')
        ]

    def get_synergies(self) -> Dict[str, Any]:
        """Get synergy definitions from JSON."""
        if not self._json_data:
            self._load_json()
        return self._json_data.get('_synergies', {})

    def get_red_flags(self) -> Dict[str, Any]:
        """Get red flag definitions from JSON."""
        if not self._json_data:
            self._load_json()
        return self._json_data.get('_red_flags', {})

    def is_using_database(self) -> bool:
        """Check if provider is using database or JSON fallback."""
        return self._using_database

    def get_source_info(self) -> str:
        """Get human-readable info about data source."""
        if self._using_database:
            count = self.db.get_mod_count()
            league = self.db.get_current_league()
            last_update = self.db.get_last_update_time()
            return (
                f"ModDatabase: {count} mods, "
                f"league={league}, "
                f"last_update={last_update}"
            )
        else:
            affix_count = len(self.get_all_affix_types())
            return f"JSON Fallback: {affix_count} affix types from {self.json_path}"


# Thread-safe singleton instance for easy access
import threading

_provider: Optional[AffixDataProvider] = None
_provider_lock = threading.Lock()


def get_affix_provider(
    mod_database=None,
    force_reload: bool = False,
) -> AffixDataProvider:
    """
    Get the global AffixDataProvider instance. Thread-safe.

    Args:
        mod_database: Optional ModDatabase instance to use
        force_reload: Force recreation of provider

    Returns:
        AffixDataProvider singleton
    """
    global _provider

    if _provider is None or force_reload:
        with _provider_lock:
            # Double-check locking pattern
            if _provider is None or force_reload:
                _provider = AffixDataProvider(mod_database=mod_database)
                logger.info(f"Initialized affix provider: {_provider.get_source_info()}")

    return _provider
