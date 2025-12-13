"""
Unit tests for core.stash_scanner module - OAuth-based stash scanning.

Tests cover:
- Account name fetching
- Stash tab listing
- Stash item fetching
- Item parsing
- Full stash scanning
- Valuable item filtering
- Price integration
"""

import pytest
from unittest.mock import Mock, patch
import requests

from core.stash_scanner import StashScanner, StashItem, StashTab
from core.poe_oauth import PoeOAuthClient

pytestmark = pytest.mark.unit


# -------------------------
# Fixtures
# -------------------------

@pytest.fixture
def mock_oauth_client():
    """Create a mocked OAuth client."""
    oauth = Mock(spec=PoeOAuthClient)
    oauth.get_access_token.return_value = "mock_access_token"
    return oauth


# -------------------------
# StashItem Tests
# -------------------------

class TestStashItem:
    """Test StashItem dataclass."""

    def test_creates_stash_item(self):
        """Should create StashItem with required fields."""
        item = StashItem(
            name="Doom Crown",
            type_line="Hubris Circlet",
            rarity="RARE",
            stash_tab_name="Currency",
            stash_tab_index=0,
            position_x=5,
            position_y=3,
            ilvl=86,
            identified=True,
            corrupted=False,
            icon="https://example.com/icon.png"
        )

        assert item.name == "Doom Crown"
        assert item.rarity == "RARE"
        assert item.ilvl == 86

    def test_stash_item_has_default_price_info(self):
        """Should have default price values."""
        item = StashItem(
            name="Item",
            type_line="Type",
            rarity="RARE",
            stash_tab_name="Tab",
            stash_tab_index=0,
            position_x=0,
            position_y=0,
            ilvl=80,
            identified=True,
            corrupted=False,
            icon=""
        )

        assert item.chaos_value == 0.0
        assert item.divine_value == 0.0
        assert item.confidence == "unknown"

    def test_stash_item_str_representation(self):
        """Should have readable string representation."""
        item = StashItem(
            name="Doom Crown",
            type_line="Hubris Circlet",
            rarity="RARE",
            stash_tab_name="Currency",
            stash_tab_index=0,
            position_x=5,
            position_y=3,
            ilvl=86,
            identified=True,
            corrupted=False,
            icon=""
        )

        str_repr = str(item)
        assert "Doom Crown" in str_repr
        assert "Currency" in str_repr
        assert "(5, 3)" in str_repr


# -------------------------
# Initialization Tests
# -------------------------

class TestStashScannerInitialization:
    """Test StashScanner initialization."""

    @patch('core.stash_scanner.requests.get')
    def test_creates_scanner_with_defaults(self, mock_get, mock_oauth_client):
        """Should create scanner with default settings."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "TestAccount"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scanner = StashScanner(mock_oauth_client)

        assert scanner.oauth == mock_oauth_client
        assert scanner.league == "Standard"
        assert scanner.realm == "pc"
        assert scanner.account_name == "TestAccount"

    @patch('core.stash_scanner.requests.get')
    def test_creates_scanner_with_custom_league(self, mock_get, mock_oauth_client):
        """Should create scanner with custom league."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "TestAccount"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scanner = StashScanner(
            mock_oauth_client,
            league="Crucible",
            realm="pc"
        )

        assert scanner.league == "Crucible"

    @patch('core.stash_scanner.requests.get')
    def test_fetches_account_name_on_init(self, mock_get, mock_oauth_client):
        """Should fetch account name during initialization."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "MyAccount"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scanner = StashScanner(mock_oauth_client)

        assert scanner.account_name == "MyAccount"
        mock_get.assert_called_once()

    @patch('core.stash_scanner.requests.get')
    def test_raises_error_if_not_authenticated(self, mock_get):
        """Should raise error if OAuth client not authenticated."""
        oauth = Mock(spec=PoeOAuthClient)
        oauth.get_access_token.return_value = None  # Not authenticated

        with pytest.raises(ValueError, match="Not authenticated"):
            StashScanner(oauth)

    @patch('core.stash_scanner.requests.get')
    def test_raises_error_on_account_fetch_failure(self, mock_get, mock_oauth_client):
        """Should raise error if account fetch fails."""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            StashScanner(mock_oauth_client)


# -------------------------
# Account Name Fetching Tests
# -------------------------

class TestAccountNameFetching:
    """Test account name fetching."""

    @patch('core.stash_scanner.requests.get')
    def test_fetch_account_name_uses_bearer_token(self, mock_get, mock_oauth_client):
        """Should use bearer token in authorization header."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "TestAccount"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        StashScanner(mock_oauth_client)

        call_args = mock_get.call_args
        assert call_args[1]['headers']['Authorization'] == 'Bearer mock_access_token'

    @patch('core.stash_scanner.requests.get')
    def test_fetch_account_name_calls_profile_endpoint(self, mock_get, mock_oauth_client):
        """Should call profile API endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "TestAccount"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        StashScanner(mock_oauth_client)

        call_args = mock_get.call_args
        assert "api/profile" in call_args[0][0]

    @patch('core.stash_scanner.requests.get')
    def test_fetch_account_name_handles_missing_name(self, mock_get, mock_oauth_client):
        """Should raise error if account name not in response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # No 'name' field
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Could not determine account name"):
            StashScanner(mock_oauth_client)


