"""
Build Matcher - Match items against popular build requirements.

Supports:
- Path of Building (PoB) code import
- Manual build requirement entry
- Highlighting items that match build needs
"""

import json
import base64
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class BuildRequirement:
    """Requirements for a build (what items/affixes are needed)."""
    build_name: str
    source: str  # "pob", "maxroll", "manual"

    # Required affixes/stats
    required_life: int = 0
    required_es: int = 0
    required_resistances: Dict[str, int] = field(default_factory=dict)
    required_attributes: Dict[str, int] = field(default_factory=dict)

    # Desired affixes (not required but valuable)
    desired_affixes: List[str] = field(default_factory=list)

    # Key uniques
    key_uniques: List[str] = field(default_factory=list)

    # Skill gems used
    main_skills: List[str] = field(default_factory=list)

    # Gear slots priority
    priority_slots: Dict[str, str] = field(default_factory=dict)


class BuildMatcher:
    """
    Matches items against build requirements.

    Can import from:
    - Path of Building codes
    - Manual entry
    - Pre-defined popular builds
    """

    def __init__(self, builds_file: Optional[Path] = None):
        """
        Initialize build matcher.

        Args:
            builds_file: Optional JSON file with saved builds
        """
        if builds_file is None:
            builds_file = Path.home() / ".poe_price_checker" / "builds.json"

        self.builds_file = builds_file
        self.builds: List[BuildRequirement] = []
        self._load_builds()

    def _load_builds(self):
        """Load saved builds from file."""
        if self.builds_file.exists():
            try:
                with open(self.builds_file) as f:
                    data = json.load(f)

                # Clear existing builds to avoid duplicates
                self.builds.clear()

                for build_data in data.get("builds", []):
                    self.builds.append(BuildRequirement(**build_data))
            except Exception as e:
                print(f"Warning: Failed to load builds: {e}")

    def _save_builds(self):
        """Save builds to file."""
        self.builds_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "builds": [
                {
                    "build_name": b.build_name,
                    "source": b.source,
                    "required_life": b.required_life,
                    "required_es": b.required_es,
                    "required_resistances": b.required_resistances,
                    "required_attributes": b.required_attributes,
                    "desired_affixes": b.desired_affixes,
                    "key_uniques": b.key_uniques,
                    "main_skills": b.main_skills,
                    "priority_slots": b.priority_slots,
                }
                for b in self.builds
            ]
        }

        with open(self.builds_file, 'w') as f:
            json.dump(data, f, indent=2)

    def import_pob_code(
            self,
            pob_code: str,
            build_name: Optional[str] = None) -> BuildRequirement:
        """
        Import a Path of Building code and extract build requirements.

        Args:
            pob_code: PoB code string (base64 encoded XML)
            build_name: Optional name for the build

        Returns:
            BuildRequirement object
        """
        try:
            # Decode PoB code
            # PoB codes are base64-encoded, zlib-compressed XML
            decoded = base64.b64decode(pob_code)
            decompressed = zlib.decompress(decoded)
            xml_text = decompressed.decode('utf-8')

            # Parse XML
            root = ET.fromstring(xml_text)

            # Extract build name if not provided
            if not build_name:
                build_elem = root.find('.//Build')
                if build_elem is not None:
                    build_name = build_elem.get(
                        'targetVersion', 'Imported Build')
                else:
                    build_name = "Imported Build"

            # Extract requirements
            build_req = BuildRequirement(
                build_name=build_name,
                source="pob"
            )

            # Extract skills
            skills_elem = root.find('.//Skills')
            if skills_elem is not None:
                for skill in skills_elem.findall('.//Gem'):
                    gem_name = skill.get('nameSpec', '')
                    if gem_name and skill.get('enabled') == 'true':
                        build_req.main_skills.append(gem_name)

            # Extract key items
            items_elem = root.find('.//Items')
            if items_elem is not None:
                for item in items_elem.findall('.//Item'):
                    item_text = item.text or ''
                    if 'Rarity: UNIQUE' in item_text:
                        # Extract unique name
                        lines = item_text.split('\n')
                        if len(lines) > 1:
                            unique_name = lines[1].strip()
                            build_req.key_uniques.append(unique_name)

            # Add to builds list
            self.builds.append(build_req)
            self._save_builds()

            return build_req

        except Exception as e:
            raise ValueError(f"Failed to parse PoB code: {e}")

    def add_manual_build(
        self,
        build_name: str,
        required_life: int = 0,
        required_es: int = 0,
        resistances: Optional[Dict[str, int]] = None,
        desired_affixes: Optional[List[str]] = None,
        key_uniques: Optional[List[str]] = None
    ) -> BuildRequirement:
        """
        Manually add a build with requirements.

        Args:
            build_name: Name of the build
            required_life: Minimum life needed
            required_es: Minimum ES needed
            resistances: Dict of resistance requirements (e.g., {"fire": 75, "cold": 75})
            desired_affixes: List of valuable affixes for this build
            key_uniques: List of unique item names needed

        Returns:
            BuildRequirement object
        """
        build_req = BuildRequirement(
            build_name=build_name,
            source="manual",
            required_life=required_life,
            required_es=required_es,
            required_resistances=resistances or {},
            desired_affixes=desired_affixes or [],
            key_uniques=key_uniques or []
        )

        self.builds.append(build_req)
        self._save_builds()

        return build_req

    def match_item_to_builds(
        self,
        item,
        affix_matches: List
    ) -> List[Dict[str, object]]:
        """
        Check if an item matches any build requirements.

        Args:
            item: ParsedItem
            affix_matches: List of AffixMatch from rare evaluator

        Returns:
            List of matching builds with relevance score
        """
        matches = []

        for build in self.builds:
            score = 0
            matched_requirements = []

            # Check if it's a key unique
            if item.rarity == "UNIQUE" and item.name:
                if item.name in build.key_uniques:
                    score += 100
                    matched_requirements.append(f"Key unique: {item.name}")

            # Check affixes
            for affix in affix_matches:
                affix_type = affix.affix_type

                # Check life requirement
                if affix_type == "life" and build.required_life > 0:
                    if affix.value and affix.value >= build.required_life * 0.7:  # 70% of requirement
                        score += 20
                        matched_requirements.append(
                            f"Life: {affix.value} (need {build.required_life})")

                # Check ES requirement
                if affix_type == "energy_shield" and build.required_es > 0:
                    if affix.value and affix.value >= build.required_es * 0.7:
                        score += 20
                        matched_requirements.append(
                            f"ES: {affix.value} (need {build.required_es})")

                # Check resistances
                if affix_type == "resistances":
                    for res_type, required in build.required_resistances.items():
                        if res_type in affix.mod_text.lower():
                            score += 10
                            matched_requirements.append(
                                f"Resistance: {res_type}")

                # Check desired affixes
                for desired in build.desired_affixes:
                    if desired.lower() in affix.mod_text.lower():
                        score += 15
                        matched_requirements.append(f"Desired: {desired}")

            if score > 0:
                matches.append({
                    "build_name": build.build_name,
                    "score": score,
                    "matched_requirements": matched_requirements
                })

        # Sort by score (cast to int since we know score is always int)
        matches.sort(key=lambda x: int(x["score"]), reverse=True)  # type: ignore[arg-type]

        return matches

    def get_build_summary(self, build_name: str) -> Optional[str]:
        """Get a summary of a build's requirements."""
        for build in self.builds:
            if build.build_name == build_name:
                lines = []
                lines.append(f"=== {build.build_name} ===")
                lines.append(f"Source: {build.source}")

                if build.required_life:
                    lines.append(f"Required Life: {build.required_life}+")
                if build.required_es:
                    lines.append(f"Required ES: {build.required_es}+")

                if build.required_resistances:
                    lines.append("Required Resistances:")
                    for res, value in build.required_resistances.items():
                        lines.append(f"  - {res.title()}: {value}%")

                if build.desired_affixes:
                    lines.append(f"Desired Affixes: {', '.join(build.desired_affixes)}")

                if build.key_uniques:
                    lines.append(f"Key Uniques: {', '.join(build.key_uniques)}")

                if build.main_skills:
                    lines.append(
                        f"Main Skills: {', '.join(build.main_skills[:3])}")

                return "\n".join(lines)

        return None

    def list_builds(self) -> List[str]:
        """Get list of all build names."""
        return [b.build_name for b in self.builds]


if __name__ == "__main__":
    # Test build matcher
    matcher = BuildMatcher()

    # Add a sample build
    build = matcher.add_manual_build(
        build_name="Lightning Strike Raider",
        required_life=4000,
        resistances={"fire": 75, "cold": 75, "lightning": 75},
        desired_affixes=[
            "increased Movement Speed",
            "increased Attack Speed",
            "Suppression"
        ],
        key_uniques=["Perseverance", "Thread of Hope"]
    )

    print(matcher.get_build_summary("Lightning Strike Raider"))
    print("\nSaved builds:", matcher.list_builds())
