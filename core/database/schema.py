"""
Database Schema Definitions.

Contains SQL statements for schema creation and migrations.
Separated from the main Database class for better maintainability.
"""

# Current schema version. Increment if schema structure changes.
SCHEMA_VERSION = 13

# Full schema creation SQL for fresh databases
CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS checked_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    chaos_value REAL NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- v4 columns for analytics
    rarity TEXT,
    item_mods_json TEXT,
    build_profile TEXT
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    source TEXT,
    listed_price_chaos REAL NOT NULL,
    listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sold_at TIMESTAMP,
    actual_price_chaos REAL,
    time_to_sale_hours REAL,
    relisted BOOLEAN DEFAULT 0,
    notes TEXT,
    -- v4 columns for analytics
    league TEXT,
    rarity TEXT,
    game_version TEXT
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    chaos_value REAL NOT NULL,
    divine_value REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plugin_state (
    plugin_name TEXT PRIMARY KEY,
    enabled BOOLEAN,
    config_json TEXT
);

CREATE TABLE IF NOT EXISTS price_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,                 -- e.g. "poe_trade", "poe_ninja"
    query_hash TEXT              -- optional deterministic hash of query params
);

CREATE TABLE IF NOT EXISTS price_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_check_id INTEGER NOT NULL
        REFERENCES price_checks(id) ON DELETE CASCADE,
    source TEXT NOT NULL,        -- which endpoint / plugin
    price_chaos REAL NOT NULL,   -- normalized to chaos
    original_currency TEXT,      -- e.g. "chaos", "divine"
    stack_size INTEGER,
    listing_id TEXT,             -- API listing id if any
    seller_account TEXT,
    listed_at TIMESTAMP,         -- listing's own timestamp if available
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- v4: Currency rate tracking for historical analytics
CREATE TABLE IF NOT EXISTS currency_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL,
    divine_to_chaos REAL NOT NULL,
    exalt_to_chaos REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_currency_rates_league_time
ON currency_rates (league, recorded_at DESC);

