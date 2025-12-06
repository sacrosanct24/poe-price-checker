"""
Local Path of Building build scanner.

Scans the local PoB installation for saved builds and provides
access to build data for AI context integration.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Use defusedxml for security
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class LocalBuildInfo:
    """Metadata about a locally saved PoB build."""

    file_path: Path
    file_name: str
    last_modified: datetime
    size_bytes: int

    # Parsed from XML (lazy loaded)
    _build_name: Optional[str] = None
    _class_name: Optional[str] = None
    _ascendancy: Optional[str] = None
    _level: Optional[int] = None
    _main_skill: Optional[str] = None
    _is_loaded: bool = False

    @property
    def display_name(self) -> str:
        """Get display name (build name or filename)."""
        if self._build_name:
            return self._build_name
        return self.file_name.replace(".xml", "")

    @property
    def summary(self) -> str:
        """Get a short summary of the build."""
        if not self._is_loaded:
            return f"{self.display_name} (not loaded)"

        parts = []
        if self._level:
            parts.append(f"Lv{self._level}")
        if self._ascendancy:
            parts.append(self._ascendancy)
        elif self._class_name:
            parts.append(self._class_name)
        if self._main_skill:
            parts.append(self._main_skill)

        return " ".join(parts) if parts else self.display_name


class PoBLocalScanner:
    """
    Scans local Path of Building installation for saved builds.

    Default location: %UserProfile%/Documents/Path of Building/Builds/
    """

    # Common PoB installation paths
    DEFAULT_PATHS = [
        Path.home() / "Documents" / "Path of Building" / "Builds",
        Path.home() / "Documents" / "Path of Building Community" / "Builds",
        Path(os.environ.get("APPDATA", "")) / "Path of Building" / "Builds",
    ]

    def __init__(self, custom_path: Optional[Path] = None):
        """
        Initialize the scanner.

        Args:
            custom_path: Custom path to PoB builds folder.
        """
        self._custom_path = custom_path
        self._builds_path: Optional[Path] = None
        self._cached_builds: List[LocalBuildInfo] = []
        self._last_scan: Optional[datetime] = None

    @property
    def builds_path(self) -> Optional[Path]:
        """Get the detected PoB builds folder path."""
        if self._builds_path is None:
            self._builds_path = self._find_builds_folder()
        return self._builds_path

    def _find_builds_folder(self) -> Optional[Path]:
        """Find the PoB builds folder."""
        # Try custom path first
        if self._custom_path and self._custom_path.exists():
            logger.info(f"Using custom PoB builds path: {self._custom_path}")
            return self._custom_path

        # Try default paths
        for path in self.DEFAULT_PATHS:
            if path.exists() and path.is_dir():
                logger.info(f"Found PoB builds folder: {path}")
                return path

        logger.warning("Could not find PoB builds folder")
        return None

    def scan_builds(self, force_refresh: bool = False) -> List[LocalBuildInfo]:
        """
        Scan for local PoB builds.

        Args:
            force_refresh: Force rescan even if cached.

        Returns:
            List of LocalBuildInfo for each found build.
        """
        if not force_refresh and self._cached_builds:
            return self._cached_builds

        builds = []
        path = self.builds_path

        if not path:
            return builds

        try:
            # Scan for XML files recursively
            for xml_file in path.rglob("*.xml"):
                try:
                    stat = xml_file.stat()
                    build_info = LocalBuildInfo(
                        file_path=xml_file,
                        file_name=xml_file.name,
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        size_bytes=stat.st_size,
                    )
                    builds.append(build_info)
                except OSError as e:
                    logger.debug(f"Could not stat {xml_file}: {e}")

            # Sort by last modified (newest first)
            builds.sort(key=lambda b: b.last_modified, reverse=True)

            logger.info(f"Found {len(builds)} local PoB builds")
            self._cached_builds = builds
            self._last_scan = datetime.now()

        except Exception as e:
            logger.error(f"Error scanning builds folder: {e}")

        return builds

    def load_build_metadata(self, build_info: LocalBuildInfo) -> bool:
        """
        Load basic metadata from a build file without full parsing.

        Args:
            build_info: The build info to populate.

        Returns:
            True if successful.
        """
        if build_info._is_loaded:
            return True

        try:
            # Parse just enough to get build metadata
            tree = ET.parse(str(build_info.file_path))
            root = tree.getroot()

            # Get build element
            build_elem = root.find("Build")
            if build_elem is not None:
                build_info._class_name = build_elem.get("className", "")
                build_info._ascendancy = build_elem.get("ascendClassName", "")
                build_info._level = int(build_elem.get("level", 1))
                build_info._main_skill = build_elem.get("mainSocketGroup", "")

            # Try to get build name from PathOfBuilding element
            pob_elem = root.find(".")
            if pob_elem is not None:
                # Some builds have a buildName attribute
                build_info._build_name = pob_elem.get("buildName", "")

            build_info._is_loaded = True
            return True

        except Exception as e:
            logger.debug(f"Could not load build metadata from {build_info.file_path}: {e}")
            return False

    def load_all_metadata(self) -> int:
        """
        Load metadata for all scanned builds.

        Returns:
            Number of builds successfully loaded.
        """
        builds = self.scan_builds()
        loaded = 0

        for build in builds:
            if self.load_build_metadata(build):
                loaded += 1

        return loaded

    def get_build_xml(self, build_info: LocalBuildInfo) -> Optional[str]:
        """
        Get the raw XML content of a build.

        Args:
            build_info: The build to read.

        Returns:
            XML string or None on error.
        """
        try:
            return build_info.file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Could not read build file {build_info.file_path}: {e}")
            return None

    def get_recent_builds(self, limit: int = 10) -> List[LocalBuildInfo]:
        """
        Get the most recently modified builds.

        Args:
            limit: Maximum number of builds to return.

        Returns:
            List of recent builds.
        """
        builds = self.scan_builds()
        return builds[:limit]

    def search_builds(self, query: str) -> List[LocalBuildInfo]:
        """
        Search builds by name, class, or skill.

        Args:
            query: Search string.

        Returns:
            Matching builds.
        """
        query_lower = query.lower()
        builds = self.scan_builds()
        results = []

        for build in builds:
            # Load metadata if not already loaded
            self.load_build_metadata(build)

            # Search in various fields
            if (
                query_lower in build.display_name.lower()
                or (build._class_name and query_lower in build._class_name.lower())
                or (build._ascendancy and query_lower in build._ascendancy.lower())
                or (build._main_skill and query_lower in build._main_skill.lower())
            ):
                results.append(build)

        return results

    def import_to_app(self, build_info: LocalBuildInfo) -> Optional[Dict[str, Any]]:
        """
        Import a local build for use in the app.

        Args:
            build_info: The build to import.

        Returns:
            Dict with build data suitable for CharacterManager.
        """
        from core.pob_integration import PoBDecoder

        xml_content = self.get_build_xml(build_info)
        if not xml_content:
            return None

        try:
            build = PoBDecoder.parse_build(xml_content)

            return {
                "name": build_info.display_name,
                "build": build,
                "source": "local",
                "file_path": str(build_info.file_path),
                "last_modified": build_info.last_modified.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to parse local build {build_info.file_path}: {e}")
            return None


# Singleton instance
_scanner: Optional[PoBLocalScanner] = None


def get_pob_scanner(custom_path: Optional[Path] = None) -> PoBLocalScanner:
    """Get the singleton PoB scanner instance."""
    global _scanner
    if _scanner is None or custom_path:
        _scanner = PoBLocalScanner(custom_path)
    return _scanner


def reset_scanner() -> None:
    """Reset the singleton scanner (for testing)."""
    global _scanner
    _scanner = None


# CLI for testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    scanner = get_pob_scanner()

    if scanner.builds_path:
        print(f"PoB Builds folder: {scanner.builds_path}")

        builds = scanner.scan_builds()
        print(f"\nFound {len(builds)} builds:")

        for i, build in enumerate(builds[:20]):  # Show first 20
            scanner.load_build_metadata(build)
            print(f"  {i+1}. {build.display_name}")
            print(f"      {build.summary}")
            print(f"      Modified: {build.last_modified}")
            print()

        if len(sys.argv) > 1:
            query = sys.argv[1]
            print(f"\nSearching for '{query}':")
            results = scanner.search_builds(query)
            for build in results:
                print(f"  - {build.display_name}: {build.summary}")
    else:
        print("Could not find PoB builds folder")
        print("Checked paths:")
        for p in PoBLocalScanner.DEFAULT_PATHS:
            print(f"  - {p}")
