"""Shared FastMCP server factory (Rule 3, no duplication between cop/thief).

``build_server`` wires a role's :class:`GameTools` onto a fresh ``FastMCP`` app:
it registers the shared communication + perception + action tools, attaches the
revocable ``StaticTokenVerifier`` (E2), and — only for the cop — registers the
cop-only ``place_barrier`` so the role asymmetry is *structural* (the tool is
absent from the thief server's ``list_tools`` entirely, a tested invariant). No
LLM is imported anywhere in this package (E3).
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from cosmos77_ex06.mcp_servers.auth import build_verifier
from cosmos77_ex06.mcp_servers.tools import GameTools
from cosmos77_ex06.shared.config import Config


def _assert_scope(role: str) -> None:
    """Cross-check ``role`` against the authenticated token's scopes (E2, PRD §4).

    On an HTTP request an access token is present: a token without the matching
    role scope is rejected before any tool body runs. Outside an HTTP context
    (in-process / in-memory transport) ``get_access_token`` returns ``None`` and
    the gate is a no-op, leaving the role/identity check in :class:`GameTools`.
    """
    token = get_access_token()
    if token is not None and role not in token.scopes:
        raise ValueError(f"token scope does not authorize role {role!r}")


def register_tools(mcp: FastMCP, tools: GameTools) -> None:
    """Register the shared tool surface, plus ``place_barrier`` for the cop only."""

    @mcp.tool
    def send_message(role: str, content: str) -> dict[str, Any]:
        """Append a free natural-language message from ``role`` to the shared log."""
        _assert_scope(role)
        return tools.send_message(role, content)

    @mcp.tool
    def receive_messages(role: str, since: int = 0) -> dict[str, Any]:
        """Return the opponent's natural-language messages with id >= ``since``."""
        _assert_scope(role)
        return tools.receive_messages(role, since)

    @mcp.tool
    def get_local_observation(role: str) -> dict[str, Any]:
        """Return only ``role``'s partial, vision-windowed view (partial observability)."""
        _assert_scope(role)
        return tools.get_local_observation(role)

    @mcp.tool
    def verify_position(role: str, x: int, y: int) -> dict[str, Any]:
        """Confirm-only: is ``(x, y)`` the opponent's cell, if inside the vision window?"""
        _assert_scope(role)
        return tools.verify_position(role, x, y)

    @mcp.tool
    def apply_move(role: str, direction: str) -> dict[str, Any]:
        """Move ``role`` one step in ``direction`` (turn order + capture enforced)."""
        _assert_scope(role)
        return tools.apply_move(role, direction)

    if tools.role == "cop":

        @mcp.tool
        def place_barrier(role: str, x: int, y: int) -> dict[str, Any]:
            """Place a cop-only barrier at ``(x, y)``, impassable to both agents."""
            _assert_scope(role)
            return tools.place_barrier(role, x, y)


def build_server(role: str, state: Any, config: Config | None = None) -> FastMCP:
    """Build a role's FastMCP server: tools + token auth, bound to ``state``."""
    cfg = config or Config()
    tools = GameTools(state, cfg, role)
    mcp = FastMCP(f"cosmos77-{role}", auth=build_verifier(role))
    register_tools(mcp, tools)
    return mcp
