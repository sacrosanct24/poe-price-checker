# OAuth Implementation Corrections

**Date:** 2024-11-23  
**Status:** ✅ Fixed

---

## What Was Wrong

Initial OAuth implementation had critical issues that would have prevented it from working with Path of Exile's OAuth API.

---

## Issues Fixed

### 1. ❌ Used localhost Instead of 127.0.0.1

**Problem:**
```python
REDIRECT_URI = "http://localhost:8080/oauth/callback"  # NOT ALLOWED
```

**Why it's wrong:**
- PoE API documentation: "We cannot accept IP addresses or localhost domains even for in-development projects" (for confidential clients)
- Public clients ARE allowed to use 127.0.0.1

**Fix:**
```python
REDIRECT_URI = "http://127.0.0.1:8080/oauth/callback"  # ✅ CORRECT
```

---

### 2. ❌ Missing PKCE Implementation

**Problem:**
- Code didn't implement PKCE (Proof Key for Code Exchange)
- PKCE is **REQUIRED** for public clients per OAuth 2.1

**What's PKCE?**
- Security measure for public clients (desktop apps)
- Prevents authorization code interception attacks
- Uses `code_verifier` and `code_challenge` parameters

**Fix:**
Added complete PKCE implementation:

```python
def _generate_pkce(self) -> None:
    # Generate code_verifier (32 random bytes)
    verifier_bytes = secrets.token_bytes(32)
    self.code_verifier = base64.urlsafe_b64encode(verifier_bytes).decode('utf-8').rstrip('=')
    
    # Generate code_challenge (SHA256 hash)
    challenge_bytes = hashlib.sha256(self.code_verifier.encode('utf-8')).digest()
    self.code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
```

Added to authorization URL:
```python
params = {
    'code_challenge': self.code_challenge,
    'code_challenge_method': 'S256',  # SHA256 hashing
}
```

Added to token exchange:
```python
data = {
    'code_verifier': self.code_verifier,  # Proves we generated the challenge
}
```

---

### 3. ❌ Missing State Parameter

**Problem:**
- Used hardcoded `'random_state_string'`
- State prevents CSRF attacks

**Fix:**
```python
state = secrets.token_urlsafe(32)  # Cryptographically random
```

---

### 4. ❌ Incorrect Client Type Assumption

**Problem:**
- Assumed confidential client (with client_secret)
- Required HTTPS redirect URI with registered domain

**Fix:**
- Changed to PUBLIC CLIENT (correct for desktop apps)
- No client_secret needed or sent
- Can use `http://127.0.0.1` redirect

```python
def __init__(
    self,
    client_id: str,
    client_secret: Optional[str] = None,  # Now optional
    is_public_client: bool = True,  # Default to public
):
    self.is_public_client = is_public_client
    
    # Only send client_secret for confidential clients
    if not self.is_public_client and self.client_secret:
        data['client_secret'] = self.client_secret
```

---

### 5. ❌ Missing Scope in Token Exchange

**Problem:**
```python
data = {
    'grant_type': 'authorization_code',
    'code': code,
    # Missing scope!
}
```

**Fix:**
```python
data = {
    'grant_type': 'authorization_code',
    'code': code,
    'scope': 'account:characters account:stashes',  # ✅ Required
}
```

---

## Token Expiration Differences

### Public Client (What We Use Now)
- **Access Token:** 10 hours
- **Refresh Token:** 7 days
- **Rate Limits:** Shared with all public clients
- **Redirect:** `http://127.0.0.1` allowed
- **Security:** PKCE required

### Confidential Client (What We Had)
- **Access Token:** 28 days
- **Refresh Token:** 90 days
- **Rate Limits:** Individual per client
- **Redirect:** HTTPS with registered domain required
- **Security:** Client secret required

**Why Public is Better for Us:**
- ✅ Correct for desktop applications
- ✅ No domain registration needed
- ✅ No HTTPS certificate needed
- ✅ More secure (PKCE prevents token theft)
- ⏰ Tokens expire faster (actually more secure)

---

## Updated Workflow

### 1. Authorization Request
```
https://www.pathofexile.com/oauth/authorize
  ?client_id=YOUR_CLIENT_ID
  &response_type=code
  &scope=account:characters account:stashes
  &state=RANDOM_32_BYTE_STRING
  &redirect_uri=http://127.0.0.1:8080/oauth/callback
  &code_challenge=SHA256_HASH_OF_VERIFIER
  &code_challenge_method=S256
```

### 2. Token Exchange
```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&grant_type=authorization_code
&code=AUTHORIZATION_CODE
&redirect_uri=http://127.0.0.1:8080/oauth/callback
&scope=account:characters account:stashes
&code_verifier=ORIGINAL_VERIFIER
```

**Note:** NO `client_secret` parameter!

### 3. Refresh Token
```
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&grant_type=refresh_token
&refresh_token=REFRESH_TOKEN
```

---

## User Impact

### What Users Need to Do Differently

**Before (Wrong):**
1. Register app with redirect: `http://localhost:8080/oauth/callback`
2. Get Client ID and Client Secret
3. Put both in `oauth_config.json`

**After (Correct):**
1. Register app as **PUBLIC CLIENT**
2. Use redirect: `http://127.0.0.1:8080/oauth/callback`
3. Get ONLY Client ID (no secret!)
4. Put only Client ID in `oauth_config.json`:
   ```json
   {
     "client_id": "YOUR_CLIENT_ID_HERE"
   }
   ```

---

## Code Changes Summary

### Files Modified:
1. **`core/poe_oauth.py`**
   - Added PKCE generation (`_generate_pkce()`)
   - Changed redirect to `127.0.0.1`
   - Made `client_secret` optional
   - Added `is_public_client` parameter
   - Added proper state generation
   - Updated token exchange to include `code_verifier`
   - Conditional inclusion of `client_secret`

2. **`STASH_SCANNER_CHECKLIST.md`**
   - Updated registration instructions
   - Changed config to exclude `client_secret`
   - Fixed test commands

3. **`docs/development/STASH_SCANNER_SETUP.md`**
   - Added public vs confidential client explanation
   - Updated all code examples
   - Fixed redirect URI in examples

---

## Security Improvements

✅ **PKCE Protection:** Prevents authorization code interception  
✅ **Random State:** Prevents CSRF attacks  
✅ **No Client Secret:** Can't be extracted from desktop app  
✅ **Shorter Token Lifetime:** Reduces exposure window  
✅ **Correct Client Type:** Follows OAuth 2.1 best practices  

---

## Testing Checklist

After these changes, verify:

- [ ] Browser opens to PoE authorization page
- [ ] Authorization page doesn't show "unverifiable" warning
- [ ] Redirect to `127.0.0.1:8080` works
- [ ] Token is successfully exchanged
- [ ] Token is saved and can be refreshed
- [ ] Stash tabs can be fetched with token

---

## References

- **PoE OAuth Documentation:** https://www.pathofexile.com/developer/docs/authorization
- **OAuth 2.1 Draft RFC:** https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07
- **PKCE RFC 7636:** https://datatracker.ietf.org/doc/html/rfc7636

---

**Status:** ✅ Implementation now complies with PoE OAuth requirements

All code has been corrected and is ready for testing!
