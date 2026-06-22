"""GeminiClient tests — mocked google-genai, gatekeeper metering (E3, Rule 6/13)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import _FakeResponse, make_client_factory


def _gk(tmp_path: Path) -> Gatekeeper:
    return Gatekeeper(tmp_path / "results")


@pytest.mark.asyncio
async def test_ask_parses_message_and_tool(
    orch_config: Config, tmp_path: Path, live_session: Any
) -> None:
    factory = make_client_factory(
        lambda _p: _FakeResponse("sweeping the north", "apply_move", {"direction": "S"})
    )
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    out = await gc.ask("cop", "prompt text", mcp_session=live_session)
    assert out == {
        "role": "cop",
        "message": "sweeping the north",
        "tool": "apply_move",
        "args": {"direction": "S"},
    }


@pytest.mark.asyncio
async def test_ask_handles_no_tool_call(
    orch_config: Config, tmp_path: Path, live_session: Any
) -> None:
    factory = make_client_factory(lambda _p: _FakeResponse("just talking", None, {}))
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    out = await gc.ask("thief", "p", mcp_session=live_session)
    assert out["tool"] is None and out["message"] == "just talking"


@pytest.mark.asyncio
async def test_ask_meters_through_gatekeeper(
    orch_config: Config, tmp_path: Path, live_session: Any
) -> None:
    factory = make_client_factory(
        lambda _p: _FakeResponse("hi", "apply_move", {"direction": "STAY"})
    )
    gk = _gk(tmp_path)
    gc = GeminiClient(orch_config, gk, client_factory=factory)
    await gc.ask("cop", "p1", mcp_session=live_session)
    await gc.ask("cop", "p2", mcp_session=live_session)
    ledger = gk.read("llm_cop")
    assert ledger["calls"] == 2
    assert ledger["tokens"] == 24
    assert ledger["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_client_is_lazily_built_and_cached(
    orch_config: Config, tmp_path: Path, live_session: Any
) -> None:
    built: list[int] = []

    def factory(_key: str | None):  # noqa: ANN202
        built.append(1)
        from .conftest import FakeGenaiClient

        return FakeGenaiClient(lambda _p: _FakeResponse("x", None, {}))

    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    assert built == []  # not built until first ask
    await gc.ask("thief", "p", mcp_session=live_session)
    await gc.ask("thief", "p", mcp_session=live_session)
    assert built == [1]  # built once, cached


@pytest.mark.asyncio
async def test_ask_uses_async_aio_path_not_sync(
    orch_config: Config, tmp_path: Path, live_session: Any
) -> None:
    """Lock the API shape: ask() awaits client.aio.models.generate_content.

    google-genai 2.9.0 raises on MCP sessions passed to the SYNCHRONOUS
    ``client.models.generate_content``; the fake mirrors that by raising there.
    A successful ask proves the client took the async path.
    """
    from .conftest import FakeGenaiClient

    fake = FakeGenaiClient(lambda _p: _FakeResponse("via aio", "apply_move", {"direction": "STAY"}))
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=lambda _k: fake)
    out = await gc.ask("cop", "p", mcp_session=live_session)
    assert out["message"] == "via aio"
    assert fake.aio.models.calls, "async aio path was not used"
    with pytest.raises(RuntimeError, match="synchronous"):
        fake.models.generate_content(model="m", contents="c", config=None)
