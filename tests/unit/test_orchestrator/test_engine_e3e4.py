"""E3 separation + E4 relay/routing tests for the orchestrator."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cosmos77_ex06.orchestrator.local import build_engine
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory


def _gk(tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(tmp_path / "results")


def _survive(prompt: str) -> _FakeResponse:
    msg = (
        "Holding near the walls."
        if "You are the COP" in prompt
        else "Drifting along the western wall."
    )
    return _FakeResponse(msg, "apply_move", {"direction": "STAY"})


def test_servers_import_no_llm() -> None:
    """E3 static check: no LLM library is imported anywhere under mcp_servers/."""
    root = Path("src/cosmos77_ex06/mcp_servers")
    pattern = re.compile(r"\b(genai|google\.genai|gemini|anthropic|openai)\b", re.IGNORECASE)
    for path in root.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert not pattern.search(line), f"LLM import in {path}: {line!r}"


@pytest.mark.asyncio
async def test_engine_relays_opponent_message_into_prompt(
    orch_config: Config, tmp_path: Path
) -> None:
    """The ENGINE relays the opponent's last NL message into the active prompt (E4)."""
    seen: list[str] = []

    def spy(prompt: str) -> _FakeResponse:
        seen.append(prompt)
        return _survive(prompt)

    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(spy))
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)
    cop_prompts = [p for p in seen if "You are the COP" in p]
    assert any("western wall" in p for p in cop_prompts)


@pytest.mark.asyncio
async def test_cop_barrier_action_is_routed(orch_config: Config, tmp_path: Path) -> None:
    """A cop that proposes place_barrier has it routed + recorded as a barrier tool."""

    def script(prompt: str) -> _FakeResponse:
        if "You are the COP" in prompt:
            return _FakeResponse("Walling off the center.", "place_barrier", {"x": 1, "y": 0})
        return _FakeResponse("Edging around.", "apply_move", {"direction": "STAY"})

    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(script))
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)
    entries = engine.transcript.to_list()
    assert "place_barrier" in [e["tool"] for e in entries if e["role"] == "cop"]
    assert any(b == [1, 0] for e in entries for b in e["board"]["barriers"])


@pytest.mark.asyncio
async def test_coordinate_leak_is_flagged_in_transcript(
    orch_config: Config, tmp_path: Path
) -> None:
    """A coordinate-leaking outgoing message is flagged in the transcript (E4 guard)."""

    def leaky(prompt: str) -> _FakeResponse:
        msg = "Cornering you at (1,1)." if "You are the COP" in prompt else "Hiding near the wall."
        return _FakeResponse(msg, "apply_move", {"direction": "STAY"})

    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(leaky))
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)
    entries = engine.transcript.to_list()
    cop_flags = [e["coord_flagged"] for e in entries if e["role"] == "cop"]
    thief_flags = [e["coord_flagged"] for e in entries if e["role"] == "thief"]
    assert all(cop_flags) and cop_flags, "coordinate leak not flagged"
    assert not any(thief_flags), "clean prose wrongly flagged"


@pytest.mark.asyncio
async def test_unknown_direction_defaults_to_stay(orch_config: Config, tmp_path: Path) -> None:
    """An invalid/garbled tool proposal is normalized to a safe STAY (no crash)."""

    def script(_p: str) -> _FakeResponse:
        return _FakeResponse("mumbling", "teleport", {"direction": "SIDEWAYS"})

    engine, clients = build_engine(orch_config, _gk(tmp_path), make_client_factory(script))
    async with clients["cop"], clients["thief"]:
        sub = await engine.play_sub_game(1)
    assert sub.winner == "thief"
    assert all(e["args"].get("direction") == "STAY" for e in engine.transcript.to_list())
