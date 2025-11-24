

# Stash Scanner Setup Guide

Complete guide to setting up OAuth and scanning your Path of Exile stash tabs.

---

## 🎯 Overview

The Stash Scanner feature allows you to:
- Scan all your stash tabs automatically
- Find valuable items (10c+) - currently uniques and currency
- Get tab name and exact position (x, y) for each valuable item
- See total value per tab

---

## Step 1: Register OAuth Application

### 1.1 Go to PoE Developer Portal

Visit: https://www.pathofexile.com/developer/docs

### 1.2 Create an Application

1. Click **"Create an Application"** or **"Register Application"**
2. Fill out the form:

```
Application Name: PoE Price Checker
Description: Desktop price checking tool for Path of Exile items
Client Type: PUBLIC CLIENT (for desktop applications)
Redirect URI: http://127.0.0.1:8080/oauth/callback
Scopes: 
  - account:characters (to get character info)
  - account:stashes (to read stash tabs)
```

**⚠️ IMPORTANT:**
- Select **PUBLIC CLIENT** type (not Confidential)
- Use `127.0.0.1` NOT `localhost` in redirect URI
- Public clients don't get a Client Secret (this is correct!)

3. Click **Submit**

### 1.3 Save Your Credentials

You'll receive:
- **Client ID**: Something like `poe-price-checker-12345`

**ℹ️ Note:** Public clients don't get a Client Secret (and don't need one!)

---

## Step 2: Configure Your Application

### 2.1 Create Config File

Create `oauth_config.json` in your project root:

```json
{
  "client_id": "YOUR_CLIENT_ID_HERE"
}
```

**Note:** No `client_secret` field for public clients!

### 2.2 Add to .gitignore

Make sure this is in `.gitignore` (already done ✓):

```
oauth_config.json
.poe_price_checker/oauth_token.json
```

### 2.3 Understanding Public vs Confidential Clients

**Why Public Client?**
- ✅ Desktop apps can't securely store secrets
- ✅ Allows `127.0.0.1` redirect URI
- ✅ Uses PKCE for security (we handle this automatically)
- ⏰ Tokens expire in 10 hours (vs 28 days for confidential)
- 🔄 Refresh tokens last 7 days (vs 90 days)

This is the **correct and secure** approach for desktop applications!

---

## Step 3: Test OAuth Flow

### 3.1 Test Authentication

```bash
cd C:\Users\toddb\PycharmProjects\exilePriceCheck
.venv\Scripts\activate
python core/poe_oauth.py
```

**What happens:**
1. Browser opens to PoE login page
2. You log in with your PoE account
3. PoE asks you to authorize the app
4. Click **"Authorize"**
5. Browser redirects to localhost (shows success message)
6. Terminal shows "✓ Authentication successful!"

**Token is saved to:** `~/.poe_price_checker/oauth_token.json`

### 3.2 Verify Token Works

Run again:
```bash
python core/poe_oauth.py
```

Should show: `✓ Already authenticated!` (no browser popup)

---

## Step 4: Test Stash Scanner

### 4.1 Scan Your Stash

```bash
python core/stash_scanner.py
```

**Expected output:**
```
INFO: Account name: YourAccountName
INFO: Fetching stash tabs for league 'Standard'
INFO: Found 24 stash tabs
INFO: Scanning tab 0: 'Currency' (CurrencyStash)
INFO: Found 50 items in tab 0
INFO: Tab 'Currency': 50 items parsed
...
INFO: Stash scan complete: 24 tabs, 485 total items

Found 24 stash tabs:
  - Currency: 50 items
  - Maps: 144 items  
  - Uniques: 87 items
  - Chaos Recipe: 42 items
  ...
```

---

## Step 5: Add to GUI

### 5.1 Load OAuth Config

Update `poe_price_checker.py` to load OAuth config:

```python
# Add to imports
from core.poe_oauth import PoeOAuthClient
from core.stash_scanner import StashScanner
import json

# Load OAuth config
oauth_config_path = Path("oauth_config.json")
if oauth_config_path.exists():
    with open(oauth_config_path) as f:
        oauth_config = json.load(f)
    
    oauth_client = PoeOAuthClient(
        client_id=oauth_config['client_id'],
        client_secret=oauth_config['client_secret'],
    )
else:
    oauth_client = None

# Pass to AppContext if needed
app_context.oauth_client = oauth_client
```

