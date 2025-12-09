"""
RePoE Tier Data Provider.

Extracts affix tier data from RePoE for use in the ideal rare calculator.
Maps our stat type keys to RePoE stat IDs and provides accurate tier information
directly from game data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

from data_sources.repoe_client import RePoEClient

logger = logging.getLogger(__name__)


# Mapping from our stat type keys to RePoE stat IDs
# Format: stat_type -> (repoe_stat_id, generation_type, is_percentage)
STAT_ID_MAPPING = {
    # Life & Defenses
    "life": ("base_maximum_life", None, False),
    "energy_shield": ("local_energy_shield", None, False),  # Flat local ES
    "energy_shield_percent": ("local_energy_shield_+%", None, True),  # % ES
    "armour": ("local_physical_damage_reduction_rating", None, False),
    "armour_percent": ("local_physical_damage_reduction_rating_+%", None, True),
    "evasion": ("local_evasion_rating", None, False),
    "evasion_percent": ("local_evasion_rating_+%", None, True),

    # Resistances
    "fire_resistance": ("base_fire_damage_resistance_%", "suffix", True),
    "cold_resistance": ("base_cold_damage_resistance_%", "suffix", True),
    "lightning_resistance": ("base_lightning_damage_resistance_%", "suffix", True),
    "chaos_resistance": ("base_chaos_damage_resistance_%", "suffix", True),

    # Attributes
    "strength": ("additional_strength", "suffix", False),
    "dexterity": ("additional_dexterity", "suffix", False),
    "intelligence": ("additional_intelligence", "suffix", False),
    "all_attributes": ("additional_all_attributes", "suffix", False),

    # Movement/Speed
    "movement_speed": ("base_movement_velocity_+%", "prefix", True),  # Boots prefix!
    "attack_speed": ("attack_speed_+%", "suffix", True),  # Gloves suffix
    "cast_speed": ("base_cast_speed_+%", "suffix", True),

    # Critical
    "critical_strike_chance": ("critical_strike_chance_+%", "suffix", True),
    "critical_strike_multiplier": ("base_critical_strike_multiplier_+", "suffix", False),

    # Mana
    "mana": ("base_maximum_mana", None, False),
    "mana_regeneration": ("mana_regeneration_rate_+%", "suffix", True),

    # Damage (various)
    "physical_damage": ("physical_damage_+%", "prefix", True),
    "elemental_damage": ("elemental_damage_+%", "prefix", True),
    "spell_damage": ("spell_damage_+%", "prefix", True),

    # Life Regen
    "life_regeneration": ("base_life_regeneration_rate_per_minute", None, False),

    # Spell Suppression (newer stat)
    "spell_suppression": ("base_chance_to_suppress_spell_damage_%", "suffix", True),

    # Accuracy
    "accuracy": ("accuracy_rating", "suffix", False),
}

# Alternative stat IDs to try if primary doesn't find results
STAT_ID_ALTERNATIVES = {
    "energy_shield": ["base_maximum_energy_shield"],
    "armour": ["base_physical_damage_reduction_rating"],
    "evasion": ["base_evasion_rating"],
    "physical_damage": ["local_physical_damage_+%"],
    "attack_speed": ("local_attack_speed_+%", "attack_speed_+%"),
}

# Tags that indicate special mods to exclude
EXCLUDE_MOD_GROUPS = {
    "essence",
    "delve",
    "incursion",
    "synthesis",
    "influenced",
    "veiled",
    "crafted",
    "conqueror",
}

# Mod ID patterns that indicate special/influenced mods (case insensitive)
EXCLUDE_MOD_ID_PATTERNS = [
    "essence",
    "delve",
    "incursion",
    "synthesis",
    "hunter",
    "redeemer",
    "crusader",
    "warlord",
    "shaper",
    "elder",
    "veiled",
    "crafted",
    "fractured",
    "uber",      # Elder/Shaper influenced (UberX naming)
    "maven",     # Maven influenced
    "influence", # Generic influence suffix
    "eyrie",     # Hunter influence
    "basilisk",  # Hunter influence
    "adjudicator", # Warlord influence
]

# Mod name patterns to exclude (influenced mods)
EXCLUDE_MOD_NAMES = [
    "Shaping",
    "Redemption",
    "Conquest",
    "Hunt",
    "Crusade",
    "Warlord",
    "Eldritch",
    "The Shaper",     # Shaper prefixes
    "Hunter's",       # Hunter prefixes
    "of the Essence", # Essence mods
    "Essences",       # Essence mods
    "Elevated",       # Elevated mods
    "of the Elder",   # Elder suffixes
]


@dataclass
class RePoETier:
    """Represents a single tier from RePoE data."""
    stat_type: str
    tier_number: int
    mod_name: str
    mod_id: str
    ilvl_required: int
    min_value: int
    max_value: int
    generation_type: str  # prefix or suffix

    @property
    def display_range(self) -> str:
        if self.min_value == self.max_value:
            return str(self.min_value)
        return f"{self.min_value}-{self.max_value}"


class RePoETierProvider:
    """
    Provides affix tier data from RePoE.

    Extracts and organizes tier data for use in the ideal rare calculator.
    Filters out special mods (essence, delve, etc.) to show only standard craftable tiers.
    """

    def __init__(self, repoe_client: Optional[RePoEClient] = None):
        """
        Initialize the tier provider.

        Args:
            repoe_client: Optional RePoE client instance. Creates one if not provided.
        """
        self._client = repoe_client or RePoEClient()
        self._tier_cache: Dict[str, List[RePoETier]] = {}
        self._mods_data: Optional[Dict] = None

    def _get_mods(self) -> Dict:
        """Load mods data with caching."""
        if self._mods_data is None:
            self._mods_data = self._client.get_mods() or {}
        return self._mods_data

    def _is_standard_mod(self, mod_info: dict, mod_id: str = "") -> bool:
        """Check if a mod is a standard craftable mod (not essence/delve/etc)."""
        # Must be item domain
        if mod_info.get('domain') != 'item':
            return False

        # Must be prefix or suffix
        gen_type = mod_info.get('generation_type', '')
        if gen_type not in ('prefix', 'suffix'):
            return False

        # Check for essence-only flag
        if mod_info.get('is_essence_only', False):
            return False

        # Check mod groups for special types
        groups = mod_info.get('groups', [])
        for group in groups:
            group_lower = group.lower()
            for exclude in EXCLUDE_MOD_GROUPS:
                if exclude in group_lower:
                    return False

        # Check mod ID for special patterns
        mod_id_lower = mod_id.lower()
        for pattern in EXCLUDE_MOD_ID_PATTERNS:
            if pattern in mod_id_lower:
                return False

        # Check mod name for influenced patterns
        mod_name = mod_info.get('name', '')
        for pattern in EXCLUDE_MOD_NAMES:
            if pattern in mod_name:
                return False

        return True

    def _has_positive_spawn_weight(self, mod_info: dict, exclude_weapon_only: bool = True) -> bool:
        """Check if mod has any positive spawn weight on non-weapon items."""
        # Tags that indicate weapon-only mods
        weapon_tags = {'weapon', 'bow', 'wand', 'sceptre', 'staff', 'sword', 'axe', 'mace', 'claw', 'dagger'}
        # Tags that indicate armor/jewelry
        armor_jewelry_tags = {
            'helmet', 'body_armour', 'gloves', 'boots', 'belt', 'ring', 'amulet', 'shield',
            'quiver', 'armour', 'default', 'int_armour', 'str_armour', 'dex_armour',
            'str_int_armour', 'str_dex_armour', 'dex_int_armour',
        }

        has_weapon_weight = False
        has_armor_weight = False

        for weight in mod_info.get('spawn_weights', []):
            if weight.get('weight', 0) > 0:
                tag = weight.get('tag', '')
                if tag in weapon_tags:
                    has_weapon_weight = True
                elif tag in armor_jewelry_tags or 'shield' in tag:
                    has_armor_weight = True

        if exclude_weapon_only:
            # If it only spawns on weapons, exclude it
            if has_weapon_weight and not has_armor_weight:
                return False

        return has_weapon_weight or has_armor_weight

    def get_tiers_for_stat(
        self,
        stat_type: str,
        force_refresh: bool = False
    ) -> List[RePoETier]:
        """
        Get all tiers for a stat type from RePoE.

        Args:
            stat_type: Our stat type key (e.g., "life", "fire_resistance")
            force_refresh: Force reload from RePoE data

        Returns:
            List of RePoETier objects sorted by tier (T1 first)
        """
        # Check cache
        if not force_refresh and stat_type in self._tier_cache:
            return self._tier_cache[stat_type]

        mapping = STAT_ID_MAPPING.get(stat_type)
        if not mapping:
            logger.warning(f"No RePoE mapping for stat type: {stat_type}")
            return []

        repoe_stat_id, expected_gen_type, _ = mapping

        mods = self._get_mods()
        matching_mods = []

        for mod_id, mod_info in mods.items():
            # Filter standard mods only
            if not self._is_standard_mod(mod_info, mod_id):
                continue

            # Filter by generation type if specified
            gen_type = mod_info.get('generation_type', '')
            if expected_gen_type and gen_type != expected_gen_type:
                continue

            # Must have spawn weight
            if not self._has_positive_spawn_weight(mod_info):
                continue

            # Check stats for matching stat ID
            for stat in mod_info.get('stats', []):
                stat_id = stat.get('id', '')
                if repoe_stat_id.lower() in stat_id.lower():
                    # Skip hybrid mods (multiple stats) - we only want pure mods
                    # Exception: Allow 2-stat mods if both are related
                    num_stats = len(mod_info.get('stats', []))
                    if num_stats > 1:
                        # Skip this mod - it's a hybrid
                        continue
                    matching_mods.append({
                        'mod_id': mod_id,
                        'mod_info': mod_info,
                        'stat': stat,
                    })
                    break

        # Try alternatives if no results
        if not matching_mods and stat_type in STAT_ID_ALTERNATIVES:
            alternatives = STAT_ID_ALTERNATIVES[stat_type]
            if isinstance(alternatives, str):
                alternatives = [alternatives]

            for alt_stat_id in alternatives:
                for mod_id, mod_info in mods.items():
                    if not self._is_standard_mod(mod_info, mod_id):
                        continue
                    if expected_gen_type and mod_info.get('generation_type') != expected_gen_type:
                        continue
                    if not self._has_positive_spawn_weight(mod_info):
                        continue

                    for stat in mod_info.get('stats', []):
                        stat_id = stat.get('id', '')
                        if alt_stat_id.lower() in stat_id.lower():
                            # Skip hybrid mods
                            if len(mod_info.get('stats', [])) > 1:
                                continue
                            matching_mods.append({
                                'mod_id': mod_id,
                                'mod_info': mod_info,
                                'stat': stat,
                            })
                            break

                if matching_mods:
                    break

        # Sort by required level (higher = better tier)
        matching_mods.sort(key=lambda x: x['mod_info'].get('required_level', 0), reverse=True)

        # Convert to RePoETier objects with tier numbers
        tiers = []
        seen_ilvls: Set[int] = set()
        tier_num = 1

        for match in matching_mods:
            mod_info = match['mod_info']
            stat = match['stat']
            ilvl = mod_info.get('required_level', 0)

            # Skip duplicate ilvl entries (same tier)
            if ilvl in seen_ilvls:
                continue
            seen_ilvls.add(ilvl)

            tier = RePoETier(
                stat_type=stat_type,
                tier_number=tier_num,
                mod_name=mod_info.get('name', '') or match['mod_id'],
                mod_id=match['mod_id'],
                ilvl_required=ilvl,
                min_value=stat.get('min', 0),
                max_value=stat.get('max', 0),
                generation_type=mod_info.get('generation_type', ''),
            )
            tiers.append(tier)
            tier_num += 1

        # Cache result
        self._tier_cache[stat_type] = tiers
        return tiers

    def get_best_tier_for_ilvl(
        self,
        stat_type: str,
        ilvl: int
    ) -> Optional[RePoETier]:
        """
        Get the best tier achievable at a given item level.

        Args:
            stat_type: Our stat type key
            ilvl: Target item level

        Returns:
            Best achievable RePoETier or None
        """
        tiers = self.get_tiers_for_stat(stat_type)

        for tier in tiers:
            if ilvl >= tier.ilvl_required:
                return tier

        # Return lowest tier if none match
        return tiers[-1] if tiers else None

    def get_tier_data_tuple(
        self,
        stat_type: str
    ) -> List[Tuple[int, int, int, int]]:
        """
        Get tier data in the format used by AffixTierCalculator.

        Returns:
            List of (tier, ilvl_required, min_value, max_value) tuples
        """
        tiers = self.get_tiers_for_stat(stat_type)
        return [
            (t.tier_number, t.ilvl_required, t.min_value, t.max_value)
            for t in tiers
        ]

    def get_all_available_stats(self) -> List[str]:
        """Get list of all stat types we have mappings for."""
        return list(STAT_ID_MAPPING.keys())

    def build_complete_tier_data(self) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """
        Build complete tier data dictionary for all stats.

        Returns:
            Dictionary in the same format as AFFIX_TIER_DATA
        """
        result = {}
        for stat_type in STAT_ID_MAPPING:
            tiers = self.get_tier_data_tuple(stat_type)
            if tiers:
                result[stat_type] = tiers
        return result

    def clear_cache(self):
        """Clear the tier cache."""
        self._tier_cache.clear()
        self._mods_data = None


# Item class to slot mapping
ITEM_CLASS_TO_SLOT = {
    "Helmet": "Helmet",
    "Body Armour": "Body Armour",
    "Gloves": "Gloves",
    "Boots": "Boots",
    "Belt": "Belt",
    "Ring": "Ring",
    "Amulet": "Amulet",
    "Shield": "Shield",
    "Quiver": "Shield",  # Treat quiver like shield for slot purposes
}


@dataclass
class BaseItemRecommendation:
    """A recommended base item with metadata."""
    name: str
    item_class: str
    drop_level: int
    tags: List[str]
    requirements: Dict[str, int]
    defense_type: str  # "armour", "evasion", "energy_shield", "hybrid"


class BaseItemRecommender:
    """Recommends base items based on build requirements."""

    def __init__(self, repoe_client: Optional["RePoEClient"] = None):
        self._client = repoe_client
        if self._client is None:
            from data_sources.repoe_client import RePoEClient
            self._client = RePoEClient()
        self._base_items: Optional[Dict] = None

    def _get_base_items(self) -> Dict:
        """Load base items with caching."""
        if self._base_items is None:
            if self._client is not None:
                self._base_items = self._client.get_base_items() or {}
            else:
                self._base_items = {}
        return self._base_items

    def _get_defense_type(self, tags: List[str]) -> str:
        """Determine defense type from item tags."""
        has_str = any("str" in t.lower() for t in tags)
        has_dex = any("dex" in t.lower() for t in tags)
        has_int = any("int" in t.lower() for t in tags)

        # Count attribute types
        count = sum([has_str, has_dex, has_int])

        if count >= 2:
            return "hybrid"
        elif has_str:
            return "armour"
        elif has_dex:
            return "evasion"
        elif has_int:
            return "energy_shield"
        return "unknown"

    def get_best_bases_for_slot(
        self,
        slot: str,
        defense_type: Optional[str] = None,
        min_drop_level: int = 60,
    ) -> List[BaseItemRecommendation]:
        """
        Get best base items for a slot.

        Args:
            slot: Equipment slot (e.g., "Helmet", "Body Armour")
            defense_type: Optional filter for "armour", "evasion", "energy_shield", "hybrid"
            min_drop_level: Minimum drop level for bases

        Returns:
            List of BaseItemRecommendation sorted by drop level (highest first)
        """
        base_items = self._get_base_items()
        results = []

        # Determine item classes for the slot
        target_classes = []
        if slot == "Helmet":
            target_classes = ["Helmet"]
        elif slot == "Body Armour":
            target_classes = ["Body Armour"]
        elif slot == "Gloves":
            target_classes = ["Gloves"]
        elif slot == "Boots":
            target_classes = ["Boots"]
        elif slot == "Belt":
            target_classes = ["Belt"]
        elif slot == "Ring":
            target_classes = ["Ring"]
        elif slot == "Amulet":
            target_classes = ["Amulet"]
        elif slot == "Shield":
            target_classes = ["Shield"]

        for item_id, item_info in base_items.items():
            item_class = item_info.get("item_class", "")
            if item_class not in target_classes:
                continue

            drop_level = item_info.get("drop_level", 0)
            if drop_level < min_drop_level:
                continue

            tags = item_info.get("tags", [])
            item_defense = self._get_defense_type(tags)

            # Filter by defense type if specified
            if defense_type and item_defense != defense_type:
                continue

            requirements = item_info.get("requirements", {})

            results.append(BaseItemRecommendation(
                name=item_info.get("name", ""),
                item_class=item_class,
                drop_level=drop_level,
                tags=tags,
                requirements=requirements,
                defense_type=item_defense,
            ))

        # Sort by drop level (higher = better base)
        results.sort(key=lambda x: x.drop_level, reverse=True)
        return results

    def get_recommended_base(
        self,
        slot: str,
        is_es_build: bool = False,
        is_evasion_build: bool = False,
        is_armour_build: bool = False,
    ) -> Optional[BaseItemRecommendation]:
        """
        Get the single best recommended base for a slot.

        Args:
            slot: Equipment slot
            is_es_build: True if building for energy shield
            is_evasion_build: True if building for evasion
            is_armour_build: True if building for armour

        Returns:
            Best base item recommendation or None
        """
        # Determine preferred defense type
        defense_type = None
        if is_es_build:
            defense_type = "energy_shield"
        elif is_evasion_build:
            defense_type = "evasion"
        elif is_armour_build:
            defense_type = "armour"

        bases = self.get_best_bases_for_slot(slot, defense_type=defense_type)
        return bases[0] if bases else None


# Singleton instance for easy access
_provider_instance: Optional[RePoETierProvider] = None
_recommender_instance: Optional[BaseItemRecommender] = None


def get_repoe_tier_provider() -> RePoETierProvider:
    """Get the singleton RePoE tier provider instance."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = RePoETierProvider()
    return _provider_instance


