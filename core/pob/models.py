"""
PoB data models - enums and dataclasses for Path of Building integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.build_archetype import BuildArchetype


class BuildCategory(str, Enum):
    """Categories for organizing builds."""
    MY_BUILDS = "my_builds"  # User's own builds - protected from bulk delete
    LEAGUE_STARTER = "league_starter"
    ENDGAME = "endgame"
    BOSS_KILLER = "boss_killer"
    MAPPER = "mapper"
    BUDGET = "budget"
    META = "meta"
    EXPERIMENTAL = "experimental"
    REFERENCE = "reference"  # For reference builds you're comparing against
    IMPORTED = "imported"  # Imported from build sites - can be bulk deleted


@dataclass
class PoBItem:
    """Represents an item from a PoB build."""
    slot: str  # "Weapon 1", "Helmet", "Body Armour", etc.
    rarity: str  # "RARE", "UNIQUE", "MAGIC", "NORMAL"
    name: str
    base_type: str
    item_level: int = 0
    quality: int = 0
    sockets: str = ""  # e.g., "R-R-R-G-G-B"
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)
    raw_text: str = ""

    @property
    def display_name(self) -> str:
        if self.name and self.name != self.base_type:
            return f"{self.name} ({self.base_type})"
        return self.base_type

    @property
    def link_count(self) -> int:
        """Count the largest link group."""
        if not self.sockets:
            return 0
        # Sockets format might be like "R-R-R G-G B" where space separates groups
        # Each group connected by - is linked
        if " " in self.sockets:
            groups = self.sockets.split(" ")
            return max(len(g.replace("-", "")) for g in groups) if groups else 0
        # No spaces - treat entire string as one group
        return len(self.sockets.replace("-", ""))


@dataclass
class PoBBuild:
    """Represents a decoded PoB build."""
    class_name: str = ""
    ascendancy: str = ""
    level: int = 1
    bandit: str = "None"
    main_skill: str = ""
    items: Dict[str, PoBItem] = field(default_factory=dict)  # slot -> item
    skills: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    raw_xml: str = ""

    # Stats from PoB (if available)
    stats: Dict[str, float] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"Level {self.level} {self.ascendancy or self.class_name}"


@dataclass
class CharacterProfile:
    """Stored character profile for upgrade comparisons."""
    name: str
    build: PoBBuild
    pob_code: str = ""
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    categories: List[str] = field(default_factory=list)  # List of BuildCategory values
    is_upgrade_target: bool = False  # Mark as the build to check upgrades against
    priorities: Optional[Any] = None  # BuildPriorities for BiS search (lazy import to avoid circular)
    _archetype: Optional["BuildArchetype"] = field(default=None, repr=False)  # Cached archetype

    # Build library fields
    tags: List[str] = field(default_factory=list)  # User-defined tags for organization
    guide_url: str = ""  # Link to build guide (Maxroll, poe.ninja, etc.)
    ssf_friendly: bool = False  # Whether build is viable for SSF
    favorite: bool = False  # Mark as favorite for quick access

    def get_item_for_slot(self, slot: str) -> Optional[PoBItem]:
        """Get the item equipped in a specific slot."""
        return self.build.items.get(slot)

    def has_category(self, category: BuildCategory) -> bool:
        """Check if profile has a specific category."""
        return category.value in self.categories

    def add_category(self, category: BuildCategory) -> None:
        """Add a category to the profile."""
        if category.value not in self.categories:
            self.categories.append(category.value)

    def remove_category(self, category: BuildCategory) -> None:
        """Remove a category from the profile."""
        if category.value in self.categories:
            self.categories.remove(category.value)

    def get_archetype(self) -> "BuildArchetype":
        """
        Get the build archetype, auto-detecting from PoB stats if needed.

        Returns:
            BuildArchetype detected from build stats
        """
        if self._archetype is None:
            self._archetype = self._detect_archetype()
        return self._archetype

    def _detect_archetype(self) -> "BuildArchetype":
        """Detect archetype from build's PoB stats."""
        from core.build_archetype import detect_archetype, get_default_archetype

        if not self.build.stats:
            return get_default_archetype()

        return detect_archetype(self.build.stats, self.build.main_skill)

    def clear_archetype_cache(self) -> None:
        """Clear cached archetype (call after build stats change)."""
        self._archetype = None
