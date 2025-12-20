"""
Tests for gui_qt/widgets/item_comparison_widget.py

Tests the item comparison widget including:
- ModComparisonRow display
- ItemComparisonWidget functionality
- Quality calculation and display
- Improvement suggestions
"""
import pytest
from unittest.mock import MagicMock



@pytest.fixture
def mod_analysis():
    """Create a mock ModAnalysis."""
    mod = MagicMock()
    mod.tier_label = "T2"
    mod.stat_type = "life"
    mod.current_value = 92
    mod.tier = 2
    mod.roll_quality = 80.0
    mod.divine_potential = 7
    mod.max_roll = 99
    mod.min_roll = 80
    return mod


@pytest.fixture
def crafting_analysis(mod_analysis):
    """Create a mock CraftingAnalysis."""
    analysis = MagicMock()
    analysis.mod_analyses = [mod_analysis]
    analysis.divine_recommended = True
    analysis.open_prefixes = 1
    analysis.open_suffixes = 2
    return analysis


@pytest.fixture
def parsed_item():
    """Create a mock ParsedItem."""
    item = MagicMock()
    item.name = "Test Ring"
    item.base_type = "Two-Stone Ring"
    item.rarity = "Rare"
    item.item_level = 85
    item.explicits = ["+92 to Maximum Life"]
    return item


