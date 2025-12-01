"""
Tests for PoE Stash API Client.

Tests the stash API client structure and data classes.
Network tests are mocked to avoid requiring real credentials.
"""
import pytest
from unittest.mock import Mock, patch

from data_sources.poe_stash_api import (
    StashTab,
    StashSnapshot,
    PoEStashClient,
    get_available_leagues,
)


class TestStashTab:
    """Tests for StashTab dataclass."""

    def test_basic_creation(self):
        """Test creating a basic stash tab."""
        tab = StashTab(
            id="abc123",
            name="Currency",
            index=0,
            type="CurrencyStash",
        )
        assert tab.id == "abc123"
        assert tab.name == "Currency"
        assert tab.index == 0
        assert tab.type == "CurrencyStash"
        assert tab.items == []
        assert tab.item_count == 0

    def test_with_items(self):
        """Test stash tab with items."""
        items = [
            {"typeLine": "Chaos Orb", "stackSize": 100},
            {"typeLine": "Exalted Orb", "stackSize": 5},
        ]
        tab = StashTab(
            id="abc123",
            name="Currency",
            index=0,
            type="CurrencyStash",
            items=items,
        )
        assert tab.item_count == 2
        assert tab.items[0]["typeLine"] == "Chaos Orb"

    def test_folder_support(self):
        """Test folder and children support."""
        child1 = StashTab(id="c1", name="Child 1", index=1, type="NormalStash")
        child2 = StashTab(id="c2", name="Child 2", index=2, type="NormalStash")

        parent = StashTab(
            id="p1",
            name="Folder",
            index=0,
            type="Folder",
            folder="My Folder",
            children=[child1, child2],
        )

        assert parent.folder == "My Folder"
        assert len(parent.children) == 2


class TestStashSnapshot:
    """Tests for StashSnapshot dataclass."""

    def test_basic_creation(self):
        """Test creating a basic snapshot."""
        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Phrecia",
        )
        assert snapshot.account_name == "TestAccount"
        assert snapshot.league == "Phrecia"
        assert snapshot.tabs == []
        assert snapshot.total_items == 0

    def test_get_all_items(self):
        """Test getting all items from snapshot."""
        tab1 = StashTab(
            id="t1", name="Tab 1", index=0, type="NormalStash",
            items=[{"typeLine": "Item A"}, {"typeLine": "Item B"}]
        )
        tab2 = StashTab(
            id="t2", name="Tab 2", index=1, type="NormalStash",
            items=[{"typeLine": "Item C"}]
        )

        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Phrecia",
            tabs=[tab1, tab2],
            total_items=3,
        )

        all_items = snapshot.get_all_items()
        assert len(all_items) == 3
        assert all_items[0]["typeLine"] == "Item A"
        assert all_items[2]["typeLine"] == "Item C"

    def test_get_all_items_with_children(self):
        """Test getting items including children tabs."""
        child = StashTab(
            id="c1", name="Child", index=1, type="NormalStash",
            items=[{"typeLine": "Child Item"}]
        )
        parent = StashTab(
            id="p1", name="Parent", index=0, type="Folder",
            items=[{"typeLine": "Parent Item"}],
            children=[child]
        )

        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Phrecia",
            tabs=[parent],
            total_items=2,
        )

        all_items = snapshot.get_all_items()
        assert len(all_items) == 2


