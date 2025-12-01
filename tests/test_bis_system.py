"""
Tests for the BiS (Best-in-Slot) system components.

Tests:
- Build Priorities
- Affix Tier Calculator
- Guide Gear Extractor
- BiS Calculator integration
"""
import pytest

from core.build_priorities import (
    BuildPriorities, PriorityTier, AVAILABLE_STATS,
    suggest_priorities_from_build
)
from core.affix_tier_calculator import (
    AffixTierCalculator, AffixTier, AFFIX_TIER_DATA,
    SLOT_AVAILABLE_AFFIXES
)
from core.guide_gear_extractor import (
    GuideGearExtractor
)
from core.pob_integration import PoBBuild, PoBItem


class TestBuildPriorities:
    """Tests for BuildPriorities class."""

    def test_create_empty_priorities(self):
        """Test creating empty priorities."""
        priorities = BuildPriorities()
        assert len(priorities.critical) == 0
        assert len(priorities.important) == 0
        assert len(priorities.nice_to_have) == 0
        assert priorities.is_life_build is True

    def test_add_priority_critical(self):
        """Test adding a critical priority."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL, min_value=80)

        assert len(priorities.critical) == 1
        assert priorities.critical[0].stat_type == "life"
        assert priorities.critical[0].min_value == 80

    def test_add_priority_moves_between_tiers(self):
        """Test that adding to a new tier removes from old tier."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        assert len(priorities.critical) == 1

        priorities.add_priority("life", PriorityTier.IMPORTANT)
        assert len(priorities.critical) == 0
        assert len(priorities.important) == 1

    def test_remove_priority(self):
        """Test removing a priority."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)

        priorities.remove_priority("life")
        assert len(priorities.critical) == 0
        assert len(priorities.important) == 1

    def test_get_priority(self):
        """Test getting a specific priority."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL, min_value=90)

        p = priorities.get_priority("life")
        assert p is not None
        assert p.stat_type == "life"
        assert p.min_value == 90

        p = priorities.get_priority("nonexistent")
        assert p is None

    def test_get_all_priorities(self):
        """Test getting all priorities in order."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE)

        all_p = priorities.get_all_priorities()
        assert len(all_p) == 3
        assert all_p[0].stat_type == "life"
        assert all_p[1].stat_type == "fire_resistance"
        assert all_p[2].stat_type == "movement_speed"

    def test_serialization(self):
        """Test to_dict and from_dict."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL, min_value=80)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        priorities.is_es_build = True

        data = priorities.to_dict()
        restored = BuildPriorities.from_dict(data)

        assert len(restored.critical) == 1
        assert restored.critical[0].stat_type == "life"
        assert restored.critical[0].min_value == 80
        assert restored.is_es_build is True

    def test_suggest_priorities_life_build(self):
        """Test auto-suggestion for life build."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 200.0,
            "FireResistOverCap": 10.0,  # Low
            "ColdResistOverCap": 50.0,
            "LightningResistOverCap": 45.0,
            "ChaosResist": 25.0,  # Low
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.is_life_build is True
        assert priorities.is_es_build is False
        # Should have life as critical
        assert any(p.stat_type == "life" for p in priorities.critical)
        # Should have fire res as important (low overcap)
        assert any(p.stat_type == "fire_resistance" for p in priorities.important)

    def test_suggest_priorities_es_build(self):
        """Test auto-suggestion for ES build."""
        stats = {
            "Life": 1000.0,
            "EnergyShield": 8000.0,  # High ES
            "FireResistOverCap": 50.0,
            "ColdResistOverCap": 50.0,
            "LightningResistOverCap": 50.0,
            "ChaosResist": 50.0,
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.is_life_build is False
        assert priorities.is_es_build is True
        assert any(p.stat_type == "energy_shield" for p in priorities.critical)


class TestAffixTierCalculator:
    """Tests for AffixTierCalculator class."""

    def test_get_best_tier_for_ilvl_86(self):
        """Test getting best tier at ilvl 86 (T1)."""
        calc = AffixTierCalculator()
        tier = calc.get_best_tier_for_ilvl("life", 86)

        assert tier is not None
        assert tier.tier == 1
        assert tier.min_value == 120
        assert tier.max_value == 129

    def test_get_best_tier_for_ilvl_75(self):
        """Test getting best tier at ilvl 75 (T3)."""
        calc = AffixTierCalculator()
        tier = calc.get_best_tier_for_ilvl("life", 75)

        assert tier is not None
        assert tier.tier == 3
        assert tier.ilvl_required == 73

    def test_get_best_tier_unknown_stat(self):
        """Test getting tier for unknown stat returns None."""
        calc = AffixTierCalculator()
        tier = calc.get_best_tier_for_ilvl("unknown_stat", 86)
        assert tier is None

    def test_get_all_tiers(self):
        """Test getting all tiers for a stat."""
        calc = AffixTierCalculator()
        tiers = calc.get_all_tiers("life")

        assert len(tiers) == 13
        assert tiers[0].tier == 1
        assert tiers[-1].tier == 13

    def test_can_slot_have_stat(self):
        """Test slot-stat availability checks."""
        calc = AffixTierCalculator()

        # Boots can have movement speed
        assert calc.can_slot_have_stat("Boots", "movement_speed") is True
        # Helmet cannot have movement speed
        assert calc.can_slot_have_stat("Helmet", "movement_speed") is False
        # Gloves can have attack speed
        assert calc.can_slot_have_stat("Gloves", "attack_speed") is True

    def test_calculate_ideal_rare_helmet(self):
        """Test ideal rare calculation for helmet."""
        calc = AffixTierCalculator()
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)

        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=84)

        assert spec.slot == "Helmet"
        assert spec.target_ilvl == 84
        # Should have life and fire res
        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types
        assert "fire_resistance" in stat_types

    def test_calculate_ideal_rare_boots_adds_movement_speed(self):
        """Test that boots automatically include movement speed."""
        calc = AffixTierCalculator()
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)

        spec = calc.calculate_ideal_rare("Boots", priorities, target_ilvl=86)

        stat_types = [a.stat_type for a in spec.affixes]
        assert "movement_speed" in stat_types

    def test_affix_tier_display_range(self):
        """Test AffixTier display_range property."""
        tier = AffixTier(
            stat_type="life",
            tier=1,
            ilvl_required=86,
            min_value=100,
            max_value=109
        )
        assert tier.display_range == "100-109"

        # Single value
        tier_single = AffixTier(
            stat_type="movement_speed",
            tier=1,
            ilvl_required=86,
            min_value=35,
            max_value=35
        )
        assert tier_single.display_range == "35"


class TestGuideGearExtractor:
    """Tests for GuideGearExtractor class."""

    @pytest.fixture
    def sample_build(self):
        """Create a sample build for testing."""
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
                explicit_mods=[
                    "+60 to Dexterity",
                    "16% increased Attack Speed",
                    "20% increased Movement Speed",
                ]
            ),
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="RARE",
                name="Apocalypse Shell",
                base_type="Astral Plate",
                explicit_mods=[
                    "+105 to maximum Life",
                    "+45% to Fire Resistance",
                    "+42% to Cold Resistance",
                ]
            ),
        }
        return build

    def test_extract_from_build(self, sample_build):
        """Test extracting gear from a build."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        assert summary.guide_name == "Slayer"
        assert len(summary.recommendations) == 2
        assert "Devoto's Devotion" in summary.uniques_needed
        assert "Body Armour" in summary.rare_slots

    def test_unique_recommendation(self, sample_build):
        """Test unique item recommendation extraction."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        helmet_rec = summary.get_recommendation("Helmet")
        assert helmet_rec is not None
        assert helmet_rec.is_unique is True
        assert helmet_rec.item_name == "Devoto's Devotion"
        assert helmet_rec.priority == 1  # Uniques are high priority

    def test_rare_recommendation(self, sample_build):
        """Test rare item recommendation extraction."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        body_rec = summary.get_recommendation("Body Armour")
        assert body_rec is not None
        assert body_rec.is_unique is False
        assert body_rec.base_type == "Astral Plate"
        assert len(body_rec.key_mods) > 0

    def test_get_unique_recommendations(self, sample_build):
        """Test filtering unique recommendations."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        uniques = summary.get_unique_recommendations()
        assert len(uniques) == 1
        assert all(r.is_unique for r in uniques)

    def test_get_rare_recommendations(self, sample_build):
        """Test filtering rare recommendations."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        rares = summary.get_rare_recommendations()
        assert len(rares) == 1
        assert all(not r.is_unique for r in rares)

    def test_format_summary_text(self, sample_build):
        """Test text formatting of gear summary."""
        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(sample_build, "Test Build")

        text = extractor.format_summary_text(summary)
        assert "Devoto's Devotion" in text
        assert "Astral Plate" in text
        assert "UNIQUE ITEMS" in text
        assert "RARE ITEM" in text


