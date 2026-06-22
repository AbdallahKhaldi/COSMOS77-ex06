"""GeminiClient tests — mocked google-genai, structured output, metering (E3, Rule 6/13)."""

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
async def test_ask_parses_message_and_move(orch_config: Config, tmp_path: Path) -> None:
    factory = make_client_factory(
        lambda _p: _FakeResponse("sweeping the north", "apply_move", {"direction": "S"})
    )
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    out = await gc.ask("cop", "prompt text")
    assert out == {
        "role": "cop",
        "message": "sweeping the north",
        "tool": "apply_move",
        "args": {"direction": "S"},
    }


@pytest.mark.asyncio
async def test_ask_parses_barrier_action(orch_config: Config, tmp_path: Path) -> None:
    factory = make_client_factory(
        lambda _p: _FakeResponse("walling off the gap", "place_barrier", {"x": 1, "y": 2})
    )
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    out = await gc.ask("cop", "prompt text")
    assert out["tool"] == "place_barrier"
    assert out["args"] == {"x": 1, "y": 2}


@pytest.mark.asyncio
async def test_ask_defaults_to_stay_on_bare_message(orch_config: Config, tmp_path: Path) -> None:
    """No action in the script -> structured output still yields a safe STAY move."""
    factory = make_client_factory(lambda _p: _FakeResponse("just talking", None, {}))
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    out = await gc.ask("thief", "p")
    assert out["message"] == "just talking"
    assert out["tool"] == "apply_move" and out["args"] == {"direction": "STAY"}


@pytest.mark.asyncio
async def test_ask_falls_back_on_unparseable_json(orch_config: Config, tmp_path: Path) -> None:
    """A non-JSON ``.text`` parses to the safe fallback (no crash)."""
    from .conftest import FakeGenaiClient

    bad = type("R", (), {"text": "not json at all", "usage_metadata": None})()
    gc = GeminiClient(
        orch_config, _gk(tmp_path), client_factory=lambda _k: FakeGenaiClient(lambda _p: bad)
    )
    out = await gc.ask("thief", "p")
    assert out == {
        "role": "thief",
        "message": "",
        "tool": "apply_move",
        "args": {"direction": "STAY"},
    }


@pytest.mark.asyncio
async def test_ask_meters_via_gatekeeper_on_async_path(orch_config: Config, tmp_path: Path) -> None:
    """Two asks meter through the gatekeeper AND prove the async aio path was used."""
    factory = make_client_factory(
        lambda _p: _FakeResponse("hi", "apply_move", {"direction": "STAY"})
    )
    gk = _gk(tmp_path)
    gc = GeminiClient(orch_config, gk, client_factory=factory)
    await gc.ask("cop", "p1")
    await gc.ask("cop", "p2")
    ledger = gk.read("llm_cop")
    assert (ledger["calls"], ledger["tokens"], ledger["model"]) == (2, 24, "gemini-2.5-flash")
    assert factory.fake.aio.models.calls, "async aio path was not used"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_client_is_lazily_built_and_cached(orch_config: Config, tmp_path: Path) -> None:
    built: list[int] = []

    def factory(_key: str | None):  # noqa: ANN202
        built.append(1)
        from .conftest import FakeGenaiClient

        return FakeGenaiClient(lambda _p: _FakeResponse("x", None, {}))

    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=factory)
    assert built == []  # not built until first ask
    await gc.ask("thief", "p")
    await gc.ask("thief", "p")
    assert built == [1]  # built once, cached


def test_build_config_is_structured_and_role_conditional(
    orch_config: Config, tmp_path: Path
) -> None:
    """No live session/tools in the config; the cop may barrier, the thief may not."""
    gc = GeminiClient(orch_config, _gk(tmp_path))
    cop_cfg = gc._build_config("cop")
    thief_cfg = gc._build_config("thief")
    assert getattr(cop_cfg, "tools", None) is None
    assert cop_cfg.response_mime_type == "application/json"
    assert cop_cfg.response_schema is not None
    cop_enum = cop_cfg.response_schema.properties["action"].properties["type"].enum
    thief_enum = thief_cfg.response_schema.properties["action"].properties["type"].enum
    assert "barrier" in cop_enum
    assert "barrier" not in thief_enum


def test_transient_retry_then_success(
    orch_config: Config, tmp_path: Path, monkeypatch: Any
) -> None:
    """A 429 on the first attempt is retried (with mocked sleep) and then succeeds."""
    import asyncio

    from .conftest import FakeGenaiClient

    attempts = {"n": 0}

    def script(_p: str) -> _FakeResponse:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: rate limit")
        return _FakeResponse("recovered", "apply_move", {"direction": "STAY"})

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("cosmos77_ex06.orchestrator.llm_retry.asyncio.sleep", _no_sleep)
    gc = GeminiClient(orch_config, _gk(tmp_path), client_factory=lambda _k: FakeGenaiClient(script))
    out = asyncio.run(gc.ask("cop", "p"))
    assert out["message"] == "recovered"
    assert attempts["n"] == 2
