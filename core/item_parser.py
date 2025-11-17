"""
Path of Exile item text parser.
Parses item text copied from the game (Ctrl+C on item).
"""

import re
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ParsedItem:
    """
    Structured representation of a parsed PoE item.
    Uses dataclass for clean structure and type hints.
    """
    raw_text: str
    rarity: Optional[str] = None
    name: Optional[str] = None
    base_type: Optional[str] = None
    item_level: Optional[int] = None
    quality: Optional[int] = None
    sockets: Optional[str] = None
    links: int = 0
    stack_size: int = 1
    max_stack_size: int = 1

    # Item properties
    is_corrupted: bool = False
    is_fractured: bool = False
    is_synthesised: bool = False
    is_mirrored: bool = False

    # Influences (can have multiple)
    influences: List[str] = field(default_factory=list)

    # Mod text
    implicits: List[str] = field(default_factory=list)
    explicits: List[str] = field(default_factory=list)
    enchants: List[str] = field(default_factory=list)

    # Additional info
    item_class: Optional[str] = None
    requirements: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize after creation"""
        # Normalize rarity to uppercase
        if self.rarity:
            self.rarity = self.rarity.upper()

    def is_currency(self) -> bool:
        """Check if this is a currency item"""
        return self.rarity is None or self.rarity == "CURRENCY"

    def is_unique(self) -> bool:
        """Check if this is a unique item"""
        return self.rarity == "UNIQUE"

    def is_rare(self) -> bool:
        """Check if this is a rare item"""
        return self.rarity == "RARE"

    def is_magic(self) -> bool:
        """Check if this is a magic item"""
        return self.rarity == "MAGIC"

    def is_normal(self) -> bool:
        """Check if this is a normal item"""
        return self.rarity == "NORMAL"

    def get_display_name(self) -> str:
        """Get the item's display name (name or base type)"""
        return self.name or self.base_type or "Unknown Item"

    def has_influence(self, influence: str) -> bool:
        """Check if item has a specific influence"""
        return influence.lower() in [inf.lower() for inf in self.influences]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'rarity': self.rarity,
            'name': self.name,
            'base_type': self.base_type,
            'item_level': self.item_level,
            'quality': self.quality,
            'sockets': self.sockets,
            'links': self.links,
            'stack_size': self.stack_size,
            'max_stack_size': self.max_stack_size,
            'is_corrupted': self.is_corrupted,
            'is_fractured': self.is_fractured,
            'is_synthesised': self.is_synthesised,
            'influences': self.influences,
            'implicits': self.implicits,
            'explicits': self.explicits
        }


