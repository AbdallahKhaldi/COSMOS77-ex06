"""Terminal conditions, sub-game result, and the config-driven scoring (PRD §5-§7).

Capture = the cop lands *exactly* on the thief's cell (tested after the cop's
move). Survival = the sub-game reaches ``max_moves`` with no capture (thief wins).
There is no draw. The scoring mapping is a single config lookup so the spec's
numbers are a one-line YAML edit (E8).
"""

from __future__ import annotations

from cosmos77_ex06.game.state import GameState
from cosmos77_ex06.shared.config import Config

COP_WIN = "cop_win"
THIEF_WIN = "thief_win"


def is_capture(state: GameState) -> bool:
    """``True`` iff the cop and thief occupy the same cell."""
    return tuple(state.cop_pos) == tuple(state.thief_pos)


def is_survival(state: GameState) -> bool:
    """``True`` iff the move limit is reached with no capture."""
    return not is_capture(state) and state.move_number >= state.max_moves


def subgame_result(state: GameState) -> str:
    """Return ``"cop_win"`` (capture) or ``"thief_win"`` (survival)."""
    return COP_WIN if is_capture(state) else THIEF_WIN


def score_for(result: str, config: Config) -> dict[str, int]:
    """Return ``{"cop": int, "thief": int}`` for a sub-game ``result`` (PRD §7)."""
    if result == COP_WIN:
        return {
            "cop": int(config.get("scoring.cop_win")),
            "thief": int(config.get("scoring.thief_loss")),
        }
    return {
        "cop": int(config.get("scoring.cop_loss")),
        "thief": int(config.get("scoring.thief_win")),
    }


def next_role(current_role: str, turn_order: list[str]) -> str:
    """Return the role that acts after ``current_role`` within the turn order."""
    idx = turn_order.index(current_role)
    return turn_order[(idx + 1) % len(turn_order)]
