
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
from core.pob_integration import CharacterManager, UpgradeChecker, BuildCategory
from datetime import datetime, timedelta, timezone
import json

# Create the MCP server
mcp = FastMCP("PoE Price Checker", dependencies=["requests"])

# Initialize core services
config = Config()
db = Database()
parser = ItemParser()
character_manager = CharacterManager()
upgrade_checker = UpgradeChecker(character_manager)

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

@mcp.tool()
def list_characters() -> dict:
    """
    List all saved character profiles from Path of Building imports.

    Returns:
        List of character names and their basic info including categories
    """
    profiles = character_manager.list_profiles()
    active = character_manager.get_active_profile()
    upgrade_target = character_manager.get_upgrade_target()

    result = {
        "characters": [],
        "active_character": active.name if active else None,
        "upgrade_target": upgrade_target.name if upgrade_target and upgrade_target.is_upgrade_target else None,
        "total_count": len(profiles),
        "available_categories": character_manager.get_available_categories()
    }

    for name in profiles:
        profile = character_manager.get_profile(name)
        if profile:
            result["characters"].append({
                "name": name,
                "class": profile.build.class_name,
                "ascendancy": profile.build.ascendancy,
                "level": profile.build.level,
                "is_active": name == (active.name if active else None),
                "is_upgrade_target": profile.is_upgrade_target,
                "categories": profile.categories
            })

    return result


@mcp.tool()
def get_character_equipment(character_name: str = None) -> dict:
    """
    Get all equipped items for a character from their PoB build.

    Args:
        character_name: Name of the character (uses active character if not specified)

    Returns:
        All equipped items organized by slot with their mods
    """
    if character_name:
        profile = character_manager.get_profile(character_name)
    else:
        profile = character_manager.get_active_profile()

    if not profile:
        return {
            "error": "No character found",
            "suggestion": "Import a PoB build first using the GUI or add_character tool"
        }

    equipment = {
        "character": profile.name,
        "class": profile.build.class_name,
        "ascendancy": profile.build.ascendancy,
        "level": profile.build.level,
        "slots": {}
    }

    for slot, item in profile.build.items.items():
        equipment["slots"][slot] = {
            "name": item.name,
            "base_type": item.base_type,
            "rarity": item.rarity,
            "display_name": item.display_name,
            "item_level": item.item_level,
            "sockets": item.sockets,
            "links": item.link_count,
            "implicit_mods": item.implicit_mods,
            "explicit_mods": item.explicit_mods
        }

    return equipment


@mcp.tool()
def get_slot_item(slot: str, character_name: str = None) -> dict:
    """
    Get details about a specific equipment slot for a character.

    Args:
        slot: Equipment slot name (e.g., "Ring 1", "Ring 2", "Helmet", "Weapon", "Body Armour")
        character_name: Name of the character (uses active character if not specified)

    Returns:
        Detailed item information for that slot
    """
    if character_name:
        profile = character_manager.get_profile(character_name)
    else:
        profile = character_manager.get_active_profile()

    if not profile:
        return {"error": "No character found"}

    item = profile.get_item_for_slot(slot)

    if not item:
        # List available slots
        available_slots = list(profile.build.items.keys())
        return {
            "slot": slot,
            "error": f"No item in slot '{slot}'",
            "available_slots": available_slots
        }

    return {
        "character": profile.name,
        "slot": slot,
        "item": {
            "name": item.name,
            "base_type": item.base_type,
            "rarity": item.rarity,
            "display_name": item.display_name,
            "item_level": item.item_level,
            "sockets": item.sockets,
            "links": item.link_count,
            "implicit_mods": item.implicit_mods,
            "explicit_mods": item.explicit_mods
        }
    }


