"""E4 message relay is process-independent: it does NOT need a shared GameState.

The reviewer's cloud-safety concern: with the two servers as separate processes,
each holds its OWN divergent ``GameState``, so a server-side message bus
(``send_message`` / ``receive_messages``) would land in different message lists.
This test wires the engine to two servers that DO NOT share a ``GameState`` and
asserts the opponent's NL message still reaches the active agent's prompt — proving
the engine-held :class:`Transcript` is the authoritative, process-independent relay.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.mcp_servers.state_factory import make_state
from cosmos77_ex06.orchestrator.engine import GameEngine
from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory


def _gk(tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(tmp_path / "results")


@pytest.mark.asyncio
async def test_message_relay_no_shared_state(orch_config: Config, tmp_path: Path) -> None:
    """Opponent message reaches the active agent without the servers sharing state."""
    seen: list[str] = []

    def spy(prompt: str) -> _FakeResponse:
        seen.append(prompt)
        msg = (
            "Holding near the walls."
            if "You are the COP" in prompt
            else "Drifting along the western wall."
        )
        return _FakeResponse(msg, "apply_move", {"direction": "STAY"})

    # Two SEPARATE GameState objects — the servers do NOT share memory.
    cop_state = make_state(orch_config)
    thief_state = make_state(orch_config)
    assert cop_state is not thief_state
    cop_server = build_server("cop", cop_state, orch_config)
    thief_server = build_server("thief", thief_state, orch_config)
    clients = {"cop": Client(cop_server), "thief": Client(thief_server)}

    factory = make_client_factory(spy)
    gemini = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    # The engine keeps its own canonical state; servers stay independent of it.
    engine = GameEngine(orch_config, clients, gemini, state=cop_state)
    async with clients["cop"], clients["thief"]:
        await engine.play_sub_game(1)

    cop_prompts = [p for p in seen if "You are the COP" in p]
    # The thief's NL line was relayed into the cop's prompt via the engine transcript,
    # not via any shared server-side message list.
    assert any("western wall" in p for p in cop_prompts)
    for state in (cop_state, thief_state):
        assert not state.messages, "relay must not depend on server-side message storage"
