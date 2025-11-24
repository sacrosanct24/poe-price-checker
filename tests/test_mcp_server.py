"""
Tests for the MCP server implementation.
Tests tools, resources, and prompts exposed by mcp_poe_server.py

These tests will be skipped if MCP SDK is not installed.
To run these tests, install MCP: pip install "mcp[cli]"
"""

import pytest
from unittest.mock import Mock, patch
from core.item_parser import ItemParser, ParsedItem
from core.database import Database
from datetime import datetime, timedelta, timezone

# Check if MCP is available
try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Skip all tests in this module if MCP is not installed
pytestmark = pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP SDK not installed - install with: pip install 'mcp[cli]'")


class TestMCPServerTools:
    """Test the MCP server tool implementations"""
    
    @pytest.fixture
    def mock_parser(self):
        """Mock ItemParser for testing"""
        with patch('mcp_poe_server.parser') as mock:
            yield mock
    
    @pytest.fixture
    def mock_db(self):
        """Mock Database for testing"""
        with patch('mcp_poe_server.db') as mock:
            yield mock
    
    @pytest.fixture
    def mock_config(self):
        """Mock Config for testing"""
        with patch('mcp_poe_server.config') as mock:
            yield mock
    
    def test_parse_item_success(self, mock_parser):
        """Test successful item parsing"""
        # Setup mock
        mock_parsed = ParsedItem(
            raw_text="test",
            name="Headhunter",
            rarity="UNIQUE",
            base_type="Leather Belt",
            item_level=85,
            is_corrupted=False,
            sockets="",
            links=0
        )
        mock_parser.parse.return_value = mock_parsed
        
        # Import and test
        from mcp_poe_server import parse_item
        
        result = parse_item("Rarity: Unique\nHeadhunter\nLeather Belt")
        
        assert result["name"] == "Headhunter"
        assert result["rarity"] == "UNIQUE"
        assert result["base_type"] == "Leather Belt"
        assert result["item_level"] == 85
        assert result["corrupted"] is False
    
    def test_parse_item_failure(self, mock_parser):
        """Test item parsing failure"""
        mock_parser.parse.return_value = None
        
        from mcp_poe_server import parse_item
        
        result = parse_item("invalid text")
        
        assert "error" in result
        assert "Failed to parse" in result["error"]
    
    def test_get_item_price(self, mock_db, mock_config):
        """Test getting item price from database"""
        from core.game_version import GameVersion
        
        # Setup mocks
        mock_game_config = Mock()
        mock_game_config.league = "Standard"
        mock_config.get_game_config.return_value = mock_game_config

        mock_db.get_latest_price_stats_for_item.return_value = {
            "mean": 15000,
            "median": 14000,
            "min": 12000,
            "max": 18000,
            "count": 50,
            "trimmed_mean": 14500
        }
        
        from mcp_poe_server import get_item_price
        
        result = get_item_price("Headhunter", "Standard", "POE1")
        
        assert result["item_name"] == "Headhunter"
        assert result["league"] == "Standard"
        assert result["mean_price"] == 15000
        assert result["median_price"] == 14000
        assert result["sample_size"] == 50

    def test_get_sales_summary(self, mock_db):
        """Test getting sales summary"""
        # Setup mock to return summary dict matching Database.get_sales_summary() signature
        mock_db.get_sales_summary.return_value = {
            "total_sales": 1,
            "total_chaos": 15000,
            "avg_chaos": 15000
        }

        # Mock the daily and recent sales queries
        mock_db.get_daily_sales_summary.return_value = []
        mock_db.get_recent_sales.return_value = []

        from mcp_poe_server import get_sales_summary
        
        result = get_sales_summary(days=7)
        
        assert result.get("total_sales", 0) == 1
        assert result.get("total_chaos", 0) == 15000
        assert result.get("average_chaos", 0) == 15000

    def test_get_sales_summary_no_sales(self, mock_db):
        """Test sales summary with no sales"""
        mock_db.get_sales_summary.return_value = {
            "total_sales": 0,
            "total_chaos": 0,
            "avg_chaos": 0
        }

        # Mock the daily and recent sales queries
        mock_db.get_daily_sales_summary.return_value = []
        mock_db.get_recent_sales.return_value = []

        from mcp_poe_server import get_sales_summary
        
        result = get_sales_summary(days=7)
        
        assert result.get("total_sales", 0) == 0
        assert result.get("total_chaos", 0) == 0

    def test_search_database(self):
        """Test database search functionality"""
        from mcp_poe_server import search_database
        
        result = search_database("Kaom", "POE1", "Standard", 10)
        
        # Currently returns a placeholder
        assert result["query"] == "Kaom"
        assert result["game"] == "POE1"
        assert result["league"] == "Standard"
        assert "message" in result


class TestMCPServerIntegration:
    """Integration tests for the MCP server"""
    
    def test_mcp_server_imports(self):
        """Test that the MCP server module can be imported"""
        import mcp_poe_server
        assert hasattr(mcp_poe_server, 'mcp')
        assert hasattr(mcp_poe_server, 'parse_item')
        assert hasattr(mcp_poe_server, 'get_item_price')
        assert hasattr(mcp_poe_server, 'get_sales_summary')
        assert hasattr(mcp_poe_server, 'search_database')
    
    def test_mcp_server_has_required_dependencies(self):
        """Test that MCP dependencies are available"""
        from mcp.server.fastmcp import FastMCP
        assert FastMCP is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
