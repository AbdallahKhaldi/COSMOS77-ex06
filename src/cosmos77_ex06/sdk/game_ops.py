"""Low-level game primitives for the SDK (``new_game`` / ``step``) — split out (Rule 1/3).

Mixed into :class:`~cosmos77_ex06.sdk.sdk.SDK`; expects ``config`` + ``gatekeeper`` on the
host. Holds the GameState construction + single-step application so ``sdk.py`` stays small.
"""

from __future__ import annotations

from typing import Any


class GameOpsMixin:
    """GameState construction + one-step application, mixed into :class:`SDK`."""

    config: Any
    gatekeeper: Any

    def new_game(self, *, cop_start: Any = None, thief_start: Any = None) -> Any:
        """Build a fresh :class:`GameState` from config (opposite corners; Phase 2)."""
        from cosmos77_ex06.game.state import GameState

        grid = list(self.config.get("grid_size"))
        cop = tuple(cop_start) if cop_start is not None else (grid[0] - 1, grid[1] - 1)
        thief = tuple(thief_start) if thief_start is not None else (0, 0)
        turn_order = list(self.config.get("turn_order"))
        state = GameState(
            grid_size=grid,
            cop_pos=cop,
            thief_pos=thief,
            max_moves=int(self.config.get("max_moves")),
            allow_diagonal=bool(self.config.get("allow_diagonal")),
            turn_order=turn_order,
            current_role=turn_order[0],
        )
        self.gatekeeper.record("new_game", {"state": state.to_dict()})
        return state

    def step(self, state: Any, role: str, action: Any) -> Any:
        """Apply one ``("move", dir)`` / ``("barrier", cell)`` for ``role`` (illegal -> raises)."""
        from cosmos77_ex06.game import rules
        from cosmos77_ex06.game.board import Board
        from cosmos77_ex06.game.moves import apply_move, place_barrier

        kind, payload = action
        board = Board(state.grid_size, state.allow_diagonal, set(state.barriers))
        pos = state.cop_pos if role == "cop" else state.thief_pos
        if kind == "barrier":
            cap = int(self.config.get("max_barriers"))
            args = (board, state.barriers_used, cap, state.cop_pos, state.thief_pos)
            state.barriers_used = place_barrier(role, tuple(payload), *args)
            state.barriers = sorted(board.barriers)
        else:
            new_pos = apply_move(pos, payload, board)
            if role == "cop":
                state.cop_pos = new_pos
            else:
                state.thief_pos = new_pos
        state.current_role = rules.next_role(role, list(state.turn_order))
        return state
