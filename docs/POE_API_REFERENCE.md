---
title: Path of Exile Official API Reference
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
---

# Path of Exile Official API Reference

**Last Updated:** January 2025
**Official Source:** https://www.pathofexile.com/developer/docs/reference

> This is a reference copy for offline use. Always check official docs for updates.

---

## Server Endpoint
```
https://api.pathofexile.com
```

## Public Stashes API (Key for Pricing)

**Endpoint:** `GET /public-stash-tabs[/<realm>]`  
**Required Scope:** `service:psapi`  
**Realms:** pc (default), xbox, sony

**Query:** `?id=<next_change_id>` for pagination

**Returns:**
- `next_change_id` - Use for next request
- `stashes[]` - Array of public stash tabs with items
  - Each item has `note` field with pricing (e.g., "~price 10 divine")
  - Empty array = end of stream, poll with same ID

**Important:** 5-minute delay on all results

## Currency Exchange API

**Endpoint:** `GET /currency-exchange[/<realm>][/<id>]`  
**Required Scope:** `service:cxapi`

Returns hourly aggregate trade history for currency pairs.

## Character & Stash APIs

- `GET /character[/<realm>]` - List characters (scope: `account:characters`)
- `GET /stash[/<realm>]/<league>` - List stashes (scope: `account:stashes`)
- `GET /stash[/<realm>]/<league>/<stash_id>` - Get stash contents

## Leagues

- `GET /league` - List leagues (scope: `service:leagues`)
- `GET /league/<league>/ladder` - Ladder (scope: `service:leagues:ladder`)

## Rate Limiting

**Required User-Agent:** `OAuth {clientId}/{version} (contact: {email})`

Check headers: `x-rate-limit-*`  
**429 = Rate limited** - Back off!

## Item Object Structure

```json
{
  "id": "64-digit-hex",
  "name": "Item Name",
  "typeLine": "Base Type",
  "ilvl": 85,
  "league": "Affliction",
  "frameType": 3,
  "note": "~price 10 divine",
  "explicitMods": [],
  "implicitMods": [],
  "sockets": [],
  "properties": []
}
```

**frameType:** 0=Normal, 1=Magic, 2=Rare, 3=Unique, 4=Gem, 5=Currency

---

## Authorization (OAuth 2.1)

### Overview

Almost all PoE APIs require OAuth 2.1 authorization. This helps enforce rate limits and provides accountability.

**OAuth Server Endpoints:**
- `/oauth/authorize` - Authorization page for user consent
- `/oauth/token` - Create tokens
- `/oauth/token/revoke` - Revoke tokens (requires `oauth:revoke` scope)
- `/oauth/token/introspect` - Check tokens (requires `oauth:introspect` scope)

**Users can review/revoke tokens:** https://www.pathofexile.com/my-account/applications

---

## Client Types

### Confidential Clients (Recommended)

Backend by a secure server you control.

**Characteristics:**
- Can use any grant type
- Redirect URIs must be HTTPS with registered domain (no IPs or localhost)
- Access tokens: **28 days**
- Refresh tokens: **90 days**
- Individual rate limits per client

### Public Clients

Applications without secure credential storage (e.g., desktop apps).

**Characteristics:**
- Must use Authorization Code + PKCE only
- Must use local redirect URI (e.g., `http://127.0.0.1:8080/callback`)
- **Cannot use `service:*` scopes**
- Access tokens: **10 hours**
- Refresh tokens: **7 days**
- Shared rate limits
- Shows warning to users about unverifiable authenticity

---

## Available Scopes

### Account Scopes
- `account:profile` - Basic profile information
- `account:leagues` - Available leagues (including private)
- `account:stashes` - Stash tabs and items
- `account:characters` - Characters and inventories
- `account:league_accounts` - Allocated atlas passives
- `account:item_filter` - Item filter management

### Service Scopes (Confidential + client_credentials only)
- `service:leagues` - Fetch leagues
- `service:leagues:ladder` - League ladders
- `service:pvp_matches` - PvP matches
- `service:pvp_matches:ladder` - PvP ladders
- `service:psapi` - **Public Stash API**
- `service:cxapi` - **Currency Exchange API**

### OAuth Scopes
- `oauth:revoke` - Revoke tokens
- `oauth:introspect` - Inspect tokens

---

## Grant Types

### 1. Authorization Code (with PKCE)

**Use when:** Your app needs to act on behalf of a user.

**Flow:**

**Step 1:** Generate PKCE values
```php
$secret = random_bytes(32);
$code_verifier = base64url_encode($secret);
$code_challenge = base64url_encode(hash('sha256', $code_verifier, true));
```

