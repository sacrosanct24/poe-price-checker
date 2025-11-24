# Stash Scanner - Quick Start Checklist

## ✅ Your Action Items

### Step 1: Register OAuth App (5 minutes)
- [ ] Go to https://www.pathofexile.com/developer/docs
- [ ] Click "Register an Application"
- [ ] Fill out form:
  - Name: `PoE Price Checker`
  - **Client Type: PUBLIC CLIENT** (for desktop app)
  - Redirect URI: `http://127.0.0.1:8080/oauth/callback` (note: 127.0.0.1, NOT localhost)
  - Scopes: `account:characters`, `account:stashes`
- [ ] Save your **Client ID** (NO secret for public clients!)

### Step 2: Create Config File (2 minutes)
- [ ] Create `oauth_config.json` in project root:
```json
{
  "client_id": "YOUR_CLIENT_ID_HERE"
}
```
**Note:** No `client_secret` needed for PUBLIC CLIENT!
- [ ] Make sure it's in `.gitignore` (already done ✓)

### Step 3: Test OAuth (3 minutes)
```bash
cd C:\Users\toddb\PycharmProjects\exilePriceCheck
.venv\Scripts\activate
python -c "import json; cfg=json.load(open('oauth_config.json')); from core.poe_oauth import PoeOAuthClient; client=PoeOAuthClient(cfg['client_id'], is_public_client=True); client.authenticate() if not client.is_authenticated() else print('Already authenticated!')"
```

- [ ] Browser opens to PoE login
- [ ] Click "Authorize"
- [ ] See "✓ Authentication Successful!" in browser
- [ ] Terminal shows success

### Step 4: Test Stash Scanner (2 minutes)
```bash
python -c "import json; from core.poe_oauth import PoeOAuthClient; from core.stash_scanner import StashScanner; cfg=json.load(open('oauth_config.json')); oauth=PoeOAuthClient(cfg['client_id'], is_public_client=True); scanner=StashScanner(oauth); tabs=scanner.scan_all_tabs(); print(f'Found {len(tabs)} tabs, {sum(len(t.items) for t in tabs)} total items')"
```

- [ ] See list of your stash tabs
- [ ] See item counts per tab

---

## 🎯 What You Get

After completing these steps, you'll have:

✅ OAuth authentication working  
✅ Ability to fetch all your stash tabs  
✅ Ability to scan every item in your stash  
✅ Foundation for price checking stash items  

---

## 📝 Next Development Steps (After Testing)

Once OAuth works, we'll add:

1. **GUI Integration** - "Scan Stash" button in Tools menu
2. **Price Checking** - Run price check on each item
3. **Results Window** - Show valuable items (>10c) with locations
4. **Export** - Save results to file

---

## 🆘 Common Issues

**Issue:** "Client ID not found"
- Solution: Double-check you copied the **Client ID** correctly

**Issue:** Browser shows "Application not found"
- Solution: 
  - Verify redirect URI is exactly `http://127.0.0.1:8080/oauth/callback` (NOT localhost!)
  - Make sure you selected **PUBLIC CLIENT** type

**Issue:** "Failed to fetch stash tabs"
- Solution: 
  - Make sure you selected the `account:stashes` scope when registering
  - Verify token hasn't expired (10 hours for public clients)
  - Check you're using correct league name

---

## 📞 When You're Ready

Once you've completed the checklist, let me know and I'll help you:
1. Create the GUI window for stash scanning
2. Integrate with your existing price checker
3. Add filtering and export features
4. Test with your actual stash

---

**Start with Step 1! 👆 Register your OAuth app and let me know when you have your credentials.**