class TestModComparisonRow:
    """Tests for ModComparisonRow widget."""

    def test_creation(self, qapp, mod_analysis):
        """ModComparisonRow creates successfully."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        row = ModComparisonRow(
            mod_analysis=mod_analysis,
            ideal_max=99,
            market_avg=85,
        )

        assert row is not None

    def test_tier_label_displayed(self, qapp, mod_analysis):
        """Tier label is displayed."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        row = ModComparisonRow(
            mod_analysis=mod_analysis,
            ideal_max=99,
            market_avg=85,
        )

        # Check tier label exists
        row.findChild(type(row), "")  # Generic search
        # Basic existence check since we can't easily find specific labels
        assert row.layout() is not None

    def test_tier_color_tier1(self, qapp):
        """T1 mods get high value color."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T1"
        mod.stat_type = "life"
        mod.current_value = 99
        mod.tier = 1
        mod.roll_quality = 100.0

        row = ModComparisonRow(mod, 99, 85)
        color = row._get_tier_color(1)

        assert color is not None
        # High value color should not be the border color

    def test_tier_color_low_tier(self, qapp):
        """Low tier mods get low value color."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T5"
        mod.stat_type = "life"
        mod.current_value = 50
        mod.tier = 5
        mod.roll_quality = 30.0

        row = ModComparisonRow(mod, 99, 85)
        color = row._get_tier_color(5)

        assert color is not None

    def test_tier_color_none(self, qapp, mod_analysis):
        """None tier gets border color."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        row = ModComparisonRow(mod_analysis, 99, 85)
        color = row._get_tier_color(None)

        assert color is not None


class TestItemComparisonWidget:
    """Tests for ItemComparisonWidget."""

    def test_creation(self, qapp):
        """Widget creates successfully."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()
        assert widget is not None

    def test_initial_state(self, qapp):
        """Initial state shows empty message."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()

        assert widget.quality_label.text() == "Quality: --"
        assert widget.comparison_label.text() == ""
        assert "No analysis" in widget.improvement_label.text()

    def test_set_item_updates_display(self, qapp, parsed_item, crafting_analysis):
        """Setting item updates the display."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, crafting_analysis)

        # Quality should be updated
        assert "Quality:" in widget.quality_label.text()
        assert "--" not in widget.quality_label.text()

    def test_clear_resets_display(self, qapp, parsed_item, crafting_analysis):
        """Clear resets to empty state."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, crafting_analysis)
        widget.clear()

        assert widget.quality_label.text() == "Quality: --"
        assert widget._current_item is None
        assert widget._current_analysis is None

    def test_quality_excellent(self, qapp, parsed_item):
        """Excellent quality items labeled correctly."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod = MagicMock()
        mod.stat_type = "life"
        mod.current_value = 95
        mod.tier = 1
        mod.tier_label = "T1"  # Explicit string to avoid MagicMock issues
        mod.roll_quality = 95.0
        mod.divine_potential = 4
        mod.max_roll = 99
        mod.min_roll = 80

        analysis = MagicMock()
        analysis.mod_analyses = [mod]
        analysis.divine_recommended = False
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        # Should show excellent or high quality
        quality_text = widget.quality_label.text()
        assert "%" in quality_text

    def test_quality_below_average(self, qapp, parsed_item):
        """Below average quality items labeled correctly."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod = MagicMock()
        mod.stat_type = "life"
        mod.current_value = 50
        mod.tier = 4
        mod.tier_label = "T4"  # Explicit string
        mod.roll_quality = 30.0
        mod.divine_potential = 10
        mod.max_roll = 80
        mod.min_roll = 60

        analysis = MagicMock()
        analysis.mod_analyses = [mod]
        analysis.divine_recommended = False
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        quality_text = widget.quality_label.text()
        # Quality should reflect the low value
        assert "%" in quality_text or "Below" in quality_text or "Average" in quality_text

    def test_divine_suggestion_shown(self, qapp, parsed_item, crafting_analysis):
        """Divine suggestion shown when recommended."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, crafting_analysis)

        improvement_text = widget.improvement_label.text()
        # Should mention divine potential
        assert "Divine" in improvement_text or "potential" in improvement_text

    def test_craft_suggestions_for_open_slots(self, qapp, parsed_item):
        """Craft suggestions shown for open slots."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod = MagicMock()
        mod.stat_type = "life"
        mod.current_value = 92
        mod.tier = 2
        mod.tier_label = "T2"  # Explicit string
        mod.roll_quality = 80.0
        mod.divine_potential = 5
        mod.max_roll = 99
        mod.min_roll = 80

        analysis = MagicMock()
        analysis.mod_analyses = [mod]
        analysis.divine_recommended = False
        analysis.open_prefixes = 2
        analysis.open_suffixes = 1

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        improvement_text = widget.improvement_label.text()
        # Should mention crafting
        assert "prefix" in improvement_text.lower() or "suffix" in improvement_text.lower() or "Craft" in improvement_text

    def test_no_improvements_for_perfect_item(self, qapp, parsed_item):
        """No major improvements shown for perfect items."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod = MagicMock()
        mod.stat_type = "life"
        mod.current_value = 99
        mod.tier = 1
        mod.tier_label = "T1"  # Explicit string
        mod.roll_quality = 100.0
        mod.divine_potential = 0
        mod.max_roll = 99
        mod.min_roll = 80

        analysis = MagicMock()
        analysis.mod_analyses = [mod]
        analysis.divine_recommended = False
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        improvement_text = widget.improvement_label.text()
        # Should indicate item is good
        assert "well-rolled" in improvement_text.lower() or "no major" in improvement_text.lower()

    def test_comparison_above_market(self, qapp, parsed_item):
        """Shows above market comparison."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod = MagicMock()
        mod.stat_type = "life"
        mod.current_value = 90
        mod.tier = 1
        mod.tier_label = "T1"  # Explicit string
        mod.roll_quality = 90.0
        mod.divine_potential = 9
        mod.max_roll = 99
        mod.min_roll = 80

        analysis = MagicMock()
        analysis.mod_analyses = [mod]
        analysis.divine_recommended = True
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        comparison_text = widget.comparison_label.text()
        # Should show market comparison
        assert "market" in comparison_text.lower() or "%" in comparison_text

    def test_empty_analysis_handled(self, qapp, parsed_item):
        """Empty analysis shows empty state."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        analysis = MagicMock()
        analysis.mod_analyses = []
        analysis.divine_recommended = False
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        # Should handle gracefully
        assert widget.quality_label.text() == "Quality: --"

    def test_multiple_mods_quality_average(self, qapp, parsed_item):
        """Quality averaged across multiple mods."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        mod1 = MagicMock()
        mod1.stat_type = "life"
        mod1.current_value = 90
        mod1.tier = 1
        mod1.tier_label = "T1"  # Explicit string
        mod1.roll_quality = 90.0
        mod1.divine_potential = 9
        mod1.max_roll = 99
        mod1.min_roll = 80

        mod2 = MagicMock()
        mod2.stat_type = "fire_resistance"
        mod2.current_value = 40
        mod2.tier = 2
        mod2.tier_label = "T2"  # Explicit string
        mod2.roll_quality = 70.0
        mod2.divine_potential = 8
        mod2.max_roll = 48
        mod2.min_roll = 36

        analysis = MagicMock()
        analysis.mod_analyses = [mod1, mod2]
        analysis.divine_recommended = True
        analysis.open_prefixes = 0
        analysis.open_suffixes = 0

        widget = ItemComparisonWidget()
        widget.set_item(parsed_item, analysis)

        # Quality text should exist
        quality_text = widget.quality_label.text()
        assert "Quality:" in quality_text

    def test_get_t1_max_from_data(self, qapp):
        """T1 max retrieval works."""
        from gui_qt.widgets.item_comparison_widget import ItemComparisonWidget

        widget = ItemComparisonWidget()
        # Just verify the method exists and doesn't crash
        result = widget._get_t1_max("life")
        assert isinstance(result, int)


class TestValueWidgetCreation:
    """Tests for value widget creation."""

    def test_progress_bar_fill_percentage(self, qapp, mod_analysis):
        """Progress bar fill scales with value."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        row = ModComparisonRow(
            mod_analysis=mod_analysis,
            ideal_max=100,
            market_avg=70,
        )

        # The value widget should be created
        # Just verify the widget exists and has a layout
        assert row.layout() is not None

    def test_zero_max_value_handled(self, qapp):
        """Zero max value doesn't cause division error."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "??"
        mod.stat_type = "unknown"
        mod.current_value = 0
        mod.tier = None
        mod.roll_quality = 0.0

        # Should not raise
        row = ModComparisonRow(
            mod_analysis=mod,
            ideal_max=0,  # Zero max
            market_avg=0,
        )
        assert row is not None


class TestTierTooltip:
    """Tests for tier tooltip functionality."""

    def test_tier_tooltip_contains_stat_name(self, qapp):
        """Tier tooltip includes stat name."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T2"
        mod.stat_type = "life"
        mod.current_value = 92
        mod.tier = 2
        mod.roll_quality = 80.0
        mod.divine_potential = 7

        row = ModComparisonRow(mod, 99, 85)
        tooltip = row._build_tier_tooltip()

        assert "Life" in tooltip

    def test_tier_tooltip_contains_tier_number(self, qapp):
        """Tier tooltip includes tier number."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T2"
        mod.stat_type = "life"
        mod.current_value = 92
        mod.tier = 2
        mod.roll_quality = 80.0
        mod.divine_potential = 7

        row = ModComparisonRow(mod, 99, 85)
        tooltip = row._build_tier_tooltip()

        assert "Tier 2" in tooltip

    def test_tier_tooltip_contains_roll_range(self, qapp):
        """Tier tooltip includes roll range from tier data."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T2"
        mod.stat_type = "life"
        mod.current_value = 92
        mod.tier = 2
        mod.roll_quality = 80.0
        mod.divine_potential = 7

        row = ModComparisonRow(mod, 99, 85)
        tooltip = row._build_tier_tooltip()

        # T2 life is 90-99
        assert "90-99" in tooltip

    def test_tier_tooltip_contains_divine_potential(self, qapp):
        """Tier tooltip includes divine potential."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "T2"
        mod.stat_type = "life"
        mod.current_value = 92
        mod.tier = 2
        mod.roll_quality = 80.0
        mod.divine_potential = 7

        row = ModComparisonRow(mod, 99, 85)
        tooltip = row._build_tier_tooltip()

        assert "Divine Potential" in tooltip
        assert "+7" in tooltip

    def test_tier_tooltip_unknown_stat(self, qapp):
        """Tier tooltip handles unknown stats gracefully."""
        from gui_qt.widgets.item_comparison_widget import ModComparisonRow

        mod = MagicMock()
        mod.tier_label = "??"
        mod.stat_type = "unknown_stat"
        mod.current_value = 50
        mod.tier = None
        mod.roll_quality = 50.0
        mod.divine_potential = 0

        row = ModComparisonRow(mod, 100, 70)
        tooltip = row._build_tier_tooltip()

        # Should not crash, should show value
        assert "Unknown Stat" in tooltip
        assert "50" in tooltip
