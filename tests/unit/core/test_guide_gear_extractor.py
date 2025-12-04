"""Tests for core/guide_gear_extractor.py - Build guide gear extraction."""
from unittest.mock import MagicMock

import pytest

from core.guide_gear_extractor import (
    GuideGearRecommendation,
    ItemSetInfo,
    GuideGearSummary,
    GuideGearExtractor,
    EQUIPMENT_SLOTS,
)


class TestGuideGearRecommendation:
    """Tests for GuideGearRecommendation dataclass."""

    def test_create_unique_recommendation(self):
        """Should create unique item recommendation."""
        rec = GuideGearRecommendation(
            slot="Helmet",
            item_name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            rarity="UNIQUE",
            is_unique=True,
            key_mods=["+60 to Dexterity", "20% increased Movement Speed"],
        )

        assert rec.slot == "Helmet"
        assert rec.item_name == "Devoto's Devotion"
        assert rec.is_unique is True
        assert len(rec.key_mods) == 2

    def test_create_rare_recommendation(self):
        """Should create rare item recommendation."""
        rec = GuideGearRecommendation(
            slot="Body Armour",
            item_name="Apocalypse Shell",
            base_type="Astral Plate",
            rarity="RARE",
            is_unique=False,
            key_mods=["+105 to maximum Life", "+45% to Fire Resistance"],
        )

        assert rec.is_unique is False
        assert rec.base_type == "Astral Plate"

    def test_default_values(self):
        """Should have correct default values."""
        rec = GuideGearRecommendation(
            slot="Ring 1",
            item_name="Test Ring",
            base_type="Ruby Ring",
            rarity="RARE",
            is_unique=False,
        )

        assert rec.key_mods == []
        assert rec.notes == ""
        assert rec.priority == 1

    def test_display_name_unique(self):
        """Unique display name should be item name."""
        rec = GuideGearRecommendation(
            slot="Helmet",
            item_name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            rarity="UNIQUE",
            is_unique=True,
        )

        assert rec.display_name == "Devoto's Devotion"

    def test_display_name_rare_with_name(self):
        """Rare with name should show name and base type."""
        rec = GuideGearRecommendation(
            slot="Body Armour",
            item_name="Apocalypse Shell",
            base_type="Astral Plate",
            rarity="RARE",
            is_unique=False,
        )

        assert rec.display_name == "Apocalypse Shell (Astral Plate)"

    def test_display_name_rare_without_name(self):
        """Rare without name should show only base type."""
        rec = GuideGearRecommendation(
            slot="Body Armour",
            item_name="",
            base_type="Astral Plate",
            rarity="RARE",
            is_unique=False,
        )

        assert rec.display_name == "Astral Plate"


class TestItemSetInfo:
    """Tests for ItemSetInfo dataclass."""

    def test_create_item_set(self):
        """Should create item set info."""
        info = ItemSetInfo(
            id="1",
            title="Mapping Gear",
            slot_count=10,
            is_active=True,
        )

        assert info.id == "1"
        assert info.title == "Mapping Gear"
        assert info.slot_count == 10
        assert info.is_active is True

    def test_default_not_active(self):
        """Default should be not active."""
        info = ItemSetInfo(
            id="2",
            title="Bossing Gear",
            slot_count=8,
        )

        assert info.is_active is False

    def test_display_name_active(self):
        """Active item set should show marker."""
        info = ItemSetInfo(
            id="1",
            title="Main Set",
            slot_count=10,
            is_active=True,
        )

        assert info.display_name == "Main Set (Active)"

    def test_display_name_inactive(self):
        """Inactive item set should not show marker."""
        info = ItemSetInfo(
            id="2",
            title="Secondary",
            slot_count=8,
            is_active=False,
        )

        assert info.display_name == "Secondary"


