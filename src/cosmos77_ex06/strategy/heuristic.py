"""Distance-greedy decision heuristic operating on the agent's *estimate* (E9).

The strategy is a pure, deterministic, client-side suggestion (PRD_strategy §3/§6):
the cop minimizes distance to its **estimated** thief cell and may drop a barrier to
cut off escape when adjacent; the thief maximizes distance and drifts toward open
space. It never reads ground truth — only the belief inferred from the free
natural-language messages plus the agent's own partial observation. The metric is
Chebyshev when ``allow_diagonal`` (king moves) else Manhattan, chosen from config
(Rule 4). All candidate actions come from :func:`game.moves.legal_moves`, so a
suggestion is always a legal move (or, for the cop, a legal barrier placement).
"""

from __future__ import annotations

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import apply_move, legal_moves
from cosmos77_ex06.game.state import Cell
from cosmos77_ex06.shared.config import Config


def manhattan(a: Cell, b: Cell) -> int:
    """Return the L1 (orthogonal-step) distance between cells ``a`` and ``b``."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def chebyshev(a: Cell, b: Cell) -> int:
    """Return the L-infinity (king-move) distance between cells ``a`` and ``b``."""
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def distance(a: Cell, b: Cell, allow_diagonal: bool) -> int:
    """Return the step-cost distance under the config-selected metric."""
    return chebyshev(a, b) if allow_diagonal else manhattan(a, b)


def _ranked_moves(self_pos: Cell, est: Cell, board: Board) -> list[tuple[int, Cell, str]]:
    """Return ``(distance-to-est, target-cell, direction)`` for every legal move.

    Sorted ascending by distance then ``(x, y)`` then name, giving a fully
    deterministic tie-break for reproducible tests (PRD_strategy §3.2).
    """
    ranked: list[tuple[int, Cell, str]] = []
    for name in legal_moves(self_pos, board):
        target = apply_move(self_pos, name, board)
        ranked.append((distance(target, est, board.allow_diagonal), target, name))
    ranked.sort(key=lambda r: (r[0], r[1][0], r[1][1], r[2]))
    return ranked


def suggest_cop_action(
    estimate: Cell,
    self_pos: Cell,
    board: Board,
    config: Config,
    barriers_left: int,
) -> dict[str, object]:
    """Suggest the cop's action: minimize distance to the estimate, else cut off escape.

    Returns ``{"action": "move", "direction": str}`` for the distance-minimizing legal
    move, or ``{"action": "place_barrier", "cell": Cell}`` when the cop is adjacent to
    the estimate, has budget, and a barrier measurably shrinks the thief's open area.
    Operates only on ``estimate`` (the NL-inferred belief), never ground truth.
    """
    barrier = _barrier_cutoff(estimate, self_pos, board, config, barriers_left)
    if barrier is not None:
        return {"action": "place_barrier", "cell": barrier}
    # ``legal_moves`` always contains STAY, so ``ranked`` is never empty.
    ranked = _ranked_moves(self_pos, estimate, board)
    return {"action": "move", "direction": ranked[0][2]}


def suggest_thief_action(
    estimate: Cell,
    self_pos: Cell,
    board: Board,
    config: Config,
) -> dict[str, object]:
    """Suggest the thief's action: maximize distance to the estimate, prefer open space.

    Returns ``{"action": "move", "direction": str}``. Among moves of equal (maximal)
    distance to the estimated cop cell, the one with the most open neighbours wins
    (open-space tie-break, PRD_strategy §3.3), so the thief avoids corners and traps.
    """
    # ``legal_moves`` always contains STAY, so ``ranked`` is never empty.
    ranked = _ranked_moves(self_pos, estimate, board)
    best = ranked[-1][0]
    far = [r for r in ranked if r[0] == best]
    far.sort(key=lambda r: (-len(board.neighbors(r[1])), r[1][0], r[1][1], r[2]))
    return {"action": "move", "direction": far[0][2]}


def _barrier_cutoff(
    estimate: Cell,
    self_pos: Cell,
    board: Board,
    config: Config,
    barriers_left: int,
) -> Cell | None:
    """Pick the empty neighbour of the estimate that best cuts off the thief's escape.

    Returns the barrier cell only when the cop is adjacent to the estimate
    (``distance <= 1``), ``barriers_left > 0``, and walling that cell strictly
    reduces the estimate's reachable open neighbours; otherwise ``None`` (the cop
    moves instead). Barriers are impassable to both agents, so the cop spends one
    only when it measurably tightens the net (PRD_strategy §3.2).
    """
    if barriers_left <= 0:
        return None
    if distance(self_pos, estimate, board.allow_diagonal) > 1:
        return None
    escapes = [c for c in board.neighbors(estimate) if c != self_pos]
    if len(escapes) <= 1:
        return None
    escapes.sort(key=lambda c: (-len(board.neighbors(c)), c[0], c[1]))
    return escapes[0]
