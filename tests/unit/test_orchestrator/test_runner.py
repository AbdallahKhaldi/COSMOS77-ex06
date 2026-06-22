"""Tests for the autonomous full-game runner (E5, E13): 6 valid sub-games + rerun."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from cosmos77_ex06.game.match import TechnicalLoss
from cosmos77_ex06.orchestrator import runner as runner_mod
from cosmos77_ex06.orchestrator.runner import run_full_game
from cosmos77_ex06.report.schema import validate_internal_game
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory


def _gk(tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(tmp_path / "results")


def _stay_factory() -> Any:
    """A genai factory whose every decision is a safe STAY move (deterministic)."""
    return make_client_factory(
        lambda _p: _FakeResponse("holding", "apply_move", {"direction": "STAY"})
    )


def _run(config: Config, tmp_path: Path, factory: Any) -> dict[str, Any]:
    return asyncio.run(run_full_game(config, _gk(tmp_path), factory))


def test_full_game_yields_exactly_num_games_valid_sub_games(
    orch_config: Config, tmp_path: Path
) -> None:
    """A clean run produces exactly ``num_games`` valid, contiguous sub-games."""
    out = _run(orch_config, tmp_path, _stay_factory())
    report = out["report"]
    num_games = int(orch_config.get("num_games"))
    assert len(report["sub_games"]) == num_games
    assert [s["index"] for s in report["sub_games"]] == list(range(1, num_games + 1))
    assert all("capture" in s for s in report["sub_games"])
    assert out["reruns"] == 0


def test_report_validates_against_schema_and_totals_sum(
    orch_config: Config, tmp_path: Path
) -> None:
    """The assembled report validates and ``totals`` equal the per-sub-game sums."""
    report = _run(orch_config, tmp_path, _stay_factory())["report"]
    validate_internal_game(report)  # raises on drift / totals mismatch
    cop = sum(s["cop_score"] for s in report["sub_games"])
    thief = sum(s["thief_score"] for s in report["sub_games"])
    assert report["totals"] == {"cop": cop, "thief": thief}


def test_report_has_exact_top_level_keys(orch_config: Config, tmp_path: Path) -> None:
    report = _run(orch_config, tmp_path, _stay_factory())["report"]
    assert set(report) == {
        "group_name",
        "students",
        "github_repo",
        "cop_mcp_url",
        "thief_mcp_url",
        "timezone",
        "sub_games",
        "totals",
    }
    assert report["students"] == [] or set(report["students"][0]) == {
        "id",
        "name_en",
        "name_he",
    }


def test_technical_loss_is_voided_and_reruns_to_reach_num_games(
    orch_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The FIRST sub-game attempt fails technically; the runner voids + re-runs it."""
    from cosmos77_ex06.orchestrator.engine import GameEngine

    real_play = GameEngine.play_sub_game
    state = {"failed": False}

    async def _flaky(self: GameEngine, index: int) -> Any:
        if not state["failed"]:
            state["failed"] = True
            raise TechnicalLoss("simulated transport failure")
        return await real_play(self, index)

    monkeypatch.setattr(GameEngine, "play_sub_game", _flaky)
    out = _run(orch_config, tmp_path, _stay_factory())
    num_games = int(orch_config.get("num_games"))
    assert len(out["report"]["sub_games"]) == num_games  # still exactly N valid
    assert out["reruns"] == 1  # one voided attempt was re-run
    assert [s["index"] for s in out["report"]["sub_games"]] == list(range(1, num_games + 1))


def test_result_flagged_technical_loss_is_voided_and_rerun(
    orch_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A RETURNED result flagged technical_loss (no exception) is voided + re-run."""
    from cosmos77_ex06.game.state import SubGameResult
    from cosmos77_ex06.orchestrator.engine import GameEngine

    real_play = GameEngine.play_sub_game
    state = {"voided": False}

    async def _flaky(self: GameEngine, index: int) -> Any:
        if not state["voided"]:
            state["voided"] = True
            return SubGameResult("technical_loss", {"cop": 0, "thief": 0}, 0, self.state, [], True)
        return await real_play(self, index)

    monkeypatch.setattr(GameEngine, "play_sub_game", _flaky)
    out = _run(orch_config, tmp_path, _stay_factory())
    num_games = int(orch_config.get("num_games"))
    assert len(out["report"]["sub_games"]) == num_games
    assert out["reruns"] == 1


def test_gives_up_after_too_many_technical_losses(
    orch_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If every attempt fails, the runner raises rather than emitting a short report."""
    from cosmos77_ex06.orchestrator.engine import GameEngine

    async def _always_fail(self: GameEngine, index: int) -> Any:
        raise TechnicalLoss("always down")

    monkeypatch.setattr(GameEngine, "play_sub_game", _always_fail)
    monkeypatch.setattr(runner_mod, "_MAX_ATTEMPTS_FACTOR", 1)
    with pytest.raises(TechnicalLoss, match="valid sub-games"):
        _run(orch_config, tmp_path, _stay_factory())
