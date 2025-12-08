"""Tests for core/pob_local_scanner.py - Local Path of Building scanner."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from core.pob_local_scanner import (
    LocalBuildInfo,
    PoBLocalScanner,
    get_pob_scanner,
    reset_scanner,
)


# =============================================================================
# LocalBuildInfo Tests
# =============================================================================


class TestLocalBuildInfo:
    """Tests for LocalBuildInfo dataclass."""

    @pytest.fixture
    def sample_build_info(self, tmp_path):
        """Create a sample build info."""
        return LocalBuildInfo(
            file_path=tmp_path / "TestBuild.xml",
            file_name="TestBuild.xml",
            last_modified=datetime(2024, 1, 15, 12, 0, 0),
            size_bytes=1024,
        )

    def test_create_build_info(self, sample_build_info):
        """Should create build info with required fields."""
        assert sample_build_info.file_name == "TestBuild.xml"
        assert sample_build_info.size_bytes == 1024
        assert sample_build_info.last_modified.year == 2024

    def test_display_name_uses_filename_when_no_build_name(self, sample_build_info):
        """display_name should use filename without .xml extension."""
        assert sample_build_info.display_name == "TestBuild"

    def test_display_name_uses_build_name_when_set(self, sample_build_info):
        """display_name should prefer build name over filename."""
        sample_build_info._build_name = "My Cyclone Build"
        assert sample_build_info.display_name == "My Cyclone Build"

    def test_summary_when_not_loaded(self, sample_build_info):
        """summary should indicate not loaded."""
        assert "not loaded" in sample_build_info.summary

    def test_summary_with_level(self, sample_build_info):
        """summary should include level."""
        sample_build_info._is_loaded = True
        sample_build_info._level = 95
        assert "Lv95" in sample_build_info.summary

    def test_summary_with_ascendancy(self, sample_build_info):
        """summary should include ascendancy."""
        sample_build_info._is_loaded = True
        sample_build_info._ascendancy = "Champion"
        assert "Champion" in sample_build_info.summary

    def test_summary_with_class_when_no_ascendancy(self, sample_build_info):
        """summary should use class when no ascendancy."""
        sample_build_info._is_loaded = True
        sample_build_info._class_name = "Duelist"
        assert "Duelist" in sample_build_info.summary

    def test_summary_prefers_ascendancy_over_class(self, sample_build_info):
        """summary should prefer ascendancy over base class."""
        sample_build_info._is_loaded = True
        sample_build_info._class_name = "Duelist"
        sample_build_info._ascendancy = "Slayer"
        assert "Slayer" in sample_build_info.summary
        assert "Duelist" not in sample_build_info.summary

    def test_summary_with_main_skill(self, sample_build_info):
        """summary should include main skill."""
        sample_build_info._is_loaded = True
        sample_build_info._main_skill = "Cyclone"
        assert "Cyclone" in sample_build_info.summary

    def test_summary_combined(self, sample_build_info):
        """summary should combine multiple elements."""
        sample_build_info._is_loaded = True
        sample_build_info._level = 100
        sample_build_info._ascendancy = "Champion"
        sample_build_info._main_skill = "Lacerate"
        summary = sample_build_info.summary
        assert "Lv100" in summary
        assert "Champion" in summary
        assert "Lacerate" in summary

    def test_summary_defaults_to_display_name(self, sample_build_info):
        """summary should fall back to display name if no metadata."""
        sample_build_info._is_loaded = True
        # No level, class, ascendancy, or skill set
        assert sample_build_info.summary == sample_build_info.display_name


# =============================================================================
# PoBLocalScanner Initialization Tests
# =============================================================================


class TestPoBLocalScannerInit:
    """Tests for PoBLocalScanner initialization."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    def test_init_with_custom_path(self, tmp_path):
        """Should accept custom builds path."""
        scanner = PoBLocalScanner(custom_path=tmp_path)
        assert scanner._custom_path == tmp_path

    def test_init_without_custom_path(self):
        """Should initialize without custom path."""
        scanner = PoBLocalScanner()
        assert scanner._custom_path is None

    def test_initial_state(self):
        """Should have empty initial state."""
        scanner = PoBLocalScanner()
        assert scanner._cached_builds == []
        assert scanner._last_scan is None