class TestIntegration:
    """Integration tests for BiS system components."""

    def test_priorities_to_ideal_rare(self):
        """Test end-to-end from priorities to ideal rare."""
        # Create priorities
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        priorities.add_priority("cold_resistance", PriorityTier.IMPORTANT)

        # Calculate ideal rare
        calc = AffixTierCalculator()
        spec = calc.calculate_ideal_rare("Helmet", priorities, target_ilvl=84)

        # Verify results
        assert spec.slot == "Helmet"
        stat_types = [a.stat_type for a in spec.affixes]
        assert "life" in stat_types
        assert "fire_resistance" in stat_types
        assert "cold_resistance" in stat_types

        # Verify tiers match ilvl 84
        for affix in spec.affixes:
            assert affix.ilvl_required <= 84

    def test_guide_extraction_preserves_mod_priority(self):
        """Test that key mods are preserved during extraction."""
        build = PoBBuild(class_name="Test", ascendancy="Test", level=90)
        build.items = {
            "Ring 1": PoBItem(
                slot="Ring 1",
                rarity="RARE",
                name="Test Ring",
                base_type="Diamond Ring",
                explicit_mods=[
                    "+75 to maximum Life",
                    "+40% to Fire Resistance",
                    "+35% to Cold Resistance",
                    "+30% to Lightning Resistance",
                    "+15 to all Attributes",
                ]
            )
        }

        extractor = GuideGearExtractor()
        summary = extractor._extract_from_build(build, "Test")

        ring_rec = summary.get_recommendation("Ring 1")
        # Life and resistance mods should be prioritized
        assert any("Life" in mod for mod in ring_rec.key_mods)


