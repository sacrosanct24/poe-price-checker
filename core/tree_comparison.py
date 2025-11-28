"""
Tree Comparison Service.

Provides simplified access to tree comparison functionality for the UI.
Leverages the existing BuildComparison module for tree parsing and comparison.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from core.build_comparison import (
    GuideBuildParser,
    BuildComparator,
    TreeSpec,
    TreeDelta,
)
from core.pob_integration import PoBBuild, PoBDecoder, CharacterManager

logger = logging.getLogger(__name__)


@dataclass
class TreeComparisonResult:
    """Result of comparing two passive trees."""
    # Similarity metrics
    similarity_percent: float
    shared_count: int
    missing_count: int  # In target, not in your build
    extra_count: int    # In your build, not in target

    # Details
    shared_nodes: List[int]
    missing_nodes: List[int]
    extra_nodes: List[int]
    missing_masteries: List[Tuple[int, int]]

    # Build info
    your_build_name: str
    target_build_name: str
    your_node_count: int
    target_node_count: int


class TreeComparisonService:
    """
    Service for comparing passive trees between builds.

    Provides a simple interface for the UI to compare:
    - Your saved build vs another saved build
    - Your saved build vs a pasted PoB code
    """

    def __init__(self, character_manager: Optional[CharacterManager] = None):
        """
        Initialize the tree comparison service.

        Args:
            character_manager: CharacterManager for accessing saved profiles
        """
        self.character_manager = character_manager
        self.parser = GuideBuildParser()
        self.comparator = BuildComparator()

    def compare_pob_codes(
        self,
        your_code: str,
        target_code: str,
        your_name: str = "Your Build",
        target_name: str = "Target Build",
    ) -> TreeComparisonResult:
        """
        Compare two builds by their PoB codes.

        Args:
            your_code: Your PoB share code
            target_code: Target PoB share code to compare against
            your_name: Display name for your build
            target_name: Display name for target build

        Returns:
            TreeComparisonResult with comparison data
        """
        # Decode both codes to XML
        your_xml = PoBDecoder.decode_pob_code(your_code)
        target_xml = PoBDecoder.decode_pob_code(target_code)

        return self._compare_xml(your_xml, target_xml, your_name, target_name)

    def compare_profile_to_code(
        self,
        profile_name: str,
        target_code: str,
        target_name: str = "Target Build",
    ) -> TreeComparisonResult:
        """
        Compare a saved profile to a PoB code.

        Args:
            profile_name: Name of saved profile
            target_code: PoB share code to compare against
            target_name: Display name for target build

        Returns:
            TreeComparisonResult with comparison data
        """
        if not self.character_manager:
            raise ValueError("CharacterManager not available")

        profile = self.character_manager.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {profile_name}")

        if not profile.pob_code:
            raise ValueError(f"Profile '{profile_name}' has no PoB code stored")

        return self.compare_pob_codes(
            your_code=profile.pob_code,
            target_code=target_code,
            your_name=profile_name,
            target_name=target_name,
        )

    def compare_profiles(
        self,
        your_profile_name: str,
        target_profile_name: str,
    ) -> TreeComparisonResult:
        """
        Compare two saved profiles.

        Args:
            your_profile_name: Name of your profile
            target_profile_name: Name of profile to compare against

        Returns:
            TreeComparisonResult with comparison data
        """
        if not self.character_manager:
            raise ValueError("CharacterManager not available")

        your_profile = self.character_manager.get_profile(your_profile_name)
        target_profile = self.character_manager.get_profile(target_profile_name)

        if not your_profile:
            raise ValueError(f"Profile not found: {your_profile_name}")
        if not target_profile:
            raise ValueError(f"Profile not found: {target_profile_name}")

        if not your_profile.pob_code:
            raise ValueError(f"Profile '{your_profile_name}' has no PoB code stored")
        if not target_profile.pob_code:
            raise ValueError(f"Profile '{target_profile_name}' has no PoB code stored")

        return self.compare_pob_codes(
            your_code=your_profile.pob_code,
            target_code=target_profile.pob_code,
            your_name=your_profile_name,
            target_name=target_profile_name,
        )

    def compare_xml_with_specs(
        self,
        your_xml: str,
        target_xml: str,
        your_name: str,
        target_name: str,
        your_spec_idx: int = 0,
        target_spec_idx: int = 0,
    ) -> TreeComparisonResult:
        """
        Compare two builds from their decoded XML with specific tree spec indices.

        Args:
            your_xml: Your decoded PoB XML
            target_xml: Target decoded PoB XML
            your_name: Display name for your build
            target_name: Display name for target build
            your_spec_idx: Index of tree spec to use from your build
            target_spec_idx: Index of tree spec to use from target build

        Returns:
            TreeComparisonResult with comparison data
        """
        return self._compare_xml(
            your_xml, target_xml, your_name, target_name,
            your_spec_idx, target_spec_idx
        )

    def _compare_xml(
        self,
        your_xml: str,
        target_xml: str,
        your_name: str,
        target_name: str,
        your_spec_idx: int = 0,
        target_spec_idx: int = 0,
    ) -> TreeComparisonResult:
        """
        Compare two builds from their decoded XML.

        Args:
            your_xml: Your decoded PoB XML
            target_xml: Target decoded PoB XML
            your_name: Display name for your build
            target_name: Display name for target build
            your_spec_idx: Index of tree spec to use from your build (default: 0)
            target_spec_idx: Index of tree spec to use from target build (default: 0)

        Returns:
            TreeComparisonResult with comparison data
        """
        # Parse tree specs from both XMLs
        your_specs = self.parser.parse_tree_specs(your_xml)
        target_specs = self.parser.parse_tree_specs(target_xml)

        if not your_specs:
            raise ValueError("Could not parse tree from your build")
        if not target_specs:
            raise ValueError("Could not parse tree from target build")

        # Use the specified spec index, falling back to 0 if out of range
        your_spec_idx = min(your_spec_idx, len(your_specs) - 1)
        target_spec_idx = min(target_spec_idx, len(target_specs) - 1)
        your_spec = your_specs[your_spec_idx]
        target_spec = target_specs[target_spec_idx]

        # Compare the trees
        delta = self.comparator.compare_trees(
            player_nodes=your_spec.nodes,
            guide_nodes=target_spec.nodes,
            player_masteries=your_spec.mastery_effects,
            guide_masteries=target_spec.mastery_effects,
        )

        # Calculate similarity (based on Jaccard index for symmetry)
        total_unique_nodes = len(your_spec.nodes | target_spec.nodes)
        if total_unique_nodes > 0:
            similarity = len(delta.shared_nodes) / total_unique_nodes * 100
        else:
            similarity = 100.0

        return TreeComparisonResult(
            similarity_percent=round(similarity, 1),
            shared_count=len(delta.shared_nodes),
            missing_count=len(delta.missing_nodes),
            extra_count=len(delta.extra_nodes),
            shared_nodes=delta.shared_nodes,
            missing_nodes=delta.missing_nodes,
            extra_nodes=delta.extra_nodes,
            missing_masteries=delta.missing_masteries,
            your_build_name=your_name,
            target_build_name=target_name,
            your_node_count=len(your_spec.nodes),
            target_node_count=len(target_spec.nodes),
        )

    def format_comparison_report(self, result: TreeComparisonResult) -> str:
        """
        Generate a human-readable comparison report.

        Args:
            result: TreeComparisonResult from a comparison

        Returns:
            Formatted string report
        """
        lines = [
            f"Tree Comparison: {result.your_build_name} vs {result.target_build_name}",
            "=" * 60,
            "",
            f"Similarity: {result.similarity_percent}%",
            "",
            f"Your build: {result.your_node_count} nodes",
            f"Target build: {result.target_node_count} nodes",
            "",
            f"Shared nodes: {result.shared_count}",
            f"Nodes you're missing: {result.missing_count}",
            f"Extra nodes you have: {result.extra_count}",
        ]

        if result.missing_masteries:
            lines.append(f"Missing masteries: {len(result.missing_masteries)}")

        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Tree Comparison Service Test")
    print("=" * 60)

    service = TreeComparisonService()
    print("Service initialized successfully")
