"""Logging configuration: console + rotating file handler."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(level: str, data_dir: Path) -> None:
    """Configure the root logger once.

    Console shows warnings and above (so the chat UI stays clean);
    the rotating file under ``data_dir/logs`` captures everything at
    the configured level.
    """
    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. in tests)
        return

    root.setLevel(getattr(logging, level, logging.INFO))

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    try:
        log_dir = data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "assistant.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)
    except OSError as exc:  # read-only filesystem, permissions, ...
        root.warning("File logging disabled: %s", exc)
