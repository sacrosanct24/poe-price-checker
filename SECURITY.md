# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| < 1.3   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in PoE Price Checker, please report it responsibly.

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email the maintainers directly or use GitHub's private vulnerability reporting feature
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Resolution**: We aim to release a fix within 30 days for critical issues
- **Disclosure**: We will coordinate with you on public disclosure timing

## Security Considerations

### Sensitive Data Handling

This application handles sensitive user data:

- **POESESSID cookies**: Used for stash tab access. These are stored locally only and never transmitted to third-party servers. The session ID grants full account access - treat it like a password.

- **OAuth tokens**: Encrypted at rest using platform-appropriate secure storage. Tokens are only used for official GGG API access.

- **Build data**: Character builds and item data are stored locally in SQLite databases.

### Network Security

- All API communications use HTTPS
- CSRF protection is implemented for OAuth flows
- Rate limiting respects GGG's API guidelines

### Local Security

- No telemetry or analytics are collected
- All data remains on your local machine
- Cache files are stored in user-specific directories

## Security Best Practices for Users

1. **Never share your POESESSID** with anyone or paste it into untrusted applications
2. **Regenerate your POESESSID** periodically by logging out and back into pathofexile.com
3. **Keep the application updated** to receive security patches
4. **Review OAuth permissions** granted to the application in your PoE account settings

## Dependencies

We regularly update dependencies to address known vulnerabilities. Run `pip list --outdated` to check for updates.

## Code Security

- Type hints are used throughout for safer code
- Input validation is performed on all external data
- SQL queries use parameterized statements to prevent injection
