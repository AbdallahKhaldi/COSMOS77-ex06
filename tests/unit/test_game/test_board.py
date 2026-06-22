"""Tests for the config-driven :class:`Board` (PRD §2-§3)."""

from __future__ import annotations

from cosmos77_ex06.game.board import Board


def test_dimensions_and_cells_from_config(make_config) -> None:
    board = Board.from_config(make_config(grid_size=[3, 2]))
    assert (board.width, board.height) == (3, 2)
    assert board.cells == [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]


def test_in_bounds_non_square() -> None:
    board = Board([4, 3], allow_diagonal=True)
    assert board.in_bounds((3, 2))
    assert not board.in_bounds((4, 2))
    assert not board.in_bounds((3, 3))
    assert not board.in_bounds((-1, 0))


def test_barrier_is_blocked_and_not_passable() -> None:
    board = Board([3, 3], allow_diagonal=True, barriers={(1, 1)})
    assert board.is_blocked((1, 1))
    assert not board.is_passable((1, 1))
    assert board.is_passable((0, 0))


def test_neighbors_8_connected_when_diagonal() -> None:
    board = Board([3, 3], allow_diagonal=True)
    assert len(board.neighbors((1, 1))) == 8


def test_neighbors_4_connected_when_no_diagonal() -> None:
    board = Board([3, 3], allow_diagonal=False)
    nbrs = board.neighbors((1, 1))
    assert len(nbrs) == 4
    assert (0, 0) not in nbrs


def test_neighbors_corner_is_pruned_by_edges() -> None:
    board = Board([3, 3], allow_diagonal=True)
    # top-left corner: only E, S, SE are in bounds
    assert sorted(board.neighbors((0, 0))) == [(0, 1), (1, 0), (1, 1)]


def test_diagonal_no_corner_cutting_rule() -> None:
    # destination passable even if both orthogonal neighbours are barriers (PRD §3)
    board = Board([3, 3], allow_diagonal=True, barriers={(1, 0), (0, 1)})
    assert (1, 1) in board.neighbors((0, 0))


def test_barrier_blocks_a_neighbor() -> None:
    board = Board([3, 3], allow_diagonal=False, barriers={(1, 0)})
    assert (1, 0) not in board.neighbors((0, 0))
