"""Cross-team / solo game logic for the live web console — kept out of sdk.py (Rule 1/2).

* :func:`cross_game` — N live games over a cop URL + a thief URL (the multiplayer match).
* :func:`local_game` — N live games of OUR cop vs OUR thief on the freeze-proof local
  in-memory engine (House Match). The bonus role-swap series lives in :mod:`web.series`.

Both thread an optional per-turn ``on_event`` hook into the :class:`GameEngine`; the
multiplayer token is passed at RUNTIME (never written to config; Rule 9). No LLM here.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus.cloud import build_cloud_engine
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


async def cross_game(
    config: Config,
    gatekeeper: Gatekeeper,
    *,
    cop_url: str,
    thief_url: str,
    token: str | None,
    on_event: Any = None,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Run ``num_games`` live games (cop_url cop vs thief_url thief); stream + return the tally."""
    engine, clients = build_cloud_engine(
        config,
        gatekeeper,
        cop_url=cop_url,
        thief_url=thief_url,
        token=token,
        on_event=on_event,
        client_factory=client_factory,
    )
    return await _play_games(engine, clients, int(config.get("num_games", default=1)), on_event)


async def _play_games(
    engine: Any, clients: dict[str, Any], num: int, on_event: Any
) -> dict[str, Any]:
    """Run ``num`` sub-games on an opened engine; accumulate totals + emit ``sub_game_end``."""
    totals = {"cop": 0, "thief": 0}
    games: list[dict[str, Any]] = []
    async with clients["cop"], clients["thief"]:
        for i in range(1, num + 1):
            r = await engine.play_sub_game(i)
            totals["cop"] += int(r.scores["cop"])
            totals["thief"] += int(r.scores["thief"])
            game = {
                "sub_game": i,
                "winner": r.winner,
                "cop_score": int(r.scores["cop"]),
                "thief_score": int(r.scores["thief"]),
                "moves": int(r.move_count),
            }
            games.append(game)
            if on_event is not None:
                on_event({"type": "sub_game_end", **game, "totals": dict(totals)})
    return _tally(totals, games, num)


def _tally(totals: dict[str, int], games: list[dict[str, Any]], num: int) -> dict[str, Any]:
    """Build the final match result from cumulative scores (cop takes a tie on the win edge)."""
    cop, thief = totals["cop"], totals["thief"]
    win = "cop" if cop > thief else "thief" if thief > cop else "tie"
    return {"winner": win, "cop_score": cop, "thief_score": thief, "games": games, "num_games": num}


async def local_game(
    config: Config,
    gatekeeper: Gatekeeper,
    *,
    on_event: Any = None,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Run ``num_games`` of OUR cop vs OUR thief on the freeze-proof local in-memory engine."""
    from cosmos77_ex06.orchestrator.local import build_engine as build_local_engine

    engine, clients = build_local_engine(config, gatekeeper, client_factory)
    engine.on_event = on_event
    return await _play_games(engine, clients, int(config.get("num_games", default=1)), on_event)
