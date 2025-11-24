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
from datetime import datetime, timedelta
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
        "rarity": parsed.rarity.name if parsed.rarity else "Unknown",
        "base_type": parsed.base_type,
        "item_level": parsed.item_level,
        "corrupted": parsed.corrupted,
        "influenced": bool(parsed.influence),
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
        league = config.get_league(game_version)
    
    # Get price stats
    stats = db.get_price_stats(game_version, league, item_name)
    
    # Get recent quotes
    quotes = db.get_quotes(game_version, league, item_name, limit=5)
    
    return {
        "item_name": item_name,
        "league": league,
        "game": game,
        "average_price": stats.get("average", 0) if stats else 0,
        "median_price": stats.get("median", 0) if stats else 0,
        "min_price": stats.get("min", 0) if stats else 0,
        "max_price": stats.get("max", 0) if stats else 0,
        "sample_size": stats.get("count", 0) if stats else 0,
        "recent_quotes": [
            {
                "price": q.chaos_value,
                "confidence": q.confidence,
                "timestamp": q.timestamp.isoformat() if q.timestamp else None
            }
            for q in quotes
        ]
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
    cutoff = datetime.now() - timedelta(days=days)
    
    # Get completed sales
    sales = db.get_sales_by_status("completed", limit=100)
    recent_sales = [s for s in sales if s.sold_at and s.sold_at >= cutoff]
    
    if not recent_sales:
        return {
            "days": days,
            "total_sales": 0,
            "total_value": 0,
            "message": "No sales in the specified period"
        }
    
    total_value = sum(s.actual_price for s in recent_sales if s.actual_price)
    
    return {
        "days": days,
        "total_sales": len(recent_sales),
        "total_value": total_value,
        "average_sale_price": total_value / len(recent_sales) if recent_sales else 0,
        "top_sales": [
            {
                "item": s.item_name,
                "price": s.actual_price,
                "date": s.sold_at.isoformat() if s.sold_at else None
            }
            for s in sorted(recent_sales, key=lambda x: x.actual_price or 0, reverse=True)[:5]
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
        league = config.get_league(game_version)
    
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
        "poe1_league": config.get_league(GameVersion.POE1),
        "poe2_league": config.get_league(GameVersion.POE2),
        "current_game": config.current_game.name,
        "database_path": str(config.db_path),
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
    # For Claude Desktop: mcp install mcp_poe_server.py
    # For testing: mcp dev mcp_poe_server.py
    mcp.run()
