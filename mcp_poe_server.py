
"""
Custom MCP Server for PoE Price Checker
Exposes database queries and item parsing capabilities to AI assistants via MCP.
"""

from mcp.server.fastmcp import FastMCP
from pathlib import Path
from core.database import Database
from core.item_parser import ItemParser
from core.config import Config
from core.game_version import GameVersion
from datetime import datetime, timedelta, timezone
import json

# Create the MCP server
mcp = FastMCP("PoE Price Checker", dependencies=["requests"])

# Initialize core services
config = Config()
db = Database()
parser = ItemParser()

@mcp.tool()
def parse_item(item_text: str) -> dict:
    """
    Parse a Path of Exile item from clipboard text.
    
    Args:
        item_text: The raw text copied from PoE (Ctrl+C on item)
        
    Returns:
        Parsed item details including name, rarity, base type, etc.
    """
    parsed = parser.parse(item_text)
    if parsed is None:
        return {"error": "Failed to parse item text"}
    
    return {
        "name": parsed.name,
        "rarity": parsed.rarity if parsed.rarity else "Unknown",
        "base_type": parsed.base_type,
        "item_level": parsed.item_level,
        "corrupted": parsed.is_corrupted,
        "influenced": bool(getattr(parsed, 'influences', None)),
        "sockets": parsed.sockets,
        "links": parsed.links
    }

@mcp.tool()
def get_item_price(item_name: str, league: str = None, game: str = "POE1") -> dict:
    """
    Get recent price data for an item from the database.
    
    Args:
        item_name: Name of the item to look up
        league: League name (e.g., "Standard", "Crucible")
        game: Game version ("POE1" or "POE2")
        
    Returns:
        Price statistics and recent quotes
    """
    game_version = GameVersion.POE1 if game == "POE1" else GameVersion.POE2
    
    if league is None:
        league = config.get_game_config(game_version).league

    # Get price stats using the actual database method
    stats = db.get_latest_price_stats_for_item(game_version, league, item_name, days=7)

    if not stats:
        return {
            "item_name": item_name,
            "league": league,
            "game": game,
            "error": "No price data found",
            "suggestion": "Try checking the item in-game first to populate the database"
        }

    return {
        "item_name": item_name,
        "league": league,
        "game": game,
        "mean_price": stats.get("mean", 0),
        "median_price": stats.get("median", 0),
        "trimmed_mean": stats.get("trimmed_mean", 0),
        "min_price": stats.get("min", 0),
        "max_price": stats.get("max", 0),
        "p25": stats.get("p25", 0),
        "p75": stats.get("p75", 0),
        "sample_size": stats.get("count", 0),
        "stddev": stats.get("stddev", 0)
    }

@mcp.tool()
def get_sales_summary(days: int = 7) -> dict:
    """
    Get a summary of recent sales activity.
    
    Args:
        days: Number of days to look back (default: 7)
        
    Returns:
        Sales statistics and top items
    """
    # Get overall sales summary
    summary = db.get_sales_summary()

    # Get daily breakdown
    daily = db.get_daily_sales_summary(days=days)

    # Get recent sales
    recent = db.get_recent_sales(limit=10)

    return {
        "days": days,
        "total_sales": summary.get("total_sales", 0),
        "total_chaos": summary.get("total_chaos", 0),
        "average_chaos": summary.get("avg_chaos", 0),
        "daily_breakdown": [
            {
                "day": row["day"],
                "sales": row["sale_count"],
                "total_chaos": float(row["total_chaos"]),
                "avg_chaos": float(row["avg_chaos"])
            }
            for row in daily
        ],
        "recent_sales": [
            {
                "item": row["item_name"],
                "price": float(row["price_chaos"]),
                "source": row["source"],
                "sold_at": row["sold_at"]
            }
            for row in recent[:5]
        ]
    }

@mcp.tool()
def search_database(
    query: str,
    game: str = "POE1",
    league: str = None,
    limit: int = 10
) -> dict:
    """
    Search for items in the price database.
    
    Args:
        query: Search term (partial item name)
        game: Game version ("POE1" or "POE2")
        league: League name (optional)
        limit: Maximum results to return
        
    Returns:
        Matching items with price information
    """
    game_version = GameVersion.POE1 if game == "POE1" else GameVersion.POE2
    
    if league is None:
        league = config.get_game_config(game_version).league

    # This is a simplified search - you'd need to add a proper search method to Database
    # For now, we'll just show the concept
    
    return {
        "query": query,
        "game": game,
        "league": league,
        "message": "Database search functionality - implement db.search_items() for full functionality",
        "suggestion": f"Use get_item_price('{query}', '{league}', '{game}') for exact matches"
    }

@mcp.resource("config://current")
def get_current_config() -> str:
    """Get the current PoE Price Checker configuration."""
    return json.dumps({
        "poe1_league": config.get_game_config(GameVersion.POE1).league,
        "poe2_league": config.get_game_config(GameVersion.POE2).league,
        "current_game": config.current_game.name,
        "config_file": str(config.config_file),
        "database_path": str(db.db_path),
    }, indent=2)

@mcp.prompt()
def analyze_item_value(item_text: str) -> str:
    """
    Generate a prompt to analyze an item's value.
    
    Args:
        item_text: Raw item text from PoE clipboard
        
    Returns:
        A prompt for the LLM to analyze the item
    """
    return f"""Please analyze this Path of Exile item and provide pricing insights:

Item Text:
{item_text}

Tasks:
1. Parse the item details
2. Look up current market prices
3. Assess if this is a good deal
4. Provide recommendations for pricing if selling
5. Note any valuable mods or properties
"""

if __name__ == "__main__":
    # Run the MCP server
    #
    # Direct Python execution (no Node.js needed):
    #   python mcp_poe_server.py
    #
    # With MCP CLI (requires Node.js):
    #   mcp dev mcp_poe_server.py      # Testing with inspector
    #   mcp install mcp_poe_server.py  # Install to Claude Desktop
    #
    # The server will start and listen for MCP connections
    print("Starting PoE Price Checker MCP Server...")
    print(f"Config: {config.config_file}")
    print(f"Database: {db.db_path}")
    print(f"POE1 League: {config.get_game_config(GameVersion.POE1).league}")
    print(f"POE2 League: {config.get_game_config(GameVersion.POE2).league}")
    print("\nServer ready for MCP connections.")
    print("Press Ctrl+C to stop.\n")

    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
