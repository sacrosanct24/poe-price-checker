"""
Unit tests for AI prompt builder.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from core.ai_prompt_builder import (
    PromptContext,
    AIPromptBuilder,
    get_prompt_builder,
    FALLBACK_PROMPT,
    UPGRADE_ADVISOR_PROMPT,
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


class TestPromptContextAllFields:
    """Additional tests for PromptContext dataclass."""

    def test_all_fields_set(self):
        """Test creating context with all optional fields."""
        mock_build_summary = Mock()
        context = PromptContext(
            item_text="Test item",
            price_results=[{"chaos_value": 100}],
            parsed_item={"name": "Test"},
            league="Settlers",
            build_name="My Build",
            build_summary=mock_build_summary,
            slot="Helmet",
            current_item_text="Current helmet",
        )

        assert context.league == "Settlers"
        assert context.build_name == "My Build"
        assert context.build_summary is mock_build_summary
        assert context.slot == "Helmet"
        assert context.current_item_text == "Current helmet"

    def test_default_values(self):
        """Test default values for optional fields."""
        context = PromptContext(
            item_text="Test",
            price_results=[],
        )

        assert context.league == ""
        assert context.build_name == ""
        assert context.build_summary is None
        assert context.slot == ""
        assert context.current_item_text == ""


class TestLoadTemplate:
    """Tests for _load_template method."""

    def test_load_template_uses_cache(self):
        """Template should be loaded from cache on second call."""
        builder = AIPromptBuilder()
        builder._template_cache["test.txt"] = "cached template content"

        result = builder._load_template("test.txt")

        assert result == "cached template content"

    def test_load_template_reads_file(self, tmp_path):
        """Template should be read from file."""
        template_path = tmp_path / "test_template.txt"
        template_path.write_text("This is a {item_text} template", encoding="utf-8")

        builder = AIPromptBuilder(prompts_dir=tmp_path)
        result = builder._load_template("test_template.txt")

        assert result == "This is a {item_text} template"
        assert "test_template.txt" in builder._template_cache

    def test_load_template_file_not_found(self):
        """Missing template file should return fallback."""
        builder = AIPromptBuilder(prompts_dir=Path("/nonexistent"))
        result = builder._load_template("missing.txt")

        assert result == FALLBACK_PROMPT

    def test_load_template_read_error(self, tmp_path):
        """Error reading file should return fallback."""
        builder = AIPromptBuilder(prompts_dir=tmp_path)

        # Patch read_text to raise an exception
        with patch.object(Path, 'read_text', side_effect=PermissionError("Access denied")):
            result = builder._load_template("error.txt")

        assert result == FALLBACK_PROMPT


class TestFormatBuildContext:
    """Tests for _format_build_context method."""

    def test_format_build_context_none(self):
        """None build_summary should return empty string."""
        builder = AIPromptBuilder()
        result = builder._format_build_context(None)
        assert result == ""

    def test_format_build_context_compact(self):
        """Compact mode should use to_compact_context."""
        mock_summary = Mock()
        mock_summary.to_compact_context.return_value = "Compact build info"

        builder = AIPromptBuilder()
        result = builder._format_build_context(mock_summary, compact=True)

        assert "Compact build info" in result
        mock_summary.to_compact_context.assert_called_once()

    def test_format_build_context_full(self):
        """Full mode should include all build details."""
        mock_summary = Mock()
        mock_summary.ascendancy = "Elementalist"
        mock_summary.class_name = "Witch"
        mock_summary.level = 95
        mock_summary.main_skill = "Arc"
        mock_summary.playstyle = "Spell Caster"
        mock_summary.damage_type = "Lightning"
        mock_summary.life = 5000
        mock_summary.energy_shield = 0
        mock_summary.fire_res = 75
        mock_summary.cold_res = 75
        mock_summary.lightning_res = 75
        mock_summary.chaos_res = -60
        mock_summary.total_dps = 1000000
        mock_summary.upgrade_priorities = ["Helmet", "Boots", "Ring"]

        builder = AIPromptBuilder()
        result = builder._format_build_context(mock_summary, compact=False)

        assert "Elementalist" in result
        assert "95" in result
        assert "Arc" in result
        assert "Spell Caster" in result
        assert "5,000" in result  # Life formatted
        assert "1,000,000" in result  # DPS formatted
        assert "Helmet" in result

    def test_format_build_context_no_ascendancy(self):
        """Should fallback to class_name if no ascendancy."""
        mock_summary = Mock()
        mock_summary.ascendancy = None
        mock_summary.class_name = "Witch"
        mock_summary.level = 50
        mock_summary.main_skill = "Arc"
        mock_summary.playstyle = None
        mock_summary.damage_type = None
        mock_summary.life = 0
        mock_summary.energy_shield = 0
        mock_summary.fire_res = 75
        mock_summary.cold_res = 75
        mock_summary.lightning_res = 75
        mock_summary.chaos_res = 0
        mock_summary.total_dps = 0
        mock_summary.upgrade_priorities = []

        builder = AIPromptBuilder()
        result = builder._format_build_context(mock_summary)

        assert "Witch" in result

    def test_format_build_context_es_build(self):
        """ES build should show ES stat."""
        mock_summary = Mock()
        mock_summary.ascendancy = "Occultist"
        mock_summary.class_name = "Witch"
        mock_summary.level = 90
        mock_summary.main_skill = "Bane"
        mock_summary.playstyle = "DoT"
        mock_summary.damage_type = "Chaos"
        mock_summary.life = 2000
        mock_summary.energy_shield = 8000
        mock_summary.fire_res = 75
        mock_summary.cold_res = 75
        mock_summary.lightning_res = 75
        mock_summary.chaos_res = 75
        mock_summary.total_dps = 500000
        mock_summary.upgrade_priorities = []

        builder = AIPromptBuilder()
        result = builder._format_build_context(mock_summary)

        assert "8,000" in result  # ES formatted
        assert "2,000" in result  # Life formatted


class TestBuildItemAnalysisPrompt:
    """Tests for build_item_analysis_prompt method."""

    def test_with_custom_template(self):
        """Custom template should be used."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[{"chaos_value": 100, "source": "test"}],
        )

        custom_template = "Custom: {item_text} - Price: {price_context}"
        result = builder.build_item_analysis_prompt(context, custom_template=custom_template)

        assert "Custom: Test Item" in result
        assert "100" in result

    def test_with_league_and_build_name(self):
        """League and build name should be included."""
        builder = AIPromptBuilder(prompts_dir=Path("/nonexistent"))  # Use fallback
        context = PromptContext(
            item_text="Test",
            price_results=[],
            league="Settlers",
            build_name="Lightning Arrow Deadeye",
        )

        result = builder.build_item_analysis_prompt(context)

        assert "Settlers" in result
        assert "Lightning Arrow Deadeye" in result

    def test_default_values_for_missing_fields(self):
        """Default values should be used when fields are empty."""
        builder = AIPromptBuilder(prompts_dir=Path("/nonexistent"))
        context = PromptContext(
            item_text="Test",
            price_results=[],
            league="",
            build_name="",
        )

        result = builder.build_item_analysis_prompt(context)

        assert "unknown league" in result
        assert "unspecified build" in result

    def test_key_error_fallback(self):
        """KeyError in template with only known placeholders should work."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[{"chaos_value": 50, "source": "test"}],
        )

        # Template with only known placeholders but missing some optional ones
        # The fallback covers item_text, price_context, build_context
        template = "Item: {item_text} Price: {price_context} Build: {build_context}"
        result = builder.build_item_analysis_prompt(context, custom_template=template)

        # Should contain the basic info
        assert "Test Item" in result
        assert "50" in result

    def test_key_error_raised_on_bad_template(self):
        """KeyError raised when template has truly unknown placeholder."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[],
        )

        # Template with unknown placeholder that can't be handled
        bad_template = "Item: {item_text} Unknown: {unknown_field}"
        with pytest.raises(KeyError):
            builder.build_item_analysis_prompt(context, custom_template=bad_template)


