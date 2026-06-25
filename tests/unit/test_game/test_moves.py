"""Tests for movement and barrier placement (PRD §3-§4)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import IllegalMoveError, apply_move, legal_moves, place_barrier


def test_legal_moves_includes_stay() -> None:
    board = Board([3, 3], allow_diagonal=True)
    assert "STAY" in legal_moves((1, 1), board)


def test_diagonals_legal_only_when_allowed() -> None:
    diag = Board([3, 3], allow_diagonal=True)
    no_diag = Board([3, 3], allow_diagonal=False)
    assert "NE" in legal_moves((1, 1), diag)
    moves = legal_moves((1, 1), no_diag)
    assert all(d not in moves for d in ("NE", "NW", "SE", "SW"))


def test_legal_moves_excludes_out_of_bounds_and_barriers() -> None:
    board = Board([3, 3], allow_diagonal=False, barriers={(1, 0)})
    moves = legal_moves((0, 0), board)
    assert "N" not in moves  # out of bounds
    assert "E" not in moves  # barrier at (1, 0)
    assert "S" in moves


def test_apply_move_returns_target() -> None:
    board = Board([3, 3], allow_diagonal=True)
    assert apply_move((1, 1), "NE", board) == (2, 0)


def test_apply_move_rejects_out_of_bounds() -> None:
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        apply_move((0, 0), "N", board)


def test_apply_move_rejects_into_barrier() -> None:
    board = Board([3, 3], allow_diagonal=True, barriers={(1, 0)})
    with pytest.raises(IllegalMoveError):
        apply_move((0, 0), "E", board)


def test_apply_move_rejects_unknown_direction() -> None:
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        apply_move((0, 0), "ZZ", board)


def test_barrier_blocks_both_agents() -> None:
    board = Board([3, 3], allow_diagonal=False)
    place_barrier("cop", (1, 1), board, 0, 5, (2, 2), (0, 0))
    assert board.is_blocked((1, 1))
    # neither the cop nor the thief may step onto it
    with pytest.raises(IllegalMoveError):
        apply_move((1, 2), "N", board)
    with pytest.raises(IllegalMoveError):
        apply_move((1, 0), "S", board)


def test_barrier_thief_rejected() -> None:
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        place_barrier("thief", (1, 1), board, 0, 5, (2, 2), (0, 0))


def test_barrier_budget_enforced() -> None:
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        place_barrier("cop", (1, 1), board, 5, 5, (2, 2), (0, 0))


def test_barrier_count_increments() -> None:
    board = Board([3, 3], allow_diagonal=True)
    used = place_barrier("cop", (1, 1), board, 0, 5, (2, 2), (0, 0))
    assert used == 1


def test_barrier_rejects_out_of_bounds() -> None:
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        place_barrier("cop", (3, 3), board, 0, 5, (2, 2), (0, 0))


def test_barrier_rejects_thief_cell_but_allows_cop_own_cell() -> None:
    """Spec §4.3: the cop walls the cell it STANDS on; it may never wall the thief's cell."""
    board = Board([3, 3], allow_diagonal=True)
    with pytest.raises(IllegalMoveError):
        place_barrier("cop", (0, 0), board, 0, 5, (2, 2), (0, 0))  # thief's cell -> rejected
    used = place_barrier("cop", (2, 2), board, 0, 5, (2, 2), (0, 0))  # cop's OWN cell -> allowed
    assert used == 1 and (2, 2) in board.barriers


def test_barrier_rejects_reblock() -> None:
    board = Board([3, 3], allow_diagonal=True, barriers={(1, 1)})
    with pytest.raises(IllegalMoveError):
        place_barrier("cop", (1, 1), board, 1, 5, (2, 2), (0, 0))
