"""
Item text parser for the PoE Price Checker.

Parses clipboard text copied from Path of Exile into a structured
ParsedItem object.

Supports:
- Rarity / name / base type
- Item level, quality, sockets/links
- Requirements (level, Str/Dex/Int)
- Implicit mods
- Enchant mods
- Explicit mods
- Influences (Shaper, Elder, Exarch, Eater, etc.)
- Corrupted, Fractured, Synthesised, Mirrored
- Stack size (currency)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional, List

logger = logging.getLogger(__name__)

LEVEL_RE = re.compile(r"^Level:\s*(\d+)")
QUALITY_RE = re.compile(r"^Quality:\s*\+?(-?\d+)%")
# Precompiled patterns for hot paths (avoid recompiling per line)
SEPARATOR_RE = re.compile(r"^-{2,}$")
RARITY_RE = re.compile(r"^Rarity:\s*(\w+)")
STACK_RE = re.compile(r"Stack Size:\s*(\d+)/(\d+)")
ITEM_LEVEL_RE = re.compile(r"Item Level:\s*(\d+)")
QUALITY_SEARCH_RE = re.compile(r"Quality:\s*\+?(\d+)%")


@dataclass
class ParsedItem:
    """Data structure representing a parsed PoE item."""

    raw_text: str

    # Basic info
    rarity: Optional[str] = None
    name: Optional[str] = None         # Top line after "Rarity: X"
    base_type: Optional[str] = None    # Second line after name (for rares)
    item_level: Optional[int] = None

    # Gem-specific
    gem_level: Optional[int] = None
    gem_quality: Optional[int] = None

    # Properties
    quality: Optional[int] = None
    sockets: Optional[str] = None
    links: int = 0
    stack_size: int = 1
    max_stack_size: int = 1

    # PoE2-specific properties
    rune_sockets: int = 0  # Number of rune sockets
    spirit: Optional[int] = None  # Spirit value (PoE2)

    # Requirements
    requirements: dict = field(default_factory=dict)

    # Affix sets
    explicits: List[str] = field(default_factory=list)
    implicits: List[str] = field(default_factory=list)
    enchants: List[str] = field(default_factory=list)

    # Influences
    influences: List[str] = field(default_factory=list)

    # Flags
    is_corrupted: bool = False
    is_fractured: bool = False
    is_synthesised: bool = False
    is_mirrored: bool = False
    is_unmodifiable: bool = False  # PoE2: Cannot be modified
    is_sanctified: bool = False  # PoE2: Sanctified item

    # PoE2 mod types
    rune_mods: List[str] = field(default_factory=list)  # Mods from socketed runes

    # Cluster jewel specific fields
    cluster_jewel_size: Optional[str] = None  # "Small", "Medium", "Large"
    cluster_jewel_passives: Optional[int] = None  # Number of passives (2-12)
    cluster_jewel_enchantment: Optional[str] = None  # e.g., "fire_damage"
    cluster_jewel_enchantment_text: Optional[str] = None  # Full enchant text
    cluster_jewel_notables: List[str] = field(default_factory=list)  # Notable names
    cluster_jewel_sockets: int = 0  # Jewel sockets on large clusters

    # Attached during price checking (set by price_service)
    _rare_evaluation: Optional[Any] = None
    _unique_evaluation: Optional[Any] = None  # UniqueItemEvaluation for uniques

    def get_display_name(self) -> str:
        """
        Human-friendly name for UI/DB rows.

        - For rares: 'Name (Base Type)' if both present and different
        - For uniques/others: name if present, else base_type
        - Fallback: 'Unknown Item'
        """
        name = (self.name or "").strip()
        base_type = (self.base_type or "").strip()

        if name and base_type and name != base_type:
            return f"{name} ({base_type})"
        if name:
            return name
        if base_type:
            return base_type
        return "Unknown Item"

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for serialization or testing."""
        return {
            "rarity": self.rarity,
            "name": self.name,
            "base_type": self.base_type,
            "item_level": self.item_level,
            "gem_level": self.gem_level,
            "gem_quality": self.gem_quality,
            "quality": self.quality,
            "sockets": self.sockets,
            "links": self.links,
            "stack_size": self.stack_size,
            "max_stack_size": self.max_stack_size,
            "requirements": self.requirements,
            "explicits": self.explicits,
            "implicits": self.implicits,
            "enchants": self.enchants,
            "is_corrupted": self.is_corrupted,
            # PoE2-specific
            "rune_sockets": self.rune_sockets,
            "spirit": self.spirit,
            "is_unmodifiable": self.is_unmodifiable,
            "is_sanctified": self.is_sanctified,
            "rune_mods": self.rune_mods,
            # Cluster jewel specific
            "cluster_jewel_size": self.cluster_jewel_size,
            "cluster_jewel_passives": self.cluster_jewel_passives,
            "cluster_jewel_enchantment": self.cluster_jewel_enchantment,
            "cluster_jewel_enchantment_text": self.cluster_jewel_enchantment_text,
            "cluster_jewel_notables": self.cluster_jewel_notables,
            "cluster_jewel_sockets": self.cluster_jewel_sockets,
        }

    @classmethod
    def from_stash_item(cls, item: dict, raw_text: str = "") -> "ParsedItem":
        """
        Create a ParsedItem from a stash API item dictionary.

        This allows RareItemEvaluator to work with items fetched from the stash API
        without needing clipboard text.

        Args:
            item: Dictionary from PoE stash API (with keys like typeLine, explicitMods, etc.)
            raw_text: Optional raw text representation (for display/debugging)

        Returns:
            ParsedItem populated from stash API data
        """
        # Map frameType to rarity string
        frame_type = item.get("frameType", 0)
        rarity_map = {
            0: "Normal",
            1: "Magic",
            2: "Rare",
            3: "Unique",
            4: "Gem",
            5: "Currency",
            6: "Divination Card",
        }
        rarity = rarity_map.get(frame_type, "Unknown")

        # Extract name, cleaning up PoE markup
        name = item.get("name", "").replace("<<set:MS>><<set:M>><<set:S>>", "")
        type_line = item.get("typeLine", "")
        base_type = item.get("baseType", type_line)

        # Build socket string and count links
        sockets = item.get("sockets", [])
        socket_str = ""
        max_links = 0
        if sockets:
            groups: dict = {}
            for s in sockets:
                g = s.get("group", 0)
                if g not in groups:
                    groups[g] = []
                groups[g].append(s.get("sColour", "?")[0])
            socket_str = "-".join("".join(g) for g in groups.values())
            max_links = max(len(g) for g in groups.values()) if groups else 0

        # Extract influences from the influences object
        influences = []
        inf_obj = item.get("influences", {})
        if inf_obj:
            # API format: {"shaper": true, "elder": true, ...}
            influence_names = {
                "shaper": "Shaper",
                "elder": "Elder",
                "crusader": "Crusader",
                "hunter": "Hunter",
                "redeemer": "Redeemer",
                "warlord": "Warlord",
            }
            for key, display_name in influence_names.items():
                if inf_obj.get(key):
                    influences.append(display_name)

        return cls(
            raw_text=raw_text or f"{name} {type_line}".strip(),
            rarity=rarity,
            name=name if name else None,
            base_type=base_type if base_type else None,
            item_level=item.get("ilvl"),
            quality=item.get("quality"),
            sockets=socket_str if socket_str else None,
            links=max_links,
            explicits=item.get("explicitMods", []),
            implicits=item.get("implicitMods", []),
            enchants=item.get("enchantMods", []),
            influences=influences,
            is_corrupted=item.get("corrupted", False),
            is_fractured=item.get("fractured", False),
            is_synthesised=item.get("synthesised", False),
            is_mirrored=item.get("mirrored", False),
        )


