"""Tests for the sub-game / game drivers and Technical-Loss (PRD §6)."""

from __future__ import annotations

from cosmos77_ex06.game import rules
from cosmos77_ex06.game.match import SubGame, TechnicalLoss


def _stay(state, role):
    return ("move", "STAY")


def _move(direction):
    def policy(state, role):
        return ("move", direction)

    return policy


def _bad(state, role):
    return ("move", "N")  # (0,0) -> N out of bounds -> IllegalMoveError


def test_cop_captures_by_walking_onto_thief(make_config) -> None:
    # thief stays at (0,0); cop starts adjacent and steps W onto it.
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False)
    sub = SubGame(
        cfg, cop_start=(1, 0), thief_start=(0, 0), cop_policy=_move("W"), thief_policy=_stay
    )
    result = sub.run()
    assert result.winner == "cop"
    assert result.state.status == "cop_win"
    assert result.scores == {"cop": 20, "thief": 5}
    assert result.move_count == 0  # captured on the first turn


def test_no_capture_when_thief_steps_away(make_config) -> None:
    # cop chases but thief always keeps distance -> survives to the limit.
    cfg = make_config(grid_size=[5, 5], allow_diagonal=False, max_moves=3)
    sub = SubGame(cfg, cop_start=(0, 0), thief_start=(4, 4), cop_policy=_stay, thief_policy=_stay)
    result = sub.run()
    assert result.winner == "thief"
    assert result.state.status == "thief_win"


def test_thief_survives_at_exactly_max_moves(make_config) -> None:
    # Both stay; never captured. Survival must fire after exactly max_moves turns.
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=4)
    sub = SubGame(cfg, cop_start=(0, 0), thief_start=(2, 2), cop_policy=_stay, thief_policy=_stay)
    result = sub.run()
    assert result.winner == "thief"
    # exactly max_moves turns were played and the reported count matches the log.
    cop_turns = [e for e in result.log if e["role"] == "cop"]
    assert len(cop_turns) == 4
    assert result.move_count == 4
    # the engine's terminal predicate is the PRD-named survival rule on the REAL result.
    assert rules.is_survival(result.state)
    assert result.scores == {"cop": 5, "thief": 10}


def test_thief_stepping_onto_cop_is_not_a_capture(make_config) -> None:
    # PRD §5 subtle detail: capture is ONLY the cop landing on the thief, never
    # the thief stepping onto the cop. The thief moves E onto the stationary
    # cop's cell on turn 0; the cop then moves W AWAY. If the engine wrongly
    # checked capture on the thief's turn it would (incorrectly) end cop_win on
    # turn 0 with the cells momentarily coincident. The correct engine checks
    # only after the cop acts, by when the cop has left -> no capture that turn.
    moves = {"thief": iter(["E"]), "cop": iter(["W"])}

    def thief_policy(state, role):
        return ("move", next(moves["thief"], "STAY"))

    def cop_policy(state, role):
        return ("move", next(moves["cop"], "STAY"))

    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=4)
    sub = SubGame(
        cfg, cop_start=(1, 0), thief_start=(0, 0), cop_policy=cop_policy, thief_policy=thief_policy
    )
    result = sub.run()
    # turn 0: thief (0,0)->E (1,0)==cop's cell (NOT a capture); cop (1,0)->W (0,0).
    # No cop_win was declared on the thief's step-on. The sub-game ran on to the
    # limit because the agents never re-coincided after the cop acted.
    assert result.winner == "thief"
    assert result.state.status == "thief_win"


def test_zero_max_moves_is_immediate_thief_win(make_config) -> None:
    # Robustness guard: max_moves<=0 means the thief wins with zero turns played;
    # the engine must NOT force a turn (which could wrongly yield a capture).
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=0)
    # cop starts adjacent and would capture on a forced turn -> must not happen.
    sub = SubGame(
        cfg, cop_start=(1, 0), thief_start=(0, 0), cop_policy=_move("W"), thief_policy=_stay
    )
    result = sub.run()
    assert result.winner == "thief"
    assert result.move_count == 0
    assert result.log == []


def test_thief_first_then_cop_within_turn(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=2)
    sub = SubGame(cfg, cop_start=(0, 0), thief_start=(2, 2), cop_policy=_stay, thief_policy=_stay)
    sub.run()
    assert [e["role"] for e in sub.log[:2]] == ["thief", "cop"]


def test_cop_can_place_barrier_as_an_action(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False, max_moves=2)

    def cop_drops(state, role):
        if state.move_number == 0:
            return ("barrier", (1, 1))
        return ("move", "STAY")

    sub = SubGame(
        cfg, cop_start=(0, 0), thief_start=(2, 2), cop_policy=cop_drops, thief_policy=_stay
    )
    result = sub.run()
    assert (1, 1) in result.state.barriers
    assert sub.barriers_used == 1


def test_technical_loss_is_voided_and_flagged(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False)
    sub = SubGame(cfg, cop_start=(0, 0), thief_start=(2, 2), cop_policy=_bad, thief_policy=_stay)
    result = sub.run()
    assert result.technical_loss is True
    assert result.winner == "technical_loss"
    assert result.scores == {"cop": 0, "thief": 0}
    assert result.state.status == "technical_loss"
    assert result.move_count == 0


def test_explicit_technical_loss_signal_is_caught(make_config) -> None:
    cfg = make_config(grid_size=[3, 3], allow_diagonal=False)

    def crashing_cop(state, role):
        raise TechnicalLoss("transport timeout")

    sub = SubGame(
        cfg, cop_start=(0, 0), thief_start=(2, 2), cop_policy=_stay, thief_policy=crashing_cop
    )
    result = sub.run()
    assert result.technical_loss is True
