"""Shared pytest fixtures and deterministic-seed setup (CLAUDE.md rule 17)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
import yaml

_CONFIG = {
    "version": "1.00",
    "grid_size": [5, 5],
    "max_moves": 25,
    "num_games": 6,
    "max_barriers": 5,
    "allow_diagonal": True,
    "turn_order": ["thief", "cop"],
    "scoring": {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5},
    "llm": {"provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.2},
    "mcp": {
        "cop_url": "http://localhost:8001/mcp",
        "thief_url": "http://localhost:8002/mcp",
        "cop_port": 8001,
        "thief_port": 8002,
    },
    "report": {"to": "rmisegal+uoh26b@gmail.com", "timezone": "Asia/Jerusalem"},
    "group": {"name": "COSMOS77", "github_repo": "https://github.com/AbdallahKhaldi/COSMOS77-ex06"},
    "paths": {"results": "results", "reports": "reports", "assets": "assets"},
}


@pytest.fixture(autouse=True)
def _seed_random() -> None:
    """Seed `random` before every test so nothing flakes."""
    random.seed(1729)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A throwaway ``config/`` dir holding a valid HW6 ``config.yaml``."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text(yaml.safe_dump(_CONFIG), encoding="utf-8")
    return cfg


@pytest.fixture
def config(config_dir: Path):
    """A :class:`Config` loaded from the throwaway config dir."""
    from cosmos77_ex06.shared.config import Config

    return Config(config_dir)