class TestBuildUpgradePrompt:
    """Tests for build_upgrade_prompt method."""

    def test_basic_upgrade_prompt(self):
        """Basic upgrade prompt should include all sections."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="New Helmet",
            price_results=[{"chaos_value": 500, "source": "trade"}],
            slot="Helmet",
            current_item_text="Old Helmet",
        )

        result = builder.build_upgrade_prompt(context)

        assert "New Helmet" in result
        assert "Old Helmet" in result
        assert "Helmet" in result  # slot
        assert "500" in result

    def test_upgrade_prompt_with_build_summary(self):
        """Upgrade prompt should include build markdown."""
        mock_summary = Mock()
        mock_summary.to_markdown.return_value = "# Build Summary\nDPS: 1M"

        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[],
            build_summary=mock_summary,
            slot="Boots",
            current_item_text="Current boots",
        )

        result = builder.build_upgrade_prompt(context)

        assert "Build Summary" in result
        assert "DPS: 1M" in result
        mock_summary.to_markdown.assert_called_once()

    def test_upgrade_prompt_no_build_summary(self):
        """Upgrade prompt should handle missing build summary."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[],
            build_summary=None,
            slot="Ring",
        )

        result = builder.build_upgrade_prompt(context)

        assert "No build data available" in result

    def test_upgrade_prompt_no_current_item(self):
        """Upgrade prompt should handle missing current item."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test Item",
            price_results=[],
            slot="Amulet",
            current_item_text="",
        )

        result = builder.build_upgrade_prompt(context)

        assert "(No current item)" in result

    def test_upgrade_prompt_custom_template(self):
        """Custom template should be used for upgrade prompt."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="New Item",
            price_results=[],
            slot="Belt",
            current_item_text="Old Belt",
        )

        custom_template = "Slot: {slot}, New: {item_text}, Old: {current_item}, Price: {price_context}, Build: {build_context}"
        result = builder.build_upgrade_prompt(context, custom_template=custom_template)

        assert "Slot: Belt" in result
        assert "New: New Item" in result
        assert "Old: Old Belt" in result

    def test_upgrade_prompt_key_error_returns_template(self):
        """KeyError in upgrade template should return template as-is."""
        builder = AIPromptBuilder()
        context = PromptContext(
            item_text="Test",
            price_results=[],
        )

        bad_template = "Item: {item_text} Unknown: {unknown_field}"
        result = builder.build_upgrade_prompt(context, custom_template=bad_template)

        # Should return the template unchanged
        assert "{unknown_field}" in result


