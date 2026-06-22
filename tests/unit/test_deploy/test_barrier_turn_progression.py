"""Regression: a cop BARRIER turn must advance the turn across two cloud states (E6).

This is the exact divergence/deadlock the review flagged. ``place_barrier`` never
touches ``current_role`` / ``move_number`` server-side, so after a thief-move +
cop-barrier full move the turn would stall and the thief would be locked out. The
fix makes the ENGINE own turn-progression inside :meth:`ClientStateSync.reconcile`
and push the merged state to BOTH servers. These tests drive that path directly —
no Gemini, no network beyond in-memory FastMCP clients — over TWO DISTINCT states.
"""

from __future__ import annotations

import itertools
from typing import Any

from fastmcp import Client

from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.mcp_servers.state_factory import make_state as make_default_state
from cosmos77_ex06.orchestrator import cloud
from cosmos77_ex06.orchestrator.sync import ClientStateSync
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_THIEF_STAY = '{"message": "holding", "action": {"type": "move", "direction": "STAY"}}'


class _RoleResp:
    """A genai response stand-in carrying a per-role decision (thief STAYs, cop barriers)."""

    def __init__(self, text: str) -> None:
        self.text, self.usage_metadata = text, None


def _barrier_text(x: int, y: int) -> str:
    """The cop's JSON decision dropping a barrier at ``(x, y)``."""
    return f'{{"message": "wall", "action": {{"type": "barrier", "x": {x}, "y": {y}}}}}'


class _Models:
    """The ``aio.models`` surface: cop -> fresh barrier, thief -> STAY (no network)."""

    def __init__(self) -> None:
        self._cells = itertools.cycle([(0, 4), (1, 4), (2, 4), (3, 4), (4, 0)])

    async def generate_content(self, *, contents: str = "", **_kw: Any) -> _RoleResp:
        """Return a role-conditional decision parsed from the prompt text."""
        if "YOU ARE THE COP" in contents.upper():
            return _RoleResp(_barrier_text(*next(self._cells)))
        return _RoleResp(_THIEF_STAY)


class _Aio:
    """The ``aio`` namespace exposing a fresh ``models`` surface."""

    def __init__(self) -> None:
        self.models = _Models()


class _RoleGemini:
    """A genai client stand-in whose ``aio.models`` drives the cop-barrier scenario."""

    def __init__(self) -> None:
        self.aio = _Aio()


async def _full_state(client: Client) -> dict[str, Any]:
    """Return a server's full canonical ground truth via ``get_full_state``."""
    return (await client.call_tool("get_full_state", {})).data


async def test_cop_barrier_turn_advances_move_and_unblocks_thief(make_state, cloud_config) -> None:
    """thief-move then cop-BARRIER advances move_number and lets the thief move again.

    Two SEPARATE GameStates (two cloud processes). We reconcile after each turn, just
    like the engine. After the cop places a barrier (which advances NOTHING on its
    own server), the engine-owned reconcile must bump ``move_number`` to 1 and set
    ``current_role`` back to ``thief`` on BOTH servers — otherwise the next thief
    ``apply_move`` is rejected ("not your turn") and the game deadlocks.
    """
    cop_state = make_state(cop=(4, 4), thief=(0, 0))
    thief_state = make_state(cop=(4, 4), thief=(0, 0))
    cop_mcp = build_server("cop", cop_state, cloud_config)
    thief_mcp = build_server("thief", thief_state, cloud_config)
    async with Client(cop_mcp) as cc, Client(thief_mcp) as tc:
        sync = ClientStateSync({"cop": cc, "thief": tc})
        engine_state = make_state(cop=(4, 4), thief=(0, 0))
        await sync.push(engine_state)  # sub-game reset: both servers current_role=thief

        # --- Move 0: thief moves, cop places a barrier (no server turn advance) ---
        moved = await tc.call_tool("apply_move", {"role": "thief", "direction": "SE"})
        assert moved.data["ok"] is True  # thief acted on its turn
        await sync.reconcile(engine_state, "thief")
        assert engine_state.current_role == "cop"  # engine handed the turn to the cop

        barrier = await cc.call_tool("place_barrier", {"role": "cop", "x": 2, "y": 2})
        assert barrier.data["ok"] is True  # cop legally placed a barrier on its turn
        await sync.reconcile(engine_state, "cop")

        # The engine OWNS progression: a barrier turn still advances the full move.
        assert engine_state.move_number == 1
        assert engine_state.current_role == "thief"
        cop_truth = await _full_state(cc)
        thief_truth = await _full_state(tc)
        assert cop_truth == thief_truth  # both processes share one canonical board
        assert cop_truth["move_number"] == 1  # the bump reached BOTH servers
        assert cop_truth["current_role"] == "thief"
        assert cop_truth["barriers"] == [[2, 2]]  # the cop's barrier mirrored to the thief

        # --- Move 1: the thief is NOT deadlocked — its server accepts the move ---
        # (E direction avoids the cop's new barrier at (2,2); the thief is at (1,1).)
        again = await tc.call_tool("apply_move", {"role": "thief", "direction": "E"})
        assert again.data["ok"] is True  # would be "not your turn" without the fix
        assert again.data["reason"] is None  # accepted, not a turn-order rejection


async def test_cloud_engine_with_cop_barriers_advances_and_stays_consistent(
    cloud_config, tmp_path
) -> None:
    """Full cloud game where the cop places barriers each move (the E6 deadlock case).

    Drives the real :class:`GameEngine` over two separate-state servers via the cloud
    builder, no-LLM stub: the COP places a barrier and the THIEF STAYs every turn.
    Without the fix the cop-barrier full move never advances ``move_number`` and the
    thief deadlocks; here the engine-owned reconcile advances the turn to the limit.
    """
    cloud_config._data["num_games"] = 1  # noqa: SLF001
    cloud_config._data["max_moves"] = 3  # noqa: SLF001
    cop_mcp = build_server("cop", make_default_state(cloud_config), cloud_config)
    thief_mcp = build_server("thief", make_default_state(cloud_config), cloud_config)
    servers = {"cop": cop_mcp, "thief": thief_mcp}
    gk = Gatekeeper(tmp_path)
    out = await cloud.run_cloud_game(
        cloud_config,
        gk,
        genai_factory=lambda _key: _RoleGemini(),
        client_factory=lambda url, auth: Client(servers["cop" if "cop" in url else "thief"]),
    )
    assert out["sub_games"][0]["moves"] == 3  # move_number reached the limit (no deadlock)
    async with Client(cop_mcp) as cc, Client(thief_mcp) as tc:
        cop_truth = (await cc.call_tool("get_full_state", {})).data
        thief_truth = (await tc.call_tool("get_full_state", {})).data
    assert cop_truth == thief_truth  # both separate-process boards stayed consistent
    assert cop_truth["move_number"] == 3 and len(cop_truth["barriers"]) >= 1  # advanced + placed