class TestPoEStashClient:
    """Tests for PoEStashClient class."""

    def test_client_initialization(self):
        """Test client initializes correctly."""
        client = PoEStashClient("fake_session_id")

        assert client.session is not None
        assert "POESESSID" in client.session.cookies.keys()
        assert client.session.headers["User-Agent"] == "PoEPriceChecker/1.0"

    def test_custom_user_agent(self):
        """Test client with custom user agent."""
        client = PoEStashClient("fake_session_id", user_agent="CustomApp/2.0")

        assert client.session.headers["User-Agent"] == "CustomApp/2.0"

    def test_rate_limiting(self):
        """Test rate limiting logic."""
        client = PoEStashClient("fake_session_id")

        # First call should not delay
        import time
        start = time.time()
        client._rate_limit()
        first_elapsed = time.time() - start
        assert first_elapsed < 0.1  # Should be instant

        # Second immediate call should delay
        start = time.time()
        client._rate_limit()
        second_elapsed = time.time() - start
        assert second_elapsed >= 0.4  # Should delay ~0.5s

    @patch('requests.Session.get')
    def test_verify_session_success(self, mock_get):
        """Test successful session verification."""
        mock_response = Mock()
        mock_response.json.return_value = [{"name": "TestChar"}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PoEStashClient("valid_session_id")
        result = client.verify_session()

        assert result is True

    @patch('requests.Session.get')
    def test_verify_session_failure(self, mock_get):
        """Test failed session verification."""
        mock_get.side_effect = Exception("Connection failed")

        client = PoEStashClient("invalid_session_id")
        result = client.verify_session()

        assert result is False

    @patch('requests.Session.get')
    def test_get_characters(self, mock_get):
        """Test getting character list."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Char1", "level": 90},
            {"name": "Char2", "level": 85},
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PoEStashClient("session_id")
        chars = client.get_characters()

        assert len(chars) == 2
        assert chars[0]["name"] == "Char1"

    @patch('requests.Session.get')
    def test_get_stash_tabs(self, mock_get):
        """Test getting stash tab list."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tabs": [
                {"n": "Currency", "type": "CurrencyStash", "id": "t1"},
                {"n": "Maps", "type": "MapStash", "id": "t2"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PoEStashClient("session_id")
        tabs = client.get_stash_tabs("TestAccount", "Phrecia")

        assert len(tabs) == 2
        assert tabs[0]["n"] == "Currency"

        # Verify correct params were passed
        call_args = mock_get.call_args
        assert call_args[1]["params"]["accountName"] == "TestAccount"
        assert call_args[1]["params"]["league"] == "Phrecia"

    @patch('requests.Session.get')
    def test_get_stash_tab_items(self, mock_get):
        """Test getting items from a specific tab."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"typeLine": "Chaos Orb", "stackSize": 50},
                {"typeLine": "Divine Orb", "stackSize": 2},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = PoEStashClient("session_id")
        result = client.get_stash_tab_items("TestAccount", "Phrecia", 0)

        assert len(result["items"]) == 2
        assert result["items"][0]["typeLine"] == "Chaos Orb"

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes(self, mock_items, mock_tabs):
        """Test fetching all stashes."""
        # Mock tab list
        mock_tabs.return_value = [
            {"n": "Tab 1", "type": "NormalStash", "id": "t1"},
            {"n": "Tab 2", "type": "NormalStash", "id": "t2"},
        ]

        # Mock items for each tab
        mock_items.side_effect = [
            {"items": [{"typeLine": "Item A"}]},
            {"items": [{"typeLine": "Item B"}, {"typeLine": "Item C"}]},
        ]

        client = PoEStashClient("session_id")
        snapshot = client.fetch_all_stashes("TestAccount", "Phrecia")

        assert snapshot.account_name == "TestAccount"
        assert snapshot.league == "Phrecia"
        assert len(snapshot.tabs) == 2
        assert snapshot.total_items == 3
        assert snapshot.tabs[0].name == "Tab 1"
        assert snapshot.tabs[1].item_count == 2

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_with_max_tabs(self, mock_items, mock_tabs):
        """Test fetching with max_tabs limit."""
        mock_tabs.return_value = [
            {"n": "Tab 1", "type": "NormalStash", "id": "t1"},
            {"n": "Tab 2", "type": "NormalStash", "id": "t2"},
            {"n": "Tab 3", "type": "NormalStash", "id": "t3"},
        ]

        mock_items.return_value = {"items": []}

        client = PoEStashClient("session_id")
        snapshot = client.fetch_all_stashes("TestAccount", "Phrecia", max_tabs=2)

        assert len(snapshot.tabs) == 2
        assert mock_items.call_count == 2

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_with_progress(self, mock_items, mock_tabs):
        """Test progress callback is called."""
        mock_tabs.return_value = [
            {"n": "Tab 1", "type": "NormalStash", "id": "t1"},
            {"n": "Tab 2", "type": "NormalStash", "id": "t2"},
        ]
        mock_items.return_value = {"items": []}

        progress_calls = []
        def progress_callback(current, total):
            progress_calls.append((current, total))

        client = PoEStashClient("session_id")
        client.fetch_all_stashes("TestAccount", "Phrecia", progress_callback=progress_callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_handles_tab_error(self, mock_items, mock_tabs):
        """Test fetch continues when a tab fails."""
        mock_tabs.return_value = [
            {"n": "Tab 1", "type": "NormalStash", "id": "t1"},
            {"n": "Tab 2", "type": "NormalStash", "id": "t2"},
        ]

        # First tab fails, second succeeds
        mock_items.side_effect = [
            Exception("Tab fetch failed"),
            {"items": [{"typeLine": "Item"}]},
        ]

        client = PoEStashClient("session_id")
        snapshot = client.fetch_all_stashes("TestAccount", "Phrecia")

        # Should have both tabs, but first has no items
        assert len(snapshot.tabs) == 2
        assert snapshot.tabs[0].item_count == 0
        assert snapshot.tabs[1].item_count == 1


class TestGetAvailableLeagues:
    """Tests for league list function."""

    def test_returns_current_leagues(self):
        """Test that current leagues are returned by default."""
        leagues = get_available_leagues()

        assert len(leagues) >= 2
        assert "Keepers" in leagues  # Current league
        # Standard not included by default
        assert "Standard" not in leagues

    def test_includes_standard_when_requested(self):
        """Test Standard included when requested."""
        leagues = get_available_leagues(include_standard=True)

        assert "Keepers" in leagues
        assert "Standard" in leagues
        assert "Hardcore" in leagues

    def test_current_league_first(self):
        """Test current league is first in list."""
        leagues = get_available_leagues()

        assert leagues[0] == "Keepers"


class TestHTTPErrors:
    """Tests for HTTP error handling."""

    @patch('requests.Session.get')
    def test_403_error(self, mock_get):
        """Test handling of 403 forbidden."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
        mock_get.return_value = mock_response

        client = PoEStashClient("invalid_session")

        with pytest.raises(Exception):
            client._get("/test")

    @patch('requests.Session.get')
    def test_429_rate_limit_error(self, mock_get):
        """Test handling of 429 rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
        mock_get.return_value = mock_response

        client = PoEStashClient("session")

        with pytest.raises(Exception):
            client._get("/test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
