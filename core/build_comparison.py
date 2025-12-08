"""
Build Comparison Module.

Compares player builds against guide/meta builds to:
1. Calculate match percentages for tree, gear, and skills
2. Identify missing nodes, items, and gems
3. Generate prioritized upgrade recommendations
4. Handle level progression stages
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import defusedxml.ElementTree as ET
import requests

from core.pob_integration import PoBBuild, PoBDecoder, PoBItem

logger = logging.getLogger(__name__)

__all__ = [
    "ProgressionStage",
    "TreeSpec",
    "SkillSetSpec",
    "TreeDelta",
    "SkillDelta",
    "ItemDelta",
    "EquipmentDelta",
    "BuildDelta",
    "MaxrollBuildFetcher",
    "GuideBuildParser",
    "BuildComparator",
]


class ProgressionStage(Enum):
    """Standard progression stages for build comparison."""
    LEVELING_EARLY = "leveling_early"      # Levels 1-40 (Acts 1-4)
    LEVELING_LATE = "leveling_late"        # Levels 40-70 (Acts 5-10)
    EARLY_MAPS = "early_maps"              # Levels 70-85
    MID_MAPS = "mid_maps"                  # Levels 85-92
    LATE_ENDGAME = "endgame"               # Levels 93+

    @classmethod
    def from_level(cls, level: int) -> "ProgressionStage":
        """Determine progression stage from character level."""
        if level < 40:
            return cls.LEVELING_EARLY
        elif level < 70:
            return cls.LEVELING_LATE
        elif level < 85:
            return cls.EARLY_MAPS
        elif level < 93:
            return cls.MID_MAPS
        else:
            return cls.LATE_ENDGAME

    @property
    def display_name(self) -> str:
        """Human-readable stage name."""
        return {
            ProgressionStage.LEVELING_EARLY: "Early Leveling (Acts 1-4)",
            ProgressionStage.LEVELING_LATE: "Late Leveling (Acts 5-10)",
            ProgressionStage.EARLY_MAPS: "Early Mapping",
            ProgressionStage.MID_MAPS: "Mid Mapping",
            ProgressionStage.LATE_ENDGAME: "Late Endgame",
        }[self]


@dataclass
class TreeSpec:
    """Parsed passive tree specification."""
    title: str
    raw_title: str  # With color codes
    tree_version: str
    class_id: int
    ascend_class_id: int
    nodes: Set[int]
    mastery_effects: List[Tuple[int, int]]  # (node_id, effect_id)
    url: str = ""
    inferred_level: Optional[int] = None


@dataclass
class SkillSetSpec:
    """Parsed skill set specification."""
    id: str
    title: str
    raw_title: str
    skills: List[Dict[str, Any]]  # List of skill groups with gems
    inferred_level: Optional[int] = None


@dataclass
class TreeDelta:
    """Differences between two passive trees."""
    missing_nodes: List[int]      # In guide, not in player
    extra_nodes: List[int]        # In player, not in guide
    shared_nodes: List[int]       # In both
    missing_masteries: List[Tuple[int, int]]
    match_percent: float


@dataclass
class SkillDelta:
    """Differences between skill setups."""
    missing_gems: List[str]
    extra_gems: List[str]
    gem_level_gaps: Dict[str, int]    # Gem -> level difference (negative = player behind)
    gem_quality_gaps: Dict[str, int]
    missing_supports: List[str]       # Support gems not linked
    match_percent: float


@dataclass
class ItemDelta:
    """Differences for a single equipment slot."""
    slot: str
    player_item: Optional[PoBItem]
    guide_item: Optional[PoBItem]
    is_match: bool
    missing_unique: Optional[str] = None  # If guide has unique player doesn't
    upgrade_priority: int = 0  # 0=no upgrade needed, 1-5 priority


@dataclass
class EquipmentDelta:
    """Full equipment comparison."""
    slot_deltas: Dict[str, ItemDelta]
    missing_uniques: List[str]
    match_percent: float


@dataclass
class BuildDelta:
    """Complete build comparison result."""
    # Component deltas
    tree_delta: TreeDelta
    skill_delta: SkillDelta
    equipment_delta: EquipmentDelta

    # Overall metrics
    overall_match_percent: float

    # Progression info
    player_level: int
    guide_level: int
    progression_stage: ProgressionStage

    # Actionable recommendations
    priority_upgrades: List[str] = field(default_factory=list)

    # Metadata
    guide_title: str = ""
    guide_spec_title: str = ""


class MaxrollBuildFetcher:
    """Fetch and cache builds from Maxroll.gg."""

    BASE_URL = "https://maxroll.gg/poe/api/pob"
    DEFAULT_TIMEOUT = 30
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self):
        self._cache: Dict[str, str] = {}  # build_id -> raw code

    def fetch(self, build_id: str) -> str:
        """
        Fetch PoB code from Maxroll.

        Args:
            build_id: The Maxroll build ID (e.g., "0nws0aiy")

        Returns:
            Raw PoB code string

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the build_id is empty
        """
        if not build_id:
            raise ValueError("build_id cannot be empty")

        if build_id in self._cache:
            return self._cache[build_id]

        url = f"{self.BASE_URL}/{build_id}"
        headers = {"User-Agent": self.USER_AGENT}

        try:
            response = requests.get(url, headers=headers, timeout=self.DEFAULT_TIMEOUT)
            response.raise_for_status()
        except requests.Timeout:
            logger.error(f"Timeout fetching build {build_id} from Maxroll")
            raise
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Build not found: {build_id}") from e
            logger.error(f"HTTP error fetching build {build_id}: {e}")
            raise

        code = response.text
        self._cache[build_id] = code
        return code

    def fetch_and_decode(self, build_id: str) -> str:
        """
        Fetch and decode to XML string.

        Args:
            build_id: The Maxroll build ID

        Returns:
            Decoded XML string from the PoB code
        """
        code = self.fetch(build_id)
        return PoBDecoder.decode_pob_code(code)

    def clear_cache(self) -> None:
        """Clear the build cache."""
        self._cache.clear()

    @staticmethod
    def extract_build_id(url: str) -> Optional[str]:
        """
        Extract build ID from Maxroll URL.

        Args:
            url: Full Maxroll URL (e.g., "https://maxroll.gg/poe/pob/0nws0aiy")

        Returns:
            Build ID string or None if not found
        """
        if not url:
            return None
        match = re.search(r'maxroll\.gg/poe/pob/([a-zA-Z0-9]+)', url)
        return match.group(1) if match else None


class GuideBuildParser:
    """
    Parse guide builds with multiple progression stages.

    Handles PoB XML parsing with support for:
    - Multiple tree specs (passive trees for different levels)
    - Multiple skill sets (gem setups for different stages)
    - Level inference from spec/skill set titles
    """

    # Pattern to extract level from titles (e.g., "lvl 92", "level 85")
    LEVEL_PATTERN = re.compile(r'(?:lvl?|level)\s*(\d+)', re.IGNORECASE)

    # Pattern to extract act ranges (e.g., "Act 1", "Act 4-10")
    ACT_PATTERN = re.compile(r'act\s*(\d+)(?:\s*-\s*(\d+))?', re.IGNORECASE)

    # Approximate character levels for each act completion
    ACT_LEVELS: Dict[int, int] = {
        1: 12, 2: 24, 3: 33, 4: 40, 5: 45,
        6: 50, 7: 55, 8: 60, 9: 65, 10: 70
    }

    # Keywords that imply progression stage when no explicit level found
    # Ordered by specificity (more specific keywords first)
    STAGE_LEVEL_HINTS: Dict[str, int] = {
        "endgame": 98,    # Most specific - check before "end"
        "bis": 100,       # Best in slot
        "final": 100,
        "late": 96,
        "mid": 92,
        "early": 85,      # Early mapping
        "budget": 80,
        "starter": 75,
    }

    # Keywords used for fallback stage matching in find_spec_for_level
    STAGE_KEYWORDS: Dict[ProgressionStage, List[str]] = {
        ProgressionStage.LEVELING_EARLY: ["act 1", "act 2", "act 3", "act 4"],
        ProgressionStage.LEVELING_LATE: ["act 5", "act 6", "act 7", "act 8", "act 9", "act 10"],
        ProgressionStage.EARLY_MAPS: ["early", "budget", "starter"],
        ProgressionStage.MID_MAPS: ["mid"],
        ProgressionStage.LATE_ENDGAME: ["late", "endgame", "bis", "final"],
    }

    # Regex pattern for PoB color codes
    COLOR_CODE_PATTERN = re.compile(r'\^x[A-Fa-f0-9]{6}|\^[0-9]')

    @classmethod
    def clean_title(cls, title: str) -> str:
        """
        Remove PoB color codes from title.

        Args:
            title: Raw title with potential color codes

        Returns:
            Cleaned title string
        """
        return cls.COLOR_CODE_PATTERN.sub('', title).strip()

    def _infer_level_from_title(self, title: str) -> Optional[int]:
        """
        Infer character level from spec/skill set title.

        Attempts to extract level information using multiple strategies:
        1. Explicit level patterns (e.g., "lvl 92", "level 85")
        2. Act references (e.g., "Act 1" → 12, "Act 4-10" → 70)
        3. Stage keywords (e.g., "Early" → 85, "Mid" → 92)

        Args:
            title: The spec or skill set title

        Returns:
            Inferred level or None if unable to determine
        """
        # First try explicit level pattern (e.g., "lvl 92", "level 85")
        level_match = self.LEVEL_PATTERN.search(title)
        if level_match:
            return int(level_match.group(1))

        # Try Act pattern (e.g., "Act 1", "Act 4-10")
        act_match = self.ACT_PATTERN.search(title)
        if act_match:
            act_start = int(act_match.group(1))
            act_end = int(act_match.group(2)) if act_match.group(2) else act_start
            # Use the end act's level as the target
            return self.ACT_LEVELS.get(act_end, self.ACT_LEVELS.get(act_start))

        # Try stage keywords (e.g., "Early", "Mid", "Late")
        title_lower = title.lower()
        for keyword, level in self.STAGE_LEVEL_HINTS.items():
            if keyword in title_lower:
                return level

        return None

    def parse_tree_specs(self, xml_string: str) -> List[TreeSpec]:
        """Parse all tree specs from PoB XML."""
        root = ET.fromstring(xml_string)
        tree_elem = root.find("Tree")

        if tree_elem is None:
            return []

        specs = []
        for spec_elem in tree_elem.findall("Spec"):
            raw_title = spec_elem.get("title", "Unnamed")
            title = self.clean_title(raw_title)

            # Parse nodes
            nodes_str = spec_elem.get("nodes", "")
            nodes = {int(n) for n in nodes_str.split(",") if n.strip()}

            # Parse mastery effects: "{nodeId,effectId},{nodeId,effectId}"
            masteries = []
            mastery_str = spec_elem.get("masteryEffects", "")
            for match in re.finditer(r'\{(\d+),(\d+)\}', mastery_str):
                masteries.append((int(match.group(1)), int(match.group(2))))

            # Get URL if present
            url_elem = spec_elem.find("URL")
            url = url_elem.text.strip() if url_elem is not None and url_elem.text else ""

            # Infer level from title
            inferred_level = self._infer_level_from_title(title)

            specs.append(TreeSpec(
                title=title,
                raw_title=raw_title,
                tree_version=spec_elem.get("treeVersion", ""),
                class_id=int(spec_elem.get("classId", 0)),
                ascend_class_id=int(spec_elem.get("ascendClassId", 0)),
                nodes=nodes,
                mastery_effects=masteries,
                url=url,
                inferred_level=inferred_level,
            ))

        return specs

    def parse_skill_sets(self, xml_string: str) -> List[SkillSetSpec]:
        """Parse all skill sets from PoB XML."""
        root = ET.fromstring(xml_string)
        skills_elem = root.find("Skills")

        if skills_elem is None:
            return []

        skill_sets = []
        for ss_elem in skills_elem.findall("SkillSet"):
            raw_title = ss_elem.get("title", "Unnamed")
            title = self.clean_title(raw_title)

            skills = []
            for skill_elem in ss_elem.findall("Skill"):
                if skill_elem.get("enabled", "true") != "true":
                    continue

                gems = []
                for gem_elem in skill_elem.findall("Gem"):
                    if gem_elem.get("enabled", "true") != "true":
                        continue
                    gems.append({
                        "name": gem_elem.get("nameSpec", gem_elem.get("skillId", "")),
                        "level": int(gem_elem.get("level", 1)),
                        "quality": int(gem_elem.get("quality", 0)),
                    })

                if gems:
                    skills.append({
                        "label": self.clean_title(skill_elem.get("label", "")),
                        "slot": skill_elem.get("slot", ""),
                        "gems": gems,
                    })

            # Infer level
            inferred_level = self._infer_level_from_title(title)

            skill_sets.append(SkillSetSpec(
                id=ss_elem.get("id", ""),
                title=title,
                raw_title=raw_title,
                skills=skills,
                inferred_level=inferred_level,
            ))

        return skill_sets

    def find_spec_for_level(
        self,
        specs: List[TreeSpec],
        target_level: int
    ) -> Optional[TreeSpec]:
        """Find the most appropriate spec for a given level."""
        if not specs:
            return None

        # First, try to find spec with inferred level
        leveled_specs = [(s, s.inferred_level) for s in specs if s.inferred_level]

        if leveled_specs:
            # Sort by level
            leveled_specs.sort(key=lambda x: x[1])

            # Find closest spec at or below target level
            best = None
            for spec, level in leveled_specs:
                if level <= target_level:
                    best = spec
                elif best is None:
                    # Target is below all specs, use lowest
                    best = spec
                    break

            if best:
                return best

        # Fallback: use stage keywords
        target_stage = ProgressionStage.from_level(target_level)
        keywords = self.STAGE_KEYWORDS.get(target_stage, [])

        for spec in specs:
            title_lower = spec.title.lower()
            for keyword in keywords:
                if keyword in title_lower:
                    return spec

        # Last resort: return first spec
        return specs[0] if specs else None

    def find_skill_set_for_level(
        self,
        skill_sets: List[SkillSetSpec],
        target_level: int
    ) -> Optional[SkillSetSpec]:
        """Find the most appropriate skill set for a given level."""
        if not skill_sets:
            return None

        # Similar logic to find_spec_for_level
        leveled = [(s, s.inferred_level) for s in skill_sets if s.inferred_level]

        if leveled:
            leveled.sort(key=lambda x: x[1])

            best = None
            for ss, level in leveled:
                if level <= target_level:
                    best = ss
                elif best is None:
                    best = ss
                    break

            if best:
                return best

        # Fallback: stage keywords
        target_stage = ProgressionStage.from_level(target_level)
        keywords = self.STAGE_KEYWORDS.get(target_stage, [])

        for ss in skill_sets:
            title_lower = ss.title.lower()
            for keyword in keywords:
                if keyword in title_lower:
                    return ss

        return skill_sets[0] if skill_sets else None


class BuildComparator:
    """Compare player builds against guide builds."""

    def __init__(self):
        self.parser = GuideBuildParser()

    def compare_trees(
        self,
        player_nodes: Set[int],
        guide_nodes: Set[int],
        player_masteries: List[Tuple[int, int]] = None,
        guide_masteries: List[Tuple[int, int]] = None,
    ) -> TreeDelta:
        """Compare two passive trees."""
        player_masteries = player_masteries or []
        guide_masteries = guide_masteries or []

        missing = guide_nodes - player_nodes
        extra = player_nodes - guide_nodes
        shared = player_nodes & guide_nodes

        # Calculate match percentage based on guide coverage
        if not guide_nodes:
            match_percent = 100.0
        else:
            match_percent = len(shared) / len(guide_nodes) * 100

        # Compare masteries
        player_mastery_set = set(player_masteries)
        guide_mastery_set = set(guide_masteries)
        missing_masteries = list(guide_mastery_set - player_mastery_set)

        return TreeDelta(
            missing_nodes=sorted(missing),
            extra_nodes=sorted(extra),
            shared_nodes=sorted(shared),
            missing_masteries=missing_masteries,
            match_percent=round(match_percent, 1),
        )

    def compare_skills(
        self,
        player_gems: Dict[str, Dict],  # gem_name -> {level, quality}
        guide_skill_set: SkillSetSpec,
    ) -> SkillDelta:
        """Compare skill gem setups."""
        guide_gems = {}
        for skill in guide_skill_set.skills:
            for gem in skill["gems"]:
                name = gem["name"]
                # Keep highest level if gem appears multiple times
                if name not in guide_gems or gem["level"] > guide_gems[name]["level"]:
                    guide_gems[name] = gem

        player_gem_names = set(player_gems.keys())
        guide_gem_names = set(guide_gems.keys())

        missing = list(guide_gem_names - player_gem_names)
        extra = list(player_gem_names - guide_gem_names)

        # Level/quality gaps for shared gems
        level_gaps = {}
        quality_gaps = {}

        for name in player_gem_names & guide_gem_names:
            player_g = player_gems[name]
            guide_g = guide_gems[name]

            level_diff = player_g.get("level", 1) - guide_g["level"]
            if level_diff < 0:
                level_gaps[name] = level_diff

            quality_diff = player_g.get("quality", 0) - guide_g["quality"]
            if quality_diff < 0:
                quality_gaps[name] = quality_diff

        # Calculate match
        if not guide_gem_names:
            match_percent = 100.0
        else:
            matched = len(player_gem_names & guide_gem_names)
            match_percent = matched / len(guide_gem_names) * 100

        return SkillDelta(
            missing_gems=sorted(missing),
            extra_gems=sorted(extra),
            gem_level_gaps=level_gaps,
            gem_quality_gaps=quality_gaps,
            missing_supports=[],  # TODO: analyze support gem links
            match_percent=round(match_percent, 1),
        )

    def compare_equipment(
        self,
        player_items: Dict[str, PoBItem],
        guide_items: Dict[str, PoBItem],
    ) -> EquipmentDelta:
        """Compare equipped items."""
        slot_deltas = {}
        missing_uniques = []
        matched_slots = 0
        total_slots = 0

        # Standard equipment slots
        slots = [
            "Weapon 1", "Weapon 2", "Helmet", "Body Armour",
            "Gloves", "Boots", "Belt", "Amulet", "Ring 1", "Ring 2"
        ]

        for slot in slots:
            player_item = player_items.get(slot)
            guide_item = guide_items.get(slot)

            if guide_item is None:
                continue

            total_slots += 1

            # Check for unique match
            is_match = False
            missing_unique = None

            if guide_item.rarity == "UNIQUE":
                if player_item and player_item.name == guide_item.name:
                    is_match = True
                    matched_slots += 1
                else:
                    missing_unique = guide_item.name
                    missing_uniques.append(guide_item.name)
            elif player_item:
                # For rares, consider it a match if same base type
                if player_item.base_type == guide_item.base_type:
                    is_match = True
                    matched_slots += 1

            # Determine upgrade priority
            priority = 0
            if not is_match:
                if guide_item.rarity == "UNIQUE":
                    priority = 2  # Medium priority for missing uniques
                    if slot in ["Body Armour", "Weapon 1"]:
                        priority = 1  # High priority for major slots
                else:
                    priority = 3  # Lower priority for rare upgrades

            slot_deltas[slot] = ItemDelta(
                slot=slot,
                player_item=player_item,
                guide_item=guide_item,
                is_match=is_match,
                missing_unique=missing_unique,
                upgrade_priority=priority,
            )

        match_percent = (matched_slots / total_slots * 100) if total_slots > 0 else 100.0

        return EquipmentDelta(
            slot_deltas=slot_deltas,
            missing_uniques=missing_uniques,
            match_percent=round(match_percent, 1),
        )

    def compare_builds(
        self,
        player_build: PoBBuild,
        guide_xml: str,
        player_level: Optional[int] = None,
    ) -> BuildDelta:
        """
        Full build comparison.

        Args:
            player_build: Player's decoded build
            guide_xml: Guide's decoded XML string
            player_level: Override level (uses player_build.level if None)

        Returns:
            BuildDelta with all comparison data
        """
        level = player_level or player_build.level
        stage = ProgressionStage.from_level(level)

        # Parse guide data
        tree_specs = self.parser.parse_tree_specs(guide_xml)
        skill_sets = self.parser.parse_skill_sets(guide_xml)
        guide_build = PoBDecoder.parse_build(guide_xml)

        # Find appropriate progression stage
        target_spec = self.parser.find_spec_for_level(tree_specs, level)
        target_skills = self.parser.find_skill_set_for_level(skill_sets, level)

        # Parse player tree (if available in raw_xml)
        player_nodes: Set[int] = set()
        player_masteries: List[Tuple[int, int]] = []
        if player_build.raw_xml:
            try:
                player_specs = self.parser.parse_tree_specs(player_build.raw_xml)
                if player_specs:
                    # Use first/active spec
                    player_nodes = player_specs[0].nodes
                    player_masteries = player_specs[0].mastery_effects
            except Exception as e:
                logger.warning(f"Could not parse player tree: {e}")

        # Tree comparison
        guide_nodes = target_spec.nodes if target_spec else set()
        guide_masteries = target_spec.mastery_effects if target_spec else []
        tree_delta = self.compare_trees(
            player_nodes, guide_nodes,
            player_masteries, guide_masteries
        )

        # Skill comparison
        player_gems = self._extract_player_gems(player_build)
        skill_delta = self.compare_skills(player_gems, target_skills) if target_skills else SkillDelta(
            missing_gems=[], extra_gems=[], gem_level_gaps={}, gem_quality_gaps={},
            missing_supports=[], match_percent=100.0
        )

        # Equipment comparison
        equipment_delta = self.compare_equipment(player_build.items, guide_build.items)

        # Calculate overall match
        overall = (
            tree_delta.match_percent * 0.4 +
            skill_delta.match_percent * 0.3 +
            equipment_delta.match_percent * 0.3
        )

        # Generate priority upgrades
        priorities = self._generate_priorities(tree_delta, skill_delta, equipment_delta)

        return BuildDelta(
            tree_delta=tree_delta,
            skill_delta=skill_delta,
            equipment_delta=equipment_delta,
            overall_match_percent=round(overall, 1),
            player_level=level,
            guide_level=target_spec.inferred_level or guide_build.level if target_spec else guide_build.level,
            progression_stage=stage,
            priority_upgrades=priorities,
            guide_title="",  # Set by caller
            guide_spec_title=target_spec.title if target_spec else "",
        )

    def _extract_player_gems(self, build: PoBBuild) -> Dict[str, Dict]:
        """Extract gem info from player build."""
        # This is simplified - real implementation would parse skills
        # from raw_xml similar to guide parsing
        gems = {}

        if build.raw_xml:
            try:
                skill_sets = self.parser.parse_skill_sets(build.raw_xml)
                if skill_sets:
                    for skill in skill_sets[0].skills:
                        for gem in skill["gems"]:
                            name = gem["name"]
                            if name not in gems or gem["level"] > gems[name].get("level", 0):
                                gems[name] = gem
            except Exception as e:
                logger.warning(f"Could not parse player gems: {e}")

        return gems

    def _generate_priorities(
        self,
        tree: TreeDelta,
        skill: SkillDelta,
        equipment: EquipmentDelta
    ) -> List[str]:
        """Generate prioritized upgrade recommendations."""
        priorities = []

        # Critical: Missing required uniques for build function
        for unique in equipment.missing_uniques[:3]:
            priorities.append(f"Acquire unique: {unique}")

        # High: Missing key gems
        for gem in skill.missing_gems[:3]:
            priorities.append(f"Get gem: {gem}")

        # Medium: Passive tree gaps
        missing_count = len(tree.missing_nodes)
        if missing_count > 10:
            priorities.append(f"Allocate {missing_count} missing passive nodes")
        elif missing_count > 0:
            priorities.append(f"Allocate {missing_count} passive nodes")

        # Medium: Gem levels
        for gem, gap in sorted(skill.gem_level_gaps.items(), key=lambda x: x[1])[:3]:
            priorities.append(f"Level up {gem} ({abs(gap)} levels behind)")

        # Lower: Equipment upgrades for non-uniques
        for slot, delta in sorted(
            equipment.slot_deltas.items(),
            key=lambda x: x[1].upgrade_priority
        ):
            if delta.upgrade_priority > 0 and not delta.missing_unique:
                priorities.append(f"Upgrade {slot} equipment")
                if len(priorities) >= 10:
                    break

        return priorities[:10]


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Build Comparison Module Test")
    print("=" * 60)

    # Test fetching
    fetcher = MaxrollBuildFetcher()
    parser = GuideBuildParser()

    try:
        xml_string = fetcher.fetch_and_decode("0nws0aiy")

        # Parse specs
        specs = parser.parse_tree_specs(xml_string)
        print(f"\nFound {len(specs)} tree specs:")
        for spec in specs[:5]:
            print(f"  - {spec.title} (Level {spec.inferred_level}, {len(spec.nodes)} nodes)")

        # Parse skill sets
        skill_sets = parser.parse_skill_sets(xml_string)
        print(f"\nFound {len(skill_sets)} skill sets:")
        for ss in skill_sets[:5]:
            print(f"  - {ss.title} (Level {ss.inferred_level})")

        # Test level matching
        print("\nLevel-appropriate spec selection:")
        for level in [40, 70, 85, 92, 98]:
            spec = parser.find_spec_for_level(specs, level)
            ss = parser.find_skill_set_for_level(skill_sets, level)
            print(f"  Level {level}: Tree='{spec.title if spec else 'None'}', Skills='{ss.title if ss else 'None'}'")

    except Exception as e:
        print(f"Error: {e}")
