"""series.bonus_series_live — the inter-group bonus role-swap (E12), engine + report mocked."""

from __future__ import annotations

import asyncio
from typing import Any

from cosmos77_ex06.web import series


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


def test_bonus_series_live_overrides_urls_and_writes(monkeypatch: Any, tmp_path: Any) -> None:
    seen: dict[str, Any] = {}

    async def fake_run_series(cfg: Any, *a: Any, **k: Any) -> Any:
        seen["g1cop"] = cfg.get("bonus.mcp.group_1_cop")
        seen["g2thief"] = cfg.get("bonus.mcp.group_2_thief")
        return {"sub_games": [{"index": 1}], "reruns": 0}

    monkeypatch.setattr(series, "run_series", fake_run_series)
    monkeypatch.setattr(
        series.bonus_report,
        "build_report",
        lambda cfg, sg: {"totals_by_group": {"COSMOS77": 60}, "bonus_claim": {}, "sub_games": sg},
    )
    monkeypatch.setattr(series.bonus_report, "serialize", lambda r: '{"ok":1}')
    result = asyncio.run(
        series.bonus_series_live(
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
