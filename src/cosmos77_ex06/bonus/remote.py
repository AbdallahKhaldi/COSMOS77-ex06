"""A remote move source — one NajAmjad MCP server behind the ``request_move`` contract (E12).

Wraps a public ``(url, token)`` cop/thief server: builds the FastMCP client (bearer auth),
calls ``request_move(observation, auth_token)``, and returns the raw prose. Bounded by a
timeout so a hung foreign server voids + re-runs the sub-game instead of wedging the series.
The token is presented BOTH as the transport bearer and as the ``auth_token`` tool argument
(their treaty: "the defender's revocable bearer token as auth_token"). No network at import;
``client_factory`` injects a fake client in tests.
"""

from __future__ import annotations

from typing import Any


class RemoteMoveSource:
    """Calls one foreign server's ``request_move`` — their agent decides the move."""

    def __init__(
        self, url: str, token: str, *, timeout: float = 10.0, client_factory: Any = None
    ) -> None:
        self.url, self.token, self.timeout = url, token, timeout
        self._client_factory = client_factory

    def _client(self) -> Any:
        """Build the FastMCP client (or the injected fake) for this server."""
        if self._client_factory is not None:
            return self._client_factory(self.url, self.token)
        from fastmcp import Client
        from fastmcp.client.auth import BearerAuth

        return Client(self.url, auth=BearerAuth(self.token), timeout=self.timeout)

    async def request_move(self, observation: dict[str, Any]) -> str:
        """Return the foreign agent's raw ``"[INTENT: ...] prose"`` for ``observation``."""
        async with self._client() as client:
            result = await client.call_tool(
                "request_move", {"observation": observation, "auth_token": self.token}
            )
            text = getattr(result, "data", None)
            if text is None and getattr(result, "content", None):
                text = result.content[0].text
            return str(text)