# -------------------------
# Stash Tabs Fetching Tests
# -------------------------

class TestStashTabsFetching:
    """Test fetching stash tab list."""

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_tabs_returns_tab_list(self, mock_get, mock_oauth_client):
        """Should return list of stash tabs."""
        # Setup: Mock account fetch
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        # Mock stash tabs fetch
        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [
                {"i": 0, "n": "Currency", "type": "CurrencyStash"},
                {"i": 1, "n": "Maps", "type": "MapStash"}
            ]
        }
        tabs_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response]

        scanner = StashScanner(mock_oauth_client)
        tabs = scanner.get_stash_tabs()

        assert len(tabs) == 2
        assert tabs[0]["n"] == "Currency"
        assert tabs[1]["n"] == "Maps"

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_tabs_uses_correct_params(self, mock_get, mock_oauth_client):
        """Should use correct query parameters."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {"tabs": []}
        tabs_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response]

        scanner = StashScanner(mock_oauth_client, league="Crucible")
        scanner.get_stash_tabs()

        call_args = mock_get.call_args_list[1]  # Second call (tabs)
        params = call_args[1]['params']

        assert params['league'] == "Crucible"
        assert params['realm'] == "pc"
        assert params['accountName'] == "TestAccount"
        assert params['tabs'] == 1

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_tabs_raises_error_if_not_authenticated(self, mock_get, mock_oauth_client):
        """Should raise error if token expired."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.side_effect = [account_response]

        scanner = StashScanner(mock_oauth_client)

        # Make OAuth client return None (expired token)
        mock_oauth_client.get_access_token.return_value = None

        with pytest.raises(ValueError, match="Not authenticated"):
            scanner.get_stash_tabs()

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_tabs_handles_api_errors(self, mock_get, mock_oauth_client):
        """Should raise error on API failure."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        mock_get.side_effect = [
            account_response,
            requests.RequestException("API error")
        ]

        scanner = StashScanner(mock_oauth_client)

        with pytest.raises(requests.RequestException):
            scanner.get_stash_tabs()


# -------------------------
# Stash Items Fetching Tests
# -------------------------

class TestStashItemsFetching:
    """Test fetching items from a stash tab."""

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_items_returns_item_list(self, mock_get, mock_oauth_client):
        """Should return list of items from tab."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "Item 1", "typeLine": "Type 1"},
                {"name": "Item 2", "typeLine": "Type 2"}
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, items_response]

        scanner = StashScanner(mock_oauth_client)
        items = scanner.get_stash_items(tab_index=0)

        assert len(items) == 2
        assert items[0]["name"] == "Item 1"

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_items_uses_correct_params(self, mock_get, mock_oauth_client):
        """Should use correct query parameters including tab index."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {"items": []}
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, items_response]

        scanner = StashScanner(mock_oauth_client)
        scanner.get_stash_items(tab_index=5)

        call_args = mock_get.call_args_list[1]
        params = call_args[1]['params']

        assert params['tabIndex'] == 5
        assert params['tabs'] == 0  # Don't need tab metadata


# -------------------------
# Item Parsing Tests
# -------------------------

class TestItemParsing:
    """Test parsing item data into StashItem objects."""

    @patch('core.stash_scanner.requests.get')
    def test_parse_item_creates_stash_item(self, mock_get, mock_oauth_client):
        """Should parse item JSON into StashItem."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        item_data = {
            "name": "Doom Crown",
            "typeLine": "Hubris Circlet",
            "frameType": 2,  # RARE
            "x": 5,
            "y": 3,
            "ilvl": 86,
            "identified": True,
            "corrupted": False,
            "icon": "https://example.com/icon.png"
        }

        item = scanner._parse_item(item_data, "Currency", 0)

        assert item.name == "Doom Crown"
        assert item.type_line == "Hubris Circlet"
        assert item.rarity == "RARE"
        assert item.position_x == 5
        assert item.position_y == 3
        assert item.ilvl == 86
        assert item.identified is True
        assert item.corrupted is False

    @patch('core.stash_scanner.requests.get')
    def test_parse_item_maps_frame_types_correctly(self, mock_get, mock_oauth_client):
        """Should map frameType to rarity correctly."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        test_cases = [
            (0, "NORMAL"),
            (1, "MAGIC"),
            (2, "RARE"),
            (3, "UNIQUE"),
            (4, "GEM"),
            (5, "CURRENCY"),
            (6, "DIVINATION_CARD")
        ]

        for frame_type, expected_rarity in test_cases:
            item_data = {
                "name": "Test",
                "typeLine": "Type",
                "frameType": frame_type,
                "x": 0, "y": 0, "ilvl": 1,
                "identified": True, "corrupted": False, "icon": ""
            }

            item = scanner._parse_item(item_data, "Tab", 0)
            assert item.rarity == expected_rarity

    @patch('core.stash_scanner.requests.get')
    def test_parse_item_handles_missing_fields(self, mock_get, mock_oauth_client):
        """Should handle missing optional fields."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Minimal item data
        item_data = {
            "frameType": 2
        }

        item = scanner._parse_item(item_data, "Tab", 0)

        assert item.name == ""
        assert item.type_line == ""
        assert item.position_x == 0
        assert item.position_y == 0
        assert item.ilvl == 0

    @patch('core.stash_scanner.requests.get')
    def test_parse_item_returns_none_on_error(self, mock_get, mock_oauth_client):
        """Should return None if parsing fails."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Invalid item data (will cause exception)
        item_data = None

        item = scanner._parse_item(item_data, "Tab", 0)

        assert item is None


# -------------------------
# Full Scan Tests
# -------------------------

class TestFullStashScan:
    """Test scanning all stash tabs."""

    @patch('core.stash_scanner.requests.get')
    def test_scan_all_tabs_returns_stash_tab_list(self, mock_get, mock_oauth_client):
        """Should scan all tabs and return structured data."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [
                {"i": 0, "n": "Currency", "type": "CurrencyStash"},
                {"i": 1, "n": "Maps", "type": "MapStash"}
            ]
        }
        tabs_response.raise_for_status = Mock()

        items_response1 = Mock()
        items_response1.json.return_value = {
            "items": [{"name": "Chaos Orb", "typeLine": "Chaos Orb", "frameType": 5, "x": 0, "y": 0, "ilvl": 0, "identified": True, "corrupted": False, "icon": ""}]
        }
        items_response1.raise_for_status = Mock()

        items_response2 = Mock()
        items_response2.json.return_value = {
            "items": [{"name": "", "typeLine": "Beach Map", "frameType": 0, "x": 0, "y": 0, "ilvl": 70, "identified": True, "corrupted": False, "icon": ""}]
        }
        items_response2.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response1, items_response2]

        scanner = StashScanner(mock_oauth_client)
        stash_tabs = scanner.scan_all_tabs()

        assert len(stash_tabs) == 2
        assert stash_tabs[0].name == "Currency"
        assert stash_tabs[0].index == 0
        assert len(stash_tabs[0].items) == 1
        assert stash_tabs[1].name == "Maps"
        assert len(stash_tabs[1].items) == 1


