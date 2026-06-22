"""The partial-observation builder — the E4 enforcement core (PRD §4.3).

``build_observation`` maps the ground-truth :class:`GameState` to a role-scoped,
vision-windowed *partial* view ``Ωi`` (the Dec-POMDP observation function ``O``).
The opponent's exact cell is disclosed **only** when it lies inside the caller's
vision window; outside it there is no field anywhere in the payload that reveals
the opponent's position. Barriers are returned as visible *terrain* only — never
the opponent's barrier budget. This isolation gives the redaction its own tests.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.game.state import Cell, GameState


def _chebyshev(a: Cell, b: Cell) -> int:
    """Chebyshev (king-move) distance between two cells."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _in_bounds(cell: Cell, grid: list[int]) -> bool:
    """``True`` iff ``cell`` lies on the ``grid``."""
    return 0 <= cell[0] < grid[0] and 0 <= cell[1] < grid[1]


def visible_cells(state: GameState, role: str, vision_radius: int) -> list[dict[str, Any]]:
    """Return the cells within ``vision_radius`` of ``role`` as terrain + occupant.

    The opponent appears as an ``occupant`` **only** when its cell is inside the
    window; otherwise the cell simply lists no opponent. This is the single
    disclosure path for the opponent's position (E4).
    """
    grid = list(state.grid_size)
    self_pos: Cell = tuple(state.cop_pos) if role == "cop" else tuple(state.thief_pos)
    opp_role = "thief" if role == "cop" else "cop"
    opp_pos: Cell = tuple(state.thief_pos) if role == "cop" else tuple(state.cop_pos)
    barriers = {tuple(b) for b in state.barriers}
    out: list[dict[str, Any]] = []
    r = int(vision_radius)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            cell = (self_pos[0] + dx, self_pos[1] + dy)
            if not _in_bounds(cell, grid):
                continue
            occupant: str | None = None
            if cell == self_pos:
                occupant = role
            elif cell == opp_pos:
                occupant = opp_role
            out.append(
                {
                    "x": cell[0],
                    "y": cell[1],
                    "blocked": cell in barriers,
                    "occupant": occupant,
                }
            )
    return out


def build_observation(
    state: GameState, role: str, vision_radius: int, max_barriers: int
) -> dict[str, Any]:
    """Return the partial, role-scoped observation for ``role`` (PRD §4.3).

    Contains the caller's own exact position, the vision window's terrain (with the
    opponent's occupant only if in-window), and turn counters. Carries **no**
    global-truth field: no opponent position, no full occupancy map, no opponent
    barrier budget. ``barriers_remaining`` is included for the cop only.
    """
    self_pos: Cell = tuple(state.cop_pos) if role == "cop" else tuple(state.thief_pos)
    obs: dict[str, Any] = {
        "role": role,
        "self": {"x": self_pos[0], "y": self_pos[1]},
        "grid_size": list(state.grid_size),
        "vision_radius": int(vision_radius),
        "visible_cells": visible_cells(state, role, vision_radius),
        "move_number": int(state.move_number),
        "moves_remaining": max(0, int(state.max_moves) - int(state.move_number)),
    }
    if role == "cop":
        obs["barriers_remaining"] = max(0, int(max_barriers) - int(state.barriers_used))
    return obs


def confirm_position(
    state: GameState, role: str, x: int, y: int, vision_radius: int
) -> dict[str, Any]:
    """Confirm-only check backing ``verify_position`` (PRD §4.4).

    Returns ``{"known": <bool>, "result": <bool|None>}``. ``known`` is ``True``
    only when ``(x, y)`` is inside the caller's vision window — outside it the
    answer is unknowable, so the tool can never enumerate cells to triangulate the
    opponent. When known, ``result`` is whether that cell holds the opponent.
    """
    self_pos: Cell = tuple(state.cop_pos) if role == "cop" else tuple(state.thief_pos)
    opp_pos: Cell = tuple(state.thief_pos) if role == "cop" else tuple(state.cop_pos)
    if not _in_bounds((x, y), list(state.grid_size)):
        return {"known": False, "result": None}
    if _chebyshev(self_pos, (x, y)) > int(vision_radius):
        return {"known": False, "result": None}
    return {"known": True, "result": (x, y) == opp_pos}
