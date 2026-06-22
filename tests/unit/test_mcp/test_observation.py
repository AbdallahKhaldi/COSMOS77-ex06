"""Partial-observability (E4) tests for the observation builder.

The headline guarantee: the opponent's exact cell is NEVER disclosed unless it
falls inside the caller's vision window."""

from __future__ import annotations

from cosmos77_ex06.mcp_servers.observation import (
    build_observation,
    confirm_position,
    visible_cells,
)


def _occupants(obs: dict) -> list[str]:
    return [c["occupant"] for c in obs["visible_cells"] if c["occupant"]]


def test_own_position_is_exact(make_state) -> None:
    """The caller always knows its own exact cell."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    obs = build_observation(state, "cop", 1, 5)
    assert obs["self"] == {"x": 4, "y": 4}


def test_opponent_not_leaked_when_out_of_vision(make_state) -> None:
    """With the thief far away, NO field reveals the thief's cell (the E4 headline)."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    obs = build_observation(state, "cop", 1, 5)
    # No top-level opponent/thief position field anywhere.
    assert "thief" not in obs
    assert "opponent" not in obs
    assert "thief_pos" not in obs
    # The thief is not an occupant of any visible cell.
    assert "thief" not in _occupants(obs)
    # The thief's true cell (0,0) is not even present in the window at all.
    assert all((c["x"], c["y"]) != (0, 0) for c in obs["visible_cells"])


def test_opponent_visible_only_inside_window(make_state) -> None:
    """Move the thief adjacent to the cop -> it appears as an occupant."""
    state = make_state(cop=(2, 2), thief=(3, 2))
    obs = build_observation(state, "cop", 1, 5)
    assert "thief" in _occupants(obs)
    thief_cells = [(c["x"], c["y"]) for c in obs["visible_cells"] if c["occupant"] == "thief"]
    assert thief_cells == [(3, 2)]


def test_no_global_truth_fields(make_state) -> None:
    """The payload has no full board / opponent budget / opponent move fields."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    obs = build_observation(state, "cop", 1, 5)
    forbidden = {"board", "occupancy", "opponent_barriers_remaining", "opponent_last_move"}
    assert forbidden.isdisjoint(obs.keys())


def test_barriers_remaining_cop_only(make_state) -> None:
    """``barriers_remaining`` appears for the cop, never the thief."""
    state = make_state()
    cop_obs = build_observation(state, "cop", 1, 5)
    thief_obs = build_observation(state, "thief", 1, 5)
    assert "barriers_remaining" in cop_obs
    assert "barriers_remaining" not in thief_obs


def test_barrier_visible_as_terrain(make_state) -> None:
    """A barrier inside the window is visible as blocked terrain."""
    state = make_state(cop=(2, 2), thief=(0, 0))
    state.barriers = [(2, 1)]
    cells = visible_cells(state, "cop", 1)
    blocked = [(c["x"], c["y"]) for c in cells if c["blocked"]]
    assert (2, 1) in blocked


def test_verify_position_unknown_outside_window(make_state) -> None:
    """verify_position is confirm-only: outside the window it returns known=False."""
    state = make_state(cop=(4, 4), thief=(0, 0))
    res = confirm_position(state, "cop", 0, 0, 1)
    assert res == {"known": False, "result": None}


def test_verify_position_confirms_inside_window(make_state) -> None:
    """Inside the window it confirms the opponent's actual cell."""
    state = make_state(cop=(2, 2), thief=(3, 2))
    hit = confirm_position(state, "cop", 3, 2, 1)
    miss = confirm_position(state, "cop", 2, 3, 1)
    assert hit == {"known": True, "result": True}
    assert miss == {"known": True, "result": False}


def test_verify_position_out_of_bounds(make_state) -> None:
    """An off-grid cell is unknowable (known=False)."""
    state = make_state(cop=(0, 0), thief=(4, 4))
    assert confirm_position(state, "cop", -1, -1, 1) == {"known": False, "result": None}


def test_verify_position_cannot_scan(make_state) -> None:
    """Every out-of-window cell is unknown -> the tool cannot triangulate."""
    state = make_state(cop=(0, 0), thief=(4, 4))
    for x in range(5):
        for y in range(5):
            if max(abs(x), abs(y)) > 1:  # outside the cop's radius-1 window
                assert confirm_position(state, "cop", x, y, 1)["known"] is False
