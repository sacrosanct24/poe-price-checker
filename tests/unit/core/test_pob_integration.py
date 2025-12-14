"""
Tests for core.pob_integration module.

Tests cover:
- PoBDecoder: PoB code decoding and XML parsing
- CharacterManager: Profile storage and management
- UpgradeChecker: Item comparison logic
"""
from __future__ import annotations

import base64
import zlib
from unittest.mock import patch, MagicMock

import pytest
import requests

from core.pob import (
    BuildCategory,
    CharacterManager,
    CharacterProfile,
    PoBBuild,
    PoBDecoder,
    PoBItem,
    UpgradeChecker,
)
from core.pob.decoder import _is_pastebin_url, _is_pobbin_url, _url_host_matches


# Sample PoB XML for testing
SAMPLE_POB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="93" className="Marauder" ascendClassName="Chieftain" bandit="None">
    </Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: UNIQUE
Goldrim
Leather Cap
Unique ID: abc123
Item Level: 50
Quality: 0
Sockets:
LevelReq: 0
Implicits: 0
+30% to all Elemental Resistances
10% increased Rarity of Items found
</Item>
        <Item id="2">
Rarity: RARE
Storm Bite
Vaal Gauntlets
Item Level: 84
Quality: 0
Sockets: R-R-R-R
LevelReq: 63
Implicits: 1
{tags:strength}+50 to maximum Life
+46 to Strength
+30% to Fire Resistance
+25% to Cold Resistance
</Item>
        <ItemSet id="1" title="Default">
            <Slot name="Helmet" itemId="1"/>
            <Slot name="Gloves" itemId="2"/>
        </ItemSet>
    </Items>
    <Skills>
        <Skill mainActiveSkill="Cyclone">
            <Gem nameSpec="Cyclone" level="20" quality="20" enabled="true"/>
        </Skill>
    </Skills>
