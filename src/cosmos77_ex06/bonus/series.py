"""Orchestrate the inter-group role-swap series over four cloud MCP URLs (E12, E13).

The bonus is a single 6-sub-game game played as a symmetric **role swap**:

    sub-games 1-3 : OUR (group_1) cop server  vs  THEIR (group_2) thief server
    sub-games 4-6 : THEIR (group_2) cop server vs  OUR  (group_1) thief server

For each sub-game the orchestrator's two FastMCP ``Client``s connect to a cop server
and a thief server that belong to DIFFERENT groups (Server/Client separation, E3,
preserved across the group boundary). We do NOT reimplement the turn loop — each
sub-game is delegated to the existing :class:`GameEngine`. A sub-game that fails
technically against a foreign server is VOIDED and RE-RUN until 6 valid sub-games
exist (E13). Everything (URLs, tokens, orientation) comes from the ``bonus`` config
block (Rule 4); the engine factory is injectable so the whole series is mockable
with no live cloud calls in tests.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from cosmos77_ex06.bonus.cloud import build_cloud_engine
from cosmos77_ex06.game.match import TechnicalLoss
from cosmos77_ex06.game.state import SubGameResult
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

#: How many of the 6 sub-games are played with OUR (group_1) cop / THEIR thief.
_OUR_COP_SUB_GAMES = 3
#: A generous rerun budget so a flaky foreign server still yields 6 valid sub-games.
_MAX_ATTEMPTS_FACTOR = 50

EngineFactory = Callable[..., tuple[Any, dict[str, Any]]]


def role_map(index: int) -> dict[str, str]:
    """Return the cop/thief group slots + the four-URL config keys for a 1-based ``index``.

    Sub-games 1-3 wire OUR cop (``group_1_cop``) against THEIR thief
    (``group_2_thief``); sub-games 4-6 swap to THEIR cop (``group_2_cop``) against
    OUR thief (``group_1_thief``). Used both to wire the clients and to label the
    ``cop_group``/``thief_group`` slots in the report.
    """
    if index <= _OUR_COP_SUB_GAMES:
        return {"cop_group": "group_1", "thief_group": "group_2"}
    return {"cop_group": "group_2", "thief_group": "group_1"}


def _url_keys(roles: dict[str, str]) -> dict[str, str]:
    """Map cop/thief group slots to their ``bonus.mcp.*`` config keys."""
    return {
        "cop": f"bonus.mcp.{roles['cop_group']}_cop",
        "thief": f"bonus.mcp.{roles['thief_group']}_thief",
    }


def _sub_game_entry(index: int, roles: dict[str, str], result: SubGameResult) -> dict[str, Any]:
    """Convert a :class:`SubGameResult` into one §9.2 ``sub_games[]`` entry."""
    return {
        "index": index,
        "cop_group": roles["cop_group"],
        "thief_group": roles["thief_group"],
        "result": "capture" if result.winner == "cop" else "survival",
        "moves": int(result.move_count),
        "cop_score": int(result.scores["cop"]),
        "thief_score": int(result.scores["thief"]),
    }


def _is_void(result: SubGameResult) -> bool:
    """True when a sub-game result is a Technical-Loss (voided, E13)."""
    return result.technical_loss or result.winner == "technical_loss"


async def _play_one(
    config: Config,
    gatekeeper: Gatekeeper,
    index: int,
    factory: EngineFactory,
    client_factory: Any,
) -> SubGameResult:
    """Wire a cross-group engine for ``index`` and play exactly one sub-game."""
    roles = role_map(index)
    keys = _url_keys(roles)
    engine, clients = factory(
        config,
        gatekeeper,
        cop_url=str(config.get(keys["cop"])),
        thief_url=str(config.get(keys["thief"])),
        client_factory=client_factory,
    )
    async with clients["cop"], clients["thief"]:
        return await engine.play_sub_game(index)


async def run_series(
    config: Config,
    gatekeeper: Gatekeeper,
    *,
    client_factory: Any = None,
    engine_factory: EngineFactory | None = None,
) -> dict[str, Any]:
    """Run the 6-sub-game role-swap series; return ``{sub_games, role_map, reruns}``.

    Delegates every sub-game to :class:`GameEngine` (no loop re-implementation);
    voids + re-runs technical failures until 6 valid sub-games exist (E13). The
    returned ``sub_games`` list (length 6, 1-based) feeds ``bonus.report.build_report``.
    ``engine_factory`` defaults to the live cloud factory (resolved at call time so it
    is monkeypatchable); ``client_factory`` is injected so tests do no live calls.
    """
    factory = engine_factory or build_cloud_engine
    num_games = _OUR_COP_SUB_GAMES * 2
    sub_games: list[dict[str, Any]] = []
    reruns = attempts = 0
    max_attempts = num_games + num_games * _MAX_ATTEMPTS_FACTOR
    while len(sub_games) < num_games and attempts < max_attempts:
        attempts += 1
        index = len(sub_games) + 1
        roles = role_map(index)
        try:
            result = await _play_one(config, gatekeeper, index, factory, client_factory)
        except Exception:  # noqa: BLE001 - any foreign-server failure voids + reruns (E13)
            reruns += 1
            continue
        if _is_void(result):
            reruns += 1
            continue
        sub_games.append(_sub_game_entry(index, roles, result))
    if len(sub_games) != num_games:
        raise TechnicalLoss(
            f"only {len(sub_games)}/{num_games} valid bonus sub-games after {attempts} attempts"
        )
    return {
        "sub_games": sub_games,
        "role_map": {i: role_map(i) for i in range(1, num_games + 1)},
        "reruns": reruns,
    }


def run_series_sync(
    config: Config,
    gatekeeper: Gatekeeper,
    runner: Callable[..., Awaitable[dict[str, Any]]] = run_series,
    **kwargs: Any,
) -> dict[str, Any]:
    """Synchronous wrapper around :func:`run_series` for the SDK/CLI entry point."""
    import asyncio

    return asyncio.run(runner(config, gatekeeper, **kwargs))
