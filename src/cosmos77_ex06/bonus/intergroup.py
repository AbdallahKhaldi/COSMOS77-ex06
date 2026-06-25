"""Cross-group sub-game orchestrator — OUR engine drives a game vs NajAmjad (E12).

We own the authoritative 5x5 board under their rules (THIEF moves first; capture = the cop
landing on the thief AFTER the cop's move; turn-limit with no capture => thief wins; barriers
OFF / variant 0 for a clean, reproducible series). Each turn we build their observation for the
active role and source its move from the right place: a :class:`RemoteMoveSource` for NajAmjad's
side, our deterministic heuristic for ours. Produces a sub_games entry + the K3 SHA-256 digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cosmos77_ex06.bonus import prose
from cosmos77_ex06.bonus.remote import RemoteMoveSource
from cosmos77_ex06.game.board import Board
from cosmos77_ex06.game.moves import IllegalMoveError, apply_move
from cosmos77_ex06.shared.config import Config

TURN_ORDER = ("thief", "cop")
FIXED_OPENING = {"cop": (4, 4), "thief": (0, 0)}


def _observation(role: str, cop: tuple, thief: tuple, left: int, turn: int, grid: list) -> dict:
    """NajAmjad's observation for the active role (their [row, col] convention, variant 0)."""
    return {
        "role": role,
        "grid": list(grid),
        "cop": prose.to_obs_cell(cop),
        "thief": prose.to_obs_cell(thief),
        "barriers": [],
        "barriers_left": int(left),
        "variant": 0,
        "turn": int(turn),
    }


def _our_direction(role: str, cop: tuple, thief: tuple, board: Board, config: Config) -> str:
    """Our deterministic heuristic move for OUR side (full-obs — we own the board)."""
    from cosmos77_ex06.strategy import heuristic

    if role == "cop":
        return heuristic.suggest_cop_action(thief, cop, board, config, 0)["direction"]
    return heuristic.suggest_thief_action(cop, thief, board, config)["direction"]


def digest(sub_games: list[dict[str, Any]]) -> str:
    """The K3 agreement digest: SHA-256 over the canonical (sorted, compact) sub_games array."""
    blob = json.dumps(sub_games, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _scores(config: Config, winner: str) -> dict[str, int]:
    """Per-role scores for ``winner`` from config (Rule 4 — never hardcoded)."""
    if winner == "cop":
        return {
            "cop": int(config.get("scoring.cop_win")),
            "thief": int(config.get("scoring.thief_loss")),
        }
    return {
        "cop": int(config.get("scoring.cop_loss")),
        "thief": int(config.get("scoring.thief_win")),
    }


async def play_sub_game(
    config: Config,
    index: int,
    our_role: str,
    opponent: RemoteMoveSource,
    *,
    opening: dict[str, tuple] | None = None,
    max_moves: int = 25,
    on_event: Any = None,
) -> dict[str, Any]:
    """Drive ONE sub-game vs NajAmjad; return a sub_games entry. ``our_role`` is the side WE play."""
    grid = list(config.get("grid_size", default=[5, 5]))
    board = Board(grid, allow_diagonal=True)
    start = opening or FIXED_OPENING
    cop, thief = tuple(start["cop"]), tuple(start["thief"])
    moves: list[dict[str, Any]] = []
    winner = "thief"
    done = False
    for turn in range(max_moves):
        for role in TURN_ORDER:
            if role == our_role:
                direction = _our_direction(role, cop, thief, board, config)
                line = prose.format_move(role, "MOVE", direction)
            else:
                line = await opponent.request_move(_observation(role, cop, thief, 5, turn, grid))
                _, direction = prose.parse_move(line)
            pos = cop if role == "cop" else thief
            try:
                new = apply_move(pos, direction, board)
            except IllegalMoveError:
                new, direction = (
                    pos,
                    "STAY",
                )  # foreign illegal move -> HOLD (would void the real series)
            cop, thief = (new, thief) if role == "cop" else (cop, new)
            moves.append(
                {
                    "turn": turn,
                    "role": role,
                    "dir": direction,
                    "cop": list(cop),
                    "thief": list(thief),
                }
            )
            if on_event:
                on_event(
                    {
                        "turn": turn,
                        "role": role,
                        "prose": line,
                        "cop": list(cop),
                        "thief": list(thief),
                    }
                )
            if role == "cop" and cop == thief:
                winner, done = "cop", True
                break
        if done:
            break
    return {
        "index": index,
        "our_role": our_role,
        "opening": {"cop": list(start["cop"]), "thief": list(start["thief"])},
        "moves": moves,
        "winner": winner,
        "scores": _scores(config, winner),
    }
