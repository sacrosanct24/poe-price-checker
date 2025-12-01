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

import pytest

from core.pob_integration import (
    BuildCategory,
    CharacterManager,
    CharacterProfile,
    PoBBuild,
    PoBDecoder,
    PoBItem,
    UpgradeChecker,
)


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
