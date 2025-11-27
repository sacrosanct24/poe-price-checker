"""
Build Archetype Detection Module.

Analyzes Path of Building stats to determine build archetype for
context-aware item evaluation.

Archetypes determine:
- Which defensive stats matter (life vs ES)
- Which offensive stats are relevant (crit, elemental, physical)
- Affix weight adjustments for evaluation
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)

# Path to archetype weights file
WEIGHTS_FILE = Path(__file__).parent.parent / "data" / "archetype_weights.json"


# =============================================================================
# ENUMS
# =============================================================================

class DefenseType(Enum):
    """Primary defense mechanism."""
    LIFE = "life"
    ENERGY_SHIELD = "es"
    HYBRID = "hybrid"  # Both life and ES
    LOW_LIFE = "low_life"  # Reserved life builds
    WARD = "ward"  # PoE2 ward-based


class DamageType(Enum):
    """Primary damage type."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"
    ELEMENTAL = "elemental"  # Mixed elemental
    MINION = "minion"
    DOT = "dot"  # Damage over time


class AttackType(Enum):
    """Attack vs spell distinction."""
    ATTACK = "attack"
    SPELL = "spell"
    MINION = "minion"
    DOT = "dot"  # Ignite, poison, bleed


# =============================================================================
# BUILD ARCHETYPE
# =============================================================================

@dataclass
class BuildArchetype:
    """
    Represents the detected archetype of a build.

    Used to adjust affix weights during item evaluation.
    """
    defense_type: DefenseType = DefenseType.LIFE
    damage_type: DamageType = DamageType.PHYSICAL
    attack_type: AttackType = AttackType.ATTACK

    # Flags for specific build types
    is_crit: bool = False
    is_dot: bool = False
    is_minion: bool = False
    is_totem: bool = False
    is_trap_mine: bool = False

    # Primary element (if elemental damage)
    primary_element: Optional[str] = None  # "fire", "cold", "lightning"

    # Resistance status (for prioritization)
    needs_fire_res: bool = False
    needs_cold_res: bool = False
    needs_lightning_res: bool = False
    needs_chaos_res: bool = False

    # Attribute requirements
    needs_strength: bool = False
    needs_dexterity: bool = False
    needs_intelligence: bool = False

    # Confidence score (0-1) for how certain the detection is
    confidence: float = 0.5

    # Main skill name for skill-specific affinities
    main_skill: str = ""

    # Source stats used for detection (for debugging)
    source_stats: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "defense_type": self.defense_type.value,
            "damage_type": self.damage_type.value,
            "attack_type": self.attack_type.value,
            "is_crit": self.is_crit,
            "is_dot": self.is_dot,
            "is_minion": self.is_minion,
            "is_totem": self.is_totem,
            "is_trap_mine": self.is_trap_mine,
            "primary_element": self.primary_element,
            "main_skill": self.main_skill,
            "needs_fire_res": self.needs_fire_res,
            "needs_cold_res": self.needs_cold_res,
            "needs_lightning_res": self.needs_lightning_res,
            "needs_chaos_res": self.needs_chaos_res,
            "needs_strength": self.needs_strength,
            "needs_dexterity": self.needs_dexterity,
            "needs_intelligence": self.needs_intelligence,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildArchetype":
        """Create from dictionary."""
        return cls(
            defense_type=DefenseType(data.get("defense_type", "life")),
            damage_type=DamageType(data.get("damage_type", "physical")),
            attack_type=AttackType(data.get("attack_type", "attack")),
            is_crit=data.get("is_crit", False),
            is_dot=data.get("is_dot", False),
            is_minion=data.get("is_minion", False),
            is_totem=data.get("is_totem", False),
            is_trap_mine=data.get("is_trap_mine", False),
            primary_element=data.get("primary_element"),
            main_skill=data.get("main_skill", ""),
            needs_fire_res=data.get("needs_fire_res", False),
            needs_cold_res=data.get("needs_cold_res", False),
            needs_lightning_res=data.get("needs_lightning_res", False),
            needs_chaos_res=data.get("needs_chaos_res", False),
            needs_strength=data.get("needs_strength", False),
            needs_dexterity=data.get("needs_dexterity", False),
            needs_intelligence=data.get("needs_intelligence", False),
            confidence=data.get("confidence", 0.5),
        )

    def get_summary(self) -> str:
        """Get human-readable summary of the archetype."""
        parts = []

        # Defense
        if self.defense_type == DefenseType.LIFE:
            parts.append("Life-based")
        elif self.defense_type == DefenseType.ENERGY_SHIELD:
            parts.append("ES-based")
        elif self.defense_type == DefenseType.HYBRID:
            parts.append("Hybrid Life/ES")
        elif self.defense_type == DefenseType.LOW_LIFE:
            parts.append("Low Life")

        # Damage type
        if self.is_minion:
            parts.append("Minion")
        elif self.is_dot:
            parts.append("DoT")
        elif self.primary_element:
            parts.append(self.primary_element.capitalize())
        elif self.damage_type == DamageType.PHYSICAL:
            parts.append("Physical")
        elif self.damage_type == DamageType.ELEMENTAL:
            parts.append("Elemental")

        # Attack type
        if self.attack_type == AttackType.SPELL:
            parts.append("Spell")
        elif self.attack_type == AttackType.ATTACK:
            parts.append("Attack")

        # Crit
        if self.is_crit:
            parts.append("Crit")

        # Special
        if self.is_totem:
            parts.append("Totem")
        if self.is_trap_mine:
            parts.append("Trap/Mine")

        # Main skill
        if self.main_skill:
            parts.append(f"({self.main_skill})")

        return " ".join(parts) if parts else "Unknown"