class TestAvailableStats:
    """Tests for AVAILABLE_STATS constant."""

    def test_all_stats_have_display_names(self):
        """Test that all stats have display names."""
        for stat_type, display_name in AVAILABLE_STATS.items():
            assert display_name, f"Stat {stat_type} has empty display name"

    def test_common_stats_present(self):
        """Test that common stats are available."""
        required = ["life", "energy_shield", "fire_resistance", "cold_resistance",
                   "lightning_resistance", "strength", "dexterity", "intelligence"]
        for stat in required:
            assert stat in AVAILABLE_STATS


class TestAffixTierData:
    """Tests for AFFIX_TIER_DATA constant."""

    def test_tier_data_format(self):
        """Test that tier data is in correct format."""
        for stat_type, tiers in AFFIX_TIER_DATA.items():
            assert isinstance(tiers, list), f"{stat_type} tiers not a list"
            for tier_data in tiers:
                assert len(tier_data) == 4, f"{stat_type} tier has wrong length"
                tier_num, ilvl, min_val, max_val = tier_data
                assert isinstance(tier_num, int)
                assert isinstance(ilvl, int)
                assert isinstance(min_val, int)
                assert isinstance(max_val, int)
                assert min_val <= max_val

    def test_tiers_sorted_by_ilvl_descending(self):
        """Test that tiers are sorted by ilvl (T1 first)."""
        for stat_type, tiers in AFFIX_TIER_DATA.items():
            ilvls = [t[1] for t in tiers]
            assert ilvls == sorted(ilvls, reverse=True), f"{stat_type} tiers not sorted"


class TestSlotAvailableAffixes:
    """Tests for SLOT_AVAILABLE_AFFIXES constant."""

    def test_all_slots_have_affixes(self):
        """Test that all slots have affix lists."""
        expected_slots = ["Helmet", "Body Armour", "Gloves", "Boots",
                        "Belt", "Ring", "Amulet", "Shield"]
        for slot in expected_slots:
            assert slot in SLOT_AVAILABLE_AFFIXES

    def test_boots_have_movement_speed(self):
        """Test that boots can have movement speed."""
        assert "movement_speed" in SLOT_AVAILABLE_AFFIXES["Boots"]

    def test_gloves_have_attack_speed(self):
        """Test that gloves can have attack speed."""
        assert "attack_speed" in SLOT_AVAILABLE_AFFIXES["Gloves"]

    def test_all_slots_have_resistances(self):
        """Test that all armor slots can have resistances."""
        armor_slots = ["Helmet", "Body Armour", "Gloves", "Boots", "Shield"]
        for slot in armor_slots:
            affixes = SLOT_AVAILABLE_AFFIXES[slot]
            assert "fire_resistance" in affixes or "resistances" in affixes or \
                   any("resistance" in a for a in affixes), f"{slot} missing resistances"
