"""
Build Summarizer for AI Context.

Generates AI-friendly summaries of PoB builds that can be used
as context when evaluating items or providing upgrade advice.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.pob import PoBBuild, CharacterProfile, PoBItem

logger = logging.getLogger(__name__)


@dataclass
class GearSlotSummary:
    """Summary of a single gear slot."""

    slot: str
    item_name: str
    base_type: str
    rarity: str
    key_mods: List[str] = field(default_factory=list)
    sockets: str = ""
    is_empty: bool = False


@dataclass
class BuildSummary:
    """AI-friendly summary of a PoB build."""

    # Basic info
    name: str
    class_name: str
    ascendancy: str
    level: int
    main_skill: str

    # Defenses
    life: int = 0
    energy_shield: int = 0
    mana: int = 0
    evasion: int = 0
    armour: int = 0
    block_chance: int = 0
    spell_block: int = 0

    # Resistances
    fire_res: int = 0
    cold_res: int = 0
    lightning_res: int = 0
    chaos_res: int = 0

    # Offense
    total_dps: float = 0
    hit_dps: float = 0
    dot_dps: float = 0
    attack_speed: float = 0
    cast_speed: float = 0
    crit_chance: float = 0
    crit_multi: float = 0

    # Key attributes
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0

    # Gear
    gear_slots: List[GearSlotSummary] = field(default_factory=list)
    empty_slots: List[str] = field(default_factory=list)

    # Skills
    active_skills: List[str] = field(default_factory=list)
    support_gems: List[str] = field(default_factory=list)
    auras: List[str] = field(default_factory=list)

    # Build focus (auto-detected)
    damage_type: str = ""  # "Physical", "Fire", "Cold", "Lightning", "Chaos", "Mixed"
    playstyle: str = ""  # "Attack", "Spell", "Minion", "Totem", "Trap/Mine"
    defense_focus: str = ""  # "Life", "ES", "Hybrid", "Evasion", "Armour"

    # Upgrade priorities (for AI advice)
    upgrade_priorities: List[str] = field(default_factory=list)
    stat_goals: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Generate a markdown summary for AI context."""
        lines = [
            f"# Build: {self.name}",
            "",
            f"**Class:** {self.ascendancy or self.class_name} (Level {self.level})",
            f"**Main Skill:** {self.main_skill}",
            "",
        ]

        # Playstyle
        if self.damage_type or self.playstyle:
            lines.append(f"**Build Type:** {self.playstyle} / {self.damage_type}")
            lines.append("")

        # Defenses
        lines.append("## Defenses")
        if self.life:
            lines.append(f"- Life: {self.life:,}")
        if self.energy_shield:
            lines.append(f"- Energy Shield: {self.energy_shield:,}")
        if self.mana:
            lines.append(f"- Mana: {self.mana:,}")
        if self.armour:
            lines.append(f"- Armour: {self.armour:,}")
        if self.evasion:
            lines.append(f"- Evasion: {self.evasion:,}")
        if self.block_chance:
            lines.append(f"- Block: {self.block_chance}%")

        lines.append("")
        lines.append("## Resistances")
        lines.append(
            f"- Fire: {self.fire_res}% | Cold: {self.cold_res}% | "
            f"Lightning: {self.lightning_res}% | Chaos: {self.chaos_res}%"
        )
        lines.append("")

        # Offense
        if self.total_dps:
            lines.append("## Offense")
            lines.append(f"- Total DPS: {self.total_dps:,.0f}")
            if self.hit_dps:
                lines.append(f"- Hit DPS: {self.hit_dps:,.0f}")
            if self.dot_dps:
                lines.append(f"- DoT DPS: {self.dot_dps:,.0f}")
            if self.crit_chance:
                lines.append(f"- Crit: {self.crit_chance:.1f}% ({self.crit_multi:.0f}% multi)")
            lines.append("")

        # Attributes
        lines.append("## Attributes")
        lines.append(f"- STR: {self.strength} | DEX: {self.dexterity} | INT: {self.intelligence}")
        lines.append("")

        # Current Gear
        lines.append("## Current Gear")
        for slot in self.gear_slots:
            if slot.is_empty:
                lines.append(f"- **{slot.slot}:** (empty)")
            else:
                lines.append(f"- **{slot.slot}:** {slot.item_name} ({slot.rarity})")
                if slot.key_mods:
                    for mod in slot.key_mods[:3]:  # Top 3 mods
                        lines.append(f"  - {mod}")
        lines.append("")

        # Empty slots
        if self.empty_slots:
            lines.append(f"**Empty Slots:** {', '.join(self.empty_slots)}")
            lines.append("")

        # Skills
        if self.active_skills:
            lines.append("## Active Skills")
            lines.append(f"{', '.join(self.active_skills)}")
            lines.append("")

        if self.auras:
            lines.append("## Auras/Reservations")
            lines.append(f"{', '.join(self.auras)}")
            lines.append("")

        # Upgrade priorities
        if self.upgrade_priorities:
            lines.append("## Upgrade Priorities")
            for i, priority in enumerate(self.upgrade_priorities, 1):
                lines.append(f"{i}. {priority}")
            lines.append("")

        # Stat goals
        if self.stat_goals:
            lines.append("## Stat Goals")
            for stat, goal in self.stat_goals.items():
                lines.append(f"- {stat}: {goal}")
            lines.append("")

        return "\n".join(lines)

    def to_compact_context(self) -> str:
        """Generate a compact context string for AI prompts."""
        parts = [
            f"Build: {self.ascendancy or self.class_name} Lv{self.level}",
            f"Main Skill: {self.main_skill}",
        ]

        # Key stats
        if self.life:
            parts.append(f"Life: {self.life:,}")
        if self.energy_shield:
            parts.append(f"ES: {self.energy_shield:,}")

        parts.append(
            f"Res: {self.fire_res}F/{self.cold_res}C/{self.lightning_res}L/{self.chaos_res}Ch"
        )

        if self.total_dps:
            parts.append(f"DPS: {self.total_dps:,.0f}")

        # Build type
        if self.playstyle and self.damage_type:
            parts.append(f"Type: {self.playstyle}/{self.damage_type}")

        return " | ".join(parts)