-- v5: Loot tracking tables
CREATE TABLE IF NOT EXISTS loot_sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    state TEXT NOT NULL DEFAULT 'idle',
    auto_detected BOOLEAN DEFAULT 0,
    notes TEXT,
    total_maps INTEGER DEFAULT 0,
    total_drops INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS loot_map_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
    map_name TEXT NOT NULL,
    area_level INTEGER,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    drop_count INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS loot_drops (
    id TEXT PRIMARY KEY,
    map_run_id TEXT NOT NULL REFERENCES loot_map_runs(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    stack_size INTEGER DEFAULT 1,
    chaos_value REAL DEFAULT 0.0,
    divine_value REAL DEFAULT 0.0,
    rarity TEXT,
    item_class TEXT,
    detected_at TIMESTAMP NOT NULL,
    source_tab TEXT,
    item_data_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_loot_sessions_league
ON loot_sessions (league, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_loot_map_runs_session
ON loot_map_runs (session_id, started_at);

CREATE INDEX IF NOT EXISTS idx_loot_drops_session
ON loot_drops (session_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_loot_drops_value
ON loot_drops (chaos_value DESC);

-- v6: Stash snapshot storage for persistence
CREATE TABLE IF NOT EXISTS stash_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    total_items INTEGER DEFAULT 0,
    priced_items INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0,
    snapshot_json TEXT,
    valuation_json TEXT,
    fetched_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stash_snapshots_account_league
ON stash_snapshots (account_name, league, fetched_at DESC);

-- v7: League economy history tables
CREATE TABLE IF NOT EXISTS league_economy_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    rate_date TEXT NOT NULL,
    chaos_value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_rates_lookup
ON league_economy_rates (league, currency_name, rate_date);

CREATE TABLE IF NOT EXISTS league_economy_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    base_type TEXT,
    item_type TEXT,
    rate_date TEXT NOT NULL,
    chaos_value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_items_lookup
ON league_economy_items (league, rate_date, chaos_value DESC);

CREATE TABLE IF NOT EXISTS league_economy_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    milestone TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    divine_to_chaos REAL NOT NULL,
    exalt_to_chaos REAL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_snapshots_league
ON league_economy_snapshots (league, milestone);

CREATE TABLE IF NOT EXISTS league_economy_top_uniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL
        REFERENCES league_economy_snapshots(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    base_type TEXT,
    chaos_value REAL NOT NULL,
    divine_value REAL,
    rank INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_top_uniques_snapshot
ON league_economy_top_uniques (snapshot_id, rank);

-- v8: Pre-aggregated summary tables for historical leagues
CREATE TABLE IF NOT EXISTS league_economy_summary (
    league TEXT PRIMARY KEY,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    total_currency_snapshots INTEGER NOT NULL DEFAULT 0,
    total_item_snapshots INTEGER NOT NULL DEFAULT 0,
    is_finalized INTEGER NOT NULL DEFAULT 0,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS league_currency_summary (
    league TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    avg_value REAL NOT NULL,
    start_value REAL,
    end_value REAL,
    peak_date TEXT,
    data_points INTEGER NOT NULL,
    PRIMARY KEY (league, currency_name)
);

CREATE TABLE IF NOT EXISTS league_top_items_summary (
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    base_type TEXT,
    avg_value REAL NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    data_points INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    PRIMARY KEY (league, item_name)
);

CREATE INDEX IF NOT EXISTS idx_league_top_items_rank
ON league_top_items_summary (league, rank);

-- v9: Upgrade advice cache for AI recommendations
CREATE TABLE IF NOT EXISTS upgrade_advice_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    slot TEXT NOT NULL,
    item_hash TEXT NOT NULL,
    advice_text TEXT NOT NULL,
    ai_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_name, slot)
);

CREATE INDEX IF NOT EXISTS idx_upgrade_advice_profile_slot
ON upgrade_advice_cache (profile_name, slot);

-- v10: Upgrade advice history (keeps last 5 per profile+slot)
CREATE TABLE IF NOT EXISTS upgrade_advice_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    slot TEXT NOT NULL,
    item_hash TEXT NOT NULL,
    advice_text TEXT NOT NULL,
    ai_model TEXT,
    ai_provider TEXT,
    include_stash INTEGER NOT NULL DEFAULT 0,
    stash_candidates_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upgrade_advice_history_lookup
ON upgrade_advice_history (profile_name, slot, created_at DESC);

-- v11: Verdict statistics persistence
CREATE TABLE IF NOT EXISTS verdict_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    session_date TEXT NOT NULL,
    keep_count INTEGER NOT NULL DEFAULT 0,
    vendor_count INTEGER NOT NULL DEFAULT 0,
    maybe_count INTEGER NOT NULL DEFAULT 0,
    keep_value REAL NOT NULL DEFAULT 0.0,
    vendor_value REAL NOT NULL DEFAULT 0.0,
    maybe_value REAL NOT NULL DEFAULT 0.0,
    items_with_meta_bonus INTEGER NOT NULL DEFAULT 0,
    total_meta_bonus REAL NOT NULL DEFAULT 0.0,
    high_confidence_count INTEGER NOT NULL DEFAULT 0,
    medium_confidence_count INTEGER NOT NULL DEFAULT 0,
    low_confidence_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league, game_version, session_date)
);

CREATE INDEX IF NOT EXISTS idx_verdict_statistics_lookup
ON verdict_statistics (league, game_version, session_date);

-- v12: Price alerts for monitoring item prices
CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    alert_type TEXT NOT NULL,  -- 'above' or 'below'
    threshold_chaos REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_price_chaos REAL,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    cooldown_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_alerts_lookup
ON price_alerts (league, game_version, enabled);

CREATE INDEX IF NOT EXISTS idx_price_alerts_item
ON price_alerts (item_name, league);

-- v13: ML training data collection
CREATE TABLE IF NOT EXISTS ml_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT UNIQUE NOT NULL,
    game_id TEXT NOT NULL DEFAULT 'poe1',
    league TEXT NOT NULL,
    item_class TEXT NOT NULL,
    base_type TEXT NOT NULL,
    ilvl INTEGER,
    influences TEXT,  -- JSON
    flags TEXT,  -- JSON: corrupted, mirrored, fractured, synthesised
    affixes TEXT,  -- JSON array: [{affix_id, tier, roll_percentile}, ...]
    price_chaos REAL NOT NULL,
    original_currency TEXT,
    original_amount REAL,
    seller_account TEXT,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    disappeared_at TIMESTAMP,
    listing_state TEXT NOT NULL DEFAULT 'LIVE',
    CHECK (listing_state IN ('LIVE', 'STALE', 'DISAPPEARED_FAST', 'DISAPPEARED_SLOW', 'EXCLUDED'))
);

CREATE INDEX IF NOT EXISTS idx_ml_listings_league ON ml_listings(league);
CREATE INDEX IF NOT EXISTS idx_ml_listings_base_type ON ml_listings(base_type);
CREATE INDEX IF NOT EXISTS idx_ml_listings_state ON ml_listings(listing_state);
CREATE INDEX IF NOT EXISTS idx_ml_listings_first_seen ON ml_listings(first_seen_at);

CREATE TABLE IF NOT EXISTS ml_collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    game_id TEXT NOT NULL DEFAULT 'poe1',
    league TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    listings_fetched INTEGER DEFAULT 0,
    listings_new INTEGER DEFAULT 0,
    listings_updated INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_details TEXT  -- JSON array of error messages
);
"""

# Migration SQL for each version upgrade
MIGRATION_V2_SQL = """
ALTER TABLE sales ADD COLUMN source TEXT;
"""

MIGRATION_V3_SQL = """
CREATE TABLE IF NOT EXISTS price_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_version TEXT NOT NULL,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    query_hash TEXT
);

