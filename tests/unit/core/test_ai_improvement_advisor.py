"""
Tests for core/ai_improvement_advisor.py

Tests the AI-powered improvement advisor including:
- ImprovementSuggestion dataclass
- ImprovementAnalysis dataclass
- AIImprovementAdvisor class
- Suggestion generation from crafting analysis
- AI response parsing
"""
from unittest.mock import MagicMock, AsyncMock

from core.ai_improvement_advisor import (
    ImprovementSuggestion,
    ImprovementAnalysis,
    AIImprovementAdvisor,
    get_quick_improvement_tips,
    IMPROVEMENT_PROMPT_TEMPLATE,
)


class TestImprovementSuggestion:
    """Tests for ImprovementSuggestion dataclass."""

    def test_all_fields(self):
        """All fields set correctly."""
        suggestion = ImprovementSuggestion(
            action="Divine Orb",
            description="Re-roll life mod",
            cost_estimate="~1 divine",
            expected_benefit="+20 life potential",
            risk_level="low",
            priority=1,
        )
        assert suggestion.action == "Divine Orb"
        assert suggestion.description == "Re-roll life mod"
        assert suggestion.cost_estimate == "~1 divine"
        assert suggestion.expected_benefit == "+20 life potential"
        assert suggestion.risk_level == "low"
        assert suggestion.priority == 1

    def test_default_values(self):
        """Default risk and priority values."""
        suggestion = ImprovementSuggestion(
            action="Craft",
            description="Add resistance",
            cost_estimate="~2c",
            expected_benefit="Better stats",
        )
        assert suggestion.risk_level == "low"
        assert suggestion.priority == 1


