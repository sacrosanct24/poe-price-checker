# Claude Desktop Configuration Fix

## Issue

The auto-installer tried to use `uv` (a modern Python package manager) which you don't have installed. Let's fix it to use your existing Python environment.

## Solution

### Option 1: Manual Config Fix (Recommended)

1. **Close Claude Desktop completely**

2. **Edit the config file:**
   - Location: `%APPDATA%\Claude\claude_desktop_config.json`
   - Or: `C:\Users\toddb\AppData\Roaming\Claude\claude_desktop_config.json`

3. **Replace the contents with:**

```json
{
  "mcpServers": {
    "PoE Price Checker": {
      "command": "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck\\mcp_poe_server.py"
      ]
    }
  }
}
```

4. **Save and restart Claude Desktop**

### Option 2: Use System Python

If your venv path is different, use this instead:

```json
{
  "mcpServers": {
    "PoE Price Checker": {
      "command": "python",
      "args": [
        "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck\\mcp_poe_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck"
      }
    }
  }
}
```

## Testing

After making the change:

1. **Restart Claude Desktop**

2. **In Claude, ask:**
   ```
   What tools do you have available?
   ```

3. **Expected response:**
   - Claude should list: parse_item, get_item_price, get_sales_summary, search_database

4. **Test with a real query:**
   ```
   Get the price of Headhunter in Standard league for POE1
   ```

## Troubleshooting

### If Tools Don't Show Up

**Check Claude logs:**
- Windows: `%APPDATA%\Claude\logs\`
- Look for MCP-related errors

**Verify Python path:**
```powershell
# In PowerShell, verify your Python path:
(Get-Command python).Path
```

Use that path in your config.

### If You See Import Errors

Make sure MCP is installed in your environment:
```powershell
.venv\Scripts\activate
pip install "mcp[cli]"
```

### If Nothing Works

Try the simplest config:
```json
{
  "mcpServers": {
    "PoE Price Checker": {
      "command": "python",
      "args": [
        "-m",
        "mcp_poe_server"
      ],
      "cwd": "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck"
    }
  }
}
```

## Alternative: Use Continue Instead

If Claude Desktop continues to have issues, you can use Continue (which you already have in PyCharm):

1. **Create/edit:** `~/.continue/config.json` or `C:\Users\toddb\.continue\config.json`

2. **Add:**
```json
{
  "mcpServers": {
    "poe-price-checker": {
      "command": "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\toddb\\PycharmProjects\\exilePriceCheck\\mcp_poe_server.py"
      ]
    }
  }
}
```

3. **Restart PyCharm**

4. **In Continue chat, ask:**
   ```
   What MCP tools do you have available?
   ```

## Quick Test Script

To verify your MCP server works standalone:

```powershell
# Activate your environment
.venv\Scripts\activate

# Run the server directly
python mcp_poe_server.py
```

It should start without errors. Press Ctrl+C to stop.

## Current Status

✅ MCP server code is working  
✅ Config file exists  
🔧 Need to fix the `uv` vs `python` issue  
⏳ Waiting for you to update config and restart Claude

---

**After fixing, come back and tell me if you see the tools in Claude!**