@mcp.tool()
def suggest_upgrades(slot_type: str, character_name: str = None) -> dict:
    """
    Get upgrade suggestions for a specific equipment slot type.
    Analyzes what stats to look for based on current gear.

    Args:
        slot_type: Type of slot to get upgrades for (e.g., "rings", "helmet", "boots", "gloves", "belt", "amulet", "body armour", "weapon")
        character_name: Name of the character (uses active character if not specified)

    Returns:
        Current item stats and suggestions for what to look for in upgrades
    """
    if character_name:
        profile = character_manager.get_profile(character_name)
    else:
        profile = character_manager.get_active_profile()

    if not profile:
        return {
            "error": "No character found",
            "suggestion": "Import a PoB build first"
        }

    # Normalize slot type to slot names
    slot_type_lower = slot_type.lower().strip()
    slot_mapping = {
        "ring": ["Ring 1", "Ring 2"],
        "rings": ["Ring 1", "Ring 2"],
        "helmet": ["Helmet"],
        "helm": ["Helmet"],
        "gloves": ["Gloves"],
        "boots": ["Boots"],
        "belt": ["Belt"],
        "amulet": ["Amulet"],
        "body armour": ["Body Armour"],
        "body armor": ["Body Armour"],
        "chest": ["Body Armour"],
        "weapon": ["Weapon"],
        "offhand": ["Offhand"],
        "shield": ["Offhand"],
    }

    slots_to_check = slot_mapping.get(slot_type_lower, [slot_type])

    result = {
        "character": profile.name,
        "slot_type": slot_type,
        "current_items": [],
        "upgrade_priorities": [],
        "stats_to_look_for": []
    }

    # Collect current items for these slots
    for slot in slots_to_check:
        item = profile.get_item_for_slot(slot)
        if item:
            # Analyze current mods
            has_life = any("life" in mod.lower() for mod in item.explicit_mods)
            has_res = any("resistance" in mod.lower() for mod in item.explicit_mods)
            has_es = any("energy shield" in mod.lower() for mod in item.explicit_mods)

            result["current_items"].append({
                "slot": slot,
                "name": item.display_name,
                "rarity": item.rarity,
                "key_stats": {
                    "has_life": has_life,
                    "has_resistances": has_res,
                    "has_energy_shield": has_es
                },
                "mods": item.explicit_mods
            })

            # Suggest what's missing
            if not has_life:
                result["upgrade_priorities"].append(f"{slot}: Add life roll")
            if not has_res:
                result["upgrade_priorities"].append(f"{slot}: Add resistances")
        else:
            result["current_items"].append({
                "slot": slot,
                "name": "EMPTY",
                "rarity": None,
                "key_stats": {},
                "mods": []
            })
            result["upgrade_priorities"].append(f"{slot}: Empty slot - any item is an upgrade!")

    # General upgrade suggestions based on slot type
    slot_suggestions = {
        "rings": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Adds # to # damage (if attack build)",
            "+# to Attributes (Str/Dex/Int)"
        ],
        "ring": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Adds # to # damage (if attack build)",
            "+# to Attributes (Str/Dex/Int)"
        ],
        "helmet": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Nearby enemies have -#% Resistance",
            "+# to Level of socketed gems"
        ],
        "helm": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Nearby enemies have -#% Resistance",
            "+# to Level of socketed gems"
        ],
        "gloves": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Attack Speed",
            "Adds # to # damage"
        ],
        "boots": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "#% increased Movement Speed",
            "Cannot be Chilled/Frozen"
        ],
        "belt": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "Flask modifiers",
            "+# to Strength"
        ],
        "amulet": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "+1 to Level of all Skill Gems",
            "Critical Strike Multiplier"
        ],
        "body armour": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "% increased maximum Life",
            "Additional Curse"
        ],
        "body armor": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "% increased maximum Life",
            "Additional Curse"
        ],
        "chest": [
            "+# to maximum Life",
            "+#% to Elemental Resistances",
            "% increased maximum Life",
            "Additional Curse"
        ],
        "weapon": [
            "High Physical DPS",
            "Critical Strike Chance",
            "Attack Speed",
            "+# to Level of socketed gems"
        ],
    }

    result["stats_to_look_for"] = slot_suggestions.get(slot_type_lower, [
        "+# to maximum Life",
        "+#% to Elemental Resistances",
        "Relevant damage mods for your build"
    ])

    return result


