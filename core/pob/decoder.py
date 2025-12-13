"""
PoB decoder - decodes Path of Building share codes into build data.

PoB codes are base64-encoded, zlib-compressed XML.
"""

from __future__ import annotations

import base64
import logging
import re
import zlib
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

from core.constants import API_TIMEOUT_DEFAULT

# Use defusedxml to prevent XXE (XML External Entity) attacks
# PoB codes from untrusted sources could contain malicious XML
import defusedxml.ElementTree as ET

from core.pob.models import PoBBuild, PoBItem

logger = logging.getLogger(__name__)

# Allowed hosts for PoB code fetching
_PASTEBIN_HOSTS = frozenset({'pastebin.com', 'www.pastebin.com'})
_POBBIN_HOSTS = frozenset({'pobb.in', 'www.pobb.in'})


def _is_pastebin_url(url: str) -> bool:
    """Check if URL is from pastebin.com using proper hostname validation."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in _PASTEBIN_HOSTS
    except Exception:
        return False


def _is_pobbin_url(url: str) -> bool:
    """Check if URL is from pobb.in using proper hostname validation."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in _POBBIN_HOSTS
    except Exception:
        return False


def _url_host_matches(url: str, host: str) -> bool:
    """Check if URL's hostname matches the given host (case-insensitive)."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        return netloc == host or netloc == f'www.{host}'
    except Exception:
        return False


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

    # Maximum sizes to prevent denial-of-service attacks
    MAX_CODE_SIZE = 500_000  # 500KB encoded (most PoB codes are < 50KB)
    MAX_XML_SIZE = 10_000_000  # 10MB decompressed (prevents zip bombs)

    @staticmethod
    def decode_pob_code(code: str) -> str:
        """
        Decode a PoB share code to XML.

        Args:
            code: The PoB share code (base64 encoded, zlib compressed)

        Returns:
            Decoded XML string

        Raises:
            ValueError: If code is invalid, too large, or decompresses to excessive size
        """
        # Remove any whitespace/newlines
        code = code.strip().replace("\n", "").replace("\r", "")

        # Security: Reject excessively large inputs
        if len(code) > PoBDecoder.MAX_CODE_SIZE:
            raise ValueError(f"PoB code too large ({len(code)} bytes, max {PoBDecoder.MAX_CODE_SIZE})")

        # Handle pastebin URLs - use proper URL parsing to prevent bypass attacks
        if _is_pastebin_url(code):
            code = PoBDecoder._fetch_pastebin(code)
        elif _is_pobbin_url(code):
            code = PoBDecoder._fetch_pobbin(code)
        elif PoBDecoder._looks_like_url(code):
            # Detect URLs from sites that don't have PoB codes directly
            PoBDecoder._raise_url_error(code)

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

            # Decompress zlib with size limit to prevent zip bombs
            # Use decompressobj to control decompression size
            decompressor = zlib.decompressobj()
            xml_data = decompressor.decompress(decoded, PoBDecoder.MAX_XML_SIZE)

            # Check if there's more data (would indicate zip bomb)
            if decompressor.unconsumed_tail:
                raise ValueError(
                    f"Decompressed data exceeds maximum size ({PoBDecoder.MAX_XML_SIZE} bytes)"
                )

            return xml_data.decode("utf-8")

        except zlib.error as e:
            logger.error(f"Failed to decompress PoB code: {e}")
            raise ValueError(f"Invalid PoB code (decompression failed): {e}")
        except Exception as e:
            logger.error(f"Failed to decode PoB code: {e}")
            raise ValueError(f"Invalid PoB code: {e}")

    @staticmethod
    def _fetch_pastebin(url: str) -> str:
        """Fetch raw content from a pastebin URL."""
        # Convert to raw URL using urlparse for security
        parsed = urlparse(url)
        if "/raw/" not in parsed.path:
            # Extract paste ID from path (last segment)
            path_parts = parsed.path.rstrip("/").split("/")
            paste_id = path_parts[-1] if path_parts else ""
            if not paste_id:
                raise ValueError("Invalid pastebin URL: no paste ID found")
            url = f"https://pastebin.com/raw/{paste_id}"

        try:
            response = requests.get(url, timeout=API_TIMEOUT_DEFAULT)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to fetch pastebin: {e}")
            raise ValueError(f"Could not fetch pastebin: {e}")

    @staticmethod
    def _fetch_pobbin(url: str) -> str:
        """Fetch raw PoB code from a pobb.in URL."""
        # pobb.in uses /u/{id}/raw or we can fetch from API
        # Use urlparse for secure URL parsing
        parsed = urlparse(url)
        path_parts = parsed.path.rstrip("/").split("/")
        paste_id = path_parts[-1] if path_parts else ""
        if not paste_id:
            raise ValueError("Invalid pobb.in URL: no paste ID found")

        # Try the raw endpoint first
        raw_url = f"https://pobb.in/{paste_id}/raw"

        try:
            response = requests.get(raw_url, timeout=API_TIMEOUT_DEFAULT)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            # Fallback: try the API endpoint
            logger.debug(f"pobb.in raw endpoint failed, trying API: {e}")
            api_url = f"https://pobb.in/api/v1/paste/{paste_id}"
            try:
                response = requests.get(api_url, timeout=API_TIMEOUT_DEFAULT)
                response.raise_for_status()
                data = response.json()
                # The API returns the code in a 'code' or 'content' field
                return str(data.get("code") or data.get("content") or "")
            except Exception as e:
                logger.error(f"Failed to fetch pobb.in: {e}")
                raise ValueError(f"Could not fetch pobb.in: {e}")

    @staticmethod
    def _looks_like_url(text: str) -> bool:
        """Check if text looks like a URL rather than a PoB code."""
        text_lower = text.lower()
        # Check for URL patterns (protocol prefix)
        if text_lower.startswith(("http://", "https://", "www.")):
            return True

        # Check for common build site domains using proper hostname validation
        # This prevents bypass attacks with URLs like "evil.com?redirect=maxroll.gg"
        build_site_hosts = [
            "maxroll.gg",
            "mobalytics.gg",
            "poe.ninja",
            "pathofexile.com",
            "poewiki.net",
            "poebuilds.cc",
            "pobarchives.com",
        ]

        # Try to parse as URL and validate hostname
        for host in build_site_hosts:
            if _url_host_matches(text, host):
                return True

        return False

    @staticmethod
    def _raise_url_error(url: str) -> None:
        """Raise a helpful error message for URLs that can't be auto-imported."""
        # Site-specific messages using proper hostname validation
        if _url_host_matches(url, "maxroll.gg"):
            raise ValueError(
                "Maxroll.gg URLs cannot be imported directly.\n\n"
                "To import this build:\n"
                "1. Open the URL in your browser\n"
                "2. Look for the 'Export to PoB' or 'Copy PoB Code' button\n"
                "3. Copy the PoB code and paste it here"
            )
        elif _url_host_matches(url, "mobalytics.gg"):
            raise ValueError(
                "Mobalytics URLs cannot be imported directly.\n\n"
                "To import this build:\n"
                "1. Open the URL in your browser\n"
                "2. Find the 'Path of Building' section\n"
                "3. Copy the PoB code and paste it here"
            )
        elif _url_host_matches(url, "poe.ninja"):
            raise ValueError(
                "poe.ninja URLs cannot be imported directly.\n\n"
                "To import this build:\n"
                "1. Open the URL in your browser\n"
                "2. Click 'Export to Path of Building'\n"
                "3. Copy the PoB code and paste it here"
            )
        elif _url_host_matches(url, "pobarchives.com"):
            raise ValueError(
                "PoB Archives URLs cannot be imported directly.\n\n"
                "To import this build:\n"
                "1. Open the URL in your browser\n"
                "2. Click the pobb.in link on the build page\n"
                "3. Copy the pobb.in URL and paste it here"
            )
        else:
            raise ValueError(
                f"URL detected but cannot be imported directly: {url}\n\n"
                "To import a build:\n"
                "- Paste a PoB code (base64 encoded string)\n"
                "- Or paste a pastebin.com URL\n"
                "- Or paste a pobb.in URL"
            )

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

            # Extract PlayerStat values (calculated build stats from PoB)
            if build_elem is not None:
                for stat_elem in build_elem.findall("PlayerStat"):
                    stat_name = stat_elem.get("stat", "")
                    stat_value = stat_elem.get("value", "")
                    if stat_name and stat_value:
                        try:
                            build.stats[stat_name] = float(stat_value)
                        except ValueError:
                            pass  # Skip non-numeric stats

                logger.debug(f"Extracted {len(build.stats)} PlayerStats from PoB")

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
        # NOTE: parsing_explicits state is implicit from implicits_remaining == 0

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
                        pass  # Invalid item level, skip
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
                        pass  # Invalid implicit count, skip
                continue

            # If we have implicits remaining, this line is an implicit mod
            if implicits_remaining > 0:
                # Clean up the mod text (remove tags like {crafted}, {fractured}, etc.)
                mod = re.sub(r"\{[^}]+\}", "", line).strip()
                if mod:
                    item.implicit_mods.append(mod)
                implicits_remaining -= 1
                # Once implicits_remaining == 0, we've finished parsing implicits
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
