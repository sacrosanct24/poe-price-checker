"""
Tests for build comparison module.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from core.build_comparison import (
    BuildComparator,
    GuideBuildParser,
    MaxrollBuildFetcher,
    ProgressionStage,
    TreeSpec,
    SkillSetSpec,
    TreeDelta,
    SkillDelta,
    ItemDelta,
    EquipmentDelta,
    BuildDelta,
)
from core.pob import PoBBuild, PoBItem

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


class TestMaxrollBuildFetcherMocked:
    """Unit tests for MaxrollBuildFetcher with mocked requests."""

    def test_fetch_empty_build_id_raises(self):
        """Empty build_id should raise ValueError."""
        fetcher = MaxrollBuildFetcher()
        with pytest.raises(ValueError, match="build_id cannot be empty"):
            fetcher.fetch("")

    def test_fetch_uses_cache(self):
        """Fetch should use cache on second call."""
        fetcher = MaxrollBuildFetcher()
        fetcher._cache["test123"] = "cached_code"

        result = fetcher.fetch("test123")

        assert result == "cached_code"

    @patch("core.build_comparison.requests.get")
    def test_fetch_success(self, mock_get):
        """Successful fetch should return and cache code."""
        mock_response = Mock()
        mock_response.text = "pob_code_here"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = MaxrollBuildFetcher()
        result = fetcher.fetch("abc123")

        assert result == "pob_code_here"
        assert fetcher._cache["abc123"] == "pob_code_here"
        mock_get.assert_called_once()

    @patch("core.build_comparison.requests.get")
    def test_fetch_timeout_raises(self, mock_get):
        """Timeout should raise requests.Timeout."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        fetcher = MaxrollBuildFetcher()
        with pytest.raises(requests.Timeout):
            fetcher.fetch("abc123")

    @patch("core.build_comparison.requests.get")
    def test_fetch_404_raises_value_error(self, mock_get):
        """404 response should raise ValueError."""
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        fetcher = MaxrollBuildFetcher()
        with pytest.raises(ValueError, match="Build not found"):
            fetcher.fetch("nonexistent")

    @patch("core.build_comparison.requests.get")
    def test_fetch_other_http_error_raises(self, mock_get):
        """Other HTTP errors should raise HTTPError."""
        mock_response = Mock()
        mock_response.status_code = 500
        http_error = requests.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        fetcher = MaxrollBuildFetcher()
        with pytest.raises(requests.HTTPError):
            fetcher.fetch("abc123")

    @patch("core.build_comparison.requests.get")
    @patch("core.build_comparison.PoBDecoder.decode_pob_code")
    def test_fetch_and_decode(self, mock_decode, mock_get):
        """fetch_and_decode should fetch and decode."""
        mock_response = Mock()
        mock_response.text = "encoded_pob"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_decode.return_value = "<Build></Build>"

        fetcher = MaxrollBuildFetcher()
        result = fetcher.fetch_and_decode("abc123")

        assert result == "<Build></Build>"
        mock_decode.assert_called_once_with("encoded_pob")

    def test_clear_cache(self):
        """clear_cache should empty the cache."""
        fetcher = MaxrollBuildFetcher()
        fetcher._cache["test"] = "data"

        fetcher.clear_cache()

        assert fetcher._cache == {}

    def test_extract_build_id_empty_url(self):
        """Empty URL should return None."""
        assert MaxrollBuildFetcher.extract_build_id("") is None
        assert MaxrollBuildFetcher.extract_build_id(None) is None


