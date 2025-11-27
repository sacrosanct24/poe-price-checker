"""
Guide Gear Extractor

Extracts recommended gear from build guides (PoB builds) for use in BiS search.
Identifies uniques and recommended rare specs from guide builds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from core.pob_integration import PoBBuild, PoBItem, CharacterManager, PoBDecoder
from core.build_comparison import GuideBuildParser

logger = logging.getLogger(__name__)


# Standard equipment slots
EQUIPMENT_SLOTS = [
    "Weapon 1", "Weapon 2", "Helmet", "Body Armour",
    "Gloves", "Boots", "Belt", "Amulet", "Ring 1", "Ring 2"
]


@dataclass
class GuideGearRecommendation:
    """A gear recommendation from a build guide."""
    slot: str
    item_name: str
    base_type: str
    rarity: str  # "UNIQUE", "RARE", etc.
    is_unique: bool
    key_mods: List[str] = field(default_factory=list)
    notes: str = ""
    priority: int = 1  # 1 = high, 2 = medium, 3 = low

    @property
    def display_name(self) -> str:
        """Get display name for the item."""
        if self.is_unique:
            return self.item_name
        elif self.item_name:
            return f"{self.item_name} ({self.base_type})"
        else:
            return self.base_type


@dataclass
class GuideGearSummary:
    """Summary of all gear recommendations from a guide."""
    profile_name: str
    guide_name: str
    recommendations: Dict[str, GuideGearRecommendation] = field(default_factory=dict)
    uniques_needed: List[str] = field(default_factory=list)
    rare_slots: List[str] = field(default_factory=list)

    def get_recommendation(self, slot: str) -> Optional[GuideGearRecommendation]:
        """Get recommendation for a specific slot."""
        return self.recommendations.get(slot)

    def get_unique_recommendations(self) -> List[GuideGearRecommendation]:
        """Get all unique item recommendations."""
        return [r for r in self.recommendations.values() if r.is_unique]

    def get_rare_recommendations(self) -> List[GuideGearRecommendation]:
        """Get all rare item recommendations."""
        return [r for r in self.recommendations.values() if not r.is_unique]


class GuideGearExtractor:
    """
    Extracts gear recommendations from build guides.

    Works with:
    1. Reference builds stored in CharacterManager
    2. PoB codes (Maxroll, pobb.in, etc.)
    """

    def __init__(self, character_manager: Optional[CharacterManager] = None):
        self.character_manager = character_manager
        self._decoder = PoBDecoder()

    def extract_from_profile(self, profile_name: str) -> Optional[GuideGearSummary]:
        """
        Extract gear recommendations from a saved profile.

        Args:
            profile_name: Name of the profile to extract from

        Returns:
            GuideGearSummary with all gear recommendations
        """
        if not self.character_manager:
            logger.warning("No CharacterManager available")
            return None

        profile = self.character_manager.get_profile(profile_name)
        if not profile or not profile.build:
            logger.warning(f"Profile '{profile_name}' not found or has no build")
            return None

        return self._extract_from_build(profile.build, profile_name)

    def extract_from_pob_code(
        self,
        pob_code: str,
        guide_name: str = "Imported Build"
    ) -> Optional[GuideGearSummary]:
        """
        Extract gear recommendations from a PoB code.

        Args:
            pob_code: Path of Building share code
            guide_name: Name to use for this guide

        Returns:
            GuideGearSummary with all gear recommendations
        """
        try:
            xml_str = self._decoder.decode_pob_code(pob_code)
            build = self._decoder.parse_build(xml_str)
            return self._extract_from_build(build, guide_name)
        except Exception as e:
            logger.exception(f"Failed to extract gear from PoB code: {e}")
            return None

    def _extract_from_build(
        self,
        build: PoBBuild,
        guide_name: str
    ) -> GuideGearSummary:
        """Extract gear recommendations from a parsed build."""
        summary = GuideGearSummary(
            profile_name=guide_name,
            guide_name=build.class_name or guide_name,
        )

        if not build.items:
            return summary

        for slot in EQUIPMENT_SLOTS:
            item = build.items.get(slot)
            if item:
                recommendation = self._item_to_recommendation(item, slot)
                summary.recommendations[slot] = recommendation

                if recommendation.is_unique:
                    summary.uniques_needed.append(recommendation.item_name)
                else:
                    summary.rare_slots.append(slot)

        return summary

    def _item_to_recommendation(
        self,
        item: PoBItem,
        slot: str
    ) -> GuideGearRecommendation:
        """Convert a PoBItem to a gear recommendation."""
        is_unique = item.rarity == "UNIQUE"

        # Extract key mods (up to 5 most relevant)
        key_mods = []
        all_mods = (item.implicit_mods or []) + (item.explicit_mods or [])

        # Prioritize certain mod types
        priority_patterns = [
            "+#% to maximum Life", "+# to maximum Life",
            "+#% to Energy Shield", "+# to maximum Energy Shield",
            "+#% to Fire Resistance", "+#% to Cold Resistance",
            "+#% to Lightning Resistance", "+#% to Chaos Resistance",
            "Movement Speed", "+# to Level",
            "increased Spell Damage", "increased Attack Speed",
            "Critical Strike"
        ]

        for mod in all_mods:
            if len(key_mods) >= 5:
                break
            # Check if mod matches any priority pattern
            for pattern in priority_patterns:
                if pattern.lower() in mod.lower():
                    key_mods.append(mod)
                    break
            else:
                # Add anyway if under limit
                if len(key_mods) < 3:
                    key_mods.append(mod)

        # Determine priority based on unique vs rare and slot importance
        priority = 2  # Default medium
        if is_unique:
            # Uniques are usually high priority (build-defining)
            priority = 1
        elif slot in ["Body Armour", "Weapon 1"]:
            priority = 1
        elif slot in ["Helmet", "Boots"]:
            priority = 2
        elif slot in ["Ring 1", "Ring 2", "Belt"]:
            priority = 3

        return GuideGearRecommendation(
            slot=slot,
            item_name=item.name or "",
            base_type=item.base_type or "",
            rarity=item.rarity,
            is_unique=is_unique,
            key_mods=key_mods,
            priority=priority,
        )

    def compare_with_current(
        self,
        guide_summary: GuideGearSummary,
        current_profile_name: str
    ) -> Dict[str, Dict]:
        """
        Compare guide gear with current player gear.

        Args:
            guide_summary: Extracted guide gear
            current_profile_name: Player's current profile

        Returns:
            Dict of slot -> comparison info
        """
        if not self.character_manager:
            return {}

        current_profile = self.character_manager.get_profile(current_profile_name)
        if not current_profile or not current_profile.build:
            return {}

        comparison = {}
        current_items = current_profile.build.items or {}

        for slot, recommendation in guide_summary.recommendations.items():
            current_item = current_items.get(slot)

            slot_comparison = {
                "recommendation": recommendation,
                "current_item": current_item,
                "has_item": current_item is not None,
                "is_match": False,
                "upgrade_needed": True,
            }

            if current_item:
                # Check if it's the same unique
                if recommendation.is_unique:
                    if (current_item.rarity == "UNIQUE" and
                        current_item.name == recommendation.item_name):
                        slot_comparison["is_match"] = True
                        slot_comparison["upgrade_needed"] = False
                else:
                    # For rares, check if base type matches or better
                    if current_item.base_type == recommendation.base_type:
                        slot_comparison["is_match"] = True
                        slot_comparison["upgrade_needed"] = False

            comparison[slot] = slot_comparison

        return comparison

    def format_summary_text(self, summary: GuideGearSummary) -> str:
        """Format gear summary as readable text."""
        lines = [f"=== Gear from: {summary.guide_name} ===", ""]

        # Uniques first
        if summary.uniques_needed:
            lines.append("UNIQUE ITEMS NEEDED:")
            for rec in summary.get_unique_recommendations():
                lines.append(f"  [{rec.slot}] {rec.item_name}")
                if rec.key_mods:
                    for mod in rec.key_mods[:3]:
                        lines.append(f"      - {mod}")
            lines.append("")

        # Rare slots
        if summary.rare_slots:
            lines.append("RARE ITEM SLOTS:")
            for rec in summary.get_rare_recommendations():
                lines.append(f"  [{rec.slot}] {rec.base_type}")
                if rec.key_mods:
                    for mod in rec.key_mods[:3]:
                        lines.append(f"      - {mod}")
            lines.append("")

        return "\n".join(lines)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test with a sample PoB item
    from core.pob_integration import PoBBuild, PoBItem

    # Create mock build with items
    build = PoBBuild(
        class_name="Slayer",
        ascendancy="Slayer",
        level=95,
    )

    # Add mock items
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
                "+38% to Lightning Resistance",
            ]
        ),
        "Boots": PoBItem(
            slot="Boots",
            rarity="RARE",
            name="Gale Stride",
            base_type="Two-Toned Boots",
            implicit_mods=["+12% to Fire and Cold Resistances"],
            explicit_mods=[
                "+89 to maximum Life",
                "30% increased Movement Speed",
                "+40% to Lightning Resistance",
            ]
        ),
    }

    extractor = GuideGearExtractor()
    summary = extractor._extract_from_build(build, "Test Slayer Build")

    print(extractor.format_summary_text(summary))
    print(f"Uniques needed: {summary.uniques_needed}")
    print(f"Rare slots: {summary.rare_slots}")
