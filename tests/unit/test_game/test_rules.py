"""Tests for terminal conditions and the config-driven scoring (PRD §5-§7)."""

from __future__ import annotations

from cosmos77_ex06.game import rules
from cosmos77_ex06.game.state import GameState


def _state(make_config, cop, thief, move_number=0) -> GameState:
    cfg = make_config()
    return GameState(
        grid_size=[5, 5],
        cop_pos=cop,
        thief_pos=thief,
        max_moves=int(cfg.get("max_moves")),
        allow_diagonal=True,
        turn_order=["thief", "cop"],
        move_number=move_number,
    )


def test_is_capture_only_when_same_cell(make_config) -> None:
    assert rules.is_capture(_state(make_config, (2, 2), (2, 2)))
    assert not rules.is_capture(_state(make_config, (2, 2), (2, 3)))


def test_is_survival_at_limit_without_capture(make_config) -> None:
    st = _state(make_config, (2, 2), (4, 4), move_number=25)
    assert rules.is_survival(st)


def test_capture_overrides_survival(make_config) -> None:
    st = _state(make_config, (2, 2), (2, 2), move_number=25)
    assert not rules.is_survival(st)
    assert rules.is_capture(st)


def test_subgame_result_capture(make_config) -> None:
    assert rules.subgame_result(_state(make_config, (1, 1), (1, 1))) == rules.COP_WIN


def test_subgame_result_survival(make_config) -> None:
    st = _state(make_config, (1, 1), (4, 4), move_number=25)
    assert rules.subgame_result(st) == rules.THIEF_WIN


def test_score_for_cop_win_matches_table(make_config) -> None:
    assert rules.score_for(rules.COP_WIN, make_config()) == {"cop": 20, "thief": 5}


def test_score_for_thief_win_matches_table(make_config) -> None:
    assert rules.score_for(rules.THIEF_WIN, make_config()) == {"cop": 5, "thief": 10}


def test_score_for_reads_config_not_hardcoded(make_config) -> None:
    cfg = make_config(scoring={"cop_win": 99, "thief_win": 7, "cop_loss": 3, "thief_loss": 1})
    assert rules.score_for(rules.COP_WIN, cfg) == {"cop": 99, "thief": 1}
    assert rules.score_for(rules.THIEF_WIN, cfg) == {"cop": 3, "thief": 7}


def test_next_role_cycles_thief_then_cop() -> None:
    order = ["thief", "cop"]
    assert rules.next_role("thief", order) == "cop"
    assert rules.next_role("cop", order) == "thief"