# ----------------------------------------------------------------------
# Parser Implementation
# ----------------------------------------------------------------------


class ItemParser:
    """
    Full item parser for PoE clipboard text.

    Handles header, body, modifiers, influences, requirements,
    sockets, corruptions, etc.
    """

    # String patterns retained for backward compatibility and readability,
    # but implementation uses module-level precompiled regex objects above.
    SEPARATOR_PATTERN = r"^-{2,}$"      # -------- separator lines
    RARITY_PATTERN = r"^Rarity:\s*(\w+)"
    STACK_PATTERN = r"Stack Size:\s*(\d+)/(\d+)"
    QUALITY_PATTERN = r"Quality:\s*\+?(\d+)%"
    ITEM_LEVEL_PATTERN = r"Item Level:\s*(\d+)"

    INFLUENCE_KEYWORDS = [
        "Shaper",
        "Elder",
        "Crusader",
        "Hunter",
        "Redeemer",
        "Warlord",
        "Searing Exarch",
        "Eater of Worlds",
    ]

    # Normalize Exarch/Eater into short forms
    INFLUENCE_NORMALIZATION = {
        "Searing Exarch": "Exarch",
        "Eater of Worlds": "Eater",
    }

    def parse(self, text: str) -> Optional[ParsedItem]:
        """
        Parse a single item from raw clipboard text.

        Returns ParsedItem or None if parsing fails or text is malformed.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        # Skip "Item Class:" line(s) if present (PoE includes this in clipboard)
        # Also skip any blank lines between Item Class and Rarity
        while lines and (lines[0].startswith("Item Class:") or not lines[0]):
            lines = lines[1:]

        # Must begin with Rarity (after skipping Item Class and blanks)
        if not lines or not RARITY_RE.match(lines[0]):
            return None

        item = ParsedItem(raw_text=text)

        try:
            lines = self._parse_header(lines, item)
            self._parse_body(lines, item)
        except Exception as e:
            # Fail closed - better to return None than misparse
            logger.debug(f"Item parse failed: {e}")
            return None

        # Final validation check: ensure useful minimum structure
        if not item.rarity or not (item.name or item.base_type):
            return None

        return item

    def parse_multiple(self, bulk_text: str) -> List[ParsedItem]:
        """
        Parse multiple items from a block of text.

        Items may be separated by:
        - blank lines, or
        - repeated "Rarity:" markers
        """
        blocks: List[str] = []
        current: List[str] = []

        for line in bulk_text.splitlines():
            if line.strip().startswith("Rarity:"):
                if current:
                    blocks.append("\n".join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            blocks.append("\n".join(current))

        items = []
        for blk in blocks:
            parsed = self.parse(blk)
            if parsed:
                items.append(parsed)

        return items

    # ------------------------------------------------------------------
    # Header Parsing
    # ------------------------------------------------------------------

    def _parse_header(self, lines: List[str], item: ParsedItem) -> List[str]:
        """
        Parse the header section of the item:
        - Rarity
        - Name
        - Base type (for rare/magic/unique, when present)
        Returns remaining lines after the header.
        """

        # Rarity: Rare / Magic / Unique / etc.
        match = RARITY_RE.match(lines[0])
        if match:
            item.rarity = match.group(1).upper()

        # Next line is item name (if present)
        if len(lines) > 1:
            item.name = lines[1]

        # Helper: is a given line a section separator ("--------")?
        def is_separator(idx: int) -> bool:
            return 0 <= idx < len(lines) and SEPARATOR_RE.match(lines[idx]) is not None

        # Non-unique items normally have a base type line after the name,
        # e.g.:
        #   Rarity: RARE
        #   Doom Visor
        #   Hubris Circlet
        #
        # But in some cases (like belts, jewels, or tests), the next line
        # is already the separator. In that case there is no separate
        # base_type line in the header.
        if item.rarity not in ("UNIQUE", "NORMAL") and len(lines) > 2:
            if is_separator(2):
                # No base_type line; header ends before the separator
                return lines[2:]
            item.base_type = lines[2]
            return lines[3:]

        # Unique items typically have:
        #   Rarity: UNIQUE
        #   Shavronne's Wrappings
        #   Occultist's Vestment
        if item.rarity == "UNIQUE" and len(lines) > 2:
            if is_separator(2):
                # No explicit base_type line before separator
                return lines[2:]
            item.base_type = lines[2]
            return lines[3:]

        # Fallback: just name + no base_type
        return lines[2:]

    # ------------------------------------------------------------------
    # Body Parsing
    # ------------------------------------------------------------------

    def _parse_body(self, lines: List[str], item: ParsedItem) -> None:
        """
        Parse the body sections of the item, which include:
        - Properties
        - Requirements
        - Influences
        - Flags
        - Mods (implicit, enchant, explicit)
        """
        current_section = 0
        in_requirements = False

        for line in lines:
            # Section break
            if SEPARATOR_RE.match(line):
                current_section += 1
                in_requirements = False
                continue

            # ───────────────────────────────────────────────
            # Item Properties
            # ───────────────────────────────────────────────

            # Item Level
            if m := ITEM_LEVEL_RE.match(line):
                item.item_level = int(m.group(1))
                continue

            # Spirit (PoE2)
            if line.startswith("Spirit:"):
                try:
                    item.spirit = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass  # Invalid spirit value, skip silently
                continue

            # Quality
            if m := QUALITY_SEARCH_RE.search(line):
                item.quality = int(m.group(1))
                continue

            # Sockets (handles both PoE1 gem sockets and PoE2 rune sockets)
            if line.startswith("Sockets:"):
                sockets = line.split(":", 1)[1].strip()
                item.sockets = sockets

                # PoE2 rune sockets: "S S S" format (space-separated S's)
                # Count 'S' characters for rune socket count
                if 'S' in sockets and not any(c in sockets for c in 'RGBW'):
                    item.rune_sockets = sockets.count('S')
                    item.links = 0  # Rune sockets don't link
                else:
                    # PoE1: Calculate links from largest connected group
                    groups = sockets.split(" ")
                    item.links = max(
                        len(g.replace("-", ""))
                        for g in groups
                    ) if groups else 0
                continue

            # Gem level
            m_level = LEVEL_RE.match(line)
            if m_level:
                try:
                    level_val = int(m_level.group(1))
                    # Only treat this as gem level when it's actually a gem
                    if (item.rarity or "").lower() == "gem":
                        item.gem_level = level_val
                except ValueError:
                    pass  # Invalid level value, skip silently
                continue

            # Quality (generic)
            m_q = QUALITY_RE.match(line)
            if m_q:
                try:
                    q_val = int(m_q.group(1))
                    item.quality = q_val
                    # Mirror quality to gem_quality for gems
                    if (item.rarity or "").lower() == "gem":
                        item.gem_quality = q_val
                except ValueError:
                    pass  # Invalid quality value, skip silently
                continue

            # Stack Size (currency)
            if m := STACK_RE.search(line):
                item.stack_size = int(m.group(1))
                item.max_stack_size = int(m.group(2))
                continue

            # ───────────────────────────────────────────────
            # Requirements
            # ───────────────────────────────────────────────

            if line.startswith("Requirements:"):
                in_requirements = True
                continue

            if in_requirements:
                self._parse_requirement_line(line, item)
                continue

            # ───────────────────────────────────────────────
            # Influences / Flags
            # ───────────────────────────────────────────────

            # Corrupted
            if "Corrupted" in line and "Uncorrupted" not in line:
                item.is_corrupted = True
                continue

            if "Fractured Item" in line:
                item.is_fractured = True
                continue

            if "Synthesised Item" in line:
                item.is_synthesised = True
                continue

            if "Mirrored" in line:
                item.is_mirrored = True
                continue

            # PoE2-specific flags
            if "Unmodifiable" in line:
                item.is_unmodifiable = True
                continue

            if "Sanctified" in line:
                item.is_sanctified = True
                continue

            # Influences
            found_influence = False
            for keyword in self.INFLUENCE_KEYWORDS:
                if keyword in line:
                    normalized = self.INFLUENCE_NORMALIZATION.get(keyword, keyword)
                    item.influences.append(normalized)
                    found_influence = True
                    break
            if found_influence:
                continue

            # ───────────────────────────────────────────────
            # Mods: implicit / enchant / explicit
            # Section 1+ contains mods in PoE clipboard format
            # ───────────────────────────────────────────────

            if current_section >= 1 and line:
                # Ignore lines belonging to other sections
                if any(kw in line for kw in ("Requirements:", "Level:", "Str:", "Dex:", "Int:")):
                    continue

                lower = line.lower()

                if "(enchant)" in lower:
                    clean = self._strip_tag(line, "enchant")
                    if clean:
                        item.enchants.append(clean)
                    continue

                if "(implicit)" in lower:
                    clean = self._strip_tag(line, "implicit")
                    if clean:
                        item.implicits.append(clean)
                    continue

                # PoE2: Rune mods (added rune)
                if "(rune)" in lower:
                    clean = self._strip_tag(line, "rune")
                    if clean:
                        item.rune_mods.append(clean)
                    continue

                # Otherwise it's a normal explicit mod
                item.explicits.append(line)

        # Post-processing: Cluster jewel detection
        if item.base_type and "Cluster Jewel" in item.base_type:
            self._parse_cluster_jewel(item)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _strip_tag(line: str, tag: str) -> str:
        """
        Remove (tag)/(Tag) from a line and strip whitespace.
        Example: "(implicit)" or "(Implicit)".
        """
        return (
            line.replace(f"({tag})", "")
                .replace(f"({tag.capitalize()})", "")
                .strip()
        )

    @staticmethod
    def _parse_requirement_line(line: str, item: ParsedItem) -> None:
        """Parse Level/Str/Dex/Int during requirements block."""
        if line.startswith("Level:"):
            try:
                item.requirements["level"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass  # Invalid requirement value, skip silently
            return

        for stat in ("Str", "Dex", "Int"):
            if line.startswith(f"{stat}:"):
                try:
                    item.requirements[stat.lower()] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass  # Invalid requirement value, skip silently
                return

    # ----------------------------------------------------------------------
    # Cluster Jewel Parsing
    # ----------------------------------------------------------------------

    # Regex for cluster jewel parsing
    CLUSTER_PASSIVE_COUNT_RE = re.compile(r"Adds (\d+) Passive Skill", re.IGNORECASE)
    CLUSTER_NOTABLE_RE = re.compile(r"1 Added Passive Skill is (.+)", re.IGNORECASE)
    CLUSTER_SOCKET_RE = re.compile(r"Adds? (\d+) Jewel Sockets?", re.IGNORECASE)

    # Mapping of keywords to enchantment types
    CLUSTER_ENCHANT_PATTERNS = {
        "fire damage": "fire_damage",
        "burning damage": "fire_damage",
        "ignite": "fire_damage",
        "cold damage": "cold_damage",
        "freeze": "cold_damage",
        "chill": "cold_damage",
        "lightning damage": "lightning_damage",
        "shock": "lightning_damage",
        "chaos damage": "chaos_damage",
        "poison": "chaos_damage",
        "physical damage": "physical_damage",
        "impale": "physical_damage",
        "elemental damage": "elemental_damage",
        "attack damage": "attack_damage",
        "attack speed": "attack_damage",
        "accuracy": "attack_damage",
        "spell damage": "spell_damage",
        "cast speed": "spell_damage",
        "minion damage": "minion_damage",
        "minions deal": "minion_damage",
        "minion life": "minion_life",
        "minion maximum life": "minion_life",
        "maximum life": "life",
        "life regeneration": "life",
        "maximum mana": "mana",
        "mana regeneration": "mana",
        "energy shield": "energy_shield",
        "maximum energy shield": "energy_shield",
        "armour": "armour",
        "physical damage reduction": "armour",
        "evasion": "evasion",
        "evasion rating": "evasion",
        "critical strike": "crit",
        "critical": "crit",
        "curse effect": "curse",
        "cursed enemies": "curse",
        "aura effect": "aura",
        "non-curse auras": "aura",
        "skill effect duration": "effect_duration",
        "totem damage": "totem",
        "totem life": "totem",
        "trap damage": "trap",
        "trap throwing speed": "trap",
        "mine damage": "mine",
        "mine throwing speed": "mine",
        "brand damage": "brand",
        "brand attachment": "brand",
        "channelling skill": "channelling",
    }

    def _parse_cluster_jewel(self, item: ParsedItem) -> None:
        """Parse cluster jewel specific properties from enchants and explicits."""
        # Determine size from base type
        base = item.base_type or ""
        if "Large" in base:
            item.cluster_jewel_size = "Large"
        elif "Medium" in base:
            item.cluster_jewel_size = "Medium"
        elif "Small" in base:
            item.cluster_jewel_size = "Small"

        # Parse enchantments for passive count and skill type
        for enchant in item.enchants:
            # Extract passive count: "Adds 8 Passive Skills"
            if m := self.CLUSTER_PASSIVE_COUNT_RE.search(enchant):
                item.cluster_jewel_passives = int(m.group(1))

            # Check for skill type enchantment: "Added Small Passive Skills grant: ..."
            if "Added Small Passive Skills grant" in enchant or "grant:" in enchant.lower():
                item.cluster_jewel_enchantment_text = enchant
                item.cluster_jewel_enchantment = self._identify_cluster_enchantment(enchant)

        # Parse explicits for notables and jewel sockets
        for mod in item.explicits:
            # Extract notable: "1 Added Passive Skill is Blowback"
            if m := self.CLUSTER_NOTABLE_RE.match(mod):
                notable_name = m.group(1).strip()
                item.cluster_jewel_notables.append(notable_name)
                continue

            # Count jewel sockets: "Adds 1 Jewel Socket"
            if m := self.CLUSTER_SOCKET_RE.search(mod):
                item.cluster_jewel_sockets += int(m.group(1))

    def _identify_cluster_enchantment(self, enchant_text: str) -> str:
        """Identify the enchantment type from full enchantment text."""
        enchant_lower = enchant_text.lower()

        for pattern, enchant_type in self.CLUSTER_ENCHANT_PATTERNS.items():
            if pattern in enchant_lower:
                return enchant_type

        return "unknown"


if __name__ == "__main__":  # pragma: no cover
    print("=== Item Parser Smoke Test ===")
    parser = ItemParser()
    sample = """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 84
Quality: +20%
Sockets: R-G-B R-R
--------
+80 to maximum Energy Shield (implicit)
--------
+50 to maximum Life
Corrupted
"""
    result = parser.parse(sample)
    print(result)
    if result:
        print(result.to_dict())
