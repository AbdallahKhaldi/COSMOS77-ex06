"""Wire the orchestrator to the CLOUD MCP servers over public HTTPS (E6).

CLOUD topology (Phase 8). Mirrors :mod:`orchestrator.local`'s structure but, instead
of in-memory transport over one shared :class:`GameState`, it opens an authenticated
FastMCP ``Client`` per server against the CONFIG URLs (``mcp.cop_url`` /
``mcp.thief_url``) using the ``ORCHESTRATOR_TOKEN`` bearer (no URL or token is ever
hardcoded; Rule 4 / Rule 9). Across SEPARATE cloud processes each server holds its
OWN state, so the engine owns the authoritative :class:`GameState` and a
:class:`ClientStateSync` mirrors the canonical board to both servers after every turn
(and at each sub-game reset) — closing the cloud state-sync gap while each server
still redacts to a partial view in ``get_local_observation`` (E4). The LLM stays in
the orchestrator (E3); the servers expose tools only.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from cosmos77_ex06.orchestrator.engine import GameEngine
from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.orchestrator.sync import ClientStateSync
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

ORCH_TOKEN_ENV = "ORCHESTRATOR_TOKEN"


def _require_https(urls: dict[str, str]) -> None:
    """Reject non-HTTPS cloud URLs (a misconfigured ``--cloud`` target; PRD §5)."""
    for role, url in urls.items():
        if not url.lower().startswith("https://"):
            raise ValueError(f"--cloud requires an https:// URL for {role}, got {url!r}")


def build_clients(
    config: Config, client_factory: Any = None
) -> tuple[dict[str, str], dict[str, Client]]:
    """Build authenticated FastMCP clients for the configured cloud URLs.

    Reads ``mcp.cop_url`` / ``mcp.thief_url`` from config and the bearer token from
    ``ORCHESTRATOR_TOKEN`` (env / .env), attaching it to every client connection.
    ``client_factory`` (optional, ``(url, auth) -> Client``) is injected by tests so
    no real network is touched in CI. Returns ``(urls, clients)``.
    """
    urls = {r: str(config.get(f"mcp.{r}_url")) for r in ("cop", "thief")}
    _require_https(urls)
    token = config.env(ORCH_TOKEN_ENV)
    if not token:
        raise KeyError(f"{ORCH_TOKEN_ENV} must be set for a --cloud run")
    factory = client_factory or (lambda url, auth: Client(url, auth=auth))
    clients = {r: factory(urls[r], BearerAuth(token)) for r in ("cop", "thief")}
    return urls, clients


def build_engine(
    config: Config,
    gatekeeper: Gatekeeper,
    genai_factory: Any = None,
    client_factory: Any = None,
) -> tuple[GameEngine, dict[str, Client]]:
    """Construct a :class:`GameEngine` wired to the cloud servers + cloud state-sync.

    ``genai_factory`` injects a mock genai client into :class:`GeminiClient`;
    ``client_factory`` injects mock FastMCP clients (both default to the real path,
    used only in live runs). The engine owns the authoritative state and carries a
    :class:`ClientStateSync` so the two separate-process servers stay consistent.
    """
    urls, clients = build_clients(config, client_factory)
    kwargs = {} if genai_factory is None else {"client_factory": genai_factory}
    gemini = GeminiClient(config, gatekeeper, **kwargs)
    engine = GameEngine(config, clients, gemini, urls=urls)
    timeout = float(config.get("mcp.tool_timeout_seconds", default=10.0))
    engine.state_sync = ClientStateSync(clients, timeout=timeout)
    return engine, clients


async def run_cloud_game(
    config: Config,
    gatekeeper: Gatekeeper,
    genai_factory: Any = None,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Open the authenticated cloud clients and run a full game; return the result dict."""
    engine, clients = build_engine(config, gatekeeper, genai_factory, client_factory)
    async with clients["cop"], clients["thief"]:
        return await engine.play_game()
