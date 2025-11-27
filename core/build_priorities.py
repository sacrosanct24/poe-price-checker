"""
Build Priorities System.

Stores user-defined stat priorities for BiS item searching.
Three tiers: Critical (must-have), Important (high priority), Nice-to-have (optional).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class PriorityTier(str, Enum):
    """Priority tiers for stats."""
    CRITICAL = "critical"      # Must-have stats
    IMPORTANT = "important"    # High priority
    NICE_TO_HAVE = "nice_to_have"  # Optional/bonus


# Available stats that can be prioritized
AVAILABLE_STATS = {
    # Defensive
    "life": "Maximum Life",
    "energy_shield": "Energy Shield",
    "armour": "Armour",
    "evasion": "Evasion",
    "spell_suppression": "Spell Suppression",

    # Resistances
    "fire_resistance": "Fire Resistance",
    "cold_resistance": "Cold Resistance",
    "lightning_resistance": "Lightning Resistance",
    "chaos_resistance": "Chaos Resistance",
    "all_resistances": "All Elemental Resistances",

    # Attributes
    "strength": "Strength",
    "dexterity": "Dexterity",
    "intelligence": "Intelligence",
    "all_attributes": "All Attributes",

    # Offensive - General
    "attack_speed": "Attack Speed",
    "cast_speed": "Cast Speed",
    "critical_strike_chance": "Critical Strike Chance",
    "critical_strike_multiplier": "Critical Strike Multiplier",

    # Offensive - Damage Types
    "physical_damage": "Physical Damage",
    "fire_damage": "Fire Damage",
    "cold_damage": "Cold Damage",
    "lightning_damage": "Lightning Damage",
    "chaos_damage": "Chaos Damage",
    "elemental_damage": "Elemental Damage",
    "spell_damage": "Spell Damage",
    "damage_over_time": "Damage over Time",
    "minion_damage": "Minion Damage",

    # Utility
    "movement_speed": "Movement Speed",
    "mana": "Maximum Mana",
    "mana_regeneration": "Mana Regeneration",
    "life_regeneration": "Life Regeneration",
    "cooldown_recovery": "Cooldown Recovery",
    "flask_charges": "Flask Charges",

    # Specific
    "gem_levels": "+Level to Gems",
    "aura_effect": "Aura Effect",
    "curse_effect": "Curse Effect",
}


@dataclass
class StatPriority:
    """A single stat with its priority and optional minimum value."""
    stat_type: str  # Key from AVAILABLE_STATS
    tier: PriorityTier
    min_value: Optional[int] = None  # Optional minimum value for search
    notes: str = ""  # User notes about why this stat is important

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stat_type": self.stat_type,
            "tier": self.tier.value,
            "min_value": self.min_value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatPriority":
        return cls(
            stat_type=data["stat_type"],
            tier=PriorityTier(data["tier"]),
            min_value=data.get("min_value"),
            notes=data.get("notes", ""),
        )


@dataclass
class BuildPriorities:
    """
    User-defined stat priorities for a build.

    Used by BiS search to know what stats to prioritize.
    """
    # Priorities organized by tier
    critical: List[StatPriority] = field(default_factory=list)
    important: List[StatPriority] = field(default_factory=list)
    nice_to_have: List[StatPriority] = field(default_factory=list)

    # Build type hints (helps with slot-specific searches)
    is_life_build: bool = True
    is_es_build: bool = False
    is_hybrid: bool = False
    uses_attack: bool = False
    uses_spell: bool = False
    uses_dot: bool = False
    uses_minions: bool = False

    def add_priority(self, stat_type: str, tier: PriorityTier,
                     min_value: Optional[int] = None, notes: str = "") -> None:
        """Add a stat priority."""
        priority = StatPriority(stat_type, tier, min_value, notes)

        # Remove from other tiers first
        self.remove_priority(stat_type)

        # Add to appropriate tier
        if tier == PriorityTier.CRITICAL:
            self.critical.append(priority)
        elif tier == PriorityTier.IMPORTANT:
            self.important.append(priority)
        else:
            self.nice_to_have.append(priority)

    def remove_priority(self, stat_type: str) -> None:
        """Remove a stat from all tiers."""
        self.critical = [p for p in self.critical if p.stat_type != stat_type]
        self.important = [p for p in self.important if p.stat_type != stat_type]
        self.nice_to_have = [p for p in self.nice_to_have if p.stat_type != stat_type]

    def get_priority(self, stat_type: str) -> Optional[StatPriority]:
        """Get priority for a stat, or None if not set."""
        for p in self.critical:
            if p.stat_type == stat_type:
                return p
        for p in self.important:
            if p.stat_type == stat_type:
                return p
        for p in self.nice_to_have:
            if p.stat_type == stat_type:
                return p
        return None

    def get_all_priorities(self) -> List[StatPriority]:
        """Get all priorities in order (critical first)."""
        return self.critical + self.important + self.nice_to_have

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "critical": [p.to_dict() for p in self.critical],
            "important": [p.to_dict() for p in self.important],
            "nice_to_have": [p.to_dict() for p in self.nice_to_have],
            "is_life_build": self.is_life_build,
            "is_es_build": self.is_es_build,
            "is_hybrid": self.is_hybrid,
            "uses_attack": self.uses_attack,
            "uses_spell": self.uses_spell,
            "uses_dot": self.uses_dot,
            "uses_minions": self.uses_minions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildPriorities":
        """Deserialize from dictionary."""
        priorities = cls()

        for p_data in data.get("critical", []):
            priorities.critical.append(StatPriority.from_dict(p_data))
        for p_data in data.get("important", []):
            priorities.important.append(StatPriority.from_dict(p_data))
        for p_data in data.get("nice_to_have", []):
            priorities.nice_to_have.append(StatPriority.from_dict(p_data))

        priorities.is_life_build = data.get("is_life_build", True)
        priorities.is_es_build = data.get("is_es_build", False)
        priorities.is_hybrid = data.get("is_hybrid", False)
        priorities.uses_attack = data.get("uses_attack", False)
        priorities.uses_spell = data.get("uses_spell", False)
        priorities.uses_dot = data.get("uses_dot", False)
        priorities.uses_minions = data.get("uses_minions", False)

        return priorities


def suggest_priorities_from_build(build_stats: Dict[str, float]) -> BuildPriorities:
    """
    Analyze build stats and suggest priorities.

    This is a starting point that users can customize.

    Args:
        build_stats: Stats dictionary from PoBBuild.stats

    Returns:
        BuildPriorities with suggested settings
    """
    priorities = BuildPriorities()

    # Determine build type
    life = build_stats.get("Life", 0)
    es = build_stats.get("EnergyShield", 0)

    if es > life * 2:
        priorities.is_life_build = False
        priorities.is_es_build = True
        priorities.add_priority("energy_shield", PriorityTier.CRITICAL,
                               notes="ES build - Energy Shield is primary defense")
    elif life > es * 2:
        priorities.is_life_build = True
        priorities.is_es_build = False
        priorities.add_priority("life", PriorityTier.CRITICAL,
                               notes="Life build - Maximum Life is primary defense")
    else:
        priorities.is_hybrid = True
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("energy_shield", PriorityTier.IMPORTANT)

    # Check resistance needs
    fire_overcap = build_stats.get("FireResistOverCap", 0)
    cold_overcap = build_stats.get("ColdResistOverCap", 0)
    lightning_overcap = build_stats.get("LightningResistOverCap", 0)
    chaos_res = build_stats.get("ChaosResist", 0)

    overcap_threshold = 30

    if fire_overcap < overcap_threshold:
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT,
                               notes=f"Fire res overcap low ({int(fire_overcap)}%)")
    if cold_overcap < overcap_threshold:
        priorities.add_priority("cold_resistance", PriorityTier.IMPORTANT,
                               notes=f"Cold res overcap low ({int(cold_overcap)}%)")
    if lightning_overcap < overcap_threshold:
        priorities.add_priority("lightning_resistance", PriorityTier.IMPORTANT,
                               notes=f"Lightning res overcap low ({int(lightning_overcap)}%)")
    if chaos_res < 40:
        priorities.add_priority("chaos_resistance", PriorityTier.NICE_TO_HAVE,
                               notes=f"Chaos res could be higher ({int(chaos_res)}%)")

    # Check attribute needs
    str_val = build_stats.get("Str", 0)
    str_req = build_stats.get("ReqStr", 0)
    dex_val = build_stats.get("Dex", 0)
    dex_req = build_stats.get("ReqDex", 0)
    int_val = build_stats.get("Int", 0)
    int_req = build_stats.get("ReqInt", 0)

    if str_val < str_req + 20:
        priorities.add_priority("strength", PriorityTier.IMPORTANT,
                               notes=f"Strength close to requirement ({int(str_val)}/{int(str_req)})")
    if dex_val < dex_req + 20:
        priorities.add_priority("dexterity", PriorityTier.IMPORTANT,
                               notes=f"Dexterity close to requirement ({int(dex_val)}/{int(dex_req)})")
    if int_val < int_req + 20:
        priorities.add_priority("intelligence", PriorityTier.IMPORTANT,
                               notes=f"Intelligence close to requirement ({int(int_val)}/{int(int_req)})")

    # Analyze damage type from DPS stats
    combined_dps = build_stats.get("CombinedDPS", 0)
    ignite_dps = build_stats.get("IgniteDPS", 0)
    total_dot = build_stats.get("TotalDotDPS", 0)

    if total_dot > combined_dps * 0.5:
        priorities.uses_dot = True
        priorities.add_priority("damage_over_time", PriorityTier.NICE_TO_HAVE,
                               notes="Build uses DoT damage")

    # Check for spell vs attack (simplified - could be enhanced)
    # This would need more context from skills to be accurate

    # Movement speed is always nice
    priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE,
                           notes="Quality of life")

    return priorities


# Testing
if __name__ == "__main__":
    # Test with sample build stats
    sample_stats = {
        "Life": 5637.0,
        "EnergyShield": 113.0,
        "FireResistOverCap": 15.0,
        "ColdResistOverCap": 136.0,
        "LightningResistOverCap": 132.0,
        "ChaosResist": 30.0,
        "Str": 332.0,
        "ReqStr": 224.0,
        "Dex": 128.0,
        "ReqDex": 111.0,
        "Int": 144.0,
        "ReqInt": 131.0,
        "CombinedDPS": 294808.0,
        "TotalDotDPS": 256940.0,
    }

    priorities = suggest_priorities_from_build(sample_stats)

    print("=== Suggested Build Priorities ===")
    print(f"Build Type: Life={priorities.is_life_build}, ES={priorities.is_es_build}")
    print()

    print("Critical:")
    for p in priorities.critical:
        print(f"  - {AVAILABLE_STATS.get(p.stat_type, p.stat_type)}: {p.notes}")

    print("\nImportant:")
    for p in priorities.important:
        print(f"  - {AVAILABLE_STATS.get(p.stat_type, p.stat_type)}: {p.notes}")

    print("\nNice to Have:")
    for p in priorities.nice_to_have:
        print(f"  - {AVAILABLE_STATS.get(p.stat_type, p.stat_type)}: {p.notes}")

    print("\n=== Serialization Test ===")
    data = priorities.to_dict()
    restored = BuildPriorities.from_dict(data)
    print(f"Critical count: {len(restored.critical)}")
    print(f"Important count: {len(restored.important)}")
    print(f"Nice to Have count: {len(restored.nice_to_have)}")
