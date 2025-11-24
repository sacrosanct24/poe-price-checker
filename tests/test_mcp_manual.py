"""
Manual test script for MCP server functionality.
Run this to verify the MCP server tools work correctly.
"""

from mcp_poe_server import (
    parse_item,
    get_item_price,
    get_sales_summary,
    search_database,
    get_current_config,
    config,
    db
)

print("="*60)
print("MCP Server Manual Test")
print("="*60)

# Test 1: Configuration
print("\n[TEST 1] Configuration")
print("-" * 40)
print(f"Config file: {config.config_file}")
print(f"Database: {db.db_path}")
print(f"Current league: {config.get_game_config().league}")
print(f"Current game: {config.current_game.name}")

# Test 2: Parse Item
print("\n[TEST 2] Parse Item")
print("-" * 40)
test_item = """Rarity: Unique
Headhunter
Leather Belt
Item Level: 40
"""
result = parse_item(test_item)
print(f"Parsed: {result}")

# Test 3: Get Item Price
print("\n[TEST 3] Get Item Price")
print("-" * 40)
price_result = get_item_price("Headhunter", "Standard", "POE1")
print(f"Price data: {price_result}")

# Test 4: Sales Summary
print("\n[TEST 4] Sales Summary")
print("-" * 40)
sales = get_sales_summary(days=30)
print(f"Total sales: {sales.get('total_sales', 0)}")
print(f"Total chaos: {sales.get('total_chaos', 0)}")
print(f"Average: {sales.get('average_chaos', 0):.2f}c")

# Test 5: Database Search
print("\n[TEST 5] Database Search")
print("-" * 40)
search = search_database("head", "POE1", "Standard", limit=5)
print(f"Search result: {search}")

# Test 6: Get Config Resource
print("\n[TEST 6] Config Resource")
print("-" * 40)
config_json = get_current_config()
print(f"Config resource:\n{config_json}")

# Test 7: Database Stats
print("\n[TEST 7] Database Stats")
print("-" * 40)
stats = db.get_stats()
print(f"Checked items: {stats.get('checked_items', 0)}")
print(f"Sales: {stats.get('sales', 0)}")
print(f"Price checks: {stats.get('price_checks', 0)}")
print(f"Price quotes: {stats.get('price_quotes', 0)}")

print("\n" + "="*60)
print("[SUCCESS] All tests completed successfully!")
print("="*60)
print("\nThe MCP server is ready to use.")
print("To start the server: python mcp_poe_server.py")
