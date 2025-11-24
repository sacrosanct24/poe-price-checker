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

import re
from dataclasses import dataclass, field
from typing import Optional, List

from core.game_version import GameVersion
LEVEL_RE = re.compile(r"^Level:\s*(\d+)")
QUALITY_RE = re.compile(r"^Quality:\s*\+?(-?\d+)%")

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
        }

# ----------------------------------------------------------------------
# Parser Implementation
# ----------------------------------------------------------------------

class ItemParser:
    """
    Full item parser for PoE clipboard text.

    Handles header, body, modifiers, influences, requirements,
    sockets, corruptions, etc.
    """

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
        if not lines or not re.match(self.RARITY_PATTERN, lines[0]):
            return None

        item = ParsedItem(raw_text=text)

        try:
            lines = self._parse_header(lines, item)
            self._parse_body(lines, item)
        except Exception:
            # Fail closed - better to return None than misparse
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
        match = re.match(self.RARITY_PATTERN, lines[0])
        if match:
            item.rarity = match.group(1).upper()

        # Next line is item name (if present)
        if len(lines) > 1:
            item.name = lines[1]

        # Helper: is a given line a section separator ("--------")?
        def is_separator(idx: int) -> bool:
            return 0 <= idx < len(lines) and re.match(self.SEPARATOR_PATTERN, lines[idx]) is not None

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
            if re.match(self.SEPARATOR_PATTERN, line):
                current_section += 1
                in_requirements = False
                continue

            # ───────────────────────────────────────────────
            # Item Properties
            # ───────────────────────────────────────────────

            # Item Level
            if m := re.match(self.ITEM_LEVEL_PATTERN, line):
                item.item_level = int(m.group(1))
                continue

            # Quality
            if m := re.search(self.QUALITY_PATTERN, line):
                item.quality = int(m.group(1))
                continue

            # Sockets
            if line.startswith("Sockets:"):
                sockets = line.split(":", 1)[1].strip()
                item.sockets = sockets

                # Calculate links: largest connected group
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
                    # Only treat this as gem level when it’s actually a gem
                    if (item.rarity or "").lower() == "gem":
                        item.gem_level = level_val
                except ValueError:
                    pass
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
                    pass
                continue

            # Stack Size (currency)
            if m := re.search(self.STACK_PATTERN, line):
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

                # Otherwise it's a normal explicit mod
                item.explicits.append(line)

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
                pass
            return

        for stat in ("Str", "Dex", "Int"):
            if line.startswith(f"{stat}:"):
                try:
                    item.requirements[stat.lower()] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                return


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
    print(result.to_dict())
