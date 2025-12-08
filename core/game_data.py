"""
Game Data - PoE1 and PoE2 class/ascendancy information.

Provides data for filtering builds by game version, class, and ascendancy.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class GameVersion(str, Enum):
    """Path of Exile game version."""
    POE1 = "poe1"
    POE2 = "poe2"

    @property
    def display_name(self) -> str:
        return {
            GameVersion.POE1: "Path of Exile 1",
            GameVersion.POE2: "Path of Exile 2",
        }[self]

    @property
    def short_name(self) -> str:
        return {
            GameVersion.POE1: "PoE1",
            GameVersion.POE2: "PoE2",
        }[self]


@dataclass
class AscendancyInfo:
    """Information about an ascendancy class."""
    name: str
    class_id: int  # PoB internal class ID


@dataclass
class ClassInfo:
    """Information about a base class."""
    name: str
    class_id: int
    ascendancies: List[AscendancyInfo]

    def get_ascendancy(self, name: str) -> Optional[AscendancyInfo]:
        """Get ascendancy by name (case-insensitive)."""
        name_lower = name.lower()
        for asc in self.ascendancies:
            if asc.name.lower() == name_lower:
                return asc
        return None


# PoE1 Classes and Ascendancies
POE1_CLASSES: Dict[str, ClassInfo] = {
    "Scion": ClassInfo(
        name="Scion",
        class_id=0,
        ascendancies=[
            AscendancyInfo("Ascendant", 1),
        ]
    ),
    "Marauder": ClassInfo(
        name="Marauder",
        class_id=1,
        ascendancies=[
            AscendancyInfo("Juggernaut", 1),
            AscendancyInfo("Berserker", 2),
            AscendancyInfo("Chieftain", 3),
        ]
    ),
    "Ranger": ClassInfo(
        name="Ranger",
        class_id=2,
        ascendancies=[
            AscendancyInfo("Raider", 1),
            AscendancyInfo("Deadeye", 2),
            AscendancyInfo("Pathfinder", 3),
        ]
    ),
    "Witch": ClassInfo(
        name="Witch",
        class_id=3,
        ascendancies=[
            AscendancyInfo("Necromancer", 1),
            AscendancyInfo("Elementalist", 2),
            AscendancyInfo("Occultist", 3),
        ]
    ),
    "Duelist": ClassInfo(
        name="Duelist",
        class_id=4,
        ascendancies=[
            AscendancyInfo("Slayer", 1),
            AscendancyInfo("Gladiator", 2),
            AscendancyInfo("Champion", 3),
        ]
    ),
    "Templar": ClassInfo(
        name="Templar",
        class_id=5,
        ascendancies=[
            AscendancyInfo("Inquisitor", 1),
            AscendancyInfo("Hierophant", 2),
            AscendancyInfo("Guardian", 3),
        ]
    ),
    "Shadow": ClassInfo(
        name="Shadow",
        class_id=6,
        ascendancies=[
            AscendancyInfo("Assassin", 1),
            AscendancyInfo("Trickster", 2),
            AscendancyInfo("Saboteur", 3),
        ]
    ),
}

# PoE2 Classes and Ascendancies
POE2_CLASSES: Dict[str, ClassInfo] = {
    "Warrior": ClassInfo(
        name="Warrior",
        class_id=1,
        ascendancies=[
            AscendancyInfo("Titan", 1),
            AscendancyInfo("Warbringer", 2),
        ]
    ),
    "Ranger": ClassInfo(
        name="Ranger",
        class_id=2,
        ascendancies=[
            AscendancyInfo("Deadeye", 1),
            AscendancyInfo("Pathfinder", 2),
        ]
    ),
    "Witch": ClassInfo(
        name="Witch",
        class_id=3,
        ascendancies=[
            AscendancyInfo("Blood Mage", 1),
            AscendancyInfo("Infernalist", 2),
        ]
    ),
    "Mercenary": ClassInfo(
        name="Mercenary",
        class_id=4,
        ascendancies=[
            AscendancyInfo("Witchhunter", 1),
            AscendancyInfo("Gemling Legionnaire", 2),
        ]
    ),
    "Monk": ClassInfo(
        name="Monk",
        class_id=5,
        ascendancies=[
            AscendancyInfo("Invoker", 1),
            AscendancyInfo("Acolyte of Chayula", 2),
        ]
    ),
    "Sorceress": ClassInfo(
        name="Sorceress",
        class_id=6,
        ascendancies=[
            AscendancyInfo("Stormweaver", 1),
            AscendancyInfo("Chronomancer", 2),
        ]
    ),
    "Huntress": ClassInfo(
        name="Huntress",
        class_id=7,
        ascendancies=[
            AscendancyInfo("Amazon", 1),
            AscendancyInfo("Beastmaster", 2),
        ]
    ),
    "Druid": ClassInfo(
        name="Druid",
        class_id=8,
        ascendancies=[
            AscendancyInfo("Oracle", 1),
            AscendancyInfo("Shaman", 2),
        ]
    ),
}


def get_classes_for_game(game_version: GameVersion) -> Dict[str, ClassInfo]:
    """Get all classes for a game version."""
    if game_version == GameVersion.POE1:
        return POE1_CLASSES
    else:
        return POE2_CLASSES


def get_all_ascendancies(game_version: GameVersion) -> List[str]:
    """Get list of all ascendancy names for a game version."""
    classes = get_classes_for_game(game_version)
    ascendancies = []
    for class_info in classes.values():
        for asc in class_info.ascendancies:
            ascendancies.append(asc.name)
    return sorted(ascendancies)


def get_class_for_ascendancy(game_version: GameVersion, ascendancy: str) -> Optional[str]:
    """Find which class an ascendancy belongs to."""
    classes = get_classes_for_game(game_version)
    asc_lower = ascendancy.lower()
    for class_name, class_info in classes.items():
        for asc in class_info.ascendancies:
            if asc.name.lower() == asc_lower:
                return class_name
    return None


def detect_game_version_from_ascendancy(ascendancy: str) -> Optional[GameVersion]:
    """
    Attempt to detect game version based on ascendancy name.

    Some ascendancies are unique to each game, which can help identify the game version.
    """
    if not ascendancy:
        return None

    asc_lower = ascendancy.lower()

    # PoE1-only ascendancies
    poe1_only = {
        "ascendant", "juggernaut", "berserker", "chieftain",
        "raider", "necromancer", "elementalist", "occultist",
        "slayer", "gladiator", "champion", "inquisitor",
        "hierophant", "guardian", "assassin", "trickster", "saboteur"
    }

    # PoE2-only ascendancies
    poe2_only = {
        "titan", "warbringer", "blood mage", "infernalist",
        "witchhunter", "gemling legionnaire", "invoker",
        "acolyte of chayula", "stormweaver", "chronomancer",
        "amazon", "beastmaster", "oracle", "shaman"
    }

    if asc_lower in poe1_only:
        return GameVersion.POE1
    elif asc_lower in poe2_only:
        return GameVersion.POE2

    # Some ascendancies exist in both games (Deadeye, Pathfinder)
    return None


def detect_game_version_from_class(class_name: str) -> Optional[GameVersion]:
    """
    Attempt to detect game version based on class name.
    """
    if not class_name:
        return None

    class_lower = class_name.lower()

    # PoE1-only classes
    poe1_only = {"scion", "marauder", "duelist", "templar", "shadow"}

    # PoE2-only classes
    poe2_only = {"warrior", "mercenary", "monk", "sorceress", "huntress", "druid"}

    if class_lower in poe1_only:
        return GameVersion.POE1
    elif class_lower in poe2_only:
        return GameVersion.POE2

    # Ranger and Witch exist in both games
    return None


def detect_game_version(class_name: str = "", ascendancy: str = "") -> Optional[GameVersion]:
    """
    Detect game version from class and/or ascendancy.

    Args:
        class_name: Base class name
        ascendancy: Ascendancy name

    Returns:
        Detected GameVersion or None if ambiguous/unknown
    """
    # Try ascendancy first (more specific)
    version = detect_game_version_from_ascendancy(ascendancy)
    if version:
        return version

    # Fall back to class
    return detect_game_version_from_class(class_name)


# Testing
if __name__ == "__main__":
    print("PoE1 Classes:")
    for name, info in POE1_CLASSES.items():
        ascs = [a.name for a in info.ascendancies]
        print(f"  {name}: {ascs}")

    print("\nPoE2 Classes:")
    for name, info in POE2_CLASSES.items():
        ascs = [a.name for a in info.ascendancies]
        print(f"  {name}: {ascs}")

    print("\nDetection tests:")
    print(f"  Necromancer -> {detect_game_version(ascendancy='Necromancer')}")
    print(f"  Stormweaver -> {detect_game_version(ascendancy='Stormweaver')}")
    print(f"  Deadeye -> {detect_game_version(ascendancy='Deadeye')}")
    print(f"  Marauder -> {detect_game_version(class_name='Marauder')}")
    print(f"  Warrior -> {detect_game_version(class_name='Warrior')}")
