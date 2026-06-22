"""GameEngine loop tests — mocked LLM + REAL in-memory MCP servers (E3, E4, E5)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from cosmos77_ex06.orchestrator.local import build_engine, run_local_game
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory

_COORD_RE = re.compile(r"\d+\s*[,;]\s*\d+|\brow\s*\d|\bcol\s*\d|\[\d+\s*,\s*\d+\]")


def _capture_script(prompt: str) -> _FakeResponse:
    """Cop drives NW toward the corner to capture; thief stays put."""
    if "You are the COP" in prompt:
        return _FakeResponse(
            "I'm closing on the corner, nowhere to run.", "apply_move", {"direction": "NW"}
        )
    return _FakeResponse(
        "All quiet, I'm holding near the start.", "apply_move", {"direction": "STAY"}
    )


def _survive_script(prompt: str) -> _FakeResponse:
    """Both agents stay; the thief survives to the move limit (thief_win)."""
    role = "cop" if "You are the COP" in prompt else "thief"
    msg = (
        "Holding position, watching the walls."
        if role == "cop"
        else "Drifting along the western wall."
    )
    return _FakeResponse(msg, "apply_move", {"direction": "STAY"})


def _gk(tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(tmp_path / "results")


@pytest.mark.asyncio
async def test_engine_runs_n_subgames_with_free_language(
    orch_config: Config, tmp_path: Path
) -> None:
    result = await run_local_game(orch_config, _gk(tmp_path), make_client_factory(_survive_script))
    assert len(result["sub_games"]) == orch_config.get("num_games")
    # E4: a free-language message every turn, never numeric coordinates.
    assert result["messages"], "no messages exchanged"
    for msg in result["messages"]:
        assert msg.strip(), "empty message field"
        assert not _COORD_RE.search(msg), f"numeric-coordinate leak: {msg!r}"


@pytest.mark.asyncio
async def test_mocked_capture_ends_subgame(orch_config: Config, tmp_path: Path) -> None:
    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(_capture_script))
    async with clients["cop"], clients["thief"]:
        sub = await engine.play_sub_game(1)
    assert sub.winner == "cop"
    assert sub.scores == {"cop": 20, "thief": 5}
    assert sub.move_count < orch_config.get("max_moves")  # ended early on capture


@pytest.mark.asyncio
async def test_survival_to_move_limit_is_thief_win(orch_config: Config, tmp_path: Path) -> None:
    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(_survive_script))
    async with clients["cop"], clients["thief"]:
        sub = await engine.play_sub_game(1)
    assert sub.winner == "thief"
    assert sub.scores == {"cop": 5, "thief": 10}
    assert sub.move_count == orch_config.get("max_moves")


@pytest.mark.asyncio
async def test_llm_called_by_engine_not_by_server(orch_config: Config, tmp_path: Path) -> None:
    factory = make_client_factory(_survive_script)
    engine, clients = build_engine(orch_config, _gk(tmp_path), factory)
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)
    # The engine drove every generate_content call (E3): the count is non-zero and
    # equals turns * roles for a full survival sub-game.
    fake = factory.fake  # type: ignore[attr-defined]
    assert fake.aio.models.calls, "engine never invoked the LLM"
    assert len(fake.aio.models.calls) == orch_config.get("max_moves") * 2


@pytest.mark.asyncio
async def test_transcript_is_complete(orch_config: Config, tmp_path: Path) -> None:
    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(_survive_script))
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)
    entries: list[dict[str, Any]] = engine.transcript.to_list()
    assert entries
    for e in entries:
        assert e["role"] in ("cop", "thief")
        assert e["nl_message"].strip()
        assert e["tool"] in ("apply_move", "place_barrier")
        assert "direction" in e["args"] or "x" in e["args"]
        assert {"cop", "thief", "barriers", "move"} <= set(e["board"])
        assert e["mcp_url"].startswith("http")
        assert e["coord_flagged"] is False  # survival script speaks clean prose (E4)
        assert "credibility" in e["estimate"]  # belief recorded per turn (E4/E11)


@pytest.mark.asyncio
async def test_gatekeeper_records_llm_calls(orch_config: Config, tmp_path: Path) -> None:
    gk = _gk(tmp_path)
    await run_local_game(orch_config, gk, make_client_factory(_survive_script))
    assert gk.read("llm_cop")["calls"] > 0
    assert gk.read("llm_thief")["calls"] > 0
