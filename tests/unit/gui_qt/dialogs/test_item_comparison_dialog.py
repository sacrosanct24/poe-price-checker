"""Tests for gui_qt/dialogs/item_comparison_dialog.py - Item comparison dialog."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QWidget

from gui_qt.dialogs.item_comparison_dialog import ItemComparisonDialog


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_app_context():
    """Create a mock application context."""
    ctx = MagicMock()
    ctx.pob_build = None
    return ctx


@pytest.fixture
def mock_item():
    """Create a mock parsed item."""
    item = MagicMock()
    item.name = "Test Item"
    item.base_type = "Body Armour"
    item.rarity = "Rare"
    item.implicits = ["+15% to Fire Resistance"]
    item.explicits = [
        "+100 to Maximum Life",
        "+50% to Fire Resistance",
        "+10% increased Attack Speed",
    ]
    item.enchants = []
    item.raw_text = "Test Item\n+100 to Maximum Life"
    return item


@pytest.fixture
def mock_item2():
    """Create a second mock parsed item."""
    item = MagicMock()
    item.name = "Better Item"
    item.base_type = "Body Armour"
    item.rarity = "Rare"
    item.implicits = ["+20% to Fire Resistance"]
    item.explicits = [
        "+120 to Maximum Life",
        "+60% to Fire Resistance",
        "+15% increased Attack Speed",
    ]
    item.enchants = []
    item.raw_text = "Better Item\n+120 to Maximum Life"
    return item


# =============================================================================
# ItemComparisonDialog Init Tests
# =============================================================================


class TestItemComparisonDialogInit:
    """Tests for dialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        assert "Comparison" in dialog.windowTitle()

    def test_init_sets_minimum_size(self, qtbot):
        """Should set minimum size."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 900
        assert dialog.minimumHeight() >= 600

    def test_init_creates_text_edits(self, qtbot):
        """Should create text edit widgets."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        assert dialog._text_edit1 is not None
        assert dialog._text_edit2 is not None

    def test_init_creates_inspectors(self, qtbot):
        """Should create item inspector widgets."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        assert dialog._inspector1 is not None
        assert dialog._inspector2 is not None

    def test_init_creates_summary_browser(self, qtbot):
        """Should create summary browser."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        assert dialog._summary_browser is not None

    def test_init_stores_app_context(self, qtbot, mock_app_context):
        """Should store app context."""
        dialog = ItemComparisonDialog(app_context=mock_app_context)
        qtbot.addWidget(dialog)

        assert dialog._app_context is mock_app_context


# =============================================================================
# Parse Item Tests
# =============================================================================


class TestItemComparisonDialogParseItem:
    """Tests for item parsing."""

    def test_parse_item1_empty_text(self, qtbot):
        """Should clear item1 when text is empty."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = MagicMock()
        dialog._text_edit1.setPlainText("")

        dialog._parse_item1()

        assert dialog._item1 is None

    def test_parse_item2_empty_text(self, qtbot):
        """Should clear item2 when text is empty."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item2 = MagicMock()
        dialog._text_edit2.setPlainText("")

        dialog._parse_item2()

        assert dialog._item2 is None

    def test_parse_item1_success(self, qtbot, mock_item):
        """Should parse valid item text."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog._parser, 'parse', return_value=mock_item):
            dialog._text_edit1.setPlainText("Item: Test Item\n+100 Life")
            dialog._parse_item1()

        assert dialog._item1 is mock_item

    def test_parse_item1_failure(self, qtbot):
        """Should handle parse errors gracefully."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog._parser, 'parse', side_effect=Exception("Parse error")):
            dialog._text_edit1.setPlainText("Invalid item text")
            dialog._parse_item1()

        assert dialog._item1 is None


# =============================================================================
# Update Comparison Tests
# =============================================================================


