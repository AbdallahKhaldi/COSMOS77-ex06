"""Autonomous full-game runner (E5, E13) — 6 VALID sub-games, no intervention.

:func:`run_full_game` drives ``num_games`` sub-games end-to-end through the
:class:`GameEngine` against the in-memory local MCP servers. A sub-game that fails
technically (a :class:`TechnicalLoss`, or any transport/orchestration exception
bubbling out of the engine) is VOIDED and RE-RUN — a voided attempt never consumes
a 1-based index and never scores — until exactly ``num_games`` valid sub-games
exist (E13). Per-role totals accumulate over the valid sub-games only, and the
result is assembled into the §9.1 internal-game report dict (config-driven, E8).
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.game.match import TechnicalLoss
from cosmos77_ex06.game.state import SubGameResult
from cosmos77_ex06.orchestrator.local import build_engine
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_MAX_ATTEMPTS_FACTOR = 50


def _sub_game_entry(index: int, result: SubGameResult) -> dict[str, Any]:
    """Build one §2.1 ``sub_games[]`` entry from a valid sub-game result.

    ``index`` is the 1-based, contiguous position over the valid sub-games;
    ``capture`` is derived from the winner (true only when the cop captured).
    """
    return {
        "index": index,
        "winner": result.winner,
        "moves": result.move_count,
        "capture": result.winner == "cop",
        "cop_score": int(result.scores["cop"]),
        "thief_score": int(result.scores["thief"]),
    }


def _is_void(result: SubGameResult) -> bool:
    """True when a sub-game result is a Technical-Loss (voided, E13)."""
    return result.technical_loss or result.winner == "technical_loss"


def build_report(
    config: Config, sub_games: list[dict[str, Any]], totals: dict[str, int]
) -> dict[str, Any]:
    """Assemble the §9.1 internal-game report dict from config + accumulated results."""
    students = [
        {"id": str(s["id"]), "name_en": str(s["name_en"]), "name_he": str(s["name_he"])}
        for s in config.get("students", default=[])
    ]
    return {
        "group_name": str(config.get("group.name")),
        "students": students,
        "github_repo": str(config.get("group.github_repo")),
        "cop_mcp_url": str(config.get("mcp.cop_url")),
        "thief_mcp_url": str(config.get("mcp.thief_url")),
        "timezone": str(config.get("report.timezone")),
        "sub_games": sub_games,
        "totals": {"cop": int(totals["cop"]), "thief": int(totals["thief"])},
    }


async def run_full_game(
    config: Config,
    gatekeeper: Gatekeeper,
    client_factory: Any = None,
    *,
    gui: bool = False,
) -> dict[str, Any]:
    """Run a full autonomous game and return ``{report, transcript, totals, reruns}``.

    Opens the in-memory cop/thief FastMCP clients once and reuses the engine for
    every (valid or voided) sub-game attempt. Technical-Losses are re-run until
    ``num_games`` valid sub-games are recorded (E13); ``client_factory`` injects a
    mock genai client for tests (omit for a live run).
    """
    engine, clients = build_engine(config, gatekeeper, client_factory, gui=gui)
    num_games = int(config.get("num_games"))
    sub_games: list[dict[str, Any]] = []
    totals = {"cop": 0, "thief": 0}
    reruns = 0
    max_attempts = num_games + num_games * _MAX_ATTEMPTS_FACTOR
    async with clients["cop"], clients["thief"]:
        attempts = 0
        while len(sub_games) < num_games and attempts < max_attempts:
            attempts += 1
            index = len(sub_games) + 1
            mark = engine.transcript.mark()
            try:
                result = await engine.play_sub_game(index)
            except Exception as exc:  # noqa: BLE001 - any orchestration failure voids + reruns (E13)
                engine.transcript.truncate(mark)
                engine.transcript.note_void(index, f"{type(exc).__name__}: {exc}")
                reruns += 1
                continue
            if _is_void(result):
                engine.transcript.truncate(mark)
                engine.transcript.note_void(index, "technical_loss")
                reruns += 1
                continue
            sub_games.append(_sub_game_entry(index, result))
            totals = {k: totals[k] + int(result.scores[k]) for k in totals}
    if len(sub_games) != num_games:
        raise TechnicalLoss(
            f"only {len(sub_games)}/{num_games} valid sub-games after {attempts} attempts"
        )
    return {
        "report": build_report(config, sub_games, totals),
        "transcript": engine.transcript.to_list(),
        "totals": totals,
        "reruns": reruns,
    }
