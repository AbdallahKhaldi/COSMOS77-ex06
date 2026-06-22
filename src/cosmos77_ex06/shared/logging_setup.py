"""Initialise logging from ``config/logging_config.json`` (rule 13 support).

Applies the dictConfig, ensuring any file handler's target directory exists
first. The project logs under the ``cosmos77_ex06`` namespace.
"""

from __future__ import annotations

import json
import logging
import logging.config
from pathlib import Path

_DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "config" / "logging_config.json"


def init_logging(config_path: Path | str | None = None) -> None:
    """Apply the dictConfig found at ``config_path`` (defaults to the repo config)."""
    path = Path(config_path) if config_path is not None else _DEFAULT_CONFIG
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    _ensure_handler_dirs(payload)
    logging.config.dictConfig(payload)


def get_logger(name: str = "cosmos77_ex06") -> logging.Logger:
    """Return a logger under the project's ``cosmos77_ex06.*`` namespace."""
    return logging.getLogger(name)


def _ensure_handler_dirs(payload: dict) -> None:
    """Create parent dirs for any handler that writes to a file or directory."""
    for handler in payload.get("handlers", {}).values():
        filename = handler.get("filename")
        if filename:
            Path(filename).expanduser().parent.mkdir(parents=True, exist_ok=True)
        directory = handler.get("directory")
        if directory:
            Path(directory).expanduser().mkdir(parents=True, exist_ok=True)