def get_base_item_recommender() -> BaseItemRecommender:
    """Get the singleton base item recommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = BaseItemRecommender()
    return _recommender_instance


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("REPOE TIER PROVIDER TEST")
    print("=" * 60)

    provider = RePoETierProvider()

    # Test life tiers
    print("\n=== Life Tiers ===")
    life_tiers = provider.get_tiers_for_stat("life")
    for tier in life_tiers[:7]:
        print(f"  T{tier.tier_number} ({tier.mod_name}): {tier.display_range} (ilvl {tier.ilvl_required})")

    # Test fire resistance
    print("\n=== Fire Resistance Tiers ===")
    fire_tiers = provider.get_tiers_for_stat("fire_resistance")
    for tier in fire_tiers[:7]:
        print(f"  T{tier.tier_number} ({tier.mod_name}): {tier.display_range}% (ilvl {tier.ilvl_required})")

    # Test movement speed
    print("\n=== Movement Speed Tiers ===")
    ms_tiers = provider.get_tiers_for_stat("movement_speed")
    for tier in ms_tiers[:7]:
        print(f"  T{tier.tier_number} ({tier.mod_name}): {tier.display_range}% (ilvl {tier.ilvl_required})")

    # Test critical strike
    print("\n=== Critical Strike Chance Tiers ===")
    crit_tiers = provider.get_tiers_for_stat("critical_strike_chance")
    for tier in crit_tiers[:5]:
        print(f"  T{tier.tier_number} ({tier.mod_name}): {tier.display_range}% (ilvl {tier.ilvl_required})")

    # Test best tier at ilvl
    print("\n=== Best Life Tier at ilvl 75 ===")
    best = provider.get_best_tier_for_ilvl("life", 75)
    if best:
        print(f"  T{best.tier_number}: {best.display_range} life ({best.mod_name})")

    # Build complete data
    print("\n=== Building Complete Tier Data ===")
    complete = provider.build_complete_tier_data()
    print(f"  Stats with tier data: {len(complete)}")
    for stat, tiers in list(complete.items())[:5]:
        print(f"    {stat}: {len(tiers)} tiers")
