"""Our side of the request_move contract — answer NajAmjad's move oracle deterministically (E12).

Given their observation ``{role, grid, cop, thief, ...}``, run OUR deterministic heuristic for that
role and return ``"[INTENT: MOVE] ... <compass>"`` in their exact prose contract. This is the brain
behind the ``request_move`` tool we expose so their orchestrator can call us (the same contract we
call them with). No LLM — the heuristic is pure logic, so Server/Client separation is preserved and
the move is a deterministic function of the observation (seeded replays agree -> hashes match).
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus import prose
from cosmos77_ex06.game.board import Board
from cosmos77_ex06.shared.config import Config


def decide(observation: dict[str, Any], config: Config) -> str:
    """Return OUR move for ``observation`` as one ``[INTENT: ...]`` prose line (deterministic).

    The cop minimizes distance to the thief; the thief runs the 1-ply maximin evade. Barriers
    stay off (variant 0). Never enters the opponent's cell on the thief side (capture-safe).
    """
    from cosmos77_ex06.strategy import heuristic

    role = str(observation["role"])
    cop = prose.from_obs_cell(observation["cop"])
    thief = prose.from_obs_cell(observation["thief"])
    grid = list(observation.get("grid") or config.get("grid_size", default=[5, 5]))
    board = Board(grid, allow_diagonal=True)
    if role == "cop":
        direction = heuristic.suggest_cop_action(thief, cop, board, config, 0)["direction"]
    else:
        direction = heuristic.suggest_thief_action(cop, thief, board, config)["direction"]
    return prose.format_move(role, "MOVE", str(direction))