### 5.2 Add "Scan Stash" Button

In `gui/main_window.py`, add to menu or toolbar:

```python
def _create_menu(self):
    # ... existing menus ...
    
    # Tools menu
    tools_menu = tk.Menu(self.menubar, tearoff=False)
    tools_menu.add_command(
        label="Scan Stash for Valuable Items...",
        command=self._scan_stash
    )
    self.menubar.add_cascade(label="Tools", menu=tools_menu)

def _scan_stash(self):
    """Open stash scanner dialog."""
    if not hasattr(self.app_context, 'oauth_client'):
        messagebox.showinfo(
            "OAuth Not Configured",
            "OAuth is not configured. See docs/development/STASH_SCANNER_SETUP.md"
        )
        return
    
    oauth = self.app_context.oauth_client
    
    # Check if authenticated
    if not oauth.is_authenticated():
        # Need to authenticate
        result = messagebox.askyesno(
            "Authentication Required",
            "You need to authenticate with Path of Exile to scan your stash.\n\n"
            "This will open your browser. Continue?"
        )
        
        if not result:
            return
        
        # Run authentication
        if not oauth.authenticate():
            messagebox.showerror("Authentication Failed", "Failed to authenticate with PoE.")
            return
    
    # Open scanner window
    self._open_stash_scanner_window()
```

---

## Step 6: Create Scanner Window

### 6.1 Create StashScannerWindow Class

Create `gui/stash_scanner_window.py`:

```python
"""
Stash scanner window for finding valuable items.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple
import threading

from core.stash_scanner import StashScanner, StashTab, StashItem


class StashScannerWindow(tk.Toplevel):
    """Window for scanning stash tabs."""
    
    def __init__(self, master, oauth_client, price_service, league="Standard"):
        super().__init__(master)
        
        self.oauth_client = oauth_client
        self.price_service = price_service
        self.league = league
        
        self.title("Stash Scanner - Find Valuable Items")
        self.geometry("900x600")
        
        self._create_ui()
        
    def _create_ui(self):
        """Create UI elements."""
        # Control frame
        control_frame = ttk.Frame(self, padding=8)
        control_frame.pack(side="top", fill="x")
        
        ttk.Label(control_frame, text="League:").pack(side="left", padx=(0, 4))
        
        self.league_var = tk.StringVar(value=self.league)
        league_combo = ttk.Combobox(
            control_frame,
            textvariable=self.league_var,
            values=["Standard", "Hardcore", "Crucible", "HC Crucible"],
            width=15,
        )
        league_combo.pack(side="left", padx=(0, 8))
        
        ttk.Label(control_frame, text="Min Value (c):").pack(side="left", padx=(8, 4))
        
        self.min_value_var = tk.StringVar(value="10")
        min_value_entry = ttk.Entry(control_frame, textvariable=self.min_value_var, width=8)
        min_value_entry.pack(side="left", padx=(0, 8))
        
        self.scan_button = ttk.Button(
            control_frame,
            text="Scan Stash",
            command=self._start_scan,
        )
        self.scan_button.pack(side="left", padx=(8, 0))
        
        self.progress_label = ttk.Label(control_frame, text="")
        self.progress_label.pack(side="left", padx=(16, 0))
        
        # Results frame
        results_frame = ttk.Frame(self, padding=8)
        results_frame.pack(side="top", fill="both", expand=True)
        
        # Results tree
        columns = ("tab", "item", "position", "chaos", "divine", "confidence")
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        
        self.results_tree.heading("tab", text="Tab")
        self.results_tree.heading("item", text="Item")
        self.results_tree.heading("position", text="Position")
        self.results_tree.heading("chaos", text="Chaos")
        self.results_tree.heading("divine", text="Divine")
        self.results_tree.heading("confidence", text="Source")
        
        self.results_tree.column("tab", width=150)
        self.results_tree.column("item", width=250)
        self.results_tree.column("position", width=80)
        self.results_tree.column("chaos", width=80)
        self.results_tree.column("divine", width=80)
        self.results_tree.column("confidence", width=100)
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Summary frame
        summary_frame = ttk.Frame(self, padding=8)
        summary_frame.pack(side="bottom", fill="x")
        
        self.summary_label = ttk.Label(summary_frame, text="Ready to scan")
        self.summary_label.pack(side="left")
    
    def _start_scan(self):
        """Start scanning in background thread."""
        self.scan_button.config(state="disabled")
        self.progress_label.config(text="Scanning...")
        self.results_tree.delete(*self.results_tree.get_children())
        
        # Get parameters
        league = self.league_var.get()
        try:
            min_value = float(self.min_value_var.get())
        except ValueError:
            min_value = 10.0
        
        # Run scan in thread
        thread = threading.Thread(
            target=self._run_scan,
            args=(league, min_value),
            daemon=True,
        )
        thread.start()
    
    def _run_scan(self, league: str, min_value: float):
        """Run scan in background thread."""
        try:
            scanner = StashScanner(self.oauth_client, league=league)
            valuable_items = scanner.scan_and_price(self.price_service, min_value)
            
            # Update UI on main thread
            self.after(0, self._display_results, valuable_items)
            
        except Exception as e:
            self.after(0, self._scan_error, str(e))
    
    def _display_results(self, valuable_items: List[Tuple[StashTab, StashItem]]):
        """Display scan results."""
        self.scan_button.config(state="normal")
        self.progress_label.config(text="")
        
        # Clear existing
        self.results_tree.delete(*self.results_tree.get_children())
        
        # Sort by chaos value descending
        valuable_items.sort(key=lambda x: x[1].chaos_value, reverse=True)
        
        total_chaos = 0.0
        total_divine = 0.0
        
        for tab, item in valuable_items:
            self.results_tree.insert(
                "",
                "end",
                values=(
                    tab.name,
                    item.name or item.type_line,
                    f"({item.position_x}, {item.position_y})",
                    f"{item.chaos_value:.1f}c",
                    f"{item.divine_value:.2f}d",
                    item.confidence,
                )
            )
            
            total_chaos += item.chaos_value
            total_divine += item.divine_value
        
        self.summary_label.config(
            text=f"Found {len(valuable_items)} valuable items | "
                 f"Total: {total_chaos:.1f}c ({total_divine:.2f}d)"
        )
    
    def _scan_error(self, error_msg: str):
        """Handle scan error."""
        self.scan_button.config(state="normal")
        self.progress_label.config(text="")
        
        messagebox.showerror("Scan Error", f"Failed to scan stash:\n\n{error_msg}")
```

---

## Troubleshooting

### "Not Authenticated" Error
**Solution:** Run `python core/poe_oauth.py` to authenticate

### "Failed to fetch stash tabs" Error  
**Solution:** 
- Check your league name is correct
- Verify OAuth scopes include `account:stashes`
- Try refreshing token

### Browser Doesn't Redirect Back
**Solution:**
- Check firewall isn't blocking port 8080
- Make sure redirect URI in PoE app settings is exactly: `http://localhost:8080/oauth/callback`

### "Rate Limit" Error
**Solution:** 
- PoE API has rate limits
- Wait a minute and try again
- Consider caching stash data

---

## Next Steps

1. **Test OAuth:** Register app and authenticate
2. **Test Scanner:** Run `python core/stash_scanner.py`
3. **Add to GUI:** Integrate stash scanner window
4. **Test End-to-End:** Scan stash from GUI

---

## API Limitations (Current Version)

**What Works:**
- ✅ Unique items (names match poe.ninja exactly)
- ✅ Currency items (Chaos Orb, Divine Orb, etc.)
- ✅ Simple items without complex mods

**What Doesn't Work Yet:**
- ❌ Rare items with specific mods (requires mod evaluation)
- ❌ Magic items with mods
- ❌ Items that need affix analysis
- ❌ Influenced items value calculation

**Future Enhancement:** Add mod parsing and value calculation for complex items.

---

**Status:** Ready to implement OAuth and basic stash scanning for uniques/currency!
