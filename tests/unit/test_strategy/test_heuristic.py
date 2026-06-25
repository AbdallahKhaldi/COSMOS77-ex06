"""Heuristic policy tests: cop reduces, thief increases distance to the estimate (E9)."""

from __future__ import annotations

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import apply_move
from cosmos77_ex06.strategy import heuristic
from cosmos77_ex06.strategy.heuristic import chebyshev, distance, manhattan


def test_distance_metrics() -> None:
    assert manhattan((0, 0), (2, 3)) == 5
    assert chebyshev((0, 0), (2, 3)) == 3
    assert distance((0, 0), (2, 3), allow_diagonal=True) == 3  # Chebyshev
    assert distance((0, 0), (2, 3), allow_diagonal=False) == 5  # Manhattan


def test_cop_move_reduces_distance_to_estimate(config) -> None:
    board = Board.from_config(config)
    self_pos, est = (0, 0), (4, 4)
    before = distance(self_pos, est, board.allow_diagonal)
    action = heuristic.suggest_cop_action(est, self_pos, board, config, barriers_left=0)
    assert action["action"] == "move"
    new_pos = apply_move(self_pos, action["direction"], board)
    assert distance(new_pos, est, board.allow_diagonal) < before


def test_thief_move_never_approaches_or_enters_the_cop(config) -> None:
    board = Board.from_config(config)
    self_pos, est = (2, 2), (0, 0)
    before = distance(self_pos, est, board.allow_diagonal)
    action = heuristic.suggest_thief_action(est, self_pos, board, config)
    assert action["action"] == "move"
    new_pos = apply_move(self_pos, action["direction"], board)
    # The optimal evader never steps toward (or onto) the cop. It may KEEP distance rather than
    # flee into a corner: maximal distance is a trap, maximal survival is not.
    assert new_pos != est
    assert distance(new_pos, est, board.allow_diagonal) >= before


def test_manhattan_metric_used_when_diagonals_off(make_config) -> None:
    config = make_config(allow_diagonal=False)
    board = Board.from_config(config)
    action = heuristic.suggest_cop_action((4, 0), (0, 0), board, config, barriers_left=0)
    # No diagonals: the cop must step orthogonally toward the estimate (eastward).
    assert action == {"action": "move", "direction": "E"}


def test_thief_prefers_open_space_on_distance_ties(config) -> None:
    board = Board.from_config(config)
    # Thief in the centre, cop estimate also centre-ish: multiple equidistant moves;
    # the open-space tie-break must pick a cell that stays fully connected (8 neighbours).
    action = heuristic.suggest_thief_action((2, 2), (2, 2), board, config)
    new_pos = apply_move((2, 2), action["direction"], board)
    assert len(board.neighbors(new_pos)) == 8  # an interior, maximally-open cell


def test_cop_places_barrier_when_adjacent_with_budget(config) -> None:
    board = Board.from_config(config)
    # Cop at (1,1), estimated thief at (2,1): adjacent (Chebyshev 1), budget available.
    action = heuristic.suggest_cop_action((2, 1), (1, 1), board, config, barriers_left=3)
    assert action["action"] == "place_barrier"
    cell = action["cell"]
    assert cell in board.neighbors((2, 1)) and cell != (1, 1)


def test_cop_does_not_place_barrier_without_budget(config) -> None:
    board = Board.from_config(config)
    action = heuristic.suggest_cop_action((2, 1), (1, 1), board, config, barriers_left=0)
    assert action["action"] == "move"


def test_cop_does_not_place_barrier_when_far(config) -> None:
    board = Board.from_config(config)
    action = heuristic.suggest_cop_action((4, 4), (0, 0), board, config, barriers_left=5)
    assert action["action"] == "move"


def test_cop_skips_barrier_when_one_escape_left(make_config) -> None:
    config = make_config(allow_diagonal=False)
    board = Board.from_config(config)
    # Estimate in the corner (0,0): orthogonal escapes are (1,0) and (0,1). The cop
    # sits on (1,0) (adjacent), so only ONE escape remains — a barrier is not worth it.
    action = heuristic.suggest_cop_action((0, 0), (1, 0), board, config, barriers_left=5)
    assert action["action"] == "move"


def test_cop_stays_when_walled_in(make_config) -> None:
    config = make_config(allow_diagonal=False)
    board = Board(grid_size=[3, 3], allow_diagonal=False, barriers={(0, 1), (1, 0)})
    # Cop boxed into the corner (0,0); only STAY is legal.
    action = heuristic.suggest_cop_action((2, 2), (0, 0), board, config, barriers_left=0)
    assert action == {"action": "move", "direction": "STAY"}


def test_thief_stays_when_walled_in(config) -> None:
    # Thief boxed into the corner (0,0); only STAY is legal.
    board = Board(grid_size=[3, 3], allow_diagonal=False, barriers={(0, 1), (1, 0)})
    action = heuristic.suggest_thief_action((2, 2), (0, 0), board, config)
    assert action == {"action": "move", "direction": "STAY"}