class TestGuideBuildParserXML:
    """Tests for GuideBuildParser with XML parsing."""

    @pytest.fixture
    def sample_xml(self):
        """Sample PoB XML for testing."""
        return """<?xml version="1.0" encoding="utf-8"?>
<PathOfBuilding>
    <Tree>
        <Spec title="^2Early lvl 70" treeVersion="3_24" classId="1" ascendClassId="1" nodes="1,2,3,4,5" masteryEffects="{100,1},{200,2}">
            <URL>https://example.com/tree</URL>
        </Spec>
        <Spec title="Late endgame" treeVersion="3_24" classId="1" ascendClassId="1" nodes="1,2,3,4,5,6,7,8,9,10" masteryEffects="">
        </Spec>
    </Tree>
    <Skills>
        <SkillSet id="1" title="^1Leveling Skills">
            <Skill enabled="true" slot="Body Armour" label="Main Skill">
                <Gem nameSpec="Arc" level="20" quality="20" enabled="true"/>
                <Gem nameSpec="Spell Echo" level="18" quality="0" enabled="true"/>
            </Skill>
            <Skill enabled="false" slot="Gloves" label="Disabled">
                <Gem nameSpec="Shield Charge" level="1" quality="0" enabled="true"/>
            </Skill>
        </SkillSet>
        <SkillSet id="2" title="Endgame Skills">
            <Skill enabled="true" slot="Body Armour" label="">
                <Gem nameSpec="Arc" level="21" quality="23" enabled="true"/>
                <Gem nameSpec="Spell Echo" level="21" quality="20" enabled="true"/>
                <Gem nameSpec="Added Lightning" level="21" quality="20" enabled="false"/>
            </Skill>
        </SkillSet>
    </Skills>
</PathOfBuilding>"""

    def test_parse_tree_specs(self, sample_xml):
        """parse_tree_specs should parse all specs."""
        parser = GuideBuildParser()
        specs = parser.parse_tree_specs(sample_xml)

        assert len(specs) == 2
        assert specs[0].title == "Early lvl 70"
        assert specs[0].inferred_level == 70
        assert len(specs[0].nodes) == 5
        assert len(specs[0].mastery_effects) == 2
        assert specs[0].url == "https://example.com/tree"

        assert specs[1].title == "Late endgame"
        assert specs[1].inferred_level == 98

    def test_parse_tree_specs_no_tree_element(self):
        """parse_tree_specs should return empty list if no Tree element."""
        parser = GuideBuildParser()
        xml = "<PathOfBuilding></PathOfBuilding>"
        specs = parser.parse_tree_specs(xml)
        assert specs == []

    def test_parse_skill_sets(self, sample_xml):
        """parse_skill_sets should parse all skill sets."""
        parser = GuideBuildParser()
        skill_sets = parser.parse_skill_sets(sample_xml)

        assert len(skill_sets) == 2

        # First skill set
        assert skill_sets[0].title == "Leveling Skills"
        assert len(skill_sets[0].skills) == 1  # Disabled skill not included
        assert skill_sets[0].skills[0]["label"] == "Main Skill"
        assert len(skill_sets[0].skills[0]["gems"]) == 2

        # Second skill set
        assert skill_sets[1].title == "Endgame Skills"
        # Disabled gem not included
        assert len(skill_sets[1].skills[0]["gems"]) == 2

    def test_parse_skill_sets_no_skills_element(self):
        """parse_skill_sets should return empty list if no Skills element."""
        parser = GuideBuildParser()
        xml = "<PathOfBuilding></PathOfBuilding>"
        skill_sets = parser.parse_skill_sets(xml)
        assert skill_sets == []

    def test_find_spec_for_level_empty_list(self):
        """find_spec_for_level should return None for empty list."""
        parser = GuideBuildParser()
        result = parser.find_spec_for_level([], 70)
        assert result is None

    def test_find_spec_for_level_matches_closest(self, sample_xml):
        """find_spec_for_level should match closest level spec at or below target."""
        parser = GuideBuildParser()
        specs = parser.parse_tree_specs(sample_xml)

        # Level 70 should match first spec (level 70)
        result = parser.find_spec_for_level(specs, 70)
        assert result.inferred_level == 70

        # Level 95 should match level 70 spec (closest at or below)
        result = parser.find_spec_for_level(specs, 95)
        assert result.inferred_level == 70  # 95 is between 70 and 98, so use 70

        # Level 100 should match level 98 spec
        result = parser.find_spec_for_level(specs, 100)
        assert result.inferred_level == 98

    def test_find_spec_for_level_below_all(self, sample_xml):
        """find_spec_for_level should return lowest when target below all."""
        parser = GuideBuildParser()
        specs = parser.parse_tree_specs(sample_xml)

        # Level 30 is below all specs
        result = parser.find_spec_for_level(specs, 30)
        # Should return the lowest spec
        assert result.inferred_level == 70

    def test_find_spec_for_level_keyword_fallback(self):
        """find_spec_for_level should use keywords when no levels inferred."""
        parser = GuideBuildParser()
        # Create specs without inferred levels
        specs = [
            TreeSpec(
                title="Budget starter",
                raw_title="Budget starter",
                tree_version="3_24",
                class_id=1,
                ascend_class_id=1,
                nodes={1, 2, 3},
                mastery_effects=[],
                inferred_level=None,
            ),
            TreeSpec(
                title="Final build",
                raw_title="Final build",
                tree_version="3_24",
                class_id=1,
                ascend_class_id=1,
                nodes={1, 2, 3, 4, 5},
                mastery_effects=[],
                inferred_level=None,
            ),
        ]

        # Should match "budget" for early maps
        result = parser.find_spec_for_level(specs, 75)
        assert "Budget" in result.title

        # Should match "final" for endgame
        result = parser.find_spec_for_level(specs, 95)
        assert "Final" in result.title

    def test_find_skill_set_for_level_empty(self):
        """find_skill_set_for_level should return None for empty list."""
        parser = GuideBuildParser()
        result = parser.find_skill_set_for_level([], 70)
        assert result is None

    def test_find_skill_set_for_level_keyword_fallback(self):
        """find_skill_set_for_level should use keywords when no levels."""
        parser = GuideBuildParser()
        skill_sets = [
            SkillSetSpec(
                id="1",
                title="Act 5 setup",
                raw_title="Act 5 setup",
                skills=[],
                inferred_level=None,
            ),
            SkillSetSpec(
                id="2",
                title="Endgame setup",
                raw_title="Endgame setup",
                skills=[],
                inferred_level=None,
            ),
        ]

        # Level 55 should match "act 5" for late leveling
        result = parser.find_skill_set_for_level(skill_sets, 55)
        assert "Act 5" in result.title