# -------------------------
# Valuable Item Filtering Tests
# -------------------------

class TestValuableItemFiltering:
    """Test filtering valuable items."""

    @patch('core.stash_scanner.requests.get')
    def test_filter_valuable_items_by_chaos_value(self, mock_get, mock_oauth_client):
        """Should filter items by minimum chaos value."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Create test data
        item1 = StashItem("Item1", "Type1", "RARE", "Tab", 0, 0, 0, 80, True, False, "")
        item1.chaos_value = 50.0

        item2 = StashItem("Item2", "Type2", "UNIQUE", "Tab", 0, 0, 0, 80, True, False, "")
        item2.chaos_value = 5.0

        item3 = StashItem("Item3", "Type3", "RARE", "Tab", 0, 0, 0, 80, True, False, "")
        item3.chaos_value = 100.0

        tab = StashTab("TestTab", 0, "NormalStash", [item1, item2, item3])

        valuable = scanner.filter_valuable_items([tab], min_chaos_value=10.0)

        assert len(valuable) == 2
        assert valuable[0][1].chaos_value == 50.0
        assert valuable[1][1].chaos_value == 100.0


# -------------------------
# Build Item Text Tests
# -------------------------

class TestBuildItemText:
    """Test building pseudo-item text from StashItem."""

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_includes_rarity(self, mock_get, mock_oauth_client):
        """Should include rarity in item text."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        item = StashItem("Doom Crown", "Hubris Circlet", "RARE", "Tab", 0, 0, 0, 86, True, False, "")

        item_text = scanner._build_item_text(item)

        assert "Rarity: RARE" in item_text

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_includes_name_and_type(self, mock_get, mock_oauth_client):
        """Should include name and type line."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        item = StashItem("Doom Crown", "Hubris Circlet", "RARE", "Tab", 0, 0, 0, 86, True, False, "")

        item_text = scanner._build_item_text(item)

        assert "Doom Crown" in item_text
        assert "Hubris Circlet" in item_text

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_includes_ilvl(self, mock_get, mock_oauth_client):
        """Should include item level."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        item = StashItem("Item", "Type", "RARE", "Tab", 0, 0, 0, 86, True, False, "")

        item_text = scanner._build_item_text(item)

        assert "Item Level: 86" in item_text

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_includes_corrupted(self, mock_get, mock_oauth_client):
        """Should include Corrupted for corrupted items."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        item = StashItem("Item", "Type", "RARE", "Tab", 0, 0, 0, 86, True, True, "")  # corrupted=True

        item_text = scanner._build_item_text(item)

        assert "Corrupted" in item_text

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_without_name(self, mock_get, mock_oauth_client):
        """Should handle items without name (just type_line)."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Item with no name, just type_line (common for currency)
        item = StashItem("", "Chaos Orb", "CURRENCY", "Tab", 0, 0, 0, 0, True, False, "")

        item_text = scanner._build_item_text(item)

        assert "Chaos Orb" in item_text
        assert "Rarity: CURRENCY" in item_text

    @patch('core.stash_scanner.requests.get')
    def test_build_item_text_without_type_line(self, mock_get, mock_oauth_client):
        """Should handle items without type_line."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Item with name but no type_line
        item = StashItem("Special Item", "", "UNIQUE", "Tab", 0, 0, 0, 50, True, False, "")

        item_text = scanner._build_item_text(item)

        assert "Special Item" in item_text


# -------------------------
# Stash Items API Error Tests
# -------------------------

class TestStashItemsApiErrors:
    """Test error handling for stash items API."""

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_items_raises_if_not_authenticated(self, mock_get, mock_oauth_client):
        """Should raise error if not authenticated."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()
        mock_get.return_value = account_response

        scanner = StashScanner(mock_oauth_client)

        # Make OAuth return None (expired token)
        mock_oauth_client.get_access_token.return_value = None

        with pytest.raises(ValueError, match="Not authenticated"):
            scanner.get_stash_items(tab_index=0)

    @patch('core.stash_scanner.requests.get')
    def test_get_stash_items_handles_api_error(self, mock_get, mock_oauth_client):
        """Should raise error on API failure."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        mock_get.side_effect = [
            account_response,
            requests.RequestException("API error")
        ]

        scanner = StashScanner(mock_oauth_client)

        with pytest.raises(requests.RequestException):
            scanner.get_stash_items(tab_index=0)


# -------------------------
# Scan and Price Tests
# -------------------------

class TestScanAndPrice:
    """Test scan_and_price integration."""

    @patch('core.stash_scanner.requests.get')
    def test_scan_and_price_prices_items(self, mock_get, mock_oauth_client):
        """Should price check items during scan."""
        # Setup mock responses
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [
                {"i": 0, "n": "Currency", "type": "CurrencyStash"},
            ]
        }
        tabs_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "", "typeLine": "Chaos Orb", "frameType": 5, "x": 0, "y": 0, "ilvl": 0, "identified": True, "corrupted": False, "icon": ""},
                {"name": "", "typeLine": "Divine Orb", "frameType": 5, "x": 1, "y": 0, "ilvl": 0, "identified": True, "corrupted": False, "icon": ""},
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response]

        # Setup mock price service
        mock_price_service = Mock()
        mock_price_service.check_item.side_effect = [
            [{"chaos_value": 1.0, "divine_value": 0.0, "source": "poe_ninja"}],
            [{"chaos_value": 200.0, "divine_value": 1.0, "source": "poe_ninja"}],
        ]

        scanner = StashScanner(mock_oauth_client)
        valuable = scanner.scan_and_price(mock_price_service, min_chaos_value=10.0)

        # Should have 1 valuable item (Divine Orb >= 10c)
        assert len(valuable) == 1
        assert valuable[0][1].chaos_value == 200.0

    @patch('core.stash_scanner.requests.get')
    def test_scan_and_price_handles_pricing_errors(self, mock_get, mock_oauth_client):
        """Should handle price service errors gracefully."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [{"i": 0, "n": "Tab", "type": "NormalStash"}]
        }
        tabs_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "Item", "typeLine": "Type", "frameType": 2, "x": 0, "y": 0, "ilvl": 80, "identified": True, "corrupted": False, "icon": ""},
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response]

        # Price service raises error
        mock_price_service = Mock()
        mock_price_service.check_item.side_effect = Exception("Price API error")

        scanner = StashScanner(mock_oauth_client)

        # Should not raise - error is logged, item stays at 0 value
        # With min_chaos_value=1.0, items with 0 value are filtered out
        valuable = scanner.scan_and_price(mock_price_service, min_chaos_value=1.0)
        assert valuable == []

    @patch('core.stash_scanner.requests.get')
    def test_scan_and_price_handles_empty_results(self, mock_get, mock_oauth_client):
        """Should handle empty price results."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [{"i": 0, "n": "Tab", "type": "NormalStash"}]
        }
        tabs_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "Item", "typeLine": "Type", "frameType": 2, "x": 0, "y": 0, "ilvl": 80, "identified": True, "corrupted": False, "icon": ""},
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response]

        # Price service returns empty list
        mock_price_service = Mock()
        mock_price_service.check_item.return_value = []

        scanner = StashScanner(mock_oauth_client)
        # Items with 0 value should be filtered out with min_chaos_value=1.0
        valuable = scanner.scan_and_price(mock_price_service, min_chaos_value=1.0)

        assert valuable == []

    @patch('core.stash_scanner.requests.get')
    def test_scan_and_price_handles_none_values(self, mock_get, mock_oauth_client):
        """Should handle None chaos/divine values."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [{"i": 0, "n": "Tab", "type": "NormalStash"}]
        }
        tabs_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "Item", "typeLine": "Type", "frameType": 2, "x": 0, "y": 0, "ilvl": 80, "identified": True, "corrupted": False, "icon": ""},
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response]

        # Price service returns None values
        mock_price_service = Mock()
        mock_price_service.check_item.return_value = [
            {"chaos_value": None, "divine_value": None, "source": "poe_ninja"}
        ]

        scanner = StashScanner(mock_oauth_client)
        valuable = scanner.scan_and_price(mock_price_service, min_chaos_value=10.0)

        # Should not crash, item gets 0 value
        assert valuable == []

    @patch('core.stash_scanner.requests.get')
    def test_scan_and_price_accumulates_tab_totals(self, mock_get, mock_oauth_client):
        """Should accumulate total tab values."""
        account_response = Mock()
        account_response.json.return_value = {"name": "TestAccount"}
        account_response.raise_for_status = Mock()

        tabs_response = Mock()
        tabs_response.json.return_value = {
            "tabs": [{"i": 0, "n": "Tab", "type": "NormalStash"}]
        }
        tabs_response.raise_for_status = Mock()

        items_response = Mock()
        items_response.json.return_value = {
            "items": [
                {"name": "Item1", "typeLine": "Type1", "frameType": 2, "x": 0, "y": 0, "ilvl": 80, "identified": True, "corrupted": False, "icon": ""},
                {"name": "Item2", "typeLine": "Type2", "frameType": 2, "x": 1, "y": 0, "ilvl": 80, "identified": True, "corrupted": False, "icon": ""},
            ]
        }
        items_response.raise_for_status = Mock()

        mock_get.side_effect = [account_response, tabs_response, items_response]

        mock_price_service = Mock()
        mock_price_service.check_item.side_effect = [
            [{"chaos_value": 100.0, "divine_value": 0.5, "source": "poe_ninja"}],
            [{"chaos_value": 50.0, "divine_value": 0.25, "source": "poe_ninja"}],
        ]

        scanner = StashScanner(mock_oauth_client)
        valuable = scanner.scan_and_price(mock_price_service, min_chaos_value=1.0)

        # Both items should be valuable
        assert len(valuable) == 2

        # Tab totals should be accumulated (150c total)
        tab = valuable[0][0]
        assert tab.total_value_chaos == 150.0
        assert tab.total_value_divine == 0.75


# -------------------------
# StashItem __str__ Tests
# -------------------------

class TestStashItemStr:
    """Test StashItem string representation."""

    def test_str_uses_type_line_when_name_empty(self):
        """Should use type_line when name is empty."""
        item = StashItem(
            name="",
            type_line="Chaos Orb",
            rarity="CURRENCY",
            stash_tab_name="Currency",
            stash_tab_index=0,
            position_x=0,
            position_y=0,
            ilvl=0,
            identified=True,
            corrupted=False,
            icon=""
        )

        str_repr = str(item)
        assert "Chaos Orb" in str_repr
        assert "Currency" in str_repr
