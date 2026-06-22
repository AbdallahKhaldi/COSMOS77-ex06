"""Deterministic config builders for the game state-machine tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from cosmos77_ex06.shared.config import Config

_BASE: dict[str, Any] = {
    "version": "1.00",
    "grid_size": [5, 5],
    "max_moves": 25,
    "num_games": 6,
    "max_barriers": 5,
    "allow_diagonal": True,
    "turn_order": ["thief", "cop"],
    "scoring": {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5},
    "paths": {"results": "results", "reports": "reports", "assets": "assets"},
}


@pytest.fixture
def make_config(tmp_path: Path):
    """Return a factory building a :class:`Config` with the given overrides."""

    counter = {"n": 0}

    def _make(**overrides: Any) -> Config:
        data = {**_BASE, **overrides}
        counter["n"] += 1
        cfg = tmp_path / f"config_{counter['n']}"
        cfg.mkdir()
        (cfg / "config.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        return Config(cfg)

    return _make
