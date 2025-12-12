"""
Tests for ExportService.
"""

import pytest
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from core.services.export_service import ExportService, ExportResult


@pytest.fixture
def mock_db():
    """Create a mock database."""
    db = Mock()
    db.conn = Mock()
    return db


@pytest.fixture
def service(mock_db):
    """Create an ExportService instance."""
    return ExportService(mock_db)


@pytest.fixture
def service_no_db():
    """Create an ExportService without database."""
    return ExportService(None)


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_success_result(self, tmp_path):
        """Test successful export result."""
        result = ExportResult(
            success=True,
            file_path=tmp_path / "test.json",
            record_count=10
        )
        assert result.success is True
        assert result.record_count == 10
        assert result.error is None

    def test_failure_result(self):
        """Test failed export result."""
        result = ExportResult(
            success=False,
            error="Test error"
        )
        assert result.success is False
        assert result.error == "Test error"


class TestExportToJson:
    """Tests for JSON export."""

    def test_export_to_json_success(self, service, tmp_path):
        """Test successful JSON export."""
        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200},
        ]
        file_path = tmp_path / "test.json"

        result = service.export_to_json(data, file_path)

        assert result.success is True
        assert result.record_count == 2
        assert file_path.exists()

        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert len(loaded) == 2
        assert loaded[0]["name"] == "Item 1"

    def test_export_to_json_pretty(self, service, tmp_path):
        """Test JSON export with pretty formatting."""
        data = [{"name": "Test"}]
        file_path = tmp_path / "pretty.json"

        result = service.export_to_json(data, file_path, pretty=True)

        assert result.success is True
        content = file_path.read_text(encoding='utf-8')
        # Pretty JSON should have newlines and indentation
        assert "\n" in content

    def test_export_to_json_compact(self, service, tmp_path):
        """Test JSON export without pretty formatting."""
        data = [{"name": "Test"}]
        file_path = tmp_path / "compact.json"

        result = service.export_to_json(data, file_path, pretty=False)

        assert result.success is True
        content = file_path.read_text(encoding='utf-8')
        # Compact JSON is single line
        assert "\n" not in content.strip()

    def test_export_to_json_empty_data(self, service, tmp_path):
        """Test JSON export with empty data."""
        file_path = tmp_path / "empty.json"

        result = service.export_to_json([], file_path)

        assert result.success is True
        assert result.record_count == 0

    def test_export_to_json_with_datetime(self, service, tmp_path):
        """Test JSON export with datetime objects."""
        now = datetime.now()
        data = [{"date": now, "value": 100}]
        file_path = tmp_path / "datetime.json"

        result = service.export_to_json(data, file_path)

        assert result.success is True
        # datetime should be converted to string
        content = json.loads(file_path.read_text(encoding='utf-8'))
        assert isinstance(content[0]["date"], str)

    def test_export_to_json_error(self, service):
        """Test JSON export with invalid path."""
        data = [{"name": "Test"}]
        invalid_path = Path("/nonexistent/directory/test.json")

        result = service.export_to_json(data, invalid_path)

        assert result.success is False
        assert result.error is not None


class TestExportToCsv:
    """Tests for CSV export."""

    def test_export_to_csv_success(self, service, tmp_path):
        """Test successful CSV export."""
        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200},
        ]
        file_path = tmp_path / "test.csv"

        result = service.export_to_csv(data, file_path)

        assert result.success is True
        assert result.record_count == 2
        assert file_path.exists()

        # Verify content
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "Item 1"

    def test_export_to_csv_with_columns(self, service, tmp_path):
        """Test CSV export with specific columns."""
        data = [
            {"name": "Test", "value": 100, "extra": "ignored"},
        ]
        file_path = tmp_path / "columns.csv"

        result = service.export_to_csv(data, file_path, columns=["name", "value"])

        assert result.success is True
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "extra" not in content

    def test_export_to_csv_empty_data(self, service, tmp_path):
        """Test CSV export with empty data."""
        file_path = tmp_path / "empty.csv"

        result = service.export_to_csv([], file_path)

        assert result.success is True
        assert result.record_count == 0

    def test_export_to_csv_error(self, service):
        """Test CSV export with invalid path."""
        data = [{"name": "Test"}]
        invalid_path = Path("/nonexistent/directory/test.csv")

        result = service.export_to_csv(data, invalid_path)

        assert result.success is False


