"""Starlette request handlers for the live match console (thin; logic in feed/runner).

Four endpoints: the page, our-info (display our URLs), run (passphrase-gated launch),
and the SSE event stream. The passphrase is checked BEFORE any game starts or any SDK
code is touched. Visitor URLs + token are used at runtime only, never persisted.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request
from starlette.responses import JSONResponse

from cosmos77_ex06.web import runner, security


def _https_ok(*urls: str) -> bool:
    """True only when every URL is a non-empty ``https://`` URL (cloud-safe; E6)."""
    return all(bool(u) and u.lower().startswith("https://") for u in urls)


async def index(request: Request) -> Any:
    """Serve the single-page console (no passphrase needed to VIEW)."""
    return request.app.state.templates.TemplateResponse(request, "index.html")


async def our_info(request: Request) -> JSONResponse:
    """Return our two live MCP URLs + the console URL for display (no secrets)."""
    feed = request.app.state.feed
    return JSONResponse(feed.our_info(request.app.state.config))


async def run(request: Request) -> JSONResponse:
    """Passphrase-gate, validate, and launch a run; return its ``run_id``."""
    body = await request.json()
    state = request.app.state
    if not security.passphrase_ok(str(body.get("passphrase", "")), state.config):
        return JSONResponse({"error": "forbidden — wrong or missing passphrase"}, status_code=403)
    action = body.get("action")
    if action not in ("exhibition", "series"):
        return JSONResponse({"error": "unknown action"}, status_code=400)
    token = str(body.get("token", ""))
    their_cop = str(body.get("their_cop_url", ""))
    their_thief = str(body.get("their_thief_url", ""))
    our_cop = str(state.config.get("mcp.cop_url", default=""))
    our_thief = str(state.config.get("mcp.thief_url", default=""))
    run_id = uuid4().hex
    if action == "exhibition":
        cop, thief = (
            (their_cop, our_thief) if body.get("role") == "their_cop" else (our_cop, their_thief)
        )
        if not _https_ok(cop, thief):
            return JSONResponse({"error": "both URLs must be https://"}, status_code=400)
        state.feed.register(run_id)
        asyncio.create_task(
            runner.run_exhibition(
                state.config,
                state.gatekeeper,
                state.feed,
                run_id,
                cop_url=cop,
                thief_url=thief,
                token=token,
            )
        )
    else:
        if not _https_ok(our_cop, our_thief, their_cop, their_thief):
            return JSONResponse({"error": "all four URLs must be https://"}, status_code=400)
        state.feed.register(run_id)
        asyncio.create_task(
            runner.run_series(
                state.config,
                state.gatekeeper,
                state.reports_dir,
                state.feed,
                run_id,
                our_cop=our_cop,
                our_thief=our_thief,
                their_cop=their_cop,
                their_thief=their_thief,
                token=token,
            )
        )
    return JSONResponse({"run_id": run_id})


async def events(request: Request) -> Any:
    """SSE stream of a run's live events (404 if ``run_id`` is unknown)."""
    run_id = request.path_params["run_id"]
    feed = request.app.state.feed
    if not feed.has(run_id):
        return JSONResponse({"error": "unknown run_id"}, status_code=404)
    return EventSourceResponse(feed.stream(run_id))
