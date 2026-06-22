"""In-memory FastMCP Client tests for the two servers (E2/E3/E4) — no network.

The in-memory transport bypasses HTTP bearer auth (auth is tested directly in
``test_auth``); here we assert the tool inventory per server, partial observability
through the tool, state mutation via ``apply_move``, and the structural cop-only
``place_barrier`` asymmetry."""

from __future__ import annotations

import pytest
from fastmcp import Client

from cosmos77_ex06.mcp_servers.server import build_server

SHARED = {
    "send_message",
    "receive_messages",
    "get_local_observation",
    "verify_position",
    "apply_move",
}


@pytest.fixture
def cop_server(make_state, mcp_config):
    """A cop FastMCP server bound to a known state (thief far from cop)."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    return build_server("cop", state, mcp_config), state


@pytest.fixture
def thief_server(make_state, mcp_config):
    """A thief FastMCP server bound to a known state."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    return build_server("thief", state, mcp_config), state


async def test_cop_lists_place_barrier(cop_server) -> None:
    """The cop server exposes the shared five PLUS place_barrier."""
    mcp, _ = cop_server
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
    assert SHARED <= names
    assert "place_barrier" in names


async def test_thief_lacks_place_barrier(thief_server) -> None:
    """The thief server exposes the shared five and NOT place_barrier (structural)."""
    mcp, _ = thief_server
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
    assert SHARED <= names
    assert "place_barrier" not in names


async def test_get_local_observation_partial_via_tool(cop_server) -> None:
    """Through the tool, the thief's cell is not leaked when out of vision (E4)."""
    mcp, _ = cop_server
    async with Client(mcp) as c:
        res = await c.call_tool("get_local_observation", {"role": "cop"})
    obs = res.data
    assert obs["self"] == {"x": 4, "y": 4}
    assert "thief" not in obs and "thief_pos" not in obs
    assert all(cell["occupant"] != "thief" for cell in obs["visible_cells"])


async def test_apply_move_updates_state_via_tool(thief_server) -> None:
    """apply_move mutates the shared GameState through the tool call."""
    mcp, state = thief_server
    async with Client(mcp) as c:
        res = await c.call_tool("apply_move", {"role": "thief", "direction": "SE"})
    assert res.data["ok"] is True
    assert res.data["new_self"] == {"x": 1, "y": 1}
    assert tuple(state.thief_pos) == (1, 1)


async def test_apply_move_rejects_out_of_turn(cop_server) -> None:
    """The cop cannot move first (thief moves first); the tool returns ok=False."""
    mcp, _ = cop_server
    async with Client(mcp) as c:
        res = await c.call_tool("apply_move", {"role": "cop", "direction": "NW"})
    assert res.data["ok"] is False
    assert res.data["reason"] == "not your turn"


async def test_place_barrier_rejected_for_thief(thief_server) -> None:
    """The thief literally cannot call place_barrier — it is not registered."""
    mcp, _ = thief_server
    async with Client(mcp) as c:
        with pytest.raises(Exception):  # noqa: B017 - unknown tool name is raised by FastMCP
            await c.call_tool("place_barrier", {"role": "thief", "x": 1, "y": 1})


async def test_send_and_receive_via_tools(cop_server) -> None:
    """receive_messages returns the opponent's prose, never the caller's own echo."""
    mcp, state = cop_server
    # The thief authored a prior message; the cop should receive only that.
    state.add_message(0, "thief", "heading south")
    async with Client(mcp) as c:
        await c.call_tool("send_message", {"role": "cop", "content": "sweeping NE"})
        got = await c.call_tool("receive_messages", {"role": "cop", "since": 0})
    contents = [m["content"] for m in got.data["messages"]]
    assert contents == ["heading south"]  # opponent only; the cop's own line is filtered


async def test_verify_position_via_tool(make_state, mcp_config) -> None:
    """The verify_position tool wrapper confirms an in-window opponent cell."""
    state = make_state(cop=(2, 2), thief=(3, 2))
    mcp = build_server("cop", state, mcp_config)
    async with Client(mcp) as c:
        res = await c.call_tool("verify_position", {"role": "cop", "x": 3, "y": 2})
    assert res.data == {"known": True, "result": True}


async def test_place_barrier_via_tool(make_state, mcp_config) -> None:
    """The cop place_barrier tool wrapper places a barrier and reports the budget."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    mcp = build_server("cop", state, mcp_config)
    async with Client(mcp) as c:
        res = await c.call_tool("place_barrier", {"role": "cop", "x": 2, "y": 2})
    assert res.data["ok"] is True
    assert res.data["barriers_remaining"] == 4


async def test_capture_reported_via_apply_move(make_state, mcp_config) -> None:
    """When the cop lands on the thief's cell, the tool reports captured=True."""
    state = make_state(cop=(1, 0), thief=(0, 0))
    state.current_role = "cop"  # cop's turn for this capture check
    mcp = build_server("cop", state, mcp_config)
    async with Client(mcp) as c:
        res = await c.call_tool("apply_move", {"role": "cop", "direction": "W"})
    assert res.data["ok"] is True
    assert res.data["captured"] is True
