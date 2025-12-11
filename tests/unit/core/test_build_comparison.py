"""
Tests for build comparison module.
"""
from __future__ import annotations

import pytest

from core.build_comparison import (
    BuildComparator,
    GuideBuildParser,
    MaxrollBuildFetcher,
    ProgressionStage,
)

pytestmark = pytest.mark.unit


class TestProgressionStage:
    """Tests for ProgressionStage enum."""

    def test_from_level_early_leveling(self):
        assert ProgressionStage.from_level(1) == ProgressionStage.LEVELING_EARLY
        assert ProgressionStage.from_level(20) == ProgressionStage.LEVELING_EARLY
        assert ProgressionStage.from_level(39) == ProgressionStage.LEVELING_EARLY

    def test_from_level_late_leveling(self):
        assert ProgressionStage.from_level(40) == ProgressionStage.LEVELING_LATE
        assert ProgressionStage.from_level(55) == ProgressionStage.LEVELING_LATE
        assert ProgressionStage.from_level(69) == ProgressionStage.LEVELING_LATE

    def test_from_level_early_maps(self):
        assert ProgressionStage.from_level(70) == ProgressionStage.EARLY_MAPS
        assert ProgressionStage.from_level(78) == ProgressionStage.EARLY_MAPS
        assert ProgressionStage.from_level(84) == ProgressionStage.EARLY_MAPS

    def test_from_level_mid_maps(self):
        assert ProgressionStage.from_level(85) == ProgressionStage.MID_MAPS
        assert ProgressionStage.from_level(90) == ProgressionStage.MID_MAPS
        assert ProgressionStage.from_level(92) == ProgressionStage.MID_MAPS

    def test_from_level_endgame(self):
        assert ProgressionStage.from_level(93) == ProgressionStage.LATE_ENDGAME
        assert ProgressionStage.from_level(98) == ProgressionStage.LATE_ENDGAME
        assert ProgressionStage.from_level(100) == ProgressionStage.LATE_ENDGAME

    def test_display_name(self):
        assert ProgressionStage.LEVELING_EARLY.display_name == "Early Leveling (Acts 1-4)"
        assert ProgressionStage.LATE_ENDGAME.display_name == "Late Endgame"


class TestGuideBuildParser:
    """Tests for GuideBuildParser."""

    def test_clean_title_removes_simple_color_codes(self):
        parser = GuideBuildParser()
        assert parser.clean_title("^2Early lvl 92") == "Early lvl 92"
        assert parser.clean_title("^1Mid ^5test") == "Mid test"

    def test_clean_title_removes_hex_color_codes(self):
        parser = GuideBuildParser()
        assert parser.clean_title("^xE05030Warning") == "Warning"
        assert parser.clean_title("^xABCDEF^1Test") == "Test"

    def test_infer_level_from_explicit_level(self):
        parser = GuideBuildParser()
        assert parser._infer_level_from_title("Lvl 92 build") == 92
        assert parser._infer_level_from_title("level 85 starter") == 85
        assert parser._infer_level_from_title("lvl92") == 92

    def test_infer_level_from_act(self):
        parser = GuideBuildParser()
        assert parser._infer_level_from_title("Act 1") == 12
        assert parser._infer_level_from_title("Act 3") == 33
        assert parser._infer_level_from_title("Act 4-10") == 70
        assert parser._infer_level_from_title("Act 10 final") == 70

    def test_infer_level_from_stage_keywords(self):
        parser = GuideBuildParser()
        assert parser._infer_level_from_title("Early No Svalinn") == 85
        assert parser._infer_level_from_title("Mid Amanamu") == 92
        assert parser._infer_level_from_title("Late endgame") == 98  # "endgame" matches first (more specific)
        assert parser._infer_level_from_title("Late game") == 96  # "late" matches when no "endgame"

    def test_infer_level_returns_none_for_unknown(self):
        parser = GuideBuildParser()
        assert parser._infer_level_from_title("Random title") is None
        assert parser._infer_level_from_title("") is None


class TestMaxrollBuildFetcher:
    """Tests for MaxrollBuildFetcher."""

    def test_extract_build_id_from_url(self):
        fetcher = MaxrollBuildFetcher()

        # Standard URL
        assert fetcher.extract_build_id("https://maxroll.gg/poe/pob/0nws0aiy") == "0nws0aiy"

        # URL with trailing slash
        assert fetcher.extract_build_id("https://maxroll.gg/poe/pob/abc123/") == "abc123"

        # Invalid URL
        assert fetcher.extract_build_id("https://example.com/test") is None