class TestImprovementAnalysis:
    """Tests for ImprovementAnalysis dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        analysis = ImprovementAnalysis()
        assert analysis.item_quality_percent == 0.0
        assert analysis.summary == ""
        assert analysis.suggestions == []
        assert analysis.ai_insight == ""
        assert analysis.crafting_path == ""
        assert analysis.value_if_improved == ""

    def test_with_suggestions(self):
        """Analysis with suggestions."""
        suggestion = ImprovementSuggestion(
            action="Divine",
            description="Re-roll",
            cost_estimate="1d",
            expected_benefit="Better rolls",
        )
        analysis = ImprovementAnalysis(
            item_quality_percent=75.0,
            summary="Good item",
            suggestions=[suggestion],
            crafting_path="Divine -> Craft suffix",
        )
        assert analysis.item_quality_percent == 75.0
        assert len(analysis.suggestions) == 1
        assert analysis.suggestions[0].action == "Divine"


class TestAIImprovementAdvisor:
    """Tests for AIImprovementAdvisor class."""

    def test_initialization_no_provider(self):
        """Advisor initializes without provider."""
        advisor = AIImprovementAdvisor()
        assert advisor._ai_provider is None

    def test_initialization_with_provider(self):
        """Advisor initializes with provider."""
        mock_provider = MagicMock()
        advisor = AIImprovementAdvisor(ai_provider=mock_provider)
        assert advisor._ai_provider == mock_provider

    def test_set_provider(self):
        """Set provider after initialization."""
        advisor = AIImprovementAdvisor()
        mock_provider = MagicMock()
        advisor.set_provider(mock_provider)
        assert advisor._ai_provider == mock_provider

    def test_get_suggestions_returns_analysis(self):
        """Sync get_suggestions returns ImprovementAnalysis."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"

        advisor = AIImprovementAdvisor()
        analysis = advisor.get_suggestions(item)

        assert isinstance(analysis, ImprovementAnalysis)

    def test_get_suggestions_with_crafting_analysis(self):
        """Get suggestions using provided crafting analysis."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"

        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(
                roll_quality=80.0,
                divine_potential=10,
                tier=2,
                stat_type="life",
                current_value=92,
                max_roll=99,
            )
        ]
        crafting.divine_recommended = True
        crafting.open_prefixes = 0
        crafting.open_suffixes = 1
        crafting.crafting_value = "high"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor.get_suggestions(item, crafting)

        assert analysis.item_quality_percent == 80.0
        assert "good" in analysis.summary.lower() or "80" in analysis.summary

    def test_quality_calculation(self):
        """Item quality calculated from mod analyses."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(roll_quality=90.0, divine_potential=0, tier=1, stat_type="life", current_value=99, max_roll=99),
            MagicMock(roll_quality=70.0, divine_potential=5, tier=2, stat_type="resist", current_value=40, max_roll=45),
        ]
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "medium"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        # Average of 90 and 70 = 80
        assert analysis.item_quality_percent == 80.0

    def test_quality_description_excellent(self):
        """Excellent quality items described correctly."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(roll_quality=90.0, divine_potential=0, tier=1, stat_type="life", current_value=99, max_roll=99),
        ]
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "medium"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert "excellent" in analysis.summary.lower()

    def test_quality_description_below_average(self):
        """Below average items described correctly."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(roll_quality=30.0, divine_potential=20, tier=3, stat_type="life", current_value=60, max_roll=80),
        ]
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert "below average" in analysis.summary.lower()

    def test_divine_suggestion_generated(self):
        """Divine suggestion generated when recommended."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 50.0
        mod.divine_potential = 20
        mod.tier = 2
        mod.stat_type = "life"
        mod.current_value = 80
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "high"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        divine_suggestions = [s for s in analysis.suggestions if "Divine" in s.action]
        assert len(divine_suggestions) == 1
        assert "+20" in divine_suggestions[0].expected_benefit

    def test_prefix_craft_suggestion(self):
        """Prefix craft suggestion when open slots."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = []
        crafting.divine_recommended = False
        crafting.open_prefixes = 2
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        prefix_suggestions = [s for s in analysis.suggestions if "Prefix" in s.action]
        assert len(prefix_suggestions) == 1
        assert "2 open" in prefix_suggestions[0].description

    def test_suffix_craft_suggestion(self):
        """Suffix craft suggestion when open slots."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = []
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 3
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        suffix_suggestions = [s for s in analysis.suggestions if "Suffix" in s.action]
        assert len(suffix_suggestions) == 1
        assert "3 open" in suffix_suggestions[0].description

    def test_exalt_suggestion_for_high_value_bases(self):
        """Exalt slam suggestion for items with good mods."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(roll_quality=90.0, divine_potential=0, tier=1, stat_type="life", current_value=99, max_roll=99),
            MagicMock(roll_quality=85.0, divine_potential=0, tier=2, stat_type="fire_res", current_value=45, max_roll=48),
            MagicMock(roll_quality=80.0, divine_potential=0, tier=2, stat_type="cold_res", current_value=42, max_roll=48),
        ]
        crafting.divine_recommended = False
        crafting.open_prefixes = 1
        crafting.open_suffixes = 0
        crafting.crafting_value = "very high"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        exalt_suggestions = [s for s in analysis.suggestions if "Exalt" in s.action]
        assert len(exalt_suggestions) == 1
        assert exalt_suggestions[0].risk_level == "high"

    def test_suggestions_sorted_by_priority(self):
        """Suggestions sorted by priority."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 50.0
        mod.divine_potential = 20
        mod.tier = 2
        mod.stat_type = "life"
        mod.current_value = 80
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 1
        crafting.open_suffixes = 1
        crafting.crafting_value = "high"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        # Should have multiple suggestions, sorted by priority
        priorities = [s.priority for s in analysis.suggestions]
        assert priorities == sorted(priorities)

    def test_crafting_path_high_value(self):
        """Crafting path generated for high value items."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 80.0
        mod.divine_potential = 10
        mod.tier = 2
        mod.stat_type = "life"
        mod.current_value = 90
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 1
        crafting.open_suffixes = 0
        crafting.crafting_value = "high"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert "Divine" in analysis.crafting_path
        assert "Benchcraft" in analysis.crafting_path

    def test_crafting_path_low_value(self):
        """Limited crafting path for low value items."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = []
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert "Limited" in analysis.crafting_path

    def test_empty_mod_analysis_default_quality(self):
        """Empty mod analysis uses default quality."""
        item = MagicMock()

        crafting = MagicMock()
        crafting.mod_analyses = []
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert analysis.item_quality_percent == 50.0


class TestAIResponseParsing:
    """Tests for AI response parsing."""

    def test_parse_summary(self):
        """Parse SUMMARY from AI response."""
        response = """SUMMARY: This ring has excellent potential for improvement.

SUGGESTIONS:
1. Divine: Re-roll life

CRAFTING PATH: Divine first, then craft suffix"""

        advisor = AIImprovementAdvisor()
        analysis = ImprovementAnalysis()
        advisor._parse_ai_response(analysis, response)

        assert "excellent potential" in analysis.summary

    def test_parse_crafting_path(self):
        """Parse CRAFTING PATH from AI response."""
        response = """SUMMARY: Good item.