class BuildSummarizer:
    """
    Generates AI-friendly summaries from PoB builds.
    """

    # Important stats to extract from PoB
    STAT_MAPPINGS = {
        # Defenses
        "Life": "life",
        "EnergyShield": "energy_shield",
        "Mana": "mana",
        "Evasion": "evasion",
        "Armour": "armour",
        "BlockChance": "block_chance",
        "SpellBlockChance": "spell_block",
        # Resistances
        "FireResist": "fire_res",
        "ColdResist": "cold_res",
        "LightningResist": "lightning_res",
        "ChaosResist": "chaos_res",
        # Offense
        "TotalDPS": "total_dps",
        "CombinedDPS": "total_dps",
        "FullDPS": "total_dps",
        "HitDPS": "hit_dps",
        "TotalDot": "dot_dps",
        "Speed": "attack_speed",
        "CastSpeed": "cast_speed",
        "CritChance": "crit_chance",
        "CritMultiplier": "crit_multi",
        # Attributes
        "Str": "strength",
        "Dex": "dexterity",
        "Int": "intelligence",
    }

    # Aura skill gems
    AURA_GEMS = {
        "Anger", "Clarity", "Determination", "Discipline", "Grace",
        "Haste", "Hatred", "Herald of Agony", "Herald of Ash",
        "Herald of Ice", "Herald of Purity", "Herald of Thunder",
        "Malevolence", "Precision", "Pride", "Purity of Elements",
        "Purity of Fire", "Purity of Ice", "Purity of Lightning",
        "Vitality", "Wrath", "Zealotry", "Defiance Banner",
        "Dread Banner", "War Banner", "Tempest Shield",
    }

    # Key mods to highlight
    KEY_MOD_PATTERNS = [
        r"\+\d+ to maximum Life",
        r"\+\d+ to maximum Energy Shield",
        r"\+\d+% to .+ Resistance",
        r"Adds \d+ to \d+ .+ Damage",
        r"\+\d+ to .+ Attributes",
        r"\d+% increased .+ Damage",
        r"\d+% increased Attack Speed",
        r"\d+% increased Cast Speed",
        r"\+\d+% to Critical Strike",
        r"Regenerate .+ Life per second",
        r"\+\d to Level of",
    ]

    def __init__(self):
        """Initialize the summarizer."""
        import re
        self._key_mod_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.KEY_MOD_PATTERNS
        ]

    def summarize_build(self, build: "PoBBuild", name: str = "") -> BuildSummary:
        """
        Create a summary from a PoBBuild.

        Args:
            build: The parsed PoB build.
            name: Optional name for the build.

        Returns:
            BuildSummary with extracted data.
        """
        summary = BuildSummary(
            name=name or build.display_name,
            class_name=build.class_name,
            ascendancy=build.ascendancy,
            level=build.level,
            main_skill=build.main_skill,
        )

        # Extract stats from PoB stats dict
        for pob_stat, summary_attr in self.STAT_MAPPINGS.items():
            if pob_stat in build.stats:
                value = build.stats[pob_stat]
                # Convert floats to ints for display stats
                if summary_attr in ("life", "energy_shield", "mana", "evasion", "armour",
                                   "strength", "dexterity", "intelligence"):
                    value = int(value)
                elif summary_attr in ("fire_res", "cold_res", "lightning_res", "chaos_res",
                                     "block_chance", "spell_block"):
                    value = int(value)
                setattr(summary, summary_attr, value)

        # Process gear
        all_slots = [
            "Weapon 1", "Weapon 2", "Helmet", "Body Armour", "Gloves",
            "Boots", "Amulet", "Ring 1", "Ring 2", "Belt",
            "Flask 1", "Flask 2", "Flask 3", "Flask 4", "Flask 5",
        ]

        for slot in all_slots:
            item = build.items.get(slot)
            if item:
                gear_summary = self._summarize_item(slot, item)
                summary.gear_slots.append(gear_summary)
            else:
                # Track empty non-flask slots
                if "Flask" not in slot:
                    summary.empty_slots.append(slot)
                    summary.gear_slots.append(GearSlotSummary(
                        slot=slot,
                        item_name="",
                        base_type="",
                        rarity="",
                        is_empty=True,
                    ))

        # Extract skills
        summary.active_skills = build.skills[:10]  # Limit to 10

        # Detect auras from skill list
        for skill in build.skills:
            if any(aura.lower() in skill.lower() for aura in self.AURA_GEMS):
                summary.auras.append(skill)

        # Auto-detect build type
        summary.damage_type = self._detect_damage_type(build)
        summary.playstyle = self._detect_playstyle(build)
        summary.defense_focus = self._detect_defense_focus(summary)

        # Generate upgrade priorities
        summary.upgrade_priorities = self._generate_upgrade_priorities(summary)
        summary.stat_goals = self._generate_stat_goals(summary)

        return summary

    def summarize_profile(self, profile: "CharacterProfile") -> BuildSummary:
        """
        Create a summary from a CharacterProfile.

        Args:
            profile: The character profile.

        Returns:
            BuildSummary with extracted data.
        """
        return self.summarize_build(profile.build, name=profile.name)

    def _summarize_item(self, slot: str, item: "PoBItem") -> GearSlotSummary:
        """Summarize a single item."""
        # Find key mods
        key_mods = []
        for mod in item.explicit_mods:
            for pattern in self._key_mod_patterns:
                if pattern.search(mod):
                    key_mods.append(mod)
                    break

        return GearSlotSummary(
            slot=slot,
            item_name=item.name or item.base_type,
            base_type=item.base_type,
            rarity=item.rarity,
            key_mods=key_mods[:5],  # Top 5 key mods
            sockets=item.sockets,
            is_empty=False,
        )

    def _detect_damage_type(self, build: "PoBBuild") -> str:
        """Detect the primary damage type."""
        stats = build.stats

        damage_types = {
            "Physical": stats.get("PhysicalDPS", 0) + stats.get("PhysicalDamage", 0),
            "Fire": stats.get("FireDPS", 0) + stats.get("FireDamage", 0),
            "Cold": stats.get("ColdDPS", 0) + stats.get("ColdDamage", 0),
            "Lightning": stats.get("LightningDPS", 0) + stats.get("LightningDamage", 0),
            "Chaos": stats.get("ChaosDPS", 0) + stats.get("ChaosDamage", 0),
        }

        if not any(damage_types.values()):
            # Check main skill name for hints
            main = build.main_skill.lower()
            if "fire" in main or "burn" in main or "ignite" in main:
                return "Fire"
            elif "cold" in main or "freeze" in main or "ice" in main:
                return "Cold"
            elif "lightning" in main or "shock" in main:
                return "Lightning"
            elif "chaos" in main or "poison" in main or "blight" in main:
                return "Chaos"
            return "Mixed"

        max_type = max(damage_types, key=lambda k: damage_types.get(k, 0))
        return max_type

    def _detect_playstyle(self, build: "PoBBuild") -> str:
        """Detect the playstyle (Attack, Spell, Minion, etc.)."""
        main = build.main_skill.lower()

        # Minion keywords
        if any(kw in main for kw in ["zombie", "skeleton", "spectre", "golem", "animate", "summon"]):
            return "Minion"

        # Totem keywords
        if "totem" in main:
            return "Totem"

        # Trap/Mine keywords
        if "trap" in main or "mine" in main:
            return "Trap/Mine"

        # Check attack vs spell from stats
        stats = build.stats
        attack_speed = stats.get("Speed", 0)
        cast_speed = stats.get("CastSpeed", 0)

        if attack_speed > cast_speed:
            return "Attack"
        elif cast_speed > 0:
            return "Spell"

        return "Attack"  # Default

    def _detect_defense_focus(self, summary: BuildSummary) -> str:
        """Detect the primary defense type."""
        life = summary.life
        es = summary.energy_shield
        armour = summary.armour
        evasion = summary.evasion

        if es > life * 1.5:
            return "ES"
        elif es > life * 0.5:
            return "Hybrid"
        elif armour > evasion * 2:
            return "Armour"
        elif evasion > armour * 2:
            return "Evasion"
        else:
            return "Life"

    def _generate_upgrade_priorities(self, summary: BuildSummary) -> List[str]:
        """Generate upgrade priority suggestions based on build state."""
        priorities = []

        # Check resistances
        total_ele_res = summary.fire_res + summary.cold_res + summary.lightning_res
        if total_ele_res < 225:  # Not capped (75% each)
            missing = []
            if summary.fire_res < 75:
                missing.append(f"Fire ({summary.fire_res}%)")
            if summary.cold_res < 75:
                missing.append(f"Cold ({summary.cold_res}%)")
            if summary.lightning_res < 75:
                missing.append(f"Lightning ({summary.lightning_res}%)")
            if missing:
                priorities.append(f"Cap resistances: {', '.join(missing)}")

        if summary.chaos_res < 0:
            priorities.append(f"Improve Chaos res (currently {summary.chaos_res}%)")

        # Check life/ES
        if summary.defense_focus in ("Life", "Hybrid"):
            if summary.life < 4000:
                priorities.append(f"Increase Life (currently {summary.life:,})")
        if summary.defense_focus in ("ES", "Hybrid"):
            if summary.energy_shield < 3000:
                priorities.append(f"Increase ES (currently {summary.energy_shield:,})")

        # Empty slots
        for slot in summary.empty_slots:
            if "Flask" not in slot:
                priorities.append(f"Fill empty slot: {slot}")

        return priorities[:5]  # Top 5

    def _generate_stat_goals(self, summary: BuildSummary) -> Dict[str, str]:
        """Generate stat goals based on build type."""
        goals = {}

        # Resistance goals
        if summary.fire_res < 75:
            goals["Fire Resistance"] = "75%+ (capped)"
        if summary.cold_res < 75:
            goals["Cold Resistance"] = "75%+ (capped)"
        if summary.lightning_res < 75:
            goals["Lightning Resistance"] = "75%+ (capped)"
        if summary.chaos_res < 0:
            goals["Chaos Resistance"] = "0%+ (positive)"

        # Life/ES goals based on defense focus
        if summary.defense_focus in ("Life", "Hybrid", "Armour", "Evasion"):
            if summary.life < 5000:
                goals["Life"] = "5000+ for mapping"
        if summary.defense_focus in ("ES", "Hybrid"):
            if summary.energy_shield < 5000:
                goals["Energy Shield"] = "5000+ for mapping"

        return goals