class TestItemComparisonDialogUpdateComparison:
    """Tests for comparison updates."""

    def test_update_comparison_no_items(self, qtbot):
        """Should show initial message when no items."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = None
        dialog._item2 = None

        dialog._update_comparison()

        assert "Paste" in dialog._summary_browser.toHtml()

    def test_update_comparison_waiting_for_item1(self, qtbot, mock_item):
        """Should show waiting message when item1 is missing."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = None
        dialog._item2 = mock_item

        dialog._update_comparison()

        assert "Waiting" in dialog._summary_browser.toHtml()

    def test_update_comparison_waiting_for_item2(self, qtbot, mock_item):
        """Should show waiting message when item2 is missing."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = mock_item
        dialog._item2 = None

        dialog._update_comparison()

        assert "Waiting" in dialog._summary_browser.toHtml()

    def test_update_comparison_both_items(self, qtbot, mock_item, mock_item2):
        """Should generate comparison when both items present."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = mock_item
        dialog._item2 = mock_item2

        dialog._update_comparison()

        html = dialog._summary_browser.toHtml()
        assert "Test Item" in html or "Comparing" in html


# =============================================================================
# Get All Mods Tests
# =============================================================================


class TestItemComparisonDialogGetAllMods:
    """Tests for mod extraction."""

    def test_get_all_mods_none_item(self, qtbot):
        """Should return empty list for None item."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods = dialog._get_all_mods(None)

        assert mods == []

    def test_get_all_mods_with_implicits(self, qtbot, mock_item):
        """Should include implicits."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods = dialog._get_all_mods(mock_item)

        assert "+15% to Fire Resistance" in mods

    def test_get_all_mods_with_explicits(self, qtbot, mock_item):
        """Should include explicits."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods = dialog._get_all_mods(mock_item)

        assert "+100 to Maximum Life" in mods

    def test_get_all_mods_combined_count(self, qtbot, mock_item):
        """Should combine all mod types."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods = dialog._get_all_mods(mock_item)

        # 1 implicit + 3 explicits + 0 enchants = 4
        assert len(mods) == 4


# =============================================================================
# Basic Mod Comparison Tests
# =============================================================================


class TestItemComparisonDialogBasicModComparison:
    """Tests for basic mod comparison."""

    def test_basic_mod_comparison_unique_mods(self, qtbot):
        """Should identify unique mods in each item."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods1 = ["+100 Life", "+50 Fire Res"]
        mods2 = ["+100 Life", "+60 Cold Res"]

        html = dialog._basic_mod_comparison(mods1, mods2)

        assert "Only in Item 1" in html
        assert "Only in Item 2" in html

    def test_basic_mod_comparison_common_count(self, qtbot):
        """Should count common mods."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mods1 = ["+100 Life", "+50 Fire Res"]
        mods2 = ["+100 Life", "+50 Fire Res"]

        html = dialog._basic_mod_comparison(mods1, mods2)

        assert "Common mods: 2" in html


# =============================================================================
# Swap Items Tests
# =============================================================================


class TestItemComparisonDialogSwapItems:
    """Tests for item swapping."""

    def test_swap_items_swaps_text(self, qtbot):
        """Should swap text between text edits."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._text_edit1.setPlainText("Item 1 Text")
        dialog._text_edit2.setPlainText("Item 2 Text")

        dialog._swap_items()

        assert dialog._text_edit1.toPlainText() == "Item 2 Text"
        assert dialog._text_edit2.toPlainText() == "Item 1 Text"

    def test_swap_items_swaps_parsed_items(self, qtbot, mock_item, mock_item2):
        """Should swap parsed items."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = mock_item
        dialog._item2 = mock_item2

        with patch.object(dialog._inspector1, 'set_item'):
            with patch.object(dialog._inspector2, 'set_item'):
                dialog._swap_items()

        assert dialog._item1 is mock_item2
        assert dialog._item2 is mock_item


# =============================================================================
# Clear All Tests
# =============================================================================