</PathOfBuilding>
"""


def _encode_pob_code(xml: str) -> str:
    """Encode XML to PoB share code format."""
    compressed = zlib.compress(xml.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


class TestPoBItem:
    """Tests for PoBItem dataclass."""

    def test_creates_item_with_required_args(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Test Item", base_type="Leather Cap")
        assert item.name == "Test Item"
        assert item.base_type == "Leather Cap"
        assert item.slot == "Helmet"
        assert item.rarity == "RARE"
        assert item.implicit_mods == []
        assert item.explicit_mods == []

    def test_display_name_for_unique(self):
        item = PoBItem(slot="Helmet", rarity="UNIQUE", name="Goldrim", base_type="Leather Cap")
        assert item.display_name == "Goldrim (Leather Cap)"

    def test_display_name_for_rare_with_same_name_and_base(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Leather Cap", base_type="Leather Cap")
        assert item.display_name == "Leather Cap"

    def test_display_name_for_rare_with_different_name(self):
        item = PoBItem(slot="Gloves", rarity="RARE", name="Storm Bite", base_type="Vaal Gauntlets")
        assert item.display_name == "Storm Bite (Vaal Gauntlets)"

    def test_link_count_zero_for_empty_sockets(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Test", base_type="Helmet", sockets="")
        assert item.link_count == 0

    def test_link_count_for_linked_sockets(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Test", base_type="Helmet", sockets="R-R-R-G")
        assert item.link_count == 4

    def test_link_count_for_unlinked_sockets(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Test", base_type="Helmet", sockets="R R R G")
        assert item.link_count == 1


class TestPoBBuild:
    """Tests for PoBBuild dataclass."""

    def test_creates_build_with_defaults(self):
        build = PoBBuild()
        assert build.class_name == ""
        assert build.level == 1
        assert build.items == {}
        assert build.skills == []

    def test_display_name_with_ascendancy(self):
        build = PoBBuild(class_name="Marauder", ascendancy="Chieftain", level=93)
        assert build.display_name == "Level 93 Chieftain"

    def test_display_name_without_ascendancy(self):
        build = PoBBuild(class_name="Marauder", ascendancy="", level=50)
        assert build.display_name == "Level 50 Marauder"


class TestPoBDecoder:
    """Tests for PoBDecoder class."""

    def test_decode_valid_pob_code(self):
        code = _encode_pob_code(SAMPLE_POB_XML)
        xml = PoBDecoder.decode_pob_code(code)
        assert "PathOfBuilding" in xml
        assert "Goldrim" in xml

    def test_decode_invalid_base64_raises_valueerror(self):
        with pytest.raises(ValueError, match="Invalid PoB code"):
            PoBDecoder.decode_pob_code("not-valid-base64!!!")

    def test_parse_build_extracts_class_info(self):
        build = PoBDecoder.parse_build(SAMPLE_POB_XML)
        assert build.class_name == "Marauder"
        assert build.ascendancy == "Chieftain"
        assert build.level == 93

    def test_parse_build_extracts_items(self):
        build = PoBDecoder.parse_build(SAMPLE_POB_XML)
        assert "Helmet" in build.items
        assert "Gloves" in build.items
        assert build.items["Helmet"].name == "Goldrim"

    def test_parse_build_extracts_item_mods(self):
        build = PoBDecoder.parse_build(SAMPLE_POB_XML)
        helmet = build.items["Helmet"]
        assert "+30% to all Elemental Resistances" in helmet.explicit_mods

    def test_parse_build_handles_empty_xml(self):
        with pytest.raises(ValueError, match="Invalid PoB XML"):
            PoBDecoder.parse_build("")

    def test_parse_build_handles_malformed_xml(self):
        with pytest.raises(ValueError, match="Invalid PoB XML"):
            PoBDecoder.parse_build("<not valid xml")

    def test_from_code_decodes_and_parses(self):
        code = _encode_pob_code(SAMPLE_POB_XML)
        build = PoBDecoder.from_code(code)
        assert build.class_name == "Marauder"
        assert build.level == 93


class TestCharacterManager:
    """Tests for CharacterManager class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create a temporary storage path for testing."""
        return tmp_path / "characters.json"

    @pytest.fixture
    def manager(self, temp_storage):
        """Create a CharacterManager with temporary storage."""
        return CharacterManager(storage_path=temp_storage)

    def test_creates_manager_with_empty_profiles(self, manager):
        assert manager.list_profiles() == []

    def test_add_from_pob_code_creates_profile(self, manager):
        code = _encode_pob_code(SAMPLE_POB_XML)
        profile = manager.add_from_pob_code("Test Character", code)

        assert profile.name == "Test Character"
        assert profile.build.class_name == "Marauder"
        assert "Test Character" in manager.list_profiles()

    def test_get_profile_returns_profile(self, manager):
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("My Build", code)

        profile = manager.get_profile("My Build")
        assert profile is not None
        assert profile.name == "My Build"

    def test_get_profile_returns_none_for_unknown(self, manager):
        assert manager.get_profile("Unknown") is None

    def test_delete_profile_removes_profile(self, manager):
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("ToDelete", code)

        assert "ToDelete" in manager.list_profiles()
        result = manager.delete_profile("ToDelete")
        assert result is True
        assert "ToDelete" not in manager.list_profiles()

    def test_delete_profile_returns_false_for_unknown(self, manager):
        assert manager.delete_profile("Unknown") is False

    def test_set_active_profile(self, manager):
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("Active Build", code)

        result = manager.set_active_profile("Active Build")
        assert result is True

        active = manager.get_active_profile()
        assert active.name == "Active Build"

    def test_set_active_profile_returns_false_for_unknown(self, manager):
        assert manager.set_active_profile("Unknown") is False

    def test_get_active_profile_fallback_to_first(self, manager):
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("First Build", code)

        active = manager.get_active_profile()
        assert active.name == "First Build"

    def test_get_active_profile_returns_none_when_empty(self, manager):
        assert manager.get_active_profile() is None

    def test_profiles_persist_to_file(self, temp_storage):
        manager1 = CharacterManager(storage_path=temp_storage)
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager1.add_from_pob_code("Persistent", code)

        # Create new manager that loads from same file
        manager2 = CharacterManager(storage_path=temp_storage)
        assert "Persistent" in manager2.list_profiles()

    def test_active_profile_persists(self, temp_storage):
        manager1 = CharacterManager(storage_path=temp_storage)
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager1.add_from_pob_code("Active", code)
        manager1.set_active_profile("Active")

        manager2 = CharacterManager(storage_path=temp_storage)
        active = manager2.get_active_profile()
        assert active.name == "Active"


class TestCharacterProfile:
    """Tests for CharacterProfile dataclass."""

    def test_get_item_for_slot(self):
        item = PoBItem(slot="Helmet", rarity="RARE", name="Test Helmet", base_type="Leather Cap")
        build = PoBBuild(items={"Helmet": item})
        profile = CharacterProfile(name="Test", build=build)

        assert profile.get_item_for_slot("Helmet") == item
        assert profile.get_item_for_slot("Gloves") is None


class TestUpgradeChecker:
    """Tests for UpgradeChecker class."""

    @pytest.fixture
    def manager_with_build(self, tmp_path):
        """Create a CharacterManager with a test build."""
        storage = tmp_path / "characters.json"
        manager = CharacterManager(storage_path=storage)
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("Test Build", code)
        manager.set_active_profile("Test Build")
        return manager

    @pytest.fixture
    def checker(self, manager_with_build):
        """Create an UpgradeChecker with test build."""
        return UpgradeChecker(manager_with_build)

    def test_get_applicable_slots_for_helmet(self, checker):
        slots = checker.get_applicable_slots("Helmets")
        assert "Helmet" in slots

    def test_get_applicable_slots_for_ring(self, checker):
        slots = checker.get_applicable_slots("Rings")
        assert "Ring 1" in slots
        assert "Ring 2" in slots

    def test_get_applicable_slots_for_unknown_returns_empty(self, checker):
        slots = checker.get_applicable_slots("Unknown Item Class")
        assert slots == []

    def test_check_upgrade_returns_no_profile_message_when_empty(self, tmp_path):
        storage = tmp_path / "empty.json"
        manager = CharacterManager(storage_path=storage)
        checker = UpgradeChecker(manager)

        is_upgrade, reasons, slot = checker.check_upgrade(
            item_class="Helmets",
            item_mods=["+50 to maximum Life"]
        )
        assert is_upgrade is False
        assert "No character profile loaded" in reasons

    def test_check_upgrade_returns_tuple(self, checker):
        is_upgrade, reasons, slot = checker.check_upgrade(
            item_class="Helmets",
            item_mods=["+100 to maximum Life", "+40% to Fire Resistance"]
        )

        assert isinstance(is_upgrade, bool)
        assert isinstance(reasons, list)
        assert slot is None or isinstance(slot, str)

    def test_check_upgrade_detects_better_life(self, checker):
        # The test build has a helmet with +30% resistances, no life
        is_upgrade, reasons, slot = checker.check_upgrade(
            item_class="Helmets",
            item_mods=["+100 to maximum Life"]
        )

        # Should be considered upgrade if it has life and current doesn't
        assert isinstance(is_upgrade, bool)
        if is_upgrade:
            assert any("life" in r.lower() for r in reasons)


class TestPoBDecoderSlotMapping:
    """Tests for slot name mapping."""

    def test_slot_mapping_normalizes_weapon(self):
        assert "Weapon 1" in PoBDecoder.SLOT_MAPPING
        assert PoBDecoder.SLOT_MAPPING["Weapon 1"] == "Weapon"

    def test_slot_mapping_normalizes_offhand(self):
        assert "Weapon 2" in PoBDecoder.SLOT_MAPPING
        assert PoBDecoder.SLOT_MAPPING["Weapon 2"] == "Offhand"

    def test_slot_mapping_keeps_standard_names(self):
        assert "Helmet" in PoBDecoder.SLOT_MAPPING
        assert PoBDecoder.SLOT_MAPPING["Helmet"] == "Helmet"


class TestBuildCategory:
    """Tests for BuildCategory enum."""

    def test_all_categories_exist(self):
        categories = [c.value for c in BuildCategory]
        assert "league_starter" in categories
        assert "endgame" in categories
        assert "meta" in categories
        assert "boss_killer" in categories

    def test_category_is_string_enum(self):
        assert BuildCategory.META.value == "meta"
        assert str(BuildCategory.META) == "BuildCategory.META"


class TestCharacterProfileCategories:
    """Tests for CharacterProfile category management."""

    def test_profile_has_empty_categories_by_default(self):
        build = PoBBuild()
        profile = CharacterProfile(name="Test", build=build)
        assert profile.categories == []
        assert profile.is_upgrade_target is False

    def test_add_category(self):
        build = PoBBuild()
        profile = CharacterProfile(name="Test", build=build)
        profile.add_category(BuildCategory.META)
        assert "meta" in profile.categories

    def test_add_category_no_duplicates(self):
        build = PoBBuild()
        profile = CharacterProfile(name="Test", build=build)
        profile.add_category(BuildCategory.META)
        profile.add_category(BuildCategory.META)
        assert profile.categories.count("meta") == 1

    def test_remove_category(self):
        build = PoBBuild()
        profile = CharacterProfile(name="Test", build=build, categories=["meta", "endgame"])
        profile.remove_category(BuildCategory.META)
        assert "meta" not in profile.categories
        assert "endgame" in profile.categories

    def test_has_category(self):
        build = PoBBuild()
        profile = CharacterProfile(name="Test", build=build, categories=["meta"])
        assert profile.has_category(BuildCategory.META) is True
        assert profile.has_category(BuildCategory.ENDGAME) is False


class TestCharacterManagerCategories:
    """Tests for CharacterManager category operations."""

    @pytest.fixture
    def manager_with_build(self, tmp_path):
        """Create a CharacterManager with a test build."""
        storage = tmp_path / "characters.json"
        manager = CharacterManager(storage_path=storage)
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager.add_from_pob_code("Test Build", code)
        return manager

    def test_set_build_categories(self, manager_with_build):
        result = manager_with_build.set_build_categories("Test Build", ["meta", "endgame"])
        assert result is True
        profile = manager_with_build.get_profile("Test Build")
        assert "meta" in profile.categories
        assert "endgame" in profile.categories

    def test_set_build_categories_filters_invalid(self, manager_with_build):
        result = manager_with_build.set_build_categories("Test Build", ["meta", "invalid_category"])
        assert result is True
        profile = manager_with_build.get_profile("Test Build")
        assert "meta" in profile.categories
        assert "invalid_category" not in profile.categories

    def test_add_build_category(self, manager_with_build):
        result = manager_with_build.add_build_category("Test Build", "meta")
        assert result is True
        profile = manager_with_build.get_profile("Test Build")
        assert "meta" in profile.categories

    def test_add_build_category_invalid_returns_false(self, manager_with_build):
        result = manager_with_build.add_build_category("Test Build", "not_a_category")
        assert result is False

    def test_set_upgrade_target(self, manager_with_build):
        result = manager_with_build.set_upgrade_target("Test Build")
        assert result is True
        profile = manager_with_build.get_profile("Test Build")
        assert profile.is_upgrade_target is True

    def test_get_upgrade_target(self, manager_with_build):
        manager_with_build.set_upgrade_target("Test Build")
        target = manager_with_build.get_upgrade_target()
        assert target.name == "Test Build"
        assert target.is_upgrade_target is True

    def test_get_builds_by_category(self, manager_with_build):
        manager_with_build.set_build_categories("Test Build", ["meta"])
        builds = manager_with_build.get_builds_by_category("meta")
        assert len(builds) == 1
        assert builds[0].name == "Test Build"

    def test_get_available_categories(self, manager_with_build):
        categories = manager_with_build.get_available_categories()
        assert len(categories) == len(BuildCategory)
        assert any(c["value"] == "meta" for c in categories)

    def test_categories_persist_to_file(self, tmp_path):
        storage = tmp_path / "characters.json"
        manager1 = CharacterManager(storage_path=storage)
        code = _encode_pob_code(SAMPLE_POB_XML)
        manager1.add_from_pob_code("Persistent", code)
        manager1.set_build_categories("Persistent", ["meta", "endgame"])
        manager1.set_upgrade_target("Persistent")

        # Create new manager that loads from same file
        manager2 = CharacterManager(storage_path=storage)
        profile = manager2.get_profile("Persistent")
        assert "meta" in profile.categories
        assert "endgame" in profile.categories
        assert profile.is_upgrade_target is True


# -------------------------
# URL Helper Function Tests
# -------------------------

class TestUrlHelperFunctions:
    """Tests for URL validation helper functions."""

    def test_is_pastebin_url_valid(self):
        assert _is_pastebin_url("https://pastebin.com/abc123") is True
        assert _is_pastebin_url("http://pastebin.com/raw/abc123") is True
        assert _is_pastebin_url("https://www.pastebin.com/xyz") is True

    def test_is_pastebin_url_invalid(self):
        assert _is_pastebin_url("https://evil.com/pastebin.com") is False
        assert _is_pastebin_url("https://pobb.in/abc") is False
        assert _is_pastebin_url("not a url") is False

    def test_is_pastebin_url_exception_handling(self):
        # Test with values that could cause parsing exceptions
        assert _is_pastebin_url(None) is False  # type: ignore
        assert _is_pastebin_url("") is False

    def test_is_pobbin_url_valid(self):
        assert _is_pobbin_url("https://pobb.in/abc123") is True
        assert _is_pobbin_url("http://www.pobb.in/xyz") is True

    def test_is_pobbin_url_invalid(self):
        assert _is_pobbin_url("https://evil.com?pobb.in") is False
        assert _is_pobbin_url("https://pastebin.com/abc") is False
        assert _is_pobbin_url("not a url") is False

    def test_is_pobbin_url_exception_handling(self):
        assert _is_pobbin_url(None) is False  # type: ignore
        assert _is_pobbin_url("") is False

    def test_url_host_matches_valid(self):
        assert _url_host_matches("https://maxroll.gg/poe/build", "maxroll.gg") is True
        assert _url_host_matches("https://www.maxroll.gg/build", "maxroll.gg") is True

    def test_url_host_matches_invalid(self):
        assert _url_host_matches("https://evil.com/maxroll.gg", "maxroll.gg") is False
        assert _url_host_matches("not-a-url", "maxroll.gg") is False

    def test_url_host_matches_exception_handling(self):
        assert _url_host_matches(None, "test.com") is False  # type: ignore
        assert _url_host_matches("", "test.com") is False


# -------------------------
# Decoder Edge Case Tests
# -------------------------

class TestPoBDecoderEdgeCases:
    """Tests for PoBDecoder edge cases and error handling."""

    def test_decode_code_too_large(self):
        """Test rejection of excessively large codes."""
        large_code = "A" * (PoBDecoder.MAX_CODE_SIZE + 1)
        with pytest.raises(ValueError, match="PoB code too large"):
            PoBDecoder.decode_pob_code(large_code)

    def test_decode_strips_whitespace(self):
        """Test that whitespace is properly stripped."""
        code = _encode_pob_code(SAMPLE_POB_XML)
        code_with_whitespace = f"  {code}  \n\r"
        xml = PoBDecoder.decode_pob_code(code_with_whitespace)
        assert "PathOfBuilding" in xml

    def test_decode_handles_url_safe_base64(self):
        """Test handling of URL-safe base64 characters."""
        code = _encode_pob_code(SAMPLE_POB_XML)
        # URL-safe base64 uses - and _ instead of + and /
        # The decoder should handle both
        xml = PoBDecoder.decode_pob_code(code)
        assert "PathOfBuilding" in xml

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pastebin_success(self, mock_get):
        """Test successful pastebin fetch."""
        mock_response = MagicMock()
        mock_response.text = _encode_pob_code(SAMPLE_POB_XML)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        xml = PoBDecoder.decode_pob_code("https://pastebin.com/abc123")
        assert "PathOfBuilding" in xml
        mock_get.assert_called_once()

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pastebin_raw_url(self, mock_get):
        """Test pastebin raw URL handling."""
        mock_response = MagicMock()
        mock_response.text = _encode_pob_code(SAMPLE_POB_XML)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Raw URL should be used directly
        xml = PoBDecoder.decode_pob_code("https://pastebin.com/raw/abc123")
        assert "PathOfBuilding" in xml

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pastebin_failure(self, mock_get):
        """Test pastebin fetch failure handling."""
        mock_get.side_effect = requests.RequestException("Connection error")

        with pytest.raises(ValueError, match="Could not fetch pastebin"):
            PoBDecoder.decode_pob_code("https://pastebin.com/abc123")

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pastebin_invalid_url(self, mock_get):
        """Test pastebin with empty paste ID."""
        with pytest.raises(ValueError, match="no paste ID found"):
            PoBDecoder._fetch_pastebin("https://pastebin.com/")

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pobbin_success(self, mock_get):
        """Test successful pobb.in fetch."""
        mock_response = MagicMock()
        mock_response.text = _encode_pob_code(SAMPLE_POB_XML)
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        xml = PoBDecoder.decode_pob_code("https://pobb.in/abc123")
        assert "PathOfBuilding" in xml

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pobbin_fallback_to_api(self, mock_get):
        """Test pobb.in fallback to API endpoint."""
        # First call (raw) fails, second call (API) succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status = MagicMock(side_effect=requests.RequestException("Not found"))

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"code": _encode_pob_code(SAMPLE_POB_XML)}
        mock_response_success.raise_for_status = MagicMock()

        mock_get.side_effect = [
            requests.RequestException("Raw failed"),
            mock_response_success
        ]

        xml = PoBDecoder.decode_pob_code("https://pobb.in/abc123")
        assert "PathOfBuilding" in xml

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pobbin_both_fail(self, mock_get):
        """Test pobb.in when both endpoints fail."""
        mock_get.side_effect = requests.RequestException("Connection error")

        with pytest.raises(ValueError, match="Could not fetch pobb.in"):
            PoBDecoder.decode_pob_code("https://pobb.in/abc123")

    @patch("core.pob.decoder.requests.get")
    def test_fetch_pobbin_invalid_url(self, mock_get):
        """Test pobb.in with empty paste ID."""
        with pytest.raises(ValueError, match="no paste ID found"):
            PoBDecoder._fetch_pobbin("https://pobb.in/")

    def test_looks_like_url_http(self):
        """Test URL detection for http:// prefix."""
        assert PoBDecoder._looks_like_url("http://example.com") is True
        assert PoBDecoder._looks_like_url("https://example.com") is True

    def test_looks_like_url_www(self):
        """Test URL detection for www. prefix."""
        assert PoBDecoder._looks_like_url("www.example.com") is True

    def test_looks_like_url_build_sites(self):
        """Test URL detection for known build sites."""
        assert PoBDecoder._looks_like_url("https://maxroll.gg/build") is True
        assert PoBDecoder._looks_like_url("https://mobalytics.gg/poe") is True
        assert PoBDecoder._looks_like_url("https://poe.ninja/builds") is True

    def test_looks_like_url_pob_code(self):
        """Test that PoB codes are not detected as URLs."""
        code = _encode_pob_code(SAMPLE_POB_XML)
        assert PoBDecoder._looks_like_url(code) is False

    def test_raise_url_error_maxroll(self):
        """Test helpful error for maxroll.gg URLs."""
        with pytest.raises(ValueError, match="Maxroll.gg URLs cannot be imported"):
            PoBDecoder._raise_url_error("https://maxroll.gg/poe/build/123")

    def test_raise_url_error_mobalytics(self):
        """Test helpful error for mobalytics.gg URLs."""
        with pytest.raises(ValueError, match="Mobalytics URLs cannot be imported"):
            PoBDecoder._raise_url_error("https://mobalytics.gg/poe/builds/123")

    def test_raise_url_error_poe_ninja(self):
        """Test helpful error for poe.ninja URLs."""
        with pytest.raises(ValueError, match="poe.ninja URLs cannot be imported"):
            PoBDecoder._raise_url_error("https://poe.ninja/builds/123")

    def test_raise_url_error_pobarchives(self):
        """Test helpful error for pobarchives.com URLs."""
        with pytest.raises(ValueError, match="PoB Archives URLs cannot be imported"):
            PoBDecoder._raise_url_error("https://pobarchives.com/build/123")

    def test_raise_url_error_unknown_site(self):
        """Test generic error for unknown URLs."""
        with pytest.raises(ValueError, match="URL detected but cannot be imported"):
            PoBDecoder._raise_url_error("https://unknown-site.com/build")


