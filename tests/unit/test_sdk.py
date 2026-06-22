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
        lambda s: s.run_local_game(),
        lambda s: s.run_full_game(),
        lambda s: s.report(),
        lambda s: s.bonus(),
    ],
)
def test_unimplemented_stages_raise(config: Config, tmp_path: Path, call) -> None:
    sdk = SDK(config=config, results_dir=tmp_path)
    with pytest.raises(NotImplementedError):
        call(sdk)