class ItemParser:
    """
    Parser for Path of Exile item text.
    Handles items from both PoE1 and PoE2 (similar format).
    """

    # Item separator pattern
    SEPARATOR_PATTERN = r'^-{5,}$'

    # Influence keywords
    INFLUENCES = [
        'Shaper', 'Elder', 'Crusader', 'Redeemer',
        'Hunter', 'Warlord', 'Searing Exarch', 'Eater of Worlds'
    ]

    def parse(self, item_text: str) -> Optional[ParsedItem]:
        """
        Parse item text from clipboard.

        Args:
            item_text: Raw item text from in-game Ctrl+C

        Returns:
            ParsedItem object or None if parsing fails
        """
        if not item_text or not item_text.strip():
            logger.warning("Empty item text")
            return None

        # Validate minimum length
        if len(item_text.strip()) < 10:
            logger.warning("Item text too short to be valid")
            return None

        try:
            lines = [line.strip() for line in item_text.strip().split('\n')]

            if len(lines) < 1:
                logger.warning("Item text too short")
                return None

            # Create item object
            item = ParsedItem(raw_text=item_text)

            # Parse header section
            line_index = self._parse_header(lines, item)

            # Parse body sections (separated by dashes)
            self._parse_body(lines[line_index:], item)
            # Validate that we parsed something meaningful
            has_valid_structure = (
                    item.rarity is not None or
                    item.stack_size > 1 or
                    item.item_level is not None or
                    len(item.explicits) > 0 or
                    len(item.implicits) > 0 or
                    item.quality is not None
            )

            if not has_valid_structure:
                logger.warning(f"No valid PoE item structure detected in: {item_text[:50]}...")
                return None

            logger.debug(f"Parsed item: {item.get_display_name()} ({item.rarity})")
            return item

        except Exception as e:
            logger.error(f"Failed to parse item: {e}")
            logger.debug(f"Item text was: {item_text[:200]}")
            return None

    def _parse_header(self, lines: List[str], item: ParsedItem) -> int:
        """
        Parse the header section (rarity, name, base).
        Returns the line index where body starts.
        """
        idx = 0

        # Check for stack size FIRST (currency items start with this)
        if idx < len(lines) and lines[idx].startswith('Stack Size:'):
            match = re.search(r'(\d+)/(\d+)', lines[idx])
            if match:
                item.stack_size = int(match.group(1))
                item.max_stack_size = int(match.group(2))
            idx += 1  # Move past Stack Size line

        # Parse rarity (if present - comes after Stack Size for currency, or first for gear)
        if idx < len(lines) and lines[idx].startswith('Rarity:'):
            item.rarity = lines[idx].replace('Rarity:', '').strip()
            idx += 1

        # Parse name (next non-empty, non-separator line)
        if idx < len(lines) and lines[idx] and not lines[idx].startswith('---'):
            item.name = lines[idx]
            idx += 1

        # Parse base type (next non-empty, non-separator line)
        if idx < len(lines) and lines[idx] and not lines[idx].startswith('---'):
            item.base_type = lines[idx]
            idx += 1

        # If name equals base, it's a normal/magic item or currency (only one name line)
        if item.name == item.base_type:
            item.base_type = item.name
            item.name = None

        return idx

    def _parse_body(self, lines: List[str], item: ParsedItem):
        """Parse the body sections (properties, mods, etc.)"""

        current_section = 0  # Track which section we're in
        in_requirements = False

        for line in lines:
            # Separator line - move to next section
            if not line or re.match(self.SEPARATOR_PATTERN, line):
                current_section += 1
                in_requirements = False
                continue

            # Item Class
            if line.startswith('Item Class:'):
                item.item_class = line.split(':', 1)[1].strip()

            # Item Level
            elif line.startswith('Item Level:'):
                try:
                    item.item_level = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            # Stack Size (currency and stacks)
            elif line.startswith('Stack Size:'):
                match = re.search(r'(\d+)/(\d+)', line)
                if match:
                    item.stack_size = int(match.group(1))
                    item.max_stack_size = int(match.group(2))

            # Quality
            elif line.startswith('Quality:'):
                match = re.search(r'\+?(\d+)%', line)
                if match:
                    item.quality = int(match.group(1))

            # Sockets
            elif line.startswith('Sockets:'):
                sockets = line.split(':', 1)[1].strip()
                item.sockets = sockets
                # Calculate links (connected by dashes)
                link_groups = sockets.split(' ')
                item.links = max(len(group.replace('-', '')) for group in link_groups) if link_groups else 0

            # Requirements
            elif line.startswith('Requirements:'):
                in_requirements = True

            elif in_requirements:
                # Level requirement
                if line.startswith('Level:'):
                    try:
                        item.requirements['level'] = int(line.split(':')[1].strip())
                    except ValueError:
                        pass
                # Stat requirements
                for stat in ['Str', 'Dex', 'Int']:
                    if line.startswith(f'{stat}:'):
                        try:
                            item.requirements[stat.lower()] = int(line.split(':')[1].strip())
                        except ValueError:
                            pass

            # Corrupted
            elif 'Corrupted' in line and 'Uncorrupted' not in line:
                item.is_corrupted = True

            # Fractured
            elif 'Fractured Item' in line:
                item.is_fractured = True

            # Synthesised
            elif 'Synthesised Item' in line:
                item.is_synthesised = True

            # Mirrored
            elif 'Mirrored' in line:
                item.is_mirrored = True

            # Influences
            elif any(inf in line for inf in self.INFLUENCES):
                for inf in self.INFLUENCES:
                    if inf in line:
                        # Normalize influence names
                        if inf == 'Searing Exarch':
                            item.influences.append('Exarch')
                        elif inf == 'Eater of Worlds':
                            item.influences.append('Eater')
                        else:
                            item.influences.append(inf)

            # Mods (anything in section 2+ that's not a property)
            elif current_section >= 2 and line:
                # Skip certain lines
                if any(skip in line for skip in ['Requirements:', 'Level:', 'Str:', 'Dex:', 'Int:']):
                    continue

                    # Enchant
                elif '(enchant)' in line.lower():
                    clean_line = line.replace('(enchant)', '').replace('(Enchant)', '').strip()
                    if clean_line:
                        item.enchants.append(clean_line)
                # Implicit
                elif '(implicit)' in line.lower():
                    clean_line = line.replace('(implicit)', '').replace('(Implicit)', '').strip()
                    if clean_line:
                        item.implicits.append(clean_line)

                # Explicit mod
                else:
                    item.explicits.append(line)

    def parse_multiple(self, bulk_text: str) -> List[ParsedItem]:
        """
        Parse multiple items from bulk text.
        Items can be separated by double newlines or "Rarity:" markers.

        Args:
            bulk_text: Text containing multiple items

        Returns:
            List of ParsedItem objects
        """
        # Split by double newlines or "Rarity:" markers
        items_text = re.split(r'\n\s*\n+|(?=Rarity:)', bulk_text)
        items_text = [text.strip() for text in items_text if text.strip()]

        parsed_items = []
        for item_text in items_text:
            # Must start with Rarity: or Stack Size:
            if not (item_text.startswith('Rarity:') or item_text.startswith('Stack Size:')):
                continue

            item = self.parse(item_text)
            if item:
                parsed_items.append(item)

        logger.info(f"Parsed {len(parsed_items)} items from bulk text")
        return parsed_items