class TestGetExportableData:
    """Tests for data retrieval methods."""

    def test_get_exportable_sales(self, service, mock_db):
        """Test getting sales data."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",), ("sale_price",)]
        mock_cursor.fetchall.return_value = [
            (1, "Item 1", 100.0),
            (2, "Item 2", 200.0),
        ]
        mock_db.conn.execute.return_value = mock_cursor

        data = service.get_exportable_sales()

        assert len(data) == 2
        assert data[0]["item_name"] == "Item 1"

    def test_get_exportable_sales_with_days(self, service, mock_db):
        """Test getting sales with date filter."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",)]
        mock_cursor.fetchall.return_value = []
        mock_db.conn.execute.return_value = mock_cursor

        service.get_exportable_sales(days=7)

        # Check that query includes date filter
        call_args = mock_db.conn.execute.call_args
        query = call_args[0][0]
        assert "WHERE sold_at >=" in query

    def test_get_exportable_sales_no_db(self, service_no_db):
        """Test getting sales without database."""
        data = service_no_db.get_exportable_sales()
        assert data == []

    def test_get_exportable_price_checks(self, service, mock_db):
        """Test getting price check data."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",), ("price_chaos",)]
        mock_cursor.fetchall.return_value = [
            (1, "Item", 50.0),
        ]
        mock_db.conn.execute.return_value = mock_cursor

        data = service.get_exportable_price_checks()

        assert len(data) == 1

    def test_get_exportable_price_checks_no_db(self, service_no_db):
        """Test getting price checks without database."""
        data = service_no_db.get_exportable_price_checks()
        assert data == []

    def test_get_exportable_loot_session(self, service, mock_db):
        """Test getting loot session data."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",), ("chaos_value",)]
        mock_cursor.fetchall.return_value = [(1, "Item", 100.0)]
        mock_db.conn.execute.return_value = mock_cursor

        data = service.get_exportable_loot_session(session_id=1)

        assert len(data) == 1

    def test_get_exportable_loot_session_no_db(self, service_no_db):
        """Test getting loot session without database."""
        data = service_no_db.get_exportable_loot_session()
        assert data == []

    def test_get_exportable_sales_error(self, service, mock_db):
        """Test error handling in get_exportable_sales."""
        mock_db.conn.execute.side_effect = Exception("Database error")

        data = service.get_exportable_sales()

        assert data == []


class TestExportData:
    """Tests for high-level export_data method."""

    def test_export_data_sales_json(self, service, mock_db, tmp_path):
        """Test exporting sales as JSON."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",)]
        mock_cursor.fetchall.return_value = [(1, "Item")]
        mock_db.conn.execute.return_value = mock_cursor

        file_path = tmp_path / "sales.json"
        result = service.export_data("sales", "json", file_path)

        assert result.success is True

    def test_export_data_price_checks_csv(self, service, mock_db, tmp_path):
        """Test exporting price checks as CSV."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",), ("item_name",)]
        mock_cursor.fetchall.return_value = [(1, "Item")]
        mock_db.conn.execute.return_value = mock_cursor

        file_path = tmp_path / "checks.csv"
        result = service.export_data("price_checks", "csv", file_path)

        assert result.success is True

    def test_export_data_unknown_type(self, service, tmp_path):
        """Test exporting unknown data type."""
        file_path = tmp_path / "unknown.json"
        result = service.export_data("unknown", "json", file_path)

        assert result.success is False
        assert "Unknown data type" in result.error

    def test_export_data_unknown_format(self, service, mock_db, tmp_path):
        """Test exporting to unknown format."""
        mock_cursor = Mock()
        mock_cursor.description = [("id",)]
        mock_cursor.fetchall.return_value = []
        mock_db.conn.execute.return_value = mock_cursor

        file_path = tmp_path / "test.xml"
        result = service.export_data("sales", "xml", file_path)

        assert result.success is False
        assert "Unknown format" in result.error
