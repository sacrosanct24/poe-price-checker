"""
Tests for core/pricing/models.py - PriceExplanation dataclass.
"""
import json
import pytest
from core.pricing.models import PriceExplanation


class TestPriceExplanationCreation:
    """Tests for PriceExplanation instantiation."""

    def test_default_values(self):
        """PriceExplanation should have sensible defaults."""
        exp = PriceExplanation()

        assert exp.summary == ""
        assert exp.source_name == ""
        assert exp.source_details == ""
        assert exp.confidence == ""
        assert exp.confidence_reason == ""
        assert exp.calculation_method == ""
        assert exp.sample_size == 0
        assert exp.price_spread == ""
        assert exp.stats_used == {}
        assert exp.is_rare_evaluation is False
        assert exp.rare_tier == ""
        assert exp.rare_score == 0
        assert exp.valuable_mods == []
        assert exp.synergies == []
        assert exp.red_flags == []
        assert exp.matches_build is False
        assert exp.build_match_details == ""
        assert exp.adjustments == []

    def test_create_with_basic_fields(self):
        """Can create with basic pricing info."""
        exp = PriceExplanation(
            summary="Price from poe.ninja",
            source_name="poe.ninja",
            confidence="high",
            sample_size=50
        )

        assert exp.summary == "Price from poe.ninja"
        assert exp.source_name == "poe.ninja"
        assert exp.confidence == "high"
        assert exp.sample_size == 50

    def test_create_rare_evaluation(self):
        """Can create with rare item evaluation fields."""
        exp = PriceExplanation(
            is_rare_evaluation=True,
            rare_tier="excellent",
            rare_score=95,
            valuable_mods=["+1 to Maximum Power Charges", "T1 Life"],
            synergies=["Crit + Power Charges"],
            red_flags=["Low ES on ES base"]
        )

        assert exp.is_rare_evaluation is True
        assert exp.rare_tier == "excellent"
        assert exp.rare_score == 95
        assert len(exp.valuable_mods) == 2
        assert len(exp.synergies) == 1
        assert len(exp.red_flags) == 1

    def test_create_with_build_match(self):
        """Can create with build matching info."""
        exp = PriceExplanation(
            matches_build=True,
            build_match_details="Matches Lightning Arrow Deadeye"
        )

        assert exp.matches_build is True
        assert "Lightning Arrow" in exp.build_match_details

    def test_create_with_adjustments(self):
        """Can create with price adjustments."""
        exp = PriceExplanation(
            adjustments=["Corrupted: -20%", "6-link: +500c"]
        )

        assert len(exp.adjustments) == 2
        assert "Corrupted" in exp.adjustments[0]


