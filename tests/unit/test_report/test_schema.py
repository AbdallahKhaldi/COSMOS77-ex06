"""Tests for the §9.1 internal-game pydantic schema (exact keys, totals, enums)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cosmos77_ex06.report.schema import InternalGameReport, validate_internal_game


def _valid_report() -> dict:
    """A schema-valid 6-sub-game report whose totals match the per-game sums."""
    sub_games = [
        {
            "index": i,
            "winner": "cop",
            "moves": 5,
            "capture": True,
            "cop_score": 20,
            "thief_score": 5,
        }
        for i in range(1, 7)
    ]
    return {
        "group_name": "COSMOS77",
        "students": [{"id": "212389712", "name_en": "Abdallah Khaldi", "name_he": "עבדאללה"}],
        "github_repo": "https://github.com/x/y",
        "cop_mcp_url": "http://localhost:8001/mcp",
        "thief_mcp_url": "http://localhost:8002/mcp",
        "timezone": "Asia/Jerusalem",
        "sub_games": sub_games,
        "totals": {"cop": 120, "thief": 30},
    }


def test_valid_report_passes_and_exposes_exact_keys() -> None:
    report = _valid_report()
    model = validate_internal_game(report)
    assert isinstance(model, InternalGameReport)
    assert set(report) == {
        "group_name",
        "students",
        "github_repo",
        "cop_mcp_url",
        "thief_mcp_url",
        "timezone",
        "sub_games",
        "totals",
    }


def test_top_level_keys_are_exactly_the_spec_set() -> None:
    """The model's field names match §9.1 byte-for-byte (no extras, none missing)."""
    assert set(InternalGameReport.model_fields) == {
        "group_name",
        "students",
        "github_repo",
        "cop_mcp_url",
        "thief_mcp_url",
        "timezone",
        "sub_games",
        "totals",
    }


def test_totals_mismatch_is_rejected() -> None:
    report = _valid_report()
    report["totals"] = {"cop": 999, "thief": 30}
    with pytest.raises(ValidationError, match="totals"):
        validate_internal_game(report)


def test_unknown_top_level_key_is_rejected() -> None:
    report = _valid_report()
    report["unexpected"] = True
    with pytest.raises(ValidationError):
        validate_internal_game(report)


def test_bad_winner_enum_is_rejected() -> None:
    report = _valid_report()
    report["sub_games"][0]["winner"] = "draw"
    with pytest.raises(ValidationError):
        validate_internal_game(report)
