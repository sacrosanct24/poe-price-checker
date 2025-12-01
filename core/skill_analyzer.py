"""
Skill Analyzer.

Analyzes skill gem tags and provides skill-specific mod affinities.
Helps prioritize mods that synergize with the build's main skill.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SkillTag(str, Enum):
    """Skill gem tags from PoE."""
    # Type tags
    ATTACK = "attack"
    SPELL = "spell"
    MELEE = "melee"
    PROJECTILE = "projectile"
    AREA = "area"
    MINION = "minion"
    TOTEM = "totem"
    TRAP = "trap"
    MINE = "mine"
    BRAND = "brand"
    CHANNELLING = "channelling"

    # Element tags
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"
    PHYSICAL = "physical"

    # Damage type tags
    DOT = "dot"  # Damage over time
    HIT = "hit"
    AILMENT = "ailment"

    # Other
    CRITICAL = "critical"
    DURATION = "duration"
    AURA = "aura"
    WARCRY = "warcry"
    TRIGGER = "trigger"


@dataclass
class SkillInfo:
    """Information about a skill gem."""
    name: str
    tags: Set[str] = field(default_factory=set)
    primary_element: Optional[str] = None
    is_main_skill: bool = False

    @classmethod
    def from_name(cls, name: str) -> "SkillInfo":
        """Create SkillInfo with auto-detected tags based on skill name."""
        info = cls(name=name)
        info.tags = SKILL_TAG_DATABASE.get(name.lower(), set())
        info.primary_element = _detect_element(name.lower(), info.tags)
        return info


# Skill to tags database (common skills)
SKILL_TAG_DATABASE: Dict[str, Set[str]] = {
    # Attack skills
    "cyclone": {"attack", "melee", "area", "physical", "channelling"},
    "boneshatter": {"attack", "melee", "physical", "duration"},
    "heavy strike": {"attack", "melee", "physical"},
    "double strike": {"attack", "melee", "physical"},
    "lacerate": {"attack", "melee", "area", "physical"},
    "blade flurry": {"attack", "melee", "area", "physical", "channelling"},
    "reave": {"attack", "melee", "area", "physical"},
    "flicker strike": {"attack", "melee", "physical", "duration"},
    "viper strike": {"attack", "melee", "chaos", "duration", "dot"},
    "lightning strike": {"attack", "melee", "projectile", "lightning"},
    "frost blades": {"attack", "melee", "projectile", "cold"},
    "molten strike": {"attack", "melee", "projectile", "fire", "area"},
    "wild strike": {"attack", "melee", "fire", "cold", "lightning"},
    "infernal blow": {"attack", "melee", "fire", "area"},
    "consecrated path": {"attack", "melee", "fire", "area"},
    "tectonic slam": {"attack", "melee", "fire", "area"},
    "sunder": {"attack", "melee", "area", "physical"},
    "earthquake": {"attack", "melee", "area", "physical", "duration"},
    "ground slam": {"attack", "melee", "area", "physical"},
    "ice crash": {"attack", "melee", "area", "cold"},
    "cleave": {"attack", "melee", "area", "physical"},
    "sweep": {"attack", "melee", "area", "physical"},
    "smite": {"attack", "melee", "area", "lightning"},

    # Projectile attacks
    "tornado shot": {"attack", "projectile", "physical", "area"},
    "split arrow": {"attack", "projectile", "physical", "area"},
    "lightning arrow": {"attack", "projectile", "lightning", "area"},
    "ice shot": {"attack", "projectile", "cold", "area"},
    "burning arrow": {"attack", "projectile", "fire"},
    "barrage": {"attack", "projectile", "physical"},
    "rain of arrows": {"attack", "projectile", "area", "physical"},
    "caustic arrow": {"attack", "projectile", "chaos", "area", "dot"},
    "toxic rain": {"attack", "projectile", "chaos", "area", "dot"},
    "scourge arrow": {"attack", "projectile", "chaos", "channelling"},
    "elemental hit": {"attack", "projectile", "fire", "cold", "lightning"},
    "galvanic arrow": {"attack", "projectile", "lightning", "area"},
    "lancing steel": {"attack", "projectile", "physical"},
    "shattering steel": {"attack", "projectile", "physical", "area"},
    "spectral helix": {"attack", "projectile", "physical"},
    "spectral throw": {"attack", "projectile", "physical"},

    # Spell skills
    "arc": {"spell", "lightning", "chaining"},
    "spark": {"spell", "lightning", "projectile", "duration"},
    "ball lightning": {"spell", "lightning", "projectile", "area"},
    "divine ire": {"spell", "lightning", "physical", "area", "channelling"},
    "crackling lance": {"spell", "lightning", "area"},
    "shock nova": {"spell", "lightning", "area"},
    "storm call": {"spell", "lightning", "area", "duration"},
    "orb of storms": {"spell", "lightning", "duration"},

    "fireball": {"spell", "fire", "projectile", "area"},
    "firestorm": {"spell", "fire", "area", "duration"},
    "flame surge": {"spell", "fire", "area"},
    "incinerate": {"spell", "fire", "area", "channelling"},
    "flameblast": {"spell", "fire", "area", "channelling"},
    "magma orb": {"spell", "fire", "projectile", "area", "chaining"},
    "armageddon brand": {"spell", "fire", "area", "duration", "brand"},
    "flame wall": {"spell", "fire", "area", "duration"},
    "cremation": {"spell", "fire", "area", "duration"},
    "detonate dead": {"spell", "fire", "area"},
    "volatile dead": {"spell", "fire", "area", "duration"},

    "ice nova": {"spell", "cold", "area"},
    "frostbolt": {"spell", "cold", "projectile"},
    "freezing pulse": {"spell", "cold", "projectile"},
    "glacial cascade": {"spell", "cold", "physical", "area"},
    "cold snap": {"spell", "cold", "area", "dot"},
    "vortex": {"spell", "cold", "area", "dot"},
    "creeping frost": {"spell", "cold", "area", "dot", "duration"},
    "winter orb": {"spell", "cold", "projectile", "channelling", "duration"},
    "ice spear": {"spell", "cold", "projectile"},
    "arctic breath": {"spell", "cold", "projectile", "area"},
    "frost bomb": {"spell", "cold", "area", "duration"},

    "essence drain": {"spell", "chaos", "projectile", "dot", "duration"},
    "contagion": {"spell", "chaos", "area", "dot", "duration"},
    "blight": {"spell", "chaos", "area", "channelling", "dot"},
    "bane": {"spell", "chaos", "area", "dot", "duration"},
    "soulrend": {"spell", "chaos", "projectile", "dot", "duration"},
    "dark pact": {"spell", "chaos", "area"},
    "forbidden rite": {"spell", "chaos", "projectile", "area"},

    # DOT / RF
    "righteous fire": {"spell", "fire", "area", "dot"},
    "scorching ray": {"spell", "fire", "channelling", "dot"},
    "searing bond": {"spell", "fire", "totem", "dot"},

    # Minion skills
    "raise zombie": {"spell", "minion"},
    "summon raging spirit": {"spell", "fire", "minion", "duration"},
    "summon skeletons": {"spell", "minion", "duration"},
    "raise spectre": {"spell", "minion"},
    "animate weapon": {"spell", "minion", "duration"},
    "summon holy relic": {"spell", "minion"},
    "herald of agony": {"minion"},
    "herald of purity": {"minion", "physical"},
    "absolution": {"spell", "minion", "physical", "lightning"},
    "dominating blow": {"attack", "minion", "melee"},

    # Totem skills
    "ancestral protector": {"attack", "melee", "totem"},
    "ancestral warchief": {"attack", "melee", "area", "totem"},
    "searing bond totem": {"totem", "fire", "dot"},

    # Traps and mines
    "explosive trap": {"trap", "fire", "area"},
    "fire trap": {"trap", "fire", "area", "dot"},
    "seismic trap": {"trap", "physical", "area", "duration"},
    "lightning trap": {"trap", "lightning"},
    "bear trap": {"trap", "physical"},
    "icicle mine": {"mine", "cold", "projectile"},
    "pyroclast mine": {"mine", "fire", "projectile", "area"},
    "arc mine": {"mine", "lightning", "chaining"},

    # Brands
    "storm brand": {"spell", "lightning", "area", "brand", "duration"},
    "penance brand": {"spell", "physical", "lightning", "area", "brand", "duration"},
    "wintertide brand": {"spell", "cold", "area", "brand", "duration", "dot"},
}


def _detect_element(skill_name: str, tags: Set[str]) -> Optional[str]:
    """Detect primary element from skill name or tags."""
    # Check tags first
    elements = ["fire", "cold", "lightning", "chaos", "physical"]
    for elem in elements:
        if elem in tags:
            return elem

    # Check skill name
    if any(kw in skill_name for kw in ["fire", "flame", "burn", "ignite", "magma"]):
        return "fire"
    if any(kw in skill_name for kw in ["cold", "ice", "frost", "freeze", "chill"]):
        return "cold"
    if any(kw in skill_name for kw in ["lightning", "shock", "arc", "spark", "storm"]):
        return "lightning"
    if any(kw in skill_name for kw in ["chaos", "poison", "wither", "blight"]):
        return "chaos"

    return None


# Affinities: which mods are valuable for which skill types
AFFIX_AFFINITIES: Dict[str, Dict[str, float]] = {
    # Tag-based affinities (key is skill tag, value is dict of affix -> multiplier)
    "attack": {
        "attack_speed": 1.5,
        "accuracy": 1.3,
        "physical_damage": 1.2,
        "added_physical_damage": 1.3,
        "melee_damage": 1.2,
    },
    "spell": {
        "cast_speed": 1.5,
        "spell_damage": 1.3,
        "spell_critical_strike_chance": 1.2,
        "mana_regeneration": 1.1,
    },
    "melee": {
        "melee_damage": 1.4,
        "attack_speed": 1.3,
        "weapon_elemental_damage": 1.2,
    },
    "projectile": {
        "projectile_damage": 1.3,
        "projectile_speed": 1.1,
    },
    "area": {
        "area_damage": 1.3,
        "area_of_effect": 1.2,
    },
    "dot": {
        "damage_over_time": 1.5,
        "damage_over_time_multiplier": 1.5,
        "skill_effect_duration": 1.2,
    },
    "minion": {
        "minion_damage": 1.5,
        "minion_life": 1.3,
        "minion_speed": 1.2,
    },
    "fire": {
        "fire_damage": 1.5,
        "fire_penetration": 1.3,
        "burning_damage": 1.3,
        "fire_damage_over_time": 1.4,
    },
    "cold": {
        "cold_damage": 1.5,
        "cold_penetration": 1.3,
        "freeze_chance": 1.1,
    },
    "lightning": {
        "lightning_damage": 1.5,
        "lightning_penetration": 1.3,
        "shock_chance": 1.1,
    },
    "chaos": {
        "chaos_damage": 1.5,
        "chaos_damage_over_time": 1.4,
        "poison_damage": 1.3,
        "wither_effect": 1.2,
    },
    "physical": {
        "physical_damage": 1.5,
        "added_physical_damage": 1.4,
        "impale_chance": 1.2,
    },
    "channelling": {
        "damage_while_channelling": 1.3,
        "channelling_speed": 1.2,
    },
    "totem": {
        "totem_damage": 1.4,
        "totem_life": 1.2,
        "totem_placement_speed": 1.1,
    },
    "trap": {
        "trap_damage": 1.4,
        "trap_throwing_speed": 1.3,
        "trap_cooldown_recovery": 1.2,
    },
    "mine": {
        "mine_damage": 1.4,
        "mine_throwing_speed": 1.3,
        "mine_detonation_speed": 1.2,
    },
    "brand": {
        "brand_damage": 1.4,
        "brand_attachment_range": 1.2,
        "brand_activation_frequency": 1.3,
    },
    "critical": {
        "critical_strike_chance": 1.4,
        "critical_strike_multiplier": 1.4,
    },
    "duration": {
        "skill_effect_duration": 1.3,
    },
}


@dataclass
class SkillAffinity:
    """Represents affix affinities for a skill."""
    skill_name: str
    skill_tags: Set[str]
    primary_element: Optional[str]
    valuable_affixes: Dict[str, float]  # affix_type -> multiplier
    anti_affixes: Set[str]  # Affixes that don't help this skill

    def get_affix_multiplier(self, affix_type: str) -> float:
        """Get the multiplier for an affix type (1.0 = neutral)."""
        return self.valuable_affixes.get(affix_type, 1.0)

    def is_valuable(self, affix_type: str) -> bool:
        """Check if an affix is valuable for this skill."""
        return affix_type in self.valuable_affixes

    def is_anti(self, affix_type: str) -> bool:
        """Check if an affix doesn't help this skill."""
        return affix_type in self.anti_affixes