# =============================================================================
# PoBLocalScanner Path Detection Tests
# =============================================================================


class TestPoBLocalScannerPathDetection:
    """Tests for builds folder path detection."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    def test_builds_path_uses_custom_path(self, tmp_path):
        """Should use custom path if provided and exists."""
        builds_folder = tmp_path / "CustomBuilds"
        builds_folder.mkdir()

        scanner = PoBLocalScanner(custom_path=builds_folder)
        assert scanner.builds_path == builds_folder

    def test_builds_path_tries_default_paths(self, tmp_path):
        """Should try default paths when no custom path."""
        with patch.object(PoBLocalScanner, "DEFAULT_PATHS", [tmp_path]):
            scanner = PoBLocalScanner()
            assert scanner.builds_path == tmp_path

    def test_builds_path_returns_none_when_not_found(self):
        """Should return None when no valid path found."""
        fake_paths = [Path("/nonexistent/path1"), Path("/nonexistent/path2")]
        with patch.object(PoBLocalScanner, "DEFAULT_PATHS", fake_paths):
            scanner = PoBLocalScanner()
            # When all paths don't exist, returns None
            assert scanner.builds_path is None or not scanner.builds_path.exists()

    def test_builds_path_caches_result(self, tmp_path):
        """Should cache detected path."""
        with patch.object(PoBLocalScanner, "DEFAULT_PATHS", [tmp_path]):
            scanner = PoBLocalScanner()
            path1 = scanner.builds_path
            path2 = scanner.builds_path
            assert path1 is path2  # Same cached instance


# =============================================================================
# PoBLocalScanner Scanning Tests
# =============================================================================


class TestPoBLocalScannerScan:
    """Tests for build scanning functionality."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    @pytest.fixture
    def scanner_with_builds(self, tmp_path):
        """Create scanner with test builds."""
        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()

        # Create some test XML files
        (builds_folder / "build1.xml").write_text("<PathOfBuilding/>")
        (builds_folder / "build2.xml").write_text("<PathOfBuilding/>")
        (builds_folder / "readme.txt").write_text("Not a build")

        return PoBLocalScanner(custom_path=builds_folder)

    def test_scan_builds_finds_xml_files(self, scanner_with_builds):
        """Should find XML files in builds folder."""
        builds = scanner_with_builds.scan_builds()
        assert len(builds) == 2
        assert all(b.file_name.endswith(".xml") for b in builds)

    def test_scan_builds_excludes_non_xml(self, scanner_with_builds):
        """Should ignore non-XML files."""
        builds = scanner_with_builds.scan_builds()
        assert not any(b.file_name == "readme.txt" for b in builds)

    def test_scan_builds_caches_results(self, scanner_with_builds):
        """Should cache scan results."""
        builds1 = scanner_with_builds.scan_builds()
        builds2 = scanner_with_builds.scan_builds()
        assert builds1 is builds2  # Same cached list

    def test_scan_builds_force_refresh(self, scanner_with_builds):
        """Should rescan when force_refresh is True."""
        builds1 = scanner_with_builds.scan_builds()
        builds2 = scanner_with_builds.scan_builds(force_refresh=True)
        assert builds1 is not builds2  # Different list

    def test_scan_builds_returns_empty_when_no_path(self):
        """Should return empty list when no builds path."""
        scanner = PoBLocalScanner(custom_path=Path("/nonexistent"))
        builds = scanner.scan_builds()
        assert builds == []

    def test_scan_builds_sorted_by_modified_time(self, tmp_path):
        """Builds should be sorted newest first."""
        import time

        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()

        # Create files with different modification times
        (builds_folder / "old.xml").write_text("<PathOfBuilding/>")
        time.sleep(0.1)
        (builds_folder / "new.xml").write_text("<PathOfBuilding/>")

        scanner = PoBLocalScanner(custom_path=builds_folder)
        builds = scanner.scan_builds()

        # Newest should be first
        assert builds[0].file_name == "new.xml"
        assert builds[1].file_name == "old.xml"

    def test_scan_builds_recursive(self, tmp_path):
        """Should scan subdirectories."""
        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()
        subfolder = builds_folder / "SubFolder"
        subfolder.mkdir()

        (builds_folder / "root.xml").write_text("<PathOfBuilding/>")
        (subfolder / "nested.xml").write_text("<PathOfBuilding/>")

        scanner = PoBLocalScanner(custom_path=builds_folder)
        builds = scanner.scan_builds()

        assert len(builds) == 2
        assert any(b.file_name == "root.xml" for b in builds)
        assert any(b.file_name == "nested.xml" for b in builds)


