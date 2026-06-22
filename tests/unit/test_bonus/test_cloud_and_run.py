"""Tests for the cloud engine factory + the high-level run/SDK driver (E12, mocked).

No network: the cloud factory's FastMCP ``Client`` construction is lazy (it never
connects until entered), and the run/SDK path is exercised with the real
``build_cloud_engine`` monkeypatched out for a fake — so coverage runs end-to-end
with zero live cloud/MCP/LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmos77_ex06.bonus.cloud import build_cloud_engine
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import capture_result, make_engine_factory, survival_result


def test_cloud_factory_wires_urls_and_token(
    bonus_config: Config, gatekeeper: Gatekeeper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The factory binds each role's client to its URL and attaches BONUS_MCP_TOKEN."""
    monkeypatch.setenv("BONUS_MCP_TOKEN", "shared-bonus-token")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    engine, clients = build_cloud_engine(
        bonus_config,
        gatekeeper,
        cop_url="https://their-cop.example/mcp",
        thief_url="https://our-thief.example/mcp",
        client_factory=lambda _k: object(),
    )
    assert engine.url_for("cop") == "https://their-cop.example/mcp"
    assert engine.url_for("thief") == "https://our-thief.example/mcp"
    assert set(clients) == {"cop", "thief"}


def _patch_factory(monkeypatch: pytest.MonkeyPatch, script) -> list[dict[str, str]]:
    """Patch the series' default engine factory with a fake; return the wiring log."""
    from cosmos77_ex06.bonus import series as series_mod

    wirings: list[dict[str, str]] = []
    monkeypatch.setattr(series_mod, "build_cloud_engine", make_engine_factory(script, wirings))
    return wirings


def test_run_bonus_builds_and_saves_canonical_json(
    bonus_config: Config, gatekeeper: Gatekeeper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_bonus drives the series, writes reports/bonus_game.json, returns its dict."""
    from cosmos77_ex06.bonus.run import run_bonus

    _patch_factory(monkeypatch, lambda i: capture_result() if i <= 3 else survival_result())
    reports = tmp_path / "reports"
    out = run_bonus(bonus_config, gatekeeper, reports, client_factory=object())
    assert out["path"] == str(reports / "bonus_game.json")
    on_disk = (reports / "bonus_game.json").read_text(encoding="utf-8")
    assert on_disk.rstrip("\n") == out["json"]
    parsed = json.loads(on_disk)
    assert parsed["report_type"] == "bonus_game"
    # g1: 3 captures as cop (60) + 3 thief survivals (30) = 90 ; g2: 15 + 15 = 30.
    assert parsed["totals_by_group"] == {"COSMOS77": 90, "PARTNER77": 30}
    assert parsed["bonus_claim"] == {"COSMOS77": 10, "PARTNER77": 7}


def test_run_bonus_save_false_skips_file(
    bonus_config: Config, gatekeeper: Gatekeeper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cosmos77_ex06.bonus.run import run_bonus

    _patch_factory(monkeypatch, lambda _i: capture_result())
    out = run_bonus(
        bonus_config, gatekeeper, tmp_path / "reports", client_factory=object(), save=False
    )
    assert out["path"] is None
    assert not (tmp_path / "reports" / "bonus_game.json").exists()


def test_sdk_bonus_runs_end_to_end(
    bonus_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SDK.bonus() delegates to the driver and produces a schema-valid report."""
    from cosmos77_ex06.bonus.schema import validate_bonus_game
    from cosmos77_ex06.sdk.sdk import SDK

    _patch_factory(monkeypatch, lambda _i: capture_result())
    sdk = SDK(config=bonus_config, results_dir=tmp_path / "results")
    out = sdk.bonus(client_factory=object())
    validate_bonus_game(out["report"])
    assert out["report"]["mutual_agreement"] is True


def test_two_codebases_match_bytes(
    bonus_config: Config, gatekeeper: Gatekeeper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two independent run_bonus calls (the 'both groups' scenario) emit identical bytes."""
    from cosmos77_ex06.bonus.diff_check import diff_files
    from cosmos77_ex06.bonus.run import run_bonus

    _patch_factory(monkeypatch, lambda i: capture_result() if i <= 3 else survival_result())
    g1 = tmp_path / "g1"
    g2 = tmp_path / "g2"
    run_bonus(bonus_config, gatekeeper, g1, client_factory=object())
    run_bonus(bonus_config, gatekeeper, g2, client_factory=object())
    assert diff_files(g1 / "bonus_game.json", g2 / "bonus_game.json")["identical"] is True
