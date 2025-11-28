---
title: MCP Quick Start
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - mcp_poe_server.py
---

# MCP Quick Start - PoE Price Checker

## 30-Second Install

```bash
cd C:\Users\toddb\PycharmProjects\exilePriceCheck
.venv\Scripts\activate
pip install "mcp[cli]"
mcp dev mcp_poe_server.py
```

## 2-Minute Test

In the MCP Inspector that opens, try:

### Test 1: Parse an Item
```json
{
  "name": "parse_item",
  "arguments": {
    "item_text": "Rarity: Unique\nHeadhunter\nLeather Belt"
  }
}
```

### Test 2: Get Price
```json
{
  "name": "get_item_price",
  "arguments": {
    "item_name": "Headhunter",
    "league": "Standard",
    "game": "POE1"
  }
}
```

### Test 3: Sales Summary
```json
{
  "name": "get_sales_summary",
  "arguments": {
    "days": 7
  }
}
```

## 5-Minute Setup with Claude

### Option 1: Auto-Install
```bash
mcp install mcp_poe_server.py
```

### Option 2: Manual Config
Edit `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "poe-price-checker": {
      "command": "python",
      "args": ["C:/Users/toddb/PycharmProjects/exilePriceCheck/mcp_poe_server.py"]
    }
  }
}
```

Restart Claude Desktop.

## What You Can Ask Me (AI)

### Price Checking
- "What's Headhunter worth in Standard?"
- "Parse this item: [paste]"
- "Is this a good price for Mageblood?"

### Sales Tracking
- "Show me sales from last week"
- "How much chaos did I make today?"
- "What's my top selling item?"

### Database Queries
- "Find all items with 'Watcher's Eye'"
- "Show me current config"
- "What items are in the database?"

### Analysis
- "Analyze this item: [paste]"
- "Should I sell this now or wait?"
- "Compare prices across leagues"

## Available Tools

| Tool | What It Does | Example |
|------|-------------|---------|
| `parse_item` | Parse PoE item text | "Parse this: [item text]" |
| `get_item_price` | Get market prices | "Price of Tabula Rasa?" |
| `get_sales_summary` | Sales statistics | "Show sales last 7 days" |
| `search_database` | Find items | "Search for Kaom" |

## Troubleshooting

### "mcp not found"
```bash
pip install "mcp[cli]"
```

### "Import errors"
```bash
# Make sure you're in project root
cd C:\Users\toddb\PycharmProjects\exilePriceCheck
```

### "Claude doesn't see tools"
1. Check config file is valid JSON
2. Use absolute paths
3. Restart Claude Desktop completely

### "Database not found"
Check that your database exists:
```bash
python -c "from core.config import Config; print(Config().db_path)"
```

## Next Steps

1. ✅ Install MCP SDK
2. ✅ Test with MCP Inspector
3. ✅ Connect to Claude Desktop
4. ✅ Try parsing an item from PoE
5. ✅ Ask me: "What can you do?"

## Full Docs

- **Setup Guide**: `MCP_SETUP_GUIDE.md` - Complete instructions
- **Recommendation**: `MCP_RECOMMENDATION.md` - Why use MCP?
- **Server Code**: `mcp_poe_server.py` - The implementation
- **Tests**: `tests/test_mcp_server.py` - Verify it works

## One-Liner Summary

**Give your AI assistant direct access to your PoE Price Checker database and item parser through natural language queries.**

---

**Ready?** Run this now:
```bash
pip install "mcp[cli]" && mcp dev mcp_poe_server.py
```