class TestBuildComparatorTreeComparison:
    """Tests for tree comparison logic."""

    def test_compare_trees_identical(self):
        comparator = BuildComparator()
        nodes = {1, 2, 3, 4, 5}

        result = comparator.compare_trees(nodes, nodes)

        assert result.match_percent == 100.0
        assert len(result.missing_nodes) == 0
        assert len(result.extra_nodes) == 0
        assert len(result.shared_nodes) == 5

    def test_compare_trees_partial_match(self):
        comparator = BuildComparator()
        player_nodes = {1, 2, 3}
        guide_nodes = {2, 3, 4, 5}

        result = comparator.compare_trees(player_nodes, guide_nodes)

        # 2 shared out of 4 guide nodes = 50%
        assert result.match_percent == 50.0
        assert sorted(result.missing_nodes) == [4, 5]
        assert result.extra_nodes == [1]
        assert sorted(result.shared_nodes) == [2, 3]

    def test_compare_trees_no_overlap(self):
        comparator = BuildComparator()
        player_nodes = {1, 2}
        guide_nodes = {3, 4}

        result = comparator.compare_trees(player_nodes, guide_nodes)

        assert result.match_percent == 0.0
        assert sorted(result.missing_nodes) == [3, 4]
        assert sorted(result.extra_nodes) == [1, 2]

    def test_compare_trees_empty_guide(self):
        comparator = BuildComparator()
        player_nodes = {1, 2, 3}
        guide_nodes = set()

        result = comparator.compare_trees(player_nodes, guide_nodes)

        # Empty guide = 100% match (nothing to match against)
        assert result.match_percent == 100.0

    def test_compare_trees_with_masteries(self):
        comparator = BuildComparator()
        player_nodes = {1, 2, 3}
        guide_nodes = {1, 2, 3}
        player_masteries = [(100, 1), (200, 2)]
        guide_masteries = [(100, 1), (200, 2), (300, 3)]

        result = comparator.compare_trees(
            player_nodes, guide_nodes,
            player_masteries, guide_masteries
        )

        # Missing one mastery
        assert len(result.missing_masteries) == 1
        assert (300, 3) in result.missing_masteries


class TestBuildComparatorEquipment:
    """Tests for equipment comparison."""

    def test_compare_equipment_matching_uniques(self):
        from core.pob import PoBItem

        comparator = BuildComparator()

        player_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="UNIQUE",
                name="The Covenant",
                base_type="Spidersilk Robe"
            )
        }

        guide_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="UNIQUE",
                name="The Covenant",
                base_type="Spidersilk Robe"
            )
        }

        result = comparator.compare_equipment(player_items, guide_items)

        assert result.match_percent == 100.0
        assert len(result.missing_uniques) == 0
        assert result.slot_deltas["Body Armour"].is_match is True

    def test_compare_equipment_missing_unique(self):
        from core.pob import PoBItem

        comparator = BuildComparator()

        player_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="RARE",
                name="Some Rare",
                base_type="Astral Plate"
            )
        }

        guide_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="UNIQUE",
                name="The Covenant",
                base_type="Spidersilk Robe"
            )
        }

        result = comparator.compare_equipment(player_items, guide_items)

        assert result.match_percent == 0.0
        assert "The Covenant" in result.missing_uniques
        assert result.slot_deltas["Body Armour"].missing_unique == "The Covenant"


@pytest.mark.integration
class TestMaxrollIntegration:
    """Integration tests that fetch from Maxroll API."""

    def test_fetch_and_parse_build(self):
        """Test fetching and parsing a real Maxroll build."""
        fetcher = MaxrollBuildFetcher()
        parser = GuideBuildParser()

        try:
            xml_string = fetcher.fetch_and_decode("0nws0aiy")
        except Exception as e:
            pytest.skip(f"Could not fetch from Maxroll API: {e}")
            return  # Explicit return to help static analysis

        # Parse tree specs
        specs = parser.parse_tree_specs(xml_string)
        assert len(specs) > 0

        # Check that at least some have inferred levels
        leveled_specs = [s for s in specs if s.inferred_level is not None]
        assert len(leveled_specs) > 0

        # Parse skill sets
        skill_sets = parser.parse_skill_sets(xml_string)
        assert len(skill_sets) > 0

    def test_find_spec_for_various_levels(self):
        """Test level-appropriate spec selection."""
        fetcher = MaxrollBuildFetcher()
        parser = GuideBuildParser()

        try:
            xml_string = fetcher.fetch_and_decode("0nws0aiy")
        except Exception as e:
            pytest.skip(f"Could not fetch from Maxroll API: {e}")
            return  # Explicit return to help static analysis

        specs = parser.parse_tree_specs(xml_string)

        # Should find different specs for different levels
        spec_70 = parser.find_spec_for_level(specs, 70)
        spec_92 = parser.find_spec_for_level(specs, 92)

        assert spec_70 is not None
        assert spec_92 is not None

        # Level 92 spec should have more nodes than level 70
        assert len(spec_92.nodes) >= len(spec_70.nodes)
