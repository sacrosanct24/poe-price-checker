"""Tests for data_sources/repoe_client.py - RePoE data client."""
import json
from unittest.mock import MagicMock, patch

import pytest

from data_sources.repoe_client import (
    ModData,
    BaseItemData,
    RePoEClient,
)


class TestModData:
    """Tests for ModData dataclass."""

    def test_create_mod_data(self):
        """Should create mod data with all fields."""
        mod = ModData(
            mod_id="LocalIncreasedPhysicalDamagePercentAndAccuracyRating1",
            name="of the Wrestler",
            domain="item",
            generation_type="suffix",
            required_level=11,
            stats=[{"id": "local_physical_damage_+%", "min": 60, "max": 69}],
            spawn_weights=[{"tag": "weapon", "weight": 1000}],
            groups=["LocalPhysicalDamageAndAccuracyRating"],
            implicit_tags=[],
            is_essence_only=False,
        )

        assert mod.mod_id == "LocalIncreasedPhysicalDamagePercentAndAccuracyRating1"
        assert mod.name == "of the Wrestler"
        assert mod.domain == "item"
        assert mod.generation_type == "suffix"

    def test_is_prefix(self):
        """is_prefix should be True for prefix mods."""
        mod = ModData(
            mod_id="test",
            name="Test",
            domain="item",
            generation_type="prefix",
            required_level=1,
            stats=[],
            spawn_weights=[],
            groups=[],
            implicit_tags=[],
            is_essence_only=False,
        )

        assert mod.is_prefix is True
        assert mod.is_suffix is False

    def test_is_suffix(self):
        """is_suffix should be True for suffix mods."""
        mod = ModData(
            mod_id="test",
            name="Test",
            domain="item",
            generation_type="suffix",
            required_level=1,
            stats=[],
            spawn_weights=[],
            groups=[],
            implicit_tags=[],
            is_essence_only=False,
        )

        assert mod.is_suffix is True
        assert mod.is_prefix is False

    def test_stat_ranges(self):
        """stat_ranges should return list of tuples."""
        mod = ModData(
            mod_id="test",
            name="Test",
            domain="item",
            generation_type="prefix",
            required_level=1,
            stats=[
                {"id": "maximum_life", "min": 80, "max": 89},
                {"id": "maximum_mana", "min": 40, "max": 44},
            ],
            spawn_weights=[],
            groups=[],
            implicit_tags=[],
            is_essence_only=False,
        )

        ranges = mod.stat_ranges
        assert len(ranges) == 2
        assert ranges[0] == ("maximum_life", 80, 89)
        assert ranges[1] == ("maximum_mana", 40, 44)


class TestBaseItemData:
    """Tests for BaseItemData dataclass."""

    def test_create_base_item(self):
        """Should create base item with all fields."""
        item = BaseItemData(
            item_id="Metadata/Items/Armours/BodyArmours/BodyInt1",
            name="Vaal Regalia",
            item_class="Body Armours",
            inventory_width=2,
            inventory_height=3,
            drop_level=68,
            tags=["int_armour", "body_armour", "default"],
            implicit_mods=["EnergyShieldImplicit1"],
            requirements={"int": 194, "level": 68},
        )

        assert item.name == "Vaal Regalia"
        assert item.item_class == "Body Armours"
        assert item.drop_level == 68
        assert "int_armour" in item.tags

    def test_default_values(self):
        """Should have default values for optional fields."""
        item = BaseItemData(
            item_id="test",
            name="Test",
            item_class="Test",
            inventory_width=1,
            inventory_height=1,
            drop_level=1,
            tags=[],
            implicit_mods=[],
            requirements={},
        )

        assert item.requirements == {}
        assert item.implicit_mods == []


