"""Tests for data_sources/mod_database.py - Local mod/affix database."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from data_sources.mod_database import ModDatabase


class TestModDatabase:
    """Tests for ModDatabase class."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temp database path."""
        return tmp_path / "test_mods.db"

    @pytest.fixture
    def db(self, temp_db_path):
        """Create ModDatabase with temp path."""
        return ModDatabase(db_path=temp_db_path)

    def test_init_creates_database(self, temp_db_path):
        """Database file should be created on init."""
        assert not temp_db_path.exists()

        db = ModDatabase(db_path=temp_db_path)

        assert temp_db_path.exists()
        db.close()

    def test_init_creates_parent_dirs(self, tmp_path):
        """Parent directories should be created if needed."""
        deep_path = tmp_path / "deep" / "nested" / "mods.db"

        db = ModDatabase(db_path=deep_path)

        assert deep_path.parent.exists()
        db.close()

    def test_init_creates_tables(self, db):
        """Required tables should be created."""
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "mods" in tables
        assert "items" in tables
        assert "metadata" in tables

    def test_context_manager(self, temp_db_path):
        """Should support context manager protocol."""
        with ModDatabase(db_path=temp_db_path) as db:
            assert db.conn is not None

        # Connection should be closed after context
        assert db.conn is None

    def test_close(self, db):
        """close() should close connection."""
        assert db.conn is not None

        db.close()

        assert db.conn is None


class TestModDatabaseMetadata:
    """Tests for metadata operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create ModDatabase with temp path."""
        return ModDatabase(db_path=tmp_path / "mods.db")

    def test_set_and_get_metadata(self, db):
        """Should store and retrieve metadata."""
        db.set_metadata("test_key", "test_value")

        result = db.get_metadata("test_key")

        assert result == "test_value"

    def test_get_metadata_not_found(self, db):
        """Should return None for missing key."""
        result = db.get_metadata("nonexistent")

        assert result is None

    def test_set_metadata_updates_existing(self, db):
        """Should update existing metadata."""
        db.set_metadata("key", "value1")
        db.set_metadata("key", "value2")

        result = db.get_metadata("key")

        assert result == "value2"

    def test_get_last_update_time(self, db):
        """Should return last update datetime."""
        now = datetime.now()
        db.set_metadata("last_update", now.isoformat())

        result = db.get_last_update_time()

        assert result is not None
        assert abs((result - now).total_seconds()) < 1

    def test_get_last_update_time_none(self, db):
        """Should return None if not set."""
        result = db.get_last_update_time()

        assert result is None

    def test_get_current_league(self, db):
        """Should return current league."""
        db.set_metadata("league", "Settlers")

        result = db.get_current_league()

        assert result == "Settlers"

    def test_should_update_empty_db(self, db):
        """Should return True for empty database."""
        result = db.should_update("Settlers")

        assert result is True

    def test_should_update_league_changed(self, db):
        """Should return True when league changes."""
        db.set_metadata("league", "Previous")
        db.set_metadata("last_update", datetime.now().isoformat())

        result = db.should_update("Settlers")

        assert result is True

    def test_should_update_stale_data(self, db):
        """Should return True for data older than 7 days."""
        db.set_metadata("league", "Settlers")
        old_time = datetime.now() - timedelta(days=10)
        db.set_metadata("last_update", old_time.isoformat())

        result = db.should_update("Settlers")

        assert result is True

    def test_should_update_fresh_data(self, db):
        """Should return False for fresh data."""
        db.set_metadata("league", "Settlers")
        db.set_metadata("last_update", datetime.now().isoformat())

        result = db.should_update("Settlers")

        assert result is False


