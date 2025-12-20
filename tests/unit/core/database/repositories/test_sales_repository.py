"""
Tests for core/database/repositories/sales_repository.py

Tests sales tracking functionality.
"""
import pytest
from datetime import datetime

from core.database import Database

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


class TestAddSale:
    """Tests for add_sale method."""

    def test_add_basic_sale(self, temp_db):
        """Adds a basic sale entry."""
        sale_id = temp_db.add_sale(
            item_name="Exalted Orb",
            listed_price_chaos=150.0,
        )
        assert sale_id > 0

    def test_add_sale_with_base_type(self, temp_db):
        """Adds sale with item base type."""
        sale_id = temp_db.add_sale(
            item_name="Watcher's Eye",
            listed_price_chaos=5000.0,
            item_base_type="Prismatic Jewel",
        )
        assert sale_id > 0

    def test_add_multiple_sales(self, temp_db):
        """Adds multiple sales with unique IDs."""
        id1 = temp_db.add_sale("Item A", 100.0)
        id2 = temp_db.add_sale("Item B", 200.0)
        id3 = temp_db.add_sale("Item C", 300.0)

        assert id1 > 0
        assert id2 > id1
        assert id3 > id2


class TestRecordInstantSale:
    """Tests for record_instant_sale method."""

    def test_record_with_chaos_value(self, temp_db):
        """Records instant sale with chaos_value parameter."""
        sale_id = temp_db.record_instant_sale(
            item_name="Divine Orb",
            chaos_value=180.0,
        )
        assert sale_id > 0

    def test_record_with_price_chaos(self, temp_db):
        """Records instant sale with price_chaos parameter."""
        sale_id = temp_db.record_instant_sale(
            item_name="Divine Orb",
            price_chaos=180.0,
        )
        assert sale_id > 0

    def test_record_with_source(self, temp_db):
        """Records sale with source information."""
        sale_id = temp_db.record_instant_sale(
            item_name="Mirror of Kalandra",
            chaos_value=50000.0,
            source="trade_site",
        )
        assert sale_id > 0

    def test_record_with_notes(self, temp_db):
        """Records sale with notes."""
        sale_id = temp_db.record_instant_sale(
            item_name="6L Armor",
            chaos_value=500.0,
            notes="Quick flip",
        )
        assert sale_id > 0

    def test_record_raises_without_price(self, temp_db):
        """Raises ValueError if no price provided."""
        with pytest.raises(ValueError, match="requires either chaos_value or price_chaos"):
            temp_db.record_instant_sale(item_name="Item")

    def test_record_with_all_params(self, temp_db):
        """Records sale with all optional parameters."""
        sale_id = temp_db.record_instant_sale(
            item_name="Rare Helmet",
            chaos_value=100.0,
            item_base_type="Eternal Burgonet",
            notes="Good rolls",
            source="manual",
        )
        assert sale_id > 0


class TestCompleteSale:
    """Tests for complete_sale method."""

    def test_complete_sale_updates_price(self, temp_db):
        """Completing sale updates actual price."""
        sale_id = temp_db.add_sale("Item", 100.0)
        temp_db.complete_sale(sale_id, actual_price_chaos=90.0)

        sales = temp_db.get_sales(sold_only=True)
        assert len(sales) == 1
        assert sales[0]["actual_price_chaos"] == 90.0

    def test_complete_sale_sets_sold_at(self, temp_db):
        """Completing sale sets sold_at timestamp."""
        sale_id = temp_db.add_sale("Item", 100.0)
        sold_time = datetime.now()
        temp_db.complete_sale(sale_id, 100.0, sold_at=sold_time)

        sales = temp_db.get_sales(sold_only=True)
        assert sales[0]["sold_at"] is not None

    def test_complete_sale_calculates_time(self, temp_db):
        """Completing sale calculates time to sale."""
        sale_id = temp_db.add_sale("Item", 100.0)
        temp_db.complete_sale(sale_id, 100.0)

        sales = temp_db.get_sales(sold_only=True)
        assert "time_to_sale_hours" in sales[0]
        assert sales[0]["time_to_sale_hours"] >= 0


