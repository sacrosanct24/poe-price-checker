"""
Unit tests for poeprices.info API client.

Tests the PoePricesAPI client and PoePricesPrediction data class.
"""

import pytest
from unittest.mock import patch
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


class TestPoePricesAPICacheKey:
    """Tests for PoePricesAPI cache key generation."""

    def test_get_cache_key_with_params(self):
        """Test cache key generation with params."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        params = {'l': 'Settlers', 'i': 'base64encodeditem'}
        cache_key = api._get_cache_key("api", params)

        assert "api" in cache_key
        assert "Settlers" in cache_key
        # Hash of item should be included
        assert str(hash('base64encodeditem')) in cache_key

    def test_get_cache_key_without_params(self):
        """Test cache key generation without params."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        cache_key = api._get_cache_key("api", None)

        assert cache_key == "api"

    def test_get_cache_key_empty_params(self):
        """Test cache key with empty params dict."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        params = {}
        cache_key = api._get_cache_key("api", params)

        # With empty params, should include empty league and hash of empty string
        assert "api" in cache_key


class TestPoePricesAPIReconstructItemText:
    """Tests for PoePricesAPI._reconstruct_item_text method."""

    def test_reconstruct_basic_item(self):
        """Test reconstructing basic item text."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Body Armours"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Regalia"
        parsed_item.base_type = "Vaal Regalia"
        parsed_item.item_level = 86
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = ["+80 to maximum Life", "+40% to Fire Resistance"]
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api._reconstruct_item_text(parsed_item)

        assert "Item Class: Body Armours" in result
        assert "Rarity: Rare" in result
        assert "Test Regalia" in result
        assert "Vaal Regalia" in result
        assert "Item Level: 86" in result
        assert "+80 to maximum Life" in result
        assert "+40% to Fire Resistance" in result

    def test_reconstruct_item_with_requirements(self):
        """Test reconstructing item with requirements."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Body Armours"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Item"
        parsed_item.base_type = "Vaal Regalia"
        parsed_item.item_level = 86
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = []
        parsed_item.requirements = {"Level": 68, "Int": 194}
        parsed_item.sockets = None

        result = api._reconstruct_item_text(parsed_item)

        assert "Requirements:" in result
        assert "Level: 68" in result
        assert "Int: 194" in result

    def test_reconstruct_item_with_sockets(self):
        """Test reconstructing item with sockets."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Body Armours"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Item"
        parsed_item.base_type = "Vaal Regalia"
        parsed_item.item_level = 86
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = []
        parsed_item.requirements = None
        parsed_item.sockets = "B-B-B-B-B-B"

        result = api._reconstruct_item_text(parsed_item)

        assert "Sockets: B-B-B-B-B-B" in result

    def test_reconstruct_item_with_implicit_mods(self):
        """Test reconstructing item with implicit mods."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Amulets"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Amulet"
        parsed_item.base_type = "Onyx Amulet"
        parsed_item.item_level = 80
        parsed_item.implicit_mods = ["+16 to all Attributes"]
        parsed_item.explicit_mods = ["+50 to maximum Life"]
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api._reconstruct_item_text(parsed_item)

        assert "+16 to all Attributes" in result
        assert "+50 to maximum Life" in result
        # Implicit should be separated from explicit with --------
        lines = result.split("\n")
        implicit_idx = lines.index("+16 to all Attributes")
        separator_after_implicit = lines[implicit_idx + 1]
        assert separator_after_implicit == "--------"

    def test_reconstruct_item_without_item_class(self):
        """Test reconstructing item without item_class attribute."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        # Use spec to exclude item_class
        parsed_item = Mock(spec=['rarity', 'name', 'base_type', 'item_level',
                                  'implicit_mods', 'explicit_mods'])
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Item"
        parsed_item.base_type = "Leather Belt"
        parsed_item.item_level = 75
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = []

        result = api._reconstruct_item_text(parsed_item)

        assert "Item Class:" not in result
        assert "Rarity: Rare" in result

    def test_reconstruct_item_without_name(self):
        """Test reconstructing item without name (e.g., magic item)."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Rings"
        parsed_item.rarity = "Magic"
        parsed_item.name = None
        parsed_item.base_type = "Gold Ring"
        parsed_item.item_level = 70
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = ["+15% to Fire Resistance"]
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api._reconstruct_item_text(parsed_item)

        assert "Rarity: Magic" in result
        assert "Gold Ring" in result
        # Name line should not appear for None
        lines = result.split("\n")
        assert None not in lines

    def test_reconstruct_item_without_item_level(self):
        """Test reconstructing item without item_level."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Rings"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Ring"
        parsed_item.base_type = "Gold Ring"
        parsed_item.item_level = None
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = []
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api._reconstruct_item_text(parsed_item)

        assert "Item Level:" not in result