class TestBuildComparatorSkills:
    """Tests for skill comparison."""

    def test_compare_skills_identical(self):
        """Identical gems should have 100% match."""
        comparator = BuildComparator()
        player_gems = {
            "Arc": {"level": 20, "quality": 20},
            "Spell Echo": {"level": 20, "quality": 20},
        }
        guide_skill_set = SkillSetSpec(
            id="1",
            title="Test",
            raw_title="Test",
            skills=[{
                "label": "Main",
                "slot": "Body Armour",
                "gems": [
                    {"name": "Arc", "level": 20, "quality": 20},
                    {"name": "Spell Echo", "level": 20, "quality": 20},
                ]
            }],
            inferred_level=90,
        )

        result = comparator.compare_skills(player_gems, guide_skill_set)

        assert result.match_percent == 100.0
        assert len(result.missing_gems) == 0
        assert len(result.extra_gems) == 0
        assert len(result.gem_level_gaps) == 0

    def test_compare_skills_missing_gems(self):
        """Missing gems should be reported."""
        comparator = BuildComparator()
        player_gems = {"Arc": {"level": 20, "quality": 20}}
        guide_skill_set = SkillSetSpec(
            id="1",
            title="Test",
            raw_title="Test",
            skills=[{
                "label": "Main",
                "slot": "Body Armour",
                "gems": [
                    {"name": "Arc", "level": 20, "quality": 20},
                    {"name": "Spell Echo", "level": 20, "quality": 20},
                ]
            }],
            inferred_level=90,
        )

        result = comparator.compare_skills(player_gems, guide_skill_set)

        assert result.match_percent == 50.0
        assert "Spell Echo" in result.missing_gems

    def test_compare_skills_extra_gems(self):
        """Extra player gems should be reported."""
        comparator = BuildComparator()
        player_gems = {
            "Arc": {"level": 20, "quality": 20},
            "Extra Gem": {"level": 20, "quality": 20},
        }
        guide_skill_set = SkillSetSpec(
            id="1",
            title="Test",
            raw_title="Test",
            skills=[{
                "label": "Main",
                "slot": "Body Armour",
                "gems": [{"name": "Arc", "level": 20, "quality": 20}]
            }],
            inferred_level=90,
        )

        result = comparator.compare_skills(player_gems, guide_skill_set)

        assert "Extra Gem" in result.extra_gems

    def test_compare_skills_level_gaps(self):
        """Level gaps should be reported for underleveled gems."""
        comparator = BuildComparator()
        player_gems = {"Arc": {"level": 15, "quality": 10}}
        guide_skill_set = SkillSetSpec(
            id="1",
            title="Test",
            raw_title="Test",
            skills=[{
                "label": "Main",
                "slot": "Body Armour",
                "gems": [{"name": "Arc", "level": 20, "quality": 20}]
            }],
            inferred_level=90,
        )

        result = comparator.compare_skills(player_gems, guide_skill_set)

        assert "Arc" in result.gem_level_gaps
        assert result.gem_level_gaps["Arc"] == -5  # Player is 5 levels behind
        assert "Arc" in result.gem_quality_gaps
        assert result.gem_quality_gaps["Arc"] == -10

    def test_compare_skills_empty_guide(self):
        """Empty guide should return 100% match."""
        comparator = BuildComparator()
        player_gems = {"Arc": {"level": 20, "quality": 20}}
        guide_skill_set = SkillSetSpec(
            id="1",
            title="Test",
            raw_title="Test",
            skills=[],
            inferred_level=90,
        )

        result = comparator.compare_skills(player_gems, guide_skill_set)

        assert result.match_percent == 100.0


