"""Bridge the HTTP layer to the (async) cross-team game logic, streaming events.

Each coroutine publishes a ``meta`` event, drives the game via :mod:`web.match` with an
``on_event`` routing every per-turn event into the run's queue, then publishes a
``game_end`` (or ``error``) and a final ``done`` sentinel. The game runs on the server's
own event loop (every turn awaits MCP + Gemini I/O), so the SSE drain stays live — no
threads. Logic-only; no LLM here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper
from cosmos77_ex06.web import match


def _meta(config: Config, mode: str) -> dict[str, Any]:
    """The opening event — mode + board geometry the browser needs to render the radar."""
    return {
        "type": "meta",
        "mode": mode,
        "grid": list(config.get("grid_size")),
        "vision_radius": int(config.get("vision_radius", default=1)),
        "max_moves": int(config.get("max_moves", default=25)),
    }


async def run_exhibition(
    config: Config,
    gatekeeper: Gatekeeper,
    feed: Any,
    run_id: str,
    *,
    cop_url: str,
    thief_url: str,
    token: str,
) -> None:
    """Run ONE live game and stream it; publish the result, then ``done``."""
    feed.publish(run_id, _meta(config, "exhibition"))
    try:
        result = await match.cross_game(
            config,
            gatekeeper,
            cop_url=cop_url,
            thief_url=thief_url,
            token=token,
            on_event=lambda e: feed.publish(run_id, e),
        )
        feed.publish(run_id, {"type": "game_end", "mode": "exhibition", "result": result})
    except Exception as exc:  # noqa: BLE001 - surface any failure to the browser, then end cleanly
        feed.publish(run_id, {"type": "error", "message": f"{type(exc).__name__}: {exc}"})
    finally:
        feed.publish(run_id, {"type": "done"})


async def run_series(
    config: Config,
    gatekeeper: Gatekeeper,
    reports_dir: Path,
    feed: Any,
    run_id: str,
    *,
    our_cop: str,
    our_thief: str,
    their_cop: str,
    their_thief: str,
    token: str,
) -> None:
    """Run the 6-game role-swap series live and stream it; publish the result, then ``done``."""
    feed.publish(run_id, _meta(config, "series"))
    try:
        result = await match.bonus_series_live(
            config,
            gatekeeper,
            reports_dir,
            our_cop=our_cop,
            our_thief=our_thief,
            their_cop=their_cop,
            their_thief=their_thief,
            token=token,
            on_event=lambda e: feed.publish(run_id, e),
        )
        feed.publish(run_id, {"type": "game_end", "mode": "series", "result": result})
    except Exception as exc:  # noqa: BLE001 - surface any failure to the browser, then end cleanly
        feed.publish(run_id, {"type": "error", "message": f"{type(exc).__name__}: {exc}"})
    finally:
        feed.publish(run_id, {"type": "done"})
