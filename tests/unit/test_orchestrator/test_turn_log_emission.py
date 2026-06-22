"""The engine emits the structured per-turn comms log during a run (E10/E6)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from cosmos77_ex06.orchestrator.local import build_engine
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory


def _survive(prompt: str) -> _FakeResponse:
    role = "cop" if "You are the COP" in prompt else "thief"
    msg = "Holding the walls." if role == "cop" else "Drifting west, watching you."
    return _FakeResponse(msg, "apply_move", {"direction": "STAY"})


@pytest.mark.asyncio
async def test_turn_emits_log_with_url_and_nl_message(
    orch_config: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    gk = Gatekeeper(tmp_path / "results")
    engine, clients = build_engine(orch_config, gk, make_client_factory(_survive))
    with caplog.at_level(logging.INFO, logger="cosmos77_ex06.orchestrator.turn"):
        async with clients["cop"], clients["thief"]:
            await engine.play_sub_game(1)
    text = "\n".join(r.getMessage() for r in caplog.records)
    # The MCP server URL and a genuine NL message are both present (E10 proof).
    assert "localhost:8002/mcp" in text or "localhost:8001/mcp" in text
    assert "Drifting west" in text or "Holding the walls" in text
    assert "apply_move" in text


@pytest.mark.asyncio
async def test_gui_true_is_headless_safe_and_unchanged(
    orch_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gui=True attaches a headless viewer (no display) without changing the result."""
    monkeypatch.setenv("GUI_HEADLESS", "1")  # force the no-display probe (cross-platform)
    gk = Gatekeeper(tmp_path / "results")
    plain, c1 = build_engine(orch_config, gk, make_client_factory(_survive))
    gui, c2 = build_engine(orch_config, gk, make_client_factory(_survive), gui=True)
    assert gui.on_turn is not None and plain.on_turn is None
    async with c1["cop"], c1["thief"]:
        a = await plain.play_sub_game(1)
    async with c2["cop"], c2["thief"]:
        b = await gui.play_sub_game(1)
    # Same scores + move count with the GUI on (headless) as off (E5/E10).
    assert a.scores == b.scores and a.move_count == b.move_count
