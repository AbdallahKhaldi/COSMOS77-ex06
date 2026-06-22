"""Fixtures for the bonus suite — a filled-in ``bonus`` config + a fake engine factory.

The whole inter-group series is mockable: :func:`run_series` accepts an
``engine_factory`` and a ``client_factory``, so no live cloud / MCP / LLM call ever
happens. The fake factory here records which cloud URLs each sub-game was wired to
(to assert the role swap) and returns an engine whose ``play_sub_game`` yields a
scripted :class:`SubGameResult`. The async ``Client``s are trivial async-context
stand-ins (the real ``async with clients[...]`` path is exercised, no network).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from cosmos77_ex06.game.state import GameState, SubGameResult
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_BONUS_CFG: dict[str, Any] = {
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
    "students": [
        {"id": "212389712", "name_en": "Abdallah Khaldi", "name_he": "עבדאללה"},
        {"id": "323118794", "name_en": "Tasneem Natour", "name_he": "תסנים"},
    ],
    "bonus": {
        "enabled": True,
        "group_1": "COSMOS77",
        "group_2": "PARTNER77",
        "github_repo_group_2": "https://github.com/Partner/partner-ex06",
        "students_group_2": [{"id": "999", "name": "Partner Student"}],
        "mcp": {
            "group_1_cop": "https://our-cop.example/mcp",
            "group_1_thief": "https://our-thief.example/mcp",
            "group_2_cop": "https://their-cop.example/mcp",
            "group_2_thief": "https://their-thief.example/mcp",
        },
        "engine_runner": "group_1",
        "claim": {"win": 10, "lose": 7, "tie": 5},
    },
    "paths": {"results": "results", "reports": "reports", "assets": "assets"},
}


@pytest.fixture
def bonus_config(tmp_path: Path) -> Config:
    """A :class:`Config` with a fully filled-in (enabled) ``bonus`` block."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    text = yaml.safe_dump(_BONUS_CFG, allow_unicode=True)
    (cfg / "config.yaml").write_text(text, encoding="utf-8")
    return Config(cfg)


@pytest.fixture
def gatekeeper(tmp_path: Path) -> Gatekeeper:
    """A throwaway gatekeeper writing under ``tmp_path/results``."""
    return Gatekeeper(tmp_path / "results")


class _FakeClient:
    """A trivial async-context client stand-in (no network)."""

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False


class _FakeEngine:
    """An engine whose ``play_sub_game`` returns a scripted result for ``index``."""

    def __init__(self, script: Callable[[int], SubGameResult]) -> None:
        self._script = script

    async def play_sub_game(self, index: int) -> SubGameResult:
        return self._script(index)


def _bare_state() -> GameState:
    return GameState(
        grid_size=[5, 5],
        cop_pos=(4, 4),
        thief_pos=(0, 0),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
    )


def make_engine_factory(
    script: Callable[[int], SubGameResult],
    wirings: list[dict[str, str]] | None = None,
) -> Callable[..., tuple[_FakeEngine, dict[str, _FakeClient]]]:
    """Build an ``engine_factory`` that records its (cop_url, thief_url) wiring per call."""

    def _factory(
        config: Config,
        gatekeeper: Gatekeeper,
        *,
        cop_url: str,
        thief_url: str,
        client_factory: Any = None,
    ) -> tuple[_FakeEngine, dict[str, _FakeClient]]:
        if wirings is not None:
            wirings.append({"cop_url": cop_url, "thief_url": thief_url})
        return _FakeEngine(script), {"cop": _FakeClient(), "thief": _FakeClient()}

    return _factory


def capture_result(scores: dict[str, int] | None = None, moves: int = 14) -> SubGameResult:
    """A cop-capture :class:`SubGameResult` (default 20/5)."""
    return SubGameResult(
        winner="cop",
        scores=scores or {"cop": 20, "thief": 5},
        move_count=moves,
        state=_bare_state(),
    )


def survival_result(scores: dict[str, int] | None = None, moves: int = 25) -> SubGameResult:
    """A thief-survival :class:`SubGameResult` (default 5/10)."""
    return SubGameResult(
        winner="thief",
        scores=scores or {"cop": 5, "thief": 10},
        move_count=moves,
        state=_bare_state(),
    )