class TestPriceExplanationSummaryLines:
    """Tests for to_summary_lines() method."""

    def test_empty_explanation_returns_empty_list(self):
        """Empty explanation should return empty list."""
        exp = PriceExplanation()
        lines = exp.to_summary_lines()
        assert lines == []

    def test_summary_line_included(self):
        """Summary should be first line if present."""
        exp = PriceExplanation(summary="Test summary")
        lines = exp.to_summary_lines()

        assert len(lines) == 1
        assert "Summary: Test summary" in lines[0]

    def test_source_name_included(self):
        """Source name should be included."""
        exp = PriceExplanation(source_name="poe.ninja")
        lines = exp.to_summary_lines()

        assert any("Source: poe.ninja" in line for line in lines)

    def test_source_with_details(self):
        """Source details should be appended in parentheses."""
        exp = PriceExplanation(
            source_name="poe.ninja",
            source_details="Currency API"
        )
        lines = exp.to_summary_lines()

        source_line = [line for line in lines if "Source:" in line][0]
        assert "poe.ninja (Currency API)" in source_line

    def test_confidence_uppercase(self):
        """Confidence should be displayed uppercase."""
        exp = PriceExplanation(confidence="high")
        lines = exp.to_summary_lines()

        assert any("Confidence: HIGH" in line for line in lines)

    def test_confidence_with_reason(self):
        """Confidence reason should be appended."""
        exp = PriceExplanation(
            confidence="high",
            confidence_reason="Large sample size"
        )
        lines = exp.to_summary_lines()

        conf_line = [line for line in lines if "Confidence:" in line][0]
        assert "HIGH - Large sample size" in conf_line

    def test_sample_size_shown_when_positive(self):
        """Sample size shown only when > 0."""
        exp_zero = PriceExplanation(sample_size=0)
        exp_positive = PriceExplanation(sample_size=50)

        lines_zero = exp_zero.to_summary_lines()
        lines_positive = exp_positive.to_summary_lines()

        assert not any("listings" in line for line in lines_zero)
        assert any("Based on: 50 listings" in line for line in lines_positive)

    def test_calculation_method_shown(self):
        """Calculation method should be displayed."""
        exp = PriceExplanation(calculation_method="trimmed_mean")
        lines = exp.to_summary_lines()

        assert any("Price method: trimmed_mean" in line for line in lines)

    def test_rare_evaluation_details(self):
        """Rare evaluation should show tier, score, mods, synergies, flags."""
        exp = PriceExplanation(
            is_rare_evaluation=True,
            rare_tier="good",
            rare_score=75,
            valuable_mods=["T1 Life", "+1 Frenzy"],
            synergies=["Life + Res"],
            red_flags=["No movement speed"]
        )
        lines = exp.to_summary_lines()

        assert any("Rare tier: good (score: 75)" in line for line in lines)
        assert any("Valuable mods:" in line for line in lines)
        assert any("Synergies:" in line for line in lines)
        assert any("Red flags:" in line for line in lines)

    def test_valuable_mods_limited_to_five(self):
        """Only first 5 valuable mods should be shown."""
        exp = PriceExplanation(
            is_rare_evaluation=True,
            valuable_mods=["Mod1", "Mod2", "Mod3", "Mod4", "Mod5", "Mod6", "Mod7"]
        )
        lines = exp.to_summary_lines()

        mods_line = [line for line in lines if "Valuable mods:" in line][0]
        # Should have exactly 5 mods (comma-separated = 4 commas)
        assert mods_line.count(",") == 4

    def test_build_match_shown(self):
        """Build match details should be shown when matches_build is True."""
        exp = PriceExplanation(
            matches_build=True,
            build_match_details="Perfect for your build"
        )
        lines = exp.to_summary_lines()

        assert any("Build match: Perfect for your build" in line for line in lines)

    def test_adjustments_shown(self):
        """Adjustments should be displayed."""
        exp = PriceExplanation(
            adjustments=["Corrupted: -20%", "Quality: +5%"]
        )
        lines = exp.to_summary_lines()

        assert any("Adjustments:" in line for line in lines)
        adj_line = [line for line in lines if "Adjustments:" in line][0]
        assert "Corrupted: -20%" in adj_line
        assert "Quality: +5%" in adj_line


