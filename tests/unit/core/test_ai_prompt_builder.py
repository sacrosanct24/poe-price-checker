"""
Unit tests for AI prompt builder.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from core.ai_prompt_builder import (
    PromptContext,
    AIPromptBuilder,
    get_prompt_builder,
    FALLBACK_PROMPT,
)


class TestPromptContext:
    """Tests for PromptContext dataclass."""

    def test_create_context(self):
        """Test creating a PromptContext."""
        context = PromptContext(
            item_text="Rarity: Unique\nHeadhunter",
            price_results=[{"item_name": "Headhunter", "chaos_value": 5000}],
        )
        assert context.item_text == "Rarity: Unique\nHeadhunter"
        assert len(context.price_results) == 1
        assert context.parsed_item is None

    def test_with_parsed_item(self):
        """Test with parsed_item."""
        context = PromptContext(
            item_text="Test",
            price_results=[],
            parsed_item={"name": "Test Item"},
        )
        assert context.parsed_item == {"name": "Test Item"}


class TestAIPromptBuilder:
    """Tests for AIPromptBuilder."""

    def test_init_default_prompts_dir(self):
        """Test initialization with default prompts directory."""
        builder = AIPromptBuilder()
        assert builder._prompts_dir is not None

    def test_init_custom_prompts_dir(self):
        """Test initialization with custom prompts directory."""
        custom_path = Path("/custom/path")
        builder = AIPromptBuilder(prompts_dir=custom_path)
        assert builder._prompts_dir == custom_path

    def test_format_price_context_empty(self):
        """Test formatting price context with no results."""
        builder = AIPromptBuilder()
        context = builder._format_price_context([])
        assert context == "No price data available."

    def test_format_price_context_single_result(self):
        """Test formatting price context with single result."""
        builder = AIPromptBuilder()
        results = [{
            "item_name": "Test Item",
            "chaos_value": 100.0,
            "source": "poe.ninja",
        }]
        context = builder._format_price_context(results)
        assert "Test Item" in context
        assert "100" in context
        assert "poe.ninja" in context

    def test_format_price_context_multiple_results(self):
        """Test formatting price context with multiple results."""
        builder = AIPromptBuilder()
        results = [
            {"item_name": "Item 1", "chaos_value": 50.0, "source": "poe.ninja"},
            {"item_name": "Item 2", "chaos_value": 75.0, "source": "poe.watch"},
        ]
        context = builder._format_price_context(results)
        assert "Item 1" in context
        assert "Item 2" in context
        assert "poe.ninja" in context
        assert "poe.watch" in context

    def test_format_price_context_fractional_value(self):
        """Test formatting price context with fractional values."""
        builder = AIPromptBuilder()
        results = [{"chaos_value": 0.25, "source": "test"}]
        context = builder._format_price_context(results)
        assert "0.25" in context

    def test_build_item_analysis_prompt_with_fallback(self):
        """Test building prompt uses fallback when template not found."""
        builder = AIPromptBuilder(prompts_dir=Path("/nonexistent"))
        context = PromptContext(
            item_text="Test Item Text",
            price_results=[{"chaos_value": 100, "source": "test"}],
        )

        prompt = builder.build_item_analysis_prompt(context)

        # Should use fallback prompt
        assert "Test Item Text" in prompt
        assert "100" in prompt

    def test_get_system_prompt(self):
        """Test getting the system prompt."""
        builder = AIPromptBuilder()
        system_prompt = builder.get_system_prompt()

        assert "Path of Exile" in system_prompt
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 50

    def test_clear_cache(self):
        """Test clearing the template cache."""
        builder = AIPromptBuilder()
        builder._template_cache["test"] = "cached"
        builder.clear_cache()
        assert len(builder._template_cache) == 0


class TestGetPromptBuilder:
    """Tests for get_prompt_builder factory function."""

    def test_returns_builder_instance(self):
        """Test that factory returns AIPromptBuilder instance."""
        builder = get_prompt_builder()
        assert isinstance(builder, AIPromptBuilder)

    def test_returns_cached_instance(self):
        """Test that factory returns the same cached instance."""
        builder1 = get_prompt_builder()
        builder2 = get_prompt_builder()
        assert builder1 is builder2


class TestPromptBuilderIntegration:
    """Integration tests for prompt building."""

    def test_full_prompt_flow(self):
        """Test complete prompt building flow."""
        builder = AIPromptBuilder()

        # Simulate item data
        context = PromptContext(
            item_text="Rarity: Unique\nHeadhunter\nLeather Belt",
            price_results=[
                {
                    "item_name": "Headhunter",
                    "chaos_value": 5000.0,
                    "divine_value": 25.0,
                    "source": "poe.ninja",
                }
            ],
        )

        prompt = builder.build_item_analysis_prompt(context)

        # Verify key information is present
        assert "Headhunter" in prompt
        assert len(prompt) > 100

    def test_prompt_handles_special_characters(self):
        """Test prompt handles special characters in item text."""
        builder = AIPromptBuilder()

        context = PromptContext(
            item_text='Item with "quotes" and other chars',
            price_results=[],
        )

        prompt = builder.build_item_analysis_prompt(context)

        # Should not raise and should contain the text
        assert "quotes" in prompt or "Item with" in prompt

    def test_prompt_handles_unicode(self):
        """Test prompt handles unicode characters."""
        builder = AIPromptBuilder()

        context = PromptContext(
            item_text="Item with unicode: \u2605 stars",
            price_results=[],
        )

        prompt = builder.build_item_analysis_prompt(context)

        # Should not raise
        assert isinstance(prompt, str)

    def test_prompt_handles_empty_item_name(self):
        """Test prompt handles results without item_name."""
        builder = AIPromptBuilder()
        results = [{"chaos_value": 50, "source": "test"}]

        context = builder._format_price_context(results)
        assert "50" in context
        assert "test" in context

    def test_prompt_no_values(self):
        """Test price context with results but no valid values."""
        builder = AIPromptBuilder()
        results = [{"item_name": "Test", "source": "test"}]  # No chaos_value

        context = builder._format_price_context(results)
        assert "no values" in context.lower() or "no price" in context.lower()
