"""Tests for league economy history service."""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.database import Database
from core.league_economy_history import (
    LeagueEconomyService,
    LeagueMilestone,
    LeagueEconomySnapshot,
    UniqueSnapshot,
    reset_league_economy_service,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    db = Database(db_path)
    yield db

    db.close()
    db_path.unlink(missing_ok=True)
    reset_league_economy_service()


@pytest.fixture
def service(temp_db):
    """Create service with temp database."""
    return LeagueEconomyService(temp_db)


@pytest.fixture
def sample_currency_csv():
    """Sample poe.ninja currency CSV data."""
    return """League;Date;Get;Pay;Value;Confidence
Settlers;2024-07-26;Divine Orb;Chaos Orb;180.5;High
Settlers;2024-07-26;Exalted Orb;Chaos Orb;12.3;High
Settlers;2024-07-27;Divine Orb;Chaos Orb;175.2;High
Settlers;2024-07-27;Exalted Orb;Chaos Orb;11.8;High
Settlers;2024-08-01;Divine Orb;Chaos Orb;160.0;High
Necropolis;2024-03-29;Divine Orb;Chaos Orb;200.0;High
"""


@pytest.fixture
def sample_item_csv():
    """Sample poe.ninja item CSV data."""
    return """League;Date;Name;BaseType;Value
Settlers;2024-07-26;Mageblood;Heavy Belt;150000.0
Settlers;2024-07-26;Headhunter;Leather Belt;45000.0
Settlers;2024-07-26;The Squire;Elegant Round Shield;35000.0
Settlers;2024-07-27;Mageblood;Heavy Belt;148000.0
Settlers;2024-07-27;Headhunter;Leather Belt;44000.0
"""


class TestLeagueEconomyService:
    """Tests for LeagueEconomyService."""

    def test_import_currency_csv(self, service, sample_currency_csv):
        """Test importing currency rates from CSV."""
        rows_imported = service.import_currency_csv(sample_currency_csv, "Settlers")
        # 5 rows for Settlers (Divine + Exalted for 3 dates, but only 5 Settlers rows)
        assert rows_imported == 5

    def test_import_currency_csv_filters_league(self, service, sample_currency_csv):
        """Test that import filters by league."""
        # Import only Necropolis
        rows_imported = service.import_currency_csv(sample_currency_csv, "Necropolis")
        assert rows_imported == 1

    def test_import_item_csv(self, service, sample_item_csv):
        """Test importing item prices from CSV."""
        rows_imported = service.import_item_csv(
            sample_item_csv, "Settlers", item_type="UniqueAccessory"
        )
        assert rows_imported == 5

    def test_get_divine_rate_history(self, service, sample_currency_csv):
        """Test getting Divine Orb rate history."""
        service.import_currency_csv(sample_currency_csv, "Settlers")

        history = service.get_divine_rate_history("Settlers")

        assert len(history) == 3
        # Should be ordered by date ascending
        assert history[0]["chaos_value"] == 180.5
        assert history[1]["chaos_value"] == 175.2
        assert history[2]["chaos_value"] == 160.0

    def test_get_currency_rate_at_date(self, service, sample_currency_csv):
        """Test getting currency rate at specific date."""
        service.import_currency_csv(sample_currency_csv, "Settlers")

        rate = service.get_currency_rate_at_date(
            "Settlers",
            "Divine Orb",
            datetime(2024, 7, 27),
        )

        assert rate == 175.2

    def test_get_currency_rate_at_date_nearest(self, service, sample_currency_csv):
        """Test that it returns nearest date if exact match not found."""
        service.import_currency_csv(sample_currency_csv, "Settlers")

        # Date between 7/27 and 8/1 - should return closest
        rate = service.get_currency_rate_at_date(
            "Settlers",
            "Divine Orb",
            datetime(2024, 7, 29),
        )

        # 7/27 is closer to 7/29 than 8/1
        assert rate == 175.2

    def test_save_and_load_milestone_snapshot(self, service):
        """Test saving and loading milestone snapshots."""
        snapshot = LeagueEconomySnapshot(
            league="Settlers",
            milestone=LeagueMilestone.WEEK_1_END,
            snapshot_date=datetime(2024, 8, 2),
            divine_to_chaos=165.0,
            exalt_to_chaos=11.5,
            top_uniques=[
                UniqueSnapshot(
                    league="Settlers",
                    date=datetime(2024, 8, 2),
                    item_name="Mageblood",
                    base_type="Heavy Belt",
                    chaos_value=145000.0,
                    divine_value=879.0,
                    rank=1,
                ),
                UniqueSnapshot(
                    league="Settlers",
                    date=datetime(2024, 8, 2),
                    item_name="Headhunter",
                    base_type="Leather Belt",
                    chaos_value=42000.0,
                    divine_value=254.5,
                    rank=2,
                ),
            ],
        )

        snapshot_id = service.save_milestone_snapshot(snapshot)
        assert snapshot_id > 0

        # Load it back
        snapshots = service.get_league_snapshots("Settlers")
        assert len(snapshots) == 1

        loaded = snapshots[0]
        assert loaded.league == "Settlers"
        assert loaded.milestone == LeagueMilestone.WEEK_1_END
        assert loaded.divine_to_chaos == 165.0
        assert loaded.exalt_to_chaos == 11.5
        assert len(loaded.top_uniques) == 2
        assert loaded.top_uniques[0].item_name == "Mageblood"
        assert loaded.top_uniques[1].item_name == "Headhunter"

    def test_multiple_milestones(self, service):
        """Test storing multiple milestones for same league."""
        milestones = [
            (LeagueMilestone.LEAGUE_START, datetime(2024, 7, 26)),
            (LeagueMilestone.WEEK_1_END, datetime(2024, 8, 2)),
            (LeagueMilestone.MONTH_1_END, datetime(2024, 8, 26)),
        ]

        for i, (milestone, date) in enumerate(milestones):
            snapshot = LeagueEconomySnapshot(
                league="Settlers",
                milestone=milestone,
                snapshot_date=date,
                divine_to_chaos=180.0 - i * 10,
            )
            service.save_milestone_snapshot(snapshot)

        snapshots = service.get_league_snapshots("Settlers")
        assert len(snapshots) == 3

        # Should be ordered by date
        assert snapshots[0].milestone == LeagueMilestone.LEAGUE_START
        assert snapshots[1].milestone == LeagueMilestone.WEEK_1_END
        assert snapshots[2].milestone == LeagueMilestone.MONTH_1_END

    def test_get_available_leagues(self, service, sample_currency_csv):
        """Test getting list of available leagues."""
        service.import_currency_csv(sample_currency_csv, "Settlers")
        service.import_currency_csv(sample_currency_csv, "Necropolis")

        leagues = service.get_available_leagues()

        assert "Settlers" in leagues
        assert "Necropolis" in leagues

    def test_get_league_date_range(self, service, sample_currency_csv):
        """Test getting date range for a league."""
        service.import_currency_csv(sample_currency_csv, "Settlers")

        date_range = service.get_league_date_range("Settlers")

        assert date_range is not None
        assert date_range["start"] == datetime(2024, 7, 26)
        assert date_range["end"] == datetime(2024, 8, 1)

    def test_get_league_date_range_empty(self, service):
        """Test date range returns None for unknown league."""
        date_range = service.get_league_date_range("UnknownLeague")
        assert date_range is None

    def test_get_top_uniques_at_date(self, service, sample_item_csv):
        """Test getting top uniques at a specific date."""
        service.import_item_csv(sample_item_csv, "Settlers")

        uniques = service.get_top_uniques_at_date(
            "Settlers",
            datetime(2024, 7, 26),
            limit=3,
        )

        assert len(uniques) == 3
        # Should be ordered by value descending
        assert uniques[0].item_name == "Mageblood"
        assert uniques[0].rank == 1
        assert uniques[1].item_name == "Headhunter"
        assert uniques[1].rank == 2
        assert uniques[2].item_name == "The Squire"
        assert uniques[2].rank == 3

    def test_display_milestone(self):
        """Test milestone display names."""
        snapshot = LeagueEconomySnapshot(
            league="Test",
            milestone=LeagueMilestone.LEAGUE_START,
            snapshot_date=datetime.now(),
            divine_to_chaos=100.0,
        )
        assert snapshot.display_milestone == "League Start"

        snapshot.milestone = LeagueMilestone.WEEK_1_END
        assert snapshot.display_milestone == "Week 1"

        snapshot.milestone = LeagueMilestone.MONTH_1_END
        assert snapshot.display_milestone == "Month 1"

        snapshot.milestone = LeagueMilestone.LEAGUE_END
        assert snapshot.display_milestone == "End of League"


class TestCsvParsing:
    """Tests for CSV parsing edge cases."""

    def test_empty_csv(self, service):
        """Test importing empty CSV."""
        rows = service.import_currency_csv("League;Date;Get;Pay;Value;Confidence", "Test")
        assert rows == 0

    def test_malformed_csv_row(self, service):
        """Test that malformed rows are skipped."""
        csv = """League;Date;Get;Pay;Value;Confidence
Settlers;bad-date;Divine Orb;Chaos Orb;180.5;High
Settlers;2024-07-26;Divine Orb;Chaos Orb;not-a-number;High
Settlers;2024-07-26;Divine Orb;Chaos Orb;180.5;High
"""
        rows = service.import_currency_csv(csv, "Settlers")
        # Only the last valid row should be imported
        assert rows == 1

    def test_csv_with_different_pay_currency(self, service):
        """Test that only Chaos Orb pay currency is imported."""
        csv = """League;Date;Get;Pay;Value;Confidence
Settlers;2024-07-26;Chaos Orb;Divine Orb;0.005;High
Settlers;2024-07-26;Divine Orb;Chaos Orb;180.5;High
"""
        rows = service.import_currency_csv(csv, "Settlers")
        # Only Divine -> Chaos row should be imported
        assert rows == 1
