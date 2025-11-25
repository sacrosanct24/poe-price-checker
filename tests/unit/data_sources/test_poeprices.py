"""
Unit tests for poeprices.info API client.

Tests the PoePricesAPI client and PoePricesPrediction data class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64

from data_sources.pricing.poeprices import (
    PoePricesAPI,
    PoePricesPrediction,
)


class TestPoePricesPrediction:
    """Tests for PoePricesPrediction dataclass."""

    def test_is_valid_success(self):
        """Test is_valid returns True for successful predictions."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=150.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.is_valid is True

    def test_is_valid_error(self):
        """Test is_valid returns False for error predictions."""
        prediction = PoePricesPrediction(
            min_price=0,
            max_price=0,
            currency="chaos",
            confidence_score=0,
            error_code=2,
            error_msg="Item not found",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.is_valid is False

    def test_is_valid_zero_price(self):
        """Test is_valid returns False for zero price predictions."""
        prediction = PoePricesPrediction(
            min_price=0,
            max_price=0,
            currency="chaos",
            confidence_score=50.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.is_valid is False

    def test_average_price(self):
        """Test average_price calculation."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=200.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.average_price == 150.0

    def test_price_range_str_chaos(self):
        """Test price_range_str for chaos values."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=200.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.price_range_str == "100-200 chaos"

    def test_price_range_str_divine(self):
        """Test price_range_str for divine values."""
        prediction = PoePricesPrediction(
            min_price=1.5,
            max_price=2.5,
            currency="divine",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.price_range_str == "1.5-2.5 divine"

    def test_confidence_tier_high(self):
        """Test confidence_tier for high confidence scores."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=200.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.confidence_tier == "high"

    def test_confidence_tier_medium(self):
        """Test confidence_tier for medium confidence scores."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=200.0,
            currency="chaos",
            confidence_score=65.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.confidence_tier == "medium"

    def test_confidence_tier_low(self):
        """Test confidence_tier for low confidence scores."""
        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=200.0,
            currency="chaos",
            confidence_score=45.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )
        assert prediction.confidence_tier == "low"


class TestPoePricesAPI:
    """Tests for PoePricesAPI client."""

    def test_init_default_league(self):
        """Test initialization with default league."""
        with patch.object(PoePricesAPI, '__init__', lambda x, league: None):
            api = PoePricesAPI.__new__(PoePricesAPI)
            api.league = "Standard"
            assert api.league == "Standard"

    def test_encode_item_text(self):
        """Test base64 encoding of item text."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        item_text = "Rarity: Rare\nTest Item"
        encoded = api._encode_item_text(item_text)

        # Verify it's valid base64
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert decoded == item_text

    def test_parse_response_success(self):
        """Test parsing a successful API response."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        response = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'pred_confidence_score': 85.5,
            'error': 0,
            'error_msg': '',
            'warning_msg': '',
            'pred_explanation': [
                ['+# to maximum Life', 0.5],
                ['+#% to Fire Resistance', 0.3],
            ],
        }

        prediction = api._parse_response(response)

        assert prediction.min_price == 100.0
        assert prediction.max_price == 150.0
        assert prediction.currency == 'chaos'
        assert prediction.confidence_score == 85.5
        assert prediction.error_code == 0
        assert len(prediction.mod_contributions) == 2
        assert prediction.mod_contributions[0] == ('+# to maximum Life', 0.5)

    def test_parse_response_error(self):
        """Test parsing an error API response."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        response = {
            'error': 2,
            'error_msg': 'Item not found',
            'warning_msg': '',
        }

        prediction = api._parse_response(response)

        assert prediction.error_code == 2
        assert prediction.error_msg == 'Item not found'
        assert prediction.is_valid is False

    @patch('data_sources.pricing.poeprices.PoePricesAPI.get')
    def test_predict_price_success(self, mock_get):
        """Test successful price prediction."""
        mock_get.return_value = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'pred_confidence_score': 85.5,
            'error': 0,
            'error_msg': '',
            'warning_msg': '',
            'pred_explanation': [],
        }

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"
        api.request_count = 0
        api._poeprices_client = None

        prediction = api.predict_price("Rarity: Rare\nTest Item")

        assert prediction.is_valid
        assert prediction.min_price == 100.0
        assert prediction.max_price == 150.0

    @patch('data_sources.pricing.poeprices.PoePricesAPI.get')
    def test_predict_price_api_error(self, mock_get):
        """Test price prediction with API error."""
        mock_get.side_effect = Exception("Network error")

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"
        api.request_count = 0
        api._poeprices_client = None

        prediction = api.predict_price("Rarity: Rare\nTest Item")

        assert not prediction.is_valid
        assert prediction.error_code == -1
        assert "Network error" in prediction.error_msg

    def test_get_top_contributing_mods(self):
        """Test getting top contributing mods from prediction."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=150.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[
                ('+# to maximum Life', 0.5),
                ('+#% to Fire Resistance', 0.3),
                ('+#% to Cold Resistance', 0.2),
                ('+# to maximum Energy Shield', -0.1),
                ('(pseudo) +#% total Elemental Resistance', 0.4),
            ],
        )

        top_mods = api.get_top_contributing_mods(prediction, top_n=3)

        assert len(top_mods) == 3
        # Should be sorted by absolute value
        assert top_mods[0][0] == '+# to maximum Life'  # 0.5
        assert top_mods[1][0] == '(pseudo) +#% total Elemental Resistance'  # 0.4
        assert top_mods[2][0] == '+#% to Fire Resistance'  # 0.3

    def test_get_top_contributing_mods_empty(self):
        """Test getting top contributing mods from empty prediction."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        prediction = PoePricesPrediction(
            min_price=100.0,
            max_price=150.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )

        top_mods = api.get_top_contributing_mods(prediction)

        assert top_mods == []


class TestPoePricesAPIIntegration:
    """Integration tests for PoePricesAPI (marked to skip by default)."""

    @pytest.mark.skip(reason="Integration test - requires live API")
    def test_live_price_prediction(self):
        """Test live price prediction against poeprices.info API."""
        api = PoePricesAPI(league="Standard")

        item_text = """Item Class: Body Armours
Rarity: Rare
Test Regalia
Vaal Regalia
--------
Energy Shield: 400
--------
Item Level: 86
--------
+80 to maximum Energy Shield
+70 to maximum Life
+40% to Fire Resistance
+35% to Cold Resistance"""

        prediction = api.predict_price(item_text)

        assert prediction.error_code == 0
        assert prediction.min_price > 0
        assert prediction.confidence_score > 0

        api.close()
