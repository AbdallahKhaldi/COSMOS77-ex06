"""Direct unit tests of the GameTools logic (deterministic, no FastMCP wiring)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.mcp_servers.tools import GameTools


@pytest.fixture
def cop_tools(make_state, mcp_config):
    return lambda **kw: GameTools(make_state(**kw), mcp_config, "cop")


@pytest.fixture
def thief_tools(make_state, mcp_config):
    return lambda **kw: GameTools(make_state(**kw), mcp_config, "thief")


def test_send_and_receive_free_text(thief_tools) -> None:
    """send_message appends free prose; receive_messages returns the opponent's prose."""
    tools = thief_tools()
    sent = tools.send_message("thief", "All quiet up north, nothing to see.")
    assert sent["ok"] is True
    # The thief's own line is filtered out of its own inbox; the cop's is delivered.
    tools.state.add_message(0, "cop", "Closing in from the east.")
    got = tools.receive_messages("thief")
    assert [m["content"] for m in got["messages"]] == ["Closing in from the east."]
    assert got["messages"][0]["from"] == "cop"
    assert got["latest_id"] == 1


def test_receive_excludes_own_messages(thief_tools) -> None:
    """A role never receives its own prior prose echoed back as incoming."""
    tools = thief_tools()
    tools.send_message("thief", "bluff: I am north")
    got = tools.receive_messages("thief")
    assert got["messages"] == []
    assert got["latest_id"] == -1


def test_receive_messages_since_filter(thief_tools) -> None:
    """The ``since`` cursor returns only newer opponent messages."""
    tools = thief_tools()
    tools.state.add_message(0, "cop", "first")
    tools.state.add_message(0, "cop", "second")
    got = tools.receive_messages("thief", since=1)
    assert [m["content"] for m in got["messages"]] == ["second"]


def test_role_mismatch_rejected(cop_tools) -> None:
    """The cop server refuses to act for the thief role."""
    tools = cop_tools()
    with pytest.raises(ValueError, match="cannot act for role"):
        tools.get_local_observation("thief")


def test_place_barrier_decrements_budget(cop_tools) -> None:
    """A cop barrier is placed and the remaining budget drops."""
    tools = cop_tools(cop=(4, 4), thief=(0, 0))
    res = tools.place_barrier("cop", 2, 2)
    assert res["ok"] is True
    assert res["cell"] == {"x": 2, "y": 2}
    assert res["barriers_remaining"] == 4
    assert (2, 2) in tools.state.barriers


def test_thief_stepping_onto_cop_is_not_a_capture(make_state, mcp_config) -> None:
    """Spec §4.3: capture is the COP landing on the thief; a thief move onto the cop is NOT a win."""
    state = make_state(cop=(1, 1), thief=(0, 0))
    state.current_role = "thief"
    thief = GameTools(state, mcp_config, "thief")
    res = thief.apply_move("thief", "SE")  # (0,0) -> (1,1): steps onto the cop's cell
    assert res["ok"] is True and res["captured"] is False


def test_place_barrier_blocks_subsequent_move(make_state, mcp_config) -> None:
    """A placed barrier is impassable to a later apply_move by either role."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    cop = GameTools(state, mcp_config, "cop")
    cop.place_barrier("cop", 1, 1)
    state.current_role = "thief"
    thief = GameTools(state, mcp_config, "thief")
    res = thief.apply_move("thief", "SE")  # (0,0)->(1,1) is now blocked
    assert res["ok"] is False
    assert "illegal move" in res["reason"]


def test_place_barrier_budget_exhausted(cop_tools) -> None:
    """Past max_barriers the placement is refused with a reason."""
    tools = cop_tools(cop=(4, 4), thief=(0, 0))
    tools.state.barriers_used = 5  # max_barriers
    res = tools.place_barrier("cop", 2, 2)
    assert res["ok"] is False
    assert "budget" in res["reason"]


def test_apply_move_increments_move_number_after_cop(make_state, mcp_config) -> None:
    """The move counter advances once per full round (after the last role)."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    thief = GameTools(state, mcp_config, "thief")
    thief.apply_move("thief", "SE")  # thief first -> no increment yet
    assert state.move_number == 0
    cop = GameTools(state, mcp_config, "cop")
    cop.apply_move("cop", "NW")  # cop last -> increment
    assert state.move_number == 1


def test_apply_move_illegal_direction(make_state, mcp_config) -> None:
    """An out-of-bounds move returns ok=False and does not advance state."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    thief = GameTools(state, mcp_config, "thief")
    res = thief.apply_move("thief", "NW")  # (0,0)->(-1,-1) off-grid
    assert res["ok"] is False
    assert tuple(state.thief_pos) == (0, 0)