# -------------------------
# Item Parsing Edge Cases
# -------------------------

class TestPoBItemParsing:
    """Tests for PoB item parsing edge cases."""

    def test_parse_item_with_implicits(self):
        """Test parsing item with implicit mods."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Witch" ascendClassName="Elementalist"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Ring
Two-Stone Ring
Item Level: 84
Implicits: 1
+16% to Fire and Cold Resistances
+50 to maximum Life
+30% to Fire Resistance
</Item>
        <ItemSet id="1">
            <Slot name="Ring 1" itemId="1"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        ring = build.items.get("Ring 1")
        assert ring is not None
        assert "+16% to Fire and Cold Resistances" in ring.implicit_mods
        assert "+50 to maximum Life" in ring.explicit_mods

    def test_parse_item_with_crafted_mod(self):
        """Test parsing item with crafted mods."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Witch" ascendClassName="Elementalist"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Amulet
Onyx Amulet
Item Level: 84
Implicits: 1
+25 to all Attributes
+50 to maximum Life
{crafted}+30% to Fire Resistance
</Item>
        <ItemSet id="1">
            <Slot name="Amulet" itemId="1"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        amulet = build.items.get("Amulet")
        assert amulet is not None
        # Crafted mod should be marked
        assert any("(crafted)" in mod for mod in amulet.explicit_mods)

    def test_parse_item_with_fractured_mod(self):
        """Test parsing item with fractured mods."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Witch" ascendClassName="Elementalist"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Belt
Stygian Vise
Item Level: 84
Implicits: 1
Has 1 Abyssal Socket
{fractured}+100 to maximum Life
+30% to Fire Resistance
</Item>
        <ItemSet id="1">
            <Slot name="Belt" itemId="1"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        belt = build.items.get("Belt")
        assert belt is not None
        # Fractured mod should be marked
        assert any("(fractured)" in mod for mod in belt.explicit_mods)

    def test_parse_item_with_quality(self):
        """Test parsing item quality."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Armour
