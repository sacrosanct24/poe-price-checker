"""Tests for ml/collection/affix_extractor.py."""

import pytest

from core.item_parser import ParsedItem
from data_sources.mod_database import ModDatabase
from ml.collection.affix_extractor import AffixExtractor


def test_extract_affix_with_tier(tmp_path):
    db_path = tmp_path / "mods.db"
    with ModDatabase(db_path=db_path) as db:
        db.conn.execute(
            """
            INSERT INTO mods (id, stat_text_raw, tier_text)
            VALUES (?, ?, ?)
            """,
            ("mod_life_t1", "+(70-79) to maximum Life", "Tier 1"),
        )
        db.conn.execute(
            """
            INSERT INTO mods (id, stat_text_raw, tier_text)
            VALUES (?, ?, ?)
            """,
            ("mod_life_t2", "+(60-69) to maximum Life", "Tier 2"),
        )
        db.conn.commit()

        item = ParsedItem(raw_text="test", explicits=["+75 to maximum Life"])
        extractor = AffixExtractor(db)
        affixes = extractor.extract(item)

    assert len(affixes) == 1
    affix = affixes[0]
    assert affix["affix_id"] == "mod_life_t1"
    assert affix["tier"] == 1
    assert affix["value"] == 75.0
    assert affix["roll_percentile"] == pytest.approx((75 - 70) / (79 - 70))


def test_extract_affix_missing_mod(tmp_path):
    db_path = tmp_path / "mods.db"
    with ModDatabase(db_path=db_path) as db:
        item = ParsedItem(raw_text="test", explicits=["+12 to maximum Mana"])
        extractor = AffixExtractor(db)
        affixes = extractor.extract(item)

    assert affixes == []
