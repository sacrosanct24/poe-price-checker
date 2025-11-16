# core/logging_setup.py
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(debug: bool = False) -> None:
    """
    Configure application-wide logging.

    - Logs to ~/.poe_price_checker/app.log (rotating, max ~1 MB, 3 backups)
    - Also logs to console (stderr) for interactive runs
    """
    log_dir = Path.home() / ".poe_price_checker"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    level = logging.DEBUG if debug else logging.INFO

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers (useful if re-running in dev/REPL)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,  # ~1 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    file_handler.setFormatter(file_fmt)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    # Console handler (simple readable format)
    console_handler = logging.StreamHandler()
    console_fmt = logging.Formatter("[%(levelname)s] %(name)s - %(message)s")
    console_handler.setFormatter(console_fmt)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    root_logger.info("Logging initialized")
    root_logger.info(f"Log file: {log_file}")