class TestModDatabaseMods:
    """Tests for mod operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create ModDatabase with temp path."""
        return ModDatabase(db_path=tmp_path / "mods.db")

    @pytest.fixture
    def sample_mods(self):
        """Sample mod data."""
        return [
            {
                "id": "mod1",
                "name": "IncreasedLife1",
                "stat_text": "+(10-20) to maximum Life",
                "stat_text_raw": "+(10-20) to maximum Life",
                "domain": 1,
                "generation_type": 1,
                "tier_text": "Tier 3",
                "required_level": 10,
            },
            {
                "id": "mod2",
                "name": "IncreasedLife2",
                "stat_text": "+(30-40) to maximum Life",
                "stat_text_raw": "+(30-40) to maximum Life",
                "domain": 1,
                "generation_type": 1,
                "tier_text": "Tier 2",
                "required_level": 30,
            },
            {
                "id": "mod3",
                "name": "IncreasedLife3",
                "stat_text": "+(50-60) to maximum Life",
                "stat_text_raw": "+(50-60) to maximum Life",
                "domain": 1,
                "generation_type": 1,
                "tier_text": "Tier 1",
                "required_level": 50,
            },
        ]

    def test_insert_mods(self, db, sample_mods):
        """Should insert mods."""
        count = db.insert_mods(sample_mods)

        assert count == 3
        assert db.get_mod_count() == 3

    def test_insert_mods_handles_api_format(self, db):
        """Should handle API format with spaces in field names."""
        api_mods = [
            {
                "id": "mod1",
                "name": "Test",
                "stat text": "Test stat",  # Space in field name
                "stat text raw": "Test stat raw",
                "domain": "1",
                "generation type": "1",  # Space in field name
                "tier text": "Tier 1",
            }
        ]

        count = db.insert_mods(api_mods)

        assert count == 1

    def test_insert_mods_replaces_existing(self, db, sample_mods):
        """Should replace existing mods."""
        db.insert_mods(sample_mods)

        # Update one mod
        sample_mods[0]["stat_text"] = "Updated text"
        db.insert_mods([sample_mods[0]])

        # Count should still be 3, not 4
        assert db.get_mod_count() == 3

    def test_find_mods_by_stat_text(self, db, sample_mods):
        """Should find mods by stat text pattern."""
        db.insert_mods(sample_mods)

        results = db.find_mods_by_stat_text("%maximum Life%")

        assert len(results) == 3

    def test_find_mods_by_stat_text_empty(self, db, sample_mods):
        """Should return empty list for no matches."""
        db.insert_mods(sample_mods)

        results = db.find_mods_by_stat_text("%Energy Shield%")

        assert results == []

    def test_find_mods_by_stat_text_generation_type(self, db, sample_mods):
        """Should filter by generation type."""
        db.insert_mods(sample_mods)

        # Add a suffix mod (generation_type = 2)
        suffix_mod = {
            "id": "suffix1",
            "name": "IncreasedLifeSuffix",
            "stat_text": "+5 to maximum Life",
            "generation_type": 2,
            "domain": 1,
        }
        db.insert_mods([suffix_mod])

        results = db.find_mods_by_stat_text("%maximum Life%", generation_type=1)

        assert len(results) == 3  # Only prefix mods

    def test_get_affix_tiers(self, db, sample_mods):
        """Should return tier ranges sorted."""
        db.insert_mods(sample_mods)

        tiers = db.get_affix_tiers("%maximum Life%")

        assert len(tiers) == 3
        # Should be sorted by tier number (T1 first)
        assert tiers[0][0] == 1  # Tier 1
        assert tiers[1][0] == 2  # Tier 2
        assert tiers[2][0] == 3  # Tier 3

    def test_get_affix_tiers_empty(self, db):
        """Should return empty list for no matches."""
        tiers = db.get_affix_tiers("%nonexistent%")

        assert tiers == []