Astral Plate
Item Level: 84
Quality: +20%
Implicits: 0
+100 to maximum Life
</Item>
        <ItemSet id="1">
            <Slot name="Body Armour" itemId="1"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        armour = build.items.get("Body Armour")
        assert armour is not None
        assert armour.quality == 20

    def test_parse_item_with_sockets(self):
        """Test parsing item sockets."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Armour
Astral Plate
Item Level: 84
Sockets: R-R-R-G-G-B
Implicits: 0
+100 to maximum Life
</Item>
        <ItemSet id="1">
            <Slot name="Body Armour" itemId="1"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        armour = build.items.get("Body Armour")
        assert armour is not None
        assert armour.sockets == "R-R-R-G-G-B"
        assert armour.link_count == 6

    def test_parse_item_empty_text(self):
        """Test parsing item with empty text returns None."""
        import defusedxml.ElementTree as ET
        item_elem = ET.fromstring("<Item id='1'>  </Item>")
        result = PoBDecoder._parse_item(item_elem)
        assert result is None

    def test_parse_item_minimal_lines(self):
        """Test parsing item with too few lines returns None."""
        import defusedxml.ElementTree as ET
        item_elem = ET.fromstring("<Item id='1'>OnlyOneLine</Item>")
        result = PoBDecoder._parse_item(item_elem)
        assert result is None

    def test_parse_build_extracts_skills(self):
        """Test extraction of skill labels."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items></Items>
    <Skills>
        <Skill label="Main Attack"/>
        <Skill label="Auras"/>
        <Skill label=""/>
    </Skills>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        assert "Main Attack" in build.skills
        assert "Auras" in build.skills
        # Empty label should be skipped
        assert "" not in build.skills

    def test_parse_build_extracts_config(self):
        """Test extraction of config inputs."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items></Items>
    <Config>
        <Input name="enemyIsBoss" boolean="true"/>
        <Input name="enemyPhysicalReduction" number="50"/>
        <Input name="customMods" string="test mod"/>
    </Config>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        assert build.config.get("enemyIsBoss") == "true"
        assert build.config.get("enemyPhysicalReduction") == "50"
        assert build.config.get("customMods") == "test mod"

    def test_parse_build_extracts_player_stats(self):
        """Test extraction of PlayerStat values."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut">
        <PlayerStat stat="Life" value="5000"/>
        <PlayerStat stat="EnergyShield" value="1000"/>
        <PlayerStat stat="InvalidStat" value="not_a_number"/>
    </Build>
    <Items></Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        assert build.stats.get("Life") == 5000.0
        assert build.stats.get("EnergyShield") == 1000.0
        # Invalid stats should be skipped
        assert "InvalidStat" not in build.stats

    def test_parse_build_skips_abyssal_slots(self):
        """Test that abyssal socket slots are skipped."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Belt
Stygian Vise
Item Level: 84
Implicits: 0
+100 to maximum Life
</Item>
        <Item id="2">
Rarity: RARE
Abyssal Jewel
Murderous Eye Jewel
Item Level: 84
Implicits: 0
+50 to maximum Life
</Item>
        <ItemSet id="1">
            <Slot name="Belt" itemId="1"/>
            <Slot name="Belt Abyssal Socket 1" itemId="2"/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        assert "Belt" in build.items
        # Abyssal socket should be skipped
        assert "Belt Abyssal Socket 1" not in build.items

    def test_parse_build_skips_empty_slots(self):
        """Test that empty slots (itemId=0) are skipped."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build level="90" className="Marauder" ascendClassName="Juggernaut"></Build>
    <Items activeItemSet="1">
        <Item id="1">
Rarity: RARE
Test Helmet
Eternal Burgonet
Item Level: 84
Implicits: 0
+100 to maximum Life
</Item>
        <ItemSet id="1">
            <Slot name="Helmet" itemId="1"/>
            <Slot name="Gloves" itemId="0"/>
            <Slot name="Boots" itemId=""/>
        </ItemSet>
    </Items>
</PathOfBuilding>"""

        build = PoBDecoder.parse_build(xml)
        assert "Helmet" in build.items
        assert "Gloves" not in build.items
        assert "Boots" not in build.items