class SkillAnalyzer:
    """
    Analyzes skills and determines mod affinities.

    Used to prioritize mods that synergize with the build's main skill.
    """

    # Anti-synergy mappings (affixes that don't help certain skill types)
    ANTI_SYNERGIES: Dict[str, Set[str]] = {
        "spell": {"attack_speed", "accuracy", "melee_damage", "added_physical_damage"},
        "attack": {"cast_speed", "spell_damage", "spell_critical_strike_chance"},
        "minion": {"attack_speed", "cast_speed", "spell_damage", "melee_damage"},
        "totem": {"attack_speed", "cast_speed"},  # Use totem-specific stats
        "dot": {"critical_strike_multiplier"},  # DOTs don't crit (usually)
    }

    def __init__(self, main_skill: str = ""):
        """
        Initialize analyzer with main skill name.

        Args:
            main_skill: Name of the main damage skill
        """
        self.main_skill = main_skill
        self._skill_info: Optional[SkillInfo] = None
        self._affinity: Optional[SkillAffinity] = None

        if main_skill:
            self._analyze_skill()

    def _analyze_skill(self) -> None:
        """Analyze the main skill to determine tags and affinities."""
        self._skill_info = SkillInfo.from_name(self.main_skill)

        # Build affinities from tags
        valuable_affixes: Dict[str, float] = {}
        for tag in self._skill_info.tags:
            if tag in AFFIX_AFFINITIES:
                for affix, mult in AFFIX_AFFINITIES[tag].items():
                    # Use highest multiplier if affix appears multiple times
                    if affix not in valuable_affixes or mult > valuable_affixes[affix]:
                        valuable_affixes[affix] = mult

        # Build anti-affixes from tags
        anti_affixes: Set[str] = set()
        for tag in self._skill_info.tags:
            if tag in self.ANTI_SYNERGIES:
                anti_affixes.update(self.ANTI_SYNERGIES[tag])

        # Remove any valuable affixes from anti list
        anti_affixes -= set(valuable_affixes.keys())

        self._affinity = SkillAffinity(
            skill_name=self.main_skill,
            skill_tags=self._skill_info.tags,
            primary_element=self._skill_info.primary_element,
            valuable_affixes=valuable_affixes,
            anti_affixes=anti_affixes,
        )

    def get_affinity(self) -> Optional[SkillAffinity]:
        """Get the skill's affinity information."""
        return self._affinity

    def get_skill_info(self) -> Optional[SkillInfo]:
        """Get basic skill information."""
        return self._skill_info

    def get_affix_multiplier(self, affix_type: str) -> float:
        """
        Get the multiplier for an affix type based on skill affinity.

        Args:
            affix_type: The affix type to check

        Returns:
            Multiplier (>1 = valuable, 1 = neutral, <1 = not useful)
        """
        if not self._affinity:
            return 1.0

        if affix_type in self._affinity.anti_affixes:
            return 0.5  # Reduced value for anti-synergy

        return self._affinity.get_affix_multiplier(affix_type)

    def get_valuable_affixes(self) -> List[Tuple[str, float]]:
        """
        Get list of valuable affixes for this skill, sorted by importance.

        Returns:
            List of (affix_type, multiplier) tuples, highest first
        """
        if not self._affinity:
            return []

        return sorted(
            self._affinity.valuable_affixes.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def get_skill_summary(self) -> str:
        """Get a human-readable summary of skill characteristics."""
        if not self._skill_info:
            return "Unknown skill"

        parts = [self.main_skill]

        if self._skill_info.tags:
            tag_str = ", ".join(sorted(self._skill_info.tags))
            parts.append(f"[{tag_str}]")

        if self._skill_info.primary_element:
            parts.append(f"({self._skill_info.primary_element})")

        return " ".join(parts)

    def is_mod_relevant(self, mod_text: str) -> Tuple[bool, str]:
        """
        Check if a mod is relevant for this skill.

        Args:
            mod_text: The mod text to analyze

        Returns:
            (is_relevant, reason) tuple
        """
        if not self._affinity:
            return True, ""

        mod_lower = mod_text.lower()

        # Check for element match
        if self._skill_info and self._skill_info.primary_element:
            elem = self._skill_info.primary_element
            if elem in mod_lower:
                return True, f"Matches {elem} damage type"

        # Check for obvious mismatches
        if "spell" in self._affinity.skill_tags and "attack" in mod_lower:
            return False, "Attack mod on spell build"
        if "attack" in self._affinity.skill_tags and "spell" in mod_lower:
            return False, "Spell mod on attack build"

        # Check for tag-relevant keywords
        for tag in self._affinity.skill_tags:
            if tag in mod_lower:
                return True, f"Matches {tag} tag"

        return True, ""  # Default to relevant


def analyze_skill(skill_name: str) -> SkillAffinity:
    """
    Convenience function to analyze a skill.

    Args:
        skill_name: Name of the skill to analyze

    Returns:
        SkillAffinity with valuable/anti affixes
    """
    analyzer = SkillAnalyzer(skill_name)
    affinity = analyzer.get_affinity()

    if affinity is None:
        # Return default empty affinity
        return SkillAffinity(
            skill_name=skill_name,
            skill_tags=set(),
            primary_element=None,
            valuable_affixes={},
            anti_affixes=set(),
        )

    return affinity


# Testing
if __name__ == "__main__":
    # Test with different skill types
    test_skills = [
        "Cyclone",
        "Arc",
        "Righteous Fire",
        "Raise Zombie",
        "Tornado Shot",
        "Essence Drain",
    ]

    for skill in test_skills:
        print(f"\n=== {skill} ===")
        analyzer = SkillAnalyzer(skill)
        print(f"Summary: {analyzer.get_skill_summary()}")

        affinity = analyzer.get_affinity()
        if affinity:
            print(f"Primary Element: {affinity.primary_element}")
            print(f"Valuable Affixes:")
            for affix, mult in analyzer.get_valuable_affixes()[:5]:
                print(f"  - {affix}: {mult:.1f}x")
            print(f"Anti Affixes: {', '.join(affinity.anti_affixes) if affinity.anti_affixes else 'None'}")
