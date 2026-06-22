"""Sub-game / game drivers and the Technical-Loss signal (PRD §6).

:class:`SubGame` drives one episode (thief-then-cop turns; capture checked after
the cop moves, then the move limit) recording a per-move log. :class:`Game` runs
``num_games`` sub-games, accumulating per-role totals. A :class:`TechnicalLoss`
voids a sub-game and flags it for re-run. An action is ``("move", direction)`` or
``("barrier", cell)``; a policy maps ``(state, role)`` to one action."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cosmos77_ex06.game import rules
from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import IllegalMoveError, apply_move, place_barrier
from cosmos77_ex06.game.state import Cell, GameState, SubGameResult
from cosmos77_ex06.shared.config import Config

Action = tuple[str, Any]
Policy = Callable[[GameState, str], Action]


class TechnicalLoss(Exception):  # noqa: N818 — spec-mandated name (PRD §6.4)
    """Unrecoverable orchestration/transport failure — voids the sub-game (E13)."""


class SubGame:
    """Drives one pursuit episode to capture or the move limit."""

    def __init__(
        self,
        config: Config,
        cop_start: Cell,
        thief_start: Cell,
        cop_policy: Policy,
        thief_policy: Policy,
    ) -> None:
        self.config = config
        self.max_moves = int(config.get("max_moves"))
        self.max_barriers = int(config.get("max_barriers"))
        self.turn_order = list(config.get("turn_order"))
        self.board = Board.from_config(config)
        self.barriers_used = 0
        self.policies: dict[str, Policy] = {"cop": cop_policy, "thief": thief_policy}
        self.state = GameState(
            grid_size=list(config.get("grid_size")),
            cop_pos=tuple(cop_start),
            thief_pos=tuple(thief_start),
            max_moves=self.max_moves,
            allow_diagonal=bool(config.get("allow_diagonal")),
            turn_order=self.turn_order,
            current_role=self.turn_order[0],
        )

    def _act(self, role: str) -> None:
        """Apply ``role``'s policy action to the board and state."""
        st = self.state
        action, payload = self.policies[role](st, role)
        pos = st.cop_pos if role == "cop" else st.thief_pos
        if action == "barrier":
            args = (self.board, self.barriers_used, self.max_barriers, st.cop_pos, st.thief_pos)
            self.barriers_used = place_barrier(role, tuple(payload), *args)
            new_pos = pos
            st.barriers = sorted(self.board.barriers)
            st.barriers_used = self.barriers_used
        else:
            new_pos = apply_move(pos, payload, self.board)
            setattr(st, "cop_pos" if role == "cop" else "thief_pos", new_pos)
        st.current_role = rules.next_role(role, self.turn_order)
        st.add_message(st.move_number, role, f"{action}:{payload}->{new_pos}")
        keys = ("turn", "role", "action", "payload", "pos")
        rec = (st.move_number, role, action, payload, new_pos)
        self.log.append(dict(zip(keys, rec, strict=True)))

    def run(self) -> SubGameResult:
        """Run the turn loop; return the result. Raises nothing — TL is captured."""
        self.log = []
        try:
            return self._loop()
        except (IllegalMoveError, TechnicalLoss):
            self.state.status = "technical_loss"
            zero = {"cop": 0, "thief": 0}
            return SubGameResult(
                "technical_loss", zero, self.state.move_number, self.state, self.log, True
            )

    def _loop(self) -> SubGameResult:
        if self.max_moves <= 0:
            return self._finish(rules.THIEF_WIN)
        while True:
            for role in self.turn_order:
                self._act(role)
                if role == "cop" and rules.is_capture(self.state):
                    return self._finish(rules.COP_WIN)
            self.state.move_number += 1
            if rules.is_survival(self.state):
                return self._finish(rules.THIEF_WIN)

    def _finish(self, result: str) -> SubGameResult:
        """Stamp the status/scores and return the terminal result."""
        self.state.status = result
        self.state.scores = scores = rules.score_for(result, self.config)
        winner = "cop" if result == rules.COP_WIN else "thief"
        return SubGameResult(winner, scores, self.state.move_number, self.state, self.log)


class Game:
    """Runs ``num_games`` valid sub-games and accumulates per-role totals (PRD §6.3)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.num_games = int(config.get("num_games"))
        self.totals: dict[str, int] = {"cop": 0, "thief": 0}
        self.results: list[SubGameResult] = []

    def play(
        self, make_subgame: Callable[[int], SubGame], max_attempts: int = 100
    ) -> dict[str, Any]:
        """Run sub-games (re-running Technical-Losses) until ``num_games`` are valid."""
        reruns = attempts = 0
        while len(self.results) < self.num_games and attempts < max_attempts:
            attempts += 1
            result = make_subgame(len(self.results)).run()
            if result.technical_loss:
                reruns += 1
                continue
            self.results.append(result)
            self.totals["cop"] += result.scores["cop"]
            self.totals["thief"] += result.scores["thief"]
        valid = len(self.results)
        return {
            "totals": dict(self.totals),
            "valid": valid,
            "reruns": reruns,
            "results": self.results,
        }