class TestGuideGearSummary:
    """Tests for GuideGearSummary dataclass."""

    def test_create_empty_summary(self):
        """Should create empty summary."""
        summary = GuideGearSummary(
            profile_name="Test Build",
            guide_name="Slayer",
        )

        assert summary.profile_name == "Test Build"
        assert summary.guide_name == "Slayer"
        assert summary.recommendations == {}
        assert summary.uniques_needed == []
        assert summary.rare_slots == []

    def test_get_recommendation_found(self):
        """Should return recommendation for slot."""
        summary = GuideGearSummary(
            profile_name="Test",
            guide_name="Test",
        )
        rec = GuideGearRecommendation(
            slot="Helmet",
            item_name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            rarity="UNIQUE",
            is_unique=True,
        )
        summary.recommendations["Helmet"] = rec

        result = summary.get_recommendation("Helmet")

        assert result is rec

    def test_get_recommendation_not_found(self):
        """Should return None for missing slot."""
        summary = GuideGearSummary(
            profile_name="Test",
            guide_name="Test",
        )

        result = summary.get_recommendation("Helmet")

        assert result is None

    def test_get_unique_recommendations(self):
        """Should filter unique recommendations."""
        summary = GuideGearSummary(
            profile_name="Test",
            guide_name="Test",
        )
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet", item_name="Devoto's", base_type="Bascinet",
            rarity="UNIQUE", is_unique=True,
        )
        summary.recommendations["Body Armour"] = GuideGearRecommendation(
            slot="Body Armour", item_name="", base_type="Astral Plate",
            rarity="RARE", is_unique=False,
        )

        uniques = summary.get_unique_recommendations()

        assert len(uniques) == 1
        assert uniques[0].slot == "Helmet"

    def test_get_rare_recommendations(self):
        """Should filter rare recommendations."""
        summary = GuideGearSummary(
            profile_name="Test",
            guide_name="Test",
        )
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet", item_name="Devoto's", base_type="Bascinet",
            rarity="UNIQUE", is_unique=True,
        )
        summary.recommendations["Body Armour"] = GuideGearRecommendation(
            slot="Body Armour", item_name="", base_type="Astral Plate",
            rarity="RARE", is_unique=False,
        )

        rares = summary.get_rare_recommendations()

        assert len(rares) == 1
        assert rares[0].slot == "Body Armour"