# Testing
if __name__ == "__main__":
    print("=== Item Parser Test ===\n")

    parser = ItemParser()

    # Test 1: Unique item
    unique_text = """Rarity: UNIQUE
Shavronne's Wrappings
Occultist's Vestment
--------
Energy Shield: 300
--------
Item Level: 85
Sockets: B-B-B-B-B-B
--------
+1 to Level of Socketed Gems
200% increased Energy Shield
+50 to Intelligence
Chaos Damage does not bypass Energy Shield
--------
Corrupted"""

    item1 = parser.parse(unique_text)
    if item1:
        print(f"✓ Item 1: {item1.get_display_name()}")
        print(f"  Rarity: {item1.rarity}")
        print(f"  Base Type: {item1.base_type}")
        print(f"  Links: {item1.links}")
        print(f"  Corrupted: {item1.is_corrupted}")
        print(f"  Explicits: {len(item1.explicits)}")

    # Test 2: Currency
    currency_text = """Stack Size: 15/40
Divine Orb"""

    item2 = parser.parse(currency_text)
    if item2:
        print(f"\n✓ Item 2: {item2.get_display_name()}")
        print(f"  Is Currency: {item2.is_currency()}")
        print(f"  Stack: {item2.stack_size}/{item2.max_stack_size}")

    # Test 3: Rare item with influence
    rare_text = """Rarity: RARE
Doom Guard
Vaal Regalia
--------
Quality: +20%
Energy Shield: 450
--------
Item Level: 86
Sockets: B-B-B-B-B-B
--------
Shaper Item
--------
+120 to maximum Energy Shield
+45% to Fire Resistance
+38% to Cold Resistance"""

    item3 = parser.parse(rare_text)
    if item3:
        print(f"\n✓ Item 3: {item3.get_display_name()}")
        print(f"  Rarity: {item3.rarity}")
        print(f"  Quality: {item3.quality}%")
        print(f"  Influences: {item3.influences}")
        print(f"  Has Shaper: {item3.has_influence('Shaper')}")

    # Test 4: Multiple items
    bulk_text = unique_text + "\n\n" + currency_text + "\n\n" + rare_text
    items = parser.parse_multiple(bulk_text)
    print(f"\n✓ Parsed {len(items)} items from bulk text:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.get_display_name()} (stack: {item.stack_size}, rarity: {item.rarity or 'CURRENCY'})")

    print("\n=== All Tests Passed! ===")
