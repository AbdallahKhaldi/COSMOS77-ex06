"""Module-level server construction, state factory, and the live HTTP-auth test.

The live test (real bearer auth over HTTP) is marked ``live`` and excluded from the
default suite (``-m 'not live'``)."""

from __future__ import annotations

import asyncio
import os

import pytest

from cosmos77_ex06.mcp_servers.state_factory import make_state


def test_make_state_defaults(mcp_config) -> None:
    """The standalone state factory builds opposite-corner starts, thief first."""
    state = make_state(mcp_config)
    assert tuple(state.cop_pos) == (4, 4)
    assert tuple(state.thief_pos) == (0, 0)
    assert state.current_role == "thief"


def test_cop_server_module_exposes_mcp() -> None:
    """The cop_server module exposes a module-level ``mcp`` with place_barrier."""
    from cosmos77_ex06.mcp_servers import cop_server

    names = {t.name for t in asyncio.run(cop_server.mcp.list_tools())}
    assert "place_barrier" in names


def test_thief_server_module_lacks_place_barrier() -> None:
    """The thief_server module's ``mcp`` has no place_barrier."""
    from cosmos77_ex06.mcp_servers import thief_server

    names = {t.name for t in asyncio.run(thief_server.mcp.list_tools())}
    assert "place_barrier" not in names


def _asgi_status(authorization: str | None) -> int:
    """POST a tools/list request through the cop ASGI app and return the HTTP status.

    Uses an in-process ``httpx.ASGITransport`` (no network, no ``live`` marker) so
    wire-level bearer-auth rejection is exercised in the default CI suite (E2).
    """
    import httpx

    from cosmos77_ex06.mcp_servers.cop_server import mcp

    app = mcp.http_app()
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    headers = {"Accept": "application/json, text/event-stream"}
    if authorization is not None:
        headers["Authorization"] = authorization

    async def _call() -> int:
        transport = httpx.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        ):
            resp = await client.post("/mcp", json=body, headers=headers)
            return resp.status_code

    return asyncio.run(_call())


def test_asgi_missing_auth_header_is_401() -> None:
    """A request with no Authorization header is rejected (401) before any tool runs."""
    assert _asgi_status(None) == 401


def test_asgi_garbage_token_is_401() -> None:
    """A request with an unknown bearer token is rejected (401) before any tool runs."""
    assert _asgi_status("Bearer not-a-real-token") == 401


def test_asgi_good_token_passes_auth() -> None:
    """The orchestrator token clears wire-level auth (not 401; handshake then proceeds)."""
    assert _asgi_status(f"Bearer {os.environ['ORCHESTRATOR_TOKEN']}") != 401


class _FakeToken:
    """Minimal stand-in for an access token carrying a fixed scope list."""

    def __init__(self, scopes: list[str]) -> None:
        self.scopes = scopes


def test_assert_scope_no_context_is_noop(monkeypatch) -> None:
    """Outside an HTTP request (no access token) the scope gate is a no-op (E2)."""
    from cosmos77_ex06.mcp_servers import server as server_mod

    monkeypatch.setattr(server_mod, "get_access_token", lambda: None)
    server_mod._assert_scope("cop")  # must not raise


def test_assert_scope_accepts_matching_role(monkeypatch) -> None:
    """A token whose scopes include the role is authorized (E2)."""
    from cosmos77_ex06.mcp_servers import server as server_mod

    monkeypatch.setattr(server_mod, "get_access_token", lambda: _FakeToken(["read", "cop"]))
    server_mod._assert_scope("cop")  # must not raise


def test_assert_scope_rejects_missing_role_scope(monkeypatch) -> None:
    """A token lacking the role scope is rejected before any tool body runs (E2)."""
    from cosmos77_ex06.mcp_servers import server as server_mod

    monkeypatch.setattr(server_mod, "get_access_token", lambda: _FakeToken(["read", "thief"]))
    with pytest.raises(ValueError, match="does not authorize role"):
        server_mod._assert_scope("cop")


@pytest.mark.live
def test_http_auth_good_and_bad_token() -> None:
    """Live: over real HTTP, the good token lists tools; a bad token is rejected."""
    import threading
    import time

    from fastmcp import Client

    from cosmos77_ex06.mcp_servers.cop_server import mcp

    port = 8401
    t = threading.Thread(
        target=lambda: mcp.run(transport="http", host="127.0.0.1", port=port),
        daemon=True,
    )
    t.start()
    time.sleep(2)
    url = f"http://127.0.0.1:{port}/mcp"

    async def good() -> list[str]:
        async with Client(url, auth=os.environ["ORCHESTRATOR_TOKEN"]) as c:
            return [x.name for x in await c.list_tools()]

    async def bad() -> None:
        async with Client(url, auth="wrong") as c:
            await c.list_tools()

    assert "apply_move" in asyncio.run(good())
    with pytest.raises(Exception):  # noqa: B017
        asyncio.run(bad())
