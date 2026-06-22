"""Fixtures for the Phase 8 deploy suite — HTTPS cloud config, fake tokens, no network."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.shared.config import Config

ORCH_TOKEN = "test-orch-token"  # noqa: S105 - fake test token, not a secret
COP_TOKEN = "test-cop-token"  # noqa: S105
THIEF_TOKEN = "test-thief-token"  # noqa: S105

_CLOUD_CFG: dict[str, Any] = {
    "version": "1.00",
    "grid_size": [5, 5],
    "max_moves": 25,
    "num_games": 6,
    "max_barriers": 5,
    "allow_diagonal": True,
    "turn_order": ["thief", "cop"],
    "vision_radius": 1,
    "scoring": {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5},
    "llm": {"provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.2},
    "mcp": {
        "cop_url": "https://cosmos-cop.fastmcp.app/mcp",
        "thief_url": "https://cosmos-thief.fastmcp.app/mcp",
        "cop_port": 8001,
        "thief_port": 8002,
    },
    "report": {"to": "x@y.z", "timezone": "Asia/Jerusalem"},
    "group": {"name": "COSMOS77", "github_repo": "https://github.com/x/y"},
    "paths": {"results": "results", "reports": "reports", "assets": "assets"},
}


@pytest.fixture(autouse=True)
def _tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject fake MCP tokens so server + client construction needs no real secrets."""
    monkeypatch.setenv("COP_MCP_TOKEN", COP_TOKEN)
    monkeypatch.setenv("THIEF_MCP_TOKEN", THIEF_TOKEN)
    monkeypatch.setenv("ORCHESTRATOR_TOKEN", ORCH_TOKEN)


@pytest.fixture
def cloud_config(tmp_path: Path) -> Config:
    """A :class:`Config` whose MCP URLs are public HTTPS (the cloud target)."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text(yaml.safe_dump(_CLOUD_CFG), encoding="utf-8")
    return Config(cfg)


@pytest.fixture
def make_state(cloud_config: Config):
    """Factory: a fresh :class:`GameState` with given cop/thief positions (thief first)."""

    def _make(cop: tuple[int, int] = (4, 4), thief: tuple[int, int] = (0, 0)) -> GameState:
        return GameState(
            grid_size=list(cloud_config.get("grid_size")),
            cop_pos=cop,
            thief_pos=thief,
            max_moves=int(cloud_config.get("max_moves")),
            allow_diagonal=bool(cloud_config.get("allow_diagonal")),
            turn_order=list(cloud_config.get("turn_order")),
            current_role="thief",
        )

    return _make
