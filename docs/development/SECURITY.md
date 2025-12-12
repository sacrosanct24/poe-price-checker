# Security Practices

This document outlines security practices and guidelines for the PoE Price Checker project.

## Security Scanning

### Automated Scans (CI)

| Tool | Purpose | Blocking |
|------|---------|----------|
| **Bandit** | Python security linter | HIGH/CRITICAL block PRs |
| **pip-audit** | Dependency vulnerabilities | Yes |
| **TruffleHog** | Secrets detection | Verified secrets only |
| **CodeQL** | Deep code analysis | Weekly scan |

### Local Security Scanning

Run full security scan locally before pushing:

```bash
python scripts/local_ci.py --security-full
```

This runs:
- Bandit in strict mode (fails on HIGH severity)
- pip-audit dependency scan
- Security test suite

## Secure Coding Guidelines

### Input Validation

1. **Database Queries**: Always use parameterized queries (SQLAlchemy handles this)
   ```python
   # Good
   session.query(Item).filter(Item.name == user_input)

   # Bad - SQL injection risk
   session.execute(f"SELECT * FROM items WHERE name = '{user_input}'")
   ```

2. **HTML Content**: Escape user-provided content before display
   ```python
   import html
   safe_text = html.escape(user_input)
   ```

3. **URLs**: Validate schemes and hosts
   ```python
   from urllib.parse import urlparse
   parsed = urlparse(url)
   if parsed.scheme not in ("http", "https"):
       raise ValueError("Invalid URL scheme")
   ```

### Credential Storage

- **Never hardcode** API keys, passwords, or tokens
- Use `SecureStorage` class for sensitive data (encrypts with Fernet)
- API keys in config are encrypted at rest

```python
from core.secure_storage import SecureStorage

storage = SecureStorage()
storage.store("api_key", sensitive_value)
retrieved = storage.retrieve("api_key")
```

### External Data

- **XML Parsing**: Use `defusedxml` (already configured)
- **JSON**: Use standard library `json` (safe by default)
- **Rate Limiting**: All API clients use rate limiting to prevent abuse

## Handling Security Findings

### Bandit Findings

When Bandit reports an issue:

1. **Evaluate severity**: HIGH/CRITICAL must be fixed before merge
2. **Check if false positive**: Some patterns are safe in context
3. **Fix or suppress**: Fix the issue, or add inline suppression with justification

```python
# Suppressing a false positive (with justification)
password = os.environ.get("DB_PASSWORD")  # nosec B105 - env var, not hardcoded
```

### Dependency Vulnerabilities

When pip-audit finds a vulnerability:

1. **Check if exploitable**: Does the vulnerable code path affect us?
2. **Update dependency**: Prefer updating to patched version
3. **Document if can't update**: If update breaks compatibility, document risk

## Security Test Suite

Located at `tests/security/`:

- `test_input_sanitization.py` - SQL injection, XSS, path traversal tests
- `test_secure_storage.py` - Credential encryption tests

Run with:
```bash
pytest tests/security/ -v
```

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public GitHub issue
2. Email security concerns privately to the maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

## Approved Suppressions

These Bandit rules are suppressed project-wide (in `.bandit`):

| Rule | Reason |
|------|--------|
| B101 | `assert` used by pytest |
| B105 | False positives for URL strings |
| B106 | False positives for config parameter names |
| B608 | All SQL uses parameterized queries |

## Security Checklist for PRs

Before merging code that handles:

- [ ] User input → Validate and sanitize
- [ ] Database queries → Use parameterized queries
- [ ] File paths → Validate against directory traversal
- [ ] External URLs → Validate scheme and host
- [ ] Credentials → Use SecureStorage, never log
- [ ] HTML display → Escape user content
- [ ] Subprocess calls → Never use shell=True with user input
