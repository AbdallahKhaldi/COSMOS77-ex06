"""Tests for the thin ``cosmos77-pursuit`` CLI dispatcher (CLAUDE.md rule 2)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.cli.main import build_parser, main


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cosmos77-pursuit 1.00" in out


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 0
    assert "cosmos77-pursuit" in capsys.readouterr().out


def test_parser_has_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--cloud", "--games", "6"])
    assert args.command == "run"
    assert args.cloud is True
    assert args.games == 6


def test_parser_has_local_and_grid_flags() -> None:
    args = build_parser().parse_args(["run", "--local", "--games", "2", "--grid", "3"])
    assert args.local is True and args.games == 2 and args.grid == 3


def test_run_local_routes_to_full_game_and_applies_overrides(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    class _FakeSDK:
        def __init__(self) -> None:
            self.config = type("C", (), {"_data": {"num_games": 6, "grid_size": [5, 5]}})()

        def run_full_game(self, *, cloud: bool = False, gui: bool = False) -> dict[str, object]:
            captured["data"] = dict(self.config._data)
            captured["gui"] = gui
            return {"report": {"totals": {"cop": 0, "thief": 20}, "sub_games": [{}, {}]}}

    monkeypatch.setattr("cosmos77_ex06.sdk.sdk.SDK", _FakeSDK)
    rc = main(["run", "--local", "--games", "2", "--grid", "3"])
    assert rc == 0
    assert captured["data"] == {"num_games": 2, "grid_size": [3, 3]}
    assert "totals" in capsys.readouterr().out


def test_run_ladder_routes_to_sanity_ladder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class _FakeSDK:
        def __init__(self) -> None:
            self.config = type("C", (), {"_data": {"num_games": 6, "grid_size": [5, 5]}})()

        def run_sanity_ladder(self) -> list[dict[str, object]]:
            return [{"grid": [2, 2], "sub_games": 6, "transcript_path": "reports/ladder_2x2.json"}]

    monkeypatch.setattr("cosmos77_ex06.sdk.sdk.SDK", _FakeSDK)
    rc = main(["run", "--local", "--ladder"])
    assert rc == 0
    assert "ladder" in capsys.readouterr().out


def test_report_command_routes_to_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report --send` routes to SDK.report(send=True) (no disk / Gmail touched)."""
    called: dict[str, bool] = {}

    def fake_report(self, *, send: bool = False, sender=None) -> dict[str, bool]:
        called["send"] = send
        return {"sent": send}

    monkeypatch.setattr("cosmos77_ex06.sdk.sdk.SDK.report", fake_report)
    main(["report", "--send"])
    assert called["send"] is True


def test_bonus_parser_accepts_partner_flag() -> None:
    args = build_parser().parse_args(["bonus", "--partner", "config/"])
    assert args.command == "bonus"
    assert args.partner == "config/"


def test_bonus_command_routes_to_sdk(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`bonus` builds an SDK and runs the series; the report summary is printed."""
    captured: dict[str, object] = {}

    class _FakeSDK:
        def __init__(self, config: object = None) -> None:
            captured["config"] = config

        def bonus(self) -> dict[str, object]:
            report = {
                "totals_by_group": {"COSMOS77": 90, "PARTNER77": 30},
                "bonus_claim": {"COSMOS77": 10, "PARTNER77": 7},
            }
            return {"report": report, "json": "{}", "path": "reports/bonus_game.json"}

    monkeypatch.setattr("cosmos77_ex06.sdk.sdk.SDK", _FakeSDK)
    rc = main(["bonus"])
    assert rc == 0
    assert captured["config"] is None  # no --partner -> default config
    out = capsys.readouterr().out
    assert "totals_by_group" in out and "reports/bonus_game.json" in out
