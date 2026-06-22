"""Tests for the game wiring on the SDK (``new_game`` / ``step``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmos77_ex06.game.moves import IllegalMoveError
from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.sdk.sdk import SDK


def test_new_game_builds_state_from_config(config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    state = sdk.new_game()
    assert isinstance(state, GameState)
    assert state.cop_pos == (4, 4)
    assert state.thief_pos == (0, 0)
    assert state.max_moves == 25
    assert state.current_role == "thief"


def test_new_game_records_to_ledger(config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    sdk.new_game()
    assert "new_game" in sdk.ledger()


def test_step_moves_role(config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    state = sdk.new_game(cop_start=(4, 4), thief_start=(0, 0))
    state = sdk.step(state, "thief", ("move", "E"))
    assert state.thief_pos == (1, 0)
    assert state.current_role == "cop"


def test_step_places_barrier(config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    state = sdk.new_game()
    state = sdk.step(state, "cop", ("barrier", (2, 2)))
    assert (2, 2) in state.barriers


def test_step_rejects_illegal_move(config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    state = sdk.new_game(cop_start=(4, 4), thief_start=(0, 0))
    with pytest.raises(IllegalMoveError):
        sdk.step(state, "thief", ("move", "N"))  # (0,0) -> out of bounds
