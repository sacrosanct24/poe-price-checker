"""Tests for core/passive_tree_data.py - Passive tree node data provider."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.passive_tree_data import (
    PassiveNode,
    PassiveTreeDataProvider,
    get_passive_tree_provider,
)


class TestPassiveNode:
    """Tests for PassiveNode dataclass."""

    def test_create_basic_node(self):
        """Should create a basic passive node."""
        node = PassiveNode(
            node_id=12345,
            name="Increased Life",
            is_notable=False,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=False,
            stats=["+10 to Maximum Life"],
        )

        assert node.node_id == 12345
        assert node.name == "Increased Life"
        assert node.stats == ["+10 to Maximum Life"]

    def test_node_type_keystone(self):
        """Keystone node should return 'keystone' type."""
        node = PassiveNode(
            node_id=1,
            name="Iron Reflexes",
            is_notable=False,
            is_keystone=True,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.node_type == "keystone"

    def test_node_type_notable(self):
        """Notable node should return 'notable' type."""
        node = PassiveNode(
            node_id=2,
            name="Constitution",
            is_notable=True,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.node_type == "notable"

    def test_node_type_mastery(self):
        """Mastery node should return 'mastery' type."""
        node = PassiveNode(
            node_id=3,
            name="Life Mastery",
            is_notable=False,
            is_keystone=False,
            is_mastery=True,
            is_ascendancy=False,
            stats=[],
        )

        assert node.node_type == "mastery"

    def test_node_type_ascendancy(self):
        """Ascendancy node should return 'ascendancy' type."""
        node = PassiveNode(
            node_id=4,
            name="Aspect of Carnage",
            is_notable=False,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=True,
            stats=[],
        )

        assert node.node_type == "ascendancy"

    def test_node_type_small(self):
        """Small node should return 'small' type."""
        node = PassiveNode(
            node_id=5,
            name="Small Life Node",
            is_notable=False,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.node_type == "small"

    def test_is_small_true(self):
        """Small node should have is_small = True."""
        node = PassiveNode(
            node_id=6,
            name="Small Node",
            is_notable=False,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.is_small is True

    def test_is_small_false_for_notable(self):
        """Notable should have is_small = False."""
        node = PassiveNode(
            node_id=7,
            name="Notable Node",
            is_notable=True,
            is_keystone=False,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.is_small is False

    def test_is_small_false_for_keystone(self):
        """Keystone should have is_small = False."""
        node = PassiveNode(
            node_id=8,
            name="Keystone Node",
            is_notable=False,
            is_keystone=True,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.is_small is False

    def test_node_type_priority(self):
        """Keystone takes priority over notable in node_type."""
        # This shouldn't happen in practice, but test the priority
        node = PassiveNode(
            node_id=9,
            name="Both",
            is_notable=True,
            is_keystone=True,
            is_mastery=False,
            is_ascendancy=False,
            stats=[],
        )

        assert node.node_type == "keystone"


class TestPassiveTreeDataProvider:
    """Tests for PassiveTreeDataProvider class."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temp cache directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def provider(self, temp_cache_dir):
        """Create provider with temp cache."""
        return PassiveTreeDataProvider(cache_dir=temp_cache_dir)

    @pytest.fixture
    def sample_tree_data(self):
        """Sample tree data for testing."""
        return {
            "nodes": {
                "100": {
                    "name": "Increased Life",
                    "isNotable": False,
                    "isKeystone": False,
                    "stats": ["+5 to Maximum Life"],
                },
                "200": {
                    "name": "Constitution",
                    "isNotable": True,
                    "isKeystone": False,
                    "stats": ["+8% to Maximum Life"],
                },
                "300": {
                    "name": "Iron Reflexes",
                    "isNotable": False,
                    "isKeystone": True,
                    "stats": ["Converts all Evasion Rating to Armour"],
                },
                "400": {
                    "name": "Life Mastery",
                    "isMastery": True,
                    "stats": [],
                },
                "500": {
                    "name": "Aspect of Carnage",
                    "ascendancyName": "Berserker",
                    "isNotable": True,
                    "stats": ["40% more Damage"],
                },
                "999": {
                    "isProxy": True,  # Should be skipped
                },
                "998": {
                    "isJewelSocket": True,  # Should be skipped
                },
            }
        }

    def test_init_creates_cache_dir(self, tmp_path):
        """Cache directory should be created on init."""
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        provider = PassiveTreeDataProvider(cache_dir=cache_dir)

        assert cache_dir.exists()

    def test_cache_path_property(self, provider, temp_cache_dir):
        """Should return correct cache path."""
        expected = temp_cache_dir / "passive_tree.json"
        assert provider.cache_path == expected

    def test_is_loaded_initially_false(self, provider):
        """is_loaded should be False initially."""
        assert provider.is_loaded() is False

    def test_get_stats_not_loaded(self, provider):
        """get_stats should show not loaded state."""
        stats = provider.get_stats()

        assert stats["loaded"] is False
        assert stats["node_count"] == 0

    @patch.object(PassiveTreeDataProvider, '_download_tree_data')
    def test_load_from_cache(self, mock_download, provider, temp_cache_dir, sample_tree_data):
        """Should load from cache file if it exists."""
        # Create cache file
        cache_file = temp_cache_dir / "passive_tree.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_tree_data, f)

        # Trigger load
        result = provider._load_data()

        assert result is True
        assert provider.is_loaded() is True
        mock_download.assert_not_called()

    @patch.object(PassiveTreeDataProvider, '_download_tree_data')
    def test_load_downloads_when_no_cache(self, mock_download, provider, sample_tree_data):
        """Should download when cache doesn't exist."""
        mock_download.return_value = sample_tree_data

        result = provider._load_data()

        assert result is True
        mock_download.assert_called_once()

    @patch.object(PassiveTreeDataProvider, '_download_tree_data')
    def test_load_once(self, mock_download, provider, sample_tree_data):
        """Should only load data once."""
        mock_download.return_value = sample_tree_data

        provider._load_data()
        provider._load_data()

        mock_download.assert_called_once()

    def test_parse_tree_data(self, provider, sample_tree_data):
        """Should parse tree data correctly."""
        provider._parse_tree_data(sample_tree_data)

        # Check parsed nodes
        assert 100 in provider._nodes
        assert provider._nodes[100].name == "Increased Life"
        assert provider._nodes[100].is_notable is False

        assert 200 in provider._nodes
        assert provider._nodes[200].is_notable is True

        assert 300 in provider._nodes
        assert provider._nodes[300].is_keystone is True

        assert 400 in provider._nodes
        assert provider._nodes[400].is_mastery is True

        assert 500 in provider._nodes
        assert provider._nodes[500].is_ascendancy is True

        # Proxy and jewel socket should be skipped
        assert 999 not in provider._nodes
        assert 998 not in provider._nodes

    @patch.object(PassiveTreeDataProvider, '_load_data')
    def test_get_node_triggers_load(self, mock_load, provider):
        """get_node should trigger data load."""
        mock_load.return_value = True

        provider.get_node(100)

        mock_load.assert_called_once()

    def test_get_node_returns_none_for_unknown(self, provider, sample_tree_data):
        """Should return None for unknown node ID."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        result = provider.get_node(99999)

        assert result is None

    def test_get_node_returns_node(self, provider, sample_tree_data):
        """Should return node for valid ID."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        result = provider.get_node(200)

        assert result is not None
        assert result.name == "Constitution"

    def test_get_node_name_found(self, provider, sample_tree_data):
        """Should return node name for valid ID."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        result = provider.get_node_name(200)

        assert result == "Constitution"

    def test_get_node_name_not_found(self, provider, sample_tree_data):
        """Should return 'Node X' for unknown ID."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        result = provider.get_node_name(99999)

        assert result == "Node 99999"

    def test_get_nodes_by_ids(self, provider, sample_tree_data):
        """Should return dict of found nodes."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        result = provider.get_nodes_by_ids([100, 200, 99999])

        assert 100 in result
        assert 200 in result
        assert 99999 not in result
        assert len(result) == 2

    def test_categorize_nodes(self, provider, sample_tree_data):
        """Should categorize nodes correctly."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        notables, keystones, small = provider.categorize_nodes([100, 200, 300])

        assert len(small) == 1
        assert small[0].node_id == 100

        assert len(notables) == 1
        assert notables[0].node_id == 200

        assert len(keystones) == 1
        assert keystones[0].node_id == 300

    def test_categorize_unknown_nodes(self, provider, sample_tree_data):
        """Unknown nodes should be treated as small."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        notables, keystones, small = provider.categorize_nodes([99999])

        assert len(small) == 1
        assert small[0].node_id == 99999
        assert small[0].name == "Node 99999"

    def test_get_stats_loaded(self, provider, sample_tree_data):
        """Should return correct stats when loaded."""
        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        stats = provider.get_stats()

        assert stats["loaded"] is True
        assert stats["node_count"] == 5  # 5 valid nodes (excluding proxy/jewel)
        assert stats["notables"] == 2  # Constitution and Aspect of Carnage
        assert stats["keystones"] == 1
        assert stats["masteries"] == 1

    def test_clear_cache(self, provider, temp_cache_dir, sample_tree_data):
        """Should clear cache and reset state."""
        # Create cache file
        cache_file = temp_cache_dir / "passive_tree.json"
        with open(cache_file, 'w') as f:
            json.dump(sample_tree_data, f)

        provider._parse_tree_data(sample_tree_data)
        provider._loaded = True

        provider.clear_cache()

        assert provider.is_loaded() is False
        assert len(provider._nodes) == 0
        assert not cache_file.exists()


class TestGetPassiveTreeProvider:
    """Tests for get_passive_tree_provider function."""

    def test_returns_singleton(self):
        """Should return singleton instance."""
        # Reset singleton
        import core.passive_tree_data
        core.passive_tree_data._provider = None

        provider1 = get_passive_tree_provider()
        provider2 = get_passive_tree_provider()

        assert provider1 is provider2

    def test_returns_provider_instance(self):
        """Should return PassiveTreeDataProvider instance."""
        import core.passive_tree_data
        core.passive_tree_data._provider = None

        provider = get_passive_tree_provider()

        assert isinstance(provider, PassiveTreeDataProvider)
