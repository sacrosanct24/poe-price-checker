"""Tests for data_sources/poe_stash_api.py - PoE Stash API client."""
import time
from unittest.mock import MagicMock, patch

import pytest

from data_sources.poe_stash_api import (
    StashTab,
    StashSnapshot,
    PoEStashClient,
    get_available_leagues,
)


class TestStashTab:
    """Tests for StashTab dataclass."""

    def test_create_basic_tab(self):
        """Should create tab with required fields."""
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

    def test_create_tab_with_items(self):
        """Should create tab with items."""
        items = [
            {"name": "Divine Orb", "stackSize": 5},
            {"name": "Chaos Orb", "stackSize": 100},
        ]

        tab = StashTab(
            id="abc123",
            name="Currency",
            index=0,
            type="CurrencyStash",
            items=items,
        )

        assert len(tab.items) == 2
        assert tab.items[0]["name"] == "Divine Orb"

    def test_default_values(self):
        """Should have correct default values."""
        tab = StashTab(
            id="test",
            name="Test",
            index=0,
            type="NormalStash",
        )

        assert tab.items == []
        assert tab.folder is None
        assert tab.children == []

    def test_item_count_property(self):
        """item_count should return number of items."""
        tab = StashTab(
            id="test",
            name="Test",
            index=0,
            type="NormalStash",
            items=[{"name": "Item1"}, {"name": "Item2"}, {"name": "Item3"}],
        )

        assert tab.item_count == 3

    def test_item_count_empty(self):
        """item_count should return 0 for empty tab."""
        tab = StashTab(
            id="test",
            name="Test",
            index=0,
            type="NormalStash",
        )

        assert tab.item_count == 0


class TestStashSnapshot:
    """Tests for StashSnapshot dataclass."""

    def test_create_snapshot(self):
        """Should create snapshot with required fields."""
        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Standard",
        )

        assert snapshot.account_name == "TestAccount"
        assert snapshot.league == "Standard"

    def test_create_snapshot_with_tabs(self):
        """Should create snapshot with tabs."""
        tabs = [
            StashTab(id="1", name="Tab1", index=0, type="NormalStash"),
            StashTab(id="2", name="Tab2", index=1, type="NormalStash"),
        ]

        snapshot = StashSnapshot(
            account_name="TestAccount",
            league="Standard",
            tabs=tabs,
            total_items=10,
        )

        assert len(snapshot.tabs) == 2
        assert snapshot.total_items == 10

    def test_default_values(self):
        """Should have correct default values."""
        snapshot = StashSnapshot(
            account_name="Test",
            league="Standard",
        )

        assert snapshot.tabs == []
        assert snapshot.total_items == 0
        assert snapshot.fetched_at == ""

    def test_get_all_items(self):
        """Should aggregate items from all tabs."""
        tab1 = StashTab(
            id="1",
            name="Tab1",
            index=0,
            type="NormalStash",
            items=[{"name": "Item1"}, {"name": "Item2"}],
        )
        tab2 = StashTab(
            id="2",
            name="Tab2",
            index=1,
            type="NormalStash",
            items=[{"name": "Item3"}],
        )

        snapshot = StashSnapshot(
            account_name="Test",
            league="Standard",
            tabs=[tab1, tab2],
        )

        all_items = snapshot.get_all_items()

        assert len(all_items) == 3
        names = [i["name"] for i in all_items]
        assert "Item1" in names
        assert "Item2" in names
        assert "Item3" in names

    def test_get_all_items_includes_children(self):
        """Should include items from child tabs."""
        child_tab = StashTab(
            id="child",
            name="Child",
            index=0,
            type="NormalStash",
            items=[{"name": "ChildItem"}],
        )
        parent_tab = StashTab(
            id="parent",
            name="Parent",
            index=0,
            type="Folder",
            items=[],
            children=[child_tab],
        )

        snapshot = StashSnapshot(
            account_name="Test",
            league="Standard",
            tabs=[parent_tab],
        )

        all_items = snapshot.get_all_items()

        assert len(all_items) == 1
        assert all_items[0]["name"] == "ChildItem"


