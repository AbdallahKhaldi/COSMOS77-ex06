"""Tests for the role-swap series (E12, E13): role assignment + URL wiring + reruns.

Mocked end-to-end — the injected engine factory records the cloud URLs each
sub-game is wired to, so the swap is asserted without any live cloud/MCP/LLM call.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from cosmos77_ex06.bonus.series import role_map, run_series
from cosmos77_ex06.game.match import TechnicalLoss
from cosmos77_ex06.game.state import SubGameResult
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

from .conftest import capture_result, make_engine_factory, survival_result


def _run(config: Config, gatekeeper: Gatekeeper, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_series(config, gatekeeper, **kwargs))


def test_role_map_swaps_at_sub_game_4() -> None:
    """Sub-games 1-3 are group_1 cop / group_2 thief; 4-6 swap."""
    assert [role_map(i) for i in (1, 2, 3)] == [
        {"cop_group": "group_1", "thief_group": "group_2"}
    ] * 3
    assert [role_map(i) for i in (4, 5, 6)] == [
        {"cop_group": "group_2", "thief_group": "group_1"}
    ] * 3


def test_series_assigns_roles_across_six_sub_games(
    bonus_config: Config, gatekeeper: Gatekeeper
) -> None:
    """The returned sub_games carry the correct cop/thief group per the swap."""
    out = _run(
        bonus_config,
        gatekeeper,
        engine_factory=make_engine_factory(lambda _i: capture_result()),
    )
    sub = out["sub_games"]
    assert [s["index"] for s in sub] == [1, 2, 3, 4, 5, 6]
    assert [s["cop_group"] for s in sub] == ["group_1"] * 3 + ["group_2"] * 3
    assert [s["thief_group"] for s in sub] == ["group_2"] * 3 + ["group_1"] * 3


def test_series_wires_the_four_urls_per_sub_game(
    bonus_config: Config, gatekeeper: Gatekeeper
) -> None:
    """Sub-games 1-3 wire OUR cop + THEIR thief; 4-6 wire THEIR cop + OUR thief."""
    wirings: list[dict[str, str]] = []
    factory = make_engine_factory(lambda _i: capture_result(), wirings)
    _run(bonus_config, gatekeeper, engine_factory=factory)
    assert wirings[0] == {
        "cop_url": "https://our-cop.example/mcp",
        "thief_url": "https://their-thief.example/mcp",
    }
    assert wirings[3] == {
        "cop_url": "https://their-cop.example/mcp",
        "thief_url": "https://our-thief.example/mcp",
    }


def test_series_result_field_maps_winner_to_capture_or_survival(
    bonus_config: Config, gatekeeper: Gatekeeper
) -> None:
    """A cop win -> 'capture'; a thief win -> 'survival'."""

    def script(index: int) -> SubGameResult:
        return capture_result() if index % 2 else survival_result()

    out = _run(bonus_config, gatekeeper, engine_factory=make_engine_factory(script))
    results = [s["result"] for s in out["sub_games"]]
    assert results == ["capture", "survival", "capture", "survival", "capture", "survival"]


def test_technical_loss_is_voided_and_reran(bonus_config: Config, gatekeeper: Gatekeeper) -> None:
    """The first attempt raises a TechnicalLoss; the series voids + re-runs it."""
    state = {"failed": False}

    def script(index: int) -> SubGameResult:
        if index == 1 and not state["failed"]:
            state["failed"] = True
            raise TechnicalLoss("foreign server down")
        return capture_result()

    out = _run(bonus_config, gatekeeper, engine_factory=make_engine_factory(script))
    assert len(out["sub_games"]) == 6
    assert out["reruns"] == 1
    assert [s["index"] for s in out["sub_games"]] == [1, 2, 3, 4, 5, 6]


def test_result_flagged_technical_loss_is_voided(
    bonus_config: Config, gatekeeper: Gatekeeper
) -> None:
    """A RETURNED result flagged technical_loss (no exception) is voided + re-run."""
    state = {"voided": False}

    def script(index: int) -> SubGameResult:
        if index == 1 and not state["voided"]:
            state["voided"] = True
            r = capture_result()
            r.technical_loss = True
            return r
        return capture_result()

    out = _run(bonus_config, gatekeeper, engine_factory=make_engine_factory(script))
    assert len(out["sub_games"]) == 6
    assert out["reruns"] == 1


def test_series_gives_up_after_too_many_failures(
    bonus_config: Config, gatekeeper: Gatekeeper, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If every attempt fails, the series raises rather than emitting a short list."""
    from cosmos77_ex06.bonus import series as series_mod

    monkeypatch.setattr(series_mod, "_MAX_ATTEMPTS_FACTOR", 1)

    def always_fail(_index: int) -> SubGameResult:
        raise TechnicalLoss("always down")

    with pytest.raises(TechnicalLoss, match="valid bonus sub-games"):
        _run(bonus_config, gatekeeper, engine_factory=make_engine_factory(always_fail))