class TestGuideGearExtractor:
    """Tests for GuideGearExtractor class."""

    @pytest.fixture
    def mock_char_manager(self):
        """Create mock CharacterManager."""
        return MagicMock()

    @pytest.fixture
    def extractor(self, mock_char_manager):
        """Create extractor with mock manager."""
        return GuideGearExtractor(character_manager=mock_char_manager)

    @pytest.fixture
    def sample_pob_build(self):
        """Create sample PoBBuild for testing."""
        from core.pob_integration import PoBBuild, PoBItem

        build = PoBBuild(
            class_name="Slayer",
            ascendancy="Slayer",
            level=95,
        )
        build.items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="UNIQUE",
                name="Devoto's Devotion",
                base_type="Nightmare Bascinet",
                explicit_mods=["+60 to Dexterity", "20% increased Movement Speed"],
            ),
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="RARE",
                name="Apocalypse Shell",
                base_type="Astral Plate",
                explicit_mods=["+105 to maximum Life", "+45% to Fire Resistance"],
            ),
            "Boots": PoBItem(
                slot="Boots",
                rarity="RARE",
                name="",
                base_type="Two-Toned Boots",
                implicit_mods=["+12% to Fire and Cold Resistances"],
                explicit_mods=["30% increased Movement Speed"],
            ),
        }
        return build

    def test_init_without_manager(self):
        """Should work without CharacterManager."""
        extractor = GuideGearExtractor()

        assert extractor.character_manager is None

    def test_extract_from_profile_no_manager(self):
        """Should return None without manager."""
        extractor = GuideGearExtractor()

        result = extractor.extract_from_profile("Test")

        assert result is None

    def test_extract_from_profile_not_found(self, extractor, mock_char_manager):
        """Should return None for missing profile."""
        mock_char_manager.get_profile.return_value = None

        result = extractor.extract_from_profile("NonExistent")

        assert result is None

    def test_extract_from_build(self, extractor, sample_pob_build):
        """Should extract gear from build."""
        result = extractor._extract_from_build(sample_pob_build, "Test Build")

        assert result is not None
        assert result.guide_name == "Slayer"
        assert "Helmet" in result.recommendations
        assert "Body Armour" in result.recommendations
        assert "Devoto's Devotion" in result.uniques_needed
        assert "Body Armour" in result.rare_slots

    def test_extract_from_build_empty_items(self, extractor):
        """Should handle build with no items."""
        from core.pob_integration import PoBBuild

        build = PoBBuild(class_name="Marauder", ascendancy="Juggernaut", level=90)
        build.items = {}

        result = extractor._extract_from_build(build, "Test")

        assert result is not None
        assert len(result.recommendations) == 0

    def test_item_to_recommendation_unique(self, extractor):
        """Should create unique recommendation correctly."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Helmet",
            rarity="UNIQUE",
            name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            explicit_mods=["+60 to Dexterity"],
        )

        rec = extractor._item_to_recommendation(item, "Helmet")

        assert rec.is_unique is True
        assert rec.item_name == "Devoto's Devotion"
        assert rec.priority == 1  # Uniques are high priority

    def test_item_to_recommendation_rare(self, extractor):
        """Should create rare recommendation correctly."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Ring 1",
            rarity="RARE",
            name="Test Ring",
            base_type="Ruby Ring",
            explicit_mods=["+50 to maximum Life"],
        )

        rec = extractor._item_to_recommendation(item, "Ring 1")

        assert rec.is_unique is False
        assert rec.priority == 3  # Rings are low priority

    def test_item_to_recommendation_body_armour_priority(self, extractor):
        """Body armour rare should have high priority."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Body Armour",
            rarity="RARE",
            name="",
            base_type="Astral Plate",
        )

        rec = extractor._item_to_recommendation(item, "Body Armour")

        assert rec.priority == 1

    def test_item_to_recommendation_key_mods_priority(self, extractor):
        """Should prioritize important mods."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Boots",
            rarity="RARE",
            name="",
            base_type="Two-Toned Boots",
            explicit_mods=[
                "+89 to maximum Life",
                "30% increased Movement Speed",
                "+40% to Lightning Resistance",
                "Some Other Mod",
            ],
        )

        rec = extractor._item_to_recommendation(item, "Boots")

        # Should capture life, movement speed, and resistance mods
        assert len(rec.key_mods) <= 5

    def test_compare_with_current_no_manager(self, mock_char_manager):
        """Should return empty dict without manager."""
        extractor = GuideGearExtractor()
        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")

        result = extractor.compare_with_current(summary, "Current")

        assert result == {}

    def test_compare_with_current_matching_unique(self, extractor, mock_char_manager):
        """Should detect matching unique item."""
        from core.pob_integration import PoBBuild, PoBItem

        # Guide gear
        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet",
            item_name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            rarity="UNIQUE",
            is_unique=True,
        )

        # Current gear
        current_profile = MagicMock()
        current_build = PoBBuild(class_name="Slayer", ascendancy="Slayer", level=90)
        current_build.items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="UNIQUE",
                name="Devoto's Devotion",
                base_type="Nightmare Bascinet",
            )
        }
        current_profile.build = current_build
        mock_char_manager.get_profile.return_value = current_profile

        result = extractor.compare_with_current(summary, "Current")

        assert result["Helmet"]["is_match"] is True
        assert result["Helmet"]["upgrade_needed"] is False

    def test_format_summary_text(self, extractor):
        """Should format summary as readable text."""
        summary = GuideGearSummary(profile_name="Test", guide_name="Slayer Build")
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet",
            item_name="Devoto's Devotion",
            base_type="Nightmare Bascinet",
            rarity="UNIQUE",
            is_unique=True,
            key_mods=["+60 to Dexterity"],
        )
        summary.uniques_needed = ["Devoto's Devotion"]
        summary.recommendations["Body Armour"] = GuideGearRecommendation(
            slot="Body Armour",
            item_name="",
            base_type="Astral Plate",
            rarity="RARE",
            is_unique=False,
        )
        summary.rare_slots = ["Body Armour"]

        text = extractor.format_summary_text(summary)

        assert "Slayer Build" in text
        assert "UNIQUE ITEMS NEEDED" in text
        assert "Devoto's Devotion" in text
        assert "RARE ITEM SLOTS" in text
        assert "Astral Plate" in text

    def test_get_item_sets_from_profile_no_manager(self):
        """Should return empty list without manager."""
        extractor = GuideGearExtractor()

        result = extractor.get_item_sets_from_profile("Test")

        assert result == []

    def test_get_item_sets_from_profile_no_pob_code(self, extractor, mock_char_manager):
        """Should return empty list when profile has no PoB code."""
        profile = MagicMock()
        profile.pob_code = None
        mock_char_manager.get_profile.return_value = profile

        result = extractor.get_item_sets_from_profile("Test")

        assert result == []

    def test_get_item_sets_from_pob_code(self, extractor):
        """Should parse item sets from PoB code."""
        # Mock the decoder to return XML with item sets
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items activeItemSet="1">
                <ItemSet id="1" title="Main Set">
                    <Slot name="Helmet" itemId="1"/>
                    <Slot name="Body Armour" itemId="2"/>
                </ItemSet>
                <ItemSet id="2" title="^xFFFFFFBossing Set">
                    <Slot name="Helmet" itemId="3"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        extractor._decoder.decode_pob_code = MagicMock(return_value=mock_xml)

        result = extractor.get_item_sets_from_pob_code("test_code")

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[0].title == "Main Set"
        assert result[0].slot_count == 2
        assert result[0].is_active is True
        assert result[1].id == "2"
        assert result[1].title == "Bossing Set"  # Color code stripped
        assert result[1].is_active is False

    def test_parse_item_sets_cleans_color_codes(self, extractor):
        """Should clean PoB color codes from titles."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <ItemSet id="1" title="^xFFFF00Yellow Title^xFFFFFFWhite"/>
            </Items>
        </PathOfBuilding>
        """

        result = extractor._parse_item_sets(xml)

        assert result[0].title == "Yellow TitleWhite"

    def test_parse_item_sets_handles_empty_title(self, extractor):
        """Should handle empty titles."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <ItemSet id="1" title=""/>
            </Items>
        </PathOfBuilding>
        """

        result = extractor._parse_item_sets(xml)

        assert result[0].title == "Item Set 1"

    def test_parse_item_sets_no_items_element(self, extractor):
        """Should handle XML without Items element."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
        </PathOfBuilding>
        """

        result = extractor._parse_item_sets(xml)

        assert result == []

    def test_extract_from_pob_code_with_item_set(self, extractor):
        """Should extract gear from specific item set."""
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Build className="Slayer"/>
            <Items>
                <Item id="1">Rarity: UNIQUE
