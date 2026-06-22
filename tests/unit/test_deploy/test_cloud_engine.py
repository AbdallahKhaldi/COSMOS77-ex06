"""End-to-end cloud engine over TWO separate-state servers, no LLM (E5/E6).

Wires the CLOUD builder to two in-process FastMCP apps that each hold their OWN
:class:`GameState` (the cloud topology), injecting a deterministic STAY-decision
"gemini" so no network is touched. Drives a full game and asserts the two servers'
ground truth stays consistent the whole way through (the engine's per-turn reconcile
mirrors the canonical board). This is the LLM-free proof that --cloud is correct.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.mcp_servers.state_factory import make_state
from cosmos77_ex06.orchestrator import cloud
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_STAY_JSON = '{"message": "holding position", "action": {"type": "move", "direction": "STAY"}}'


class _StubResp:
    """A genai response stand-in carrying a fixed STAY decision."""

    text = _STAY_JSON
    usage_metadata = None


class _StubModels:
    """The ``aio.models`` surface — its async generate returns the STAY response."""

    async def generate_content(self, **_kw: Any) -> _StubResp:
        """Return a deterministic STAY decision (no network)."""
        return _StubResp()


class _StubAio:
    """The ``aio`` namespace exposing ``models``."""

    models = _StubModels()


class _StubGemini:
    """A genai client stand-in whose ``aio.models.generate_content`` is deterministic."""

    aio = _StubAio()


async def test_cloud_engine_keeps_two_states_consistent(cloud_config, tmp_path) -> None:
    """A full short cloud game keeps both separate-state servers in lockstep (E6)."""
    cloud_config._data["num_games"] = 1  # noqa: SLF001 - one short sub-game is enough
    cloud_config._data["max_moves"] = 3  # noqa: SLF001
    cop_mcp = build_server("cop", make_state(cloud_config), cloud_config)
    thief_mcp = build_server("thief", make_state(cloud_config), cloud_config)
    servers = {"cop": cop_mcp, "thief": thief_mcp}

    def _client_factory(url: str, auth: Any) -> Client:
        role = "cop" if "cop" in url else "thief"
        return Client(servers[role])

    gk = Gatekeeper(tmp_path)
    out = await cloud.run_cloud_game(
        cloud_config, gk, genai_factory=lambda _key: _StubGemini(), client_factory=_client_factory
    )
    assert out["totals"]["thief"] >= 0  # the game completed end-to-end

    # After the game, both servers' canonical boards must be identical (consistent).
    async with Client(cop_mcp) as cc, Client(thief_mcp) as tc:
        cop_truth = (await cc.call_tool("get_full_state", {})).data
        thief_truth = (await tc.call_tool("get_full_state", {})).data
    assert cop_truth == thief_truth


async def test_runner_cloud_branch_builds_full_report(cloud_config, tmp_path) -> None:
    """runner.run_full_game(cloud=True) drives the cloud builder + validates the report (E6)."""
    from cosmos77_ex06.orchestrator import runner

    cloud_config._data["num_games"] = 1  # noqa: SLF001
    cloud_config._data["max_moves"] = 2  # noqa: SLF001
    cop_mcp = build_server("cop", make_state(cloud_config), cloud_config)
    thief_mcp = build_server("thief", make_state(cloud_config), cloud_config)
    servers = {"cop": cop_mcp, "thief": thief_mcp}
    gk = Gatekeeper(tmp_path)
    out = await runner.run_full_game(
        cloud_config,
        gk,
        lambda _key: _StubGemini(),
        cloud=True,
        mcp_client_factory=lambda url, auth: Client(servers["cop" if "cop" in url else "thief"]),
    )
    assert out["report"]["cop_mcp_url"] == "https://cosmos-cop.fastmcp.app/mcp"
    assert len(out["report"]["sub_games"]) == 1
