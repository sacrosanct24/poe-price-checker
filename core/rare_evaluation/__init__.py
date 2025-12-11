"""
Rare Item Evaluation Package.

Evaluates rare items for potential value based on affixes and bases.

Public API:
- RareItemEvaluator: Main evaluator class
- RareItemEvaluation: Evaluation result dataclass
- AffixMatch: Matched affix dataclass

Example:
    from core.rare_evaluation import RareItemEvaluator
    evaluator = RareItemEvaluator()
    result = evaluator.evaluate(parsed_item)
"""
from core.rare_evaluation.models import AffixMatch, RareItemEvaluation
from core.rare_evaluation.evaluator import RareItemEvaluator

__all__ = [
    "RareItemEvaluator",
    "RareItemEvaluation",
    "AffixMatch",
]
