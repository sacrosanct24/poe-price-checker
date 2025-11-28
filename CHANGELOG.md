# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

---

## [1.1.0] - 2025-11-28

### Security

This release addresses multiple security improvements identified during a comprehensive security audit.

#### Token Storage (HIGH)
- OAuth tokens are now encrypted at rest using Fernet encryption with PBKDF2 key derivation
- Token files have restricted permissions (owner-only access on Windows via `icacls`, 0600 on Unix)

#### OAuth Flow (MEDIUM)
- Added state parameter validation to prevent CSRF attacks during OAuth authentication
- State mismatch now properly logs and rejects the authentication attempt

#### API Security (HIGH)
- Fixed regex pattern in Cargo API client to properly sanitize input values
- Added exponential backoff for rate-limited requests (429 responses) in PoE Stash API

#### Input Validation (MEDIUM)
- PoB integration now uses `urlparse` for safer URL handling instead of string manipulation
- Item Inspector uses `html.escape()` to prevent XSS in displayed item names

### Changed
- Upgraded test suite from 671 to 1200+ tests with improved security coverage
- OAuth tests updated to verify encrypted token storage

### Technical Details
- `core/secure_storage.py`: Added `_restrict_file_permissions()` method for cross-platform file security
- `core/poe_oauth.py`: Integrated SecureStorage for token encryption/decryption
- `data_sources/cargo_api_client.py`: Improved regex character class for input sanitization
- `data_sources/poe_stash_api.py`: Added retry logic with exponential backoff (2s, 4s, 8s)
- `core/pob_integration.py`: Safe URL parsing with `urlparse`
- `gui_qt/widgets/item_inspector.py`: HTML escaping for user-visible content

---

## [1.0.0] - 2025-11-27

### Added

#### Core Features
- **Item Price Checking**: Paste items from Path of Exile to get instant price estimates
- **Clipboard Monitoring**: Automatic detection of copied items with Ctrl+C
- **Multiple Price Sources**: Integration with poe.ninja and poeprices.info APIs
- **PoE 2 Support**: Full compatibility with Path of Exile 2 items and mechanics

#### Build Integration
- **Path of Building Import**: Import character builds via PoB share codes or Pastebin URLs
- **Build Archetype Detection**: Automatic identification of build types (life, ES, hybrid, attack, spell, etc.)
- **Build-Effective Values**: See how item stats translate to actual build power
- **Upgrade Comparison**: Compare items against your current equipped gear

#### Rare Item Evaluation
- **Smart Scoring System**: Multi-factor evaluation considering build relevance
- **Tier Analysis**: Display of mod tiers with RePoE data integration
- **Archetype Matching**: Scores items based on compatibility with build archetypes
- **Configurable Weights**: Customize evaluation priorities for different build types

#### BiS Item Search
- **Trade Search Integration**: Generate optimized trade searches based on build needs
- **Guide Gear Extraction**: See what items your reference build recommends
- **Ideal Rare Calculator**: View ideal mod tiers for any equipment slot
- **Priority System**: Set critical, important, and nice-to-have stat priorities

#### Stash Viewer
- **Account Stash Access**: View all stash tabs with POESESSID authentication
- **Automatic Valuation**: Price all items in your stash tabs
- **Search and Filter**: Find items by name with minimum value filtering
- **Tab-by-Tab Browsing**: Navigate stash tabs with value summaries

#### Price Rankings
- **Market Overview**: See most valuable items by category
- **Currency Rates**: Live exchange rates for all PoE currencies
- **Historical Context**: Compare current prices to market trends

#### Sales Tracking
- **Record Sales**: Track items you've sold with prices and notes
- **Sales Dashboard**: View total earnings and daily statistics
- **Recent Sales History**: Browse past sales with filtering

#### User Interface
- **Dark Theme**: PoE-inspired dark color scheme with gold/blue accents
- **Responsive Layout**: Resizable windows with splitter panels
- **Item Inspector**: Detailed view with mod highlighting and copy support
- **Status Bar**: League info, Divine:Chaos ratio, and connection status

### Technical Features
- **PyQt6 GUI**: Modern, native-feeling desktop application
- **SQLite Database**: Local storage for sales, settings, and cache
- **Comprehensive Testing**: 200+ unit tests with pytest
- **Type Annotations**: Full type hints for better code quality
- **Modular Architecture**: Clean separation of core logic, data sources, and UI

### Documentation
- README with installation and usage instructions
- Development guides in `docs/` folder
- API integration documentation
- Code of Conduct and Contributing guidelines

---

## Version History Note

This is the initial public release (v1.0.0). The project was developed privately before this release. Future versions will include detailed changelogs tracking all modifications.

---

[Unreleased]: https://github.com/sacrosanct24/exilePriceCheck/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/sacrosanct24/exilePriceCheck/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/sacrosanct24/exilePriceCheck/releases/tag/v1.0.0