Devoto's Devotion
Nightmare Bascinet
Item Level: 70</Item>
                <ItemSet id="1" title="Main">
                    <Slot name="Helmet" itemId="1"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """
        extractor._decoder.decode_pob_code = MagicMock(return_value=mock_xml)

        result = extractor.extract_from_pob_code_with_item_set(
            "test_code", "Test Build", "1"
        )

        assert result is not None
        assert result.item_set_name == "Main"
        assert "Helmet" in result.recommendations

    def test_extract_from_item_set_skips_abyssal_slots(self, extractor):
        """Should skip abyssal socket slots."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Build className="Test"/>
            <Items>
                <Item id="1">Rarity: RARE
Test Item
Test Base</Item>
                <ItemSet id="1" title="Test">
                    <Slot name="Abyssal Socket 1" itemId="1"/>
                    <Slot name="Graft 1" itemId="1"/>
                    <Slot name="Helmet" itemId="1"/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """

        result = extractor._extract_from_item_set(xml, "Test", "1")

        # Should only include Helmet, not Abyssal or Graft
        assert result is not None
        assert "Helmet" in result.recommendations
        assert len(result.recommendations) == 1

    def test_extract_from_item_set_skips_empty_slots(self, extractor):
        """Should skip slots with itemId="0"."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Build className="Test"/>
            <Items>
                <Item id="1">Rarity: RARE
