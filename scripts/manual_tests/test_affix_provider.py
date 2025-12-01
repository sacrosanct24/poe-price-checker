"""
Test script for AffixDataProvider

Demonstrates the hybrid database + JSON fallback system.
"""
import logging
from data_sources.affix_data_provider import AffixDataProvider, get_affix_provider
from data_sources.mod_database import ModDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)


def test_json_fallback():
    """Test using JSON fallback (no database)."""
    print("=" * 80)
    print("TEST 1: JSON Fallback (No Database)")
    print("=" * 80)

    provider = AffixDataProvider(mod_database=None)

    print(f"\nData source: {provider.get_source_info()}")
    print(f"Using database: {provider.is_using_database()}")

    # Test getting tier ranges
    print("\n--- Life Tiers (from JSON) ---")
    life_tiers = provider.get_affix_tiers("life")
    for tier, min_val, max_val in life_tiers:
        print(f"  T{tier}: {min_val}-{max_val}")

    print("\n--- Movement Speed Tiers (from JSON) ---")
    ms_tiers = provider.get_affix_tiers("movement_speed")
    for tier, min_val, max_val in ms_tiers:
        print(f"  T{tier}: {min_val}-{max_val}%")

    # Test getting affix config
    print("\n--- Life Affix Config ---")
    life_config = provider.get_affix_config("life")
    print(f"  Patterns: {life_config.get('tier1', [])}")
    print(f"  Weight: {life_config.get('weight')}")
    print(f"  Categories: {life_config.get('categories')}")

    # Test getting all types
    print("\n--- All Affix Types ---")
    all_types = provider.get_all_affix_types()
    print(f"  Total: {len(all_types)}")
    print(f"  Types: {', '.join(all_types[:10])}...")


def test_empty_database():
    """Test with empty database (should still fall back to JSON)."""
    print("\n" + "=" * 80)
    print("TEST 2: Empty Database (Falls back to JSON)")
    print("=" * 80)

    # Create empty database
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_empty.db"
        db = ModDatabase(db_path)

        provider = AffixDataProvider(mod_database=db)

        print(f"\nData source: {provider.get_source_info()}")
        print(f"Using database: {provider.is_using_database()}")
        print(f"Database mod count: {db.get_mod_count()}")

        # Should still get tiers from JSON
        print("\n--- Life Tiers (should be from JSON) ---")
        life_tiers = provider.get_affix_tiers("life")
        for tier, min_val, max_val in life_tiers:
            print(f"  T{tier}: {min_val}-{max_val}")


def test_populated_database():
    """Test with populated database (mock data)."""
    print("\n" + "=" * 80)
    print("TEST 3: Populated Database (Mock Data)")
    print("=" * 80)

    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_populated.db"
        db = ModDatabase(db_path)

        # Insert mock mod data
        mock_mods = [
            {
                'id': 'LifeT1',
                'name': 'of the Titan',
                'stat_text': '+# to maximum Life',
                'domain': 1,
                'generation_type': 7,  # suffix
                'mod_group': 'IncreasedLife',
                'required_level': 44,
                'stat1_id': 'base_maximum_life',
                'stat1_min': 100,
                'stat1_max': 109,
                'stat2_id': None,
                'stat2_min': None,
                'stat2_max': None,
                'tags': 'life',
            },
            {
                'id': 'LifeT2',
                'name': 'of the Bear',
                'stat_text': '+# to maximum Life',
                'domain': 1,
                'generation_type': 7,
                'mod_group': 'IncreasedLife',
                'required_level': 30,
                'stat1_id': 'base_maximum_life',
                'stat1_min': 90,
                'stat1_max': 99,
                'stat2_id': None,
                'stat2_min': None,
                'stat2_max': None,
                'tags': 'life',
            },
            {
                'id': 'LifeT3',
                'name': 'of the Troll',
                'stat_text': '+# to maximum Life',
                'domain': 1,
                'generation_type': 7,
                'mod_group': 'IncreasedLife',
                'required_level': 18,
                'stat1_id': 'base_maximum_life',
                'stat1_min': 80,
                'stat1_max': 89,
                'stat2_id': None,
                'stat2_min': None,
                'stat2_max': None,
                'tags': 'life',
            },
        ]

        count = db.insert_mods(mock_mods)
        print(f"\nInserted {count} mock mods")

        # Set metadata
        db.set_metadata('league', 'Test League')
        db.set_metadata('last_update', '2025-01-01T12:00:00')

        provider = AffixDataProvider(mod_database=db)

        print(f"\nData source: {provider.get_source_info()}")
        print(f"Using database: {provider.is_using_database()}")

        # Test querying database
        print("\n--- Life Tiers (from Database) ---")
        life_tiers = provider.get_affix_tiers(
            affix_type="life",
            stat_text_pattern="%to maximum Life"
        )
        for tier, min_val, max_val in life_tiers:
            print(f"  T{tier}: {min_val}-{max_val}")


def test_singleton_provider():
    """Test the singleton get_affix_provider()."""
    print("\n" + "=" * 80)
    print("TEST 4: Singleton Provider")
    print("=" * 80)

    provider1 = get_affix_provider()
    provider2 = get_affix_provider()

    print(f"\nProvider 1: {id(provider1)}")
    print(f"Provider 2: {id(provider2)}")
    print(f"Same instance: {provider1 is provider2}")
    print(f"\nSource: {provider1.get_source_info()}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("AFFIX DATA PROVIDER TEST SUITE")
    print("=" * 80)

    try:
        test_json_fallback()
        test_empty_database()
        test_populated_database()
        test_singleton_provider()

        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
