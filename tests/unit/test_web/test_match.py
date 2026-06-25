"""match.cross_game / bonus_series_live — the web game logic (engine + bonus mocked)."""

from __future__ import annotations

import asyncio
from typing import Any

from cosmos77_ex06.web import match


class _FakeClient:
    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *a: Any) -> bool:
        return False


class _FakeResult:
    winner = "cop"
    scores = {"cop": 20, "thief": 5}
    move_count = 4


class _FakeEngine:
    def __init__(self, on_event: Any) -> None:
        self.on_event = on_event

    async def play_sub_game(self, index: int) -> _FakeResult:
        if self.on_event:
            self.on_event({"type": "turn"})
        return _FakeResult()


class _SeriesCfg:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {"grid_size": [3, 3]}

    def get(self, key: str, default: Any = None) -> Any:
        cur: Any = self._data
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur


def test_cross_game_passes_token_and_callback(monkeypatch: Any) -> None:
    seen: dict[str, Any] = {}

    def fake_build(*a: Any, **k: Any) -> Any:
        seen.update(cop_url=k["cop_url"], token=k["token"])
        return _FakeEngine(k["on_event"]), {"cop": _FakeClient(), "thief": _FakeClient()}

    monkeypatch.setattr(match, "build_cloud_engine", fake_build)
    events: list[dict[str, Any]] = []
    result = asyncio.run(
        match.cross_game(
            _SeriesCfg(),
            None,
            cop_url="https://c/mcp",
            thief_url="https://t/mcp",
            token="tok",
            on_event=events.append,
        )
    )
    assert seen["token"] == "tok" and seen["cop_url"] == "https://c/mcp"
    assert result["winner"] == "cop" and result["cop_score"] == 20
    types = [e.get("type") for e in events]
    assert "turn" in types and "sub_game_end" in types


def test_bonus_series_live_overrides_urls_and_writes(monkeypatch: Any, tmp_path: Any) -> None:
    seen: dict[str, Any] = {}

    async def fake_run_series(cfg: Any, *a: Any, **k: Any) -> Any:
        seen["g1cop"] = cfg.get("bonus.mcp.group_1_cop")
        seen["g2thief"] = cfg.get("bonus.mcp.group_2_thief")
        return {"sub_games": [{"index": 1}], "reruns": 0}

    monkeypatch.setattr(match, "run_series", fake_run_series)
    monkeypatch.setattr(
        match.bonus_report,
        "build_report",
        lambda cfg, sg: {"totals_by_group": {"COSMOS77": 60}, "bonus_claim": {}, "sub_games": sg},
    )
    monkeypatch.setattr(match.bonus_report, "serialize", lambda r: '{"ok":1}')
    result = asyncio.run(
        match.bonus_series_live(
            _SeriesCfg(),
            None,
            tmp_path,
            our_cop="https://oc/mcp",
            our_thief="https://ot/mcp",
            their_cop="https://tc/mcp",
            their_thief="https://tt/mcp",
            token="tok",
        )
    )
    assert seen["g1cop"] == "https://oc/mcp" and seen["g2thief"] == "https://tt/mcp"
    assert result["totals_by_group"] == {"COSMOS77": 60}
    assert (tmp_path / "bonus_game.json").exists()


def test_build_cloud_engine_attaches_state_sync(monkeypatch: Any) -> None:
    """Cross-process games need ClientStateSync or the canonical board never moves."""
    from cosmos77_ex06.bonus import cloud

    monkeypatch.setattr(cloud, "GeminiClient", lambda *a, **k: object())
    monkeypatch.setattr(cloud, "GameEngine", lambda *a, **k: type("E", (), {})())
    monkeypatch.setattr(cloud, "ClientStateSync", lambda clients: ("sync", clients))
    monkeypatch.setattr("fastmcp.Client", lambda url, auth=None: ("client", url))
    engine, clients = cloud.build_cloud_engine(
        object(), None, cop_url="https://c/mcp", thief_url="https://t/mcp", token="tok"
    )
    assert engine.state_sync[0] == "sync"
    assert set(clients) == {"cop", "thief"}
