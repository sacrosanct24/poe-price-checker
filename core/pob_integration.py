"""
Path of Building (PoB) Integration.

Provides functionality to:
1. Decode PoB pastebin/share codes into build data
2. Extract character equipment for upgrade comparison
3. Compare items against character's current gear
4. Store multiple character profiles

PoB codes are base64-encoded, zlib-compressed XML.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


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
        groups = self.sockets.replace(" ", "").split("-")
        # Each group connected by - is linked
        # But sockets format might be like "R-R-R G-G B" where space separates groups
        # Let's handle both formats
        if " " in self.sockets:
            groups = self.sockets.split(" ")
            return max(len(g.replace("-", "")) for g in groups) if groups else 0
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

    def get_item_for_slot(self, slot: str) -> Optional[PoBItem]:
        """Get the item equipped in a specific slot."""
        return self.build.items.get(slot)


class PoBDecoder:
    """
    Decodes Path of Building share codes into build data.

    PoB codes are:
    1. URL-safe base64 encoded
    2. zlib compressed
    3. XML formatted
    """

    # Slot mappings from PoB XML to standard names
    SLOT_MAPPING = {
        "Weapon 1": "Weapon",
        "Weapon 2": "Offhand",
        "Weapon 1 Swap": "Weapon Swap",
        "Weapon 2 Swap": "Offhand Swap",
        "Helmet": "Helmet",
        "Body Armour": "Body Armour",
        "Gloves": "Gloves",
        "Boots": "Boots",
        "Amulet": "Amulet",
        "Ring 1": "Ring 1",
        "Ring 2": "Ring 2",
        "Belt": "Belt",
        "Flask 1": "Flask 1",
        "Flask 2": "Flask 2",
        "Flask 3": "Flask 3",
        "Flask 4": "Flask 4",
        "Flask 5": "Flask 5",
    }

    @staticmethod
    def decode_pob_code(code: str) -> str:
        """
        Decode a PoB share code to XML.

        Args:
            code: The PoB share code (base64 encoded, zlib compressed)

        Returns:
            Decoded XML string
        """
        # Remove any whitespace/newlines
        code = code.strip().replace("\n", "").replace("\r", "")

        # Handle pastebin URLs
        if "pastebin.com" in code:
            code = PoBDecoder._fetch_pastebin(code)
        elif "pobb.in" in code:
            code = PoBDecoder._fetch_pobbin(code)

        # PoB uses URL-safe base64 with some modifications
        # Replace - with + and _ with /
        code = code.replace("-", "+").replace("_", "/")

        # Add padding if needed
        padding = 4 - (len(code) % 4)
        if padding != 4:
            code += "=" * padding

        try:
            # Decode base64
            decoded = base64.b64decode(code)

            # Decompress zlib
            xml_data = zlib.decompress(decoded)

            return xml_data.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to decode PoB code: {e}")
            raise ValueError(f"Invalid PoB code: {e}")

    @staticmethod
    def _fetch_pastebin(url: str) -> str:
        """Fetch raw content from a pastebin URL."""
        # Convert to raw URL
        if "/raw/" not in url:
            paste_id = url.split("/")[-1]
            url = f"https://pastebin.com/raw/{paste_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to fetch pastebin: {e}")
            raise ValueError(f"Could not fetch pastebin: {e}")

    @staticmethod
    def _fetch_pobbin(url: str) -> str:
        """Fetch raw PoB code from a pobb.in URL."""
        # pobb.in uses /u/{id}/raw or we can fetch from API
        paste_id = url.rstrip("/").split("/")[-1]

        # Try the raw endpoint first
        raw_url = f"https://pobb.in/{paste_id}/raw"

        try:
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            return response.text.strip()
        except Exception:
            # Fallback: try the API endpoint
            api_url = f"https://pobb.in/api/v1/paste/{paste_id}"
            try:
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                # The API returns the code in a 'code' or 'content' field
                return data.get("code") or data.get("content", "")
            except Exception as e:
                logger.error(f"Failed to fetch pobb.in: {e}")
                raise ValueError(f"Could not fetch pobb.in: {e}")

    @staticmethod
    def parse_build(xml_string: str) -> PoBBuild:
        """
        Parse PoB XML into a PoBBuild object.

        Args:
            xml_string: Decoded XML from PoB

        Returns:
            PoBBuild object with extracted data
        """
        build = PoBBuild(raw_xml=xml_string)

        try:
            root = ET.fromstring(xml_string)

            # Extract build info
            build_elem = root.find("Build")
            if build_elem is not None:
                build.level = int(build_elem.get("level", 1))
                build.class_name = build_elem.get("className", "")
                build.ascendancy = build_elem.get("ascendClassName", "")
                build.bandit = build_elem.get("bandit", "None")
                build.main_skill = build_elem.get("mainSocketGroup", "")

            # Extract items
            items_elem = root.find("Items")
            if items_elem is not None:
                # First, parse all items and store by their ID
                items_by_id: Dict[str, PoBItem] = {}
                for item_elem in items_elem.findall("Item"):
                    item = PoBDecoder._parse_item(item_elem)
                    if item:
                        item_id = item_elem.get("id", "")
                        items_by_id[item_id] = item

                # Then, map items to slots using Slot elements
                # Slots can be directly under Items, or inside ItemSet elements
                slot_elements = list(items_elem.findall("Slot"))

                # Also check inside ItemSet elements (newer PoB format)
                active_item_set = items_elem.get("activeItemSet", "1")
                for item_set in items_elem.findall("ItemSet"):
                    item_set_id = item_set.get("id", "")
                    # Prefer the active item set, but fall back to any if none active
                    if item_set_id == active_item_set or not slot_elements:
                        slot_elements.extend(item_set.findall("Slot"))

                for slot_elem in slot_elements:
                    slot_name = slot_elem.get("name", "")
                    item_id = slot_elem.get("itemId", "")

                    # Skip special slots like abyssal sockets, grafts for now
                    if "Abyssal" in slot_name or "Graft" in slot_name:
                        continue

                    # Skip slots with itemId of 0 (empty)
                    if not item_id or item_id == "0":
                        continue

                    if item_id in items_by_id:
                        item = items_by_id[item_id]
                        item.slot = slot_name
                        build.items[slot_name] = item

            # Extract skills
            skills_elem = root.find("Skills")
            if skills_elem is not None:
                for skill_elem in skills_elem.findall("Skill"):
                    skill_name = skill_elem.get("label", "")
                    if skill_name:
                        build.skills.append(skill_name)

            # Extract config
            config_elem = root.find("Config")
            if config_elem is not None:
                for input_elem in config_elem.findall("Input"):
                    name = input_elem.get("name", "")
                    value = input_elem.get("boolean") or input_elem.get("number") or input_elem.get("string")
                    if name and value:
                        build.config[name] = value

        except ET.ParseError as e:
            logger.error(f"Failed to parse PoB XML: {e}")
            raise ValueError(f"Invalid PoB XML: {e}")

        return build

    @staticmethod
    def _parse_item(item_elem: ET.Element) -> Optional[PoBItem]:
        """Parse an item element from PoB XML."""
        raw_text = item_elem.text or ""
        if not raw_text.strip():
            return None

        # PoB item format:
        # Rarity: RARE/UNIQUE/etc
        # Item Name
        # Base Type
        # [Unique ID: ...]
        # [Elder Item / Shaper Item / etc]
        # Item Level: N
        # [Quality: N]
        # [Sockets: ...]
        # LevelReq: N
        # Implicits: N
        # [implicit mods - N lines]
        # [explicit mods - remaining lines]
        # {crafted} prefix for crafted mods

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

        # Parse item attributes from XML element
        item.slot = item_elem.get("id", "")

        # Metadata fields to skip when parsing mods
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
        parsing_explicits = False

        for i, line in enumerate(lines):
            # Skip empty lines
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

            # Skip metadata lines
            if any(line.startswith(prefix) for prefix in METADATA_PREFIXES):
                # Extract specific values
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

            # If we have implicits remaining, this line is an implicit mod
            if implicits_remaining > 0:
                # Clean up the mod text (remove tags like {crafted}, {fractured}, etc.)
                mod = re.sub(r"\{[^}]+\}", "", line).strip()
                if mod:
                    item.implicit_mods.append(mod)
                implicits_remaining -= 1
                if implicits_remaining == 0:
                    parsing_explicits = True
                continue

            # If we've parsed all implicits (or there were none), this is an explicit mod
            if implicit_count >= 0:
                # After Implicits line, everything else is explicit mods
                # Clean up the mod text (remove tags but keep the mod readable)
                mod = line
                # Extract tag info but keep in clean format
                is_crafted = "{crafted}" in mod.lower()
                is_fractured = "{fractured}" in mod.lower()

                # Remove tags for clean mod text
                mod = re.sub(r"\{[^}]+\}", "", mod).strip()

                if mod:
                    # Optionally mark crafted/fractured mods
                    if is_crafted:
                        mod = f"(crafted) {mod}"
                    elif is_fractured:
                        mod = f"(fractured) {mod}"
                    item.explicit_mods.append(mod)

        return item

    @staticmethod
    def from_code(code: str) -> PoBBuild:
        """
        Decode a PoB code and parse it into a build.

        Args:
            code: PoB share code or pastebin URL

        Returns:
            PoBBuild object
        """
        xml_string = PoBDecoder.decode_pob_code(code)
        return PoBDecoder.parse_build(xml_string)


class CharacterManager:
    """
    Manages stored character profiles for upgrade comparisons.

    Stores profiles in a JSON file for persistence.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the character manager.

        Args:
            storage_path: Path to store character profiles
        """
        self.storage_path = storage_path or Path(__file__).parent.parent / "data" / "characters.json"
        self._profiles: Dict[str, CharacterProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, profile_data in data.items():
                    self._profiles[name] = self._deserialize_profile(profile_data)
                logger.info(f"Loaded {len(self._profiles)} character profiles")
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")

    def _save_profiles(self):
        """Save profiles to storage file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                name: self._serialize_profile(profile)
                for name, profile in self._profiles.items()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def _serialize_profile(self, profile: CharacterProfile) -> dict:
        """Serialize a profile to dict for JSON storage."""
        return {
            "name": profile.name,
            "pob_code": profile.pob_code,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "notes": profile.notes,
            "build": {
                "class_name": profile.build.class_name,
                "ascendancy": profile.build.ascendancy,
                "level": profile.build.level,
                "main_skill": profile.build.main_skill,
                "items": {
                    slot: {
                        "slot": item.slot,
                        "rarity": item.rarity,
                        "name": item.name,
                        "base_type": item.base_type,
                        "item_level": item.item_level,
                        "quality": item.quality,
                        "sockets": item.sockets,
                        "implicit_mods": item.implicit_mods,
                        "explicit_mods": item.explicit_mods,
                    }
                    for slot, item in profile.build.items.items()
                },
            },
        }

    def _deserialize_profile(self, data: dict) -> CharacterProfile:
        """Deserialize a profile from dict."""
        build_data = data.get("build", {})
        build = PoBBuild(
            class_name=build_data.get("class_name", ""),
            ascendancy=build_data.get("ascendancy", ""),
            level=build_data.get("level", 1),
            main_skill=build_data.get("main_skill", ""),
        )

        for slot, item_data in build_data.get("items", {}).items():
            build.items[slot] = PoBItem(
                slot=item_data.get("slot", ""),
                rarity=item_data.get("rarity", "RARE"),
                name=item_data.get("name", ""),
                base_type=item_data.get("base_type", ""),
                item_level=item_data.get("item_level", 0),
                quality=item_data.get("quality", 0),
                sockets=item_data.get("sockets", ""),
                implicit_mods=item_data.get("implicit_mods", []),
                explicit_mods=item_data.get("explicit_mods", []),
            )

        return CharacterProfile(
            name=data.get("name", ""),
            build=build,
            pob_code=data.get("pob_code", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            notes=data.get("notes", ""),
        )

    def add_from_pob_code(self, name: str, pob_code: str, notes: str = "") -> CharacterProfile:
        """
        Add a character from a PoB code.

        Args:
            name: Character name
            pob_code: PoB share code or pastebin URL
            notes: Optional notes

        Returns:
            Created CharacterProfile
        """
        from datetime import datetime

        build = PoBDecoder.from_code(pob_code)
        now = datetime.now().isoformat()

        profile = CharacterProfile(
            name=name,
            build=build,
            pob_code=pob_code,
            created_at=now,
            updated_at=now,
            notes=notes,
        )

        self._profiles[name] = profile
        self._save_profiles()

        logger.info(f"Added character profile: {name}")
        return profile

    def get_profile(self, name: str) -> Optional[CharacterProfile]:
        """Get a character profile by name."""
        return self._profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all profile names."""
        return list(self._profiles.keys())

    def delete_profile(self, name: str) -> bool:
        """Delete a character profile."""
        if name in self._profiles:
            del self._profiles[name]
            self._save_profiles()
            return True
        return False

    def get_active_profile(self) -> Optional[CharacterProfile]:
        """Get the first/active profile (for simple single-character use)."""
        if self._profiles:
            return next(iter(self._profiles.values()))
        return None


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


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("POB INTEGRATION TEST")
    print("=" * 60)

    # Test with a sample PoB code (this is a simple test code)
    # You can replace this with a real PoB pastebin URL
    test_code = None

    if test_code:
        print("\n1. Testing PoB code decoding...")
        try:
            build = PoBDecoder.from_code(test_code)
            print(f"   Class: {build.class_name}")
            print(f"   Ascendancy: {build.ascendancy}")
            print(f"   Level: {build.level}")
            print(f"   Items: {len(build.items)}")

            for slot, item in build.items.items():
                print(f"     {slot}: {item.display_name}")

        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("\n1. Skipping PoB decode test (no test code provided)")

    print("\n2. Testing CharacterManager...")
    manager = CharacterManager()
    print(f"   Profiles: {manager.list_profiles()}")

    print("\n3. Testing UpgradeChecker...")
    checker = UpgradeChecker(manager)
    slots = checker.get_applicable_slots("Body Armour")
    print(f"   Body Armour fits in: {slots}")

    print("\n" + "=" * 60)