CRAFTING PATH: Divine -> Benchcraft resistance -> Consider Aisling"""

        advisor = AIImprovementAdvisor()
        analysis = ImprovementAnalysis()
        advisor._parse_ai_response(analysis, response)

        assert "Divine" in analysis.crafting_path
        assert "Benchcraft" in analysis.crafting_path

    def test_parse_empty_response(self):
        """Empty response doesn't crash."""
        advisor = AIImprovementAdvisor()
        analysis = ImprovementAnalysis()
        analysis.summary = "Original summary"

        advisor._parse_ai_response(analysis, "")

        assert analysis.summary == "Original summary"

    def test_parse_malformed_response(self):
        """Malformed response handled gracefully."""
        response = "Random text without expected sections"

        advisor = AIImprovementAdvisor()
        analysis = ImprovementAnalysis()
        analysis.summary = "Original"

        advisor._parse_ai_response(analysis, response)

        # Should not crash, keeps original values
        assert analysis.summary == "Original"


class TestItemFormatting:
    """Tests for item formatting methods."""

    def test_format_item_for_prompt(self):
        """Item formatted correctly for AI prompt."""
        item = MagicMock()
        item.name = "Glyph Coil"
        item.base_type = "Two-Stone Ring"
        item.rarity = "Rare"
        item.item_level = 85
        item.explicits = ["+78 to Maximum Life", "+42% to Fire Resistance"]

        advisor = AIImprovementAdvisor()
        formatted = advisor._format_item_for_prompt(item)

        assert "Glyph Coil" in formatted
        assert "Two-Stone Ring" in formatted
        assert "Rare" in formatted
        assert "85" in formatted
        assert "+78 to Maximum Life" in formatted

    def test_format_item_missing_attributes(self):
        """Item with missing attributes handled."""
        item = MagicMock(spec=[])
        # No attributes set

        advisor = AIImprovementAdvisor()
        formatted = advisor._format_item_for_prompt(item)

        # Should not crash, produces some output
        assert isinstance(formatted, str)

    def test_format_mods_for_prompt(self):
        """Mods formatted correctly for AI prompt."""
        crafting = MagicMock()
        crafting.mod_analyses = [
            MagicMock(
                tier_label="T2",
                stat_type="life",
                current_value=92,
                roll_quality=80.0,
            ),
            MagicMock(
                tier_label="T1",
                stat_type="fire_resistance",
                current_value=45,
                roll_quality=95.0,
            ),
        ]

        advisor = AIImprovementAdvisor()
        formatted = advisor._format_mods_for_prompt(crafting)

        assert "T2" in formatted
        assert "Life" in formatted  # Title case
        assert "80%" in formatted
        assert "T1" in formatted
        assert "Fire Resistance" in formatted

    def test_format_mods_empty(self):
        """Empty mod list handled."""
        crafting = MagicMock()
        crafting.mod_analyses = []

        advisor = AIImprovementAdvisor()
        formatted = advisor._format_mods_for_prompt(crafting)

        assert "No mods" in formatted


class TestAsyncMethods:
    """Tests for async methods."""

    def test_get_suggestions_async_returns_analysis(self):
        """Async get_suggestions returns ImprovementAnalysis."""
        import asyncio

        async def run_test():
            item = MagicMock()
            item.explicits = ["+92 to Maximum Life"]
            item.rarity = "Rare"

            advisor = AIImprovementAdvisor()
            analysis = await advisor.get_suggestions_async(item)
            return analysis

        analysis = asyncio.run(run_test())
        assert isinstance(analysis, ImprovementAnalysis)

    def test_get_suggestions_async_with_ai_provider(self):
        """Async method uses AI provider when available."""
        import asyncio

        async def run_test():
            mock_provider = MagicMock()
            mock_provider.generate_async = AsyncMock(return_value="SUMMARY: AI says this is great.\n\nCRAFTING PATH: Buy better item")

            item = MagicMock()
            item.name = "Test"
            item.base_type = "Ring"
            item.rarity = "Rare"
            item.item_level = 85
            item.explicits = ["+92 to Maximum Life"]

            mod_mock = MagicMock()
            mod_mock.roll_quality = 80.0
            mod_mock.tier_label = "T2"
            mod_mock.stat_type = "life"
            mod_mock.current_value = 92
            mod_mock.tier = 2  # Important: explicit integer value
            mod_mock.divine_potential = 5
            mod_mock.max_roll = 99

            crafting = MagicMock()
            crafting.mod_analyses = [mod_mock]
            crafting.open_prefixes = 1
            crafting.open_suffixes = 2
            crafting.divine_recommended = False
            crafting.crafting_value = "medium"
            crafting.get_divine_summary.return_value = "Low potential"

            advisor = AIImprovementAdvisor(ai_provider=mock_provider)
            analysis = await advisor.get_suggestions_async(item, crafting)
            return analysis

        analysis = asyncio.run(run_test())
        assert "AI says" in analysis.summary or analysis.ai_insight != ""

    def test_get_suggestions_async_ai_failure_handled(self):
        """AI failure doesn't crash async method."""
        import asyncio

        async def run_test():
            mock_provider = MagicMock()
            mock_provider.generate_async = AsyncMock(side_effect=Exception("API Error"))

            item = MagicMock()
            item.explicits = ["+92 to Maximum Life"]
            item.rarity = "Rare"

            advisor = AIImprovementAdvisor(ai_provider=mock_provider)
            analysis = await advisor.get_suggestions_async(item)
            return analysis

        analysis = asyncio.run(run_test())
        assert "unavailable" in analysis.ai_insight.lower()


