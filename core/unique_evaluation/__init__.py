"""
Unique item evaluation package.

Provides comprehensive evaluation for unique items including meta scoring,
corruption analysis, link evaluation, and build relevance.
"""

from core.unique_evaluation.evaluator import UniqueItemEvaluator
from core.unique_evaluation.models import (
    CorruptionMatch,
    LinkEvaluation,
    MetaRelevance,
    UniqueItemEvaluation,
)

__all__ = [
    "UniqueItemEvaluator",
    "UniqueItemEvaluation",
    "CorruptionMatch",
    "LinkEvaluation",
    "MetaRelevance",
]
