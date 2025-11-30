"""
Tests for Build Library functionality.

Tests the CharacterManager methods for build organization,
search, export/import, and the new build library fields.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from core.pob_integration import (
    CharacterManager,
    CharacterProfile,
    PoBBuild,
    PoBItem,
    BuildCategory,
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage path."""
    return tmp_path / "characters.json"


@pytest.fixture
def manager(temp_storage):
    """Create a CharacterManager with temp storage."""
    return CharacterManager(storage_path=temp_storage)


@pytest.fixture
def sample_profile():
    """Create a sample CharacterProfile."""
    build = PoBBuild(
        class_name="Marauder",
        ascendancy="Juggernaut",
        level=95,
        main_skill="Cyclone",
        stats={"dps": 1000000, "life": 5500},
    )
    build.items["Helmet"] = PoBItem(
        slot="Helmet",
        rarity="RARE",
        name="Test Crown",
        base_type="Eternal Burgonet",
    )
    return CharacterProfile(
        name="Test Build",
        build=build,
        pob_code="test_code_123",
        notes="Test build for cyclone",
        categories=[BuildCategory.ENDGAME.value],
    )


class TestCharacterProfileLibraryFields:
    """Test the new library fields on CharacterProfile."""

    def test_default_values(self):
        """Test default values for library fields."""
        profile = CharacterProfile(name="Test", build=PoBBuild())
        assert profile.tags == []
        assert profile.guide_url == ""
        assert profile.ssf_friendly is False
        assert profile.favorite is False

    def test_set_library_fields(self):
        """Test setting library fields."""
        profile = CharacterProfile(
            name="Test",
            build=PoBBuild(),
            tags=["fast", "tanky"],
            guide_url="https://maxroll.gg/build",
            ssf_friendly=True,
            favorite=True,
        )
        assert profile.tags == ["fast", "tanky"]
        assert profile.guide_url == "https://maxroll.gg/build"
        assert profile.ssf_friendly is True
        assert profile.favorite is True


class TestCharacterManagerSerialization:
    """Test serialization/deserialization of library fields."""

    def test_serialize_library_fields(self, manager, sample_profile):
        """Test that library fields are serialized."""
        sample_profile.tags = ["mapper", "cheap"]
        sample_profile.guide_url = "https://example.com/guide"
        sample_profile.ssf_friendly = True
        sample_profile.favorite = True

        serialized = manager._serialize_profile(sample_profile)

        assert serialized["tags"] == ["mapper", "cheap"]
        assert serialized["guide_url"] == "https://example.com/guide"
        assert serialized["ssf_friendly"] is True
        assert serialized["favorite"] is True

    def test_deserialize_library_fields(self, manager):
        """Test that library fields are deserialized."""
        data = {
            "name": "Test Build",
            "pob_code": "abc123",
            "notes": "",
            "categories": [],
            "is_upgrade_target": False,
            "tags": ["budget", "league_start"],
            "guide_url": "https://example.com",
            "ssf_friendly": True,
            "favorite": True,
            "build": {
                "class_name": "Witch",
                "ascendancy": "Necromancer",
                "level": 90,
                "main_skill": "Summon Skeletons",
                "stats": {},
                "items": {},
            },
        }

        profile = manager._deserialize_profile(data)

        assert profile.tags == ["budget", "league_start"]
        assert profile.guide_url == "https://example.com"
        assert profile.ssf_friendly is True
        assert profile.favorite is True

    def test_deserialize_missing_library_fields(self, manager):
        """Test deserialization with missing library fields uses defaults."""
        data = {
            "name": "Old Build",
            "pob_code": "",
            "notes": "",
            "categories": [],
            "is_upgrade_target": False,
            "build": {
                "class_name": "Ranger",
                "ascendancy": "",
                "level": 1,
                "main_skill": "",
                "stats": {},
                "items": {},
            },
        }

        profile = manager._deserialize_profile(data)

        assert profile.tags == []
        assert profile.guide_url == ""
        assert profile.ssf_friendly is False
        assert profile.favorite is False


