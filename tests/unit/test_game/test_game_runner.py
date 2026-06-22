"""Tests for the full-game runner: accumulation, bands, resets, re-runs (PRD §6)."""

from __future__ import annotations

from cosmos77_ex06.game.match import Game, SubGame


def _stay(state, role):
    return ("move", "STAY")


def _move(direction):
    def policy(state, role):
        return ("move", direction)

    return policy


def _bad(state, role):
    return ("move", "N")  # (0,0) -> N out of bounds -> IllegalMoveError


def _capture_subgame(cfg):
    return SubGame(cfg, (1, 0), (0, 0), cop_policy=_move("W"), thief_policy=_stay)


def _survival_subgame(cfg):
    return SubGame(cfg, (0, 0), (2, 2), cop_policy=_stay, thief_policy=_stay)


def test_full_game_all_captures_totals(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, num_games=6)
    out = Game(cfg).play(lambda i: _capture_subgame(cfg))
    assert out["valid"] == 6
    assert out["totals"] == {"cop": 120, "thief": 30}  # 6 * (20, 5)


def test_full_game_all_survivals_totals(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, num_games=6, max_moves=2)
    out = Game(cfg).play(lambda i: _survival_subgame(cfg))
    assert out["valid"] == 6
    assert out["totals"] == {"cop": 30, "thief": 60}  # 6 * (5, 10)


def test_full_game_mixed_totals_in_band(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, num_games=6, max_moves=2)
    builders = [_capture_subgame] * 3 + [_survival_subgame] * 3
    out = Game(cfg).play(lambda i: builders[i](cfg))
    assert out["valid"] == 6
    # 3 captures + 3 survivals -> cop 3*20 + 3*5 = 75, thief 3*5 + 3*10 = 45.
    # Each role stays inside its OWN band (cop 30-120, thief 30-60), not a shared
    # 30-90 band (an all-capture game lands cop at 120 -> the shared band is false).
    assert out["totals"] == {"cop": 75, "thief": 45}
    assert 30 <= out["totals"]["cop"] <= 120
    assert 30 <= out["totals"]["thief"] <= 60


def test_barrier_budget_and_set_reset_per_subgame(make_config) -> None:
    # PRD §4 / §6.2: each sub-game starts with a fresh board (barriers cleared)
    # and a reset barrier budget. A barrier placed in sub-game 0 must be absent
    # from sub-game 1, and barriers_used must restart at 0.
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=2)
    built: list[SubGame] = []

    def cop_drops(state, role):
        return ("barrier", (1, 1)) if state.move_number == 0 else ("move", "STAY")

    def make(index: int) -> SubGame:
        policy = cop_drops if index == 0 else _stay
        sub = SubGame(cfg, (0, 0), (2, 2), cop_policy=policy, thief_policy=_stay)
        built.append(sub)
        return sub

    Game(cfg).play(make)
    first, second = built[0], built[1]
    assert (1, 1) in first.state.barriers and first.barriers_used == 1
    # sub-game 1 is a brand-new board: no carried barriers, budget reset to 0.
    assert second.board.barriers == set()
    assert second.state.barriers == []
    assert second.barriers_used == 0


def test_technical_loss_subgame_does_not_count_and_triggers_rerun(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, num_games=2)
    calls = {"n": 0}

    def make(valid_index):  # 2nd attempt fails technically; the rest capture cleanly
        calls["n"] += 1
        if calls["n"] == 2:
            return SubGame(cfg, (0, 0), (2, 2), cop_policy=_bad, thief_policy=_stay)
        return _capture_subgame(cfg)

    out = Game(cfg).play(make)
    assert out["valid"] == 2
    assert out["reruns"] == 1
    assert len(out["results"]) == 2
    assert all(not r.technical_loss for r in out["results"])
