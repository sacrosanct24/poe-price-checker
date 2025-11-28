---
title: MCP Setup Guide
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - mcp_poe_server.py
---

# MCP Setup Guide for PoE Price Checker

## What is MCP?

**Model Context Protocol (MCP)** is Anthropic's open standard that allows AI assistants like Claude to connect to your applications and data sources. Think of it as a "USB-C port for AI" - one standardized interface for all AI integrations.

## Why Add MCP to PoE Price Checker?

With MCP, you can:
- ✅ Ask Claude to **parse items** directly from clipboard text
- ✅ Query your **price database** using natural language
- ✅ Get **sales summaries** and statistics on command
- ✅ Have AI **analyze item values** automatically
- ✅ Search for items without opening the GUI

## Installation

### Step 1: Install MCP SDK

```bash
# From your project directory
cd C:\Users\toddb\PycharmProjects\exilePriceCheck

# Activate your virtual environment (if using one)
.venv\Scripts\activate

# Install MCP
pip install "mcp[cli]"
```

### Step 2: Verify Installation

```bash
# This should show MCP version info
python -c "import mcp; print(mcp.__version__)"
```

### Step 3: Test the MCP Server

```bash
# Run in development mode with MCP Inspector
mcp dev mcp_poe_server.py
```

This opens a web interface where you can test all the tools.

## Integration with Claude Desktop

### Option 1: Automatic Installation (Easiest)

```bash
# Install the server into Claude Desktop
mcp install mcp_poe_server.py
```

### Option 2: Manual Configuration

1. Open Claude Desktop configuration file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

2. Add this configuration:

```json
{
  "mcpServers": {
    "poe-price-checker": {
      "command": "python",
      "args": [
        "C:/Users/toddb/PycharmProjects/exilePriceCheck/mcp_poe_server.py"
      ]
    }
  }
}
```

3. Restart Claude Desktop

## Integration with Continue (Alternative Client)

Continue is another MCP-compatible client that works with PyCharm:

1. Create or edit `~/.continue/config.json`:

```json
{
  "mcpServers": {
    "poe-price-checker": {
      "command": "python",
      "args": [
        "C:/Users/toddb/PycharmProjects/exilePriceCheck/mcp_poe_server.py"
      ]
    }
  },
  "models": [
    {
      "title": "Claude with PoE Tools",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "apiKey": "your-api-key-here"
    }
  ]
}
```

2. Restart PyCharm or reload Continue

For more on Continue, see: https://continue.dev

## Available Tools

Once connected, I (the AI) will have access to these tools:

### 1. **parse_item**
```
Parse item text from PoE clipboard
Example: "Parse this item: [paste item text]"
```

### 2. **get_item_price**
```
Get current market prices for an item
Example: "What's the price of Headhunter in Standard league?"
```

### 3. **get_sales_summary**
```
Get sales statistics for recent activity
Example: "Show me sales from the last 7 days"
```

### 4. **search_database**
```
Search for items in the price database
Example: "Search for items matching 'Kaom'"
```

### Resources

- **config://current** - View current configuration

### Prompts

- **analyze_item_value** - Get AI analysis of an item's value

## Usage Examples

### Example 1: Parse and Price an Item

**You say:**
> I just found this item, what's it worth?
> [paste item text from PoE]

**I (AI) will:**
1. Parse the item using `parse_item` tool
2. Look up prices using `get_item_price` tool
3. Provide valuation and recommendations

### Example 2: Sales Analysis

**You say:**
> How much chaos have I made this week?

**I (AI) will:**
1. Use `get_sales_summary(days=7)` tool
2. Calculate total profit
3. Show top sales and trends

### Example 3: Item Search

**You say:**
> Find all items with "Watcher's Eye" in the database

**I (AI) will:**
1. Use `search_database` tool
2. Show matching items with prices
3. Provide market insights

## Advanced: Running as Standalone Web Server

If you want other LLMs (ChatGPT, Gemini, etc.) to access your price checker:

```python
# Create web_mcp_server.py
from mcp_poe_server import mcp

if __name__ == "__main__":
    # Run as HTTP server instead of stdio
    mcp.run(transport="http", host="localhost", port=8000)
```

Then run:
```bash
python web_mcp_server.py
```

Now any AI can access your price checker at `http://localhost:8000`

## Testing Your Setup

### Test 1: Check Server is Running

```bash
mcp dev mcp_poe_server.py
```

Expected: Web browser opens with MCP Inspector showing 4 tools

### Test 2: Test Tool Execution

In MCP Inspector, try:
```json
{
  "name": "parse_item",
  "arguments": {
    "item_text": "Rarity: Unique\nHeadhunter\nLeather Belt"
  }
}
```

Expected: Returns parsed item details

### Test 3: Test from Claude

In Claude Desktop, ask:
> "What tools do you have available?"

Expected: Claude lists your PoE Price Checker tools

## Troubleshooting

### Issue: "mcp command not found"

**Solution:**
```bash
pip install "mcp[cli]"
# or
python -m mcp dev mcp_poe_server.py
```

### Issue: "Import errors in mcp_poe_server.py"

**Solution:** Make sure you're running from project root:
```bash
cd C:\Users\toddb\PycharmProjects\exilePriceCheck
python mcp_poe_server.py
```

### Issue: "Claude doesn't see the tools"

**Solution:**
1. Check Claude Desktop config file is valid JSON
2. Use absolute paths in config
3. Restart Claude Desktop completely
4. Check logs in Claude: Help → View Logs

### Issue: "Database not found"

**Solution:** The MCP server uses your existing config. Make sure:
```python
# In mcp_poe_server.py, verify paths:
config = Config()  # Should load from default location
db = Database()    # Should find your database
```

## Security Considerations

⚠️ **Important:** Your MCP server has access to:
- Your price database (read/write)
- File system (through Database class)
- Network (poe.ninja API calls)

**Recommendations:**
- Don't expose the web server to public internet
- Use localhost only: `host="127.0.0.1"`
- Keep API keys in environment variables
- Review tool code before running

## Benefits vs. Traditional Setup

### Before MCP:
1. Open PoE Price Checker GUI
2. Copy item from game
3. Wait for parsing
4. Manually check prices
5. Switch windows constantly

### After MCP:
1. Copy item from game
2. Ask AI: "What's this worth?"
3. Get instant answer with context
4. AI can track sales automatically
5. Natural language queries: "Show profit last week"

## Next Steps

1. **Install MCP SDK** (15 seconds)
2. **Test with MCP Inspector** (2 minutes)
3. **Connect to Claude Desktop** (5 minutes)
4. **Try it out!** (Mind blown 🤯)

## Need Help?

- MCP Documentation: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Claude Desktop Download: https://claude.ai/download

## Changelog

### 2024-11-XX - Initial MCP Integration
- Added `mcp_poe_server.py` with 4 tools
- Added configuration guide
- Added testing instructions
- Integrated with existing Database and ItemParser classes

---

**Ready to try it?** Run:
```bash
pip install "mcp[cli]"
mcp dev mcp_poe_server.py
```
