"""Build a fresh standalone :class:`GameState` for a runnable MCP server.

In the full pipeline (Phase 4) the orchestrator owns the canonical state and a
server is bound to it. For a server run standalone (``python -m ...cop_server``)
this builds a default state from config — opposite-corner starts, the thief first
— so the process is independently runnable and connect-testable.
"""

from __future__ import annotations

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.shared.config import Config


def make_state(config: Config) -> GameState:
    """Return a fresh sub-game :class:`GameState` from ``config`` defaults."""
    grid = list(config.get("grid_size"))
    turn_order = list(config.get("turn_order"))
    return GameState(
        grid_size=grid,
        cop_pos=(grid[0] - 1, grid[1] - 1),
        thief_pos=(0, 0),
        max_moves=int(config.get("max_moves")),
        allow_diagonal=bool(config.get("allow_diagonal")),
        turn_order=turn_order,
        current_role=turn_order[0],
    )