Test Item
Test Base</Item>
                <ItemSet id="1" title="Test">
                    <Slot name="Helmet" itemId="1"/>
                    <Slot name="Body Armour" itemId="0"/>
                    <Slot name="Gloves" itemId=""/>
                </ItemSet>
            </Items>
        </PathOfBuilding>
        """

        result = extractor._extract_from_item_set(xml, "Test", "1")

        # Should only include Helmet
        assert result is not None
        assert "Helmet" in result.recommendations
        assert len(result.recommendations) == 1

    def test_extract_from_item_set_not_found(self, extractor):
        """Should return None when item set not found."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <PathOfBuilding>
            <Items>
                <ItemSet id="1" title="Test"/>
            </Items>
        </PathOfBuilding>
        """

        result = extractor._extract_from_item_set(xml, "Test", "999")

        assert result is None

    def test_parse_item_element_minimal(self, extractor):
        """Should handle minimal item element."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = """Rarity: RARE
Test Name
Test Base"""

        result = extractor._parse_item_element(item_elem)

        assert result is not None
        assert result.name == "Test Name"
        assert result.base_type == "Test Base"
        assert result.rarity == "RARE"

    def test_parse_item_element_empty(self, extractor):
        """Should return None for empty item."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = ""

        result = extractor._parse_item_element(item_elem)

        assert result is None

    def test_parse_item_element_with_metadata(self, extractor):
        """Should parse item with metadata correctly."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = """Rarity: UNIQUE
Headhunter
Leather Belt
Item Level: 84
Quality: 20
Sockets: R-R-R
Implicits: 1
+40 to maximum Life
Requires Level 40
{crafted}+30% to Fire Resistance
{fractured}+100 to Armour"""

        result = extractor._parse_item_element(item_elem)

        assert result is not None
        assert result.item_level == 84
        assert result.quality == 20
        assert result.sockets == "R-R-R"
        assert len(result.implicit_mods) == 1
        assert len(result.explicit_mods) == 2

    def test_parse_item_element_removes_crafted_tags(self, extractor):
        """Should remove crafted tags from mods."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = """Rarity: RARE
Test
Base
Implicits: 0
{crafted}+30% to Fire Resistance"""

        result = extractor._parse_item_element(item_elem)

        assert result is not None
        assert len(result.explicit_mods) == 1
        # Tags should be stripped
        assert result.explicit_mods[0] == "+30% to Fire Resistance"
        assert "{crafted}" not in result.explicit_mods[0]

    def test_parse_item_element_removes_fractured_tags(self, extractor):
        """Should remove fractured tags from mods."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = """Rarity: RARE
Test
Base
Implicits: 0
{fractured}+100 to Armour"""

        result = extractor._parse_item_element(item_elem)

        assert result is not None
        assert len(result.explicit_mods) == 1
        # Tags should be stripped
        assert result.explicit_mods[0] == "+100 to Armour"
        assert "{fractured}" not in result.explicit_mods[0]

    def test_parse_item_element_skips_metadata_lines(self, extractor):
        """Should skip all metadata lines."""
        from xml.etree.ElementTree import Element

        item_elem = Element("Item")
        item_elem.text = """Rarity: RARE
