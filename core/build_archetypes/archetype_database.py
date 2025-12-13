"""
Build Archetype Database.

Contains definitions of 25+ popular build archetypes for PoE1.
These are used to analyze items for cross-build value.

Data sourced from:
- poe.ninja build statistics
- Popular build guides (maxroll, poebuilds)
- Community meta analysis
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.build_archetypes.archetype_models import (
    BuildArchetype,
    BuildCategory,
    DamageType,
    DefenseType,
    StatWeight,
)


def _create_stat_weights(stats: Dict[str, float]) -> List[StatWeight]:
    """Helper to create StatWeight list from dict."""
    return [StatWeight(stat_name=k, weight=v) for k, v in stats.items()]


# =============================================================================
# META BUILD ARCHETYPES
# =============================================================================

# --- Attack Builds ---

RF_JUGGERNAUT = BuildArchetype(
    id="rf_juggernaut",
    name="RF Juggernaut",
    description="Righteous Fire tank with high life regen",
    category=BuildCategory.DOT,
    ascendancy="Juggernaut",
    damage_types=[DamageType.FIRE],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 2.0,
        "life_regeneration_rate": 2.0,
        "fire_resistance": 1.8,
        "maximum_fire_resistance": 2.5,
        "fire_damage_over_time_multiplier": 1.5,
        "burning_damage": 1.5,
        "armour": 1.3,
        "strength": 1.2,
    }),
    required_stats={"maximum_life"},
    popularity=0.08,
    tags=["tanky", "league_starter", "rf", "dot", "fire", "regen"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

LIGHTNING_ARROW_DEADEYE = BuildArchetype(
    id="la_deadeye",
    name="Lightning Arrow Deadeye",
    description="Fast bow build with chain and pierce",
    category=BuildCategory.ATTACK,
    ascendancy="Deadeye",
    damage_types=[DamageType.LIGHTNING, DamageType.ELEMENTAL],
    defense_types=[DefenseType.EVASION, DefenseType.LIFE],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "elemental_damage_with_attacks": 2.0,
        "lightning_damage": 1.8,
        "attack_speed": 1.5,
        "critical_strike_chance": 1.8,
        "critical_strike_multiplier": 1.8,
        "added_lightning_damage": 1.5,
        "accuracy_rating": 1.3,
        "evasion_rating": 1.2,
        "dexterity": 1.2,
    }),
    required_stats={"maximum_life"},
    popularity=0.06,
    tags=["bow", "fast", "clear", "lightning", "crit", "mapping"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

BONESHATTER_JUGGERNAUT = BuildArchetype(
    id="boneshatter_jugg",
    name="Boneshatter Juggernaut",
    description="Melee slam build with trauma stacking",
    category=BuildCategory.ATTACK,
    ascendancy="Juggernaut",
    damage_types=[DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 2.0,
        "physical_damage": 1.8,
        "attack_speed": 1.5,
        "melee_damage": 1.5,
        "armour": 1.5,
        "stun_threshold_reduction": 1.3,
        "strength": 1.3,
        "added_physical_damage": 1.5,
    }),
    required_stats={"maximum_life"},
    popularity=0.05,
    tags=["melee", "slam", "tanky", "league_starter", "physical", "stun"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

TORNADO_SHOT_DEADEYE = BuildArchetype(
    id="ts_deadeye",
    name="Tornado Shot Deadeye",
    description="High-budget bow build with insane clear",
    category=BuildCategory.ATTACK,
    ascendancy="Deadeye",
    damage_types=[DamageType.PHYSICAL, DamageType.ELEMENTAL],
    defense_types=[DefenseType.EVASION, DefenseType.LIFE],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "elemental_damage_with_attacks": 2.0,
        "added_cold_damage": 1.8,
        "added_lightning_damage": 1.8,
        "critical_strike_chance": 2.0,
        "critical_strike_multiplier": 2.0,
        "attack_speed": 1.5,
        "projectile_speed": 1.3,
        "dexterity": 1.2,
    }),
    required_stats={"maximum_life", "critical_strike_chance"},
    popularity=0.04,
    tags=["bow", "expensive", "crit", "elemental", "mapping", "endgame"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

CYCLONE_SLAYER = BuildArchetype(
    id="cyclone_slayer",
    name="Cyclone Slayer",
    description="Classic melee spin-to-win build",
    category=BuildCategory.ATTACK,
    ascendancy="Slayer",
    damage_types=[DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "physical_damage": 1.8,
        "attack_speed": 1.5,
        "melee_damage": 1.5,
        "critical_strike_chance": 1.5,
        "critical_strike_multiplier": 1.5,
        "life_leech": 1.8,
        "area_of_effect": 1.3,
        "strength": 1.2,
    }),
    required_stats={"maximum_life"},
    popularity=0.04,
    tags=["melee", "cyclone", "leech", "physical", "crit"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=2,
)

# --- Spell Builds ---

SPARK_INQUISITOR = BuildArchetype(
    id="spark_inquisitor",
    name="Spark Inquisitor",
    description="Lightning spell with high clear speed",
    category=BuildCategory.SPELL,
    ascendancy="Inquisitor",
    damage_types=[DamageType.LIGHTNING],
    defense_types=[DefenseType.LIFE, DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "spell_damage": 1.8,
        "lightning_damage": 2.0,
        "cast_speed": 1.5,
        "critical_strike_chance_for_spells": 1.8,
        "critical_strike_multiplier": 1.8,
        "projectile_speed": 1.5,
        "mana_regeneration": 1.3,
        "intelligence": 1.2,
    }),
    required_stats={"spell_damage"},
    popularity=0.05,
    tags=["spell", "lightning", "crit", "clear", "inquisitor"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=2,
)

COLD_DOT_OCCULTIST = BuildArchetype(
    id="cold_dot_occultist",
    name="Cold DoT Occultist",
    description="Vortex/Cold Snap damage over time build",
    category=BuildCategory.DOT,
    ascendancy="Occultist",
    damage_types=[DamageType.COLD],
    defense_types=[DefenseType.ENERGY_SHIELD, DefenseType.LIFE],
    key_stats=_create_stat_weights({
        "maximum_energy_shield": 2.0,
        "cold_damage_over_time_multiplier": 2.0,
        "spell_damage": 1.5,
        "cold_damage": 1.8,
        "energy_shield_recharge": 1.5,
        "chaos_resistance": 1.3,
        "intelligence": 1.2,
    }),
    required_stats={"cold_damage_over_time_multiplier"},
    popularity=0.04,
    tags=["spell", "cold", "dot", "es", "occultist", "tanky"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

ARC_ELEMENTALIST = BuildArchetype(
    id="arc_elementalist",
    name="Arc Elementalist",
    description="Chain lightning spell caster",
    category=BuildCategory.SPELL,
    ascendancy="Elementalist",
    damage_types=[DamageType.LIGHTNING],
    defense_types=[DefenseType.LIFE, DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "spell_damage": 1.8,
        "lightning_damage": 2.0,
        "cast_speed": 1.5,
        "critical_strike_chance_for_spells": 1.5,
        "shock_effect": 1.5,
        "mana": 1.2,
        "intelligence": 1.2,
    }),
    required_stats={"spell_damage"},
    popularity=0.03,
    tags=["spell", "lightning", "chain", "clear", "elementalist"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

FIREBALL_IGNITE_ELEMENTALIST = BuildArchetype(
    id="fireball_ignite",
    name="Fireball Ignite Elementalist",
    description="Ignite-based fire spell build",
    category=BuildCategory.DOT,
    ascendancy="Elementalist",
    damage_types=[DamageType.FIRE],
    defense_types=[DefenseType.LIFE],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "fire_damage": 2.0,
        "burning_damage": 2.0,
        "fire_damage_over_time_multiplier": 2.0,
        "ignite_chance": 1.5,
        "spell_damage": 1.5,
        "cast_speed": 1.3,
    }),
    required_stats={"fire_damage"},
    popularity=0.03,
    tags=["spell", "fire", "ignite", "dot", "elementalist"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

# --- Minion Builds ---

SUMMON_RAGING_SPIRITS_NECRO = BuildArchetype(
    id="srs_necro",
    name="SRS Necromancer",
    description="Summon Raging Spirits minion build",
    category=BuildCategory.MINION,
    ascendancy="Necromancer",
    damage_types=[DamageType.FIRE, DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "minion_damage": 2.0,
        "minion_life": 1.5,
        "minion_attack_speed": 1.5,
        "cast_speed": 1.3,
        "mana_regeneration": 1.3,
        "intelligence": 1.2,
    }),
    required_stats={"minion_damage"},
    popularity=0.04,
    tags=["minion", "summoner", "srs", "league_starter", "necro"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

SKELETON_MAGES_NECRO = BuildArchetype(
    id="skele_mages",
    name="Skeleton Mages Necromancer",
    description="Ranged skeleton minion army",
    category=BuildCategory.MINION,
    ascendancy="Necromancer",
    damage_types=[DamageType.ELEMENTAL],
    defense_types=[DefenseType.LIFE, DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "minion_damage": 2.0,
        "minion_life": 1.5,
        "minion_spell_damage": 1.8,
        "minion_cast_speed": 1.5,
        "plus_to_maximum_skeletons": 2.0,
        "intelligence": 1.2,
    }),
    required_stats={"minion_damage"},
    popularity=0.03,
    tags=["minion", "summoner", "skeletons", "mages", "necro"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=2,
)

ARAKAALI_FANG_OCCULTIST = BuildArchetype(
    id="arakaali_fang",
    name="Arakaali's Fang Occultist",
    description="Spider summoner with high damage",
    category=BuildCategory.MINION,
    ascendancy="Occultist",
    damage_types=[DamageType.CHAOS, DamageType.PHYSICAL],
    defense_types=[DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_energy_shield": 2.0,
        "minion_damage": 2.0,
        "minion_life": 1.5,
        "chaos_damage": 1.5,
        "energy_shield_recharge": 1.3,
        "chaos_resistance": 1.5,
        "intelligence": 1.2,
    }),
    required_stats={"minion_damage"},
    popularity=0.02,
    tags=["minion", "summoner", "spider", "chaos", "es", "occultist"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

# --- Totem/Trap/Mine Builds ---

EXPLOSIVE_TRAP_SABOTEUR = BuildArchetype(
    id="explosive_trap",
    name="Explosive Trap Saboteur",
    description="Fire trap build with high single target",
    category=BuildCategory.TOTEM_TRAP_MINE,
    ascendancy="Saboteur",
    damage_types=[DamageType.FIRE, DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.EVASION],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "trap_damage": 2.0,
        "fire_damage": 1.8,
        "critical_strike_chance": 1.8,
        "critical_strike_multiplier": 1.8,
        "trap_throwing_speed": 1.5,
        "dexterity": 1.2,
    }),
    required_stats={"trap_damage"},
    popularity=0.03,
    tags=["trap", "fire", "crit", "saboteur", "boss_killer"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=2,
)

SEISMIC_TRAP_SABOTEUR = BuildArchetype(
    id="seismic_trap",
    name="Seismic Trap Saboteur",
    description="Physical trap build with cooldown recovery",
    category=BuildCategory.TOTEM_TRAP_MINE,
    ascendancy="Saboteur",
    damage_types=[DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.EVASION],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "trap_damage": 2.0,
        "physical_damage": 1.8,
        "critical_strike_chance": 1.8,
        "critical_strike_multiplier": 1.8,
        "cooldown_recovery": 1.5,
        "trap_throwing_speed": 1.3,
        "dexterity": 1.2,
    }),
    required_stats={"trap_damage"},
    popularity=0.02,
    tags=["trap", "physical", "crit", "saboteur", "cooldown"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

ANCESTRAL_WARCHIEF_CHIEFTAIN = BuildArchetype(
    id="aw_chieftain",
    name="Ancestral Warchief Chieftain",
    description="Melee totem build with fire conversion",
    category=BuildCategory.TOTEM_TRAP_MINE,
    ascendancy="Chieftain",
    damage_types=[DamageType.FIRE, DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "totem_damage": 2.0,
        "fire_damage": 1.8,
        "physical_damage": 1.5,
        "attack_speed": 1.3,
        "totem_life": 1.3,
        "strength": 1.5,
        "armour": 1.3,
    }),
    required_stats={"totem_damage"},
    popularity=0.02,
    tags=["totem", "melee", "fire", "chieftain", "league_starter"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

# --- Energy Shield Builds ---

COC_ICE_NOVA_OCCULTIST = BuildArchetype(
    id="coc_ice_nova",
    name="CoC Ice Nova Occultist",
    description="Cast on Crit cyclone with Ice Nova",
    category=BuildCategory.SPELL,
    ascendancy="Occultist",
    damage_types=[DamageType.COLD],
    defense_types=[DefenseType.ENERGY_SHIELD],
    key_stats=_create_stat_weights({
        "maximum_energy_shield": 2.0,
        "cold_damage": 2.0,
        "spell_damage": 1.8,
        "critical_strike_chance": 2.0,
        "critical_strike_multiplier": 1.8,
        "attack_speed": 1.5,
        "cooldown_recovery": 2.0,
        "intelligence": 1.3,
    }),
    required_stats={"critical_strike_chance", "cooldown_recovery"},
    popularity=0.03,
    tags=["coc", "cold", "cyclone", "crit", "es", "expensive"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

LOW_LIFE_AURABOT = BuildArchetype(
    id="ll_aurabot",
    name="Low Life Aurabot",
    description="Support build stacking auras",
    category=BuildCategory.AURA_SUPPORT,
    ascendancy="Guardian",
    damage_types=[],
    defense_types=[DefenseType.ENERGY_SHIELD, DefenseType.LOW_LIFE],
    key_stats=_create_stat_weights({
        "maximum_energy_shield": 2.0,
        "aura_effect": 2.5,
        "mana_reservation_efficiency": 2.0,
        "chaos_resistance": 2.0,
        "energy_shield_regeneration": 1.5,
        "intelligence": 1.3,
    }),
    required_stats={"aura_effect", "mana_reservation_efficiency"},
    popularity=0.02,
    tags=["support", "aura", "ll", "es", "party", "guardian"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

# --- Chaos/Poison Builds ---

POISONOUS_CONCOCTION_PF = BuildArchetype(
    id="poison_concoction",
    name="Poisonous Concoction Pathfinder",
    description="Flask-based poison attack build",
    category=BuildCategory.ATTACK,
    ascendancy="Pathfinder",
    damage_types=[DamageType.CHAOS],
    defense_types=[DefenseType.LIFE, DefenseType.EVASION],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "chaos_damage": 2.0,
        "poison_damage": 2.0,
        "attack_speed": 1.5,
        "flask_effect": 1.8,
        "flask_charges_gained": 1.5,
        "evasion_rating": 1.3,
        "dexterity": 1.2,
    }),
    required_stats={"chaos_damage"},
    popularity=0.03,
    tags=["poison", "chaos", "flask", "pathfinder", "league_starter"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

CAUSTIC_ARROW_PF = BuildArchetype(
    id="caustic_arrow",
    name="Caustic Arrow Pathfinder",
    description="Chaos DoT bow build",
    category=BuildCategory.DOT,
    ascendancy="Pathfinder",
    damage_types=[DamageType.CHAOS],
    defense_types=[DefenseType.LIFE, DefenseType.EVASION],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "chaos_damage_over_time_multiplier": 2.0,
        "chaos_damage": 2.0,
        "damage_over_time": 1.8,
        "area_of_effect": 1.3,
        "evasion_rating": 1.3,
        "dexterity": 1.2,
    }),
    required_stats={"chaos_damage_over_time_multiplier"},
    popularity=0.02,
    tags=["bow", "chaos", "dot", "pathfinder", "league_starter"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

# --- Additional Popular Builds ---

DETONATE_DEAD_NECRO = BuildArchetype(
    id="dd_necro",
    name="Detonate Dead Necromancer",
    description="Corpse explosion ignite build",
    category=BuildCategory.SPELL,
    ascendancy="Necromancer",
    damage_types=[DamageType.FIRE],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "fire_damage": 2.0,
        "burning_damage": 1.8,
        "fire_damage_over_time_multiplier": 1.8,
        "cast_speed": 1.3,
        "armour": 1.3,
        "block_chance": 1.5,
    }),
    required_stats={"fire_damage"},
    popularity=0.03,
    tags=["spell", "fire", "ignite", "corpse", "necro", "tanky"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

LACERATE_GLADIATOR = BuildArchetype(
    id="lacerate_glad",
    name="Lacerate Gladiator",
    description="Bleed-based melee build with block",
    category=BuildCategory.ATTACK,
    ascendancy="Gladiator",
    damage_types=[DamageType.PHYSICAL],
    defense_types=[DefenseType.LIFE, DefenseType.BLOCK, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 1.8,
        "physical_damage": 2.0,
        "bleed_damage": 2.0,
        "physical_damage_over_time_multiplier": 1.8,
        "attack_speed": 1.3,
        "block_chance": 1.8,
        "spell_block_chance": 1.5,
        "armour": 1.3,
        "strength": 1.2,
    }),
    required_stats={"physical_damage"},
    popularity=0.02,
    tags=["melee", "bleed", "block", "gladiator", "tanky"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

ESSENCE_DRAIN_TRICKSTER = BuildArchetype(
    id="ed_trickster",
    name="Essence Drain Trickster",
    description="Chaos DoT spell with great clear",
    category=BuildCategory.DOT,
    ascendancy="Trickster",
    damage_types=[DamageType.CHAOS],
    defense_types=[DefenseType.HYBRID, DefenseType.EVASION],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "maximum_energy_shield": 1.5,
        "chaos_damage_over_time_multiplier": 2.0,
        "chaos_damage": 2.0,
        "spell_damage": 1.5,
        "damage_over_time": 1.8,
        "cast_speed": 1.3,
        "evasion_rating": 1.2,
    }),
    required_stats={"chaos_damage_over_time_multiplier"},
    popularity=0.03,
    tags=["spell", "chaos", "dot", "trickster", "league_starter"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=1,
)

ICE_SHOT_DEADEYE = BuildArchetype(
    id="ice_shot_deadeye",
    name="Ice Shot Deadeye",
    description="Cold bow build with freezing and shattering",
    category=BuildCategory.ATTACK,
    ascendancy="Deadeye",
    damage_types=[DamageType.COLD],
    defense_types=[DefenseType.EVASION, DefenseType.LIFE],
    key_stats=_create_stat_weights({
        "maximum_life": 1.5,
        "cold_damage": 2.0,
        "elemental_damage_with_attacks": 1.8,
        "critical_strike_chance": 2.0,
        "critical_strike_multiplier": 2.0,
        "attack_speed": 1.5,
        "added_cold_damage": 1.8,
        "freeze_chance": 1.3,
        "dexterity": 1.2,
    }),
    required_stats={"cold_damage", "critical_strike_chance"},
    popularity=0.03,
    tags=["bow", "cold", "crit", "freeze", "deadeye"],
    league_starter=False,
    ssf_viable=False,
    budget_tier=3,
)

HERALD_OF_AGONY_JUGG = BuildArchetype(
    id="hoag_jugg",
    name="Herald of Agony Juggernaut",
    description="Tanky crawler minion build",
    category=BuildCategory.MINION,
    ascendancy="Juggernaut",
    damage_types=[DamageType.PHYSICAL, DamageType.CHAOS],
    defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
    key_stats=_create_stat_weights({
        "maximum_life": 2.0,
        "minion_damage": 2.0,
        "poison_chance": 1.5,
        "attack_speed": 1.3,
        "armour": 1.8,
        "chaos_resistance": 1.5,
        "strength": 1.3,
    }),
    required_stats={"minion_damage"},
    popularity=0.02,
    tags=["minion", "hoag", "tanky", "jugg", "poison"],
    league_starter=True,
    ssf_viable=True,
    budget_tier=2,
)


# =============================================================================
# ARCHETYPE REGISTRY
# =============================================================================

ALL_ARCHETYPES: List[BuildArchetype] = [
    # Attack
    RF_JUGGERNAUT,
    LIGHTNING_ARROW_DEADEYE,
    BONESHATTER_JUGGERNAUT,
    TORNADO_SHOT_DEADEYE,
    CYCLONE_SLAYER,
    LACERATE_GLADIATOR,
    ICE_SHOT_DEADEYE,
    POISONOUS_CONCOCTION_PF,
    CAUSTIC_ARROW_PF,
    # Spell
    SPARK_INQUISITOR,
    COLD_DOT_OCCULTIST,
    ARC_ELEMENTALIST,
    FIREBALL_IGNITE_ELEMENTALIST,
    COC_ICE_NOVA_OCCULTIST,
    ESSENCE_DRAIN_TRICKSTER,
    DETONATE_DEAD_NECRO,
    # Minion
    SUMMON_RAGING_SPIRITS_NECRO,
    SKELETON_MAGES_NECRO,
    ARAKAALI_FANG_OCCULTIST,
    HERALD_OF_AGONY_JUGG,
    # Totem/Trap/Mine
    EXPLOSIVE_TRAP_SABOTEUR,
    SEISMIC_TRAP_SABOTEUR,
    ANCESTRAL_WARCHIEF_CHIEFTAIN,
    # Support
    LOW_LIFE_AURABOT,
]


class ArchetypeDatabase:
    """
    Database of build archetypes for cross-build analysis.

    Provides lookup and filtering methods for archetypes.
    """

    def __init__(self, archetypes: Optional[List[BuildArchetype]] = None):
        """Initialize with optional custom archetype list."""
        self._archetypes = archetypes or ALL_ARCHETYPES
        self._by_id: Dict[str, BuildArchetype] = {
            arch.id: arch for arch in self._archetypes
        }

    def get_all(self) -> List[BuildArchetype]:
        """Get all archetypes."""
        return list(self._archetypes)

    def get_by_id(self, archetype_id: str) -> Optional[BuildArchetype]:
        """Get archetype by ID."""
        return self._by_id.get(archetype_id)

    def get_by_category(self, category: BuildCategory) -> List[BuildArchetype]:
        """Get archetypes by category."""
        return [a for a in self._archetypes if a.category == category]

    def get_by_damage_type(self, damage_type: DamageType) -> List[BuildArchetype]:
        """Get archetypes that use a specific damage type."""
        return [a for a in self._archetypes if damage_type in a.damage_types]

    def get_by_defense_type(self, defense_type: DefenseType) -> List[BuildArchetype]:
        """Get archetypes that use a specific defense type."""
        return [a for a in self._archetypes if defense_type in a.defense_types]

    def get_league_starters(self) -> List[BuildArchetype]:
        """Get league starter friendly archetypes."""
        return [a for a in self._archetypes if a.league_starter]

    def get_ssf_viable(self) -> List[BuildArchetype]:
        """Get SSF viable archetypes."""
        return [a for a in self._archetypes if a.ssf_viable]

    def get_by_budget(self, max_tier: int) -> List[BuildArchetype]:
        """Get archetypes within budget tier."""
        return [a for a in self._archetypes if a.budget_tier <= max_tier]

    def get_by_tag(self, tag: str) -> List[BuildArchetype]:
        """Get archetypes with a specific tag."""
        tag_lower = tag.lower()
        return [a for a in self._archetypes if tag_lower in a.tags]

    def get_popular(self, min_popularity: float = 0.03) -> List[BuildArchetype]:
        """Get archetypes above a popularity threshold."""
        return [a for a in self._archetypes if a.popularity >= min_popularity]

    def search(self, query: str) -> List[BuildArchetype]:
        """Search archetypes by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for arch in self._archetypes:
            if (query_lower in arch.name.lower() or
                query_lower in arch.description.lower() or
                    any(query_lower in tag for tag in arch.tags)):
                results.append(arch)
        return results


# Global database instance
_database: Optional[ArchetypeDatabase] = None


def get_archetype_database() -> ArchetypeDatabase:
    """Get the global archetype database instance."""
    global _database
    if _database is None:
        _database = ArchetypeDatabase()
    return _database
