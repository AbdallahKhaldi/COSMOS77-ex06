"""Fixtures for the orchestrator suite — mock google-genai, in-memory MCP, no network.

The seam: :class:`GeminiClient` accepts a ``client_factory`` that builds the
underlying google-genai client. Here we inject a FAKE client whose
``models.generate_content`` returns scripted responses carrying a free-language
message (``.text``) and a proposed tool call (``.function_calls``). The FastMCP
layer is the REAL in-memory ``Client`` against the REAL cop/thief servers, so the
test proves the LLM is invoked by the engine and the servers only execute tools.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from cosmos77_ex06.shared.config import Config

_CFG: dict[str, Any] = {
    "version": "1.00",
    "grid_size": [2, 2],
    "max_moves": 4,
    "num_games": 2,
    "max_barriers": 5,
    "allow_diagonal": True,
    "turn_order": ["thief", "cop"],
    "vision_radius": 1,
    "scoring": {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5},
    "llm": {"provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.2},
    "mcp": {
        "cop_url": "http://localhost:8001/mcp",
        "thief_url": "http://localhost:8002/mcp",
        "cop_port": 8001,
        "thief_port": 8002,
    },
    "report": {"to": "rmisegal+uoh26b@gmail.com", "timezone": "Asia/Jerusalem"},
    "group": {"name": "COSMOS77", "github_repo": "https://x"},
    "paths": {"results": "results", "reports": "reports", "assets": "assets"},
}


@pytest.fixture(autouse=True)
def _tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake MCP tokens so the servers build without real secrets."""
    monkeypatch.setenv("COP_MCP_TOKEN", "t-cop")
    monkeypatch.setenv("THIEF_MCP_TOKEN", "t-thief")
    monkeypatch.setenv("ORCHESTRATOR_TOKEN", "t-orch")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-not-used")


@pytest.fixture
def orch_config(tmp_path: Path) -> Config:
    """A tiny 2x2 / 4-move config for fast deterministic sub-games."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "config.yaml").write_text(yaml.safe_dump(_CFG), encoding="utf-8")
    return Config(cfg)


class _FakeResponse:
    """Mimics a google-genai response: ``.text`` + ``.function_calls`` + usage."""

    def __init__(self, text: str, tool: str | None, args: dict[str, Any]) -> None:
        self.text = text
        self.function_calls = [type("FC", (), {"name": tool, "args": args})()] if tool else []
        self.usage_metadata = type("U", (), {"total_token_count": 12})()


class _FakeSyncModels:
    """The SYNC ``client.models`` surface — google-genai forbids MCP sessions here."""

    def generate_content(self, *, model: str, contents: str, config: Any) -> _FakeResponse:
        """Mirror google-genai 2.9.0: reject MCP sessions on the synchronous path."""
        raise RuntimeError("MCP sessions are not supported in synchronous methods.")


class _FakeAsyncModels:
    """The ASYNC ``client.aio.models`` surface the client MUST use (locks the shape)."""

    def __init__(self, script: Callable[[str], _FakeResponse]) -> None:
        self._script = script
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> _FakeResponse:
        """Record the call and return a scripted response (no network)."""
        self.calls.append({"model": model, "contents": contents, "config": config})
        return self._script(contents)


class _FakeAio:
    """Mirrors ``google.genai.Client.aio`` — exposes ``.models`` (async)."""

    def __init__(self, models: _FakeAsyncModels) -> None:
        self.models = models


class FakeGenaiClient:
    """A stand-in for ``google.genai.Client`` driven by a per-prompt script.

    ``.aio.models.generate_content`` is the awaited path; the synchronous
    ``.models.generate_content`` raises, asserting the client never takes the
    unsupported sync route with a live MCP session.
    """

    def __init__(self, script: Callable[[str], _FakeResponse]) -> None:
        self.aio = _FakeAio(_FakeAsyncModels(script))
        self.models = _FakeSyncModels()


def make_client_factory(
    script: Callable[[str], _FakeResponse],
) -> Callable[[str | None], FakeGenaiClient]:
    """Build a ``client_factory(api_key)`` returning a scripted fake genai client."""
    fake = FakeGenaiClient(script)

    def _factory(api_key: str | None) -> FakeGenaiClient:
        return fake

    _factory.fake = fake  # type: ignore[attr-defined]
    return _factory


@pytest.fixture
def fake_response_cls() -> type[_FakeResponse]:
    """Expose the fake-response class so tests can script messages + tool calls."""
    return _FakeResponse


@pytest.fixture
async def live_session(orch_config: Config):
    """A REAL in-memory FastMCP ClientSession (so GenerateContentConfig validates)."""
    from fastmcp import Client

    from cosmos77_ex06.mcp_servers.server import build_server
    from cosmos77_ex06.mcp_servers.state_factory import make_state

    server = build_server("cop", make_state(orch_config), orch_config)
    async with Client(server) as client:
        yield client.session
