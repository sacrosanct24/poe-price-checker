"""
Build Archetypes Module

Provides cross-build intelligence for item evaluation:
- BuildArchetype: Defines what stats/mods a build archetype wants
- ArchetypeDatabase: Collection of 20-30 meta build archetypes
- ArchetypeMatcher: Scores items against all archetypes

Usage:
    from core.build_archetypes import ArchetypeMatcher, get_archetype_database

    matcher = ArchetypeMatcher()
    analysis = matcher.match_item(parsed_item)
    for match in analysis.get_top_matches(3):
        print(f"{match.archetype.name}: {match.score:.0f}% match")
"""

from core.build_archetypes.archetype_models import (
    BuildArchetype,
    BuildCategory,
    DamageType,
    DefenseType,
    StatWeight,
    ArchetypeMatch,
    CrossBuildAnalysis,
)
from core.build_archetypes.archetype_database import (
    ArchetypeDatabase,
    get_archetype_database,
    ALL_ARCHETYPES,
)
from core.build_archetypes.archetype_matcher import (
    ArchetypeMatcher,
    get_archetype_matcher,
    analyze_item_for_builds,
    get_top_builds_for_item,
)

__all__ = [
    # Models
    "BuildArchetype",
    "BuildCategory",
    "DamageType",
    "DefenseType",
    "StatWeight",
    "ArchetypeMatch",
    "CrossBuildAnalysis",
    # Database
    "ArchetypeDatabase",
    "get_archetype_database",
    "ALL_ARCHETYPES",
    # Matcher
    "ArchetypeMatcher",
    "get_archetype_matcher",
    "analyze_item_for_builds",
    "get_top_builds_for_item",
]
