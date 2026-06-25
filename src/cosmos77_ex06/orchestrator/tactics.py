"""Heuristic tactical assist (E9) — a legal pursuit/evasion move for the orchestrator.

The LLM still owns the free natural-language message (E4) and gets this as a HINT; but
when it proposes an illegal move (a common compass-geometry slip — e.g. picking SW from
a corner), the engine falls back to this guaranteed-legal action so the agent advances
competently instead of freezing. It operates on the agent's BELIEF — the opponent's cell
only when it is inside the vision window — with a centre-sweep target when blind, so the
decision stays within partial observability and never reads ground truth for aiming.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.strategy import heuristic


def _target_cell(state: Any, estimate: dict[str, Any] | None) -> tuple[int, int]:
    """The cell the heuristic aims at: the opponent if in view, else the board centre."""
    seen = estimate.get("opponent_cell") if estimate else None
    if seen:
        return (int(seen[0]), int(seen[1]))
    grid = state.grid_size
    return (grid[0] // 2, grid[1] // 2)


def suggest(engine: Any, role: str, estimate: dict[str, Any] | None) -> dict[str, Any]:
    """The heuristic's suggested action for ``role`` (pursue if cop, evade if thief)."""
    state = engine.state
    board = Board(list(state.grid_size), bool(state.allow_diagonal), set(state.barriers))
    target = _target_cell(state, estimate)
    if role == "cop":
        use_barriers = bool(engine.config.get("strategy.use_barriers", default=False))
        left = int(engine.config.get("max_barriers")) - int(state.barriers_used)
        return heuristic.suggest_cop_action(
            target, tuple(state.cop_pos), board, engine.config, left if use_barriers else 0
        )
    return heuristic.suggest_thief_action(target, tuple(state.thief_pos), board, engine.config)


def to_action(role: str, suggestion: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Convert a heuristic suggestion into the ``(tool, args)`` the engine executes."""
    if suggestion.get("action") == "place_barrier":
        cell = suggestion["cell"]
        return "place_barrier", {"role": role, "x": int(cell[0]), "y": int(cell[1])}
    return "apply_move", {"role": role, "direction": str(suggestion["direction"])}


def hint(suggestion: dict[str, Any]) -> str:
    """A short imperative hint for the LLM prompt (E9 suggestion line)."""
    if suggestion.get("action") == "place_barrier":
        return "drop a barrier to cut off the escape"
    return str(suggestion["direction"])