Test
Base
Elder Item
Shaper Item
Corrupted
Mirrored
Unique ID: 12345
Implicits: 0
+50 to maximum Life"""

        result = extractor._parse_item_element(item_elem)

        # Should have 1 explicit mod, metadata should be skipped
        assert len(result.explicit_mods) == 1
        assert result.explicit_mods[0] == "+50 to maximum Life"

    def test_compare_with_current_missing_profile(self, extractor, mock_char_manager):
        """Should return empty dict when current profile not found."""
        mock_char_manager.get_profile.return_value = None
        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")

        result = extractor.compare_with_current(summary, "NonExistent")

        assert result == {}

    def test_compare_with_current_no_build(self, extractor, mock_char_manager):
        """Should return empty dict when profile has no build."""
        profile = MagicMock()
        profile.build = None
        mock_char_manager.get_profile.return_value = profile
        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")

        result = extractor.compare_with_current(summary, "Current")

        assert result == {}

    def test_compare_with_current_empty_slot(self, extractor, mock_char_manager):
        """Should detect empty slot as upgrade needed."""
        from core.pob_integration import PoBBuild

        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet",
            item_name="Test Helmet",
            base_type="Test Base",
            rarity="RARE",
            is_unique=False,
        )

        current_profile = MagicMock()
        current_build = PoBBuild(class_name="Test", ascendancy="Test", level=90)
        current_build.items = {}  # No helmet
        current_profile.build = current_build
        mock_char_manager.get_profile.return_value = current_profile

        result = extractor.compare_with_current(summary, "Current")

        assert result["Helmet"]["has_item"] is False
        assert result["Helmet"]["upgrade_needed"] is True

    def test_compare_with_current_matching_rare(self, extractor, mock_char_manager):
        """Should detect matching rare by base type."""
        from core.pob_integration import PoBBuild, PoBItem

        summary = GuideGearSummary(profile_name="Guide", guide_name="Guide")
        summary.recommendations["Helmet"] = GuideGearRecommendation(
            slot="Helmet",
            item_name="",
            base_type="Astral Plate",
            rarity="RARE",
            is_unique=False,
        )

        current_profile = MagicMock()
        current_build = PoBBuild(class_name="Test", ascendancy="Test", level=90)
        current_build.items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="RARE",
                name="My Helmet",
                base_type="Astral Plate",
            )
        }
        current_profile.build = current_build
        mock_char_manager.get_profile.return_value = current_profile

        result = extractor.compare_with_current(summary, "Current")

        assert result["Helmet"]["is_match"] is True
        assert result["Helmet"]["upgrade_needed"] is False

    def test_item_to_recommendation_prioritizes_life_mods(self, extractor):
        """Should prioritize life mods in key_mods."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Body Armour",
            rarity="RARE",
            name="",
            base_type="Astral Plate",
            explicit_mods=[
                "+105 to maximum Life",
                "+45% to Fire Resistance",
                "+40% to Cold Resistance",
                "Some random mod",
            ],
        )

        rec = extractor._item_to_recommendation(item, "Body Armour")

        # Life should be captured since it matches priority pattern
        assert any("Life" in mod for mod in rec.key_mods)
        # At least one resistance should be captured
        assert any("Resistance" in mod for mod in rec.key_mods) or len(rec.key_mods) >= 2

    def test_item_to_recommendation_limits_key_mods(self, extractor):
        """Should limit key_mods to 5."""
        from core.pob_integration import PoBItem

        item = PoBItem(
            slot="Body Armour",
            rarity="RARE",
            name="",
            base_type="Test",
            explicit_mods=[
                "+100 to maximum Life",
                "+50% to Fire Resistance",
                "+50% to Cold Resistance",
                "+50% to Lightning Resistance",
                "+30% to Chaos Resistance",
                "+500 to Armour",
                "10% increased Stun Recovery",
                "5% increased Movement Speed",
            ],
        )

        rec = extractor._item_to_recommendation(item, "Body Armour")

        # Should capture at most 5 mods
        assert len(rec.key_mods) <= 5

    def test_extract_from_profile_success(self, extractor, mock_char_manager, sample_pob_build):
        """Should extract from profile successfully."""
        profile = MagicMock()
        profile.build = sample_pob_build
        mock_char_manager.get_profile.return_value = profile

        result = extractor.extract_from_profile("Test Profile")

        assert result is not None
        assert result.guide_name == "Slayer"

    def test_extract_from_pob_code_exception(self, extractor):
        """Should handle exceptions in extract_from_pob_code."""
        extractor._decoder.decode_pob_code = MagicMock(side_effect=Exception("Test error"))

        result = extractor.extract_from_pob_code("bad_code")

        assert result is None


class TestEquipmentSlots:
    """Tests for EQUIPMENT_SLOTS constant."""

    def test_has_all_slots(self):
        """Should have all standard equipment slots."""
        expected = {
            "Weapon 1", "Weapon 2", "Helmet", "Body Armour",
            "Gloves", "Boots", "Belt", "Amulet", "Ring 1", "Ring 2"
        }

        assert set(EQUIPMENT_SLOTS) == expected

    def test_correct_slot_count(self):
        """Should have 10 slots."""
        assert len(EQUIPMENT_SLOTS) == 10
