"""
AI-Powered Item Improvement Advisor.

Uses AI providers to generate intelligent suggestions for improving items:
- Divine orb recommendations
- Crafting suggestions
- Upgrade paths
- Value optimization tips

Part of Phase 4: Think Big features.

Usage:
    from core.ai_improvement_advisor import AIImprovementAdvisor

    advisor = AIImprovementAdvisor(ai_provider)
    suggestions = await advisor.get_suggestions(item, crafting_analysis)
    print(suggestions.summary)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.item_parser import ParsedItem
    from core.crafting_potential import CraftingAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ImprovementSuggestion:
    """A single improvement suggestion."""
    action: str  # e.g., "Divine", "Craft", "Exalt"
    description: str  # What to do
    cost_estimate: str  # e.g., "~1 divine", "~50c"
    expected_benefit: str  # What you'll gain
    risk_level: str = "low"  # "low", "medium", "high"
    priority: int = 1  # 1 = highest priority


@dataclass
class ImprovementAnalysis:
    """Complete improvement analysis for an item."""
    item_quality_percent: float = 0.0  # How close to ideal (0-100)
    summary: str = ""  # One-line summary
    suggestions: List[ImprovementSuggestion] = field(default_factory=list)
    ai_insight: str = ""  # AI-generated insight
    crafting_path: str = ""  # Suggested crafting path
    value_if_improved: str = ""  # Estimated value after improvements


# Prompt templates for AI providers
IMPROVEMENT_PROMPT_TEMPLATE = """You are a Path of Exile item crafting expert. Analyze this item and provide improvement suggestions.

ITEM:
{item_text}

CURRENT ANALYSIS:
- Quality: {quality_percent}% of optimal
- Open Slots: {open_slots}
- Divine Potential: {divine_potential}
- Crafting Value: {crafting_value}

MOD DETAILS:
{mod_details}

Provide 2-3 specific, actionable suggestions to improve this item. For each suggestion:
1. State the action (Divine, Craft, Exalt, etc.)
2. Explain why and what you expect to gain
3. Estimate the cost

Keep responses concise and practical. Focus on value-for-money improvements.

Response format:
SUMMARY: [One sentence overall assessment]

SUGGESTIONS:
1. [Action]: [Description] (Cost: ~X, Benefit: Y)
2. [Action]: [Description] (Cost: ~X, Benefit: Y)

