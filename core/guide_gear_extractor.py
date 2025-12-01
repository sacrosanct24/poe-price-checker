"""
Guide Gear Extractor

Extracts recommended gear from build guides (PoB builds) for use in BiS search.
Identifies uniques and recommended rare specs from guide builds.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.pob_integration import PoBBuild, PoBItem, CharacterManager, PoBDecoder

# Use defusedxml to prevent XXE attacks
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

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
class ItemSetInfo:
    """Information about an item set (loadout) in a PoB build."""
    id: str
    title: str
    slot_count: int
    is_active: bool = False

    @property
    def display_name(self) -> str:
        """Display name with active marker."""
        marker = " (Active)" if self.is_active else ""
        return f"{self.title}{marker}"


@dataclass
class GuideGearSummary:
    """Summary of all gear recommendations from a guide."""
    profile_name: str
    guide_name: str
    recommendations: Dict[str, GuideGearRecommendation] = field(default_factory=dict)
    uniques_needed: List[str] = field(default_factory=list)
    rare_slots: List[str] = field(default_factory=list)
    item_set_name: str = ""  # Name of the item set this was extracted from

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

    def get_item_sets_from_profile(self, profile_name: str) -> List[ItemSetInfo]:
        """
        Get list of item sets (loadouts) from a profile's PoB code.

        Args:
            profile_name: Name of the profile

        Returns:
            List of ItemSetInfo objects
        """
        if not self.character_manager:
            return []

        profile = self.character_manager.get_profile(profile_name)
        if not profile or not profile.pob_code:
            return []

        try:
            xml_str = self._decoder.decode_pob_code(profile.pob_code)
            return self._parse_item_sets(xml_str)
        except Exception as e:
            logger.warning(f"Failed to parse item sets from profile: {e}")
            return []

    def get_item_sets_from_pob_code(self, pob_code: str) -> List[ItemSetInfo]:
        """
        Get list of item sets (loadouts) from a PoB code.

        Args:
            pob_code: Path of Building share code

        Returns:
            List of ItemSetInfo objects
        """
        try:
            xml_str = self._decoder.decode_pob_code(pob_code)
            return self._parse_item_sets(xml_str)
        except Exception as e:
            logger.warning(f"Failed to parse item sets from PoB code: {e}")
            return []

    def _parse_item_sets(self, xml_string: str) -> List[ItemSetInfo]:
        """Parse item sets from PoB XML."""
        try:
            root = ET.fromstring(xml_string)
            items_elem = root.find("Items")
            if items_elem is None:
                return []

            item_sets = []
            active_set = items_elem.get("activeItemSet", "1")

            for item_set in items_elem.findall("ItemSet"):
                set_id = item_set.get("id", "?")
                raw_title = item_set.get("title", "Unnamed")
                # Clean PoB color codes like ^xFFFFFF
                import re
                title = re.sub(r"\^x[0-9A-Fa-f]{6}", "", raw_title).strip()
                if not title:
                    title = f"Item Set {set_id}"
                slots = len(item_set.findall("Slot"))

                item_sets.append(ItemSetInfo(
                    id=set_id,
                    title=title,
                    slot_count=slots,
                    is_active=(set_id == active_set),
                ))

            return item_sets

        except Exception as e:
            logger.warning(f"Failed to parse item sets: {e}")
            return []

    def extract_from_profile_with_item_set(
        self,
        profile_name: str,
        item_set_id: str
    ) -> Optional[GuideGearSummary]:
        """
        Extract gear from a specific item set in a profile.

        Args:
            profile_name: Name of the profile
            item_set_id: ID of the item set to extract from

        Returns:
            GuideGearSummary for the specified item set
        """
        if not self.character_manager:
            return None

        profile = self.character_manager.get_profile(profile_name)
        if not profile or not profile.pob_code:
            return None

        try:
            xml_str = self._decoder.decode_pob_code(profile.pob_code)
            return self._extract_from_item_set(xml_str, profile_name, item_set_id)
        except Exception as e:
            logger.exception(f"Failed to extract from item set: {e}")
            return None

    def extract_from_pob_code_with_item_set(
        self,
        pob_code: str,
        guide_name: str,
        item_set_id: str
    ) -> Optional[GuideGearSummary]:
        """
        Extract gear from a specific item set in a PoB code.

        Args:
            pob_code: Path of Building share code
            guide_name: Name to use for this guide
            item_set_id: ID of the item set to extract from

        Returns:
            GuideGearSummary for the specified item set
        """
        try:
            xml_str = self._decoder.decode_pob_code(pob_code)
            return self._extract_from_item_set(xml_str, guide_name, item_set_id)
        except Exception as e:
            logger.exception(f"Failed to extract from item set: {e}")
            return None

    def _extract_from_item_set(
        self,
        xml_string: str,
        guide_name: str,
        item_set_id: str
    ) -> Optional[GuideGearSummary]:
        """Extract items from a specific item set in PoB XML."""
        try:
            root = ET.fromstring(xml_string)

            # Get build info
            build_elem = root.find("Build")
            class_name = build_elem.get("className", "") if build_elem is not None else ""

            items_elem = root.find("Items")
            if items_elem is None:
                return None

            # Find the target item set
            target_item_set = None
            item_set_title = ""
            for item_set in items_elem.findall("ItemSet"):
                if item_set.get("id") == item_set_id:
                    target_item_set = item_set
                    raw_title = item_set.get("title", "Unnamed")
                    import re
                    item_set_title = re.sub(r"\^x[0-9A-Fa-f]{6}", "", raw_title).strip()
                    break

            if target_item_set is None:
                logger.warning(f"Item set {item_set_id} not found")
                return None

            # Parse all items by ID
            items_by_id: Dict[str, PoBItem] = {}
            for item_elem in items_elem.findall("Item"):
                item = self._parse_item_element(item_elem)
                if item:
                    item_id = item_elem.get("id", "")
                    items_by_id[item_id] = item

            # Map slots to items from this specific item set
            slot_items: Dict[str, PoBItem] = {}
            for slot_elem in target_item_set.findall("Slot"):
                slot_name = slot_elem.get("name", "")
                item_id = slot_elem.get("itemId", "")

                # Skip special slots
                if "Abyssal" in slot_name or "Graft" in slot_name:
                    continue
                if not item_id or item_id == "0":
                    continue

                if item_id in items_by_id:
                    slot_items[slot_name] = items_by_id[item_id]

            # Build summary
            summary = GuideGearSummary(
                profile_name=guide_name,
                guide_name=class_name or guide_name,
                item_set_name=item_set_title,
            )

            for slot in EQUIPMENT_SLOTS:
                item = slot_items.get(slot)
                if item:
                    recommendation = self._item_to_recommendation(item, slot)
                    summary.recommendations[slot] = recommendation

                    if recommendation.is_unique:
                        summary.uniques_needed.append(recommendation.item_name)
                    else:
                        summary.rare_slots.append(slot)

            return summary

        except Exception as e:
            logger.exception(f"Failed to extract from item set: {e}")
            return None

    def _parse_item_element(self, item_elem) -> Optional[PoBItem]:
        """Parse a single item element from PoB XML."""
        raw_text = item_elem.text or ""
        if not raw_text.strip():
            return None

        lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return None

        item = PoBItem(
            slot="",
            rarity="RARE",
            name="",
            base_type="",
            raw_text=raw_text,
        )

        # Metadata fields to skip
        METADATA_PREFIXES = (
            "Rarity:", "Unique ID:", "Item Level:", "Quality:", "Sockets:",
            "LevelReq:", "Implicits:", "Elder Item", "Shaper Item", "Crusader Item",
            "Hunter Item", "Redeemer Item", "Warlord Item", "Synthesised Item",
            "Fractured Item", "Corrupted", "Mirrored", "Split", "Unidentified",
            "Radius:", "Limited to:", "Has Alt Variant", "Selected Variant:",
            "Catalyst:", "Talisman Tier:", "Requires ", "League:",
        )

        implicit_count = 0
        implicits_remaining = 0
        import re

        for i, line in enumerate(lines):
            if not line:
                continue

            # Rarity
            if line.startswith("Rarity:"):
                item.rarity = line.replace("Rarity:", "").strip().upper()
                continue

            # Item name (line after Rarity)
            if i == 1:
                item.name = line
                continue

            # Base type (line after name)
            if i == 2:
                item.base_type = line
                continue

            # Skip metadata lines but extract values
            if any(line.startswith(prefix) for prefix in METADATA_PREFIXES):
                if line.startswith("Item Level:"):
                    try:
                        item.item_level = int(line.replace("Item Level:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("Quality:"):
                    qual = re.search(r"\+?(\d+)%?", line)
                    if qual:
                        item.quality = int(qual.group(1))
                elif line.startswith("Sockets:"):
                    item.sockets = line.replace("Sockets:", "").strip()
                elif line.startswith("Implicits:"):
                    try:
                        implicit_count = int(line.replace("Implicits:", "").strip())
                        implicits_remaining = implicit_count
                    except ValueError:
                        pass
                continue

            # Implicit mods
            if implicits_remaining > 0:
                mod = re.sub(r"\{[^}]+\}", "", line).strip()
                if mod:
                    item.implicit_mods.append(mod)
                implicits_remaining -= 1
                continue

            # Explicit mods
            if implicit_count >= 0:
                mod = re.sub(r"\{[^}]+\}", "", line).strip()
                if mod:
                    item.explicit_mods.append(mod)

        return item


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
