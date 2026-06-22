"""Tests for logging initialisation (rule 13 support)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cosmos77_ex06.shared.logging_setup import get_logger, init_logging

_PAYLOAD = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": "PLACEHOLDER",
        },
    },
    "loggers": {"cosmos77_ex06": {"level": "DEBUG", "handlers": ["console", "rotating_file"]}},
}


def test_get_logger_default_namespace() -> None:
    assert get_logger().name == "cosmos77_ex06"


def test_get_logger_custom_namespace() -> None:
    assert get_logger("cosmos77_ex06.game").name == "cosmos77_ex06.game"


def test_init_logging_creates_handler_dir(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "run.log"
    payload = json.loads(json.dumps(_PAYLOAD))
    payload["handlers"]["rotating_file"]["filename"] = str(log_path)
    cfg_path = tmp_path / "logging_config.json"
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")
    init_logging(cfg_path)
    assert log_path.parent.exists()
    logging.getLogger("cosmos77_ex06").info("hello")
