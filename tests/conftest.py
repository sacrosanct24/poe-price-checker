# tests/conftest.py
"""
Pytest configuration and fixtures for PoE Price Checker tests.
Provides clean test isolation and shared fixtures.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from core.config import Config
from core.database import Database
from core.item_parser import ItemParser, ParsedItem
from core.game_version import GameVersion


@pytest.fixture
def temp_config_file(tmp_path):
    """Provide a temporary config file path that auto-cleans"""
    config_path = tmp_path / "config.json"
    yield config_path
    # Cleanup happens automatically via tmp_path


@pytest.fixture
def temp_config(tmp_path):
    """
    Provide a fresh Config instance with isolated storage.
    Each test gets a completely clean config with no shared state.

    CRITICAL: Uses tmp_path to ensure complete isolation from user's actual config.
    """
    config_path = tmp_path / "test_config.json"
    config = Config(config_file=config_path)
    return config


@pytest.fixture
def temp_db_file(tmp_path):
    """Provide a temporary database file path"""
    db_path = tmp_path / "test.db"
    yield db_path
    # Cleanup happens automatically


@pytest.fixture
def temp_db(tmp_path):
    """
    Provide a fresh Database instance with isolated storage.
    Each test gets a completely clean database.

    CRITICAL: Uses tmp_path to ensure complete isolation.
    """
    db_path = tmp_path / "test_database.db"
    db = Database(db_path=db_path)
    yield db
    db.close()


@pytest.fixture
def parser():
    """Provide an ItemParser instance"""
    return ItemParser()


@pytest.fixture
def sample_unique_item():
    """Sample unique item text"""
    return """Rarity: UNIQUE
Shavronne's Wrappings
Occultist's Vestment
--------
Energy Shield: 300
--------
Item Level: 85
Sockets: B-B-B-B-B-B
--------
+1 to Level of Socketed Gems
200% increased Energy Shield
+50 to Intelligence
Chaos Damage does not bypass Energy Shield
--------
Corrupted"""


@pytest.fixture
def sample_currency():
    """Sample currency item text"""
    return """Stack Size: 15/40
Divine Orb"""


@pytest.fixture
def sample_rare_item():
    """Sample rare item text"""
    return """Rarity: RARE
Doom Guard
Vaal Regalia
--------
Quality: +20%
Energy Shield: 450
--------
Item Level: 86
Sockets: B-B-B-B-B-B
--------
+120 to maximum Energy Shield
+45% to Fire Resistance
+38% to Cold Resistance"""


@pytest.fixture
def sample_magic_item():
    """Sample magic item text"""
    return """Rarity: MAGIC
Seething Divine Life Flask of Staunching
--------
Quality: +20%
--------
Recovers 2400 Life over 0.30 seconds
Immunity to Bleeding during Flask effect
Removes Bleeding on use"""


@pytest.fixture
def sample_normal_item():
    """Sample normal item text"""
    return """Rarity: NORMAL
Iron Ring"""


@pytest.fixture
def sample_item_with_implicit():
    """Item with implicit mod"""
    return """Rarity: RARE
Crystal Belt
--------
+80 to maximum Energy Shield (implicit)
--------
+45 to maximum Life
+38% to Cold Resistance
+25% to Lightning Resistance"""


@pytest.fixture
def sample_item_with_enchant():
    """Item with enchant"""
    return """Rarity: RARE
Lion Pelt Hubris Circlet
--------
Tornado Shot fires 2 additional secondary Projectiles (enchant)
--------
+75 to maximum Energy Shield
+42% to Fire Resistance"""