"""Tests for core/guide_gear_extractor.py - Build guide gear extraction."""
from unittest.mock import MagicMock, patch

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