class TestCharacterManagerUpdateProfile:
    """Test the update_profile method."""

    def test_update_tags(self, manager, sample_profile):
        """Test updating tags via update_profile."""
        manager._profiles["Test Build"] = sample_profile

        result = manager.update_profile("Test Build", tags=["new", "tags"])

        assert result is True
        assert manager._profiles["Test Build"].tags == ["new", "tags"]

    def test_update_multiple_fields(self, manager, sample_profile):
        """Test updating multiple fields at once."""
        manager._profiles["Test Build"] = sample_profile

        result = manager.update_profile(
            "Test Build",
            tags=["updated"],
            guide_url="https://new.url",
            ssf_friendly=True,
            notes="New notes",
        )

        assert result is True
        profile = manager._profiles["Test Build"]
        assert profile.tags == ["updated"]
        assert profile.guide_url == "https://new.url"
        assert profile.ssf_friendly is True
        assert profile.notes == "New notes"

    def test_update_nonexistent_profile(self, manager):
        """Test updating a profile that doesn't exist."""
        result = manager.update_profile("Nonexistent", tags=["test"])
        assert result is False


class TestCharacterManagerTagMethods:
    """Test tag-related methods."""

    def test_set_tags(self, manager, sample_profile):
        """Test set_tags method."""
        manager._profiles["Test Build"] = sample_profile

        result = manager.set_tags("Test Build", ["a", "b", "c"])

        assert result is True
        assert manager._profiles["Test Build"].tags == ["a", "b", "c"]

    def test_add_tag(self, manager, sample_profile):
        """Test adding a single tag."""
        sample_profile.tags = ["existing"]
        manager._profiles["Test Build"] = sample_profile

        result = manager.add_tag("Test Build", "new_tag")

        assert result is True
        assert "new_tag" in manager._profiles["Test Build"].tags
        assert "existing" in manager._profiles["Test Build"].tags

    def test_add_duplicate_tag(self, manager, sample_profile):
        """Test adding a duplicate tag doesn't create duplicates."""
        sample_profile.tags = ["existing"]
        manager._profiles["Test Build"] = sample_profile

        manager.add_tag("Test Build", "existing")

        assert manager._profiles["Test Build"].tags.count("existing") == 1

    def test_remove_tag(self, manager, sample_profile):
        """Test removing a tag."""
        sample_profile.tags = ["keep", "remove"]
        manager._profiles["Test Build"] = sample_profile

        result = manager.remove_tag("Test Build", "remove")

        assert result is True
        assert manager._profiles["Test Build"].tags == ["keep"]

    def test_get_all_tags(self, manager):
        """Test get_all_tags returns all unique tags."""
        profile1 = CharacterProfile(
            name="Build1",
            build=PoBBuild(),
            tags=["tag1", "tag2"],
        )
        profile2 = CharacterProfile(
            name="Build2",
            build=PoBBuild(),
            tags=["tag2", "tag3"],
        )
        manager._profiles["Build1"] = profile1
        manager._profiles["Build2"] = profile2

        tags = manager.get_all_tags()

        assert sorted(tags) == ["tag1", "tag2", "tag3"]

    def test_get_builds_by_tag(self, manager):
        """Test filtering builds by tag."""
        profile1 = CharacterProfile(
            name="Build1",
            build=PoBBuild(),
            tags=["mapper"],
        )
        profile2 = CharacterProfile(
            name="Build2",
            build=PoBBuild(),
            tags=["bosser"],
        )
        manager._profiles["Build1"] = profile1
        manager._profiles["Build2"] = profile2

        mapper_builds = manager.get_builds_by_tag("mapper")

        assert len(mapper_builds) == 1
        assert mapper_builds[0].name == "Build1"


class TestCharacterManagerFavorites:
    """Test favorite functionality."""

    def test_toggle_favorite_on(self, manager, sample_profile):
        """Test toggling favorite on."""
        sample_profile.favorite = False
        manager._profiles["Test Build"] = sample_profile

        result = manager.toggle_favorite("Test Build")

        assert result is True
        assert manager._profiles["Test Build"].favorite is True

    def test_toggle_favorite_off(self, manager, sample_profile):
        """Test toggling favorite off."""
        sample_profile.favorite = True
        manager._profiles["Test Build"] = sample_profile

        result = manager.toggle_favorite("Test Build")

        assert result is True
        assert manager._profiles["Test Build"].favorite is False

    def test_get_favorite_builds(self, manager):
        """Test getting favorite builds."""
        profile1 = CharacterProfile(name="Fav", build=PoBBuild(), favorite=True)
        profile2 = CharacterProfile(name="NotFav", build=PoBBuild(), favorite=False)
        manager._profiles["Fav"] = profile1
        manager._profiles["NotFav"] = profile2

        favorites = manager.get_favorite_builds()

        assert len(favorites) == 1
        assert favorites[0].name == "Fav"