class TestPriceExplanationSerialization:
    """Tests for JSON serialization/deserialization."""

    def test_to_json_returns_valid_json(self):
        """to_json should return valid JSON string."""
        exp = PriceExplanation(
            summary="Test",
            source_name="poe.ninja",
            sample_size=100
        )

        json_str = exp.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["summary"] == "Test"
        assert data["source_name"] == "poe.ninja"
        assert data["sample_size"] == 100

    def test_to_json_includes_all_fields(self):
        """to_json should include all dataclass fields."""
        exp = PriceExplanation()
        json_str = exp.to_json()
        data = json.loads(json_str)

        expected_fields = [
            "summary", "source_name", "source_details", "confidence",
            "confidence_reason", "calculation_method", "sample_size",
            "price_spread", "stats_used", "is_rare_evaluation", "rare_tier",
            "rare_score", "valuable_mods", "synergies", "red_flags",
            "matches_build", "build_match_details", "adjustments"
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_from_json_restores_object(self):
        """from_json should restore identical object."""
        original = PriceExplanation(
            summary="Price from poe.ninja",
            source_name="poe.ninja",
            confidence="high",
            confidence_reason="Large sample",
            sample_size=50,
            is_rare_evaluation=True,
            rare_tier="good",
            rare_score=80,
            valuable_mods=["T1 Life", "T1 Res"],
            adjustments=["Corrupted: -10%"]
        )

        json_str = original.to_json()
        restored = PriceExplanation.from_json(json_str)

        assert restored.summary == original.summary
        assert restored.source_name == original.source_name
        assert restored.confidence == original.confidence
        assert restored.sample_size == original.sample_size
        assert restored.is_rare_evaluation == original.is_rare_evaluation
        assert restored.rare_tier == original.rare_tier
        assert restored.rare_score == original.rare_score
        assert restored.valuable_mods == original.valuable_mods
        assert restored.adjustments == original.adjustments

    def test_from_json_handles_invalid_json(self):
        """from_json should handle invalid JSON gracefully."""
        result = PriceExplanation.from_json("not valid json")

        assert result.summary == "Unable to parse explanation"

    def test_from_json_handles_wrong_type(self):
        """from_json should handle JSON with wrong structure."""
        result = PriceExplanation.from_json('["array", "not", "object"]')

        assert result.summary == "Unable to parse explanation"

    def test_from_json_handles_missing_fields(self):
        """from_json should handle partial JSON."""
        # This tests that default_factory fields work correctly
        partial_json = '{"summary": "Test", "source_name": "test"}'
        result = PriceExplanation.from_json(partial_json)

        assert result.summary == "Test"
        assert result.source_name == "test"
        # Defaults should be applied
        assert result.valuable_mods == []
        assert result.stats_used == {}

    def test_roundtrip_preserves_data(self):
        """JSON roundtrip should preserve all data."""
        exp = PriceExplanation(
            summary="Full test",
            source_name="poe.ninja",
            source_details="Currency API v2",
            confidence="high",
            confidence_reason="50+ listings",
            calculation_method="trimmed_mean",
            sample_size=75,
            price_spread="tight",
            stats_used={"min": 10, "max": 20, "median": 15},
            is_rare_evaluation=True,
            rare_tier="excellent",
            rare_score=95,
            valuable_mods=["Mod1", "Mod2"],
            synergies=["Syn1"],
            red_flags=["Flag1"],
            matches_build=True,
            build_match_details="Perfect match",
            adjustments=["Adj1", "Adj2"]
        )

        roundtripped = PriceExplanation.from_json(exp.to_json())

        # All fields should match
        assert roundtripped.summary == exp.summary
        assert roundtripped.source_name == exp.source_name
        assert roundtripped.source_details == exp.source_details
        assert roundtripped.confidence == exp.confidence
        assert roundtripped.confidence_reason == exp.confidence_reason
        assert roundtripped.calculation_method == exp.calculation_method
        assert roundtripped.sample_size == exp.sample_size
        assert roundtripped.price_spread == exp.price_spread
        assert roundtripped.stats_used == exp.stats_used
        assert roundtripped.is_rare_evaluation == exp.is_rare_evaluation
        assert roundtripped.rare_tier == exp.rare_tier
        assert roundtripped.rare_score == exp.rare_score
        assert roundtripped.valuable_mods == exp.valuable_mods
        assert roundtripped.synergies == exp.synergies
        assert roundtripped.red_flags == exp.red_flags
        assert roundtripped.matches_build == exp.matches_build
        assert roundtripped.build_match_details == exp.build_match_details
        assert roundtripped.adjustments == exp.adjustments


class TestPriceExplanationEdgeCases:
    """Edge case tests for PriceExplanation."""

    def test_empty_lists_remain_independent(self):
        """Default empty lists should not be shared between instances."""
        exp1 = PriceExplanation()
        exp2 = PriceExplanation()

        exp1.valuable_mods.append("Test")

        assert "Test" in exp1.valuable_mods
        assert "Test" not in exp2.valuable_mods

    def test_empty_dict_remains_independent(self):
        """Default empty dict should not be shared between instances."""
        exp1 = PriceExplanation()
        exp2 = PriceExplanation()

        exp1.stats_used["key"] = "value"

        assert "key" in exp1.stats_used
        assert "key" not in exp2.stats_used

    def test_unicode_in_summary(self):
        """Should handle unicode characters in fields."""
        exp = PriceExplanation(
            summary="Price: 100 ← cheap!",
            valuable_mods=["日本語テスト", "émoji: 🔥"]
        )

        json_str = exp.to_json()
        restored = PriceExplanation.from_json(json_str)

        assert restored.summary == exp.summary
        assert restored.valuable_mods == exp.valuable_mods

    def test_special_characters_in_json(self):
        """Should handle special JSON characters."""
        exp = PriceExplanation(
            summary='Quote: "test" and backslash: \\',
            source_details="Tab:\there"
        )

        json_str = exp.to_json()
        restored = PriceExplanation.from_json(json_str)

        assert restored.summary == exp.summary
        assert restored.source_details == exp.source_details