@mcp.tool()
def add_character(name: str, pob_code: str) -> dict:
    """
    Import a new character from a Path of Building code.

    Args:
        name: Name to save the character as
        pob_code: PoB share code or pastebin URL

    Returns:
        Success status and character details
    """
    try:
        profile = character_manager.add_from_pob_code(name, pob_code)
        return {
            "success": True,
            "character": {
                "name": profile.name,
                "class": profile.build.class_name,
                "ascendancy": profile.build.ascendancy,
                "level": profile.build.level,
                "items_count": len(profile.build.items)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
def set_active_character(name: str) -> dict:
    """
    Set which character to use for upgrade comparisons.

    Args:
        name: Name of the character to make active

    Returns:
        Success status
    """
    success = character_manager.set_active_profile(name)
    if success:
        return {
            "success": True,
            "message": f"'{name}' is now the active character"
        }
    else:
        available = character_manager.list_profiles()
        return {
            "success": False,
            "error": f"Character '{name}' not found",
            "available_characters": available
        }


@mcp.tool()
def set_upgrade_target(name: str) -> dict:
    """
    Mark a build as your upgrade target - the build you're actively gearing.
    This is the build that will be used when checking if items are upgrades.

    Args:
        name: Name of the character to mark as upgrade target

    Returns:
        Success status
    """
    success = character_manager.set_upgrade_target(name)
    if success:
        return {
            "success": True,
            "message": f"'{name}' is now your upgrade target build"
        }
    else:
        available = character_manager.list_profiles()
        return {
            "success": False,
            "error": f"Character '{name}' not found",
            "available_characters": available
        }


@mcp.tool()
def set_build_categories(name: str, categories: list) -> dict:
    """
    Set categories for a build (replaces existing categories).

    Available categories:
    - league_starter: Good for starting a new league
    - endgame: Optimized for endgame content
    - boss_killer: Specialized for boss fights
    - mapper: Fast map clearing build
    - budget: Low currency investment build
    - meta: Currently popular/strong build
    - experimental: Testing/theory crafting
    - reference: Reference build for comparison

    Args:
        name: Character name
        categories: List of category values

    Returns:
        Success status with updated categories
    """
    success = character_manager.set_build_categories(name, categories)
    if success:
        profile = character_manager.get_profile(name)
        return {
            "success": True,
            "message": f"Categories updated for '{name}'",
            "categories": profile.categories if profile else []
        }
    else:
        return {
            "success": False,
            "error": f"Character '{name}' not found or invalid categories",
            "available_categories": character_manager.get_available_categories()
        }


@mcp.tool()
def add_build_category(name: str, category: str) -> dict:
    """
    Add a single category to a build.

    Args:
        name: Character name
        category: Category to add (e.g., "meta", "league_starter", "endgame")

    Returns:
        Success status
    """
    success = character_manager.add_build_category(name, category)
    if success:
        profile = character_manager.get_profile(name)
        return {
            "success": True,
            "message": f"Added '{category}' to '{name}'",
            "categories": profile.categories if profile else []
        }
    else:
        return {
            "success": False,
            "error": f"Failed to add category. Character not found or invalid category.",
            "available_categories": character_manager.get_available_categories()
        }


@mcp.tool()
def remove_build_category(name: str, category: str) -> dict:
    """
    Remove a category from a build.

    Args:
        name: Character name
        category: Category to remove

    Returns:
        Success status
    """
    success = character_manager.remove_build_category(name, category)
    if success:
        profile = character_manager.get_profile(name)
        return {
            "success": True,
            "message": f"Removed '{category}' from '{name}'",
            "categories": profile.categories if profile else []
        }
    else:
        return {
            "success": False,
            "error": f"Failed to remove category"
        }


@mcp.tool()
def get_builds_by_category(category: str) -> dict:
    """
    Get all builds with a specific category.

    Args:
        category: Category to filter by (e.g., "meta", "league_starter", "endgame")

    Returns:
        List of builds with that category
    """
    builds = character_manager.get_builds_by_category(category)
    return {
        "category": category,
        "builds": [
            {
                "name": b.name,
                "class": b.build.class_name,
                "ascendancy": b.build.ascendancy,
                "level": b.build.level,
                "categories": b.categories,
                "is_upgrade_target": b.is_upgrade_target
            }
            for b in builds
        ],
        "count": len(builds)
    }


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