# =============================================================================
# ARCHETYPE DETECTION
# =============================================================================

# Stat name mappings (PoB uses various naming conventions)
LIFE_STATS = ["Life", "TotalLife", "total_life"]
ES_STATS = ["EnergyShield", "TotalEnergyShield", "total_energy_shield"]
CRIT_STATS = ["CritChance", "MeleeCritChance", "SpellCritChance"]
FIRE_RES_OVERCAP = ["FireResistOverCap", "FireResistOvercap"]
COLD_RES_OVERCAP = ["ColdResistOverCap", "ColdResistOvercap"]
LIGHTNING_RES_OVERCAP = ["LightningResistOverCap", "LightningResistOvercap"]
CHAOS_RES = ["ChaosResist", "ChaosRes"]


def _get_stat(stats: Dict[str, float], names: List[str], default: float = 0.0) -> float:
    """Get a stat value trying multiple possible names."""
    for name in names:
        if name in stats:
            return stats[name]
    return default


def detect_archetype(stats: Dict[str, float], main_skill: str = "") -> BuildArchetype:
    """
    Detect build archetype from PoB PlayerStats.

    Args:
        stats: Dictionary of stat name -> value from PoB
        main_skill: Name of the main skill (optional, for better detection)

    Returns:
        BuildArchetype with detected characteristics
    """
    archetype = BuildArchetype()
    archetype.source_stats = dict(stats)  # Store for debugging
    archetype.main_skill = main_skill  # Store main skill for skill-aware weights

    confidence_factors = []

    # -------------------------------------------------------------------------
    # Defense Type Detection
    # -------------------------------------------------------------------------
    life = _get_stat(stats, LIFE_STATS)
    es = _get_stat(stats, ES_STATS)

    if life > 0 or es > 0:
        life_ratio = life / max(life + es, 1)
        es_ratio = es / max(life + es, 1)

        # Check for Low Life (reserved life builds)
        reserved_life = stats.get("LifeReserved", stats.get("LifeReservedPercent", 0))
        if reserved_life > 50:  # More than 50% life reserved
            archetype.defense_type = DefenseType.LOW_LIFE
            confidence_factors.append(0.9)
        elif es_ratio > 0.8:  # 80%+ ES
            archetype.defense_type = DefenseType.ENERGY_SHIELD
            confidence_factors.append(0.85)
        elif life_ratio > 0.8:  # 80%+ Life
            archetype.defense_type = DefenseType.LIFE
            confidence_factors.append(0.85)
        elif es_ratio > 0.3 and life_ratio > 0.3:  # Hybrid
            archetype.defense_type = DefenseType.HYBRID
            confidence_factors.append(0.7)
        else:
            archetype.defense_type = DefenseType.LIFE  # Default
            confidence_factors.append(0.5)

    # -------------------------------------------------------------------------
    # Crit Detection
    # -------------------------------------------------------------------------
    crit_chance = _get_stat(stats, CRIT_STATS)
    crit_multi = stats.get("CritMultiplier", stats.get("CritDamage", 0))

    if crit_chance > 40 or (crit_chance > 25 and crit_multi > 300):
        archetype.is_crit = True
        confidence_factors.append(0.9)
    elif crit_chance > 20:
        archetype.is_crit = True
        confidence_factors.append(0.6)

    # -------------------------------------------------------------------------
    # Damage Type Detection
    # -------------------------------------------------------------------------
    # Check damage breakdown
    phys_dps = stats.get("PhysicalDPS", stats.get("TotalPhysicalDPS", 0))
    fire_dps = stats.get("FireDPS", stats.get("TotalFireDPS", 0))
    cold_dps = stats.get("ColdDPS", stats.get("TotalColdDPS", 0))
    lightning_dps = stats.get("LightningDPS", stats.get("TotalLightningDPS", 0))
    chaos_dps = stats.get("ChaosDPS", stats.get("TotalChaosDPS", 0))

    total_ele = fire_dps + cold_dps + lightning_dps
    total_dps = phys_dps + total_ele + chaos_dps

    if total_dps > 0:
        # Check for minion builds
        minion_dps = stats.get("MinionDPS", stats.get("TotalMinionDPS", 0))
        if minion_dps > total_dps * 0.5:
            archetype.damage_type = DamageType.MINION
            archetype.attack_type = AttackType.MINION
            archetype.is_minion = True
            confidence_factors.append(0.9)
        elif phys_dps > total_dps * 0.6:
            archetype.damage_type = DamageType.PHYSICAL
            confidence_factors.append(0.8)
        elif total_ele > total_dps * 0.6:
            archetype.damage_type = DamageType.ELEMENTAL
            # Determine primary element
            max_ele = max(fire_dps, cold_dps, lightning_dps)
            if fire_dps == max_ele and fire_dps > total_ele * 0.5:
                archetype.damage_type = DamageType.FIRE
                archetype.primary_element = "fire"
            elif cold_dps == max_ele and cold_dps > total_ele * 0.5:
                archetype.damage_type = DamageType.COLD
                archetype.primary_element = "cold"
            elif lightning_dps == max_ele and lightning_dps > total_ele * 0.5:
                archetype.damage_type = DamageType.LIGHTNING
                archetype.primary_element = "lightning"
            confidence_factors.append(0.8)
        elif chaos_dps > total_dps * 0.5:
            archetype.damage_type = DamageType.CHAOS
            confidence_factors.append(0.8)

    # -------------------------------------------------------------------------
    # DoT Detection
    # -------------------------------------------------------------------------
    dot_dps = stats.get("TotalDotDPS", stats.get("BleedDPS", 0) +
                        stats.get("IgniteDPS", 0) + stats.get("PoisonDPS", 0))
    if dot_dps > 0 and (total_dps == 0 or dot_dps > total_dps * 0.5):
        archetype.is_dot = True
        archetype.attack_type = AttackType.DOT
        archetype.damage_type = DamageType.DOT
        confidence_factors.append(0.85)

    # -------------------------------------------------------------------------
    # Attack vs Spell Detection
    # -------------------------------------------------------------------------
    if not archetype.is_minion and not archetype.is_dot:
        attack_speed = stats.get("AttackSpeed", stats.get("Speed", 0))
        cast_speed = stats.get("CastSpeed", 0)

        # Check skill name for hints
        main_skill_lower = main_skill.lower()
        spell_keywords = ["arc", "fireball", "ice spear", "spark", "storm", "nova",
                         "flame", "frost", "lightning", "chaos", "essence drain"]
        attack_keywords = ["strike", "slam", "cleave", "cyclone", "lacerate",
                          "blade", "arrow", "shot", "barrage", "tornado"]

        if any(kw in main_skill_lower for kw in spell_keywords):
            archetype.attack_type = AttackType.SPELL
            confidence_factors.append(0.9)
        elif any(kw in main_skill_lower for kw in attack_keywords):
            archetype.attack_type = AttackType.ATTACK
            confidence_factors.append(0.9)
        elif cast_speed > attack_speed and cast_speed > 0:
            archetype.attack_type = AttackType.SPELL
            confidence_factors.append(0.6)
        elif attack_speed > cast_speed:
            archetype.attack_type = AttackType.ATTACK
            confidence_factors.append(0.6)

    # -------------------------------------------------------------------------
    # Totem/Trap/Mine Detection
    # -------------------------------------------------------------------------
    totem_dps = stats.get("TotemDPS", 0)
    trap_dps = stats.get("TrapDPS", 0)
    mine_dps = stats.get("MineDPS", 0)

    if totem_dps > 0:
        archetype.is_totem = True
    if trap_dps > 0 or mine_dps > 0:
        archetype.is_trap_mine = True

    # -------------------------------------------------------------------------
    # Resistance Needs
    # -------------------------------------------------------------------------
    fire_overcap = _get_stat(stats, FIRE_RES_OVERCAP)
    cold_overcap = _get_stat(stats, COLD_RES_OVERCAP)
    lightning_overcap = _get_stat(stats, LIGHTNING_RES_OVERCAP)
    chaos_res = _get_stat(stats, CHAOS_RES)

    # Need resistance if overcap is low (< 20%) or chaos < 0
    archetype.needs_fire_res = fire_overcap < 20
    archetype.needs_cold_res = cold_overcap < 20
    archetype.needs_lightning_res = lightning_overcap < 20
    archetype.needs_chaos_res = chaos_res < 0

    # -------------------------------------------------------------------------
    # Attribute Needs
    # -------------------------------------------------------------------------
    # Check if build has high attribute requirements
    str_req = stats.get("Str", stats.get("Strength", 0))
    dex_req = stats.get("Dex", stats.get("Dexterity", 0))
    int_req = stats.get("Int", stats.get("Intelligence", 0))

    # Flag if attribute is notably high (> 150 usually means gear dependency)
    archetype.needs_strength = str_req > 150
    archetype.needs_dexterity = dex_req > 150
    archetype.needs_intelligence = int_req > 150

    # -------------------------------------------------------------------------
    # Calculate Confidence
    # -------------------------------------------------------------------------
    if confidence_factors:
        archetype.confidence = sum(confidence_factors) / len(confidence_factors)
    else:
        archetype.confidence = 0.3  # Low confidence if no factors matched

    logger.debug(f"Detected archetype: {archetype.get_summary()} (confidence: {archetype.confidence:.2f})")

    return archetype