CRAFTING PATH: [Brief optimal upgrade path if budget allows]
"""


class AIImprovementAdvisor:
    """
    Uses AI providers to generate item improvement suggestions.

    Can work with various AI backends (Gemini, Claude, OpenAI, etc.)
    through the data_sources/ai abstraction.
    """

    def __init__(self, ai_provider: Optional[Any] = None):
        """
        Initialize the advisor.

        Args:
            ai_provider: AI provider instance (e.g., GeminiProvider)
        """
        self._ai_provider = ai_provider

    def set_provider(self, provider: Any) -> None:
        """Set the AI provider."""
        self._ai_provider = provider

    async def get_suggestions_async(
        self,
        item: "ParsedItem",
        crafting_analysis: Optional["CraftingAnalysis"] = None,
    ) -> ImprovementAnalysis:
        """
        Get AI-powered improvement suggestions (async).

        Args:
            item: Parsed item to analyze
            crafting_analysis: Pre-computed crafting analysis (optional)

        Returns:
            ImprovementAnalysis with suggestions
        """
        analysis = ImprovementAnalysis()

        # Build analysis from crafting data
        if crafting_analysis:
            analysis = self._build_from_crafting_analysis(item, crafting_analysis)

        # If we have an AI provider, get AI insight
        if self._ai_provider:
            try:
                ai_response = await self._get_ai_insight_async(item, crafting_analysis)
                analysis.ai_insight = ai_response
                self._parse_ai_response(analysis, ai_response)
            except Exception as e:
                logger.debug(f"AI insight failed: {e}")
                analysis.ai_insight = "AI analysis unavailable"

        return analysis

    def get_suggestions(
        self,
        item: "ParsedItem",
        crafting_analysis: Optional["CraftingAnalysis"] = None,
    ) -> ImprovementAnalysis:
        """
        Get improvement suggestions (sync version).

        Args:
            item: Parsed item to analyze
            crafting_analysis: Pre-computed crafting analysis (optional)

        Returns:
            ImprovementAnalysis with suggestions
        """
        analysis = ImprovementAnalysis()

        # Build analysis from crafting data
        if crafting_analysis:
            analysis = self._build_from_crafting_analysis(item, crafting_analysis)
        else:
            # Try to generate crafting analysis
            try:
                from core.crafting_potential import analyze_crafting_potential
                crafting_analysis = analyze_crafting_potential(item)
                analysis = self._build_from_crafting_analysis(item, crafting_analysis)
            except Exception as e:
                logger.debug(f"Crafting analysis failed: {e}")

        return analysis

    def _build_from_crafting_analysis(
        self,
        item: "ParsedItem",
        crafting: "CraftingAnalysis",
    ) -> ImprovementAnalysis:
        """Build improvement analysis from crafting analysis."""
        analysis = ImprovementAnalysis()

        # Calculate quality percent
        if crafting.mod_analyses:
            total_quality = sum(m.roll_quality for m in crafting.mod_analyses)
            analysis.item_quality_percent = total_quality / len(crafting.mod_analyses)
        else:
            analysis.item_quality_percent = 50.0  # Default

        # Build summary
        quality_desc = "excellent" if analysis.item_quality_percent >= 85 else \
                       "good" if analysis.item_quality_percent >= 70 else \
                       "average" if analysis.item_quality_percent >= 50 else "below average"
        analysis.summary = f"This item is {quality_desc} ({analysis.item_quality_percent:.0f}% optimal)"

        # Generate suggestions from crafting analysis
        suggestions = []

        # Divine suggestion
        if crafting.divine_recommended:
            best_divine_target = None
            best_potential = 0
            for mod in crafting.mod_analyses:
                if mod.divine_potential > best_potential and mod.tier and mod.tier <= 2:
                    best_potential = mod.divine_potential
                    best_divine_target = mod

            if best_divine_target:
                stat = (best_divine_target.stat_type or "mod").replace("_", " ").title()
                current = best_divine_target.current_value or 0
                max_roll = best_divine_target.max_roll

                suggestions.append(ImprovementSuggestion(
                    action="Divine Orb",
                    description=f"Re-roll {stat} (currently {current}, max {max_roll})",
                    cost_estimate="~1 divine",
                    expected_benefit=f"+{best_potential} {stat} potential",
                    risk_level="low",
                    priority=1,
                ))

        # Craft suggestion for open slots
        if crafting.open_prefixes > 0:
            suggestions.append(ImprovementSuggestion(
                action="Benchcraft Prefix",
                description=f"Craft life or damage prefix ({crafting.open_prefixes} open)",
                cost_estimate="~2c",
                expected_benefit="Add valuable stat",
                risk_level="low",
                priority=2 if crafting.divine_recommended else 1,
            ))

        if crafting.open_suffixes > 0:
            suggestions.append(ImprovementSuggestion(
                action="Benchcraft Suffix",
                description=f"Craft resistance or speed ({crafting.open_suffixes} open)",
                cost_estimate="~2c",
                expected_benefit="Add valuable stat",
                risk_level="low",
                priority=2 if crafting.open_prefixes > 0 else 1,
            ))

        # Advanced crafting for high-value bases
        good_mod_count = sum(1 for m in crafting.mod_analyses if m.tier and m.tier <= 2)
        if good_mod_count >= 3 and (crafting.open_prefixes > 0 or crafting.open_suffixes > 0):
            suggestions.append(ImprovementSuggestion(
                action="Exalt Slam",
                description="Slam for random high-tier mod (risky but high reward)",
                cost_estimate="~1 divine",
                expected_benefit="Potentially valuable mod",
                risk_level="high",
                priority=3,
            ))

        # Low quality suggestions
        low_rolls = [m for m in crafting.mod_analyses if m.roll_quality < 40 and m.tier and m.tier >= 3]
        if low_rolls and not crafting.divine_recommended:
            suggestions.append(ImprovementSuggestion(
                action="Reroll/Replace",
                description="Consider finding similar item with better rolls",
                cost_estimate="Variable",
                expected_benefit="Better base stats",
                risk_level="low",
                priority=4,
            ))

        # Sort by priority
        suggestions.sort(key=lambda x: x.priority)
        analysis.suggestions = suggestions[:4]  # Top 4

        # Crafting path
        if crafting.crafting_value in ("high", "very high"):
            steps = []
            if crafting.divine_recommended:
                steps.append("Divine for better rolls")
            if crafting.open_prefixes > 0 or crafting.open_suffixes > 0:
                steps.append("Benchcraft open slots")
            if good_mod_count >= 3:
                steps.append("Consider slam/Aisling if budget allows")
            analysis.crafting_path = " -> ".join(steps) if steps else "Item is well-crafted"
        else:
            analysis.crafting_path = "Limited crafting potential"

        return analysis

    async def _get_ai_insight_async(
        self,
        item: "ParsedItem",
        crafting: Optional["CraftingAnalysis"],
    ) -> str:
        """Get AI-generated insight (async)."""
        if not self._ai_provider:
            return ""

        # Build prompt
        item_text = self._format_item_for_prompt(item)
        mod_details = self._format_mods_for_prompt(crafting) if crafting else "No mod analysis"

        quality = crafting.mod_analyses[0].roll_quality if crafting and crafting.mod_analyses else 50
        open_slots = f"{crafting.open_prefixes}P/{crafting.open_suffixes}S" if crafting else "Unknown"
        divine_pot = crafting.get_divine_summary() if crafting else "Unknown"
        craft_val = crafting.crafting_value if crafting else "unknown"

        prompt = IMPROVEMENT_PROMPT_TEMPLATE.format(
            item_text=item_text,
            quality_percent=quality,
            open_slots=open_slots,
            divine_potential=divine_pot,
            crafting_value=craft_val,
            mod_details=mod_details,
        )

        try:
            # Call AI provider
            response = await self._ai_provider.generate_async(prompt)
            return str(response) if response else ""
        except Exception as e:
            logger.debug(f"AI generation failed: {e}")
            return ""

    def _format_item_for_prompt(self, item: "ParsedItem") -> str:
        """Format item for AI prompt."""
        lines = []

        name = getattr(item, 'name', '') or ''
        base = getattr(item, 'base_type', '') or ''
        rarity = getattr(item, 'rarity', '') or ''
        ilvl = getattr(item, 'item_level', 0) or 0

        if name:
            lines.append(name)
        if base:
            lines.append(base)
        lines.append(f"Rarity: {rarity}")
        lines.append(f"Item Level: {ilvl}")

        lines.append("--------")

        explicits = getattr(item, 'explicits', []) or []
        for mod in explicits:
            lines.append(mod)

        return "\n".join(lines)

    def _format_mods_for_prompt(self, crafting: "CraftingAnalysis") -> str:
        """Format mod analysis for AI prompt."""
        lines = []
        for mod in crafting.mod_analyses:
            tier = mod.tier_label or "??"
            stat = (mod.stat_type or "unknown").replace("_", " ").title()
            val = mod.current_value or 0
            quality = mod.roll_quality
            lines.append(f"- {tier} {stat}: {val} ({quality:.0f}% of tier range)")
        return "\n".join(lines) if lines else "No mods detected"

    def _parse_ai_response(self, analysis: ImprovementAnalysis, response: str) -> None:
        """Parse AI response and update analysis."""
        if not response:
            return

        # Extract summary
        if "SUMMARY:" in response:
            try:
                summary_line = response.split("SUMMARY:")[1].split("\n")[0].strip()
                if summary_line:
                    analysis.summary = summary_line
            except (IndexError, ValueError):
                pass

        # Extract crafting path
        if "CRAFTING PATH:" in response:
            try:
                path_line = response.split("CRAFTING PATH:")[1].split("\n")[0].strip()
                if path_line:
                    analysis.crafting_path = path_line
            except (IndexError, ValueError):
                pass


def get_quick_improvement_tips(
    item: "ParsedItem",
    crafting_analysis: Optional["CraftingAnalysis"] = None,
) -> List[str]:
    """
    Get quick improvement tips without AI.

    Args:
        item: Parsed item
        crafting_analysis: Pre-computed analysis (optional)

    Returns:
        List of improvement tip strings
    """
    advisor = AIImprovementAdvisor()
    analysis = advisor.get_suggestions(item, crafting_analysis)

    tips = []
    for suggestion in analysis.suggestions[:3]:
        tips.append(f"{suggestion.action}: {suggestion.description}")

    return tips


# Testing
if __name__ == "__main__":
    from core.item_parser import ParsedItem
    from core.crafting_potential import analyze_crafting_potential

    # Create a test item
    test_item = ParsedItem(
        raw_text="Test Ring",
        name="Glyph Coil",
        base_type="Two-Stone Ring",
        rarity="Rare",
        item_level=85,
        explicits=[
            "+78 to Maximum Life",
            "+42% to Fire Resistance",
            "+35% to Cold Resistance",
        ],
    )

    print("=== AI Improvement Advisor Test ===\n")

    # Get crafting analysis
    crafting = analyze_crafting_potential(test_item)
    print(f"Quality: {crafting.crafting_value}")
    print(f"Open slots: {crafting.open_prefixes}P/{crafting.open_suffixes}S")
    print()

    # Get suggestions
    advisor = AIImprovementAdvisor()
    analysis = advisor.get_suggestions(test_item, crafting)

    print(f"Summary: {analysis.summary}")
    print(f"Quality: {analysis.item_quality_percent:.0f}%")
    print(f"Crafting Path: {analysis.crafting_path}")
    print()

    print("Suggestions:")
    for i, sug in enumerate(analysis.suggestions, 1):
        print(f"  {i}. {sug.action}: {sug.description}")
        print(f"     Cost: {sug.cost_estimate}, Benefit: {sug.expected_benefit}")
        print()