**Step 2:** Redirect user to authorization
```
https://www.pathofexile.com/oauth/authorize
  ?client_id=YOUR_CLIENT_ID
  &response_type=code
  &scope=account:profile account:stashes
  &state=RANDOM_STATE_STRING
  &redirect_uri=https://example.com/callback
  &code_challenge=YOUR_CODE_CHALLENGE
  &code_challenge_method=S256
```

**Step 3:** User approves, redirected to your URI
```
https://example.com/callback?code=AUTH_CODE&state=YOUR_STATE
```

**Step 4:** Exchange code for tokens (within 30 seconds!)
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&client_secret=YOUR_SECRET
&grant_type=authorization_code
&code=AUTH_CODE
&redirect_uri=https://example.com/callback
&scope=account:profile account:stashes
&code_verifier=YOUR_CODE_VERIFIER
```

**Response:**
```json
{
  "access_token": "486132c90fedb152360bc0e1aa54eea155768eb9",
  "expires_in": 2592000,
  "token_type": "bearer",
  "scope": "account:profile",
  "username": "PlayerName",
  "sub": "c5b9c286-8d05-47af-be41-67ab10a8c53e",
  "refresh_token": "17abaa74e599192f7650a4b89b6e9dfef2ff68cd"
}
```

---

### 2. Client Credentials Grant

**Use when:** Accessing services unrelated to individual accounts (e.g., Public Stash API).

**Flow:**

```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&client_secret=YOUR_SECRET
&grant_type=client_credentials
&scope=service:psapi service:cxapi
```

**Response:**
```json
{
  "access_token": "cded8a4638ae9bc5fe6cd897890e25e41f0f4e21",
  "expires_in": null,
  "token_type": "bearer",
  "username": "YourAccount",
  "sub": "c5b9c286-8d05-47af-be41-67ab10a8c53e",
  "scope": "service:psapi"
}
```

**⚠️ Important:** 
- Tokens don't expire (revoke manually)
- Identity = registered owner's account
- Tokens can access YOUR account data with appropriate scopes
- **Keep credentials secret!**

---

### 3. Refresh Token Grant

**Use when:** Renewing expired access token without user interaction.

**Flow:**

```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&client_secret=YOUR_SECRET
&grant_type=refresh_token
&refresh_token=YOUR_REFRESH_TOKEN
```

**Response:**
```json
{
  "access_token": "41bcefbc2f0d6ea0fa1cce10c435310d3c475e5b",
  "expires_in": 2592000,
  "token_type": "bearer",
  "scope": "account:profile",
  "username": "PlayerName",
  "sub": "c5b9c286-8d05-47af-be41-67ab10a8c53e",
  "refresh_token": "4e9dbe97e038430bd943d35f8d5f8bef99699396"
}
```

**⚠️ Important:**
- New refresh token inherits expiry of used token
- Cannot extend refresh token expiration
- Old refresh token is immediately expired

---

## Using Access Tokens

**Include in Authorization header:**
```http
GET /profile
Authorization: Bearer 486132c90fedb152360bc0e1aa54eea155768eb9
User-Agent: OAuth myapp/1.0.0 (contact: myapp@example.com)
```

**Error Responses:**
- **401 Unauthorized** - Token expired or revoked → Generate new token
- **403 Forbidden** - Token lacks required scope → Request correct scopes

---

## Token Management Best Practices

### Access Tokens
- ✅ Can be stored client-side (cookies, localStorage)
- ✅ Send over HTTPS only
- ✅ Never share with anyone but the owner
- ⏰ Expire after 28 days (confidential) or 10 hours (public)

### Refresh Tokens
- ⚠️ **Must be stored server-side securely**
- ❌ Never send to client/browser
- ❌ Never log or expose
- ⏰ Expire after 90 days (confidential) or 7 days (public)
- 💡 Can be disabled if your flow doesn't support secure storage

### Client Credentials
- ⚠️ **Keep secret at all costs**
- ❌ Never embed in client code
- ❌ Never commit to version control
- ❌ Never distribute in binaries

---

## Registration

**Email:** oauth@grindinggear.com

**Include:**
1. PoE account name
2. Application name
3. Client type (confidential/public)
4. Grant types needed
5. **Required scopes with justification**
6. Redirect URI(s)

**Notes:**
- Requests are low priority
- Expect delays, especially during league launches
- Be specific about why you need each scope

---

**Full OAuth 2.1 specification:** https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-11  
**Official PoE OAuth docs:** https://www.pathofexile.com/developer/docs/authorization  
**See official docs for complete details on all endpoints and types.**
