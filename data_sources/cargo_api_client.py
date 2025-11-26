"""
PoE Wiki Cargo API Client

Fetches mod/affix data from the Path of Exile Wiki's Cargo database API.
https://www.poewiki.net/wiki/Path_of_Exile_Wiki:Data_query_API
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class CargoAPIClient:
    """
    Client for querying the PoE Wiki Cargo database API.

    The Cargo API provides access to comprehensive game data including:
    - Mod/affix data with tier ranges and spawn weights
    - Item base types and properties
    - Skill information
    - Area data
    """

    BASE_URL = "https://www.poewiki.net/w/api.php"

    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize the Cargo API client.

        Args:
            rate_limit: Minimum seconds between requests (default: 1.0)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PoE-Price-Checker/1.0 (Rare Item Pricing Tool)'
        })
        self.rate_limit = rate_limit
        self.last_request_time = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def query(
        self,
        tables: str,
        fields: str,
        where: Optional[str] = None,
        join_on: Optional[str] = None,
        group_by: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cargo database query.

        Args:
            tables: Table name(s) to query (e.g., "mods")
            fields: Comma-separated field list (e.g., "mods.id,mods.name")
            where: SQL WHERE clause (optional)
            join_on: SQL JOIN clause (optional)
            group_by: SQL GROUP BY clause (optional)
            order_by: SQL ORDER BY clause (optional)
            limit: Maximum results to return (default: 500)
            offset: Result offset for pagination (default: 0)

        Returns:
            List of result dictionaries

        Example:
            >>> client = CargoAPIClient()
            >>> results = client.query(
            ...     tables="mods",
            ...     fields="mods.name,mods.stat1_min,mods.stat1_max",
            ...     where="mods.name LIKE '%maximum Life' AND mods.generation_type=7",
            ...     limit=10
            ... )
        """
        self._wait_for_rate_limit()

        params = {
            'action': 'cargoquery',
            'format': 'json',
            'tables': tables,
            'fields': fields,
            'limit': limit,
            'offset': offset,
        }

        if where:
            params['where'] = where
        if join_on:
            params['join_on'] = join_on
        if group_by:
            params['group_by'] = group_by
        if order_by:
            params['order_by'] = order_by

        try:
            logger.debug(f"Cargo API query: tables={tables}, limit={limit}, offset={offset}")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract results from Cargo's nested structure
            if 'cargoquery' in data:
                results = []
                for item in data['cargoquery']:
                    if 'title' in item:
                        results.append(item['title'])
                return results
            else:
                logger.warning(f"Unexpected Cargo API response format: {data}")
                return []

        except requests.RequestException as e:
            logger.error(f"Cargo API request failed: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Cargo API response: {e}")
            raise

    def get_mods_by_stat_text(
        self,
        stat_text_pattern: str,
        generation_type: int = 7,  # 7 = suffix, 6 = prefix
        domain: int = 1,  # 1 = item
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Query mods by stat text pattern.

        Args:
            stat_text_pattern: SQL LIKE pattern for stat text (e.g., "%maximum Life")
            generation_type: 6=prefix, 7=suffix (default: 7)
            domain: 1=item, 2=flask, 3=monster, etc. (default: 1)
            limit: Maximum results (default: 500)

        Returns:
            List of mod dictionaries with fields:
                - id: Mod ID
                - name: Internal mod name
                - stat_text: Display text
                - stat1_id: Primary stat ID
                - stat1_min: Minimum value
                - stat1_max: Maximum value
                - level_requirement: Required item level
                - mod_group: Mod group name
                - spawn_weight: Spawn probability weight
        """
        fields = (
            "mods.id,mods.name,mods.stat_text,mods.required_level,"
            "mods.domain,mods.generation_type,mods.mod_group,"
            "mods.stat1_id,mods.stat1_min,mods.stat1_max,"
            "mods.stat2_id,mods.stat2_min,mods.stat2_max,"
            "mods.tags"
        )

        where_clauses = [
            f"mods.stat_text LIKE '{stat_text_pattern}'",
            f"mods.generation_type={generation_type}",
            f"mods.domain={domain}",
        ]

        return self.query(
            tables="mods",
            fields=fields,
            where=" AND ".join(where_clauses),
            limit=limit,
        )

    def get_all_item_mods(
        self,
        generation_type: Optional[int] = None,
        batch_size: int = 500,
        max_total: int = 40000,
        domain: Optional[int] = 1,
    ) -> List[Dict[str, Any]]:
        """
        Get all item mods with pagination.

        Args:
            generation_type: Filter by type (1=prefix, 2=suffix, None=all)
            batch_size: Results per batch (default: 500)
            max_total: Maximum total results (default: 20000)
            domain: Domain filter (1=items, None=all)

        Returns:
            List of all matching mods
        """
        all_mods = []
        offset = 0

        # Use only fields that actually exist in the mods table
        fields = (
            "mods.id,mods.name,mods.stat_text,mods.stat_text_raw,"
            "mods.required_level,mods.domain,mods.generation_type,"
            "mods.mod_groups,mods.tier_text,mods.tags"
        )

        # Note: WHERE clauses cause MWException errors on the wiki API
        # So we fetch all mods and filter client-side
        while offset < max_total:
            batch = self.query(
                tables="mods",
                fields=fields,
                where=None,  # Can't use WHERE - causes API errors
                limit=batch_size,
                offset=offset,
            )

            if not batch:
                break

            # Filter client-side
            for mod in batch:
                mod_domain = mod.get('domain')
                mod_gen = mod.get('generation type')

                # Convert to int for comparison
                try:
                    mod_domain = int(mod_domain) if mod_domain else None
                    mod_gen = int(mod_gen) if mod_gen else None
                except (ValueError, TypeError):
                    pass

                # Apply filters
                if domain is not None and mod_domain != domain:
                    continue
                if generation_type is not None and mod_gen != generation_type:
                    continue

                all_mods.append(mod)

            logger.info(f"Fetched batch at offset {offset}, filtered to {len(all_mods)} mods")

            if len(batch) < batch_size:
                break

            offset += batch_size

        logger.info(f"Fetched {len(all_mods)} total mods from Cargo API")
        return all_mods

    def get_unique_items(
        self,
        batch_size: int = 500,
        max_total: int = 5000,
    ) -> List[Dict[str, Any]]:
        """
        Get all unique items from the wiki with pagination.

        Args:
            batch_size: Results per batch (default: 500)
            max_total: Maximum total results (default: 5000)

        Returns:
            List of unique item dictionaries with fields:
                - name: Item name (e.g., "Headhunter")
                - base_item: Base type (e.g., "Leather Belt")
                - class: Item class (e.g., "Belt")
                - rarity: "Unique"
                - required_level: Level requirement
                - drop_enabled: Whether item can drop
        """
        all_items = []
        offset = 0

        fields = (
            "items.name,"
            "items.base_item,"
            "items.class,"
            "items.rarity,"
            "items.required_level,"
            "items.drop_enabled"
        )

        while offset < max_total:
            batch = self.query(
                tables="items",
                fields=fields,
                where='items.rarity="Unique"',
                limit=batch_size,
                offset=offset,
            )

            if not batch:
                break

            all_items.extend(batch)
            logger.info(f"Fetched {len(batch)} unique items at offset {offset}")

            if len(batch) < batch_size:
                break

            offset += batch_size

        logger.info(f"Fetched {len(all_items)} total unique items from Cargo API")
        return all_items

    def get_items_by_class(
        self,
        item_class: str,
        batch_size: int = 500,
        max_total: int = 2000,
    ) -> List[Dict[str, Any]]:
        """
        Get all items of a specific class from the wiki.

        Args:
            item_class: Item class to filter (e.g., "Belt", "Helmet")
            batch_size: Results per batch (default: 500)
            max_total: Maximum total results (default: 2000)

        Returns:
            List of item dictionaries
        """
        all_items = []
        offset = 0

        fields = (
            "items.name,"
            "items.base_item,"
            "items.class,"
            "items.rarity,"
            "items.required_level,"
            "items.drop_enabled"
        )

        while offset < max_total:
            batch = self.query(
                tables="items",
                fields=fields,
                where=f'items.class="{item_class}"',
                limit=batch_size,
                offset=offset,
            )

            if not batch:
                break

            all_items.extend(batch)

            if len(batch) < batch_size:
                break

            offset += batch_size

        logger.info(f"Fetched {len(all_items)} {item_class} items from Cargo API")
        return all_items

    def get_all_items(
        self,
        item_classes: List[str] = None,
        batch_size: int = 500,
        max_total: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Get all items from specified classes with pagination.

        Args:
            item_classes: List of item classes to fetch. If None, fetches common valuable types.
            batch_size: Results per batch (default: 500)
            max_total: Maximum total results (default: 10000)

        Returns:
            List of item dictionaries
        """
        if item_classes is None:
            # Default to valuable/tradeable item types
            item_classes = [
                "Unique",  # Unique items (rarity filter)
                "Divination Card",
                "Skill Gem",
                "Support Gem",
                "Map Fragment",  # Includes scarabs
                "Currency Item",
                "Map",
                "Incubator",
                "Resonator",
                "Breachstone",
            ]

        all_items = []

        fields = (
            "items.name,"
            "items.base_item,"
            "items.class,"
            "items.rarity,"
            "items.required_level,"
            "items.drop_enabled"
        )

        for item_class in item_classes:
            offset = 0
            class_items = []

            # Handle "Unique" as a rarity filter instead of class
            if item_class == "Unique":
                where_clause = 'items.rarity="Unique"'
            else:
                where_clause = f'items.class="{item_class}"'

            while offset < max_total:
                batch = self.query(
                    tables="items",
                    fields=fields,
                    where=where_clause,
                    limit=batch_size,
                    offset=offset,
                )

                if not batch:
                    break

                class_items.extend(batch)

                if len(batch) < batch_size:
                    break

                offset += batch_size

            logger.info(f"Fetched {len(class_items)} {item_class} items")
            all_items.extend(class_items)

        logger.info(f"Fetched {len(all_items)} total items from Cargo API")
        return all_items

    def get_divination_cards(self, batch_size: int = 500) -> List[Dict[str, Any]]:
        """Get all divination cards."""
        return self.get_items_by_class("Divination Card", batch_size=batch_size)

    def get_skill_gems(self, batch_size: int = 500) -> List[Dict[str, Any]]:
        """Get all skill gems (both active and support)."""
        active = self.get_items_by_class("Skill Gem", batch_size=batch_size)
        support = self.get_items_by_class("Support Gem", batch_size=batch_size)
        return active + support

    def get_scarabs(self, batch_size: int = 500) -> List[Dict[str, Any]]:
        """Get all scarabs (classified as Map Fragment with 'Scarab' in name)."""
        all_frags = self.get_items_by_class("Map Fragment", batch_size=batch_size)
        return [item for item in all_frags if "Scarab" in item.get("name", "")]

    def get_currency(self, batch_size: int = 500) -> List[Dict[str, Any]]:
        """Get all currency items."""
        return self.get_items_by_class("Currency Item", batch_size=batch_size)
