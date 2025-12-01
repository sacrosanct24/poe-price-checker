"""
Unit tests for core.build_matcher module - Build requirement matching.

Tests cover:
- Path of Building (PoB) code import and parsing
- Build requirement extraction from PoB XML
- Item-to-build matching algorithm
- Manual build creation
- Build persistence (save/load)
- Build summary and listing
"""

import pytest
import json
import base64
import zlib
from pathlib import Path
from unittest.mock import Mock

from core.build_matcher import BuildMatcher
from core.rare_item_evaluator import AffixMatch

pytestmark = pytest.mark.unit


# -------------------------
# Test Data
# -------------------------

def create_pob_xml(
    build_name="Test Build",
    skills=None,
    items=None
):
    """Create a minimal valid PoB XML string."""
    skills_xml = ""
    if skills:
        gems_xml = ""
        for skill in skills:
            gems_xml += f'<Gem nameSpec="{skill}" enabled="true"/>'
        skills_xml = f'<Skills>{gems_xml}</Skills>'

    items_xml = ""
    if items:
        items_content = ""
        for item in items:
            items_content += f'<Item>{item}</Item>'
        items_xml = f'<Items>{items_content}</Items>'

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build targetVersion="{build_name}"/>
    {skills_xml}
    {items_xml}
</PathOfBuilding>'''

    return xml


def encode_pob_code(xml_string):
    """Encode XML as PoB code (base64 + zlib compression)."""
    compressed = zlib.compress(xml_string.encode('utf-8'))
    encoded = base64.b64encode(compressed).decode('utf-8')
    return encoded


def create_mock_parsed_item(
    name="Test Item",
    rarity="RARE",
    base_type="Hubris Circlet"
):
    """Create a mock ParsedItem."""
    item = Mock()
    item.name = name
    item.rarity = rarity
    item.base_type = base_type
    return item


# -------------------------
# Initialization Tests
# -------------------------

class TestBuildMatcherInitialization:
    """Test build matcher initialization."""

    def test_creates_matcher_with_default_file(self, tmp_path, monkeypatch):
        """Should create matcher with default builds file path."""
        # Use a temp path to avoid loading real builds.json from user home
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        matcher = BuildMatcher()

        expected_path = fake_home / ".poe_price_checker" / "builds.json"
        assert matcher.builds_file == expected_path
        assert matcher.builds == []

    def test_creates_matcher_with_custom_file(self, tmp_path):
        """Should accept custom builds file path."""
        custom_file = tmp_path / "custom_builds.json"

        matcher = BuildMatcher(builds_file=custom_file)

        assert matcher.builds_file == custom_file

    def test_loads_existing_builds_on_init(self, tmp_path):
        """Should load existing builds from file on initialization."""
        builds_file = tmp_path / "builds.json"

        # Create builds file
        builds_data = {
            "builds": [
                {
                    "build_name": "Saved Build",
                    "source": "manual",
                    "required_life": 4000,
                    "required_es": 0,
                    "required_resistances": {},
                    "required_attributes": {},
                    "desired_affixes": ["Movement Speed"],
                    "key_uniques": [],
                    "main_skills": [],
                    "priority_slots": {}
                }
            ]
        }

        with open(builds_file, 'w') as f:
            json.dump(builds_data, f)

        matcher = BuildMatcher(builds_file=builds_file)

        assert len(matcher.builds) == 1
        assert matcher.builds[0].build_name == "Saved Build"
        assert matcher.builds[0].required_life == 4000

    def test_handles_missing_builds_file(self, tmp_path):
        """Should handle missing builds file gracefully."""
        builds_file = tmp_path / "nonexistent.json"

        matcher = BuildMatcher(builds_file=builds_file)

        assert matcher.builds == []

    def test_handles_corrupted_builds_file(self, tmp_path):
        """Should handle corrupted builds file gracefully."""
        builds_file = tmp_path / "corrupted.json"

        with open(builds_file, 'w') as f:
            f.write("invalid json {")

        matcher = BuildMatcher(builds_file=builds_file)

        assert matcher.builds == []


# -------------------------
# PoB Code Import Tests
# -------------------------

class TestPoBCodeImport:
    """Test Path of Building code import and parsing."""

    def test_imports_valid_pob_code(self, tmp_path):
        """Should successfully import valid PoB code."""
        xml = create_pob_xml(build_name="Lightning Strike Build")
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        build = matcher.import_pob_code(pob_code, build_name="Lightning Strike")

        assert build is not None
        assert build.build_name == "Lightning Strike"
        assert build.source == "pob"
        assert len(matcher.builds) == 1

    def test_extracts_skills_from_pob_xml(self, tmp_path):
        """Should extract skill gems from PoB XML."""
        xml = create_pob_xml(
            build_name="Test Build",
            skills=["Lightning Strike", "Multistrike Support", "Elemental Damage with Attacks Support"]
        )
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        build = matcher.import_pob_code(pob_code)

        assert "Lightning Strike" in build.main_skills
        assert "Multistrike Support" in build.main_skills
        assert len(build.main_skills) == 3

    def test_extracts_unique_items_from_pob(self, tmp_path):
        """Should extract unique items from PoB XML."""
        unique_item1 = "Rarity: UNIQUE\nPerseverance\nVanguard Belt"
        unique_item2 = "Rarity: UNIQUE\nThread of Hope\nCrimson Jewel"

        xml = create_pob_xml(
            build_name="Test Build",
            items=[unique_item1, unique_item2]
        )
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        build = matcher.import_pob_code(pob_code)

        assert "Perseverance" in build.key_uniques
        assert "Thread of Hope" in build.key_uniques

    def test_uses_provided_build_name(self, tmp_path):
        """Should use provided build name instead of extracting."""
        xml = create_pob_xml(build_name="Auto Name")
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        build = matcher.import_pob_code(pob_code, build_name="Custom Name")

        assert build.build_name == "Custom Name"

    def test_handles_invalid_pob_code(self, tmp_path):
        """Should raise error for invalid PoB code."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        with pytest.raises(ValueError, match="Failed to parse PoB code"):
            matcher.import_pob_code("invalid_base64_string")

    def test_handles_malformed_xml(self, tmp_path):
        """Should raise error for malformed XML in PoB code."""
        invalid_xml = "not xml"
        compressed = zlib.compress(invalid_xml.encode('utf-8'))
        pob_code = base64.b64encode(compressed).decode('utf-8')

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        with pytest.raises(ValueError, match="Failed to parse PoB code"):
            matcher.import_pob_code(pob_code)

    def test_saves_imported_build(self, tmp_path):
        """Imported build should be saved to file."""
        builds_file = tmp_path / "builds.json"
        xml = create_pob_xml(build_name="Test Build")
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=builds_file)
        matcher.import_pob_code(pob_code, build_name="Test Build")

        # Verify file was created and contains build
        assert builds_file.exists()
        with open(builds_file) as f:
            data = json.load(f)

        assert len(data["builds"]) == 1
        assert data["builds"][0]["build_name"] == "Test Build"


# -------------------------
# Manual Build Creation Tests
# -------------------------

class TestManualBuildCreation:
    """Test manually creating build requirements."""

    def test_creates_manual_build(self, tmp_path):
        """Should create build with manual requirements."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        build = matcher.add_manual_build(
            build_name="Lightning Strike Raider",
            required_life=4000,
            required_es=0,
            resistances={"fire": 75, "cold": 75, "lightning": 75},
            desired_affixes=["Movement Speed", "Attack Speed"],
            key_uniques=["Perseverance"]
        )

        assert build.build_name == "Lightning Strike Raider"
        assert build.source == "manual"
        assert build.required_life == 4000
        assert build.required_resistances["fire"] == 75
        assert "Movement Speed" in build.desired_affixes
        assert "Perseverance" in build.key_uniques

    def test_manual_build_added_to_list(self, tmp_path):
        """Manual build should be added to builds list."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        matcher.add_manual_build(
            build_name="Test Build",
            required_life=3000
        )

        assert len(matcher.builds) == 1
        assert matcher.builds[0].build_name == "Test Build"

    def test_manual_build_saves_to_file(self, tmp_path):
        """Manual build should be saved to file."""
        builds_file = tmp_path / "builds.json"
        matcher = BuildMatcher(builds_file=builds_file)

        matcher.add_manual_build(
            build_name="Test Build",
            required_life=3000
        )

        assert builds_file.exists()
        with open(builds_file) as f:
            data = json.load(f)

        assert len(data["builds"]) == 1
        assert data["builds"][0]["required_life"] == 3000

    def test_manual_build_with_defaults(self, tmp_path):
        """Should handle missing optional parameters with defaults."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        build = matcher.add_manual_build(build_name="Minimal Build")

        assert build.required_life == 0
        assert build.required_es == 0
        assert build.required_resistances == {}
        assert build.desired_affixes == []
        assert build.key_uniques == []


# -------------------------
# Build Persistence Tests
# -------------------------

class TestBuildPersistence:
    """Test saving and loading builds."""

    def test_saves_multiple_builds(self, tmp_path):
        """Should save multiple builds to file."""
        builds_file = tmp_path / "builds.json"
        matcher = BuildMatcher(builds_file=builds_file)

        matcher.add_manual_build("Build 1", required_life=3000)
        matcher.add_manual_build("Build 2", required_life=4000)

        # Reload from file
        matcher2 = BuildMatcher(builds_file=builds_file)

        assert len(matcher2.builds) == 2
        assert matcher2.builds[0].build_name == "Build 1"
        assert matcher2.builds[1].build_name == "Build 2"

    def test_creates_parent_directory(self, tmp_path):
        """Should create parent directory when saving."""
        builds_file = tmp_path / "subdir" / "nested" / "builds.json"
        matcher = BuildMatcher(builds_file=builds_file)

        matcher.add_manual_build("Test Build")

        assert builds_file.exists()
        assert builds_file.parent.exists()

    def test_load_clears_existing_builds(self, tmp_path):
        """Loading builds should clear existing builds to avoid duplicates."""
        builds_file = tmp_path / "builds.json"

        # Create initial builds
        matcher1 = BuildMatcher(builds_file=builds_file)
        matcher1.add_manual_build("Build 1")

        # Create new instance and add another build
        matcher2 = BuildMatcher(builds_file=builds_file)
        matcher2.add_manual_build("Build 2")

        # Should have 2 builds, not 3
        matcher3 = BuildMatcher(builds_file=builds_file)
        assert len(matcher3.builds) == 2


# -------------------------
# Item Matching Tests
# -------------------------

class TestItemMatching:
    """Test matching items to build requirements."""

    def test_matches_key_unique(self, tmp_path):
        """Should match key unique items."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Test Build",
            key_uniques=["Perseverance", "Thread of Hope"]
        )

        item = create_mock_parsed_item(name="Perseverance", rarity="UNIQUE")
        affix_matches = []

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["build_name"] == "Test Build"
        assert matches[0]["score"] == 100
        assert "Perseverance" in matches[0]["matched_requirements"][0]

    def test_matches_life_requirement(self, tmp_path):
        """Should match life requirements."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Test Build",
            required_life=100
        )

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False)
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["score"] == 20
        assert "Life" in matches[0]["matched_requirements"][0]

    def test_matches_es_requirement(self, tmp_path):
        """Should match energy shield requirements."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "CI Build",
            required_es=100
        )

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("energy_shield", "", "", 110, 9, "tier1", False)
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["score"] == 20
        assert "ES" in matches[0]["matched_requirements"][0]

    def test_matches_resistance_requirement(self, tmp_path):
        """Should match resistance requirements."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Test Build",
            resistances={"fire": 75, "cold": 75}
        )

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("resistances", "", "+47% to Fire Resistance", 47, 8, "tier1", False)
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["score"] == 10
        assert "fire" in matches[0]["matched_requirements"][0].lower()

    def test_matches_desired_affixes(self, tmp_path):
        """Should match desired affixes."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Test Build",
            desired_affixes=["Movement Speed", "Attack Speed"]
        )

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("movement_speed", "", "30% increased Movement Speed", 30, 9, "tier1", False)
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["score"] == 15
        assert "Movement Speed" in matches[0]["matched_requirements"][0]

    def test_no_match_without_requirements(self, tmp_path):
        """Should not match if item doesn't meet requirements."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Test Build",
            required_life=100
        )

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = []  # No affixes

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 0

    def test_matches_multiple_builds(self, tmp_path):
        """Should match against multiple builds."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build("Build 1", required_life=100)
        matcher.add_manual_build("Build 2", required_es=100)

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False),
            AffixMatch("energy_shield", "", "", 110, 9, "tier1", False)
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 2
        build_names = [m["build_name"] for m in matches]
        assert "Build 1" in build_names
        assert "Build 2" in build_names

    def test_matches_sorted_by_score(self, tmp_path):
        """Matches should be sorted by score descending."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build("Low Score Build", required_life=100)
        matcher.add_manual_build(
            "High Score Build",
            key_uniques=["Test Item"]
        )

        item = create_mock_parsed_item(name="Test Item", rarity="UNIQUE")
        affix_matches = []

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["build_name"] == "High Score Build"
        assert matches[0]["score"] == 100

    def test_life_match_accepts_70_percent_of_requirement(self, tmp_path):
        """Should accept life that's 70% of requirement."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build("Test Build", required_life=100)

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("life", "", "", 70, 6, "tier3", False)  # Exactly 70%
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        assert len(matches) == 1
        assert matches[0]["score"] > 0

    def test_life_match_rejects_below_70_percent(self, tmp_path):
        """Should reject life below 70% of requirement."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build("Test Build", required_life=100)

        item = create_mock_parsed_item(rarity="RARE")
        affix_matches = [
            AffixMatch("life", "", "", 50, 5, "tier3", False)  # Only 50%
        ]

        matches = matcher.match_item_to_builds(item, affix_matches)

        # Should match but with 0 score for life
        if len(matches) > 0:
            assert matches[0]["score"] == 0


# -------------------------
# Build Summary Tests
# -------------------------

class TestBuildSummary:
    """Test build summary generation."""

    def test_gets_build_summary(self, tmp_path):
        """Should generate summary for build."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build(
            "Lightning Strike Raider",
            required_life=4000,
            required_es=0,
            resistances={"fire": 75, "cold": 75},
            desired_affixes=["Movement Speed"],
            key_uniques=["Perseverance"]
        )

        summary = matcher.get_build_summary("Lightning Strike Raider")

        assert summary is not None
        assert "Lightning Strike Raider" in summary
        assert "manual" in summary
        assert "4000" in summary
        assert "Fire: 75" in summary
        assert "Movement Speed" in summary
        assert "Perseverance" in summary

    def test_returns_none_for_unknown_build(self, tmp_path):
        """Should return None for non-existent build."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        summary = matcher.get_build_summary("Nonexistent Build")

        assert summary is None

    def test_summary_includes_main_skills(self, tmp_path):
        """Summary should include main skills."""
        xml = create_pob_xml(
            build_name="Test",
            skills=["Lightning Strike", "Multistrike", "Elemental Damage"]
        )
        pob_code = encode_pob_code(xml)

        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.import_pob_code(pob_code, build_name="Test Build")

        summary = matcher.get_build_summary("Test Build")

        assert "Lightning Strike" in summary


# -------------------------
# Build Listing Tests
# -------------------------

class TestBuildListing:
    """Test listing all builds."""

    def test_lists_all_build_names(self, tmp_path):
        """Should return list of all build names."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")
        matcher.add_manual_build("Build A")
        matcher.add_manual_build("Build B")
        matcher.add_manual_build("Build C")

        build_names = matcher.list_builds()

        assert len(build_names) == 3
        assert "Build A" in build_names
        assert "Build B" in build_names
        assert "Build C" in build_names

    def test_returns_empty_list_when_no_builds(self, tmp_path):
        """Should return empty list when no builds exist."""
        matcher = BuildMatcher(builds_file=tmp_path / "builds.json")

        build_names = matcher.list_builds()

        assert build_names == []