class TestMarkSaleUnsold:
    """Tests for mark_sale_unsold method."""

    def test_mark_unsold_sets_timestamp(self, temp_db):
        """Marking unsold sets sold_at timestamp."""
        sale_id = temp_db.add_sale("Item", 100.0)
        temp_db.mark_sale_unsold(sale_id)

        sales = temp_db.get_sales()
        matching = [s for s in sales if s["id"] == sale_id]
        assert len(matching) == 1
        assert matching[0]["sold_at"] is not None

    def test_mark_unsold_adds_note(self, temp_db):
        """Marking unsold adds 'Did not sell' note."""
        sale_id = temp_db.add_sale("Item", 100.0)
        temp_db.mark_sale_unsold(sale_id)

        sales = temp_db.get_sales()
        matching = [s for s in sales if s["id"] == sale_id]
        assert matching[0]["notes"] == "Did not sell"


class TestGetSales:
    """Tests for get_sales method."""

    def test_get_all_sales(self, temp_db):
        """Returns all sales."""
        temp_db.add_sale("Item A", 100.0)
        temp_db.add_sale("Item B", 200.0)

        sales = temp_db.get_sales()
        assert len(sales) >= 2

    def test_get_sold_only(self, temp_db):
        """Returns only completed sales."""
        id1 = temp_db.add_sale("Sold Item", 100.0)
        temp_db.add_sale("Unsold Item", 200.0)
        temp_db.complete_sale(id1, 95.0)

        sales = temp_db.get_sales(sold_only=True)
        assert len(sales) == 1
        assert sales[0]["item_name"] == "Sold Item"

    def test_get_sales_with_limit(self, temp_db):
        """Respects limit parameter."""
        for i in range(10):
            temp_db.add_sale(f"Item {i}", float(i * 10))

        sales = temp_db.get_sales(limit=5)
        assert len(sales) == 5

    def test_get_sales_returns_all_items(self, temp_db):
        """Returns all sales items."""
        temp_db.add_sale("First", 100.0)
        temp_db.add_sale("Second", 200.0)
        temp_db.add_sale("Third", 300.0)

        sales = temp_db.get_sales()
        # Should have all 3
        names = [s["item_name"] for s in sales]
        assert "First" in names
        assert "Second" in names
        assert "Third" in names


class TestGetRecentSales:
    """Tests for get_recent_sales method."""

    def test_get_recent_returns_list(self, temp_db):
        """Returns a list of sales."""
        temp_db.record_instant_sale("Item", chaos_value=100.0)

        sales = temp_db.get_recent_sales()
        assert isinstance(sales, list)
        assert len(sales) >= 1

    def test_get_recent_with_search(self, temp_db):
        """Filters by search text."""
        temp_db.record_instant_sale("Divine Orb", chaos_value=180.0)
        temp_db.record_instant_sale("Exalted Orb", chaos_value=15.0)

        sales = temp_db.get_recent_sales(search_text="Divine")
        assert len(sales) == 1
        assert "Divine" in sales[0]["item_name"]

    def test_get_recent_with_source_filter(self, temp_db):
        """Filters by source."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0, source="trade")
        temp_db.record_instant_sale("Item B", chaos_value=200.0, source="loot")

        sales = temp_db.get_recent_sales(source="trade")
        assert len(sales) == 1
        assert sales[0]["source"] == "trade"

    def test_get_recent_with_limit(self, temp_db):
        """Respects limit parameter."""
        for i in range(10):
            temp_db.record_instant_sale(f"Item {i}", chaos_value=float(i))

        sales = temp_db.get_recent_sales(limit=3)
        assert len(sales) == 3

    def test_get_recent_source_all_returns_all(self, temp_db):
        """Source 'All' returns all sources."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0, source="trade")
        temp_db.record_instant_sale("Item B", chaos_value=200.0, source="loot")

        sales = temp_db.get_recent_sales(source="All")
        assert len(sales) == 2