class TestCharacterManagerSSF:
    """Test SSF functionality."""

    def test_set_ssf_friendly(self, manager, sample_profile):
        """Test setting SSF friendly flag."""
        manager._profiles["Test Build"] = sample_profile

        result = manager.set_ssf_friendly("Test Build", True)

        assert result is True
        assert manager._profiles["Test Build"].ssf_friendly is True

    def test_get_ssf_builds(self, manager):
        """Test getting SSF-friendly builds."""
        profile1 = CharacterProfile(name="SSF", build=PoBBuild(), ssf_friendly=True)
        profile2 = CharacterProfile(name="Trade", build=PoBBuild(), ssf_friendly=False)
        manager._profiles["SSF"] = profile1
        manager._profiles["Trade"] = profile2

        ssf_builds = manager.get_ssf_builds()

        assert len(ssf_builds) == 1
        assert ssf_builds[0].name == "SSF"


class TestCharacterManagerGuideUrl:
    """Test guide URL functionality."""

    def test_set_guide_url(self, manager, sample_profile):
        """Test setting guide URL."""
        manager._profiles["Test Build"] = sample_profile

        result = manager.set_guide_url("Test Build", "https://maxroll.gg/poe/build")

        assert result is True
        assert manager._profiles["Test Build"].guide_url == "https://maxroll.gg/poe/build"


class TestCharacterManagerSearch:
    """Test search functionality."""

    @pytest.fixture
    def populated_manager(self, manager):
        """Create manager with multiple profiles."""
        manager._profiles["Cyclone Jugg"] = CharacterProfile(
            name="Cyclone Jugg",
            build=PoBBuild(ascendancy="Juggernaut", main_skill="Cyclone"),
            categories=[BuildCategory.ENDGAME.value],
            tags=["tanky", "melee"],
            ssf_friendly=True,
            favorite=True,
        )
        manager._profiles["Lightning Arrow"] = CharacterProfile(
            name="Lightning Arrow",
            build=PoBBuild(ascendancy="Deadeye", main_skill="Lightning Arrow"),
            categories=[BuildCategory.MAPPER.value],
            tags=["fast", "ranged"],
            ssf_friendly=False,
            favorite=False,
        )
        manager._profiles["RF Jugg"] = CharacterProfile(
            name="RF Jugg",
            build=PoBBuild(ascendancy="Juggernaut", main_skill="Righteous Fire"),
            categories=[BuildCategory.LEAGUE_STARTER.value],
            tags=["tanky", "budget"],
            ssf_friendly=True,
            favorite=False,
        )
        return manager

    def test_search_by_query(self, populated_manager):
        """Test search by query string."""
        results = populated_manager.search_builds(query="cyclone")
        assert len(results) == 1
        assert results[0].name == "Cyclone Jugg"

    def test_search_by_ascendancy(self, populated_manager):
        """Test search matches ascendancy."""
        results = populated_manager.search_builds(query="juggernaut")
        assert len(results) == 2

    def test_search_by_category(self, populated_manager):
        """Test search by category filter."""
        results = populated_manager.search_builds(
            categories=[BuildCategory.ENDGAME.value]
        )
        assert len(results) == 1
        assert results[0].name == "Cyclone Jugg"

    def test_search_by_tag(self, populated_manager):
        """Test search by tag filter."""
        results = populated_manager.search_builds(tags=["tanky"])
        assert len(results) == 2

    def test_search_ssf_only(self, populated_manager):
        """Test SSF-only filter."""
        results = populated_manager.search_builds(ssf_only=True)
        assert len(results) == 2
        assert all(r.ssf_friendly for r in results)

    def test_search_favorites_only(self, populated_manager):
        """Test favorites-only filter."""
        results = populated_manager.search_builds(favorites_only=True)
        assert len(results) == 1
        assert results[0].name == "Cyclone Jugg"

    def test_search_combined_filters(self, populated_manager):
        """Test combining multiple filters."""
        results = populated_manager.search_builds(
            tags=["tanky"],
            ssf_only=True,
            favorites_only=True,
        )
        assert len(results) == 1
        assert results[0].name == "Cyclone Jugg"

    def test_search_no_results(self, populated_manager):
        """Test search with no matches."""
        results = populated_manager.search_builds(query="nonexistent")
        assert len(results) == 0


