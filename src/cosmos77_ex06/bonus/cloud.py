"""Build a cross-group :class:`GameEngine` wired to two PUBLIC cloud MCP URLs (E6).

This is the live activation seam for the bonus series. Unlike the local in-memory
topology (``orchestrator/local.py``), each bonus server is a *foreign, remote*
FastMCP deployment that holds its own ground-truth state, so the orchestrator just
opens a token-authed :class:`fastmcp.Client` against each public HTTPS URL and
reuses the existing :class:`GameEngine` turn loop (Server/Client separation, E3,
preserved across the group boundary). The shared bonus token comes from
``BONUS_MCP_TOKEN`` in ``.env`` (Rule 9 — never in the repo); rotating it revokes
cross-group access after the series. This module performs NO network at import time
and is fully bypassed in tests via the injected ``engine_factory``.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.orchestrator.engine import GameEngine
from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def build_cloud_engine(
    config: Config,
    gatekeeper: Gatekeeper,
    *,
    cop_url: str,
    thief_url: str,
    token: str | None = None,
    on_event: Any = None,
    client_factory: Any = None,
) -> tuple[GameEngine, dict[str, Any]]:
    """Construct a :class:`GameEngine` whose cop/thief clients hit the given cloud URLs.

    Opens a token-authed FastMCP ``Client`` per URL and passes both — plus the per-role
    URLs (transcript evidence, E6) — into the engine. ``token`` overrides the default
    ``BONUS_MCP_TOKEN`` (the web console passes the visitor-supplied token at runtime,
    never persisted; Rule 9). ``on_event`` is the optional live per-turn hook (web
    console). ``client_factory`` injects a mock genai client for tests. Returns the
    engine and the two UNENTERED clients (open them with ``async with`` before playing).
    """
    from fastmcp import Client

    auth = token or config.env("BONUS_MCP_TOKEN")
    clients = {
        "cop": Client(cop_url, auth=auth),
        "thief": Client(thief_url, auth=auth),
    }
    kwargs = {} if client_factory is None else {"client_factory": client_factory}
    gemini = GeminiClient(config, gatekeeper, **kwargs)
    engine = GameEngine(
        config, clients, gemini, urls={"cop": cop_url, "thief": thief_url}, on_event=on_event
    )
    return engine, clients