class TestBuildComparatorEquipmentExtended:
    """Extended equipment comparison tests."""

    def test_compare_equipment_matching_rares(self):
        """Matching rare base types should match."""
        comparator = BuildComparator()

        player_items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="RARE",
                name="My Helmet",
                base_type="Hubris Circlet"
            )
        }
        guide_items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="RARE",
                name="Guide Helmet",
                base_type="Hubris Circlet"
            )
        }

        result = comparator.compare_equipment(player_items, guide_items)

        assert result.match_percent == 100.0
        assert result.slot_deltas["Helmet"].is_match is True

    def test_compare_equipment_empty_player_slot(self):
        """Empty player slot should not match."""
        comparator = BuildComparator()

        player_items = {}
        guide_items = {
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="UNIQUE",
                name="Crown of Eyes",
                base_type="Hubris Circlet"
            )
        }

        result = comparator.compare_equipment(player_items, guide_items)

        assert result.match_percent == 0.0
        assert "Crown of Eyes" in result.missing_uniques

    def test_compare_equipment_upgrade_priority(self):
        """Upgrade priority should be set correctly."""
        comparator = BuildComparator()

        player_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="RARE",
                name="Random Chest",
                base_type="Random Base"
            ),
            "Boots": PoBItem(
                slot="Boots",
                rarity="RARE",
                name="Random Boots",
                base_type="Random Base"
            )
        }
        guide_items = {
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="UNIQUE",
                name="Kaom's Heart",
                base_type="Glorious Plate"
            ),
            "Boots": PoBItem(
                slot="Boots",
                rarity="UNIQUE",
                name="Atziri's Step",
                base_type="Slink Boots"
            )
        }

        result = comparator.compare_equipment(player_items, guide_items)

        # Body Armour (major slot) should have priority 1
        assert result.slot_deltas["Body Armour"].upgrade_priority == 1
        # Boots should have priority 2
        assert result.slot_deltas["Boots"].upgrade_priority == 2


class TestBuildComparatorFullComparison:
    """Tests for full build comparison."""

    @pytest.fixture
    def sample_guide_xml(self):
        """Sample guide XML."""
        return """<?xml version="1.0" encoding="utf-8"?>
<PathOfBuilding>
    <Build level="95" className="Witch" ascendClassName="Elementalist">
    </Build>
    <Tree>
        <Spec title="Endgame" treeVersion="3_24" classId="3" ascendClassId="1" nodes="1,2,3,4,5">
        </Spec>
    </Tree>
    <Skills>
        <SkillSet id="1" title="Endgame">
            <Skill enabled="true" slot="Body Armour">
                <Gem nameSpec="Arc" level="21" quality="20" enabled="true"/>
            </Skill>
        </SkillSet>
    </Skills>
    <Items>
    </Items>
</PathOfBuilding>"""

    def test_compare_builds_basic(self, sample_guide_xml):
        """compare_builds should produce BuildDelta."""
        comparator = BuildComparator()

        player_build = PoBBuild(
            level=90,
            class_name="Witch",
            ascendancy="Elementalist",
            items={},
            raw_xml="",
        )

        result = comparator.compare_builds(player_build, sample_guide_xml)

        assert isinstance(result, BuildDelta)
        assert result.player_level == 90
        assert result.progression_stage == ProgressionStage.MID_MAPS
        assert isinstance(result.tree_delta, TreeDelta)
        assert isinstance(result.skill_delta, SkillDelta)
        assert isinstance(result.equipment_delta, EquipmentDelta)

    def test_compare_builds_with_player_level_override(self, sample_guide_xml):
        """player_level parameter should override build level."""
        comparator = BuildComparator()

        player_build = PoBBuild(
            level=90,
            class_name="Witch",
            ascendancy="Elementalist",
            items={},
            raw_xml="",
        )

        result = comparator.compare_builds(player_build, sample_guide_xml, player_level=95)

        assert result.player_level == 95
        assert result.progression_stage == ProgressionStage.LATE_ENDGAME


