"""
Tests for core/database/repositories/price_alert_repository.py

Tests price alert CRUD operations and cooldown logic.
"""
import pytest

from core.database import Database

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


# ============================================================================
# Create Alert Tests
# ============================================================================


class TestCreateAlert:
    """Tests for create_price_alert method."""

    def test_create_basic_alert(self, temp_db):
        """Creates a basic price alert."""
        alert_id = temp_db.create_price_alert(
            item_name="Divine Orb",
            league="Standard",
            game_version="poe1",
            alert_type="below",
            threshold_chaos=100.0,
        )
        assert alert_id > 0

    def test_create_alert_with_base_type(self, temp_db):
        """Creates alert with item base type."""
        alert_id = temp_db.create_price_alert(
            item_name="Mageblood",
            league="Standard",
            game_version="poe1",
            alert_type="above",
            threshold_chaos=50000.0,
            item_base_type="Heavy Belt",
        )
        assert alert_id > 0

        alert = temp_db.get_price_alert(alert_id)
        assert alert["item_base_type"] == "Heavy Belt"

    def test_create_alert_with_custom_cooldown(self, temp_db):
        """Creates alert with custom cooldown."""
        alert_id = temp_db.create_price_alert(
            item_name="Exalted Orb",
            league="Standard",
            game_version="poe1",
            alert_type="below",
            threshold_chaos=10.0,
            cooldown_minutes=60,
        )

        alert = temp_db.get_price_alert(alert_id)
        assert alert["cooldown_minutes"] == 60

    def test_create_multiple_alerts(self, temp_db):
        """Creates multiple alerts for different items."""
        id1 = temp_db.create_price_alert(
            "Item1", "Standard", "poe1", "below", 100.0
        )
        id2 = temp_db.create_price_alert(
            "Item2", "Standard", "poe1", "above", 200.0
        )
        assert id1 > 0
        assert id2 > 0
        assert id1 != id2


# ============================================================================
# Get Alert Tests
# ============================================================================


class TestGetAlert:
    """Tests for get_price_alert method."""

    def test_get_existing_alert(self, temp_db):
        """Gets an existing alert by ID."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 50.0
        )

        alert = temp_db.get_price_alert(alert_id)

        assert alert is not None
        assert alert["item_name"] == "Test Item"
        assert alert["league"] == "Standard"
        assert alert["alert_type"] == "below"
        assert alert["threshold_chaos"] == 50.0
        assert alert["enabled"] == 1

    def test_get_nonexistent_alert(self, temp_db):
        """Returns None for nonexistent alert."""
        alert = temp_db.get_price_alert(99999)
        assert alert is None

    def test_alert_has_timestamps(self, temp_db):
        """Alert has created_at and updated_at."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 50.0
        )

        alert = temp_db.get_price_alert(alert_id)

        assert alert["created_at"] is not None
        assert alert["updated_at"] is not None


# ============================================================================
# Get Active Alerts Tests
# ============================================================================


