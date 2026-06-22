"""Movement and barrier-placement contract over a :class:`Board` (PRD §3-§4).

``legal_moves`` lists the directions whose target is passable (``STAY`` always
included; the four diagonals only when ``allow_diagonal``). ``apply_move`` returns
the new cell or raises :class:`IllegalMoveError` — it never silently clamps, so a
bad action surfaces as a hard, deterministic error (used by Technical-Loss
detection). ``place_barrier`` is **cop-only**, budget-bounded by ``max_barriers``,
and rejects out-of-bounds, occupied, or already-blocked cells.
"""

from __future__ import annotations

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.state import Cell


class IllegalMoveError(Exception):
    """Raised when a requested move or barrier placement violates the rules."""


def legal_moves(pos: Cell, board: Board) -> list[str]:
    """Return the legal direction names from ``pos`` (``STAY`` always legal)."""
    out: list[str] = []
    for name, (dx, dy) in board.directions().items():
        target = (pos[0] + dx, pos[1] + dy)
        if board.is_passable(target):
            out.append(name)
    return out


def apply_move(pos: Cell, direction: str, board: Board) -> Cell:
    """Return the cell reached by ``direction`` from ``pos``.

    Raises :class:`IllegalMoveError` for an unknown direction or one whose target
    is out-of-bounds or a barrier.
    """
    table = board.directions()
    if direction not in table:
        raise IllegalMoveError(f"unknown direction: {direction!r}")
    dx, dy = table[direction]
    target = (pos[0] + dx, pos[1] + dy)
    if not board.is_passable(target):
        raise IllegalMoveError(f"illegal move {direction} from {pos} -> {target}")
    return target


def place_barrier(
    role: str,
    cell: Cell,
    board: Board,
    barriers_used: int,
    max_barriers: int,
    cop_pos: Cell,
    thief_pos: Cell,
) -> int:
    """Place a barrier (cop-only) and return the new ``barriers_used`` count.

    Raises :class:`IllegalMoveError` if the caller is not the cop, the budget is
    exhausted, or ``cell`` is out-of-bounds, already blocked, or occupied by an
    agent. On success the cell becomes impassable for *both* agents.
    """
    if role != "cop":
        raise IllegalMoveError("only the cop may place barriers")
    if barriers_used >= max_barriers:
        raise IllegalMoveError(f"barrier budget exhausted ({max_barriers})")
    if not board.in_bounds(cell):
        raise IllegalMoveError(f"barrier out of bounds: {cell}")
    if board.is_blocked(cell):
        raise IllegalMoveError(f"cell already blocked: {cell}")
    if cell in (cop_pos, thief_pos):
        raise IllegalMoveError(f"cannot drop a barrier onto an agent: {cell}")
    board.add_barrier(cell)
    return barriers_used + 1
