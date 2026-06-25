"""Cross-team game logic for the live web console — kept out of sdk.py (Rule 1/2).

Two async entry points the web runner drives:
* :func:`cross_game` — ONE live game over a cop URL + a thief URL (the "exhibition").
* :func:`bonus_series_live` — the full 6-sub-game role-swap (E12), streamed live, also
  writing the byte-identical ``bonus_game`` JSON.

Both thread an optional per-turn ``on_event`` hook into the :class:`GameEngine` and pass
the visitor-supplied token at RUNTIME (never written to config; Rule 9). No LLM here.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from cosmos77_ex06.bonus import report as bonus_report
from cosmos77_ex06.bonus.cloud import build_cloud_engine
from cosmos77_ex06.bonus.series import run_series
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
    num = int(config.get("num_games", default=1))
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
    win = (
        "cop"
        if totals["cop"] > totals["thief"]
        else "thief"
        if totals["thief"] > totals["cop"]
        else "tie"
    )
    return {
        "winner": win,
        "cop_score": totals["cop"],
        "thief_score": totals["thief"],
        "games": games,
        "num_games": num,
    }


def _series_config(config: Config, urls: dict[str, str]) -> Config:
    """A per-run config copy with the four ``bonus.mcp.*`` URLs set (no shared mutation)."""
    cfg = copy.copy(config)
    cfg._data = copy.deepcopy(config._data)  # noqa: SLF001 - intentional per-run override
    mcp = cfg._data.setdefault("bonus", {}).setdefault("mcp", {})
    mcp.update(urls)
    return cfg


async def bonus_series_live(
    config: Config,
    gatekeeper: Gatekeeper,
    reports_dir: Path,
    *,
    our_cop: str,
    our_thief: str,
    their_cop: str,
    their_thief: str,
    token: str | None,
    on_event: Any = None,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Run the 6-game role-swap series live; write the byte-identical JSON; return the result."""
    cfg = _series_config(
        config,
        {
            "group_1_cop": our_cop,
            "group_1_thief": our_thief,
            "group_2_cop": their_cop,
            "group_2_thief": their_thief,
        },
    )

    def factory(
        c: Config, gk: Gatekeeper, *, cop_url: str, thief_url: str, client_factory: Any = None
    ):
        return build_cloud_engine(
            c,
            gk,
            cop_url=cop_url,
            thief_url=thief_url,
            token=token,
            on_event=on_event,
            client_factory=client_factory,
        )

    series = await run_series(
        cfg, gatekeeper, client_factory=client_factory, engine_factory=factory
    )
    report = bonus_report.build_report(cfg, series["sub_games"])
    text = bonus_report.serialize(report)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "bonus_game.json"
    path.write_text(text + "\n", encoding="utf-8")
    return {
        "totals_by_group": report["totals_by_group"],
        "bonus_claim": report.get("bonus_claim"),
        "sub_games": report["sub_games"],
        "path": str(path),
    }