class TestGetActiveAlerts:
    """Tests for get_active_price_alerts method."""

    def test_get_active_alerts(self, temp_db):
        """Returns enabled alerts for league."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Standard", "poe1", "above", 200.0)

        alerts = temp_db.get_active_price_alerts("Standard", "poe1")

        assert len(alerts) == 2

    def test_excludes_disabled_alerts(self, temp_db):
        """Does not return disabled alerts."""
        id1 = temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Standard", "poe1", "above", 200.0)

        # Disable first alert
        temp_db.update_price_alert(id1, enabled=False)

        alerts = temp_db.get_active_price_alerts("Standard", "poe1")

        assert len(alerts) == 1
        assert alerts[0]["item_name"] == "Item2"

    def test_filters_by_league(self, temp_db):
        """Only returns alerts for specified league."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Settlers", "poe1", "above", 200.0)

        alerts = temp_db.get_active_price_alerts("Standard", "poe1")

        assert len(alerts) == 1
        assert alerts[0]["item_name"] == "Item1"

    def test_filters_by_game_version(self, temp_db):
        """Only returns alerts for specified game version."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Standard", "poe2", "above", 200.0)

        alerts = temp_db.get_active_price_alerts("Standard", "poe1")

        assert len(alerts) == 1
        assert alerts[0]["item_name"] == "Item1"


# ============================================================================
# Update Alert Tests
# ============================================================================


class TestUpdateAlert:
    """Tests for update_price_alert method."""

    def test_update_threshold(self, temp_db):
        """Updates threshold value."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.update_price_alert(alert_id, threshold_chaos=150.0)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["threshold_chaos"] == 150.0

    def test_update_alert_type(self, temp_db):
        """Updates alert type."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.update_price_alert(alert_id, alert_type="above")

        alert = temp_db.get_price_alert(alert_id)
        assert alert["alert_type"] == "above"

    def test_disable_alert(self, temp_db):
        """Disables an alert."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.update_price_alert(alert_id, enabled=False)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["enabled"] == 0

    def test_enable_alert(self, temp_db):
        """Re-enables a disabled alert."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )
        temp_db.update_price_alert(alert_id, enabled=False)

        temp_db.update_price_alert(alert_id, enabled=True)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["enabled"] == 1

    def test_update_cooldown(self, temp_db):
        """Updates cooldown minutes."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0, cooldown_minutes=30
        )

        temp_db.update_price_alert(alert_id, cooldown_minutes=60)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["cooldown_minutes"] == 60

    def test_update_nonexistent_alert_returns_false(self, temp_db):
        """Returns False when updating nonexistent alert."""
        result = temp_db.update_price_alert(99999, threshold_chaos=100.0)
        assert result is False


# ============================================================================
# Delete Alert Tests
# ============================================================================


class TestDeleteAlert:
    """Tests for delete_price_alert method."""

    def test_delete_existing_alert(self, temp_db):
        """Deletes an existing alert."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        result = temp_db.delete_price_alert(alert_id)

        assert result is True
        assert temp_db.get_price_alert(alert_id) is None

    def test_delete_nonexistent_alert(self, temp_db):
        """Returns False when deleting nonexistent alert."""
        result = temp_db.delete_price_alert(99999)
        assert result is False


# ============================================================================
# Trigger Logic Tests
# ============================================================================


class TestShouldTrigger:
    """Tests for should_alert_trigger method."""

    def test_triggers_when_price_below_threshold(self, temp_db):
        """Triggers when price drops below threshold."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "below", 100.0
        )

        # Price is 80c, threshold is 100c, should trigger
        should = temp_db.should_alert_trigger(alert_id, 80.0)
        assert should is True

    def test_triggers_when_price_above_threshold(self, temp_db):
        """Triggers when price rises above threshold."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "above", 100.0
        )

        # Price is 120c, threshold is 100c, should trigger
        should = temp_db.should_alert_trigger(alert_id, 120.0)
        assert should is True

    def test_no_trigger_when_price_below_for_above_alert(self, temp_db):
        """Does not trigger when price is below threshold for 'above' alert."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "above", 100.0
        )

        should = temp_db.should_alert_trigger(alert_id, 80.0)
        assert should is False

    def test_no_trigger_when_price_above_for_below_alert(self, temp_db):
        """Does not trigger when price is above threshold for 'below' alert."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "below", 100.0
        )

        should = temp_db.should_alert_trigger(alert_id, 120.0)
        assert should is False

    def test_no_trigger_for_disabled_alert(self, temp_db):
        """Does not trigger for disabled alerts."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "below", 100.0
        )
        temp_db.update_price_alert(alert_id, enabled=False)

        should = temp_db.should_alert_trigger(alert_id, 80.0)
        assert should is False

    def test_no_trigger_during_cooldown(self, temp_db):
        """Does not trigger during cooldown period."""
        alert_id = temp_db.create_price_alert(
            "Divine Orb", "Standard", "poe1", "below", 100.0, cooldown_minutes=30
        )

        # Record a trigger
        temp_db.record_alert_trigger(alert_id, 80.0)

        # Should not trigger again during cooldown
        should = temp_db.should_alert_trigger(alert_id, 70.0)
        assert should is False


# ============================================================================
# Record Trigger Tests
# ============================================================================


