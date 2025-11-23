"""
Tests for logging setup module.
Currently has 0% coverage - these tests provide basic coverage.
"""
from __future__ import annotations

import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.logging_setup import setup_logging

pytestmark = pytest.mark.unit


def test_setup_logging_creates_log_directory(tmp_path):
    """setup_logging should create log directory if it doesn't exist"""
    # Patch Path.home() to use tmp_path
    with patch('core.logging_setup.Path.home', return_value=tmp_path):
        setup_logging()

    log_dir = tmp_path / ".poe_price_checker"
    log_file = log_dir / "app.log"

    assert log_dir.exists()
    assert log_file.exists()


def test_setup_logging_sets_root_logger_level():
    """setup_logging should configure root logger with appropriate level"""
    with patch('core.logging_setup.Path.home') as mock_home:
        mock_home.return_value = Path("/tmp")
        
        setup_logging(debug=True)

        root_logger = logging.getLogger()
        # Should be set to DEBUG when debug=True
        assert root_logger.level == logging.DEBUG


def test_setup_logging_adds_file_and_console_handlers(tmp_path):
    """setup_logging should add both file and console handlers"""
    with patch('core.logging_setup.Path.home', return_value=tmp_path):
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging()

        # Should have added 2 handlers (file + console)
        assert len(root_logger.handlers) == 2


def test_setup_logging_uses_default_log_file_location(tmp_path):
    """setup_logging should use default log file location"""
    with patch('core.logging_setup.Path.home', return_value=tmp_path):
        setup_logging()
        
        # Should have created log file in default location
        expected_path = tmp_path / ".poe_price_checker" / "app.log"
        assert expected_path.exists()


def test_setup_logging_can_be_called_multiple_times_safely(tmp_path):
    """Calling setup_logging multiple times should not crash"""
    with patch('core.logging_setup.Path.home', return_value=tmp_path):
        # Should not raise
        setup_logging()
        setup_logging()
        setup_logging()

        # Should still have exactly 2 handlers (old ones removed)
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 2
