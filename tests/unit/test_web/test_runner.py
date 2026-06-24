"""runner.run_exhibition / run_series — event streaming to the per-run feed (match mocked)."""

from __future__ import annotations

import asyncio
from typing import Any

from cosmos77_ex06.web import runner
from cosmos77_ex06.web.feed import MatchFeed


class _GridCfg:
    def get(self, key: str, default: Any = None) -> Any:
        return [3, 3] if key == "grid_size" else default


def _types(feed: MatchFeed, run_id: str, n: int) -> list[str]:
    return [feed._queues[run_id].get_nowait()["type"] for _ in range(n)]  # noqa: SLF001


def test_run_exhibition_streams_meta_turn_end_done(monkeypatch: Any) -> None:
    feed = MatchFeed()
    feed.register("r1")

    async def fake_cross(*a: Any, **k: Any) -> dict[str, Any]:
        k["on_event"]({"type": "turn"})
        return {"winner": "thief", "cop_score": 5, "thief_score": 10, "moves": 7}

    monkeypatch.setattr(runner.match, "cross_game", fake_cross)
    asyncio.run(
        runner.run_exhibition(
            _GridCfg(),
            None,
            feed,
            "r1",
            cop_url="https://c/mcp",
            thief_url="https://t/mcp",
            token="t",
        )
    )
    assert _types(feed, "r1", 4) == ["meta", "turn", "game_end", "done"]


def test_run_series_streams_meta_turn_end_done(monkeypatch: Any) -> None:
    feed = MatchFeed()
    feed.register("r1")

    async def fake_series_live(*a: Any, **k: Any) -> dict[str, Any]:
        k["on_event"]({"type": "turn"})
        return {
            "totals_by_group": {"COSMOS77": 60},
            "bonus_claim": {},
            "sub_games": [],
            "path": "x",
        }

    monkeypatch.setattr(runner.match, "bonus_series_live", fake_series_live)
    asyncio.run(
        runner.run_series(
            _GridCfg(),
            None,
            "reports",
            feed,
            "r1",
            our_cop="https://oc/mcp",
            our_thief="https://ot/mcp",
            their_cop="https://tc/mcp",
            their_thief="https://tt/mcp",
            token="t",
        )
    )
    assert _types(feed, "r1", 4) == ["meta", "turn", "game_end", "done"]


def test_run_exhibition_publishes_error_then_done(monkeypatch: Any) -> None:
    feed = MatchFeed()
    feed.register("r1")

    async def boom(*a: Any, **k: Any) -> dict[str, Any]:
        raise RuntimeError("foreign server down")

    monkeypatch.setattr(runner.match, "cross_game", boom)
    asyncio.run(
        runner.run_exhibition(
            _GridCfg(),
            None,
            feed,
            "r1",
            cop_url="https://c/mcp",
            thief_url="https://t/mcp",
            token="t",
        )
    )
    assert _types(feed, "r1", 3) == ["meta", "error", "done"]