# =============================================================================
# PoBLocalScanner Metadata Loading Tests
# =============================================================================


class TestPoBLocalScannerMetadata:
    """Tests for metadata loading."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    @pytest.fixture
    def build_with_metadata(self, tmp_path):
        """Create build file with metadata."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
    <Build
        className="Marauder"
        ascendClassName="Berserker"
        level="92"
        mainSocketGroup="Cyclone">
    </Build>
</PathOfBuilding>"""

        build_file = tmp_path / "TestBuild.xml"
        build_file.write_text(xml_content)

        return LocalBuildInfo(
            file_path=build_file,
            file_name="TestBuild.xml",
            last_modified=datetime.now(),
            size_bytes=len(xml_content),
        )

    def test_load_build_metadata(self, build_with_metadata, tmp_path):
        """Should load metadata from XML."""
        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.load_build_metadata(build_with_metadata)

        assert result is True
        assert build_with_metadata._is_loaded is True
        assert build_with_metadata._class_name == "Marauder"
        assert build_with_metadata._ascendancy == "Berserker"
        assert build_with_metadata._level == 92
        assert build_with_metadata._main_skill == "Cyclone"

    def test_load_build_metadata_skips_if_loaded(self, build_with_metadata, tmp_path):
        """Should skip loading if already loaded."""
        build_with_metadata._is_loaded = True
        build_with_metadata._class_name = "Existing"

        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.load_build_metadata(build_with_metadata)

        assert result is True
        assert build_with_metadata._class_name == "Existing"

    def test_load_build_metadata_handles_missing_file(self, tmp_path):
        """Should handle missing file gracefully."""
        build_info = LocalBuildInfo(
            file_path=tmp_path / "missing.xml",
            file_name="missing.xml",
            last_modified=datetime.now(),
            size_bytes=0,
        )

        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.load_build_metadata(build_info)

        assert result is False
        assert build_info._is_loaded is False

    def test_load_build_metadata_handles_malformed_xml(self, tmp_path):
        """Should handle malformed XML gracefully."""
        build_file = tmp_path / "bad.xml"
        build_file.write_text("not valid xml <><><>")

        build_info = LocalBuildInfo(
            file_path=build_file,
            file_name="bad.xml",
            last_modified=datetime.now(),
            size_bytes=20,
        )

        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.load_build_metadata(build_info)

        assert result is False


# =============================================================================
# PoBLocalScanner Utility Methods Tests
# =============================================================================


class TestPoBLocalScannerUtility:
    """Tests for utility methods."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    def test_get_build_xml(self, tmp_path):
        """Should read XML content from file."""
        xml_content = "<PathOfBuilding>Test Content</PathOfBuilding>"
        build_file = tmp_path / "build.xml"
        build_file.write_text(xml_content)

        build_info = LocalBuildInfo(
            file_path=build_file,
            file_name="build.xml",
            last_modified=datetime.now(),
            size_bytes=len(xml_content),
        )

        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.get_build_xml(build_info)

        assert result == xml_content

    def test_get_build_xml_returns_none_for_missing(self, tmp_path):
        """Should return None for missing file."""
        build_info = LocalBuildInfo(
            file_path=tmp_path / "missing.xml",
            file_name="missing.xml",
            last_modified=datetime.now(),
            size_bytes=0,
        )

        scanner = PoBLocalScanner(custom_path=tmp_path)
        result = scanner.get_build_xml(build_info)

        assert result is None

    def test_get_recent_builds(self, tmp_path):
        """Should return limited number of recent builds."""
        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()

        # Create multiple build files
        for i in range(15):
            (builds_folder / f"build{i}.xml").write_text("<PathOfBuilding/>")

        scanner = PoBLocalScanner(custom_path=builds_folder)
        recent = scanner.get_recent_builds(limit=5)

        assert len(recent) == 5

    def test_load_all_metadata(self, tmp_path):
        """Should load metadata for all builds."""
        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()

        xml = """<PathOfBuilding><Build className="Test" level="1"/></PathOfBuilding>"""
        (builds_folder / "build1.xml").write_text(xml)
        (builds_folder / "build2.xml").write_text(xml)

        scanner = PoBLocalScanner(custom_path=builds_folder)
        loaded = scanner.load_all_metadata()

        assert loaded == 2