class TestModDatabaseItems:
    """Tests for item operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create ModDatabase with temp path."""
        return ModDatabase(db_path=tmp_path / "mods.db")

    @pytest.fixture
    def sample_items(self):
        """Sample item data."""
        return [
            {
                "name": "Headhunter",
                "base_item": "Leather Belt",
                "item_class": "Belt",
                "rarity": "Unique",
                "required_level": 40,
                "drop_enabled": 1,
            },
            {
                "name": "Mageblood",
                "base_item": "Heavy Belt",
                "item_class": "Belt",
                "rarity": "Unique",
                "required_level": 44,
                "drop_enabled": 1,
            },
            {
                "name": "House of Mirrors",
                "base_item": None,
                "item_class": "Divination Card",
                "rarity": "Normal",
                "required_level": None,
                "drop_enabled": 1,
            },
        ]

    def test_insert_items(self, db, sample_items):
        """Should insert items."""
        count = db.insert_items(sample_items)

        assert count == 3
        assert db.get_item_count() == 3

    def test_insert_items_handles_api_format(self, db):
        """Should handle API format with spaces in field names."""
        api_items = [
            {
                "name": "Headhunter",
                "base item": "Leather Belt",  # Space in field name
                "class": "Belt",  # Different name
                "rarity": "Unique",
                "required level": 40,  # Space in field name
                "drop enabled": 1,
            }
        ]

        count = db.insert_items(api_items)

        assert count == 1

    def test_find_unique_by_name(self, db, sample_items):
        """Should find unique item by name."""
        db.insert_items(sample_items)

        result = db.find_unique_by_name("Headhunter")

        assert result is not None
        assert result["name"] == "Headhunter"
        assert result["item_class"] == "Belt"

    def test_find_unique_by_name_not_found(self, db, sample_items):
        """Should return None for not found."""
        db.insert_items(sample_items)

        result = db.find_unique_by_name("Nonexistent")

        assert result is None

    def test_find_unique_by_name_not_unique(self, db, sample_items):
        """Should return None for non-unique items."""
        db.insert_items(sample_items)

        # House of Mirrors is Normal rarity, not Unique
        result = db.find_unique_by_name("House of Mirrors")

        assert result is None

    def test_find_items_by_base(self, db, sample_items):
        """Should find items by base type."""
        db.insert_items(sample_items)

        results = db.find_items_by_base("Leather Belt")

        assert len(results) == 1
        assert results[0]["name"] == "Headhunter"

    def test_get_unique_items_by_class(self, db, sample_items):
        """Should get unique items by class."""
        db.insert_items(sample_items)

        results = db.get_unique_items_by_class("Belt")

        assert len(results) == 2
        names = {r["name"] for r in results}
        assert "Headhunter" in names
        assert "Mageblood" in names

    def test_get_unique_item_count(self, db, sample_items):
        """Should count only unique items."""
        db.insert_items(sample_items)

        count = db.get_unique_item_count()

        assert count == 2  # Headhunter and Mageblood

    def test_get_items_by_class(self, db, sample_items):
        """Should get all items of a class."""
        db.insert_items(sample_items)

        results = db.get_items_by_class("Divination Card")

        assert len(results) == 1
        assert results[0]["name"] == "House of Mirrors"

    def test_get_divination_cards(self, db, sample_items):
        """Should get divination cards."""
        db.insert_items(sample_items)

        results = db.get_divination_cards()

        assert len(results) == 1
        assert results[0]["name"] == "House of Mirrors"

    def test_find_item_by_name(self, db, sample_items):
        """Should find any item by name."""
        db.insert_items(sample_items)

        result = db.find_item_by_name("House of Mirrors")

        assert result is not None
        assert result["item_class"] == "Divination Card"

    def test_search_items(self, db, sample_items):
        """Should search items by pattern."""
        db.insert_items(sample_items)

        results = db.search_items("%blood%")

        assert len(results) == 1
        assert results[0]["name"] == "Mageblood"

    def test_search_items_limit(self, db, sample_items):
        """Should respect limit."""
        db.insert_items(sample_items)

        results = db.search_items("%", limit=2)

        assert len(results) == 2

    def test_get_scarabs(self, db):
        """Should find items with 'Scarab' in name."""
        scarab_items = [
            {"name": "Polished Breach Scarab", "item_class": "Map Fragment"},
            {"name": "Gilded Ambush Scarab", "item_class": "Map Fragment"},
            {"name": "Fragment of the Minotaur", "item_class": "Map Fragment"},
        ]
        db.insert_items(scarab_items)

        results = db.get_scarabs()

        assert len(results) == 2
        names = {r["name"] for r in results}
        assert "Polished Breach Scarab" in names
        assert "Gilded Ambush Scarab" in names
