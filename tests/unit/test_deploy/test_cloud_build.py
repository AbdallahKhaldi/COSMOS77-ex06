"""--cloud wiring tests: clients built against CONFIG URLs with the token, no network.

The FastMCP ``Client`` is mocked via an injected ``client_factory`` so CI never
touches the network (Rule 6). We assert: the orchestrator reads ``mcp.cop_url`` /
``mcp.thief_url`` from config, attaches a ``BearerAuth(ORCHESTRATOR_TOKEN)``, refuses
non-HTTPS targets and a missing token, and attaches a :class:`ClientStateSync` so the
cloud run keeps the two separate-process servers consistent (E6).
"""

from __future__ import annotations

from typing import Any

import pytest

from cosmos77_ex06.orchestrator import cloud
from cosmos77_ex06.orchestrator.sync import ClientStateSync
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


class _FakeClient:
    """Records the URL + auth it was built with (stands in for a FastMCP Client)."""

    def __init__(self, url: str, auth: Any) -> None:
        self.url = url
        self.auth = auth


def _factory(calls: list[tuple[str, Any]]):
    """A client_factory that records every ``(url, auth)`` and returns a fake client."""

    def _make(url: str, auth: Any) -> _FakeClient:
        calls.append((url, auth))
        return _FakeClient(url, auth)

    return _make


def test_build_clients_uses_config_urls_and_token(cloud_config) -> None:
    """The clients are built against the config HTTPS URLs with the orchestrator token."""
    calls: list[tuple[str, Any]] = []
    urls, clients = cloud.build_clients(cloud_config, _factory(calls))
    assert urls == {
        "cop": "https://cosmos-cop.fastmcp.app/mcp",
        "thief": "https://cosmos-thief.fastmcp.app/mcp",
    }
    assert {c.url for c in clients.values()} == set(urls.values())
    # BearerAuth carries the orchestrator token (read from .env / env, never hardcoded).
    for _url, auth in calls:
        assert auth.token.get_secret_value() == "test-orch-token"


def test_build_clients_rejects_non_https(cloud_config) -> None:
    """A http:// (non-cloud) URL under --cloud is rejected before any client is built."""
    cloud_config._data["mcp"]["cop_url"] = "http://localhost:8001/mcp"  # noqa: SLF001
    with pytest.raises(ValueError, match="https"):
        cloud.build_clients(cloud_config, _factory([]))


def test_build_clients_requires_token(cloud_config, monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing ORCHESTRATOR_TOKEN aborts the cloud run (no anonymous public calls)."""
    monkeypatch.delenv("ORCHESTRATOR_TOKEN", raising=False)
    with pytest.raises(KeyError, match="ORCHESTRATOR_TOKEN"):
        cloud.build_clients(cloud_config, _factory([]))


def test_build_engine_attaches_cloud_state_sync(cloud_config, tmp_path) -> None:
    """The cloud engine carries a ClientStateSync (the separate-process consistency fix)."""
    gk = Gatekeeper(tmp_path)
    engine, clients = cloud.build_engine(
        cloud_config, gk, genai_factory=lambda _key: object(), client_factory=_factory([])
    )
    assert isinstance(engine.state_sync, ClientStateSync)
    assert engine.url_for("cop") == "https://cosmos-cop.fastmcp.app/mcp"
    assert set(clients) == {"cop", "thief"}


async def test_run_cloud_game_opens_clients_and_plays(cloud_config, tmp_path, monkeypatch) -> None:
    """run_cloud_game enters both clients as async contexts and returns play_game()'s dict."""
    entered: list[str] = []

    class _CtxClient(_FakeClient):
        async def __aenter__(self) -> _CtxClient:
            entered.append(self.url)
            return self

        async def __aexit__(self, *exc: object) -> None:
            return None

    def _ctx_factory(url: str, auth: Any) -> _CtxClient:
        return _CtxClient(url, auth)

    async def _fake_play(self: Any) -> dict[str, Any]:
        return {"totals": {"cop": 0, "thief": 0}, "transcript": []}

    monkeypatch.setattr("cosmos77_ex06.orchestrator.engine.GameEngine.play_game", _fake_play)
    gk = Gatekeeper(tmp_path)
    out = await cloud.run_cloud_game(
        cloud_config, gk, genai_factory=lambda _key: object(), client_factory=_ctx_factory
    )
    assert out["totals"] == {"cop": 0, "thief": 0}
    assert len(entered) == 2  # both cloud clients were opened