CREATE TABLE IF NOT EXISTS price_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_check_id INTEGER NOT NULL
        REFERENCES price_checks(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    price_chaos REAL NOT NULL,
    original_currency TEXT,
    stack_size INTEGER,
    listing_id TEXT,
    seller_account TEXT,
    listed_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATION_V4_CURRENCY_RATES_SQL = """
CREATE TABLE IF NOT EXISTS currency_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL,
    divine_to_chaos REAL NOT NULL,
    exalt_to_chaos REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_currency_rates_league_time
ON currency_rates (league, recorded_at DESC);
"""

MIGRATION_V5_SQL = """
CREATE TABLE IF NOT EXISTS loot_sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    state TEXT NOT NULL DEFAULT 'idle',
    auto_detected BOOLEAN DEFAULT 0,
    notes TEXT,
    total_maps INTEGER DEFAULT 0,
    total_drops INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS loot_map_runs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
    map_name TEXT NOT NULL,
    area_level INTEGER,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    drop_count INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS loot_drops (
    id TEXT PRIMARY KEY,
    map_run_id TEXT NOT NULL REFERENCES loot_map_runs(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES loot_sessions(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    stack_size INTEGER DEFAULT 1,
    chaos_value REAL DEFAULT 0.0,
    divine_value REAL DEFAULT 0.0,
    rarity TEXT,
    item_class TEXT,
    detected_at TIMESTAMP NOT NULL,
    source_tab TEXT,
    item_data_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_loot_sessions_league
ON loot_sessions (league, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_loot_map_runs_session
ON loot_map_runs (session_id, started_at);

CREATE INDEX IF NOT EXISTS idx_loot_drops_session
ON loot_drops (session_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_loot_drops_value
ON loot_drops (chaos_value DESC);
"""

MIGRATION_V6_SQL = """
CREATE TABLE IF NOT EXISTS stash_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    total_items INTEGER DEFAULT 0,
    priced_items INTEGER DEFAULT 0,
    total_chaos_value REAL DEFAULT 0.0,
    snapshot_json TEXT,
    valuation_json TEXT,
    fetched_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_stash_snapshots_account_league
ON stash_snapshots (account_name, league, fetched_at DESC);
"""

MIGRATION_V7_SQL = """
CREATE TABLE IF NOT EXISTS league_economy_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    rate_date TEXT NOT NULL,
    chaos_value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_rates_lookup
ON league_economy_rates (league, currency_name, rate_date);

CREATE TABLE IF NOT EXISTS league_economy_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    base_type TEXT,
    item_type TEXT,
    rate_date TEXT NOT NULL,
    chaos_value REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_items_lookup
ON league_economy_items (league, rate_date, chaos_value DESC);

CREATE TABLE IF NOT EXISTS league_economy_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    milestone TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    divine_to_chaos REAL NOT NULL,
    exalt_to_chaos REAL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_snapshots_league
ON league_economy_snapshots (league, milestone);

CREATE TABLE IF NOT EXISTS league_economy_top_uniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL
        REFERENCES league_economy_snapshots(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    base_type TEXT,
    chaos_value REAL NOT NULL,
    divine_value REAL,
    rank INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_league_economy_top_uniques_snapshot
ON league_economy_top_uniques (snapshot_id, rank);
"""

MIGRATION_V8_SQL = """
CREATE TABLE IF NOT EXISTS league_economy_summary (
    league TEXT PRIMARY KEY,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    total_currency_snapshots INTEGER NOT NULL DEFAULT 0,
    total_item_snapshots INTEGER NOT NULL DEFAULT 0,
    is_finalized INTEGER NOT NULL DEFAULT 0,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS league_currency_summary (
    league TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    avg_value REAL NOT NULL,
    start_value REAL,
    end_value REAL,
    peak_date TEXT,
    data_points INTEGER NOT NULL,
    PRIMARY KEY (league, currency_name)
);

CREATE TABLE IF NOT EXISTS league_top_items_summary (
    league TEXT NOT NULL,
    item_name TEXT NOT NULL,
    base_type TEXT,
    avg_value REAL NOT NULL,
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    data_points INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    PRIMARY KEY (league, item_name)
);

CREATE INDEX IF NOT EXISTS idx_league_top_items_rank
ON league_top_items_summary (league, rank);
"""

MIGRATION_V9_SQL = """
CREATE TABLE IF NOT EXISTS upgrade_advice_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    slot TEXT NOT NULL,
    item_hash TEXT NOT NULL,
    advice_text TEXT NOT NULL,
    ai_model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_name, slot)
);

CREATE INDEX IF NOT EXISTS idx_upgrade_advice_profile_slot
ON upgrade_advice_cache (profile_name, slot);
"""

MIGRATION_V10_SQL = """
CREATE TABLE IF NOT EXISTS upgrade_advice_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    slot TEXT NOT NULL,
    item_hash TEXT NOT NULL,
    advice_text TEXT NOT NULL,
    ai_model TEXT,
    ai_provider TEXT,
    include_stash INTEGER NOT NULL DEFAULT 0,
    stash_candidates_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_upgrade_advice_history_lookup
ON upgrade_advice_history (profile_name, slot, created_at DESC);
"""

MIGRATION_V11_SQL = """
CREATE TABLE IF NOT EXISTS verdict_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    session_date TEXT NOT NULL,
    keep_count INTEGER NOT NULL DEFAULT 0,
    vendor_count INTEGER NOT NULL DEFAULT 0,
    maybe_count INTEGER NOT NULL DEFAULT 0,
    keep_value REAL NOT NULL DEFAULT 0.0,
    vendor_value REAL NOT NULL DEFAULT 0.0,
    maybe_value REAL NOT NULL DEFAULT 0.0,
    items_with_meta_bonus INTEGER NOT NULL DEFAULT 0,
    total_meta_bonus REAL NOT NULL DEFAULT 0.0,
    high_confidence_count INTEGER NOT NULL DEFAULT 0,
    medium_confidence_count INTEGER NOT NULL DEFAULT 0,
    low_confidence_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league, game_version, session_date)
);

CREATE INDEX IF NOT EXISTS idx_verdict_statistics_lookup
ON verdict_statistics (league, game_version, session_date);
"""

MIGRATION_V12_SQL = """
CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    item_base_type TEXT,
    league TEXT NOT NULL,
    game_version TEXT NOT NULL DEFAULT 'poe1',
    alert_type TEXT NOT NULL,  -- 'above' or 'below'
    threshold_chaos REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_price_chaos REAL,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    cooldown_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_price_alerts_lookup
ON price_alerts (league, game_version, enabled);

CREATE INDEX IF NOT EXISTS idx_price_alerts_item
ON price_alerts (item_name, league);
"""

MIGRATION_V13_SQL = """
CREATE TABLE IF NOT EXISTS ml_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT UNIQUE NOT NULL,
    game_id TEXT NOT NULL DEFAULT 'poe1',
    league TEXT NOT NULL,
    item_class TEXT NOT NULL,
    base_type TEXT NOT NULL,
    ilvl INTEGER,
    influences TEXT,
    flags TEXT,
    affixes TEXT,
    price_chaos REAL NOT NULL,
    original_currency TEXT,
    original_amount REAL,
    seller_account TEXT,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    disappeared_at TIMESTAMP,
    listing_state TEXT NOT NULL DEFAULT 'LIVE',
    CHECK (listing_state IN ('LIVE', 'STALE', 'DISAPPEARED_FAST', 'DISAPPEARED_SLOW', 'EXCLUDED'))
);

CREATE INDEX IF NOT EXISTS idx_ml_listings_league ON ml_listings(league);
CREATE INDEX IF NOT EXISTS idx_ml_listings_base_type ON ml_listings(base_type);
CREATE INDEX IF NOT EXISTS idx_ml_listings_state ON ml_listings(listing_state);
CREATE INDEX IF NOT EXISTS idx_ml_listings_first_seen ON ml_listings(first_seen_at);

CREATE TABLE IF NOT EXISTS ml_collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    game_id TEXT NOT NULL DEFAULT 'poe1',
    league TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    listings_fetched INTEGER DEFAULT 0,
    listings_new INTEGER DEFAULT 0,
    listings_updated INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    error_details TEXT
);
"""

# Whitelist of allowed column names and types for v4 migration security
ALLOWED_MIGRATION_COLUMNS = {
    "league": "TEXT",
    "rarity": "TEXT",
    "game_version": "TEXT",
    "item_mods_json": "TEXT",
    "build_profile": "TEXT",
}