class TestBuildComparatorPriorities:
    """Tests for priority generation."""

    def test_generate_priorities(self):
        """_generate_priorities should create prioritized list."""
        comparator = BuildComparator()

        tree_delta = TreeDelta(
            missing_nodes=[1, 2, 3, 4, 5],
            extra_nodes=[],
            shared_nodes=[10, 11, 12],
            missing_masteries=[],
            match_percent=60.0,
        )

        skill_delta = SkillDelta(
            missing_gems=["Arc", "Spell Echo"],
            extra_gems=[],
            gem_level_gaps={"Fireball": -5},
            gem_quality_gaps={},
            missing_supports=[],
            match_percent=50.0,
        )

        equipment_delta = EquipmentDelta(
            slot_deltas={
                "Helmet": ItemDelta(
                    slot="Helmet",
                    player_item=None,
                    guide_item=Mock(),
                    is_match=False,
                    missing_unique="Crown of Eyes",
                    upgrade_priority=2,
                ),
                "Boots": ItemDelta(
                    slot="Boots",
                    player_item=None,
                    guide_item=Mock(),
                    is_match=False,
                    missing_unique=None,
                    upgrade_priority=3,
                ),
            },
            missing_uniques=["Crown of Eyes"],
            match_percent=0.0,
        )

        priorities = comparator._generate_priorities(tree_delta, skill_delta, equipment_delta)

        assert len(priorities) <= 10
        # Should include unique first
        assert any("Crown of Eyes" in p for p in priorities)
        # Should include missing gems
        assert any("Arc" in p for p in priorities)
        # Should include passive nodes
        assert any("5 passive nodes" in p for p in priorities)
        # Should include gem level gaps
        assert any("Fireball" in p for p in priorities)

    def test_generate_priorities_many_missing_nodes(self):
        """Many missing nodes should show special message."""
        comparator = BuildComparator()

        tree_delta = TreeDelta(
            missing_nodes=list(range(20)),  # 20 missing nodes
            extra_nodes=[],
            shared_nodes=[],
            missing_masteries=[],
            match_percent=0.0,
        )

        skill_delta = SkillDelta(
            missing_gems=[],
            extra_gems=[],
            gem_level_gaps={},
            gem_quality_gaps={},
            missing_supports=[],
            match_percent=100.0,
        )

        equipment_delta = EquipmentDelta(
            slot_deltas={},
            missing_uniques=[],
            match_percent=100.0,
        )

        priorities = comparator._generate_priorities(tree_delta, skill_delta, equipment_delta)

        # Should say "20 missing" for large count
        assert any("20 missing" in p for p in priorities)


