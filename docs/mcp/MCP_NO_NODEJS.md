# MCP Server Without Node.js

**Good News:** You can run the MCP server without installing Node.js!

## 🚀 Quick Start (No Node.js Needed)

### Method 1: Direct Python (Easiest)

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run the server directly
python mcp_poe_server.py
```

### Method 2: Use the Batch File

Just double-click: **`start_mcp_server.bat`**

That's it! The server will start and be ready for connections.

---

## 📝 What About the MCP CLI?

The `mcp` command (which requires Node.js/npx) provides:
- **`mcp dev`** - Web-based testing interface
- **`mcp install`** - Auto-configuration for Claude Desktop

But you don't actually need these! They're just convenience tools.

---

## 🔌 Connecting to AI Assistants

### Option 1: Claude Desktop (Manual Config)

1. **Start the MCP server:**
   ```bash
   python mcp_poe_server.py
   ```

2. **Edit Claude Desktop config:**
   - Open: `%APPDATA%\Claude\claude_desktop_config.json`
   - Add:
   ```json
   {
     "mcpServers": {
       "poe-price-checker": {
         "command": "python",
         "args": [
           "C:/Users/toddb/PycharmProjects/exilePriceCheck/mcp_poe_server.py"
         ],
         "cwd": "C:/Users/toddb/PycharmProjects/exilePriceCheck"
       }
     }
   }
   ```

3. **Restart Claude Desktop**

### Option 2: Continue (PyCharm)

You're already using Continue! Here's the config:

1. **Edit:** `~/.continue/config.json`

2. **Add:**
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

3. **Restart Continue/PyCharm**

### Option 3: Direct Testing (Python REPL)

```python
# Test the tools directly
from mcp_poe_server import parse_item, get_item_price, get_sales_summary

# Parse an item
result = parse_item("Rarity: Unique\nHeadhunter\nLeather Belt")
print(result)

# Get prices
prices = get_item_price("Headhunter", "Standard", "POE1")
print(prices)

# Get sales
sales = get_sales_summary(days=7)
print(sales)
```

---

## 🤔 Should I Install Node.js?

### Don't Install If:
- ✅ You just want the MCP server to work
- ✅ You're comfortable with manual configuration
- ✅ You prefer direct Python execution

### Do Install If:
- 🎯 You want the `mcp dev` web inspector (useful for testing)
- 🎯 You want `mcp install` auto-configuration
- 🎯 You're developing multiple MCP servers

**Node.js download:** https://nodejs.org/en/download/

---

## ✅ Verify It's Working

### Test 1: Start the Server

```bash
python mcp_poe_server.py
```

**Expected output:**
```
Configuration loaded successfully
Database initialized: C:\Users\toddb\.poe_price_checker\data.db
Starting PoE Price Checker MCP Server...
Database: C:\Users\toddb\.poe_price_checker\data.db
POE1 League: Standard
POE2 League: Standard
Server ready for MCP connections.
Press Ctrl+C to stop.
```

### Test 2: Check the Tools

```python
# In Python REPL
from mcp_poe_server import mcp

# List available tools
print(mcp.list_tools())

# Should show: parse_item, get_item_price, get_sales_summary, search_database
```

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'mcp'"

**Fix:**
```bash
pip install "mcp[cli]"
```

### Error: "Config file not found"

**Fix:** Run the main GUI once to create config:
```bash
python main.py
```

### Server Starts But AI Can't Connect

**Fix:** Check the JSON config for typos:
- Path uses forward slashes: `C:/Users/...`
- No trailing commas in JSON
- Valid JSON syntax (use jsonlint.com)

---

## 📊 What You Can Do Now

Even without Node.js, you can:

✅ Run the MCP server  
✅ Connect to Claude Desktop  
✅ Connect to Continue (PyCharm)  
✅ Use all MCP tools  
✅ Test functionality in Python  

The only things you're missing are:
- `mcp dev` web inspector (nice to have, not essential)
- `mcp install` auto-config (we did it manually above)

---

## 🎯 Recommended Next Steps

1. **Start the server:**
   ```bash
   python mcp_poe_server.py
   ```

2. **Leave it running in one terminal**

3. **Test in another terminal:**
   ```python
   from mcp_poe_server import get_item_price
   print(get_item_price("Headhunter"))
   ```

4. **If working, configure your AI assistant** (see above)

---

## 💡 Pro Tips

### Background Server (Windows)

Create a Windows Task Scheduler task to run the server on startup:

```
Program: C:\Users\toddb\PycharmProjects\exilePriceCheck\.venv\Scripts\python.exe
Arguments: mcp_poe_server.py
Start in: C:\Users\toddb\PycharmProjects\exilePriceCheck
Run: At startup
```

### Testing Without AI

You can test all functionality directly:

```python
# test_mcp_manual.py
from mcp_poe_server import *

# Test parsing
print("=== Test Item Parsing ===")
result = parse_item("""Rarity: Unique
Headhunter
Leather Belt
Item Level: 40
""")
print(result)

# Test prices
print("\n=== Test Price Lookup ===")
prices = get_item_price("Headhunter", "Standard", "POE1")
print(prices)

# Test sales
print("\n=== Test Sales Summary ===")
sales = get_sales_summary(days=30)
print(sales)
```

---

## 🎉 Summary

**You don't need Node.js!** Just run:

```bash
python mcp_poe_server.py
```

The MCP server will work perfectly with Python alone. Node.js is only needed for the optional CLI convenience tools.

---

**Last Updated:** 2025-01-23  
**Tested With:** Python 3.13.3, MCP SDK 1.22.0  
**Node.js Required:** ❌ No
