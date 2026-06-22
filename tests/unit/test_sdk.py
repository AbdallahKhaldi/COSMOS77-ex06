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
        lambda s: s.run_full_game(),
        lambda s: s.report(),
        lambda s: s.bonus(),
    ],
)
def test_unimplemented_stages_raise(config: Config, tmp_path: Path, call) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        call(sdk)


def test_run_local_game_drives_orchestrator(
    config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SDK.run_local_game delegates to the orchestrator and returns its result dict."""

    async def _fake_run(cfg, gk, client_factory):  # noqa: ANN001, ANN202
        return {"sub_games": [{}], "totals": {"cop": 20, "thief": 5}, "messages": ["hi"]}

    monkeypatch.setattr("cosmos77_ex06.orchestrator.local.run_local_game", _fake_run)
    sdk = SDK(config=config, results_dir=tmp_path)
    out = sdk.run_local_game()
    assert out["totals"] == {"cop": 20, "thief": 5}