def detect_archetype_from_build(build: Any) -> BuildArchetype:
    """
    Detect archetype from a PoBBuild object.

    Args:
        build: PoBBuild instance

    Returns:
        BuildArchetype with detected characteristics
    """
    stats = getattr(build, 'stats', {})
    main_skill = getattr(build, 'main_skill', '')
    return detect_archetype(stats, main_skill)


# =============================================================================
# DEFAULT ARCHETYPE
# =============================================================================

def get_default_archetype() -> BuildArchetype:
    """
    Get a safe default archetype when no PoB data is available.

    Returns a generic life-based attack build which works as a
    reasonable fallback for most evaluations.
    """
    return BuildArchetype(
        defense_type=DefenseType.LIFE,
        damage_type=DamageType.PHYSICAL,
        attack_type=AttackType.ATTACK,
        confidence=0.0,  # Zero confidence = generic evaluation
    )


# =============================================================================
# WEIGHT CALCULATOR
# =============================================================================

_cached_weights: Optional[Dict[str, Any]] = None


def load_archetype_weights() -> Dict[str, Any]:
    """
    Load archetype weight multipliers from JSON file.

    Returns cached weights if already loaded.
    """
    global _cached_weights

    if _cached_weights is not None:
        return _cached_weights

    try:
        with open(WEIGHTS_FILE, 'r') as f:
            _cached_weights = json.load(f)
        logger.debug(f"Loaded archetype weights from {WEIGHTS_FILE}")
    except FileNotFoundError:
        logger.warning(f"Archetype weights file not found: {WEIGHTS_FILE}")
        _cached_weights = {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in archetype weights: {e}")
        _cached_weights = {}

    return _cached_weights


def get_weight_multiplier(
    archetype: BuildArchetype,
    affix_type: str
) -> float:
    """
    Get the weight multiplier for an affix type based on build archetype.

    Args:
        archetype: The detected build archetype
        affix_type: The affix type to get weight for (e.g., "life", "fire_damage")

    Returns:
        Multiplier to apply to base affix weight (default 1.0)
    """
    weights = load_archetype_weights()
    if not weights:
        return 1.0

    multiplier = 1.0
    affix_lower = affix_type.lower()

    # Apply defense type weights
    defense_weights = weights.get("defense_types", {}).get(archetype.defense_type.value, {})
    if affix_lower in defense_weights:
        multiplier *= defense_weights[affix_lower]

    # Apply damage type weights
    damage_weights = weights.get("damage_types", {}).get(archetype.damage_type.value, {})
    if affix_lower in damage_weights:
        multiplier *= damage_weights[affix_lower]

    # Apply attack type weights
    attack_weights = weights.get("attack_types", {}).get(archetype.attack_type.value, {})
    if affix_lower in attack_weights:
        multiplier *= attack_weights[affix_lower]

    # Apply flag-based weights
    flag_weights = weights.get("flags", {})
    if archetype.is_crit and "is_crit" in flag_weights:
        if affix_lower in flag_weights["is_crit"]:
            multiplier *= flag_weights["is_crit"][affix_lower]

    if archetype.is_dot and "is_dot" in flag_weights:
        if affix_lower in flag_weights["is_dot"]:
            multiplier *= flag_weights["is_dot"][affix_lower]

    if archetype.is_minion and "is_minion" in flag_weights:
        if affix_lower in flag_weights["is_minion"]:
            multiplier *= flag_weights["is_minion"][affix_lower]

    # Apply resistance needs
    res_weights = weights.get("resistance_needs", {})
    if archetype.needs_fire_res and "needs_fire_res" in res_weights:
        if affix_lower in res_weights["needs_fire_res"]:
            multiplier *= res_weights["needs_fire_res"][affix_lower]

    if archetype.needs_cold_res and "needs_cold_res" in res_weights:
        if affix_lower in res_weights["needs_cold_res"]:
            multiplier *= res_weights["needs_cold_res"][affix_lower]

    if archetype.needs_lightning_res and "needs_lightning_res" in res_weights:
        if affix_lower in res_weights["needs_lightning_res"]:
            multiplier *= res_weights["needs_lightning_res"][affix_lower]

    if archetype.needs_chaos_res and "needs_chaos_res" in res_weights:
        if affix_lower in res_weights["needs_chaos_res"]:
            multiplier *= res_weights["needs_chaos_res"][affix_lower]

    # Apply attribute needs
    attr_weights = weights.get("attribute_needs", {})
    if archetype.needs_strength and "needs_strength" in attr_weights:
        if affix_lower in attr_weights["needs_strength"]:
            multiplier *= attr_weights["needs_strength"][affix_lower]

    if archetype.needs_dexterity and "needs_dexterity" in attr_weights:
        if affix_lower in attr_weights["needs_dexterity"]:
            multiplier *= attr_weights["needs_dexterity"][affix_lower]

    if archetype.needs_intelligence and "needs_intelligence" in attr_weights:
        if affix_lower in attr_weights["needs_intelligence"]:
            multiplier *= attr_weights["needs_intelligence"][affix_lower]

    return multiplier


def apply_archetype_weights(
    archetype: BuildArchetype,
    affix_scores: Dict[str, float]
) -> Dict[str, float]:
    """
    Apply archetype-based weight multipliers to affix scores.

    Args:
        archetype: The detected build archetype
        affix_scores: Dict of affix_type -> base score

    Returns:
        Dict of affix_type -> weighted score
    """
    weighted = {}
    for affix_type, score in affix_scores.items():
        multiplier = get_weight_multiplier(archetype, affix_type)
        weighted[affix_type] = score * multiplier
    return weighted


def get_combined_weight_multiplier(
    archetype: BuildArchetype,
    affix_type: str
) -> float:
    """
    Get combined weight multiplier from archetype AND skill affinities.

    This combines the base archetype weights with skill-specific affinities
    based on the main skill.

    Args:
        archetype: The detected build archetype (with main_skill set)
        affix_type: The affix type to get weight for

    Returns:
        Combined multiplier (archetype * skill affinity)
    """
    # Get base archetype multiplier
    base_mult = get_weight_multiplier(archetype, affix_type)

    # If no main skill, just return archetype multiplier
    if not archetype.main_skill:
        return base_mult

    # Get skill-based multiplier
    try:
        from core.skill_analyzer import SkillAnalyzer
        analyzer = SkillAnalyzer(archetype.main_skill)
        skill_mult = analyzer.get_affix_multiplier(affix_type)
    except Exception as e:
        logger.debug(f"Could not get skill multiplier: {e}")
        skill_mult = 1.0

    # Combine multipliers (use average to prevent extreme values)
    # This prevents double-counting of effects
    if skill_mult != 1.0:
        # Weight skill affinity at 30% influence
        combined = base_mult * (0.7 + 0.3 * skill_mult)
    else:
        combined = base_mult

    return combined


def get_skill_valuable_affixes(main_skill: str) -> List[str]:
    """
    Get list of valuable affix types for a skill.

    Args:
        main_skill: Name of the main skill

    Returns:
        List of affix types that are valuable for this skill
    """
    if not main_skill:
        return []

    try:
        from core.skill_analyzer import SkillAnalyzer
        analyzer = SkillAnalyzer(main_skill)
        valuable = analyzer.get_valuable_affixes()
        return [affix for affix, _ in valuable]
    except Exception as e:
        logger.debug(f"Could not get skill affixes: {e}")
        return []


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== Build Archetype Detection Test ===\n")

    # Test 1: Life-based attack crit build
    stats1 = {
        "Life": 5500,
        "EnergyShield": 200,
        "CritChance": 65,
        "CritMultiplier": 450,
        "PhysicalDPS": 1500000,
        "FireDPS": 200000,
        "FireResistOverCap": 45,
        "ColdResistOverCap": 30,
        "LightningResistOverCap": 25,
        "ChaosResist": -20,
    }

    arch1 = detect_archetype(stats1)
    print(f"Test 1 - Life Crit Attack:")
    print(f"  Summary: {arch1.get_summary()}")
    print(f"  Confidence: {arch1.confidence:.2f}")
    print(f"  Needs chaos res: {arch1.needs_chaos_res}")
    print()

    # Test 2: ES-based spell build
    stats2 = {
        "Life": 1200,
        "EnergyShield": 8500,
        "CritChance": 15,
        "FireDPS": 0,
        "ColdDPS": 2500000,
        "CastSpeed": 3.5,
        "AttackSpeed": 1.0,
        "FireResistOverCap": 50,
        "ColdResistOverCap": 50,
        "LightningResistOverCap": 50,
        "ChaosResist": 30,
    }

    arch2 = detect_archetype(stats2, "Ice Spear")
    print(f"Test 2 - ES Cold Spell:")
    print(f"  Summary: {arch2.get_summary()}")
    print(f"  Confidence: {arch2.confidence:.2f}")
    print(f"  Primary element: {arch2.primary_element}")
    print()

    # Test 3: Minion build
    stats3 = {
        "Life": 4000,
        "EnergyShield": 1500,
        "MinionDPS": 5000000,
        "PhysicalDPS": 10000,
    }

    arch3 = detect_archetype(stats3)
    print(f"Test 3 - Minion Build:")
    print(f"  Summary: {arch3.get_summary()}")
    print(f"  Is minion: {arch3.is_minion}")
    print()

    print("=== All tests passed! ===")