class TestGetDistinctSaleSources:
    """Tests for get_distinct_sale_sources method."""

    def test_returns_unique_sources(self, temp_db):
        """Returns distinct sources."""
        temp_db.record_instant_sale("Item 1", chaos_value=100.0, source="trade")
        temp_db.record_instant_sale("Item 2", chaos_value=200.0, source="loot")
        temp_db.record_instant_sale("Item 3", chaos_value=300.0, source="trade")

        sources = temp_db.get_distinct_sale_sources()
        assert "trade" in sources
        assert "loot" in sources
        # Should be distinct
        assert sources.count("trade") == 1

    def test_excludes_empty_sources(self, temp_db):
        """Excludes empty/null sources."""
        temp_db.record_instant_sale("Item", chaos_value=100.0, source="")
        temp_db.record_instant_sale("Item 2", chaos_value=200.0, source="valid")

        sources = temp_db.get_distinct_sale_sources()
        assert "" not in sources
        assert "valid" in sources

    def test_returns_sorted_list(self, temp_db):
        """Returns sources sorted alphabetically."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0, source="zebra")
        temp_db.record_instant_sale("Item B", chaos_value=200.0, source="alpha")

        sources = temp_db.get_distinct_sale_sources()
        assert sources == sorted(sources, key=str.lower)


class TestGetSalesSummary:
    """Tests for get_sales_summary method."""

    def test_summary_with_no_sales(self, temp_db):
        """Returns zeros with no sales."""
        summary = temp_db.get_sales_summary()

        assert summary["total_sales"] == 0
        assert summary["total_chaos"] == 0.0
        assert summary["avg_chaos"] == 0.0

    def test_summary_counts_sales(self, temp_db):
        """Counts total sales correctly."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0)
        temp_db.record_instant_sale("Item B", chaos_value=200.0)

        summary = temp_db.get_sales_summary()
        assert summary["total_sales"] == 2

    def test_summary_sums_chaos(self, temp_db):
        """Sums total chaos correctly."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0)
        temp_db.record_instant_sale("Item B", chaos_value=200.0)

        summary = temp_db.get_sales_summary()
        assert summary["total_chaos"] == 300.0

    def test_summary_averages_chaos(self, temp_db):
        """Calculates average correctly."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0)
        temp_db.record_instant_sale("Item B", chaos_value=200.0)

        summary = temp_db.get_sales_summary()
        assert summary["avg_chaos"] == 150.0


class TestGetDailySalesSummary:
    """Tests for get_daily_sales_summary method."""

    def test_returns_list(self, temp_db):
        """Returns a list of daily summaries."""
        temp_db.record_instant_sale("Item", chaos_value=100.0)

        summary = temp_db.get_daily_sales_summary(days=7)
        assert isinstance(summary, list)

    def test_groups_by_day(self, temp_db):
        """Groups sales by day."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0)
        temp_db.record_instant_sale("Item B", chaos_value=200.0)

        summary = temp_db.get_daily_sales_summary(days=7)
        # Today's sales should be grouped
        assert len(summary) >= 1

    def test_includes_count_and_totals(self, temp_db):
        """Each day includes count and totals."""
        temp_db.record_instant_sale("Item A", chaos_value=100.0)
        temp_db.record_instant_sale("Item B", chaos_value=200.0)

        summary = temp_db.get_daily_sales_summary(days=7)
        if summary:
            day_data = summary[0]
            assert "sale_count" in day_data.keys()
            assert "total_chaos" in day_data.keys()
            assert "avg_chaos" in day_data.keys()


class TestSalesIntegration:
    """Integration tests for sales workflows."""

    def test_full_sale_lifecycle(self, temp_db):
        """Tests complete sale workflow."""
        # List item
        sale_id = temp_db.add_sale("Rare Ring", 50.0, item_base_type="Two-Stone Ring")

        # Get pending sales
        pending = temp_db.get_sales(sold_only=False)
        assert any(s["id"] == sale_id for s in pending)

        # Complete sale
        temp_db.complete_sale(sale_id, actual_price_chaos=45.0)

        # Verify in sold list
        sold = temp_db.get_sales(sold_only=True)
        sale = next(s for s in sold if s["id"] == sale_id)
        assert sale["actual_price_chaos"] == 45.0

        # Verify in summary
        summary = temp_db.get_sales_summary()
        assert summary["total_sales"] >= 1

    def test_instant_sale_appears_in_all_views(self, temp_db):
        """Instant sales appear in all query methods."""
        temp_db.record_instant_sale(
            "Quick Sale",
            chaos_value=100.0,
            source="loot",
        )

        # Should appear in get_sales
        all_sales = temp_db.get_sales()
        assert any("Quick Sale" in s["item_name"] for s in all_sales)

        # Should appear in get_recent_sales
        recent = temp_db.get_recent_sales()
        assert any("Quick Sale" in s["item_name"] for s in recent)

        # Should be in summary
        summary = temp_db.get_sales_summary()
        assert summary["total_sales"] >= 1

        # Source should be tracked
        sources = temp_db.get_distinct_sale_sources()
        assert "loot" in sources