class TestRePoEClient:
    """Tests for RePoEClient class."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temp cache directory."""
        cache_dir = tmp_path / "repoe_cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def client(self, temp_cache_dir):
        """Create client with temp cache."""
        return RePoEClient(cache_dir=temp_cache_dir, auto_download=False)

    @pytest.fixture
    def sample_mods_data(self):
        """Sample mods data for testing."""
        return {
            "IncreasedLife1": {
                "name": "of the Whelpling",
                "domain": "item",
                "generation_type": "suffix",
                "required_level": 1,
                "stats": [{"id": "maximum_life", "min": 10, "max": 19}],
                "spawn_weights": [{"tag": "ring", "weight": 1000}],
                "groups": ["IncreasedLife"],
            },
            "IncreasedLife2": {
                "name": "of the Lizard",
                "domain": "item",
                "generation_type": "suffix",
                "required_level": 11,
                "stats": [{"id": "maximum_life", "min": 20, "max": 29}],
                "spawn_weights": [{"tag": "ring", "weight": 1000}],
                "groups": ["IncreasedLife"],
            },
            "FireDamage1": {
                "name": "Heated",
                "domain": "item",
                "generation_type": "prefix",
                "required_level": 1,
                "stats": [{"id": "fire_damage_+%", "min": 5, "max": 9}],
                "spawn_weights": [{"tag": "weapon", "weight": 1000}],
                "groups": ["FireDamage"],
            },
        }

    @pytest.fixture
    def sample_base_items_data(self):
        """Sample base items data for testing."""
        return {
            "Metadata/Items/Rings/Ring1": {
                "name": "Coral Ring",
                "item_class": "Rings",
                "inventory_width": 1,
                "inventory_height": 1,
                "drop_level": 1,
                "tags": ["ring", "default"],
                "implicits": ["LifeImplicit1"],
                "requirements": {},
            },
            "Metadata/Items/Armours/BodyArmours/BodyInt1": {
                "name": "Vaal Regalia",
                "item_class": "Body Armours",
                "inventory_width": 2,
                "inventory_height": 3,
                "drop_level": 68,
                "tags": ["int_armour", "body_armour"],
                "implicits": ["EnergyShieldImplicit1"],
                "requirements": {"int": 194, "level": 68},
            },
        }

    def test_init_creates_cache_dir(self, tmp_path):
        """Should create cache directory on init."""
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        RePoEClient(cache_dir=cache_dir, auto_download=False)

        assert cache_dir.exists()

    def test_init_default_cache_dir(self):
        """Should use default cache directory."""
        with patch('data_sources.repoe_client.Path.mkdir'):
            client = RePoEClient(auto_download=False)
            assert "repoe_cache" in str(client.cache_dir)

    def test_data_files_constant(self, client):
        """Should have expected data files defined."""
        assert "mods" in client.DATA_FILES
        assert "base_items" in client.DATA_FILES
        assert "stat_translations" in client.DATA_FILES

    def test_get_cache_path(self, client, temp_cache_dir):
        """Should return correct cache path for data type."""
        path = client._get_cache_path("mods")
        assert path == temp_cache_dir / "mods.min.json"

    def test_load_data_from_cache(self, client, temp_cache_dir, sample_mods_data):
        """Should load data from cache file."""
        # Create cache file
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        result = client._load_data("mods")

        assert result is not None
        assert "IncreasedLife1" in result

    def test_load_data_caches_in_memory(self, client, temp_cache_dir, sample_mods_data):
        """Should cache loaded data in memory."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        client._load_data("mods")

        assert "mods" in client._data_cache

    def test_load_data_uses_memory_cache(self, client, temp_cache_dir, sample_mods_data):
        """Should use memory cache on subsequent calls."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        client._load_data("mods")
        # Modify memory cache
        client._data_cache["mods"]["test"] = "modified"

        result = client._load_data("mods")

        assert result.get("test") == "modified"

    def test_load_data_no_cache_no_download(self, client):
        """Should return None when no cache and auto_download=False."""
        result = client._load_data("mods")

        assert result is None

    @patch('data_sources.repoe_client.requests.get')
    def test_download_data(self, mock_get, client, sample_mods_data):
        """Should download data from RePoE GitHub."""
        client.auto_download = True
        mock_response = MagicMock()
        mock_response.json.return_value = sample_mods_data
        mock_get.return_value = mock_response

        result = client._download_data("mods")

        assert result is not None
        mock_get.assert_called_once()

    @patch('data_sources.repoe_client.requests.get')
    def test_download_data_caches_file(self, mock_get, client, temp_cache_dir, sample_mods_data):
        """Should cache downloaded data to file."""
        client.auto_download = True
        mock_response = MagicMock()
        mock_response.json.return_value = sample_mods_data
        mock_get.return_value = mock_response

        client._download_data("mods")

        cache_file = temp_cache_dir / "mods.min.json"
        assert cache_file.exists()

    def test_download_data_unknown_type(self, client):
        """Should return None for unknown data type."""
        result = client._download_data("unknown_type")

        assert result is None

    def test_get_mods(self, client, temp_cache_dir, sample_mods_data):
        """get_mods should return mods data."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        result = client.get_mods()

        assert result is not None
        assert "IncreasedLife1" in result

    def test_get_base_items(self, client, temp_cache_dir, sample_base_items_data):
        """get_base_items should return base items data."""
        cache_file = temp_cache_dir / "base_items.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_base_items_data, f)

        result = client.get_base_items()

        assert result is not None

    def test_find_mod_by_stat(self, client, temp_cache_dir, sample_mods_data):
        """Should find mods by stat text."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        results = client.find_mod_by_stat("maximum_life")

        assert len(results) == 2  # IncreasedLife1 and IncreasedLife2

    def test_find_mod_by_stat_no_matches(self, client, temp_cache_dir, sample_mods_data):
        """Should return empty list for no matches."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        results = client.find_mod_by_stat("nonexistent_stat")

        assert results == []

    def test_find_mods_for_item_tag(self, client, temp_cache_dir, sample_mods_data):
        """Should find mods for item tag."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        results = client.find_mods_for_item_tag("ring")

        assert len(results) == 2  # Life mods

    def test_find_mods_for_item_tag_with_generation_type(self, client, temp_cache_dir, sample_mods_data):
        """Should filter by generation type."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        results = client.find_mods_for_item_tag("weapon", generation_type="prefix")

        assert len(results) == 1
        assert results[0].name == "Heated"

    def test_get_mod_tiers(self, client, temp_cache_dir, sample_mods_data):
        """Should return sorted mod tiers."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        tiers = client.get_mod_tiers("maximum_life")

        assert len(tiers) == 2
        # Should be sorted by max value descending
        assert tiers[0][2] >= tiers[1][2]  # max values

    def test_parse_mod(self, client):
        """Should parse raw mod data correctly."""
        raw = {
            "name": "Test Mod",
            "domain": "item",
            "generation_type": "prefix",
            "required_level": 50,
            "stats": [{"id": "test", "min": 1, "max": 10}],
            "spawn_weights": [],
            "groups": ["TestGroup"],
            "implicit_tags": [],
            "is_essence_only": True,
        }

        mod = client._parse_mod("test_mod_id", raw)

        assert isinstance(mod, ModData)
        assert mod.mod_id == "test_mod_id"
        assert mod.name == "Test Mod"
        assert mod.is_essence_only is True

    def test_find_base_item(self, client, temp_cache_dir, sample_base_items_data):
        """Should find base item by name."""
        cache_file = temp_cache_dir / "base_items.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_base_items_data, f)

        result = client.find_base_item("Vaal Regalia")

        assert result is not None
        assert result.name == "Vaal Regalia"
        assert result.item_class == "Body Armours"

    def test_find_base_item_case_insensitive(self, client, temp_cache_dir, sample_base_items_data):
        """Should find base item case-insensitively."""
        cache_file = temp_cache_dir / "base_items.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_base_items_data, f)

        result = client.find_base_item("vaal regalia")

        assert result is not None
        assert result.name == "Vaal Regalia"

    def test_find_base_item_not_found(self, client, temp_cache_dir, sample_base_items_data):
        """Should return None for unknown base item."""
        cache_file = temp_cache_dir / "base_items.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_base_items_data, f)

        result = client.find_base_item("Nonexistent Item")

        assert result is None

    def test_parse_base_item(self, client):
        """Should parse raw base item data correctly."""
        raw = {
            "name": "Test Item",
            "item_class": "Rings",
            "inventory_width": 1,
            "inventory_height": 1,
            "drop_level": 10,
            "tags": ["ring"],
            "implicits": ["TestImplicit"],
            "requirements": {"level": 10},
        }

        item = client._parse_base_item("test_id", raw)

        assert isinstance(item, BaseItemData)
        assert item.item_id == "test_id"
        assert item.implicit_mods == ["TestImplicit"]

    def test_get_cache_stats(self, client, temp_cache_dir, sample_mods_data):
        """Should return cache statistics."""
        # Create a cache file
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        # Load it to populate memory cache
        client._load_data("mods")

        stats = client.get_cache_stats()

        assert "cache_dir" in stats
        assert stats["cached_files"] >= 1
        assert "mods" in stats["memory_cached"]

    def test_clear_cache(self, client, temp_cache_dir, sample_mods_data):
        """Should clear all cached data."""
        cache_file = temp_cache_dir / "mods.min.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_mods_data, f)

        client._load_data("mods")
        assert "mods" in client._data_cache

        client.clear_cache()

        assert client._data_cache == {}
        assert not cache_file.exists()
