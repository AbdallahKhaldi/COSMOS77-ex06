"""Starlette request handlers for the live match console (thin; logic in feed/runner).

Four endpoints: the page, our-info (display our URLs), run (passphrase-gated launch),
and the SSE event stream. The passphrase is checked BEFORE any game starts or any SDK
code is touched. Visitor URLs + token are used at runtime only, never persisted.
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
from typing import Any
from uuid import uuid4

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket

from cosmos77_ex06.web import runner, security


def _https_ok(*urls: str) -> bool:
    """True only when every URL is a non-empty ``https://`` URL (cloud-safe; E6)."""
    return all(bool(u) and u.lower().startswith("https://") for u in urls)


def _clamp(value: int, lo: int, hi: int) -> int:
    """Bound a user-supplied setting to a safe range (caps runtime + Gemini spend)."""
    return max(lo, min(hi, value))


def _run_config(base: Any, body: dict[str, Any]) -> Any:
    """A per-run config copy with optional grid / moves / games overrides (clamped)."""
    cfg = copy.copy(base)
    cfg._data = copy.deepcopy(base._data)  # noqa: SLF001 - intentional per-run override
    data = cfg._data  # noqa: SLF001
    if body.get("grid"):
        side = _clamp(int(body["grid"]), 3, 8)
        data["grid_size"] = [side, side]
    if body.get("moves"):
        data["max_moves"] = _clamp(int(body["moves"]), 5, 40)
    if body.get("games"):
        data["num_games"] = _clamp(int(body["games"]), 1, 8)
    return cfg


async def our_info(request: Request) -> JSONResponse:
    """Return our two live MCP URLs + the console URL for display (no secrets)."""
    feed = request.app.state.feed
    return JSONResponse(feed.our_info(request.app.state.config))


async def run(request: Request) -> JSONResponse:
    """Passphrase-gate, validate, and launch a run; return its ``run_id``.

    Three actions: ``solo`` (our cop vs our thief, our own token), ``exhibition`` (our
    side vs a rival's single game), ``series`` (the 6-game role-swap bonus).
    """
    body = await request.json()
    state = request.app.state
    if not security.passphrase_ok(str(body.get("passphrase", "")), state.config):
        return JSONResponse({"error": "Wrong or missing passphrase."}, status_code=403)
    cap = int(state.config.get("web.max_concurrent_runs", default=6))
    if state.feed.active_count() >= cap:
        msg = "Server busy — too many live matches. Try again shortly."
        return JSONResponse({"error": msg}, status_code=429)
    cfg = _run_config(state.config, body)
    action = body.get("action")
    if action not in ("solo", "exhibition", "series"):
        return JSONResponse({"error": "unknown action"}, status_code=400)
    our_cop = str(cfg.get("mcp.cop_url", default=""))
    our_thief = str(cfg.get("mcp.thief_url", default=""))
    their_cop = str(body.get("their_cop_url", ""))
    their_thief = str(body.get("their_thief_url", ""))
    run_id = uuid4().hex
    if action == "solo":
        state.feed.register(run_id)
        asyncio.create_task(runner.run_solo(cfg, state.gatekeeper, state.feed, run_id))
        return JSONResponse({"run_id": run_id})
    if action == "series":
        if not _https_ok(our_cop, our_thief, their_cop, their_thief):
            return JSONResponse({"error": "All four URLs must be https://"}, status_code=400)
        state.feed.register(run_id)
        asyncio.create_task(
            runner.run_series(
                cfg,
                state.gatekeeper,
                state.reports_dir,
                state.feed,
                run_id,
                our_cop=our_cop,
                our_thief=our_thief,
                their_cop=their_cop,
                their_thief=their_thief,
                token=str(body.get("token", "")),
            )
        )
        return JSONResponse({"run_id": run_id})
    if body.get("role") == "their_cop":
        cop, thief = their_cop, our_thief
    else:
        cop, thief = our_cop, their_thief
    token = str(body.get("token", ""))
    if not _https_ok(cop, thief):
        return JSONResponse(
            {"error": "Both URLs must be https:// — are our servers live?"}, status_code=400
        )
    state.feed.register(run_id)
    asyncio.create_task(
        runner.run_exhibition(
            cfg, state.gatekeeper, state.feed, run_id, cop_url=cop, thief_url=thief, token=token
        )
    )
    return JSONResponse({"run_id": run_id})


async def events(request: Request) -> Any:
    """SSE stream of a run's live events (404 if ``run_id`` is unknown)."""
    run_id = request.path_params["run_id"]
    feed = request.app.state.feed
    if not feed.has(run_id):
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    return EventSourceResponse(
        feed.stream(run_id),
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


async def ws_events(websocket: WebSocket) -> None:
    """WebSocket stream of a run's live events — the path that survives SSE-buffering tunnels."""
    run_id = websocket.path_params["run_id"]
    feed = websocket.app.state.feed
    await websocket.accept()
    if not feed.has(run_id):
        await websocket.close()
        return
    with contextlib.suppress(Exception):  # client may vanish mid-stream
        async for frame in feed.stream(run_id):
            await websocket.send_text(frame["data"])
    with contextlib.suppress(Exception):
        await websocket.close()