class TestCharacterManagerExportImport:
    """Test export/import functionality."""

    def test_export_profile(self, manager, sample_profile):
        """Test exporting a profile."""
        sample_profile.tags = ["exported"]
        sample_profile.favorite = True
        manager._profiles["Test Build"] = sample_profile

        exported = manager.export_profile("Test Build")

        assert exported is not None
        assert exported["name"] == "Test Build"
        assert exported["tags"] == ["exported"]
        assert exported["favorite"] is True

    def test_export_nonexistent(self, manager):
        """Test exporting a nonexistent profile."""
        result = manager.export_profile("Nonexistent")
        assert result is None

    def test_import_profile(self, manager):
        """Test importing a profile."""
        data = {
            "name": "Imported Build",
            "pob_code": "import_code",
            "notes": "Imported",
            "categories": [BuildCategory.IMPORTED.value],
            "is_upgrade_target": False,
            "tags": ["imported"],
            "guide_url": "https://imported.url",
            "ssf_friendly": True,
            "favorite": False,
            "build": {
                "class_name": "Templar",
                "ascendancy": "Guardian",
                "level": 100,
                "main_skill": "Smite",
                "stats": {},
                "items": {},
            },
        }

        name = manager.import_profile(data)

        assert name == "Imported Build"
        assert "Imported Build" in manager._profiles
        profile = manager._profiles["Imported Build"]
        assert profile.tags == ["imported"]
        assert profile.ssf_friendly is True

    def test_import_duplicate_name(self, manager, sample_profile):
        """Test importing with duplicate name creates unique name."""
        manager._profiles["Test Build"] = sample_profile

        data = {
            "name": "Test Build",
            "pob_code": "new_code",
            "notes": "",
            "categories": [],
            "is_upgrade_target": False,
            "build": {
                "class_name": "Shadow",
                "ascendancy": "",
                "level": 1,
                "main_skill": "",
                "stats": {},
                "items": {},
            },
        }

        name = manager.import_profile(data, overwrite=False)

        assert name == "Test Build (1)"
        assert "Test Build (1)" in manager._profiles

    def test_import_overwrite(self, manager, sample_profile):
        """Test importing with overwrite replaces existing."""
        manager._profiles["Test Build"] = sample_profile

        data = {
            "name": "Test Build",
            "pob_code": "replaced_code",
            "notes": "Replaced",
            "categories": [],
            "is_upgrade_target": False,
            "build": {
                "class_name": "Duelist",
                "ascendancy": "Champion",
                "level": 50,
                "main_skill": "Lacerate",
                "stats": {},
                "items": {},
            },
        }

        name = manager.import_profile(data, overwrite=True)

        assert name == "Test Build"
        assert manager._profiles["Test Build"].build.ascendancy == "Champion"

    def test_import_invalid_data(self, manager):
        """Test importing invalid data returns None."""
        result = manager.import_profile({"invalid": "data"})
        assert result is None

    def test_get_all_profiles(self, manager, sample_profile):
        """Test getting all profiles as list."""
        manager._profiles["Build1"] = sample_profile
        manager._profiles["Build2"] = CharacterProfile(name="Build2", build=PoBBuild())

        profiles = manager.get_all_profiles()

        assert len(profiles) == 2


class TestPersistence:
    """Test that changes are persisted to storage."""

    def test_library_fields_persist(self, temp_storage):
        """Test that library fields are saved and loaded."""
        # Create and modify manager
        manager1 = CharacterManager(storage_path=temp_storage)
        manager1._profiles["Test"] = CharacterProfile(
            name="Test",
            build=PoBBuild(),
            tags=["persisted"],
            guide_url="https://test.com",
            ssf_friendly=True,
            favorite=True,
        )
        manager1._save_profiles()

        # Create new manager instance
        manager2 = CharacterManager(storage_path=temp_storage)

        assert "Test" in manager2._profiles
        profile = manager2._profiles["Test"]
        assert profile.tags == ["persisted"]
        assert profile.guide_url == "https://test.com"
        assert profile.ssf_friendly is True
        assert profile.favorite is True