# Storage for generated summaries
_summary_cache: Dict[str, BuildSummary] = {}


def get_build_summary(profile_name: str) -> Optional[BuildSummary]:
    """Get cached build summary by profile name."""
    return _summary_cache.get(profile_name)


def cache_build_summary(profile_name: str, summary: BuildSummary) -> None:
    """Cache a build summary."""
    _summary_cache[profile_name] = summary


def clear_summary_cache() -> None:
    """Clear the summary cache."""
    _summary_cache.clear()


def save_summary_to_file(summary: BuildSummary, path: Path, format: str = "json") -> bool:
    """
    Save a build summary to a file.

    Args:
        summary: The build summary.
        path: Output file path.
        format: "json" or "markdown"

    Returns:
        True if successful.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            path.write_text(summary.to_json(), encoding="utf-8")
        elif format == "markdown":
            path.write_text(summary.to_markdown(), encoding="utf-8")
        else:
            logger.error(f"Unknown format: {format}")
            return False

        logger.info(f"Saved build summary to {path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save summary: {e}")
        return False


# CLI for testing
if __name__ == "__main__":
    import sys
    from core.pob import CharacterManager

    logging.basicConfig(level=logging.INFO)

    manager = CharacterManager()
    summarizer = BuildSummarizer()

    profiles = manager.list_profiles()

    if not profiles:
        print("No profiles found in CharacterManager")
        print("Try importing a build first with the main application")
        sys.exit(1)

    print(f"Found {len(profiles)} profiles:")
    for i, name in enumerate(profiles, 1):
        print(f"  {i}. {name}")

    # Summarize first profile
    profile = manager.get_profile(profiles[0])
    if profile:
        summary = summarizer.summarize_profile(profile)

        print("\n" + "=" * 60)
        print("MARKDOWN SUMMARY:")
        print("=" * 60)
        print(summary.to_markdown())

        print("\n" + "=" * 60)
        print("COMPACT CONTEXT:")
        print("=" * 60)
        print(summary.to_compact_context())