class TestConvenienceFunction:
    """Tests for get_quick_improvement_tips function."""

    def test_returns_list(self):
        """Function returns list of tips."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"

        tips = get_quick_improvement_tips(item)

        assert isinstance(tips, list)

    def test_with_crafting_analysis(self):
        """Function uses provided crafting analysis."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 50.0
        mod.divine_potential = 20
        mod.tier = 2
        mod.stat_type = "life"
        mod.current_value = 80
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 1
        crafting.open_suffixes = 1
        crafting.crafting_value = "high"
        crafting.craft_options = []

        tips = get_quick_improvement_tips(item, crafting)

        assert len(tips) >= 1
        # Tips should include action and description
        assert any("Divine" in tip for tip in tips) or any("Benchcraft" in tip for tip in tips)

    def test_limited_to_three_tips(self):
        """Function returns at most 3 tips."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 40.0
        mod.divine_potential = 30
        mod.tier = 2
        mod.stat_type = "life"
        mod.current_value = 70
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 2
        crafting.open_suffixes = 2
        crafting.crafting_value = "high"
        crafting.craft_options = []

        tips = get_quick_improvement_tips(item, crafting)

        assert len(tips) <= 3


class TestPromptTemplate:
    """Tests for prompt template."""

    def test_template_has_placeholders(self):
        """Template has all required placeholders."""
        assert "{item_text}" in IMPROVEMENT_PROMPT_TEMPLATE
        assert "{quality_percent}" in IMPROVEMENT_PROMPT_TEMPLATE
        assert "{open_slots}" in IMPROVEMENT_PROMPT_TEMPLATE
        assert "{divine_potential}" in IMPROVEMENT_PROMPT_TEMPLATE
        assert "{crafting_value}" in IMPROVEMENT_PROMPT_TEMPLATE
        assert "{mod_details}" in IMPROVEMENT_PROMPT_TEMPLATE

    def test_template_is_valid_format_string(self):
        """Template can be formatted."""
        formatted = IMPROVEMENT_PROMPT_TEMPLATE.format(
            item_text="Test Item",
            quality_percent=75,
            open_slots="1P/2S",
            divine_potential="High",
            crafting_value="medium",
            mod_details="T1 Life: 99",
        )
        assert "Test Item" in formatted
        assert "75" in formatted


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_crafting_analysis(self):
        """None crafting analysis handled."""
        item = MagicMock()
        item.explicits = ["+92 to Maximum Life"]
        item.rarity = "Rare"
        item.fractured_mods = []

        advisor = AIImprovementAdvisor()

        # Should try to generate its own analysis
        analysis = advisor.get_suggestions(item, None)
        assert isinstance(analysis, ImprovementAnalysis)

    def test_mod_with_none_values(self):
        """Mod analysis with None values handled."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 50.0
        mod.divine_potential = 0
        mod.tier = None
        mod.stat_type = None
        mod.current_value = None
        mod.max_roll = None

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = True
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        # Should not crash
        assert isinstance(analysis, ImprovementAnalysis)

    def test_very_high_quality_items(self):
        """100% quality items handled."""
        item = MagicMock()

        mod = MagicMock()
        mod.roll_quality = 100.0
        mod.divine_potential = 0
        mod.tier = 1
        mod.stat_type = "life"
        mod.current_value = 99
        mod.max_roll = 99

        crafting = MagicMock()
        crafting.mod_analyses = [mod]
        crafting.divine_recommended = False
        crafting.open_prefixes = 0
        crafting.open_suffixes = 0
        crafting.crafting_value = "low"
        crafting.craft_options = []

        advisor = AIImprovementAdvisor()
        analysis = advisor._build_from_crafting_analysis(item, crafting)

        assert analysis.item_quality_percent == 100.0
        assert "excellent" in analysis.summary.lower()
