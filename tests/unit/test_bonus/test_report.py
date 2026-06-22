"""Tests for the bonus_game report (E12): schema, canonical determinism, totals, claim."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from cosmos77_ex06.bonus.report import bonus_claim, build, build_report, serialize, totals_by_group
from cosmos77_ex06.bonus.schema import BonusGameReport, validate_bonus_game
from cosmos77_ex06.shared.config import Config


def _sg(index: int, cop: str, thief: str, result: str, cs: int, ts: int) -> dict[str, Any]:
    return {
        "index": index,
        "cop_group": cop,
        "thief_group": thief,
        "result": result,
        "moves": 10,
        "cop_score": cs,
        "thief_score": ts,
    }


# Six captures (every cop wins): g1 = 3*20 + 3*5 = 75; g2 = 3*5 + 3*20 = 75 -> TIE.
_TIE_SUB_GAMES = [_sg(i, "group_1", "group_2", "capture", 20, 5) for i in range(1, 4)] + [
    _sg(i, "group_2", "group_1", "capture", 20, 5) for i in range(4, 7)
]


def _win_sub_games() -> list[dict[str, Any]]:
    """group_1 captures all 3 of its cop games; group_2 fails (survival) -> g1 wins."""
    return [_sg(i, "group_1", "group_2", "capture", 20, 5) for i in range(1, 4)] + [
        _sg(i, "group_2", "group_1", "survival", 5, 10) for i in range(4, 7)
    ]  # g1 = 60+30 = 90 ; g2 = 15+15 = 30


def test_totals_by_group_sums_cop_and_thief_credits() -> None:
    totals = totals_by_group(_TIE_SUB_GAMES, "COSMOS77", "PARTNER77")
    assert totals == {"COSMOS77": 75, "PARTNER77": 75}


def test_bonus_claim_win_lose() -> None:
    """The higher total claims 10, the lower 7."""
    totals = {"COSMOS77": 90, "PARTNER77": 30}
    claim = bonus_claim(totals, "COSMOS77", "PARTNER77", {"win": 10, "lose": 7, "tie": 5})
    assert claim == {"COSMOS77": 10, "PARTNER77": 7}


def test_bonus_claim_lose_when_lower() -> None:
    totals = {"COSMOS77": 30, "PARTNER77": 90}
    claim = bonus_claim(totals, "COSMOS77", "PARTNER77", {"win": 10, "lose": 7, "tie": 5})
    assert claim == {"COSMOS77": 7, "PARTNER77": 10}


def test_bonus_claim_tie_gives_five_each() -> None:
    totals = {"COSMOS77": 75, "PARTNER77": 75}
    claim = bonus_claim(totals, "COSMOS77", "PARTNER77", {"win": 10, "lose": 7, "tie": 5})
    assert claim == {"COSMOS77": 5, "PARTNER77": 5}


def test_build_report_has_exact_top_level_keys(bonus_config: Config) -> None:
    report = build_report(bonus_config, _win_sub_games())
    assert set(report) == {
        "report_type",
        "groups",
        "github_repo_group_1",
        "github_repo_group_2",
        "mcp_url_group_1_cop",
        "mcp_url_group_1_thief",
        "mcp_url_group_2_cop",
        "mcp_url_group_2_thief",
        "timezone",
        "students_group_1",
        "students_group_2",
        "sub_games",
        "totals_by_group",
        "bonus_claim",
        "mutual_agreement",
    }


def test_build_report_validates_and_is_schema_typed(bonus_config: Config) -> None:
    report = build_report(bonus_config, _win_sub_games())
    model = validate_bonus_game(report)
    assert isinstance(model, BonusGameReport)
    assert report["report_type"] == "bonus_game"
    assert report["mutual_agreement"] is True
    assert report["totals_by_group"] == {"COSMOS77": 90, "PARTNER77": 30}
    assert report["bonus_claim"] == {"COSMOS77": 10, "PARTNER77": 7}


def test_build_report_wires_the_four_urls(bonus_config: Config) -> None:
    report = build_report(bonus_config, _win_sub_games())
    assert report["mcp_url_group_1_cop"] == "https://our-cop.example/mcp"
    assert report["mcp_url_group_1_thief"] == "https://our-thief.example/mcp"
    assert report["mcp_url_group_2_cop"] == "https://their-cop.example/mcp"
    assert report["mcp_url_group_2_thief"] == "https://their-thief.example/mcp"
    assert report["students_group_1"][0] == {"id": "212389712", "name": "Abdallah Khaldi"}
    assert report["students_group_2"] == [{"id": "999", "name": "Partner Student"}]


def test_serializer_is_deterministic_byte_for_byte(bonus_config: Config) -> None:
    """The SAME value object serializes to IDENTICAL bytes across repeated builds."""
    a = build(bonus_config, _win_sub_games())
    b = build(bonus_config, _win_sub_games())
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_serializer_ignores_dict_insertion_order(bonus_config: Config) -> None:
    """A report built with shuffled top-level key order serializes to the same bytes.

    This is the cross-codebase parity property a partner relies on: sorted keys make
    insertion order irrelevant, so two independent dicts holding the same data match.
    """
    canonical = build_report(bonus_config, _win_sub_games())
    shuffled = {k: canonical[k] for k in reversed(list(canonical))}
    assert serialize(shuffled) == serialize(canonical)


def test_serializer_emits_raw_unicode_not_escapes(bonus_config: Config) -> None:
    """ensure_ascii=False: Hebrew names (if present) are raw UTF-8, not \\uXXXX."""
    cfg = bonus_config
    cfg._data["bonus"]["students_group_2"] = [{"id": "1", "name": "תסנים"}]  # noqa: SLF001
    text = build(cfg, _win_sub_games())
    assert "תסנים" in text
    assert "\\u" not in text


def test_mismatched_totals_rejected(bonus_config: Config) -> None:
    """A report whose totals_by_group disagree with the sub-game sums is rejected."""
    report = build_report(bonus_config, _win_sub_games())
    report["totals_by_group"] = {"COSMOS77": 999, "PARTNER77": 30}
    with pytest.raises(ValidationError, match="totals_by_group"):
        validate_bonus_game(report)


def test_unknown_top_level_key_rejected(bonus_config: Config) -> None:
    report = build_report(bonus_config, _win_sub_games())
    report["surprise"] = True
    with pytest.raises(ValidationError):
        validate_bonus_game(report)
