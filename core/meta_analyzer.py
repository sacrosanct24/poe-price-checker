"""
Meta Analyzer - Aggregate affix data from multiple builds

Analyzes popular builds to identify:
- Most common affixes across meta builds
- League-specific valuable affixes
- Dynamic affix weights based on popularity
"""
from __future__ import annotations

import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports when running as script
_script_dir = Path(__file__).parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger(__name__)


@dataclass
class AffixPopularity:
    """Affix with popularity metrics."""
    affix_pattern: str  # e.g., "+# to maximum Life"
    affix_type: str  # e.g., "life"

    # Popularity metrics
    appearance_count: int = 0  # How many builds have this
    total_builds: int = 0  # Total builds analyzed

    # Value ranges seen
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None

    # Which classes/ascendancies use it most
    popular_with: List[str] = field(default_factory=list)

    @property
    def popularity_percent(self) -> float:
        """Percentage of builds using this affix."""
        if self.total_builds == 0:
            return 0.0
        return (self.appearance_count / self.total_builds) * 100


class MetaAnalyzer:
    """
    Analyze build data to identify meta affixes.

    Features:
    - Aggregate affixes across builds
    - Calculate affix popularity
    - Generate dynamic weights
    - Identify league-specific metas
    """

    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize meta analyzer.

        Args:
            cache_file: Optional file to cache analysis results
        """
        self.cache_file = cache_file or Path("data/meta_affixes.json")

        # Affix patterns to track
        # Maps affix_type -> list of patterns
        self.affix_patterns = {
            'life': ['+# to maximum Life', 'Regenerate # Life per second'],
            'resistances': [
                '+#% to Fire Resistance',
                '+#% to Cold Resistance',
                '+#% to Lightning Resistance'
            ],
            'chaos_resistance': ['+#% to Chaos Resistance'],
            'movement_speed': ['#% increased Movement Speed'],
            'attack_speed': ['#% increased Attack Speed'],
            'cast_speed': ['#% increased Cast Speed'],
            'spell_suppression': ['+#% chance to Suppress Spell Damage'],
            'energy_shield': ['+# to maximum Energy Shield', '#% increased Energy Shield'],
            'critical_strike_multiplier': ['+#% to Global Critical Strike Multiplier'],
            'attributes': ['+# to Strength', '+# to Dexterity', '+# to Intelligence'],
            'mana': ['+# to maximum Mana'],
        }

        # Analysis results
        self.affix_popularity: Dict[str, AffixPopularity] = {}
        self.builds_analyzed = 0
        self.last_analysis: Optional[datetime] = None

    def analyze_builds(
        self,
        builds: List,  # List of BuildRequirement objects
        league: str = "Unknown",
    ) -> Dict[str, AffixPopularity]:
        """
        Analyze a collection of builds to extract meta affixes.

        Args:
            builds: List of BuildRequirement objects from BuildMatcher
            league: Current league name

        Returns:
            Dict mapping affix_type -> AffixPopularity
        """
        logger.info(f"Analyzing {len(builds)} builds for league: {league}")

        # Reset counters
        self.builds_analyzed = len(builds)
        affix_counter = Counter()
        affix_values = defaultdict(list)
        affix_classes = defaultdict(set)

        for build in builds:
            # Track desired affixes
            for desired in build.desired_affixes:
                # Try to match to known patterns
                affix_type = self._identify_affix_type(desired)
                if affix_type:
                    affix_counter[affix_type] += 1
                    if build.build_name:
                        affix_classes[affix_type].add(build.build_name)

            # Track required stats
            if build.required_life > 0:
                affix_counter['life'] += 1
                affix_values['life'].append(build.required_life)

            if build.required_es > 0:
                affix_counter['energy_shield'] += 1
                affix_values['energy_shield'].append(build.required_es)

            if build.required_resistances:
                for res_type in build.required_resistances:
                    if res_type == 'chaos':
                        affix_counter['chaos_resistance'] += 1
                    else:
                        affix_counter['resistances'] += 1

        # Create AffixPopularity objects
        self.affix_popularity = {}

        for affix_type, count in affix_counter.items():
            # Get pattern
            patterns = self.affix_patterns.get(affix_type, [])
            pattern = patterns[0] if patterns else affix_type

            # Get value stats
            values = affix_values.get(affix_type, [])
            min_val = min(values) if values else None
            max_val = max(values) if values else None
            avg_val = sum(values) / len(values) if values else None

            # Get popular classes
            classes = list(affix_classes.get(affix_type, []))

            self.affix_popularity[affix_type] = AffixPopularity(
                affix_pattern=pattern,
                affix_type=affix_type,
                appearance_count=count,
                total_builds=self.builds_analyzed,
                min_value=min_val,
                max_value=max_val,
                avg_value=avg_val,
                popular_with=classes[:5]  # Top 5 classes
            )

        self.last_analysis = datetime.now()

        # Save to cache
        self._save_cache(league)

        logger.info(f"Analyzed {self.builds_analyzed} builds, found {len(self.affix_popularity)} meta affixes")

        return self.affix_popularity

    def _identify_affix_type(self, affix_text: str) -> Optional[str]:
        """
        Identify affix type from text.

        Args:
            affix_text: Affix description (e.g., "increased Movement Speed")

        Returns:
            Affix type key, or None if not recognized
        """
        affix_text_lower = affix_text.lower()

        # Pattern matching
        if 'life' in affix_text_lower:
            if 'regen' in affix_text_lower:
                return 'life'  # Could separate life_regen
            return 'life'

        if 'movement' in affix_text_lower or 'move' in affix_text_lower:
            return 'movement_speed'

        if 'attack speed' in affix_text_lower:
            return 'attack_speed'

        if 'cast speed' in affix_text_lower:
            return 'cast_speed'

        if 'suppression' in affix_text_lower or 'suppress' in affix_text_lower:
            return 'spell_suppression'

        if 'energy shield' in affix_text_lower or 'es' == affix_text_lower:
            return 'energy_shield'

        if 'critical' in affix_text_lower and 'mult' in affix_text_lower:
            return 'critical_strike_multiplier'

        if any(res in affix_text_lower for res in ['fire', 'cold', 'lightning']):
            return 'resistances'

        if 'chaos' in affix_text_lower and 'resist' in affix_text_lower:
            return 'chaos_resistance'

        if any(attr in affix_text_lower for attr in ['strength', 'dexterity', 'intelligence']):
            return 'attributes'

        if 'mana' in affix_text_lower:
            return 'mana'

        return None

    def get_top_affixes(self, limit: int = 10) -> List[Tuple[str, AffixPopularity]]:
        """
        Get top affixes by popularity.

        Args:
            limit: Number of top affixes to return

        Returns:
            List of (affix_type, AffixPopularity) tuples sorted by popularity
        """
        sorted_affixes = sorted(
            self.affix_popularity.items(),
            key=lambda x: x[1].appearance_count,
            reverse=True
        )
        return sorted_affixes[:limit]

    def generate_dynamic_weights(
        self,
        base_weight: float = 5.0,
        popularity_multiplier: float = 0.1,
    ) -> Dict[str, float]:
        """
        Generate dynamic affix weights based on meta popularity.

        Args:
            base_weight: Base weight for all affixes
            popularity_multiplier: How much to boost weight per % popularity

        Returns:
            Dict mapping affix_type -> weight
        """
        weights = {}

        for affix_type, popularity in self.affix_popularity.items():
            # Calculate weight based on popularity
            # Base weight + (popularity % * multiplier)
            popularity_pct = popularity.popularity_percent
            weight = base_weight + (popularity_pct * popularity_multiplier)

            weights[affix_type] = round(weight, 1)

        return weights

    def _save_cache(self, league: str) -> None:
        """Save analysis results to cache file."""
        if not self.cache_file:
            return

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'league': league,
                'builds_analyzed': self.builds_analyzed,
                'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
                'affixes': {}
            }

            for affix_type, pop in self.affix_popularity.items():
                data['affixes'][affix_type] = {
                    'pattern': pop.affix_pattern,
                    'appearance_count': pop.appearance_count,
                    'total_builds': pop.total_builds,
                    'popularity_percent': pop.popularity_percent,
                    'min_value': pop.min_value,
                    'max_value': pop.max_value,
                    'avg_value': pop.avg_value,
                    'popular_with': pop.popular_with,
                }

            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved meta analysis to {self.cache_file}")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def load_cache(self) -> bool:
        """
        Load cached analysis results.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.cache_file or not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            self.builds_analyzed = data.get('builds_analyzed', 0)

            last_analysis_str = data.get('last_analysis')
            if last_analysis_str:
                self.last_analysis = datetime.fromisoformat(last_analysis_str)

            # Reconstruct AffixPopularity objects
            self.affix_popularity = {}
            for affix_type, affix_data in data.get('affixes', {}).items():
                self.affix_popularity[affix_type] = AffixPopularity(
                    affix_pattern=affix_data['pattern'],
                    affix_type=affix_type,
                    appearance_count=affix_data['appearance_count'],
                    total_builds=affix_data['total_builds'],
                    min_value=affix_data.get('min_value'),
                    max_value=affix_data.get('max_value'),
                    avg_value=affix_data.get('avg_value'),
                    popular_with=affix_data.get('popular_with', []),
                )

            logger.info(f"Loaded cached meta analysis from {self.cache_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return False

    def print_summary(self) -> None:
        """Print a summary of meta analysis."""
        print("=" * 80)
        print("META AFFIX ANALYSIS")
        print("=" * 80)
        print(f"Builds Analyzed: {self.builds_analyzed}")
        print(f"Last Analysis: {self.last_analysis}")
        print(f"\nTop Meta Affixes:")
        print("-" * 80)

        for i, (affix_type, pop) in enumerate(self.get_top_affixes(10), 1):
            print(f"{i:2d}. {affix_type:25s} - {pop.popularity_percent:5.1f}% "
                  f"({pop.appearance_count}/{pop.total_builds} builds)")

            if pop.avg_value:
                print(f"    Avg Value: {pop.avg_value:.1f} (range: {pop.min_value}-{pop.max_value})")

            if pop.popular_with:
                print(f"    Popular with: {', '.join(pop.popular_with[:3])}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    # Test meta analyzer
    logging.basicConfig(level=logging.INFO)

    from core.build_matcher import BuildMatcher

    print("Testing Meta Analyzer")
    print("=" * 80)

    # Create some sample builds
    matcher = BuildMatcher()

    # Add sample builds
    builds = [
        matcher.add_manual_build(
            "Lightning Strike Raider",
            required_life=4000,
            resistances={"fire": 75, "cold": 75, "lightning": 75},
            desired_affixes=["Movement Speed", "Attack Speed", "Suppression"]
        ),
        matcher.add_manual_build(
            "Righteous Fire Juggernaut",
            required_life=8000,
            resistances={"fire": 90, "chaos": 75},
            desired_affixes=["Life Regeneration", "Maximum Life", "Fire Resistance"]
        ),
        matcher.add_manual_build(
            "Poison Blade Vortex Pathfinder",
            required_life=5000,
            resistances={"chaos": 75},
            desired_affixes=["Cast Speed", "Attack Speed", "Chaos Resistance"]
        ),
    ]

    # Analyze
    analyzer = MetaAnalyzer()
    analyzer.analyze_builds(matcher.builds, league="Ancestor")

    # Show results
    analyzer.print_summary()

    # Show dynamic weights
    print("\nDynamic Weights:")
    weights = analyzer.generate_dynamic_weights()
    for affix_type, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {affix_type:25s}: {weight:.1f}")

    print("\n" + "=" * 80)
