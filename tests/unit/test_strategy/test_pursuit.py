"""Optimal retrograde pursuit — the cop forces a capture from any cop-win start (E9)."""

from __future__ import annotations

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import apply_move, legal_moves
from cosmos77_ex06.strategy import pursuit


def test_five_by_five_every_start_is_a_cop_win() -> None:
    board = Board([5, 5], allow_diagonal=True)
    assert pursuit.is_cop_win((4, 4), (0, 0), board, thief_to_move=True)
    rank = pursuit._solved(board)["rank"]  # noqa: SLF001 - assert the solved table directly
    assert rank[((4, 4), (0, 0), 1)] == 8  # 8 plies to forced capture from the agreed opening
    starts = [(c, t) for c in board.cells for t in board.cells if c != t]
    assert all((c, t, 1) in rank for c, t in starts)  # cop wins from ALL 600 thief-first starts


def test_optimal_cop_catches_worst_case_evader_within_limit() -> None:
    board = Board([5, 5], allow_diagonal=True)
    rank = pursuit._solved(board)["rank"]  # noqa: SLF001
    cop, thief = (4, 4), (0, 0)
    for move in range(1, 26):
        best_t, best_r = thief, -1
        for direction in legal_moves(thief, board):
            landing = apply_move(thief, direction, board)
            if landing == cop:
                continue
            dtc = rank.get((cop, landing, 0))
            dtc = 10**9 if dtc is None else dtc  # would-be escape ranks highest
            if dtc > best_r:
                best_r, best_t = dtc, landing
        thief = best_t
        cop = apply_move(cop, pursuit.best_move(cop, thief, board), board)
        if cop == thief:
            assert move <= 25
            return
    raise AssertionError("optimal cop failed to catch the worst-case evader within 25 moves")


def test_barriered_board_falls_back_to_none() -> None:
    board = Board([5, 5], allow_diagonal=True, barriers={(2, 2)})
    assert pursuit.best_move((4, 4), (0, 0), board) is None  # solver only runs on an open board
