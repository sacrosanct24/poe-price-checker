"""
Build Archetypes Module.

Provides cross-build item analysis to answer:
"What builds would want this item?"

Components:
- archetype_models: Data structures for build archetypes
- archetype_database: Database of 25+ popular build archetypes
- archetype_matcher: Scoring engine for item-to-build matching

Usage:
    from core.build_archetypes import analyze_item_for_builds, get_top_builds_for_item

    # Get full analysis
    analysis = analyze_item_for_builds(parsed_item)
    print(analysis.get_summary())

    # Get top 3 builds
    top_builds = get_top_builds_for_item(parsed_item, limit=3)
    for match in top_builds:
        print(f"{match.archetype.name}: {match.score:.0f}%")
"""

from core.build_archetypes.archetype_models import (
    ArchetypeMatch,
    BuildArchetype,
    BuildCategory,
    CrossBuildAnalysis,
    DamageType,
    DefenseType,
    StatWeight,
)
from core.build_archetypes.archetype_database import (
    ALL_ARCHETYPES,
    ArchetypeDatabase,
    get_archetype_database,
)
from core.build_archetypes.archetype_matcher import (
    ArchetypeMatcher,
    analyze_item_for_builds,
    extract_item_stats,
    get_archetype_matcher,
    get_top_builds_for_item,
)

__all__ = [
    # Models
    "ArchetypeMatch",
    "BuildArchetype",
    "BuildCategory",
    "CrossBuildAnalysis",
    "DamageType",
    "DefenseType",
    "StatWeight",
    # Database
    "ALL_ARCHETYPES",
    "ArchetypeDatabase",
    "get_archetype_database",
    # Matcher
    "ArchetypeMatcher",
    "analyze_item_for_builds",
    "extract_item_stats",
    "get_archetype_matcher",
    "get_top_builds_for_item",
]
