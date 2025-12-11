"""
Upgrade checker - compares items against character gear to determine upgrades.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from core.pob.manager import CharacterManager


class UpgradeChecker:
    """
    Compares items against character's current gear to determine if upgrades.

    Uses mod analysis and slot matching to identify potential upgrades.
    """

    # Slot type mappings for item comparison
    ITEM_CLASS_TO_SLOTS = {
        "Body Armour": ["Body Armour"],
        "Body Armours": ["Body Armour"],
        "Helmets": ["Helmet"],
        "Helmet": ["Helmet"],
        "Gloves": ["Gloves"],
        "Boots": ["Boots"],
        "Belts": ["Belt"],
        "Belt": ["Belt"],
        "Amulets": ["Amulet"],
        "Amulet": ["Amulet"],
        "Rings": ["Ring 1", "Ring 2"],
        "Ring": ["Ring 1", "Ring 2"],
        "One Handed Swords": ["Weapon", "Offhand"],
        "One Handed Axes": ["Weapon", "Offhand"],
        "One Handed Maces": ["Weapon", "Offhand"],
        "Daggers": ["Weapon", "Offhand"],
        "Claws": ["Weapon", "Offhand"],
        "Wands": ["Weapon", "Offhand"],
        "Sceptres": ["Weapon", "Offhand"],
        "Two Handed Swords": ["Weapon"],
        "Two Handed Axes": ["Weapon"],
        "Two Handed Maces": ["Weapon"],
        "Staves": ["Weapon"],
        "Bows": ["Weapon"],
        "Shields": ["Offhand"],
        "Quivers": ["Offhand"],
        "Flasks": ["Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5"],
    }

    def __init__(self, character_manager: CharacterManager):
        """
        Initialize the upgrade checker.

        Args:
            character_manager: CharacterManager with stored profiles
        """
        self.character_manager = character_manager

    def get_applicable_slots(self, item_class: str) -> List[str]:
        """
        Get equipment slots an item class can fit into.

        Args:
            item_class: Item class (e.g., "Body Armour", "Rings")

        Returns:
            List of applicable slot names
        """
        # Normalize item class
        normalized = item_class.strip()
        return self.ITEM_CLASS_TO_SLOTS.get(normalized, [])

    def check_upgrade(
        self,
        item_class: str,
        item_mods: List[str],
        profile_name: Optional[str] = None,
    ) -> Tuple[bool, List[str], Optional[str]]:
        """
        Check if an item is a potential upgrade for a character.

        Args:
            item_class: The item's class (e.g., "Body Armour")
            item_mods: List of item modifiers
            profile_name: Specific profile to check against (uses active if None)

        Returns:
            Tuple of (is_potential_upgrade, reasons, compared_slot)
        """
        # Get profile
        if profile_name:
            profile = self.character_manager.get_profile(profile_name)
        else:
            profile = self.character_manager.get_active_profile()

        if not profile:
            return False, ["No character profile loaded"], None

        # Get applicable slots
        slots = self.get_applicable_slots(item_class)
        if not slots:
            return False, [f"Unknown item class: {item_class}"], None

        # Compare against each applicable slot
        for slot in slots:
            current_item = profile.get_item_for_slot(slot)
            if not current_item:
                # Empty slot = definite upgrade
                return True, [f"Empty slot: {slot}"], slot

            # Compare mods (simplified - count valuable stats)
            upgrade_reasons = self._compare_mods(item_mods, current_item.explicit_mods)
            if upgrade_reasons:
                return True, upgrade_reasons, slot

        return False, ["No improvement detected"], slots[0] if slots else None

    def _compare_mods(
        self,
        new_mods: List[str],
        current_mods: List[str],
    ) -> List[str]:
        """
        Compare mods between new and current items.

        Returns list of reasons if new item is better, empty if not.
        """
        reasons = []

        # Extract numeric values from mods for comparison
        new_life = self._extract_stat(new_mods, r"\+(\d+) to maximum Life")
        current_life = self._extract_stat(current_mods, r"\+(\d+) to maximum Life")

        if new_life and current_life and new_life > current_life:
            reasons.append(f"More life: {new_life} vs {current_life}")
        elif new_life and not current_life:
            reasons.append(f"Adds {new_life} life (current has none)")

        # Compare resistances
        for res_type in ["Fire", "Cold", "Lightning", "Chaos"]:
            pattern = rf"\+(\d+)%? to {res_type} Resistance"
            new_res = self._extract_stat(new_mods, pattern)
            current_res = self._extract_stat(current_mods, pattern)

            if new_res and current_res and new_res > current_res:
                reasons.append(f"More {res_type} res: {new_res}% vs {current_res}%")
            elif new_res and not current_res:
                reasons.append(f"Adds {new_res}% {res_type} res")

        # Compare energy shield
        new_es = self._extract_stat(new_mods, r"\+(\d+) to maximum Energy Shield")
        current_es = self._extract_stat(current_mods, r"\+(\d+) to maximum Energy Shield")

        if new_es and current_es and new_es > current_es:
            reasons.append(f"More ES: {new_es} vs {current_es}")

        return reasons

    def _extract_stat(self, mods: List[str], pattern: str) -> Optional[int]:
        """Extract a numeric stat from mod list using regex pattern."""
        for mod in mods:
            match = re.search(pattern, mod, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