class TestItemComparisonDialogClearAll:
    """Tests for clearing all items."""

    def test_clear_all_clears_text(self, qtbot):
        """Should clear text edits."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._text_edit1.setPlainText("Some text")
        dialog._text_edit2.setPlainText("Other text")

        dialog._clear_all()

        assert dialog._text_edit1.toPlainText() == ""
        assert dialog._text_edit2.toPlainText() == ""

    def test_clear_all_clears_items(self, qtbot, mock_item):
        """Should clear parsed items."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = mock_item
        dialog._item2 = mock_item

        dialog._clear_all()

        assert dialog._item1 is None
        assert dialog._item2 is None


# =============================================================================
# Set Item Tests
# =============================================================================


class TestItemComparisonDialogSetItem:
    """Tests for programmatic item setting."""

    def test_set_item1_sets_item(self, qtbot, mock_item):
        """Should set item1."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog._inspector1, 'set_item'):
            dialog.set_item1(mock_item)

        assert dialog._item1 is mock_item

    def test_set_item1_with_raw_text(self, qtbot, mock_item):
        """Should set text from raw_text attribute."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog._inspector1, 'set_item'):
            dialog.set_item1(mock_item)

        assert dialog._text_edit1.toPlainText() == mock_item.raw_text

    def test_set_item2_sets_item(self, qtbot, mock_item):
        """Should set item2."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog._inspector2, 'set_item'):
            dialog.set_item2(mock_item)

        assert dialog._item2 is mock_item


# =============================================================================
# Generate Comparison HTML Tests
# =============================================================================


class TestItemComparisonDialogGenerateComparisonHtml:
    """Tests for HTML generation."""

    def test_generate_comparison_html_empty(self, qtbot):
        """Should return empty string when no items."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = None
        dialog._item2 = None

        html = dialog._generate_comparison_html()

        assert html == ""

    def test_generate_comparison_html_includes_names(self, qtbot, mock_item, mock_item2):
        """Should include item names."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        dialog._item1 = mock_item
        dialog._item2 = mock_item2

        html = dialog._generate_comparison_html()

        assert "Test Item" in html
        assert "Better Item" in html

    def test_generate_comparison_html_with_upgrade_calculator(
        self, qtbot, mock_item, mock_item2
    ):
        """Should use upgrade calculator if available."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        mock_calc = MagicMock()
        mock_calc.compare_items.return_value = {
            "is_upgrade": True,
            "is_downgrade": False,
            "summary": "Better stats",
            "improvements": ["More life"],
            "losses": [],
        }
        dialog._upgrade_calculator = mock_calc
        dialog._item1 = mock_item
        dialog._item2 = mock_item2

        html = dialog._generate_comparison_html()

        assert "UPGRADE" in html


# =============================================================================
# Load Build Stats Tests
# =============================================================================


class TestItemComparisonDialogLoadBuildStats:
    """Tests for build stats loading."""

    def test_load_build_stats_without_context(self, qtbot):
        """Should handle missing app context."""
        dialog = ItemComparisonDialog()
        qtbot.addWidget(dialog)

        # Should not raise
        dialog._load_build_stats()

        assert dialog._build_stats is None

    def test_load_build_stats_without_build(self, qtbot, mock_app_context):
        """Should handle missing build."""
        dialog = ItemComparisonDialog(app_context=mock_app_context)
        qtbot.addWidget(dialog)

        dialog._load_build_stats()

        assert dialog._build_stats is None

    def test_load_build_stats_with_build(self, qtbot, mock_app_context):
        """Should load stats from build."""
        mock_build = MagicMock()
        mock_stats = MagicMock()
        mock_build.stats = mock_stats
        mock_app_context.pob_build = mock_build

        dialog = ItemComparisonDialog(app_context=mock_app_context)
        qtbot.addWidget(dialog)

        assert dialog._build_stats is mock_stats
        assert dialog._calculator is not None
        assert dialog._upgrade_calculator is not None