class TestRecordTrigger:
    """Tests for record_alert_trigger method."""

    def test_record_trigger_updates_count(self, temp_db):
        """Increments trigger count."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.record_alert_trigger(alert_id, 80.0)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["trigger_count"] == 1

    def test_record_trigger_updates_last_price(self, temp_db):
        """Updates last known price."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.record_alert_trigger(alert_id, 80.0)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["last_price_chaos"] == 80.0

    def test_record_trigger_updates_timestamp(self, temp_db):
        """Updates last triggered timestamp."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0
        )

        temp_db.record_alert_trigger(alert_id, 80.0)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["last_triggered_at"] is not None

    def test_multiple_triggers_increment_count(self, temp_db):
        """Multiple triggers increment count correctly."""
        alert_id = temp_db.create_price_alert(
            "Test Item", "Standard", "poe1", "below", 100.0, cooldown_minutes=0
        )

        temp_db.record_alert_trigger(alert_id, 80.0)
        temp_db.record_alert_trigger(alert_id, 70.0)
        temp_db.record_alert_trigger(alert_id, 60.0)

        alert = temp_db.get_price_alert(alert_id)
        assert alert["trigger_count"] == 3
        assert alert["last_price_chaos"] == 60.0


# ============================================================================
# Statistics Tests
# ============================================================================


class TestAlertStatistics:
    """Tests for get_price_alert_statistics method."""

    def test_empty_stats(self, temp_db):
        """Returns zeros for empty database."""
        stats = temp_db.get_price_alert_statistics()

        assert stats["total_alerts"] == 0
        assert stats["enabled_alerts"] == 0
        assert stats["total_triggers"] == 0

    def test_stats_count_alerts(self, temp_db):
        """Counts total and enabled alerts."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        id2 = temp_db.create_price_alert("Item2", "Standard", "poe1", "above", 200.0)
        temp_db.create_price_alert("Item3", "Standard", "poe1", "below", 50.0)
        temp_db.update_price_alert(id2, enabled=False)

        stats = temp_db.get_price_alert_statistics()

        assert stats["total_alerts"] == 3
        assert stats["enabled_alerts"] == 2

    def test_stats_count_by_type(self, temp_db):
        """Counts alerts by type."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Standard", "poe1", "above", 200.0)
        temp_db.create_price_alert("Item3", "Standard", "poe1", "below", 50.0)

        stats = temp_db.get_price_alert_statistics()

        assert stats["below_alerts"] == 2
        assert stats["above_alerts"] == 1

    def test_stats_sum_triggers(self, temp_db):
        """Sums total trigger count."""
        id1 = temp_db.create_price_alert(
            "Item1", "Standard", "poe1", "below", 100.0, cooldown_minutes=0
        )
        id2 = temp_db.create_price_alert(
            "Item2", "Standard", "poe1", "below", 200.0, cooldown_minutes=0
        )

        temp_db.record_alert_trigger(id1, 80.0)
        temp_db.record_alert_trigger(id1, 70.0)
        temp_db.record_alert_trigger(id2, 150.0)

        stats = temp_db.get_price_alert_statistics()

        assert stats["total_triggers"] == 3


# ============================================================================
# Clear Alerts Tests
# ============================================================================


class TestClearAlerts:
    """Tests for clear_price_alerts method."""

    def test_clear_all_alerts(self, temp_db):
        """Clears all alerts."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Settlers", "poe1", "above", 200.0)
        temp_db.create_price_alert("Item3", "Standard", "poe2", "below", 50.0)

        deleted = temp_db.clear_price_alerts()

        assert deleted == 3
        assert len(temp_db.get_all_price_alerts()) == 0

    def test_clear_by_league(self, temp_db):
        """Clears alerts for specific league."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Settlers", "poe1", "above", 200.0)
        temp_db.create_price_alert("Item3", "Standard", "poe1", "below", 50.0)

        deleted = temp_db.clear_price_alerts(league="Standard")

        assert deleted == 2
        remaining = temp_db.get_all_price_alerts()
        assert len(remaining) == 1
        assert remaining[0]["league"] == "Settlers"

    def test_clear_by_game_version(self, temp_db):
        """Clears alerts for specific game version."""
        temp_db.create_price_alert("Item1", "Standard", "poe1", "below", 100.0)
        temp_db.create_price_alert("Item2", "Standard", "poe2", "above", 200.0)

        deleted = temp_db.clear_price_alerts(game_version="poe1")

        assert deleted == 1
        remaining = temp_db.get_all_price_alerts()
        assert len(remaining) == 1
        assert remaining[0]["game_version"] == "poe2"
