"""Tests for the SDK skeleton (CLAUDE.md rule 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmos77_ex06.sdk.sdk import SDK
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def test_construction_derives_results_dir(config: Config) -> None:
    sdk = SDK(config=config)
    assert sdk.repo_root == config.config_dir.parent
    assert sdk.results_dir == sdk.repo_root / "results"
    assert isinstance(sdk.gatekeeper, Gatekeeper)


def test_explicit_results_dir_override(config: Config, tmp_path: Path) -> None:
    override = tmp_path / "custom_results"
    sdk = SDK(config=config, results_dir=override)
    assert sdk.results_dir == override


def test_ledger_delegates_to_gatekeeper(config: Config, tmp_path: Path) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    sdk.gatekeeper.record("subgame_1", {"winner": "cop"})
    assert "subgame_1" in sdk.ledger()


@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.report(),
    ],
)
def test_unimplemented_stages_raise(config: Config, tmp_path: Path, call) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        call(sdk)


def test_run_full_game_validates_saves_and_returns(
    config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SDK.run_full_game validates the report, writes it to disk, returns the pair."""
    import json

    report = {
        "group_name": "COSMOS77",
        "students": [{"id": "1", "name_en": "A", "name_he": "א"}],
        "github_repo": "https://x/y",
        "cop_mcp_url": "http://localhost:8001/mcp",
        "thief_mcp_url": "http://localhost:8002/mcp",
        "timezone": "Asia/Jerusalem",
        "sub_games": [
            {
                "index": 1,
                "winner": "cop",
                "moves": 3,
                "capture": True,
                "cop_score": 20,
                "thief_score": 5,
            }
        ],
        "totals": {"cop": 20, "thief": 5},
    }

    async def _fake_runner(cfg, gk, client_factory, *, gui=False):  # noqa: ANN001, ANN202
        return {"report": report, "transcript": [{"turn": 1}]}

    monkeypatch.setattr("cosmos77_ex06.orchestrator.runner.run_full_game", _fake_runner)
    sdk = SDK(config=config, results_dir=tmp_path)
    out = sdk.run_full_game()
    assert out["report"] == report and out["transcript"] == [{"turn": 1}]
    saved = sdk.reports_dir / "internal_game.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == report


def test_run_sanity_ladder_saves_a_transcript_per_size(
    config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ladder runs 4 rungs and writes one transcript file per grid size."""
    calls: list[list[int]] = []

    def _fake_full_game(self, *, cloud=False, client_factory=None, gui=False):  # noqa: ANN001, ANN202
        calls.append(list(self.config.get("grid_size")))
        return {"report": {"sub_games": [{}, {}]}, "transcript": [{"turn": 1}]}

    monkeypatch.setattr(SDK, "run_full_game", _fake_full_game)
    sdk = SDK(config=config, results_dir=tmp_path)
    summary = sdk.run_sanity_ladder()
    assert [r["grid"] for r in summary] == [[2, 2], [3, 3], [4, 4], [5, 5]]
    assert calls == [[2, 2], [3, 3], [4, 4], [5, 5]]
    for rung in summary:
        assert Path(rung["transcript_path"]).exists()
    assert list(sdk.config.get("grid_size")) == [5, 5]  # restored


def test_run_local_game_drives_orchestrator(
    config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SDK.run_local_game delegates to the orchestrator and returns its result dict."""

    async def _fake_run(cfg, gk, client_factory, *, gui=False):  # noqa: ANN001, ANN202
        return {"sub_games": [{}], "totals": {"cop": 20, "thief": 5}, "messages": ["hi"]}

    monkeypatch.setattr("cosmos77_ex06.orchestrator.local.run_local_game", _fake_run)
    sdk = SDK(config=config, results_dir=tmp_path)
    out = sdk.run_local_game()
    assert out["totals"] == {"cop": 20, "thief": 5}
