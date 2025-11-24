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
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from core.item_parser import ParsedItem


@dataclass
class AffixMatch:
    """Represents a matched valuable affix on an item."""
    affix_type: str  # e.g., "life", "resistances"
    pattern: str     # Pattern that matched
    mod_text: str    # Actual mod text from item
    value: Optional[float]  # Extracted numeric value
    weight: int      # Importance weight (1-10)
    tier: str        # "tier1", "tier2", etc.


@dataclass
class RareItemEvaluation:
    """Results of rare item evaluation."""
    item: ParsedItem
    base_score: int  # 0-100 based on base type and ilvl
    affix_score: int  # 0-100 based on valuable affixes
    total_score: int  # Combined score
    
    is_valuable_base: bool
    has_high_ilvl: bool
    matched_affixes: List[AffixMatch]
    
    # Categorization
    tier: str  # "excellent", "good", "average", "vendor"
    estimated_value: str  # "10c+", "50c+", "1div+", etc.
    
    # Build matching (if provided)
    matches_build: bool = False
    build_name: Optional[str] = None
    matching_requirements: List[str] = None


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
        self.valuable_affixes = self._load_valuable_affixes()
        self.valuable_bases = self._load_valuable_bases()
        
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
        
        # Evaluate affixes
        matched_affixes = self._match_affixes(item)
        affix_score = self._calculate_affix_score(matched_affixes)
        
        # Calculate total score
        total_score = self._calculate_total_score(
            base_score, affix_score, has_high_ilvl
        )
        
        # Determine tier and estimated value
        tier, estimated_value = self._determine_tier(total_score, matched_affixes)
        
        return RareItemEvaluation(
            item=item,
            base_score=base_score,
            affix_score=affix_score,
            total_score=total_score,
            is_valuable_base=is_valuable_base,
            has_high_ilvl=has_high_ilvl,
            matched_affixes=matched_affixes,
            tier=tier,
            estimated_value=estimated_value
        )
    
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
        Match item's explicit mods against valuable affixes.
        
        Returns:
            List of AffixMatch objects
        """
        matches = []
        
        for mod_text in item.explicits:
            for affix_type, affix_data in self.valuable_affixes.items():
                if affix_type.startswith("_"):
                    continue
                
                tier1_patterns = affix_data.get("tier1", [])
                weight = affix_data.get("weight", 5)
                min_value = affix_data.get("min_value", 0)
                
                for pattern in tier1_patterns:
                    # Convert pattern to regex
                    # "+# to maximum Life" -> r"\+(\d+) to maximum Life"
                    # First replace # with placeholder
                    regex_pattern = pattern.replace("#", "__NUMBER__")
                    # Escape special regex characters
                    regex_pattern = re.escape(regex_pattern)
                    # Replace placeholder with number capture group
                    regex_pattern = regex_pattern.replace("__NUMBER__", r"(\d+(?:\.\d+)?)")

                    match = re.search(regex_pattern, mod_text, re.IGNORECASE)
                    if match:
                        # Extract value
                        value = None
                        if match.groups():
                            try:
                                value = float(match.group(1))
                            except (ValueError, IndexError):
                                value = None
                        
                        # Check minimum value requirement
                        if value and value >= min_value:
                            matches.append(AffixMatch(
                                affix_type=affix_type,
                                pattern=pattern,
                                mod_text=mod_text,
                                value=value,
                                weight=weight,
                                tier="tier1"
                            ))
                            break  # Only match once per mod
        
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
    
    def _calculate_total_score(
        self, base_score: int, affix_score: int, has_high_ilvl: bool
    ) -> int:
        """
        Calculate total item score.
        
        Args:
            base_score: 0-50
            affix_score: 0-100
            has_high_ilvl: Boolean
            
        Returns:
            Total score 0-100
        """
        # Weight: base 30%, affixes 60%, ilvl 10%
        weighted_score = (
            base_score * 0.3 +
            affix_score * 0.6 +
            (10 if has_high_ilvl else 0)
        )
        
        return min(100, int(weighted_score))
    
    def _determine_tier(
        self, total_score: int, matches: List[AffixMatch]
    ) -> Tuple[str, str]:
        """
        Determine item tier and estimated value.
        
        Returns:
            (tier, estimated_value)
        """
        num_good_affixes = len([m for m in matches if m.weight >= 8])
        
        if total_score >= 75 and num_good_affixes >= 3:
            return "excellent", "1div+"
        elif total_score >= 60 and num_good_affixes >= 2:
            return "good", "50c+"
        elif total_score >= 40 and num_good_affixes >= 1:
            return "average", "10c+"
        else:
            return "vendor", "<10c"
    
    def get_summary(self, evaluation: RareItemEvaluation) -> str:
        """
        Get human-readable summary of evaluation.
        
        Returns:
            Multi-line string summary
        """
        lines = []
        lines.append(f"=== Rare Item Evaluation ===")
        lines.append(f"Item: {evaluation.item.get_display_name()}")
        lines.append(f"Base: {evaluation.item.base_type}")
        lines.append(f"iLvl: {evaluation.item.item_level or 'Unknown'}")
        lines.append("")
        
        lines.append(f"Tier: {evaluation.tier.upper()}")
        lines.append(f"Estimated Value: {evaluation.estimated_value}")
        lines.append(f"Total Score: {evaluation.total_score}/100")
        lines.append(f"  - Base Score: {evaluation.base_score}/50")
        lines.append(f"  - Affix Score: {evaluation.affix_score}/100")
        lines.append("")
        
        if evaluation.matched_affixes:
            lines.append(f"Valuable Affixes ({len(evaluation.matched_affixes)}):")
            for match in evaluation.matched_affixes:
                value_str = f" [{match.value}]" if match.value else ""
                lines.append(f"  [OK] {match.affix_type}: {match.mod_text}{value_str}")
        else:
            lines.append("No valuable affixes found")
        
        lines.append("")
        lines.append(f"Valuable Base: {'Yes' if evaluation.is_valuable_base else 'No'}")
        lines.append(f"High iLvl (84+): {'Yes' if evaluation.has_high_ilvl else 'No'}")
        
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
    
    print("\n" + "="*50 + "\n")
    
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
