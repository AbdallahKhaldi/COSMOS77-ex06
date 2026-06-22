"""Cloud state-sync proof — TWO independent server states stay consistent (E6).

This is the no-LLM proof that the Phase-8 fix closes the separate-process gap. Two
``build_server`` apps are wired to TWO DISTINCT :class:`GameState` objects (exactly
what two cloud processes' ``make_state`` would produce). We drive moves via direct
tool calls and reconcile through :class:`ClientStateSync`, then assert both servers'
``get_local_observation`` agree with the canonical board — AND show that without the
sync the two boards diverge. No Gemini is involved anywhere.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.orchestrator.sync import ClientStateSync


async def _obs(client: Client, role: str) -> dict[str, Any]:
    """Call ``get_local_observation`` through a client and return the redacted view."""
    res = await client.call_tool("get_local_observation", {"role": role})
    return res.data


def _opp_seen(obs: dict[str, Any], opp: str) -> tuple[int, int] | None:
    """Return the opponent's cell if the redacted view discloses it, else ``None``."""
    for cell in obs["visible_cells"]:
        if cell["occupant"] == opp:
            return (cell["x"], cell["y"])
    return None


async def test_sync_state_updates_obs_but_still_redacts(make_state, cloud_config) -> None:
    """sync_state sets the server's TRUTH; get_local_observation reflects it yet redacts.

    The cop server starts blind to a far thief. After the orchestrator mirrors a
    canonical board where the thief sits NEXT TO the cop, the cop's observation now
    discloses the thief (in-window) — but the payload still carries NO global
    ``thief_pos`` field (E4 partial observability holds; sync_state only set truth).
    """
    cop_state = make_state(cop=(2, 2), thief=(0, 0))
    cop_mcp = build_server("cop", cop_state, cloud_config)
    canonical = make_state(cop=(2, 2), thief=(2, 3)).to_dict()  # thief now adjacent
    async with Client(cop_mcp) as c:
        before = await _obs(c, "cop")
        await c.call_tool("sync_state", {"state": canonical})
        after = await _obs(c, "cop")
    assert "thief_pos" not in after and "thief" not in after  # never a global-truth field
    assert _opp_seen(before, "thief") is None  # was blind before
    assert _opp_seen(after, "thief") == (2, 3)  # now sees it (in-window only)


async def test_two_separate_states_stay_consistent_with_sync(make_state, cloud_config) -> None:
    """Two DISTINCT GameStates (two processes) converge after a mirrored reconcile (E6).

    The thief moves on its OWN server; the orchestrator reconciles (pull thief truth
    -> push to both). Afterwards the cop server's ground truth equals the thief
    server's: both ``get_full_state`` payloads are byte-identical. Proves the fix
    works across genuinely separate state objects.
    """
    cop_state = make_state(cop=(4, 4), thief=(0, 0))
    thief_state = make_state(cop=(4, 4), thief=(0, 0))
    cop_mcp = build_server("cop", cop_state, cloud_config)
    thief_mcp = build_server("thief", thief_state, cloud_config)
    async with Client(cop_mcp) as cc, Client(thief_mcp) as tc:
        clients = {"cop": cc, "thief": tc}
        sync = ClientStateSync(clients)
        engine_state = make_state(cop=(4, 4), thief=(0, 0))
        await tc.call_tool("apply_move", {"role": "thief", "direction": "SE"})  # thief -> (1,1)
        await sync.reconcile(engine_state, "thief")
        cop_truth = (await cc.call_tool("get_full_state", {})).data
        thief_truth = (await tc.call_tool("get_full_state", {})).data
        cop_obs = await _obs(cc, "cop")  # partial view AFTER the reconcile mirror
    assert cop_truth["thief_pos"] == [1, 1]  # cop server learned the thief's move
    assert cop_truth == thief_truth  # both processes share one canonical board
    assert engine_state.thief_pos == (1, 1)  # engine owns the same authoritative truth
    assert engine_state.current_role == "cop"  # engine handed the turn on (owns progression)
    assert "thief_pos" not in cop_obs  # partial observability still enforced after sync (E4)


async def test_without_sync_two_states_diverge(make_state, cloud_config) -> None:
    """Control: WITHOUT mirroring, the cop server never sees the thief's move (diverges).

    Same setup, but no ``sync_state`` call. The thief server advances; the cop server
    is stale. This is exactly the cloud bug the Phase-8 fix removes.
    """
    cop_state = make_state(cop=(4, 4), thief=(0, 0))
    thief_state = make_state(cop=(4, 4), thief=(0, 0))
    cop_mcp = build_server("cop", cop_state, cloud_config)
    thief_mcp = build_server("thief", thief_state, cloud_config)
    async with Client(cop_mcp) as cc, Client(thief_mcp) as tc:
        await tc.call_tool("apply_move", {"role": "thief", "direction": "SE"})
        cop_truth = (await cc.call_tool("get_full_state", {})).data
        thief_truth = (await tc.call_tool("get_full_state", {})).data
    assert thief_truth["thief_pos"] == [1, 1]
    assert cop_truth["thief_pos"] == [0, 0]  # STALE — proves divergence without the fix
    assert cop_truth != thief_truth


async def test_sync_state_overwrites_in_place(make_state, cloud_config) -> None:
    """sync_state writes onto the EXISTING state handle (the server keeps its reference)."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    mcp = build_server("cop", state, cloud_config)
    canonical = make_state(cop=(1, 1), thief=(3, 3))
    canonical.move_number = 7
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
        res = await c.call_tool("sync_state", {"state": canonical.to_dict()})
    assert {"sync_state", "get_full_state"} <= names  # both tools registered (E6)
    assert res.data == {"ok": True, "move_number": 7}
    assert state.cop_pos == (1, 1) and state.thief_pos == (3, 3)  # same object mutated
    assert state.move_number == 7


def test_overwrite_state_helper_is_pure() -> None:
    """The state_mirror helper overwrites every field deterministically (unit-level)."""
    from cosmos77_ex06.mcp_servers.state_mirror import full_state, overwrite_state

    target = GameState(
        grid_size=[5, 5],
        cop_pos=(0, 0),
        thief_pos=(0, 0),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
    )
    src = GameState(
        grid_size=[5, 5],
        cop_pos=(2, 2),
        thief_pos=(3, 3),
        max_moves=25,
        allow_diagonal=True,
        turn_order=["thief", "cop"],
        move_number=4,
    )
    ack = overwrite_state(target, src.to_dict())
    assert ack == {"ok": True, "move_number": 4}
    assert full_state(target) == src.to_dict()