# =============================================================================
# PoBLocalScanner Search Tests
# =============================================================================


class TestPoBLocalScannerSearch:
    """Tests for search functionality."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    @pytest.fixture
    def scanner_with_varied_builds(self, tmp_path):
        """Create scanner with builds of different types."""
        builds_folder = tmp_path / "Builds"
        builds_folder.mkdir()

        builds = [
            ("CycloneBerserker.xml", "Marauder", "Berserker", "Cyclone"),
            ("LacerateChampion.xml", "Duelist", "Champion", "Lacerate"),
            ("FrostboltOccultist.xml", "Witch", "Occultist", "Frostbolt"),
        ]

        for filename, class_name, ascendancy, skill in builds:
            xml = f"""<PathOfBuilding>
                <Build className="{class_name}" ascendClassName="{ascendancy}"
                       level="90" mainSocketGroup="{skill}"/>
            </PathOfBuilding>"""
            (builds_folder / filename).write_text(xml)

        return PoBLocalScanner(custom_path=builds_folder)

    def test_search_by_filename(self, scanner_with_varied_builds):
        """Should find builds by filename."""
        results = scanner_with_varied_builds.search_builds("Cyclone")
        assert len(results) >= 1
        assert any("Cyclone" in b.file_name for b in results)

    def test_search_by_class(self, scanner_with_varied_builds):
        """Should find builds by class name."""
        results = scanner_with_varied_builds.search_builds("Marauder")
        assert len(results) >= 1
        # After loading metadata, should match class
        for b in results:
            scanner_with_varied_builds.load_build_metadata(b)
            assert b._class_name == "Marauder" or "Marauder" in b.display_name.lower()

    def test_search_by_ascendancy(self, scanner_with_varied_builds):
        """Should find builds by ascendancy."""
        results = scanner_with_varied_builds.search_builds("Champion")
        assert len(results) >= 1

    def test_search_case_insensitive(self, scanner_with_varied_builds):
        """Search should be case insensitive."""
        results1 = scanner_with_varied_builds.search_builds("CHAMPION")
        results2 = scanner_with_varied_builds.search_builds("champion")
        # Both should find the Champion build
        assert len(results1) == len(results2)

    def test_search_no_results(self, scanner_with_varied_builds):
        """Should return empty list for no matches."""
        results = scanner_with_varied_builds.search_builds("NonexistentBuild")
        assert results == []


# =============================================================================
# Singleton Functions Tests
# =============================================================================


class TestSingletonFunctions:
    """Tests for singleton management functions."""

    def teardown_method(self):
        """Reset singleton after each test."""
        reset_scanner()

    def test_get_pob_scanner_returns_singleton(self):
        """Should return same instance on multiple calls."""
        scanner1 = get_pob_scanner()
        scanner2 = get_pob_scanner()
        assert scanner1 is scanner2

    def test_get_pob_scanner_with_custom_path_creates_new(self, tmp_path):
        """Should create new scanner when custom path provided."""
        scanner1 = get_pob_scanner()
        scanner2 = get_pob_scanner(custom_path=tmp_path)
        assert scanner1 is not scanner2

    def test_reset_scanner_clears_singleton(self):
        """reset_scanner should clear the singleton."""
        scanner1 = get_pob_scanner()
        reset_scanner()
        scanner2 = get_pob_scanner()
        assert scanner1 is not scanner2
