"""
Rare Item Evaluator - Assess value of rare items based on affixes and bases.

This module evaluates rare items by:
1. Checking if the base type is valuable
2. Checking item level (ilvl 84+ for top tier mods)
3. Evaluating explicit mods against "evergreen" valuable affixes
4. Scoring items based on affix combinations
5. Comparing against popular build requirements (optional)
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from core.item_parser import ParsedItem
from core.build_archetype import (
    BuildArchetype, get_weight_multiplier
)


@dataclass
class AffixMatch:
    """Represents a matched valuable affix on an item."""
    affix_type: str  # e.g., "life", "resistances"
    pattern: str     # Pattern that matched
    mod_text: str    # Actual mod text from item
    value: Optional[float]  # Extracted numeric value
    weight: int      # Importance weight (1-10)
    tier: str        # "tier1", "tier2", "tier3"
    is_influence_mod: bool = False  # True if from influence


@dataclass
class RareItemEvaluation:
    """Results of rare item evaluation."""
    item: ParsedItem
    base_score: int  # 0-100 based on base type and ilvl
    affix_score: int  # 0-100 based on valuable affixes
    synergy_bonus: int  # Bonus from mod combinations
    red_flag_penalty: int  # Penalty from anti-synergies
    total_score: int  # Combined score

    is_valuable_base: bool
    has_high_ilvl: bool
    matched_affixes: List[AffixMatch]

    # Categorization
    tier: str  # "excellent", "good", "average", "vendor"
    estimated_value: str  # "10c+", "50c+", "1div+", etc.

    # Fields with defaults must come last
    synergies_found: List[str] = None  # Names of synergies detected
    red_flags_found: List[str] = None  # Names of red flags detected

    # Slot-specific bonuses (Phase 1.3)
    slot_bonus: int = 0  # Bonus from slot-specific rules
    slot_bonus_reasons: List[str] = None  # Reasons for slot bonuses

    # Crafting potential (Phase 1.3)
    open_prefixes: int = 0  # Estimated open prefix slots
    open_suffixes: int = 0  # Estimated open suffix slots
    crafting_bonus: int = 0  # Bonus for crafting potential

    # Fractured items (Phase 1.3)
    is_fractured: bool = False
    fractured_bonus: int = 0  # Bonus for fractured T1 mods
    fractured_mod: str = None  # The fractured mod if detected

    # Build archetype matching (Phase 2)
    matched_archetypes: List[str] = None  # Which build archetypes this item fits
    archetype_bonus: int = 0  # Bonus for fitting meta archetypes
    meta_bonus: int = 0  # Bonus from current meta popularity

    # Build matching (if provided)
    matches_build: bool = False
    build_name: Optional[str] = None
    matching_requirements: List[str] = None

    # Build archetype context (Phase 2 - PoB integration)
    build_archetype: Optional[BuildArchetype] = None
    archetype_weighted_score: int = 0  # Score adjusted by archetype weights
    archetype_affix_details: List[Dict[str, Any]] = None  # Per-affix weight details

    def __post_init__(self):
        if self.synergies_found is None:
            self.synergies_found = []
        if self.red_flags_found is None:
            self.red_flags_found = []
        if self.slot_bonus_reasons is None:
            self.slot_bonus_reasons = []
        if self.matched_archetypes is None:
            self.matched_archetypes = []
        if self.archetype_affix_details is None:
            self.archetype_affix_details = []


class RareItemEvaluator:
    """
    Evaluates rare items for potential value.

    Uses:
    - Valuable base types
    - Item level requirements
    - Evergreen valuable affixes
    - Optional build requirements
    """

    def __init__(self, data_dir: Path = None):
        """
        Initialize evaluator with data files.

        Args:
            data_dir: Directory containing valuable_affixes.json and valuable_bases.json
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"

        self.data_dir = data_dir
        self.config = self._load_valuable_affixes()
        self.valuable_affixes = {
            k: v for k, v in self.config.items() if not k.startswith("_")}
        self.synergies = self.config.get("_synergies", {})
        self.red_flags = self.config.get("_red_flags", {})
        self.influence_mods = self.config.get("_influence_mods", {})
        self.valuable_bases = self._load_valuable_bases()
        self.slot_rules = self.valuable_bases.get("_slot_rules", {})

        # Phase 2: Build archetypes and meta integration
        self.build_archetypes = self._load_build_archetypes()
        self.meta_weights = self._load_meta_weights()

    def _load_valuable_affixes(self) -> Dict:
        """Load valuable affixes configuration."""
        affix_file = self.data_dir / "valuable_affixes.json"
        if affix_file.exists():
            with open(affix_file) as f:
                return json.load(f)
        return {}

    def _load_valuable_bases(self) -> Dict:
        """Load valuable base types configuration."""
        base_file = self.data_dir / "valuable_bases.json"
        if base_file.exists():
            with open(base_file) as f:
                return json.load(f)
        return {}

    def _load_build_archetypes(self) -> Dict:
        """Load build archetype definitions."""
        archetype_file = self.data_dir / "build_archetypes.json"
        if archetype_file.exists():
            with open(archetype_file) as f:
                data = json.load(f)
                return data.get("archetypes", {})
        return {}

    def _load_meta_weights(self) -> Dict:
        """Load meta-based weight adjustments."""
        # First try meta_affixes.json (from MetaAnalyzer)
        meta_file = self.data_dir / "meta_affixes.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                    return data.get("affixes", {})
            except Exception:
                pass

        # Fallback to build_archetypes.json meta section
        archetype_file = self.data_dir / "build_archetypes.json"
        if archetype_file.exists():
            try:
                with open(archetype_file) as f:
                    data = json.load(f)
                    return data.get("_meta_weights", {}).get("popularity_boosts", {})
            except Exception:
                pass

        return {}

    def evaluate(self, item: ParsedItem) -> RareItemEvaluation:
        """
        Evaluate a rare item for potential value.

        Args:
            item: Parsed item to evaluate

        Returns:
            RareItemEvaluation with scores and matched affixes
        """
        # Only evaluate rares
        if not item.rarity or item.rarity.upper() != "RARE":
            return RareItemEvaluation(
                item=item,
                base_score=0,
                affix_score=0,
                synergy_bonus=0,
                red_flag_penalty=0,
                total_score=0,
                is_valuable_base=False,
                has_high_ilvl=False,
                matched_affixes=[],
                tier="not_rare",
                estimated_value="N/A"
            )

        # Evaluate base
        is_valuable_base, base_score = self._evaluate_base(item)
        has_high_ilvl = self._check_ilvl(item)

        # Evaluate affixes (including influence mods)
        matched_affixes = self._match_affixes(item)
        affix_score = self._calculate_affix_score(matched_affixes)

        # Check for synergies
        synergies_found, synergy_bonus = self._check_synergies(matched_affixes)

        # Check for red flags
        red_flags_found, red_flag_penalty = self._check_red_flags(
            item, matched_affixes)

        # Phase 1.3: Slot-specific rules
        slot_bonus, slot_bonus_reasons = self._check_slot_rules(
            item, matched_affixes)

        # Phase 1.3: Open affix detection (crafting potential)
        open_prefixes, open_suffixes, crafting_bonus = self._detect_open_affixes(
            item, matched_affixes)

        # Phase 1.3: Fractured item handling
        is_fractured, fractured_bonus, fractured_mod = self._check_fractured(
            item, matched_affixes)

        # Phase 2: Build archetype matching
        matched_archetypes, archetype_bonus = self._match_archetypes(
            matched_affixes)

        # Phase 2: Meta popularity bonus
        meta_bonus = self._calculate_meta_bonus(matched_affixes)

        # Calculate total score (now includes Phase 2 bonuses)
        total_score = self._calculate_total_score(
            base_score, affix_score, has_high_ilvl, synergy_bonus, red_flag_penalty,
            slot_bonus, crafting_bonus, fractured_bonus, archetype_bonus, meta_bonus)

        # Determine tier and estimated value
        tier, estimated_value = self._determine_tier(
            total_score, matched_affixes, synergies_found,
            is_fractured, crafting_bonus, matched_archetypes)

        return RareItemEvaluation(
            item=item,
            base_score=base_score,
            affix_score=affix_score,
            synergy_bonus=synergy_bonus,
            red_flag_penalty=red_flag_penalty,
            total_score=total_score,
            is_valuable_base=is_valuable_base,
            has_high_ilvl=has_high_ilvl,
            matched_affixes=matched_affixes,
            synergies_found=synergies_found,
            red_flags_found=red_flags_found,
            slot_bonus=slot_bonus,
            slot_bonus_reasons=slot_bonus_reasons,
            open_prefixes=open_prefixes,
            open_suffixes=open_suffixes,
            crafting_bonus=crafting_bonus,
            is_fractured=is_fractured,
            fractured_bonus=fractured_bonus,
            fractured_mod=fractured_mod,
            matched_archetypes=matched_archetypes,
            archetype_bonus=archetype_bonus,
            meta_bonus=meta_bonus,
            tier=tier,
            estimated_value=estimated_value
        )

    def evaluate_with_archetype(
        self,
        item: ParsedItem,
        archetype: BuildArchetype
    ) -> RareItemEvaluation:
        """
        Evaluate a rare item with build archetype context.

        This applies archetype-based weight multipliers to affix scores,
        making the evaluation build-aware.

        Args:
            item: Parsed item to evaluate
            archetype: Build archetype for weight adjustments

        Returns:
            RareItemEvaluation with archetype-weighted scores
        """
        # First do standard evaluation
        evaluation = self.evaluate(item)

        if evaluation.tier == "not_rare":
            return evaluation

        # Apply archetype weights to matched affixes
        weighted_total = 0.0
        affix_details = []

        for match in evaluation.matched_affixes:
            base_weight = match.weight
            multiplier = get_weight_multiplier(archetype, match.affix_type)
            weighted_weight = base_weight * multiplier

            affix_details.append({
                "affix_type": match.affix_type,
                "mod_text": match.mod_text,
                "base_weight": base_weight,
                "multiplier": round(multiplier, 2),
                "weighted_weight": round(weighted_weight, 2),
                "tier": match.tier,
            })

            weighted_total += weighted_weight

        # Calculate archetype-weighted score (similar to _calculate_affix_score logic)
        num_matches = len(evaluation.matched_affixes)
        if num_matches >= 3 and weighted_total >= 25:
            archetype_affix_score = min(100, int(60 + weighted_total))
        elif num_matches >= 2 and weighted_total >= 16:
            archetype_affix_score = min(100, int(40 + weighted_total * 2))
        elif num_matches >= 1:
            archetype_affix_score = min(100, int(20 + weighted_total * 3))
        else:
            archetype_affix_score = 0

        # Recalculate total with archetype-weighted affix score
        archetype_total = self._calculate_total_score(
            evaluation.base_score,
            archetype_affix_score,
            evaluation.has_high_ilvl,
            evaluation.synergy_bonus,
            evaluation.red_flag_penalty,
            evaluation.slot_bonus,
            evaluation.crafting_bonus,
            evaluation.fractured_bonus,
            evaluation.archetype_bonus,
            evaluation.meta_bonus
        )

        # Update evaluation with archetype info
        evaluation.build_archetype = archetype
        evaluation.archetype_weighted_score = archetype_total
        evaluation.archetype_affix_details = affix_details

        return evaluation

    def _evaluate_base(self, item: ParsedItem) -> Tuple[bool, int]:
        """
        Check if item is on a valuable base type.

        Returns:
            (is_valuable, score_0_to_50)
        """
        if not item.base_type:
            return False, 0

        base_type = item.base_type.strip()

        # Check each category
        for category, data in self.valuable_bases.items():
            if category.startswith("_"):
                continue

            high_tier = data.get("high_tier", [])
            if base_type in high_tier:
                return True, 50

        return False, 10  # Not a top-tier base, but still give some points

    def _check_ilvl(self, item: ParsedItem) -> bool:
        """Check if item level is high enough for top-tier mods."""
        return item.item_level and item.item_level >= 84

    def _match_affixes(self, item: ParsedItem) -> List[AffixMatch]:
        """
        Match item's explicit mods against valuable affixes (all tiers).

        Returns:
            List of AffixMatch objects
        """
        matches = []

        # First check influence mods if item has influences
        if item.influences:
            influence_matches = self._match_influence_mods(item)
            matches.extend(influence_matches)

        # Then check regular affixes
        for mod_text in item.explicits:
            for affix_type, affix_data in self.valuable_affixes.items():
                if affix_type.startswith("_"):
                    continue

                # Try each tier (T1, T2, T3)
                for tier_name in ["tier1", "tier2", "tier3"]:
                    tier_patterns = affix_data.get(tier_name, [])
                    if not tier_patterns:
                        continue

                    weight = affix_data.get(
                        f"{tier_name}_weight", affix_data.get(
                            "weight", 5))
                    min_value = affix_data.get("min_value", 0)

                    for pattern in tier_patterns:
                        # Convert pattern to regex
                        regex_pattern = pattern.replace("#", "__NUMBER__")
                        regex_pattern = re.escape(regex_pattern)
                        regex_pattern = regex_pattern.replace(
                            "__NUMBER__", r"(\d+(?:\.\d+)?)")

                        match = re.search(
                            regex_pattern, mod_text, re.IGNORECASE)
                        if match:
                            # Extract value
                            value = None
                            if match.groups():
                                try:
                                    value = float(match.group(1))
                                except (ValueError, IndexError):
                                    value = None

                            # Determine actual tier based on value ranges
                            actual_tier = self._determine_tier_from_value(
                                affix_type, affix_data, value
                            )

                            # Get weight for actual tier
                            tier_weight = affix_data.get(
                                f"{actual_tier}_weight", weight)

                            # Check minimum value requirement
                            if value and value >= min_value:
                                matches.append(AffixMatch(
                                    affix_type=affix_type,
                                    pattern=pattern,
                                    mod_text=mod_text,
                                    value=value,
                                    weight=tier_weight,
                                    tier=actual_tier,
                                    is_influence_mod=False
                                ))
                                break  # Only match once per mod

                    if matches and matches[-1].mod_text == mod_text:
                        break  # Already matched this mod, don't check lower tiers

        return matches

    def _determine_tier_from_value(
        self, affix_type: str, affix_data: Dict, value: Optional[float]
    ) -> str:
        """
        Determine the actual tier based on the rolled value.

        Returns:
            "tier1", "tier2", or "tier3"
        """
        if value is None:
            return "tier3"

        # Check tier ranges
        for tier in ["tier1", "tier2", "tier3"]:
            tier_range = affix_data.get(f"{tier}_range")
            if tier_range and len(tier_range) == 2:
                min_val, max_val = tier_range
                if min_val <= value <= max_val:
                    return tier

        # Default to tier based on thresholds
        tier1_range = affix_data.get("tier1_range")
        if tier1_range and value >= tier1_range[0]:
            return "tier1"

        tier2_range = affix_data.get("tier2_range")
        if tier2_range and value >= tier2_range[0]:
            return "tier2"

        return "tier3"

    def _match_influence_mods(self, item: ParsedItem) -> List[AffixMatch]:
        """
        Match influence-specific high-value mods.

        Returns:
            List of AffixMatch objects for influence mods
        """
        matches = []

        for influence in item.influences:
            influence_lower = influence.lower()
            influence_data = self.influence_mods.get(influence_lower, {})
            high_value_mods = influence_data.get("high_value", [])
            weight = influence_data.get("weight", 10)

            for mod_text in item.explicits:
                for pattern in high_value_mods:
                    # Convert pattern to regex
                    regex_pattern = pattern.replace("#", "__NUMBER__")
                    regex_pattern = re.escape(regex_pattern)
                    regex_pattern = regex_pattern.replace(
                        "__NUMBER__", r"(\d+(?:\.\d+)?)")

                    if re.search(regex_pattern, mod_text, re.IGNORECASE):
                        matches.append(AffixMatch(
                            affix_type=f"{influence_lower}_mod",
                            pattern=pattern,
                            mod_text=mod_text,
                            value=None,
                            weight=weight,
                            tier="influence",
                            is_influence_mod=True
                        ))
                        break

        return matches

    def _calculate_affix_score(self, matches: List[AffixMatch]) -> int:
        """
        Calculate score based on matched affixes.

        Returns:
            Score from 0-100
        """
        if not matches:
            return 0

        # Sum weighted scores
        total_weight = sum(m.weight for m in matches)

        # Normalize to 0-100
        # Consider 3+ high-weight affixes as "excellent" (90+)
        # 2 high-weight affixes as "good" (70+)
        # 1 high-weight affix as "decent" (50+)

        if len(matches) >= 3 and total_weight >= 25:
            return min(100, 60 + total_weight)
        elif len(matches) >= 2 and total_weight >= 16:
            return min(100, 40 + total_weight * 2)
        elif len(matches) >= 1:
            return min(100, 20 + total_weight * 3)

        return 0

    def _check_synergies(
            self, matches: List[AffixMatch]) -> Tuple[List[str], int]:
        """
        Check for synergistic mod combinations.

        Returns:
            (list_of_synergy_names, total_bonus_score)
        """
        found_synergies = []
        total_bonus = 0

        # Count affixes by type
        affix_counts = {}
        for match in matches:
            affix_counts[match.affix_type] = affix_counts.get(
                match.affix_type, 0) + 1

        # Check each synergy
        for synergy_name, synergy_data in self.synergies.items():
            required = synergy_data.get("required", {})

            # Check if all requirements are met
            meets_requirements = True
            for req_affix, req_count in required.items():
                actual_count = affix_counts.get(req_affix, 0)
                if actual_count < req_count:
                    meets_requirements = False
                    break

            if meets_requirements:
                found_synergies.append(synergy_name)
                total_bonus += synergy_data.get("bonus_score", 0)

        return found_synergies, total_bonus

    def _check_red_flags(self, item: ParsedItem,
                         matches: List[AffixMatch]) -> Tuple[List[str], int]:
        """
        Check for anti-synergies and red flags.

        Returns:
            (list_of_red_flag_names, total_penalty_score)
        """
        found_flags = []
        total_penalty = 0

        # Get affix types present
        affix_types = set(match.affix_type for match in matches)

        # Determine item slot
        item_slot = self._determine_item_slot(item)

        # Check each red flag
        for flag_name, flag_data in self.red_flags.items():
            check_type = flag_data.get("check")

            if check_type == "has_both":
                required_affixes = flag_data.get("affixes", [])
                if all(affix in affix_types for affix in required_affixes):
                    found_flags.append(flag_name)
                    total_penalty += flag_data.get("penalty_score", 0)

            elif check_type == "missing_required":
                required_slot = flag_data.get("slot")
                required_affix = flag_data.get("required_affix")

                if item_slot == required_slot and required_affix not in affix_types:
                    found_flags.append(flag_name)
                    total_penalty += flag_data.get("penalty_score", 0)

        return found_flags, total_penalty

    def _determine_item_slot(self, item: ParsedItem) -> Optional[str]:
        """
        Determine what slot the item goes in based on base type.

        Returns:
            "boots", "helmet", "gloves", "body_armour", "belt", "ring", "amulet", or None
        """
        if not item.base_type:
            return None

        base_lower = item.base_type.lower()

        # Check common patterns
        if "boots" in base_lower or "greaves" in base_lower:
            return "boots"
        elif "helmet" in base_lower or "circlet" in base_lower or "crown" in base_lower or "helm" in base_lower:
            return "helmet"
        elif "gloves" in base_lower or "gauntlets" in base_lower or "mitts" in base_lower:
            return "gloves"
        elif "plate" in base_lower or "vest" in base_lower or "garb" in base_lower or "regalia" in base_lower or "coat" in base_lower:
            return "body_armour"
        elif "belt" in base_lower or "vise" in base_lower or "sash" in base_lower:
            return "belt"
        elif "ring" in base_lower:
            return "ring"
        elif "amulet" in base_lower or "talisman" in base_lower:
            return "amulet"

        return None

    def _check_slot_rules(
        self, item: ParsedItem, matches: List[AffixMatch]
    ) -> Tuple[int, List[str]]:
        """
        Apply slot-specific evaluation rules.

        Returns:
            (bonus_score, list_of_reasons)
        """
        bonus = 0
        reasons = []

        item_slot = self._determine_item_slot(item)
        if not item_slot or item_slot not in self.slot_rules:
            return bonus, reasons

        slot_config = self.slot_rules[item_slot]
        affix_types = set(match.affix_type for match in matches)

        # Check for premium bases (e.g., Stygian Vise)
        premium_bases = slot_config.get("premium_bases", [])
        if item.base_type and item.base_type in premium_bases:
            premium_bonus = slot_config.get("premium_bonus", 0)
            bonus += premium_bonus
            reasons.append(f"Premium base ({item.base_type}): +{premium_bonus}")

        # Check if item has all bonus affixes for the slot
        bonus_affixes = slot_config.get("bonus_affixes", [])
        if bonus_affixes:
            matched_bonus = [a for a in bonus_affixes if a in affix_types]
            if len(matched_bonus) >= 3:
                all_bonus = slot_config.get("all_bonus_score", 0)
                bonus += all_bonus
                reasons.append(
                    f"Slot-optimal affixes ({len(matched_bonus)}): +{all_bonus}")

        # Check for 6-link bonus on body armour
        if item_slot == "body_armour":
            # Detect 6-link from sockets field
            if hasattr(item, 'sockets') and item.sockets:
                socket_str = str(item.sockets)
                # Count max linked group (look for 6 consecutive linked sockets)
                if "-" in socket_str:
                    _ = socket_str.replace(" ", "").split("-")
                    # This is simplified - real detection would parse socket groups
                    linked_count = socket_str.count("-") + 1
                    if linked_count >= 6 or "6L" in socket_str.upper():
                        six_link_bonus = slot_config.get("six_link_bonus", 0)
                        bonus += six_link_bonus
                        reasons.append(f"6-Link: +{six_link_bonus}")

        return bonus, reasons

    def _detect_open_affixes(
        self, item: ParsedItem, matches: List[AffixMatch]
    ) -> Tuple[int, int, int]:
        """
        Estimate open prefix/suffix slots for crafting potential.

        Returns:
            (open_prefixes, open_suffixes, crafting_bonus)
        """
        # Typical rare can have 3 prefixes and 3 suffixes (6 total affixes)
        total_explicits = len(item.explicits) if item.explicits else 0

        # Estimate based on total mod count
        # This is simplified - proper detection requires knowing prefix vs suffix
        estimated_filled = min(6, total_explicits)

        # Rough heuristic: assume roughly equal prefix/suffix split
        filled_prefixes = estimated_filled // 2
        filled_suffixes = estimated_filled - filled_prefixes

        open_prefixes = max(0, 3 - filled_prefixes)
        open_suffixes = max(0, 3 - filled_suffixes)

        # Calculate bonus for crafting potential
        crafting_bonus = 0

        # Items with open slots have crafting potential
        if open_prefixes >= 1 or open_suffixes >= 1:
            # Base bonus for having any open slot
            crafting_bonus = 5

            # Extra bonus for multiple open slots
            if open_prefixes + open_suffixes >= 2:
                crafting_bonus = 10

            # High-value crafting base (2+ open with good existing mods)
            if open_prefixes + open_suffixes >= 2 and len(matches) >= 2:
                t1_count = len([m for m in matches if m.tier == "tier1"])
                if t1_count >= 1:
                    crafting_bonus = 15

        return open_prefixes, open_suffixes, crafting_bonus

    def _check_fractured(
        self, item: ParsedItem, matches: List[AffixMatch]
    ) -> Tuple[bool, int, Optional[str]]:
        """
        Check for fractured items and evaluate fractured mod value.

        Returns:
            (is_fractured, bonus_score, fractured_mod_text)
        """
        is_fractured = getattr(item, 'is_fractured', False)
        if not is_fractured:
            return False, 0, None

        bonus = 0
        fractured_mod = None

        # Try to identify the fractured mod
        # Fractured mods are typically marked in the item text
        # For now, we'll check if any T1 mods exist (likely the fractured one)
        t1_matches = [m for m in matches if m.tier == "tier1"]

        if t1_matches:
            # Assume the best T1 mod is fractured (simplified)
            best_t1 = max(t1_matches, key=lambda m: m.weight)
            fractured_mod = best_t1.mod_text

            # T1 fractured mod = significant crafting base value
            bonus = 25  # Base bonus for T1 fractured

            # Extra bonus for high-weight fractured mods
            if best_t1.weight >= 9:
                bonus = 35  # Premium fractured mod (life, MS, etc.)
            elif best_t1.weight >= 7:
                bonus = 30  # Good fractured mod (res, ES, etc.)

        elif matches:
            # T2/T3 fractured still has some value
            best_match = max(matches, key=lambda m: m.weight)
            fractured_mod = best_match.mod_text
            bonus = 10  # Lower tier fractured

        return True, bonus, fractured_mod

    def _match_archetypes(
        self, matches: List[AffixMatch]
    ) -> Tuple[List[str], int]:
        """
        Match item against build archetypes to determine fit.

        Returns:
            (list_of_matching_archetypes, bonus_score)
        """
        matched = []
        total_bonus = 0

        if not self.build_archetypes:
            return matched, total_bonus

        # Get affix types present on item
        affix_types = set(match.affix_type for match in matches)

        for archetype_key, archetype in self.build_archetypes.items():
            priority_affixes = set(archetype.get("priority_affixes", []))
            anti_affixes = set(archetype.get("anti_affixes", []))

            # Check for anti-affixes (disqualifiers)
            if anti_affixes & affix_types:
                continue

            # Count how many priority affixes match
            matching_priority = priority_affixes & affix_types

            # Need at least 2 priority affixes to match archetype
            if len(matching_priority) >= 2:
                matched.append(archetype_key)

                # Bonus based on how well item fits
                if len(matching_priority) >= 4:
                    total_bonus = max(total_bonus, 15)  # Excellent fit
                elif len(matching_priority) >= 3:
                    total_bonus = max(total_bonus, 10)  # Good fit
                else:
                    total_bonus = max(total_bonus, 5)   # Decent fit

        return matched, total_bonus

    def _calculate_meta_bonus(self, matches: List[AffixMatch]) -> int:
        """
        Calculate bonus based on current meta popularity.

        Returns:
            Meta bonus score (0-10)
        """
        if not self.meta_weights:
            return 0

        bonus = 0
        affix_types = set(match.affix_type for match in matches)

        # Check for meta-boosted affixes
        for affix_type in affix_types:
            if affix_type in self.meta_weights:
                # Meta weights can be either a dict with popularity_percent or a simple int
                meta_data = self.meta_weights[affix_type]
                if isinstance(meta_data, dict):
                    # From meta_affixes.json (MetaAnalyzer output)
                    popularity = meta_data.get("popularity_percent", 0)
                    if popularity >= 50:
                        bonus += 3
                    elif popularity >= 30:
                        bonus += 2
                    elif popularity >= 10:
                        bonus += 1
                else:
                    # Simple boost value from build_archetypes.json
                    bonus += int(meta_data)

        return min(10, bonus)  # Cap at 10

    def _calculate_total_score(
        self, base_score: int, affix_score: int, has_high_ilvl: bool,
        synergy_bonus: int = 0, red_flag_penalty: int = 0,
        slot_bonus: int = 0, crafting_bonus: int = 0, fractured_bonus: int = 0,
        archetype_bonus: int = 0, meta_bonus: int = 0
    ) -> int:
        """
        Calculate total item score.

        Args:
            base_score: 0-50
            affix_score: 0-100
            has_high_ilvl: Boolean
            synergy_bonus: Bonus from synergies
            red_flag_penalty: Penalty from red flags (negative number)
            slot_bonus: Bonus from slot-specific rules
            crafting_bonus: Bonus for open affixes/crafting potential
            fractured_bonus: Bonus for fractured items
            archetype_bonus: Bonus for matching build archetypes
            meta_bonus: Bonus from current meta popularity

        Returns:
            Total score 0-100
        """
        # Weight: base 30%, affixes 60%, ilvl 10%
        weighted_score = (
            base_score * 0.3 +
            affix_score * 0.6 +
            (10 if has_high_ilvl else 0)
        )

        # Add all bonuses and penalties
        final_score = (
            weighted_score +
            synergy_bonus +
            red_flag_penalty +
            slot_bonus +
            crafting_bonus +
            fractured_bonus +
            archetype_bonus +
            meta_bonus
        )

        return max(0, min(100, int(final_score)))

    def _determine_tier(
        self, total_score: int, matches: List[AffixMatch], synergies: List[str],
        is_fractured: bool = False, crafting_bonus: int = 0,
        matched_archetypes: List[str] = None
    ) -> Tuple[str, str]:
        """
        Determine item tier and estimated value.

        Returns:
            (tier, estimated_value)
        """
        num_good_affixes = len([m for m in matches if m.weight >= 8])
        num_t1_affixes = len([m for m in matches if m.tier == "tier1"])
        has_synergy = len(synergies) > 0
        has_influence_mod = any(m.is_influence_mod for m in matches)
        has_crafting_potential = crafting_bonus >= 10
        fits_meta = matched_archetypes and len(matched_archetypes) >= 1

        # Fractured T1 items are crafting bases - special tier
        if is_fractured and num_t1_affixes >= 1:
            if total_score >= 70:
                return "excellent", "1-5div (crafting base)"
            elif total_score >= 50:
                return "good", "50c-1div (crafting base)"

        # Excellent tier: high score + T1 mods + synergies
        if total_score >= 80 and (num_t1_affixes >= 2 or has_influence_mod):
            return "excellent", "200c-5div"
        elif total_score >= 75 and num_good_affixes >= 3:
            return "excellent", "1div+"
        elif total_score >= 75 and fits_meta and num_t1_affixes >= 1:
            return "excellent", "100c-2div (meta)"

        # Good tier: decent score + good mods or synergies
        elif total_score >= 65 and (has_synergy or has_influence_mod):
            return "good", "50-200c"
        elif total_score >= 60 and num_good_affixes >= 2:
            return "good", "50c+"
        elif total_score >= 55 and has_crafting_potential:
            return "good", "30-100c (craftable)"
        elif total_score >= 55 and fits_meta:
            return "good", "30-80c (meta fit)"

        # Average tier: usable items
        elif total_score >= 45:
            return "average", "10-50c"
        elif total_score >= 35:
            return "average", "5-10c"

        # Vendor tier
        else:
            return "vendor", "<5c"

    def get_summary(self, evaluation: RareItemEvaluation) -> str:
        """
        Get human-readable summary of evaluation.

        Returns:
            Multi-line string summary
        """
        lines = []
        lines.append("=== Rare Item Evaluation ===")
        lines.append(f"Item: {evaluation.item.get_display_name()}")
        lines.append(f"Base: {evaluation.item.base_type}")
        lines.append(f"iLvl: {evaluation.item.item_level or 'Unknown'}")
        if evaluation.item.influences:
            lines.append(
                f"Influences: {
                    ', '.join(
                        evaluation.item.influences)}")
        if evaluation.is_fractured:
            lines.append("Fractured: Yes")
        lines.append("")

        lines.append(f"Tier: {evaluation.tier.upper()}")
        lines.append(f"Estimated Value: {evaluation.estimated_value}")
        lines.append(f"Total Score: {evaluation.total_score}/100")
        lines.append(f"  - Base Score: {evaluation.base_score}/50")
        lines.append(f"  - Affix Score: {evaluation.affix_score}/100")
        if evaluation.synergy_bonus > 0:
            lines.append(f"  - Synergy Bonus: +{evaluation.synergy_bonus}")
        if evaluation.red_flag_penalty < 0:
            lines.append(
                f"  - Red Flag Penalty: {evaluation.red_flag_penalty}")
        if evaluation.slot_bonus > 0:
            lines.append(f"  - Slot Bonus: +{evaluation.slot_bonus}")
        if evaluation.crafting_bonus > 0:
            lines.append(f"  - Crafting Bonus: +{evaluation.crafting_bonus}")
        if evaluation.fractured_bonus > 0:
            lines.append(f"  - Fractured Bonus: +{evaluation.fractured_bonus}")
        if evaluation.archetype_bonus > 0:
            lines.append(f"  - Archetype Bonus: +{evaluation.archetype_bonus}")
        if evaluation.meta_bonus > 0:
            lines.append(f"  - Meta Bonus: +{evaluation.meta_bonus}")
        lines.append("")

        if evaluation.matched_affixes:
            lines.append(
                f"Valuable Affixes ({len(evaluation.matched_affixes)}):")
            for match in evaluation.matched_affixes:
                value_str = f" [{match.value}]" if match.value else ""
                tier_str = f" ({
                    match.tier})" if not match.is_influence_mod else " (influence)"
                weight_str = f" weight:{match.weight}"
                lines.append(
                    f"  [OK] {
                        match.affix_type}: {
                        match.mod_text}{value_str}{tier_str}{weight_str}")
        else:
            lines.append("No valuable affixes found")

        if evaluation.synergies_found:
            lines.append("")
            lines.append(
                f"Synergies Detected ({len(evaluation.synergies_found)}):")
            for synergy in evaluation.synergies_found:
                synergy_data = self.synergies.get(synergy, {})
                desc = synergy_data.get("description", synergy)
                bonus = synergy_data.get("bonus_score", 0)
                lines.append(f"  [+] {desc} (+{bonus} score)")

        if evaluation.red_flags_found:
            lines.append("")
            lines.append(f"Red Flags ({len(evaluation.red_flags_found)}):")
            for flag in evaluation.red_flags_found:
                flag_data = self.red_flags.get(flag, {})
                desc = flag_data.get("description", flag)
                penalty = flag_data.get("penalty_score", 0)
                lines.append(f"  [!] {desc} ({penalty} score)")

        if evaluation.slot_bonus_reasons:
            lines.append("")
            lines.append("Slot Bonuses:")
            for reason in evaluation.slot_bonus_reasons:
                lines.append(f"  [+] {reason}")

        # Crafting potential section
        if evaluation.open_prefixes > 0 or evaluation.open_suffixes > 0:
            lines.append("")
            lines.append("Crafting Potential:")
            lines.append(
                f"  Open Slots: ~{evaluation.open_prefixes}P / "
                f"~{evaluation.open_suffixes}S")
            if evaluation.crafting_bonus > 0:
                lines.append(
                    f"  Crafting Value: +{evaluation.crafting_bonus} score")

        # Fractured item section
        if evaluation.is_fractured and evaluation.fractured_mod:
            lines.append("")
            lines.append("Fractured Mod:")
            lines.append(f"  {evaluation.fractured_mod}")
            lines.append(
                f"  Crafting Base Value: +{evaluation.fractured_bonus} score")

        # Build archetype matching section
        if evaluation.matched_archetypes:
            lines.append("")
            lines.append(
                f"Build Archetypes ({len(evaluation.matched_archetypes)}):")
            for archetype_key in evaluation.matched_archetypes:
                archetype = self.build_archetypes.get(archetype_key, {})
                name = archetype.get("name", archetype_key)
                desc = archetype.get("description", "")
                lines.append(f"  [+] {name}")
                if desc:
                    lines.append(f"      {desc}")

        lines.append("")
        lines.append(
            f"Valuable Base: {
                'Yes' if evaluation.is_valuable_base else 'No'}")
        lines.append(
            f"High iLvl (84+): {'Yes' if evaluation.has_high_ilvl else 'No'}")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the evaluator
    from core.item_parser import ItemParser

    parser = ItemParser()
    evaluator = RareItemEvaluator()

    # Test item 1: Good rare helmet
    sample1 = """Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 86
--------
+45 to maximum Energy Shield (implicit)
--------
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+15% to Chaos Resistance
+85 to maximum Energy Shield
"""

    item1 = parser.parse(sample1)
    if item1:
        eval1 = evaluator.evaluate(item1)
        print(evaluator.get_summary(eval1))

    print("\n" + "=" * 50 + "\n")

    # Test item 2: Mediocre rare
    sample2 = """Rarity: RARE
Bad Ring
Iron Ring
--------
Item Level: 45
--------
+5 to maximum Life
+10% to Fire Resistance
+8 to Strength
"""

    item2 = parser.parse(sample2)
    if item2:
        eval2 = evaluator.evaluate(item2)
        print(evaluator.get_summary(eval2))