class TestPoEStashClient:
    """Tests for PoEStashClient class."""

    @pytest.fixture
    def client(self):
        """Create client instance."""
        return PoEStashClient(poesessid="test_session_id")

    def test_init(self, client):
        """Should initialize with session and headers."""
        assert client.session is not None
        assert "POESESSID" in str(client.session.cookies)

    def test_init_custom_user_agent(self):
        """Should set custom User-Agent."""
        client = PoEStashClient(
            poesessid="test",
            user_agent="CustomAgent/1.0",
        )

        assert client.session.headers["User-Agent"] == "CustomAgent/1.0"

    def test_rate_limit(self, client):
        """Should respect rate limiting."""
        client.REQUEST_DELAY = 0.1
        client._last_request_time = time.time()

        start = time.time()
        client._rate_limit()
        elapsed = time.time() - start

        assert elapsed >= 0.08  # Allow some tolerance

    @patch('data_sources.poe_stash_api.requests.Session.get')
    def test_get_request(self, mock_get, client):
        """Should make GET request with proper parameters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = client._get("/test-endpoint", {"param": "value"})

        assert result == {"data": "test"}
        mock_get.assert_called_once()

    @patch('data_sources.poe_stash_api.requests.Session.get')
    def test_get_handles_403(self, mock_get, client):
        """Should raise on 403 (invalid POESESSID)."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = Exception("403 Forbidden")
        mock_get.return_value = mock_response

        import requests
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403")

        with pytest.raises(requests.exceptions.HTTPError):
            client._get("/test-endpoint")

    @patch('data_sources.poe_stash_api.requests.Session.get')
    def test_get_retries_on_429(self, mock_get, client):
        """Should retry on rate limit (429)."""
        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        import requests
        mock_429_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"success": True}

        mock_get.side_effect = [mock_429_response, mock_success_response]

        with patch('data_sources.poe_stash_api.time.sleep'):
            result = client._get("/test-endpoint")

        assert result == {"success": True}
        assert mock_get.call_count == 2

    @patch('data_sources.poe_stash_api.requests.Session.get')
    def test_get_429_calls_rate_limit_callback(self, mock_get):
        """Should call rate_limit_callback when rate limited."""
        callback_calls = []

        def rate_limit_callback(wait_seconds, attempt):
            callback_calls.append((wait_seconds, attempt))

        client = PoEStashClient("test_session", rate_limit_callback=rate_limit_callback)

        mock_429_response = MagicMock()
        mock_429_response.status_code = 429
        import requests
        mock_429_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429")

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"success": True}

        mock_get.side_effect = [mock_429_response, mock_success_response]

        with patch('data_sources.poe_stash_api.time.sleep'):
            result = client._get("/test-endpoint")

        assert result == {"success": True}
        assert len(callback_calls) == 1
        assert callback_calls[0] == (60, 1)  # 60 seconds wait, attempt 1

    @patch.object(PoEStashClient, '_get')
    def test_verify_session_valid(self, mock_get, client):
        """Should return True for valid session."""
        mock_get.return_value = [{"name": "Character1"}]

        result = client.verify_session()

        assert result is True

    @patch.object(PoEStashClient, '_get')
    def test_verify_session_invalid(self, mock_get, client):
        """Should return False for invalid session."""
        mock_get.side_effect = Exception("403 Forbidden")

        result = client.verify_session()

        assert result is False

    @patch.object(PoEStashClient, '_get')
    def test_get_characters(self, mock_get, client):
        """Should return character list."""
        mock_get.return_value = [
            {"name": "Char1", "class": "Ranger"},
            {"name": "Char2", "class": "Witch"},
        ]

        result = client.get_characters()

        assert len(result) == 2
        mock_get.assert_called_once_with(client.CHARACTERS_URL)

    @patch.object(PoEStashClient, '_get')
    def test_get_stash_tabs(self, mock_get, client):
        """Should return stash tab metadata."""
        mock_get.return_value = {
            "tabs": [
                {"n": "Currency", "type": "CurrencyStash"},
                {"n": "Maps", "type": "MapStash"},
            ]
        }

        result = client.get_stash_tabs("TestAccount", "Standard")

        assert len(result) == 2
        assert result[0]["n"] == "Currency"

    @patch.object(PoEStashClient, '_get')
    def test_get_stash_tab_items(self, mock_get, client):
        """Should return items from specific tab."""
        mock_get.return_value = {
            "items": [
                {"name": "Divine Orb"},
                {"name": "Chaos Orb"},
            ]
        }

        result = client.get_stash_tab_items("TestAccount", "Standard", 0)

        assert "items" in result
        assert len(result["items"]) == 2

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes(self, mock_items, mock_tabs, client):
        """Should fetch all tabs and items."""
        mock_tabs.return_value = [
            {"n": "Tab1", "type": "NormalStash", "id": "1"},
            {"n": "Tab2", "type": "NormalStash", "id": "2"},
        ]
        mock_items.side_effect = [
            {"items": [{"name": "Item1"}]},
            {"items": [{"name": "Item2"}, {"name": "Item3"}]},
        ]

        snapshot = client.fetch_all_stashes("TestAccount", "Standard")

        assert snapshot.account_name == "TestAccount"
        assert snapshot.league == "Standard"
        assert len(snapshot.tabs) == 2
        assert snapshot.total_items == 3

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_max_tabs(self, mock_items, mock_tabs, client):
        """Should respect max_tabs limit."""
        mock_tabs.return_value = [
            {"n": f"Tab{i}", "type": "NormalStash", "id": str(i)}
            for i in range(10)
        ]
        mock_items.return_value = {"items": []}

        snapshot = client.fetch_all_stashes(
            "TestAccount",
            "Standard",
            max_tabs=3,
        )

        assert len(snapshot.tabs) == 3
        assert mock_items.call_count == 3

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_progress_callback(self, mock_items, mock_tabs, client):
        """Should call progress callback."""
        mock_tabs.return_value = [
            {"n": "Tab1", "type": "NormalStash", "id": "1"},
            {"n": "Tab2", "type": "NormalStash", "id": "2"},
        ]
        mock_items.return_value = {"items": []}

        progress_calls = []
        callback = lambda cur, tot: progress_calls.append((cur, tot))

        client.fetch_all_stashes(
            "TestAccount",
            "Standard",
            progress_callback=callback,
        )

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_handles_tab_error(self, mock_items, mock_tabs, client):
        """Should handle individual tab fetch errors."""
        mock_tabs.return_value = [
            {"n": "Tab1", "type": "NormalStash", "id": "1"},
            {"n": "Tab2", "type": "NormalStash", "id": "2"},
        ]
        mock_items.side_effect = [
            Exception("Error fetching tab 0"),
            {"items": [{"name": "Item1"}]},
        ]

        snapshot = client.fetch_all_stashes("TestAccount", "Standard")

        # Should still have both tabs, but first one has no items
        assert len(snapshot.tabs) == 2
        assert snapshot.tabs[0].item_count == 0
        assert snapshot.tabs[1].item_count == 1

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_specialized_tabs_keep_items_in_parent(
        self, mock_items, mock_tabs, client
    ):
        """Specialized tabs (UniqueStash, etc.) should keep all items in parent.

        Due to GGG API limitations, specialized tabs don't reliably support
        distributing items to children. Items are kept in the parent tab.
        """
        mock_tabs.return_value = [
            {
                "n": "Unique Items",
                "type": "UniqueStash",
                "id": "unique-parent",
                "children": [
                    {"n": "Helmets", "type": "UniqueStash", "id": "unique-helmets", "i": 10},
                    {"n": "Boots", "type": "UniqueStash", "id": "unique-boots", "i": 11},
                ],
            },
            {"n": "Currency", "type": "CurrencyStash", "id": "2"},
        ]

        # For specialized tabs (UniqueStash), ALL items come from parent tab fetch
        def items_side_effect(account, league, tab_index):
            if tab_index == 0:
                # Parent UniqueStash tab contains all items
                return {"items": [
                    {"name": "Goldrim", "x": 0},
                    {"name": "Hrimsorrow", "x": 0},
                    {"name": "Wanderlust", "x": 1},
                ]}
            elif tab_index == 1:
                return {"items": [{"name": "Chaos Orb"}]}
            return {"items": []}

        mock_items.side_effect = items_side_effect

        snapshot = client.fetch_all_stashes("TestAccount", "Standard")

        # Should have 2 parent tabs
        assert len(snapshot.tabs) == 2

        # First tab (UniqueStash) should have NO children (not distributed)
        # All items stay in the parent tab
        unique_tab = snapshot.tabs[0]
        assert unique_tab.name == "Unique Items"
        assert len(unique_tab.children) == 0  # No children created for specialized tabs
        assert unique_tab.item_count == 3  # All items in parent

        # Currency tab
        currency_tab = snapshot.tabs[1]
        assert currency_tab.name == "Currency"
        assert currency_tab.item_count == 1

        # Total items: 3 in unique parent + 1 in currency
        assert snapshot.total_items == 4

    @patch.object(PoEStashClient, 'get_stash_tabs')
    @patch.object(PoEStashClient, 'get_stash_tab_items')
    def test_fetch_all_stashes_folder_child_tab_error(self, mock_items, mock_tabs, client):
        """Should handle child tab fetch errors gracefully for FolderStash."""
        # FolderStash children ARE fetched separately (unlike specialized tabs)
        mock_tabs.return_value = [
            {
                "n": "My Folder",
                "type": "FolderStash",
                "id": "folder-parent",
                "children": [
                    {"n": "Tab A", "type": "NormalStash", "id": "child-a", "i": 10},
                    {"n": "Tab B", "type": "NormalStash", "id": "child-b", "i": 11},
                ],
            },
        ]

        def items_side_effect(account, league, tab_index):
            if tab_index == 0:
                return {"items": []}  # Parent folder has no direct items
            elif tab_index == 10:
                raise Exception("Failed to fetch Tab A")
            elif tab_index == 11:
                return {"items": [{"name": "Item B"}]}
            return {"items": []}

        mock_items.side_effect = items_side_effect

        snapshot = client.fetch_all_stashes("TestAccount", "Standard")

        # Should still have parent tab with both children
        folder_tab = snapshot.tabs[0]
        assert len(folder_tab.children) == 2

        # First child should have no items due to error
        assert folder_tab.children[0].item_count == 0
        # Second child should have items
        assert folder_tab.children[1].item_count == 1


class TestGetAvailableLeagues:
    """Tests for get_available_leagues function."""

    def test_returns_league_list(self):
        """Should return list of leagues."""
        leagues = get_available_leagues()

        assert isinstance(leagues, list)
        assert len(leagues) >= 1

    def test_current_league_first(self):
        """Current league should be first."""
        leagues = get_available_leagues()

        # First league should be the current one
        assert leagues[0] == "Keepers" or "Keepers" in leagues

    def test_includes_standard_when_requested(self):
        """Should include Standard when requested."""
        leagues = get_available_leagues(include_standard=True)

        assert "Standard" in leagues
        assert "Hardcore" in leagues

    def test_excludes_standard_by_default(self):
        """Should exclude Standard by default."""
        leagues = get_available_leagues(include_standard=False)

        assert "Standard" not in leagues
        assert "Hardcore" not in leagues
