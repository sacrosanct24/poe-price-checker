"""
AI prompt builder for item analysis.

Constructs prompts for AI providers with item and price context.
Supports template-based prompts that can be customized without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "data" / "prompts"

# Default template filename
DEFAULT_TEMPLATE = "item_analysis.txt"

# Fallback prompt if template file is missing
FALLBACK_PROMPT = """Analyze this Path of Exile item and provide a brief assessment:

PLAYER CONTEXT:
- League: {league}
- Current build: {build_name}

ITEM:
{item_text}

PRICE CONTEXT:
{price_context}

Provide a concise analysis (3-5 paragraphs) covering:
- Item type and key properties
- Whether this is useful for the player's build ({build_name})
- Other suitable builds/classes
- Price fairness in {league} league
- Notable strengths or weaknesses"""


@dataclass
class PromptContext:
    """Context data for building an AI prompt.

    Attributes:
        item_text: The raw item text (from clipboard or game).
        price_results: List of price check results from various sources.
        parsed_item: Optional parsed item data for additional context.
        league: Current league name (e.g., "Settlers", "Standard").
        build_name: Player's current build name for context.
    """

    item_text: str
    price_results: List[Dict[str, Any]]
    parsed_item: Optional[Any] = None
    league: str = ""
    build_name: str = ""


class AIPromptBuilder:
    """Builds prompts for AI item analysis.

    Loads templates from the prompts directory and substitutes
    item/price context into placeholders.

    Example:
        >>> builder = AIPromptBuilder()
        >>> context = PromptContext(
        ...     item_text="Rarity: Unique\\nHeadhunter...",
        ...     price_results=[{"chaos_value": 100}],
        ... )
        >>> prompt = builder.build_item_analysis_prompt(context)
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize the prompt builder.

        Args:
            prompts_dir: Directory containing prompt templates.
                        Defaults to data/prompts/.
        """
        self._prompts_dir = prompts_dir or PROMPTS_DIR
        self._template_cache: Dict[str, str] = {}

    def _load_template(self, template_name: str) -> str:
        """Load a prompt template from file.

        Args:
            template_name: Name of the template file.

        Returns:
            Template content, or fallback if file not found.
        """
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        template_path = self._prompts_dir / template_name
        try:
            content = template_path.read_text(encoding="utf-8")
            self._template_cache[template_name] = content
            logger.debug(f"Loaded prompt template: {template_path}")
            return content
        except FileNotFoundError:
            logger.warning(
                f"Prompt template not found: {template_path}, using fallback"
            )
            return FALLBACK_PROMPT
        except Exception as e:
            logger.error(f"Error loading prompt template: {e}")
            return FALLBACK_PROMPT

    def _format_price_context(self, price_results: List[Dict[str, Any]]) -> str:
        """Format price results into readable context.

        Args:
            price_results: List of price check results.

        Returns:
            Formatted price context string.
        """
        if not price_results:
            return "No price data available."

        lines = []
        for result in price_results:
            source = result.get("source", "unknown")
            chaos_value = result.get("chaos_value")
            item_name = result.get("item_name", "")

            if chaos_value is not None:
                # Format value with appropriate precision
                if chaos_value >= 1:
                    value_str = f"{chaos_value:.0f} chaos"
                else:
                    value_str = f"{chaos_value:.2f} chaos"

                if item_name:
                    lines.append(f"- {item_name}: {value_str} ({source})")
                else:
                    lines.append(f"- {value_str} ({source})")

        if not lines:
            return "Price check returned no values."

        return "\n".join(lines)

    def build_item_analysis_prompt(
        self,
        context: PromptContext,
        template_name: str = DEFAULT_TEMPLATE,
        custom_template: Optional[str] = None,
    ) -> str:
        """Build a complete prompt for item analysis.

        Args:
            context: The prompt context containing item and price data.
            template_name: Name of the template file to use (if no custom_template).
            custom_template: Optional custom template string to use instead of file.

        Returns:
            Fully formatted prompt ready to send to AI.
        """
        # Use custom template if provided, otherwise load from file
        if custom_template:
            template = custom_template
        else:
            template = self._load_template(template_name)

        # Format price context
        price_context = self._format_price_context(context.price_results)

        # Build substitution dict with all placeholders
        substitutions = {
            "item_text": context.item_text.strip(),
            "price_context": price_context,
            "league": context.league or "unknown league",
            "build_name": context.build_name or "unspecified build",
        }

        # Substitute placeholders
        try:
            prompt = template.format(**substitutions)
        except KeyError as e:
            logger.warning(f"Unknown placeholder in template: {e}")
            # Fall back to basic substitution
            prompt = template.format(
                item_text=substitutions["item_text"],
                price_context=substitutions["price_context"],
            )

        return prompt

    def get_system_prompt(self) -> str:
        """Get the system prompt for AI context.

        Returns:
            System prompt string for AI provider.
        """
        return (
            "You are an expert Path of Exile player and economy analyst. "
            "You help players understand their items, evaluate prices, "
            "and make informed trading decisions. Be concise and practical."
        )

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()
        logger.debug("Prompt template cache cleared")


# Module-level convenience instance
_default_builder: Optional[AIPromptBuilder] = None


def get_prompt_builder() -> AIPromptBuilder:
    """Get the default prompt builder instance.

    Returns:
        The shared AIPromptBuilder instance.
    """
    global _default_builder
    if _default_builder is None:
        _default_builder = AIPromptBuilder()
    return _default_builder
