"""
Pricing Models.

Data structures for price results and explanations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class PriceExplanation:
    """
    Structured explanation for why a price was suggested.

    This captures all the reasoning that went into a price suggestion,
    making it easy to display "why" to users.
    """
    # Primary reasoning
    summary: str = ""  # One-line summary: "Price from poe.ninja with high confidence"

    # Data source details
    source_name: str = ""  # "poe.ninja", "poe.watch", "rare_evaluator", etc.
    source_details: str = ""  # Additional source info

    # Statistical confidence
    confidence: str = ""  # "high", "medium", "low", "none"
    confidence_reason: str = ""  # "High sample size (50) with tight spread"

    # Price calculation details
    calculation_method: str = ""  # "trimmed_mean", "median", "mean", "evaluation"
    sample_size: int = 0  # Number of listings/data points
    price_spread: str = ""  # "tight", "moderate", "high"

    # Statistical details (optional)
    stats_used: dict = field(default_factory=dict)  # min, max, p25, p75, etc.

    # For rare items
    is_rare_evaluation: bool = False
    rare_tier: str = ""  # "excellent", "good", "average", "vendor"
    rare_score: int = 0  # Total score
    valuable_mods: List[str] = field(default_factory=list)  # Key mods found
    synergies: List[str] = field(default_factory=list)  # Synergies detected
    red_flags: List[str] = field(default_factory=list)  # Anti-synergies

    # Build matching
    matches_build: bool = False
    build_match_details: str = ""

    # Adjustments made
    adjustments: List[str] = field(default_factory=list)  # "Corrupted: -20%", etc.

    def to_summary_lines(self) -> List[str]:
        """Generate human-readable summary lines."""
        lines = []

        if self.summary:
            lines.append(f"Summary: {self.summary}")

        if self.source_name:
            src = f"Source: {self.source_name}"
            if self.source_details:
                src += f" ({self.source_details})"
            lines.append(src)

        if self.confidence:
            conf = f"Confidence: {self.confidence.upper()}"
            if self.confidence_reason:
                conf += f" - {self.confidence_reason}"
            lines.append(conf)

        if self.sample_size > 0:
            lines.append(f"Based on: {self.sample_size} listings")

        if self.calculation_method:
            lines.append(f"Price method: {self.calculation_method}")

        if self.is_rare_evaluation:
            lines.append(f"Rare tier: {self.rare_tier} (score: {self.rare_score})")
            if self.valuable_mods:
                lines.append(f"Valuable mods: {', '.join(self.valuable_mods[:5])}")
            if self.synergies:
                lines.append(f"Synergies: {', '.join(self.synergies)}")
            if self.red_flags:
                lines.append(f"Red flags: {', '.join(self.red_flags)}")

        if self.matches_build:
            lines.append(f"Build match: {self.build_match_details}")

        if self.adjustments:
            lines.append(f"Adjustments: {', '.join(self.adjustments)}")

        return lines

    def to_json(self) -> str:
        """Serialize to JSON string for storage in result row."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "PriceExplanation":
        """Deserialize from JSON string."""
        try:
            data = json.loads(json_str)
            return cls(**data)
        except (json.JSONDecodeError, TypeError):
            return cls(summary="Unable to parse explanation")