class TestGetPromptBuilderSingleton:
    """Tests for get_prompt_builder singleton."""

    def test_resets_correctly(self):
        """Test singleton can be reset for testing."""
        import core.ai_prompt_builder as module

        # Reset singleton
        module._default_builder = None

        builder1 = get_prompt_builder()
        assert isinstance(builder1, AIPromptBuilder)

        builder2 = get_prompt_builder()
        assert builder1 is builder2

        # Reset for other tests
        module._default_builder = None


class TestFallbackPromptTemplate:
    """Tests for fallback prompt template."""

    def test_fallback_prompt_has_placeholders(self):
        """Fallback prompt should have required placeholders."""
        assert "{item_text}" in FALLBACK_PROMPT
        assert "{price_context}" in FALLBACK_PROMPT
        assert "{league}" in FALLBACK_PROMPT
        assert "{build_name}" in FALLBACK_PROMPT
        assert "{build_context}" in FALLBACK_PROMPT

    def test_upgrade_advisor_prompt_has_placeholders(self):
        """Upgrade advisor prompt should have required placeholders."""
        assert "{item_text}" in UPGRADE_ADVISOR_PROMPT
        assert "{price_context}" in UPGRADE_ADVISOR_PROMPT
        assert "{build_context}" in UPGRADE_ADVISOR_PROMPT
        assert "{slot}" in UPGRADE_ADVISOR_PROMPT
        assert "{current_item}" in UPGRADE_ADVISOR_PROMPT
