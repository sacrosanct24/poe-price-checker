"""
Mod Data Loader

Fetches mod data from PoE Wiki Cargo API and populates the local database.
Runs on first startup or when league changes.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports when running as script
_script_dir = Path(__file__).parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from data_sources.cargo_api_client import CargoAPIClient
from data_sources.mod_database import ModDatabase

logger = logging.getLogger(__name__)


class ModDataLoader:
    """
    Loads mod/affix data from Cargo API into local database.

    Handles:
    - Fetching all relevant item mods
    - Parsing and transforming data
    - Populating database
    - Tracking last update time and league
    """

    def __init__(
        self,
        database: Optional[ModDatabase] = None,
        api_client: Optional[CargoAPIClient] = None,
    ):
        """
        Initialize the data loader.

        Args:
            database: ModDatabase instance (creates new if None)
            api_client: CargoAPIClient instance (creates new if None)
        """
        self.db = database or ModDatabase()
        self.api = api_client or CargoAPIClient(rate_limit=1.0)

    def should_update(self, current_league: str) -> bool:
        """
        Check if database needs updating.

        Args:
            current_league: Current active league name

        Returns:
            True if update is needed
        """
        return self.db.should_update(current_league)

    def load_all_mods(
        self,
        current_league: str,
        max_mods: int = 5000,
        batch_size: int = 500,
    ) -> int:
        """
        Load all item mods from Cargo API into database.

        Args:
            current_league: Current league name (for metadata)
            max_mods: Maximum mods to fetch (default: 5000)
            batch_size: Mods per API request (default: 500)

        Returns:
            Number of mods loaded
        """
        logger.info(f"Loading mod data for league: {current_league}")

        try:
            # Fetch all item mods (both prefixes and suffixes)
            logger.info("Fetching mods from Cargo API (this may take a minute)...")
            mods = self.api.get_all_item_mods(
                generation_type=None,  # Get both prefixes and suffixes
                batch_size=batch_size,
                max_total=max_mods,
            )

            if not mods:
                logger.warning("No mods returned from Cargo API")
                return 0

            # Insert into database
            logger.info(f"Inserting {len(mods)} mods into database...")
            count = self.db.insert_mods(mods)

            # Update metadata
            self.db.set_metadata('league', current_league)
            self.db.set_metadata('last_update', datetime.now().isoformat())
            self.db.set_metadata('mod_count', str(count))

            logger.info(f"✓ Successfully loaded {count} mods for league {current_league}")
            return count

        except Exception as e:
            logger.error(f"Failed to load mod data: {e}")
            raise

    def load_specific_affixes(
        self,
        affix_patterns: list[str],
        current_league: str,
    ) -> int:
        """
        Load specific affixes by stat text patterns.

        Useful for targeted updates or testing.

        Args:
            affix_patterns: List of SQL LIKE patterns (e.g., ["%maximum Life", "%Fire Resistance"])
            current_league: Current league name

        Returns:
            Total number of mods loaded
        """
        total_count = 0

        for pattern in affix_patterns:
            logger.info(f"Loading mods matching: {pattern}")

            try:
                # Fetch both prefixes and suffixes
                for gen_type in [6, 7]:
                    mods = self.api.get_mods_by_stat_text(
                        stat_text_pattern=pattern,
                        generation_type=gen_type,
                        limit=500,
                    )

                    if mods:
                        count = self.db.insert_mods(mods)
                        total_count += count
                        logger.info(f"  Loaded {count} mods (generation_type={gen_type})")

            except Exception as e:
                logger.warning(f"Failed to load pattern '{pattern}': {e}")
                continue

        # Update metadata
        if total_count > 0:
            self.db.set_metadata('league', current_league)
            self.db.set_metadata('last_update', datetime.now().isoformat())

        logger.info(f"Loaded {total_count} mods total")
        return total_count

    def get_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Dictionary with stats (mod_count, last_update, league, etc.)
        """
        return {
            'mod_count': self.db.get_mod_count(),
            'last_update': self.db.get_last_update_time(),
            'league': self.db.get_current_league(),
        }


def ensure_mod_database_updated(
    current_league: str = "Standard",
    force_update: bool = False,
) -> ModDatabase:
    """
    Ensure mod database is initialized and up-to-date.

    This is the main entry point for setting up the mod database.
    Call this during application startup.

    Args:
        current_league: Current active league
        force_update: Force update even if not needed

    Returns:
        ModDatabase instance ready for use
    """
    loader = ModDataLoader()

    # Check if update is needed
    if force_update or loader.should_update(current_league):
        logger.info("Mod database needs updating")
        try:
            loader.load_all_mods(current_league)
        except Exception as e:
            logger.error(f"Failed to update mod database: {e}")
            logger.info("Continuing with existing data (if any)")
    else:
        stats = loader.get_stats()
        logger.info(
            f"Mod database is up-to-date: {stats['mod_count']} mods, "
            f"league={stats['league']}, last_update={stats['last_update']}"
        )

    return loader.db


if __name__ == "__main__":
    # Test/manual update script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("MOD DATABASE LOADER")
    print("=" * 80)

    league = input("Enter league name (default: Standard): ").strip() or "Standard"

    loader = ModDataLoader()
    print(f"\nLoading mods for league: {league}")
    print("This will fetch data from PoE Wiki and may take 1-2 minutes...")

    try:
        count = loader.load_all_mods(league)
        print(f"\n✓ Successfully loaded {count} mods!")

        # Show some stats
        stats = loader.get_stats()
        print(f"\nDatabase stats:")
        print(f"  Total mods: {stats['mod_count']}")
        print(f"  League: {stats['league']}")
        print(f"  Last update: {stats['last_update']}")

        # Test query
        print(f"\nTesting query for 'maximum Life' affixes...")
        life_tiers = loader.db.get_affix_tiers("%to maximum Life")
        print(f"Found {len(life_tiers)} tiers:")
        for tier, min_val, max_val in life_tiers[:5]:
            print(f"  T{tier}: {min_val}-{max_val} Life")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise

    print("\n" + "=" * 80)
