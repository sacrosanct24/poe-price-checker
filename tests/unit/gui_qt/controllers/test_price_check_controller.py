"""Tests for PriceCheckController."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from gui_qt.controllers.price_check_controller import (
    PriceCheckController,
    PriceCheckResult,
)


@dataclass
class MockParsedItem:
    """Mock ParsedItem for testing."""
    name: str = "Test Item"
    rarity: str = "Unique"
    slot: str = "ring"


@pytest.fixture
def mock_parser():
    """Create mock parser."""
    parser = MagicMock()
    parser.parse.return_value = MockParsedItem()
    return parser


@pytest.fixture
def mock_price_service():
    """Create mock price service."""
    service = MagicMock()
    service.check_item.return_value = [
        {"item_name": "Test Item", "chaos_value": 50, "source": "poe.ninja"},
    ]
    return service


@pytest.fixture
def mock_rare_evaluator():
    """Create mock rare evaluator."""
    evaluator = MagicMock()
    evaluator.evaluate.return_value = MagicMock(score=75)
    return evaluator


@pytest.fixture
def controller(mock_parser, mock_price_service, mock_rare_evaluator):
    """Create controller with mocks."""
    return PriceCheckController(
        parser=mock_parser,
        price_service=mock_price_service,
        rare_evaluator=mock_rare_evaluator,
    )


class TestPriceCheckResult:
    """Tests for PriceCheckResult dataclass."""

    def test_best_price_with_results(self):
        """best_price returns highest chaos value."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[
                {"chaos_value": 10},
                {"chaos_value": 50},
                {"chaos_value": 30},
            ],
        )
        assert result.best_price == 50

    def test_best_price_empty_results(self):
        """best_price returns 0 for empty results."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[],
        )
        assert result.best_price == 0.0

    def test_best_price_handles_none_values(self):
        """best_price handles None chaos values."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[
                {"chaos_value": None},
                {"chaos_value": 25},
            ],
        )
        assert result.best_price == 25

    def test_result_count(self):
        """result_count returns number of results."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{}, {}, {}],
        )
        assert result.result_count == 3


class TestPriceCheckController:
    """Tests for PriceCheckController."""

    def test_check_price_success(self, controller, mock_parser, mock_price_service):
        """check_price returns Ok result on success."""
        result = controller.check_price("Item: Test")

        assert result.is_ok()
        data = result.unwrap()
        assert data.parsed_item is not None
        assert len(data.results) == 1
        assert len(data.formatted_rows) == 1

    def test_check_price_empty_text(self, controller):
        """check_price returns Err for empty text."""
        result = controller.check_price("")
        assert result.is_err()
        assert "No item text" in result.error

    def test_check_price_whitespace_only(self, controller):
        """check_price returns Err for whitespace only."""
        result = controller.check_price("   \n  ")
        assert result.is_err()

    def test_check_price_parse_failure(self, controller, mock_parser):
        """check_price returns Err when parsing fails."""
        mock_parser.parse.return_value = None

        result = controller.check_price("Invalid item")

        assert result.is_err()
        assert "parse" in result.error.lower()

    def test_check_price_parse_exception(self, controller, mock_parser):
        """check_price returns Err when parser raises exception."""
        mock_parser.parse.side_effect = ValueError("Parse error")

        result = controller.check_price("Item text")

        assert result.is_err()
        assert "Parse error" in result.error

    def test_check_price_service_exception(self, controller, mock_price_service):
        """check_price returns Err when price service fails."""
        mock_price_service.check_item.side_effect = Exception("API error")

        result = controller.check_price("Item text")

        assert result.is_err()
        assert "error" in result.error.lower()

    def test_check_price_rare_evaluation(self, controller, mock_parser, mock_rare_evaluator):
        """check_price evaluates rare items."""
        mock_parser.parse.return_value = MockParsedItem(rarity="Rare")

        result = controller.check_price("Rare item text")

        assert result.is_ok()
        data = result.unwrap()
        assert data.is_rare
        assert data.evaluation is not None
        mock_rare_evaluator.evaluate.assert_called_once()

    def test_check_price_non_rare_no_evaluation(self, controller, mock_rare_evaluator):
        """check_price skips evaluation for non-rare items."""
        result = controller.check_price("Unique item text")

        assert result.is_ok()
        data = result.unwrap()
        assert not data.is_rare
        assert data.evaluation is None
        mock_rare_evaluator.evaluate.assert_not_called()


class TestFormatResults:
    """Tests for result formatting."""

    def test_format_results_basic(self, controller):
        """Formats basic result correctly."""
        parsed = MockParsedItem(name="Ring of Power")
        results = [
            {
                "item_name": "Ring of Power",
                "chaos_value": 100,
                "divine_value": 0.5,
                "source": "poe.ninja",
                "listing_count": 50,
            }
        ]

        formatted = controller._format_results(parsed, results)

        assert len(formatted) == 1
        row = formatted[0]
        assert row["item_name"] == "Ring of Power"
        assert row["chaos_value"] == 100.0
        assert row["divine_value"] == 0.5
        assert row["source"] == "poe.ninja"
        assert row["listing_count"] == 50
        assert row["_item"] is parsed

    def test_format_results_handles_missing_values(self, controller):
        """Formats results with missing values gracefully."""
        parsed = MockParsedItem(name="Test")
        results = [{}]

        formatted = controller._format_results(parsed, results)

        row = formatted[0]
        assert row["item_name"] == "Test"  # Falls back to parsed.name
        assert row["chaos_value"] == 0.0
        assert row["divine_value"] == 0.0
        assert row["listing_count"] == 0
        assert row["source"] == ""

    def test_format_results_explanation_dict(self, controller):
        """Formats explanation dict as JSON string."""
        parsed = MockParsedItem()
        results = [
            {"explanation": {"method": "direct", "confidence": 0.9}}
        ]

        formatted = controller._format_results(parsed, results)

        assert "direct" in formatted[0]["price_explanation"]
        assert "confidence" in formatted[0]["price_explanation"]

    def test_format_results_explanation_object(self, controller):
        """Formats explanation object as JSON string."""
        parsed = MockParsedItem()

        class Explanation:
            def __init__(self):
                self.method = "fuzzy"

        results = [{"explanation": Explanation()}]

        formatted = controller._format_results(parsed, results)

        assert "fuzzy" in formatted[0]["price_explanation"]


class TestSafeConversions:
    """Tests for safe type conversions."""

    def test_safe_float_valid(self):
        """Converts valid values to float."""
        assert PriceCheckController._safe_float(10) == 10.0
        assert PriceCheckController._safe_float(10.5) == 10.5
        assert PriceCheckController._safe_float("25.5") == 25.5

    def test_safe_float_invalid(self):
        """Returns 0.0 for invalid values."""
        assert PriceCheckController._safe_float(None) == 0.0
        assert PriceCheckController._safe_float("") == 0.0
        assert PriceCheckController._safe_float("invalid") == 0.0

    def test_safe_int_valid(self):
        """Converts valid values to int."""
        assert PriceCheckController._safe_int(10) == 10
        assert PriceCheckController._safe_int(10.9) == 10
        assert PriceCheckController._safe_int("25") == 25

    def test_safe_int_invalid(self):
        """Returns 0 for invalid values."""
        assert PriceCheckController._safe_int(None) == 0
        assert PriceCheckController._safe_int("") == 0
        assert PriceCheckController._safe_int("invalid") == 0


class TestParseItem:
    """Tests for parse_item method."""

    def test_parse_item_success(self, controller, mock_parser):
        """parse_item returns Ok with parsed item."""
        result = controller.parse_item("Item text")

        assert result.is_ok()
        assert result.unwrap() is not None

    def test_parse_item_empty(self, controller):
        """parse_item returns Err for empty text."""
        result = controller.parse_item("")
        assert result.is_err()

    def test_parse_item_failure(self, controller, mock_parser):
        """parse_item returns Err when parsing fails."""
        mock_parser.parse.return_value = None

        result = controller.parse_item("Invalid")

        assert result.is_err()


class TestEvaluateRare:
    """Tests for evaluate_rare method."""

    def test_evaluate_rare_success(self, controller, mock_rare_evaluator):
        """evaluate_rare returns Ok with evaluation."""
        parsed = MockParsedItem(rarity="Rare")

        result = controller.evaluate_rare(parsed)

        assert result.is_ok()
        assert result.unwrap().score == 75

    def test_evaluate_rare_no_evaluator(self, mock_parser, mock_price_service):
        """evaluate_rare returns Err when no evaluator."""
        controller = PriceCheckController(
            parser=mock_parser,
            price_service=mock_price_service,
            rare_evaluator=None,
        )
        parsed = MockParsedItem(rarity="Rare")

        result = controller.evaluate_rare(parsed)

        assert result.is_err()
        assert "not available" in result.error

    def test_evaluate_rare_non_rare_item(self, controller):
        """evaluate_rare returns Err for non-rare items."""
        parsed = MockParsedItem(rarity="Unique")

        result = controller.evaluate_rare(parsed)

        assert result.is_err()
        assert "not rare" in result.error.lower()


class TestSummaryAndToast:
    """Tests for summary and toast methods."""

    def test_get_price_summary_no_results(self, controller):
        """Summary for no results."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[],
        )
        assert controller.get_price_summary(result) == "No prices found"

    def test_get_price_summary_one_result(self, controller):
        """Summary for one result."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{}],
        )
        assert controller.get_price_summary(result) == "Found 1 price result"

    def test_get_price_summary_multiple_results(self, controller):
        """Summary for multiple results."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{}, {}, {}],
        )
        assert "3" in controller.get_price_summary(result)

    def test_should_show_toast_high_value(self, controller):
        """Toast for high value items."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{"chaos_value": 150}],
        )

        show, toast_type, message = controller.should_show_toast(result)

        assert show is True
        assert toast_type == "success"
        assert "150" in message

    def test_should_show_toast_medium_value(self, controller):
        """Toast for medium value items."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{"chaos_value": 25}],
        )

        show, toast_type, message = controller.should_show_toast(result)

        assert show is True
        assert toast_type == "info"

    def test_should_show_toast_low_value(self, controller):
        """No toast for low value items."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[{"chaos_value": 5}],
        )

        show, toast_type, message = controller.should_show_toast(result)

        assert show is False

    def test_should_show_toast_no_results(self, controller):
        """No toast for empty results."""
        result = PriceCheckResult(
            parsed_item=MockParsedItem(),
            results=[],
        )

        show, toast_type, message = controller.should_show_toast(result)

        assert show is False


class TestSetters:
    """Tests for setter methods."""

    def test_set_upgrade_checker(self, controller):
        """Can set upgrade checker."""
        checker = MagicMock()
        controller.set_upgrade_checker(checker)
        assert controller._upgrade_checker is checker

    def test_set_rare_evaluator(self, controller):
        """Can set rare evaluator."""
        evaluator = MagicMock()
        controller.set_rare_evaluator(evaluator)
        assert controller._rare_evaluator is evaluator
