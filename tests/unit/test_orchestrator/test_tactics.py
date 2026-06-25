"""orchestrator.tactics — the heuristic pursuit/evasion assist (E9) the engine falls back to."""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.orchestrator import tactics


class _State:
    def __init__(
        self,
        grid: tuple[int, int] = (5, 5),
        cop: tuple[int, int] = (4, 4),
        thief: tuple[int, int] = (0, 0),
    ) -> None:
        self.grid_size = list(grid)
        self.allow_diagonal = True
        self.cop_pos = cop
        self.thief_pos = thief
        self.barriers: set[tuple[int, int]] = set()
        self.barriers_used = 0


class _Cfg:
    def get(self, key: str, default: Any = None) -> Any:
        return 5 if key == "max_barriers" else default


class _Engine:
    def __init__(self, state: _State) -> None:
        self.state = state
        self.config = _Cfg()


def test_to_action_move() -> None:
    assert tactics.to_action("cop", {"action": "move", "direction": "NW"}) == (
        "apply_move",
        {"role": "cop", "direction": "NW"},
    )


def test_to_action_barrier() -> None:
    assert tactics.to_action("cop", {"action": "place_barrier", "cell": (2, 3)}) == (
        "place_barrier",
        {"role": "cop", "x": 2, "y": 3},
    )


def test_target_is_opponent_when_seen() -> None:
    assert tactics._target_cell(_State(), {"opponent_cell": [1, 2]}) == (1, 2)  # noqa: SLF001


def test_target_is_board_centre_when_blind() -> None:
    assert tactics._target_cell(_State((5, 5)), {"opponent_cell": None}) == (2, 2)  # noqa: SLF001


def test_cop_pursues_toward_centre_when_blind() -> None:
    """The frozen-cop fix: from the (4,4) corner the legal step toward centre is NW, not SW."""
    sug = tactics.suggest(_Engine(_State()), "cop", {"opponent_cell": None})
    assert sug["action"] == "move" and sug["direction"] == "NW"


def test_thief_evades_off_its_corner() -> None:
    eng = _Engine(_State(cop=(2, 2), thief=(0, 0)))
    sug = tactics.suggest(eng, "thief", {"opponent_cell": [2, 2]})
    assert sug["action"] == "move" and sug["direction"] != "STAY"