class TestBuildComparatorExtractGems:
    """Tests for _extract_player_gems."""

    def test_extract_player_gems_empty_raw_xml(self):
        """Empty raw_xml should return empty dict."""
        comparator = BuildComparator()
        build = PoBBuild(
            level=90,
            class_name="Witch",
            ascendancy="Elementalist",
            items={},
            raw_xml="",
        )

        gems = comparator._extract_player_gems(build)

        assert gems == {}

    def test_extract_player_gems_with_raw_xml(self):
        """Should extract gems from raw_xml."""
        comparator = BuildComparator()
        raw_xml = """<?xml version="1.0" encoding="utf-8"?>
<PathOfBuilding>
    <Skills>
        <SkillSet id="1" title="Main">
            <Skill enabled="true" slot="Body Armour">
                <Gem nameSpec="Arc" level="20" quality="20" enabled="true"/>
                <Gem nameSpec="Spell Echo" level="18" quality="10" enabled="true"/>
            </Skill>
        </SkillSet>
    </Skills>
</PathOfBuilding>"""

        build = PoBBuild(
            level=90,
            class_name="Witch",
            ascendancy="Elementalist",
            items={},
            raw_xml=raw_xml,
        )

        gems = comparator._extract_player_gems(build)

        assert "Arc" in gems
        assert gems["Arc"]["level"] == 20
        assert "Spell Echo" in gems
        assert gems["Spell Echo"]["level"] == 18

    def test_extract_player_gems_invalid_xml(self):
        """Invalid raw_xml should return empty dict."""
        comparator = BuildComparator()
        build = PoBBuild(
            level=90,
            class_name="Witch",
            ascendancy="Elementalist",
            items={},
            raw_xml="not valid xml",
        )

        gems = comparator._extract_player_gems(build)

        assert gems == {}


class TestDataclasses:
    """Tests for dataclass creation."""

    def test_tree_spec_creation(self):
        """TreeSpec should be creatable with all fields."""
        spec = TreeSpec(
            title="Test",
            raw_title="^1Test",
            tree_version="3_24",
            class_id=1,
            ascend_class_id=2,
            nodes={1, 2, 3},
            mastery_effects=[(100, 1)],
            url="https://test.com",
            inferred_level=90,
        )

        assert spec.title == "Test"
        assert spec.nodes == {1, 2, 3}
        assert spec.inferred_level == 90

    def test_skill_set_spec_creation(self):
        """SkillSetSpec should be creatable."""
        spec = SkillSetSpec(
            id="1",
            title="Test Skills",
            raw_title="Test Skills",
            skills=[{"label": "Main", "gems": []}],
            inferred_level=85,
        )

        assert spec.id == "1"
        assert spec.title == "Test Skills"

    def test_tree_delta_creation(self):
        """TreeDelta should be creatable."""
        delta = TreeDelta(
            missing_nodes=[1, 2],
            extra_nodes=[3],
            shared_nodes=[4, 5],
            missing_masteries=[(100, 1)],
            match_percent=60.0,
        )

        assert delta.missing_nodes == [1, 2]
        assert delta.match_percent == 60.0

    def test_skill_delta_creation(self):
        """SkillDelta should be creatable."""
        delta = SkillDelta(
            missing_gems=["Arc"],
            extra_gems=["Fireball"],
            gem_level_gaps={"Arc": -5},
            gem_quality_gaps={"Arc": -10},
            missing_supports=["Spell Echo"],
            match_percent=50.0,
        )

        assert delta.missing_gems == ["Arc"]
        assert delta.gem_level_gaps["Arc"] == -5

    def test_item_delta_creation(self):
        """ItemDelta should be creatable."""
        delta = ItemDelta(
            slot="Helmet",
            player_item=None,
            guide_item=None,
            is_match=False,
            missing_unique="Crown of Eyes",
            upgrade_priority=2,
        )

        assert delta.slot == "Helmet"
        assert delta.missing_unique == "Crown of Eyes"

    def test_equipment_delta_creation(self):
        """EquipmentDelta should be creatable."""
        delta = EquipmentDelta(
            slot_deltas={},
            missing_uniques=["Crown of Eyes"],
            match_percent=0.0,
        )

        assert delta.missing_uniques == ["Crown of Eyes"]

    def test_build_delta_creation(self):
        """BuildDelta should be creatable."""
        tree = TreeDelta([], [], [], [], 100.0)
        skill = SkillDelta([], [], {}, {}, [], 100.0)
        equip = EquipmentDelta({}, [], 100.0)

        delta = BuildDelta(
            tree_delta=tree,
            skill_delta=skill,
            equipment_delta=equip,
            overall_match_percent=100.0,
            player_level=90,
            guide_level=95,
            progression_stage=ProgressionStage.MID_MAPS,
            priority_upgrades=["Get item X"],
            guide_title="Test Guide",
            guide_spec_title="Endgame",
        )

        assert delta.overall_match_percent == 100.0
        assert delta.player_level == 90
        assert delta.guide_title == "Test Guide"
