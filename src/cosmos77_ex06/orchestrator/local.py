"""Wire the orchestrator to the LOCAL MCP servers via in-memory FastMCP clients.

LOCAL-ONLY topology (Phase 4). Builds one shared ground-truth :class:`GameState`,
mounts the cop + thief FastMCP servers on it (tools only, E3), opens an in-memory
``Client`` per server, and runs a full game through :class:`GameEngine`. The two
servers are SEPARATE FastMCP apps but here they share ONE in-process ``GameState``
through :class:`_StateProxy`, so ground truth (positions, barriers, capture) stays
consistent. This shared-memory shortcut is valid ONLY in-process: a true cloud run
(Phase 7/8) with the servers as separate processes would need one state-holding
service, not shared Python memory.

The natural-language CHANNEL, by contrast, is already process-independent: the
ENGINE holds the transcript and relays the opponent's last NL message into the
active prompt (E4), so message passing never depends on shared server memory — see
``test_message_relay_no_shared_state``. Returns the transcript + totals.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from cosmos77_ex06.mcp_servers.server import build_server
from cosmos77_ex06.orchestrator.engine import GameEngine
from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def build_engine(
    config: Config,
    gatekeeper: Gatekeeper,
    client_factory: Any = None,
) -> tuple[GameEngine, dict[str, Client]]:
    """Construct a :class:`GameEngine` wired to in-memory cop/thief servers.

    ``client_factory`` (optional) injects a mock genai client into
    :class:`GeminiClient`; when omitted the real SDK client is used (live only).
    Returns the engine and the two unentered FastMCP clients (open them with
    ``async with`` before calling :meth:`GameEngine.play_game`).
    """
    engine_holder: dict[str, Any] = {}
    cop_server = build_server("cop", _StateProxy(engine_holder), config)
    thief_server = build_server("thief", _StateProxy(engine_holder), config)
    clients = {"cop": Client(cop_server), "thief": Client(thief_server)}
    kwargs = {} if client_factory is None else {"client_factory": client_factory}
    gemini = GeminiClient(config, gatekeeper, **kwargs)
    engine = GameEngine(config, clients, gemini)
    engine_holder["state"] = engine.state
    return engine, clients


class _StateProxy:
    """Forwards attribute access to the engine's shared state (set after wiring).

    The servers bind their tools to this proxy at construction time; the engine's
    live :class:`GameState` is injected once it exists, so both servers and the
    engine mutate the SAME ground truth in place across sub-games. This is a
    LOCAL-ONLY (in-process) shortcut: across separate processes each server would
    hold a divergent state, so a cloud deployment must replace this with one
    state-holding service (Phase 7/8). The NL message relay does NOT rely on this —
    it runs through the engine-held transcript and is process-independent.
    """

    def __init__(self, holder: dict[str, Any]) -> None:
        object.__setattr__(self, "_holder", holder)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._holder["state"], name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._holder["state"], name, value)


async def run_local_game(
    config: Config,
    gatekeeper: Gatekeeper,
    client_factory: Any = None,
) -> dict[str, Any]:
    """Open the in-memory clients and run a full local game; return the result dict."""
    engine, clients = build_engine(config, gatekeeper, client_factory)
    async with clients["cop"], clients["thief"]:
        return await engine.play_game()
