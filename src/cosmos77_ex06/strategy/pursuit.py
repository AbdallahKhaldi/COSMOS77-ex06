"""Optimal single-cop pursuit via retrograde analysis (E9) — guaranteed capture from a cop-win start.

A greedy distance-minimizing cop can be mirrored forever in open space. This solves the pursuit
game EXACTLY by backward induction over every ``(cop, thief, side-to-move)`` state, computing the
distance-to-capture (DTC) under optimal play: the cop minimizes it, the evader maximizes it,
capture = the cop stepping onto the thief. From any cop-win state the returned move forces a
capture in the FEWEST plies against ANY evader (their MARL thief included). On a 5x5 with king
moves the cop wins from effectively every start, so we catch within the 25-move limit. The move is
deterministic; barriers are never used (variant 0). Solved once per grid size and cached.
"""

from __future__ import annotations

import heapq

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import apply_move, legal_moves
from cosmos77_ex06.game.state import Cell

_COP, _THIEF = 0, 1
_cache: dict[tuple[int, int], dict] = {}


def _tables(width: int, height: int) -> dict:
    """Retrograde-solve the open-board pursuit; return rank[(cop,thief,side)] + move lookups."""
    board = Board([width, height], allow_diagonal=True)
    cells = board.cells
    mv = {c: [*board.neighbors(c), c] for c in cells}  # legal landings incl. STAY
    dir_of = {(c, apply_move(c, d, board)): d for c in cells for d in legal_moves(c, board)}
    rank: dict[tuple, int] = {}
    cnt: dict[tuple, int] = {}
    heap: list = []
    for cop in cells:
        for thief in cells:
            if cop == thief:
                continue
            cnt[(cop, thief, _THIEF)] = sum(1 for t in mv[thief] if t != cop)
            if thief in board.neighbors(cop):  # the cop can step onto the thief now (capture)
                rank[(cop, thief, _COP)] = 1
                heapq.heappush(heap, (1, cop, thief, _COP))
    while heap:
        r, cop, thief, side = heapq.heappop(heap)
        if rank.get((cop, thief, side)) != r:
            continue
        if side == _COP:
            for tp in mv[thief]:  # thief-to-move predecessors (thief moved tp -> thief)
                pred = (cop, tp, _THIEF)
                if tp == cop or pred in rank:
                    continue
                cnt[pred] -= 1
                if cnt[pred] == 0:
                    worst = max(rank[(cop, t2, _COP)] for t2 in mv[tp] if t2 != cop)
                    rank[pred] = 1 + worst
                    heapq.heappush(heap, (1 + worst, cop, tp, _THIEF))
        else:
            for cp in mv[cop]:  # cop-to-move predecessors (cop moved cp -> cop); min = first reach
                if cp == thief or (cp, thief, _COP) in rank:
                    continue
                rank[(cp, thief, _COP)] = 1 + r
                heapq.heappush(heap, (1 + r, cp, thief, _COP))
    return {"rank": rank, "mv": mv, "dir_of": dir_of}


def _solved(board: Board) -> dict:
    """Return the cached solve for this board's size (solving on first use)."""
    key = (board.width, board.height)
    if key not in _cache:
        _cache[key] = _tables(*key)
    return _cache[key]


def is_cop_win(cop: Cell, thief: Cell, board: Board, thief_to_move: bool = True) -> bool:
    """True iff the cop can force a capture from this state (thief moving first by default)."""
    if board.barriers:
        return False
    side = _THIEF if thief_to_move else _COP
    return (tuple(cop), tuple(thief), side) in _solved(board)["rank"]


def best_move(cop: Cell, thief: Cell, board: Board) -> str | None:
    """The cop's optimal direction toward forced capture, or None on a thief-win/barriered board."""
    if board.barriers:
        return None  # the solver assumes an open board (variant 0)
    tab = _solved(board)
    rank, mv, dir_of = tab["rank"], tab["mv"], tab["dir_of"]
    cop, thief = tuple(cop), tuple(thief)
    best = None
    for c2 in mv[cop]:
        if c2 == thief:
            cost = 1
        else:
            r = rank.get((c2, thief, _THIEF))
            if r is None:
                continue  # this move lets the thief escape forever
            cost = 1 + r
        cand = (cost, c2[0], c2[1], dir_of[(cop, c2)])
        if best is None or cand < best:
            best = cand
    return best[3] if best else None


def best_evasion(cop: Cell, thief: Cell, board: Board) -> str | None:
    """The thief's optimal direction: maximise distance-to-capture (survive longest); never enter cop.

    Against an optimal cop this delays capture as long as the board allows; against a SUBOPTIMAL cop
    (e.g. a trained policy with a blind spot) maximal delay is exactly what runs out their 25 moves
    and wins. Open board only; ``None`` falls the caller back to the maximin heuristic.
    """
    if board.barriers:
        return None
    tab = _solved(board)
    rank, mv, dir_of = tab["rank"], tab["mv"], tab["dir_of"]
    cop, thief = tuple(cop), tuple(thief)
    best = None
    for t2 in mv[thief]:
        if t2 == cop:
            continue  # never enter the cop's cell (keeps capture unambiguous)
        r = rank.get((cop, t2, _COP))
        dtc = 10**9 if r is None else r  # an escape (none on 5x5) ranks highest
        cand = (-dtc, -len(board.neighbors(t2)), t2[0], t2[1], dir_of[(thief, t2)])
        if best is None or cand < best:
            best = cand
    return best[4] if best else None