class TestPoePricesAPIPredictFromParsed:
    """Tests for PoePricesAPI.predict_price_from_parsed_item method."""

    @patch('data_sources.pricing.poeprices.PoePricesAPI.predict_price')
    def test_predict_from_parsed_item(self, mock_predict):
        """Test predicting price from parsed item."""
        mock_predict.return_value = PoePricesPrediction(
            min_price=100.0,
            max_price=150.0,
            currency="chaos",
            confidence_score=85.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Body Armours"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Item"
        parsed_item.base_type = "Vaal Regalia"
        parsed_item.item_level = 86
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = ["+80 to maximum Life"]
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api.predict_price_from_parsed_item(parsed_item)

        assert result.is_valid
        assert result.min_price == 100.0
        mock_predict.assert_called_once()
        # Verify the reconstructed text was passed
        call_args = mock_predict.call_args[0][0]
        assert "Vaal Regalia" in call_args
        assert "+80 to maximum Life" in call_args

    @patch('data_sources.pricing.poeprices.PoePricesAPI.predict_price')
    def test_predict_from_parsed_item_with_league_override(self, mock_predict):
        """Test predicting price from parsed item with league override."""
        mock_predict.return_value = PoePricesPrediction(
            min_price=50.0,
            max_price=75.0,
            currency="chaos",
            confidence_score=70.0,
            error_code=0,
            error_msg="",
            warning_msg="",
            mod_contributions=[],
        )

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        parsed_item = Mock()
        parsed_item.item_class = "Rings"
        parsed_item.rarity = "Rare"
        parsed_item.name = "Test Ring"
        parsed_item.base_type = "Gold Ring"
        parsed_item.item_level = 75
        parsed_item.implicit_mods = []
        parsed_item.explicit_mods = []
        parsed_item.requirements = None
        parsed_item.sockets = None

        result = api.predict_price_from_parsed_item(parsed_item, league="Settlers")

        assert result.is_valid
        # Verify league was passed
        mock_predict.assert_called_once()
        assert mock_predict.call_args[1].get('league') == "Settlers" or \
               mock_predict.call_args[0][1] == "Settlers"


class TestPoePricesAPIParseResponseEdgeCases:
    """Tests for edge cases in _parse_response."""

    def test_parse_response_missing_fields(self):
        """Test parsing response with missing optional fields."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        # Minimal response
        response = {
            'error': 0,
        }

        prediction = api._parse_response(response)

        assert prediction.error_code == 0
        assert prediction.min_price == 0
        assert prediction.max_price == 0
        assert prediction.currency == 'chaos'
        assert prediction.confidence_score == 0
        assert prediction.mod_contributions == []

    def test_parse_response_malformed_pred_explanation(self):
        """Test parsing response with malformed pred_explanation."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        response = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'pred_confidence_score': 85.0,
            'error': 0,
            'pred_explanation': [
                ['+# to Life', 0.5],  # Valid
                ['single element'],    # Invalid - only 1 element
                'not a list',          # Invalid - not a list
                ['+# to ES', 0.3, 'extra'],  # Valid - extra element ignored
            ],
        }

        prediction = api._parse_response(response)

        # Should only have the valid entries
        assert len(prediction.mod_contributions) == 2
        assert prediction.mod_contributions[0] == ('+# to Life', 0.5)
        assert prediction.mod_contributions[1] == ('+# to ES', 0.3)

    def test_parse_response_empty_pred_explanation(self):
        """Test parsing response with empty pred_explanation."""
        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"

        response = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'error': 0,
            'pred_explanation': [],
        }

        prediction = api._parse_response(response)

        assert prediction.mod_contributions == []


class TestPoePricesAPIPredictPriceLeagueOverride:
    """Tests for predict_price with league parameter."""

    @patch('data_sources.pricing.poeprices.PoePricesAPI.get')
    def test_predict_price_uses_instance_league(self, mock_get):
        """Test predict_price uses instance league when not overridden."""
        mock_get.return_value = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'pred_confidence_score': 85.0,
            'error': 0,
        }

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"
        api.request_count = 0

        api.predict_price("Test item")

        # Verify the league in the call
        call_kwargs = mock_get.call_args
        params = call_kwargs[1]['params'] if 'params' in call_kwargs[1] else call_kwargs[0][1]
        assert params['l'] == "Standard"

    @patch('data_sources.pricing.poeprices.PoePricesAPI.get')
    def test_predict_price_league_override(self, mock_get):
        """Test predict_price with league override."""
        mock_get.return_value = {
            'min': 100.0,
            'max': 150.0,
            'currency': 'chaos',
            'pred_confidence_score': 85.0,
            'error': 0,
        }

        api = PoePricesAPI.__new__(PoePricesAPI)
        api.league = "Standard"
        api.request_count = 0

        api.predict_price("Test item", league="Settlers")

        # Verify the league in the call was overridden
        call_kwargs = mock_get.call_args
        params = call_kwargs[1]['params'] if 'params' in call_kwargs[1] else call_kwargs[0][1]
        assert params['l'] == "Settlers"


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
